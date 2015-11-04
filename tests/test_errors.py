import os
import unittest

from pyramid import testing
from pyramid.config import Configurator
from pyramid.authentication import BasicAuthAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from .base import DATA_DIR
from .resource import BOOKS

def dummy_check(username, password, request):
    if username == 'somebody' and password == 'bar':
        return [] # authorized without roles
    if username == 'writer' and password == 'bar':
        return ['api-user-writer']
    if username == 'admin' and password == 'bar':
        return ['admin']

class Root:
    __name__ = 'root'
    __parent__ = None

class ErrorsTests(unittest.TestCase):

    def setUp(self):
        settings = {
            'pyramlson.apidef_path': os.path.join(DATA_DIR, 'test-api.raml'),
        }
        auth_policy = BasicAuthAuthenticationPolicy(dummy_check, 'TEST REALM')
        self.config = testing.setUp(settings=settings)
        self.config.set_authorization_policy(ACLAuthorizationPolicy())
        self.config.set_authentication_policy(auth_policy)
        self.config.include('pyramlson')
        self.config.scan('.resource')
        from webtest import TestApp
        self.testapp = TestApp(self.config.make_wsgi_app())

    def tearDown(self):
        testing.tearDown()

    def test_general_notfound(self):
        r = self.testapp.get('/foo', status=404)
        self.assertEquals(r.json_body['message'], '/foo')
        self.assertEquals(r.json_body['success'], False)

    def test_unauthorized(self):
        r = self.testapp.get('/api/v1/books', status=401)
        self.assertEquals(r.json_body['message'], 'You must login to perform this action.')
        self.assertEquals(r.json_body['success'], False)

    def test_bad_roles(self):
        self.testapp.authorization = ('Basic', ('somebody', 'bar'))
        r = self.testapp.get('/api/v1/books', status=403)
        self.assertEquals(r.json_body['message'], 'You are not allowed to perform this action.')
        self.assertEquals(r.json_body['success'], False)

class ErrorsWithDebugTests(unittest.TestCase):
    def setUp(self):
        settings = {
            'pyramlson.apidef_path': os.path.join(DATA_DIR, 'test-errors-api.raml'),
            'pyramlson.debug': 'true',
        }
        self.config = testing.setUp(settings=settings)
        self.config.include('pyramlson')
        self.config.scan('.error_resource')
        from webtest import TestApp
        self.testapp = TestApp(self.config.make_wsgi_app())

    def test_traceback(self):
        r = self.testapp.get('/api/v1/foo', status=500)
        self.assertEquals(r.json_body['success'], False)
        self.assertTrue('traceback' in r.json_body)

class UnknownErrorTests(unittest.TestCase):
    def setUp(self):
        settings = {
            'pyramlson.apidef_path': os.path.join(DATA_DIR, 'test-errors-api.raml'),
            'pyramlson.debug': 'true',
        }
        self.config = testing.setUp(settings=settings)
        self.config.include('pyramlson')
        self.config.scan('.error_resource')
        from webtest import TestApp
        self.testapp = TestApp(self.config.make_wsgi_app())

    def test_unknown_error(self):
        r = self.testapp.get('/api/v1/foo', status=500)
        self.assertEquals(r.json_body['success'], False)
        self.assertEquals(r.json_body['message'], "Unknown error")
