import jsonschema
from lxml import etree
from lxml.etree import XMLSyntaxError, DocumentInvalid
from pyramid.httpexceptions import HTTPBadRequest

from .apidef import IRamlApiDefinition


# last failsafe mime type for response objects,
# is used when everything else fails
DEFAULT_MTYPE = 'application/json'

def get_accepted_mtype(request):
    accepted = request.accept
    settings = request.registry.settings
    if accepted not in SUPPORTED_CONVERTERS:
        return settings.get('pyramid_raml.default_mime_type', DEFAULT_MTYPE)
    return accepted

def prepare_body(request, resource):
    accepted = get_accepted_mtype(request)
    for body in resource.body:
        # only json is supported as of now
        mtype = body.mime_type
        if mtype == accepted:
            if mtype not in SUPPORTED_CONVERTERS:
                raise HTTPBadRequest(u"Sorry, body of mime type '{}' is not supported, please use one of {}".format(
                    mtype, ', '.join(SUPPORTED_CONVERTERS.keys())))
            if not request.body:
                raise HTTPBadRequest(u"Empty body!".format(request.body))
            converter = SUPPORTED_CONVERTERS[mtype]
            return converter(body, request)

def prepare_json_body(body, request):
    try:
        data = request.json_body
    except ValueError as e:
        raise HTTPBadRequest(u"Invalid JSON body: {}".format(request.body))
    apidef = request.registry.queryUtility(IRamlApiDefinition)
    schema = apidef.get_schema(body, 'application/json')
    if schema:
        try:
            jsonschema.validate(data, schema, format_checker=jsonschema.draft4_format_checker)
        except jsonschema.ValidationError as e:
            raise HTTPBadRequest(str(e))
    return data

def prepare_xml_body(body, request):
    xml = request.body
    apidef = request.registry.queryUtility(IRamlApiDefinition)
    try:
        parsed_body = etree.fromstring(xml)
    except XMLSyntaxError as e:
        raise HTTPBadRequest(u"Invalid XML body: {}".format(request.body))
    xmlschema = apidef.get_schema(body, 'text/xml')
    if xmlschema:
        try:
            xmlschema.assertValid(parsed_body)
        except DocumentInvalid as e:
            raise HTTPBadRequest(str(e))
    return xml


SUPPORTED_CONVERTERS = {
    'application/json': prepare_json_body,
    'text/xml': prepare_xml_body,
}
