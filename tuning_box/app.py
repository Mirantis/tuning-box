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

import itertools

import flask
import flask_restful
from flask_restful import fields
from werkzeug import routing
from werkzeug import urls

from tuning_box import db

api = flask_restful.Api()

namespace_fields = {
    'id': fields.Integer,
    'name': fields.String,
}


@api.resource('/namespaces', '/namespaces/<int:namespace_id>')
class Namespace(flask_restful.Resource):
    method_decorators = [flask_restful.marshal_with(namespace_fields)]

    def get(self, namespace_id=None):
        if namespace_id is None:
            return db.Namespace.query.all()
        else:
            return db.Namespace.query.get_or_404(namespace_id)

    def post(self):
        namespace = db.Namespace(name=flask.request.json['name'])
        db.db.session.add(namespace)
        db.db.session.commit()
        return namespace, 201

    def put(self, namespace_id):
        namespace = db.Namespace.query.get_or_404(namespace_id)
        namespace.name = flask.request.json['name']
        db.db.session.commit()
        return namespace, 201

    def delete(self, namespace_id):
        namespace = db.Namespace.query.get_or_404(namespace_id)
        db.db.session.delete(namespace)
        db.db.session.commit()
        return None, 204

schema_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'component_id': fields.Integer,
    'namespace_id': fields.Integer,
    'content': fields.String,
}

template_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'component_id': fields.Integer,
    'content': fields.String,
}

component_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'schemas': fields.List(fields.Nested(schema_fields)),
    'templates': fields.List(fields.Nested(template_fields)),
}


@api.resource('/components', '/components/<int:component_id>')
class Component(flask_restful.Resource):
    method_decorators = [flask_restful.marshal_with(component_fields)]

    def get(self, component_id=None):
        if component_id is None:
            return db.Component.query.all()
        else:
            return db.Component.query.get_or_404(component_id)

    def post(self):
        component = db.Component(name=flask.request.json['name'])
        component.schemas = []
        for schema_data in flask.request.json.get('schemas'):
            schema = db.Schema(name=schema_data['name'],
                               namespace_id=schema_data['namespace_id'],
                               content=schema_data['content'])
            component.schemas.append(schema)
        component.templates = []
        for template_data in flask.request.json.get('templates'):
            template = db.Template(name=template_data['name'],
                                   content=template_data['content'])
            component.templates.append(template)
        db.db.session.add(component)
        db.db.session.commit()
        return component, 201

    def delete(self, component_id):
        component = db.Component.query.get_or_404(component_id)
        db.db.session.delete(component)
        db.db.session.commit()
        return None, 204

environment_fields = {
    'id': fields.Integer,
    'components': fields.List(fields.Integer(attribute='id')),
    'hierarchy_levels': fields.List(fields.String(attribute='name')),
}


@api.resource('/environments', '/environments/<int:environment_id>')
class Environment(flask_restful.Resource):
    method_decorators = [flask_restful.marshal_with(environment_fields)]

    def get(self, environment_id=None):
        if environment_id is None:
            return db.Environment.query.all()
        else:
            return db.Environment.query.get_or_404(environment_id)

    def post(self):
        component_ids = flask.request.json['components']
        components = [db.Component.query.get_or_404(i) for i in component_ids]

        hierarchy_levels = []
        level = None
        for name in flask.request.json['hierarchy_levels']:
            level = db.EnvironmentHierarchyLevel(name=name, parent=level)
            hierarchy_levels.append(level)

        environment = db.Environment(components=components,
                                     hierarchy_levels=hierarchy_levels)
        db.db.session.add(environment)
        db.db.session.commit()
        return environment, 201

    def delete(self, environment_id):
        environment = db.Environment.query.get_or_404(environment_id)
        db.db.session.delete(environment)
        db.db.session.commit()
        return None, 204


class LevelsConverter(routing.BaseConverter):
    """Converter that maps nested levels to list of tuples.

    For example, "level1/value1/level2/value2/" is mapped to
    [("level1", "value1"), ("level2", "value2")].

    Note that since it can be empty it includes following "/":

        Rule('/smth/<levels:levels>values')

    will parse "/smth/values" and "/smth/level1/value1/values".
    """

    regex = "([^/]+/[^/]+/)*"

    def to_python(self, value):
        spl = value.split('/')
        return list(zip(spl[::2], spl[1::2]))

    def to_url(self, value):
        parts = itertools.chain.from_iterable(value)
        quoted_parts = (urls.url_quote(p, charset=self.map.charset, safe='')
                        for p in parts)
        return ''.join(p + '/' for p in quoted_parts)


@api.resource(
    '/environments/<int:environment_id>/schema/<int:schema_id>/values')
class EnvironmentSchemaValues(flask_restful.Resource):
    def put(self, environment_id, schema_id):
        esv = db.EnvironmentSchemaValues.query.get((environment_id, schema_id))
        if esv is None:
            esv = db.EnvironmentSchemaValues(
                environment_id=environment_id, schema_id=schema_id)
            db.db.session.add(esv)
        esv.values = flask.request.json
        db.db.session.commit()
        return None, 204


def build_app():
    app = flask.Flask(__name__)
    api.init_app(app)  # init_app spoils Api object if app is a blueprint
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # silence warning
    db.db.init_app(app)
    return app


def main():
    import logging
    logging.basicConfig(level=logging.DEBUG)

    app = build_app()
    app.run()

if __name__ == '__main__':
    main()
