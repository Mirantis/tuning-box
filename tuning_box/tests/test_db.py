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

import flask

from tuning_box import db
from tuning_box.tests import base


class _DBTestCase(base.TestCase):
    def setUp(self):
        super(_DBTestCase, self).setUp()
        self.app = flask.Flask('test')
        self.app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///'
        self.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # no warning
        db.db.init_app(self.app)
        with self.app.app_context():
            db.fix_sqlite()
            db.db.create_all()


class TestDB(_DBTestCase):
    def test_create_all(self):
        pass


class TestEnvironmentHierarchyLevel(_DBTestCase):
    def setUp(self):
        super(TestEnvironmentHierarchyLevel, self).setUp()
        with self.app.app_context():
            session = db.db.session
            environment = db.Environment()
            session.add(environment)
            session.commit()
            self.environment_id = environment.id

    def _create_levels(self, num):
        session = db.db.session
        last_lvl = None
        for i in range(num):
            lvl = db.EnvironmentHierarchyLevel(
                environment_id=self.environment_id,
                parent=last_lvl,
                name="lvl%s" % (i,),
            )
            session.add(lvl)
            last_lvl = lvl
        session.commit()

    def _test_get_for_environment(self, num, expected):
        with self.app.app_context():
            self._create_levels(num)
            res = db.EnvironmentHierarchyLevel.get_for_environment(
                db.Environment(id=self.environment_id))
        level_names = [level.name for level in res]
        self.assertEqual(level_names, expected)

    def test_get_for_environment_empty(self):
        self._test_get_for_environment(0, [])

    def test_get_for_environment_one(self):
        self._test_get_for_environment(1, ['lvl0'])

    def test_get_for_environment_three(self):
        self._test_get_for_environment(3, ['lvl0', 'lvl1', 'lvl2'])
