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

from werkzeug import routing

from tuning_box import converters
from tuning_box.tests import base


class TestLevels(base.TestCase):
    def setUp(self):
        super(TestLevels, self).setUp()
        self.map = routing.Map([
            routing.Rule('/smth/<levels:levels>values', endpoint='l'),
        ], converters={'levels': converters.Levels})
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


class TestIdOrName(base.TestCase):
    def setUp(self):
        super(TestIdOrName, self).setUp()
        self.map = routing.Map([
            routing.Rule('/<id_or_name:id_or_name>', endpoint='i'),
        ], converters={'id_or_name': converters.IdOrName})
        self.mapad = self.map.bind('example.org', '/')

    def test_int(self):
        route, kwargs = self.mapad.match('/1')
        self.assertEqual(kwargs['id_or_name'], 1)

    def test_name(self):
        route, kwargs = self.mapad.match('/name')
        self.assertEqual(kwargs['id_or_name'], 'name')

    def test_name_with_slashes(self):
        route, kwargs = self.mapad.match('/name/with/slashes')
        self.assertEqual(kwargs['id_or_name'], 'name/with/slashes')

    def test_reverse_int(self):
        res = self.mapad.build('i', {'id_or_name': 1})
        self.assertEqual(res, '/1')

    def test_reverse_name(self):
        res = self.mapad.build('i', {'id_or_name': 'name'})
        self.assertEqual(res, '/name')

    def test_reverse_name_with_slashes(self):
        res = self.mapad.build('i', {'id_or_name': 'name/with/slashes'})
        self.assertEqual(res, '/name/with/slashes')
