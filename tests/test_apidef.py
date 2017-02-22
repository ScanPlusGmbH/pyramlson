import json
import os
import unittest

from pyramid import testing

from pyramlson import apidef

from .base import DATA_DIR

def get_api(which='test-api.raml'):
    path = os.path.join(DATA_DIR, which)
    return apidef.RamlApiDefinition(path)

def test_base():
    api = get_api()
    assert api.raml != None
    assert api.base_uri == 'http://{apiUri}/api/v1'
    assert api.base_path == '/api/v1'

def test_notexisting_resources():
    api = get_api()
    assert len(list(api.get_resources('/foo'))) == 0
    assert list(api.get_resources('/books'))[0] == api.raml.resources[0]

def test_filtered_resources():
    api = get_api('test-errors-api.raml')
    assert len(list(api.get_resources('/foo'))) == 1
    assert len(list(api.get_resources('/bar'))) == 1

def test_all_resources():
    api = get_api('test-errors-api.raml')
    assert len(list(api.get_resources())) == 3

def test_schema():
    api = get_api()
    assert api.get_schema(None) is None

    resource = list(api.get_resources('/books'))[1]
    body = resource.body[0]
    schema = json.load(open(os.path.join(DATA_DIR, 'schemas', 'BookRecord.json')))
    assert api.get_schema(body) == schema

def test_existing_traits():
    api = get_api()
    trait = api.get_trait('sorted')
    assert trait is not None
    assert str(trait.description) == 'A sorted collection resource'
    assert len(trait.query_params) == len(api.raml.traits[0].query_params)

    trait = api.get_trait('paged')
    assert trait is not None
    assert str(trait.description) == 'A paged collection resource'
    assert len(trait.query_params) == len(api.raml.traits[1].query_params)

def test_notexisting_traits():
    api = get_api()
    trait = api.get_trait('foo')
    assert trait is None

def test_empty_traits():
    api = get_api('test-errors-api.raml')
    assert api.get_trait('foo') is None

class TestMissingRaml(unittest.TestCase):
    def test_missing_raml(self):
        # not providing a path to RAML specs file in settings['pyramlson.apidef_path']
        # must raise a ValueError
        config = testing.setUp()
        self.assertRaises(ValueError, config.include, 'pyramlson')
