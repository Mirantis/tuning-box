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
import flask_restful
from flask_restful import fields

from tuning_box import db

api = flask_restful.Api()

namespace_fields = {
    'id': fields.Integer,
    'name': fields.String,
}


@api.resource('/namespaces', '/namespaces/<int:namespace_id>')
class Namespace(flask_restful.Resource):
    @flask_restful.marshal_with(namespace_fields)
    def get(self, namespace_id=None):
        if namespace_id is None:
            return db.Namespace.query.all()
        else:
            return db.Namespace.query.get_or_404(namespace_id)


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
