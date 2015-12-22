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

import json

from flask import testing
from werkzeug import routing
from werkzeug import wrappers

from tuning_box import app
from tuning_box import db
from tuning_box.tests import base


class JSONResponse(wrappers.BaseResponse):
    @property
    def json(self):
        return json.loads(self.data.decode(self.charset))


class Client(testing.FlaskClient):
    def __init__(self, app):
        super(Client, self).__init__(app, response_wrapper=JSONResponse)

    def open(self, *args, **kwargs):
        data = kwargs.get('data')
        if data is not None:
            kwargs['data'] = json.dumps(data)
            kwargs['content_type'] = 'application/json'
        return super(Client, self).open(*args, **kwargs)


class TestApp(base.TestCase):
    def setUp(self):
        super(TestApp, self).setUp()
        self.app = app.build_app()
        self.app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///'
        with self.app.app_context():
            db.db.create_all()
        self.client = Client(self.app)

    def _fixture(self):
        with self.app.app_context():
            namespace = db.Namespace(id=3, name='nsname')
            db.db.session.add(namespace)
            component = db.Component(
                id=7,
                name='component1',
                schemas=[db.Schema(
                    id=5,
                    name='schema1',
                    namespace_id=namespace.id,
                    content='schema1_content',
                )],
                templates=[db.Template(
                    id=5,
                    name='template1',
                    content='template1_content',
                )],
            )
            db.db.session.add(component)
            environment = db.Environment(id=9, components=[component])
            hierarchy_levels = [
                db.EnvironmentHierarchyLevel(name="lvl1"),
                db.EnvironmentHierarchyLevel(name="lvl2"),
            ]
            hierarchy_levels[1].parent = hierarchy_levels[0]
            environment.hierarchy_levels = hierarchy_levels
            db.db.session.add(environment)
            db.db.session.commit()

    def test_get_namespaces_empty(self):
        res = self.client.get('/namespaces')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, [])

    def test_get_namespaces(self):
        self._fixture()
        res = self.client.get('/namespaces')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, [{'id': 3, 'name': 'nsname'}])

    def test_get_one_namespace(self):
        self._fixture()
        res = self.client.get('/namespaces/3')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {'id': 3, 'name': 'nsname'})

    def test_get_one_namespace_404(self):
        res = self.client.get('/namespaces/3')
        self.assertEqual(res.status_code, 404)

    def test_post_namespace(self):
        res = self.client.post('/namespaces', data={'name': 'nsname'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json, {'id': 1, 'name': 'nsname'})

    def test_put_namepsace(self):
        self._fixture()
        res = self.client.put('/namespaces/3', data={'name': 'nsname1'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json, {'id': 3, 'name': 'nsname1'})
        with self.app.app_context():
            namespace = db.Namespace.query.get(3)
            self.assertEqual(namespace.name, 'nsname1')

    def test_put_namepsace_404(self):
        res = self.client.put('/namespaces/3', data={'name': 'nsname1'})
        self.assertEqual(res.status_code, 404)

    def test_delete_namepsace(self):
        self._fixture()
        res = self.client.delete('/namespaces/3')
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')
        with self.app.app_context():
            namespace = db.Namespace.query.get(3)
            self.assertIsNone(namespace)

    def test_delete_namepsace_404(self):
        res = self.client.delete('/namespaces/3')
        self.assertEqual(res.status_code, 404)

    @property
    def _component_json(self):
        return {
            'id': 7,
            'name': 'component1',
            'schemas': [{
                'id': 5,
                'name': 'schema1',
                'component_id': 7,
                'namespace_id': 3,
                'content': 'schema1_content',
            }],
            'templates': [{
                'id': 5,
                'name': 'template1',
                'component_id': 7,
                'content': 'template1_content',
            }],
        }

    def test_get_components_empty(self):
        res = self.client.get('/components')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, [])

    def test_get_components(self):
        self._fixture()
        res = self.client.get('/components')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, [self._component_json])

    def test_get_one_component(self):
        self._fixture()
        res = self.client.get('/components/7')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, self._component_json)

    def test_get_one_component_404(self):
        res = self.client.get('/components/7')
        self.assertEqual(res.status_code, 404)

    def test_post_component(self):
        self._fixture()  # Just for namespace
        json = self._component_json
        del json['id']
        del json['schemas'][0]['id'], json['schemas'][0]['component_id']
        del json['templates'][0]['id'], json['templates'][0]['component_id']
        res = self.client.post('/components', data=json)
        self.assertEqual(res.status_code, 201)
        json['id'] = 8
        json['schemas'][0]['component_id'] = json['id']
        json['templates'][0]['component_id'] = json['id']
        json['schemas'][0]['id'] = json['templates'][0]['id'] = 6
        self.assertEqual(res.json, json)

    def test_delete_component(self):
        self._fixture()
        res = self.client.delete('/components/7')
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')
        with self.app.app_context():
            component = db.Component.query.get(7)
            self.assertIsNone(component)

    def test_delete_component_404(self):
        res = self.client.delete('/components/7')
        self.assertEqual(res.status_code, 404)

    def test_get_environments_empty(self):
        res = self.client.get('/environments')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, [])

    def test_get_environments(self):
        self._fixture()
        res = self.client.get('/environments')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, [{'id': 9, 'components': [7],
                                     'hierarchy_levels': ['lvl1', 'lvl2']}])

    def test_get_one_environment(self):
        self._fixture()
        res = self.client.get('/environments/9')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json, {'id': 9, 'components': [7],
                                    'hierarchy_levels': ['lvl1', 'lvl2']})

    def test_get_one_environment_404(self):
        res = self.client.get('/environments/9')
        self.assertEqual(res.status_code, 404)

    def test_post_environment(self):
        self._fixture()
        json = {'components': [7], 'hierarchy_levels': ['lvla', 'lvlb']}
        res = self.client.post('/environments', data=json)
        self.assertEqual(res.status_code, 201)
        json['id'] = 10
        self.assertEqual(res.json, json)

    def test_post_environment_404(self):
        self._fixture()
        json = {'components': [8], 'hierarchy_levels': ['lvla', 'lvlb']}
        res = self.client.post('/environments', data=json)
        self.assertEqual(res.status_code, 404)

    def test_delete_environment(self):
        self._fixture()
        res = self.client.delete('/environments/9')
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')
        with self.app.app_context():
            environment = db.Environment.query.get(9)
            self.assertIsNone(environment)

    def test_delete_environment_404(self):
        res = self.client.delete('/environments/9')
        self.assertEqual(res.status_code, 404)

    def test_put_esv_root(self):
        self._fixture()
        res = self.client.put('/environments/9/schema/5/values',
                              data={'k': 'v'})
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')
        with self.app.app_context():
            esv = db.EnvironmentSchemaValues.query.filter_by(
                environment_id=9, schema_id=5).one_or_none()
            self.assertIsNotNone(esv)
            self.assertEqual(esv.values, {'k': 'v'})
            self.assertIsNone(esv.level_value.level)
            self.assertIsNone(esv.level_value.parent)
            self.assertIsNone(esv.level_value.value)

    def test_put_esv_deep(self):
        self._fixture()
        res = self.client.put(
            '/environments/9/schema/5/lvl1/val1/lvl2/val2/values',
            data={'k': 'v'},
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.data, b'')
        with self.app.app_context():
            esv = db.EnvironmentSchemaValues.query.filter_by(
                environment_id=9, schema_id=5).one_or_none()
            self.assertIsNotNone(esv)
            self.assertEqual(esv.values, {'k': 'v'})
            level_value = esv.level_value
            self.assertEqual(level_value.level.name, 'lvl2')
            self.assertEqual(level_value.value, 'val2')
            level_value = level_value.parent
            self.assertEqual(level_value.level.name, 'lvl1')
            self.assertEqual(level_value.value, 'val1')
            level_value = level_value.parent
            self.assertIsNone(level_value.level)
            self.assertIsNone(level_value.parent)
            self.assertIsNone(level_value.value)

    def test_put_esv_bad_level(self):
        self._fixture()
        res = self.client.put('/environments/9/schema/5/lvlx/1/values',
                              data={'k': 'v'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json,
            {"message": "Unexpected level name 'lvlx'. Expected 'lvl1'."},
        )


class TestLevelsConverter(base.TestCase):
    def setUp(self):
        super(TestLevelsConverter, self).setUp()
        self.map = routing.Map([
            routing.Rule('/smth/<levels:levels>values', endpoint='l'),
        ], converters={'levels': app.LevelsConverter})
        self.mapad = self.map.bind('example.org', '/')

    def test_empty(self):
        route, kwargs = self.mapad.match('/smth/values')
        self.assertEqual(kwargs['levels'], [])

    def test_one(self):
        route, kwargs = self.mapad.match('/smth/level1/value1/values')
        self.assertEqual(kwargs['levels'], [('level1', 'value1')])

    def test_multi(self):
        route, kwargs = self.mapad.match(
            '/smth/level1/value1/level2/value2/values')
        self.assertEqual(kwargs['levels'],
                         [('level1', 'value1'), ('level2', 'value2')])

    def test_reverse_empty(self):
        res = self.mapad.build('l', {'levels': []})
        self.assertEqual(res, '/smth/values')

    def test_reverse_one(self):
        res = self.mapad.build('l', {'levels': [('level1', 'value1')]})
        self.assertEqual(res, '/smth/level1/value1/values')

    def test_reverse_multi(self):
        res = self.mapad.build(
            'l', {'levels': [('level1', 'value1'), ('level2', 'value2')]})
        self.assertEqual(res, '/smth/level1/value1/level2/value2/values')
