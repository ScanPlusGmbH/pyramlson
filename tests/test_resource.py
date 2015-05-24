import os
import pytest
from webtest import TestApp
from pyramid.config import Configurator
from pyramid.testing import DummyRequest
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy

from .base import DATA_DIR

def make_app(config):
    return TestApp(config.make_wsgi_app())

def test_method_with_permission():
    settings = {'pyramid_raml.apidef_path': os.path.join(DATA_DIR, 'test-api.raml')}
    config = Configurator(settings=settings, introspection=True)
    config.include('pyramid_raml')
    config.scan('.resource')
    app = make_app(config)
    r = app.get('/api/v1/books', status=200)
    r = app.get('/api/v1/books/123', status=200)
    r = app.get('/api/v1/books/321', status=200)
    r = app.get('/api/v1/books/111', status=404)
    print("response", r)
