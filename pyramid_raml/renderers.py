import json
import traceback
import dicttoxml
import jsonschema

from pyramid.renderers import JSON
from lxml import etree
from collections import namedtuple


RendererState = namedtuple('RendererState', ['schema', 'data'])


def validating_xml_serializer(obj, **kw):
    (data, xmlschema) = (obj, None)
    if type(obj) is RendererState:
        data = obj.data
        xmlschema = obj.schema
    serialized = dicttoxml.dicttoxml(data, **kw)
    if xmlschema:
        xmlschema.assertValid(etree.fromstring(serialized))
    return serialized

class ValidatingXmlRenderer(object):
    """ Renderer that returns a XML-encoded string """
    def __init__(self, serializer=validating_xml_serializer, **kw):
        self.serializer = serializer
        self.kw = kw

    def __call__(self, info):
        """ Returns a XML-encoded string with content-type
        ``application/xml``. The content-type may be overridden by
        setting ``request.response.content_type``."""
        def _render(value, system):
            request = system.get('request')
            if request is not None:
                response = request.response
                ct = response.content_type
                if ct == response.default_content_type:
                    response.content_type = 'application/xml'
            return self.serializer(value, **self.kw)

        return _render


def validating_json_serializer(obj, default, **kw):
    (data, schema) = (obj, None)
    if type(obj) is RendererState:
        data = obj.data
        schema = obj.schema
    if schema:
        # will raise a jsonschema.ValidationError in case of a validation error
        try:
            jsonschema.validate(data, schema, format_checker=jsonschema.draft4_format_checker)
        except Exception as e:
            print("VALIDATION PROBLEM", str(e))
            print("".join(traceback.format_exception(*request.exc_info)))
    return json.dumps(data, default=default, **kw)


class ValidatingJsonRenderer(JSON):

    def __init__(self, adapters=(), **kw):
        super(ValidatingJsonRenderer, self).__init__(
                serializer=validating_json_serializer,
                adapters=adapters, **kw)

    def __call__(self, info):
        """ Returns a plain JSON-encoded string with content-type
        ``application/json``. The content-type may be overridden by
        setting ``request.response.content_type``."""
        def _render(value, system):
            request = system.get('request')
            if request is not None:
                response = request.response
                ct = response.content_type
                if ct == response.default_content_type:
                    response.content_type = 'application/json'
            default = self._make_default(request)
            return self.serializer(value, default=default, **self.kw)

        return _render
