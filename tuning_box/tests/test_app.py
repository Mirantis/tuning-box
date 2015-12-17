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