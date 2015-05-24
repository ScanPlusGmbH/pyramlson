import os
import pytest
from pyramid_raml import apidef

from .base import DATA_DIR

def test_method_with_permission():
    path = os.path.join(DATA_DIR, 'test-api.raml')
    api = apidef.RamlApiDefinition(path)
    assert api.base_path == '/api/v1'
