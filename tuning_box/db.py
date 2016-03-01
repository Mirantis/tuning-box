# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import functools
import json

import flask_sqlalchemy
import sqlalchemy.event
import sqlalchemy.ext.declarative as sa_decl
from sqlalchemy import types

db = flask_sqlalchemy.SQLAlchemy()
pk_type = db.Integer
pk = functools.partial(db.Column, pk_type, primary_key=True)


def fk(cls, **kwargs):
    return db.Column(pk_type, db.ForeignKey(cls.id), **kwargs)


class ModelMixin(object):
    id = db.Column(pk_type, primary_key=True)

    def __repr__(self):
        args = []
        for attr in self.__repr_attrs__:
            value = getattr(self, attr)
            if attr == 'content' and value is not None and len(value) > 15:
                value = value[:10] + '<...>'
            args.append('{}={!r}'.format(attr, value))
        return '{}({})'.format(type(self).__name__, ','.join(args))


class Json(types.TypeDecorator):
    impl = db.Text

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)


class Namespace(ModelMixin, db.Model):
    name = db.Column(db.String(128))
    __repr_attrs__ = ('id', 'name')

# Component registry


class Component(ModelMixin, db.Model):
    name = db.Column(db.String(128))
    schemas = db.relationship("Schema", backref="component")
    templates = db.relationship("Template", backref="component")

    __repr_attrs__ = ('id', 'name')


class Schema(ModelMixin, db.Model):
    name = db.Column(db.String(128))
    component_id = fk(Component)
    namespace_id = fk(Namespace)
    namespace = db.relationship(Namespace)
    content = db.Column(Json)

    __repr_attrs__ = ('id', 'name', 'component', 'namespace', 'content')


class Template(ModelMixin, db.Model):
    name = db.Column(db.String(128))
    component_id = fk(Component)
    content = db.Column(Json)

    __repr_attrs__ = ('id', 'name', 'component', 'content')

# Environment data storage

_environment_components = db.Table(
    'environment_components',
    db.Column('environment_id', pk_type, db.ForeignKey('environment.id')),
    db.Column('component_id', pk_type, db.ForeignKey('component.id')),
)


class Environment(ModelMixin, db.Model):
    components = db.relationship(Component, secondary=_environment_components)

    __repr_attrs__ = ('id',)


class EnvironmentHierarchyLevel(ModelMixin, db.Model):
    environment_id = fk(Environment)
    environment = db.relationship(Environment, backref='hierarchy_levels')
    name = db.Column(db.String(128))
    parent_id = db.Column(pk_type,
                          db.ForeignKey('environment_hierarchy_level.id'))

    @sa_decl.declared_attr
    def parent(cls):
        return db.relationship(cls,
                               backref=db.backref('child', uselist=False),
                               remote_side=cls.id)

    __table_args__ = (
        db.UniqueConstraint(environment_id, name),
        db.UniqueConstraint(environment_id, parent_id),
    )
    __repr_attrs__ = ('id', 'environment', 'parent', 'name')

    @classmethod
    def get_for_environment(cls, environment):
        query = cls.query.filter_by(environment=environment, parent=None)
        root_level = query.one_or_none()
        if not root_level:
            return []
        env_levels = [root_level]
        while env_levels[-1].child:
            env_levels.append(env_levels[-1].child)
        return env_levels


class EnvironmentHierarchyLevelValue(ModelMixin, db.Model):
    level_id = fk(EnvironmentHierarchyLevel)
    level = db.relationship(EnvironmentHierarchyLevel)
    parent_id = db.Column(
        pk_type, db.ForeignKey('environment_hierarchy_level_value.id'))
    value = db.Column(db.String(128))

    @sa_decl.declared_attr
    def parent(cls):
        return db.relationship(cls, remote_side=cls.id)

    __repr_attrs__ = ('id', 'level', 'parent', 'value')


class EnvironmentSchemaValues(ModelMixin, db.Model):
    environment_id = fk(Environment)
    environment = db.relationship(Environment)
    schema_id = fk(Schema)
    schema = db.relationship(Schema)
    level_value_id = fk(EnvironmentHierarchyLevelValue)
    level_value = db.relationship('EnvironmentHierarchyLevelValue')
    values = db.Column(Json)

    __table_args__ = (
        db.UniqueConstraint(environment_id, schema_id, level_value_id),
    )
    __repr_attrs__ = ('id', 'environment', 'schema', 'level_value', 'values')


def get_or_create(cls, **attrs):
    with db.session.begin(nested=True):
        item = cls.query.filter_by(**attrs).one_or_none()
        if not item:
            item = cls(**attrs)
            db.session.add(item)
    return item


def fix_sqlite():
    engine = db.engine

    @sqlalchemy.event.listens_for(engine, "connect")
    def _connect(dbapi_connection, connection_record):
        dbapi_connection.isolation_level = None

    @sqlalchemy.event.listens_for(engine, "begin")
    def _begin(conn):
        conn.execute("BEGIN")


def prefix_tables(prefix):
    for table in db.get_tables_for_bind():
        table.name = prefix + table.name


def unprefix_tables(prefix):
    for table in db.get_tables_for_bind():
        if not table.name.startswith(prefix):
            raise ValueError("Wrong prefix for table {} - it doesn't start "
                             "with {}".format(table.name, prefix))
    for table in db.get_tables_for_bind():
        table.name = table.name[len(prefix):]
