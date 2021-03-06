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

import os

# oslo_db internals refuse to work properly if this is not set
# actual file name in that URL doesn't matter, it'll be generated by oslo.db
os.environ.setdefault("OS_TEST_DBAPI_ADMIN_CONNECTION", "sqlite:///testdb")

from alembic import command as alembic_command
from alembic import config as alembic_config
import flask
from oslo_db.sqlalchemy import test_base
from oslo_db.sqlalchemy import test_migrations
import testscenarios
from werkzeug import exceptions

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

    def test_get_or_create_get(self):
        with self.app.app_context():
            db.db.session.add(db.Component(name="nsname"))
            res = db.get_or_create(db.Component, name="nsname")
            self.assertEqual(res.name, "nsname")

    def test_get_or_create_create(self):
        with self.app.app_context():
            res = db.get_or_create(db.Component, name="nsname")
            self.assertIsNotNone(res.id)
            self.assertEqual(res.name, "nsname")


class TestGetByIdOrName(_DBTestCase):
    def setUp(self):
        super(TestGetByIdOrName, self).setUp()
        ctx = self.app.app_context()
        ctx.push()
        self.addCleanup(ctx.pop)
        self.component = db.Component(name="compname")
        db.db.session.add(self.component)
        db.db.session.flush()

    def test_by_id(self):
        res = db.Component.query.get_by_id_or_name(self.component.id)
        self.assertEqual(self.component, res)

    def test_by_name(self):
        res = db.Component.query.get_by_id_or_name(self.component.name)
        self.assertEqual(self.component, res)

    def test_by_id_fail(self):
        self.assertRaises(
            exceptions.NotFound,
            db.Component.query.get_by_id_or_name,
            self.component.id + 1,
        )

    def test_by_name_fail(self):
        self.assertRaises(
            exceptions.NotFound,
            db.Component.query.get_by_id_or_name,
            self.component.name + "_",
        )


class TestDBPrefixed(base.PrefixedTestCaseMixin, TestDB):
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


class TestEnvironmentHierarchyLevelPrefixed(base.PrefixedTestCaseMixin,
                                            TestEnvironmentHierarchyLevel):
    pass


class TestMigrationsSync(testscenarios.WithScenarios,
                         test_migrations.ModelsMigrationsSync,
                         base.TestCase,
                         test_base.DbTestCase):
    scenarios = [
        ('sqlite', {'FIXTURE': test_base.DbFixture}),
        # ('mysql', {'FIXTURE': test_base.MySQLOpportunisticFixture}),
        ('postgres', {'FIXTURE': test_base.PostgreSQLOpportunisticFixture}),
    ]

    def get_metadata(self):
        return db.db.metadata

    def get_engine(self):
        return self.engine

    def get_alembic_config(self, engine):
        config = alembic_config.Config()
        config.set_main_option('sqlalchemy.url', str(engine.url))
        config.set_main_option('script_location', 'tuning_box/migrations')
        config.set_main_option('version_table', 'alembic_version')
        return config

    def db_sync(self, engine):
        config = self.get_alembic_config(engine)
        alembic_command.upgrade(config, 'head')


class TestMigrationsSyncPrefixed(base.PrefixedTestCaseMixin,
                                 TestMigrationsSync):
    def include_object(self, object_, name, type_, reflected, compare_to):
        # ModelsMigrationsSync doesn't pass any config to MigrationContext
        # so alembic assumes 'alembic_version' table by default, not our
        # prefixed table
        if type_ == 'table' and name == 'test_prefix_alembic_version':
            return False

        return super(TestMigrationsSyncPrefixed, self).include_object(
            object_, name, type_, reflected, compare_to)

    def get_alembic_config(self, engine):
        config = super(TestMigrationsSyncPrefixed, self).get_alembic_config(
            engine)
        config.set_main_option('version_table', 'test_prefix_alembic_version')
        config.set_main_option('table_prefix', 'test_prefix_')
        return config
