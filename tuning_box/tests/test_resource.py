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

from solar.core import resource as solar_resource
from solar.dblayer import model

from tuning_box import resource
from tuning_box.tests import base


class TestResource(base.TestCase):
    def setUp(self):
        super(TestResource, self).setUp()
        self.addCleanup(model.ModelMeta.remove_all)

    def assert_resources_num(self, num):
        self.assertEqual(num, len(solar_resource.load_all()))

    def test_create_environment(self):
        r = resource.create_environment({
            'hierarchy_levels': ['node'],
        })
        inputs = r.resource_inputs()
        self.assertEqual(inputs['hierarchy_levels'], ['node'])
        self.assert_resources_num(1)

    def test_create_environment_no_levels(self):
        self.assertRaises(
            resource.ValidationError,
            resource.create_environment, {})
        self.assert_resources_num(0)

    def test_create_and_get_environment(self):
        r = resource.create_environment({
            'hierarchy_levels': ['node'],
        })
        env_id = r.name
        r1 = resource.get_environment(env_id)
        self.assertEqual(r1.name, env_id)
        inputs = r1.resource_inputs()
        self.assertEqual(inputs['hierarchy_levels'], ['node'])
        self.assert_resources_num(1)

    def test_get_environment_not_found(self):
        self.assertRaises(
            resource.EnvironmentNotFound,
            resource.get_environment, 1)
