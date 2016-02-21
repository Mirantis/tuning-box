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

import uuid

from solar.core import resource
from solar.core import validation


class EnvironmentNotFound(Exception):
    pass


class ConsistencyError(Exception):
    pass


class ValidationError(Exception):
    pass


def _create_validated(cls, name, args=None, tags=None):
    r = cls(name, "", args=args, tags=tags)
    errors = validation.validate_resource(r)
    if errors:
        r.delete()
        raise ValidationError(errors)
    return r


class EnvironmentResource(resource.Resource):
    _metadata = {
        'input': {
            'hierarchy_levels': {'schema': ["str!"]},
            'components': {'schema': ["str!"], 'value': []},
            'location_id': {'schema': "str!", 'value': 'empty'},
        },
        'tags': ["type=environment"],
    }


def create_environment(env_data):
    id_ = env_data.pop("id", None)
    if not id_:
        id_ = uuid.uuid4().hex
    name = "environment_{}".format(id_)
    tags = ["environment={}".format(id_)]
    r = _create_validated(EnvironmentResource, name, args=env_data, tags=tags)
    return r


def get_environment(env_id):
    resources = resource.load_by_tags({
        "environment={}".format(env_id),
        "type=environment",
    })
    if not resources:
        raise EnvironmentNotFound(env_id)
    if len(resources) > 1:
        raise ConsistencyError("More than one environment with same tag found")
    return resources[0]
