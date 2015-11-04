import logging
import ramlfications

from collections import OrderedDict
from zope.interface import Interface

try:
    from urllib.parse import urlparse
except ImportError: # pragma: no cover
    from urlparse import urlparse

log = logging.getLogger(__name__)


class IRamlApiDefinition(Interface):
        pass


class RamlApiDefinition(object):

    __traits_cache = {}

    def __init__(self, apidef_path):
        self.raml = ramlfications.parse(apidef_path)
        self.base_uri = self.raml.base_uri
        if self.base_uri.endswith('/'):
            self.base_uri = self.base_uri[:-1]
        self.base_path = urlparse(self.base_uri).path

    @property
    def default_mime_type(self):
        return self.raml.media_type

    def get_trait(self, name):
        if not self.raml.traits:
            return None
        trait = None
        if name not in self.__traits_cache:
            for trait in self.raml.traits:
                if trait.name == name:
                    self.__traits_cache[name] = trait
        return self.__traits_cache.get(name)

    def get_resources(self, path=None):
        """ Get resources.
        """
        if not path:
            return self.raml.resources
        return (res for res in self.raml.resources if res.path == path)

    def get_schema_def(self, name):
        for schemas in self.raml.schemas:
            if name in schemas:
                return schemas[name]

    def get_schema(self, body, mime_type):
        if isinstance(body, list):
            bodies = body
            for body in bodies:
                if body.mime_type == 'application/json':
                    break
        if not body or not body.schema:
            return None
        schema = body.schema
        # FIXME there should be a better way to detect an inline schema
        if '$schema' not in schema:
            schema = self.get_schema_def(schema)
        return schema
