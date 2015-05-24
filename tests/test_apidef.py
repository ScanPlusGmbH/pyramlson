import json
import os
import pytest
from pyramid_raml import apidef

from .base import DATA_DIR

def get_api():
    path = os.path.join(DATA_DIR, 'test-api.raml')
    return apidef.RamlApiDefinition(path)

def test_base():
    api = get_api()
    assert api.raml != None
    assert api.base_uri == 'http://{apiUri}/api/v1'
    assert api.base_path == '/api/v1'

def test_resources():
    api = get_api()
    assert len(list(api.get_resources('/foo'))) == 0
    assert list(api.get_resources('/books'))[0] == api.raml.resources[0]

def test_schema():
    api = get_api()
    resource = list(api.get_resources('/books'))[0]
    assert api.get_schema(resource) is None

    resource = list(api.get_resources('/books'))[1]
    schema = json.load(open(os.path.join(DATA_DIR, 'schemas', 'BookRecord.json')))
    assert api.get_schema(resource) == schema
