# coding: utf-8
"""
Pyramlson API Definition utility
"""
import ramlfications

from zope.interface import Interface

try:
    from urllib.parse import urlparse
except ImportError: # pragma: no cover
    from urlparse import urlparse


class IRamlApiDefinition(Interface):
    """ Marker interface for API Definition """
    # pylint: disable=inherit-non-class
    pass


class RamlApiDefinition(object):
    """ RAML Definition utility.
        Abstracts the access to parsed RAML data.

        :param apidef_path: Path to RAML definition
        :param args_transform_cb: Optional callback that transforms
            view callable argument names (e.g. camelCase vs.
            underscore_case)
        :param convert_params: If true, all parameters
            will be converted to their declared types before beeing
            passed in to the view callable
    """

    __traits_cache = {}

    def __init__(self, apidef_path, args_transform_cb=None, convert_params=False):
        self.raml = ramlfications.parse(apidef_path)
        self.base_uri = self.raml.base_uri
        if self.base_uri.endswith('/'):
            self.base_uri = self.base_uri[:-1]
        self.base_path = urlparse(self.base_uri).path
        self.args_transform_cb = args_transform_cb
        self.convert_params = convert_params

    @property
    def default_mime_type(self):
        """ Return the default mime-type for a resource
            if none was defined in RAML
        """
        return self.raml.media_type

    def get_trait(self, name):
        """ Return a trait from RAML """
        if not self.raml.traits:
            return None
        trait = None
        if name not in self.__traits_cache:
            for trait in self.raml.traits:
                if trait.name == name:
                    self.__traits_cache[name] = trait
        return self.__traits_cache.get(name)

    def get_resources(self, path=None):
        """ Get resources """
        if not path:
            return self.raml.resources
        return (res for res in self.raml.resources if res.path == path)

    def get_schema_def(self, name):
        """ Get schema definition """
        if self.raml.schemas is None:
            return None
        for schemas in self.raml.schemas:
            if name in schemas:
                return schemas[name]

    def get_schema(self, body):
        """ Extract a schema from body for a given mime-type """
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
