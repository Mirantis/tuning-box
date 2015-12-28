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
from sqlalchemy import types

db = flask_sqlalchemy.SQLAlchemy()
pk_type = db.Integer
pk = functools.partial(db.Column, pk_type, primary_key=True)


def fk(cls, **kwargs):
    return db.Column(pk_type, db.ForeignKey(cls.id), **kwargs)


class Json(types.TypeDecorator):
    impl = db.Text

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)


class Namespace(db.Model):
    id = pk()
    name = db.Column(db.String(128))

# Component registry


class Component(db.Model):
    id = pk()
    name = db.Column(db.String(128))
    schemas = db.relationship("Schema", backref="component")
    templates = db.relationship("Template", backref="component")


class Schema(db.Model):
    id = pk()
    name = db.Column(db.String(128))
    component_id = fk(Component)
    namespace_id = fk(Namespace)
    content = db.Column(Json)


class Template(db.Model):
    id = pk()
    name = db.Column(db.String(128))
    component_id = fk(Component)
    content = db.Column(Json)

# Environment data storage

_environment_components = db.Table(
    'environment_components',
    db.Column('environment_id', pk_type, db.ForeignKey('environment.id')),
    db.Column('component_id', pk_type, db.ForeignKey('component.id')),
)


class Environment(db.Model):
    id = pk()
    components = db.relationship(Component, secondary=_environment_components)


class EnvironmentHierarchyLevel(db.Model):
    id = pk()
    environment_id = fk(Environment)
    environment = db.relationship(Environment, backref='hierarchy_levels')
    name = db.Column(db.String(128))
    parent_id = db.Column(pk_type,
                          db.ForeignKey('environment_hierarchy_level.id'))
    parent = db.relationship('EnvironmentHierarchyLevel',
                             backref=db.backref('child', uselist=False),
                             remote_side=[id])

    __table_args__ = (
        db.UniqueConstraint(environment_id, name),
        db.UniqueConstraint(environment_id, parent_id),
    )

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


class EnvironmentHierarchyLevelValue(db.Model):
    id = pk()
    level_id = fk(EnvironmentHierarchyLevel)
    level = db.relationship(EnvironmentHierarchyLevel)
    parent_id = db.Column(
        pk_type, db.ForeignKey('environment_hierarchy_level_value.id'))
    parent = db.relationship('EnvironmentHierarchyLevelValue',
                             remote_side=[id])
    value = db.Column(db.String(128))


class EnvironmentSchemaValues(db.Model):
    id = pk()
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
