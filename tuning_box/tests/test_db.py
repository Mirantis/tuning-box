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


class TestDB(base.TestCase):
    def test_create_all(self):
        app = flask.Flask('test')
        app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///'
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # silence warning
        db.db.init_app(app)
        with app.app_context():
            db.db.create_all()
