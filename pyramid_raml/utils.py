import logging
import jsonschema
import xmltodict

from lxml import etree
from lxml.etree import XMLSyntaxError, DocumentInvalid
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.renderers import render_to_response

from .apidef import IRamlApiDefinition
from .renderers import RendererState


log = logging.getLogger(__name__)

# last failsafe mime type for response objects,
# is used when everything else fails
DEFAULT_MTYPE = 'application/json'

def get_accepted_mtype(request, wanted):
    settings = request.registry.settings
    accepted = request.accept.best_match((wanted,))
    if accepted not in SUPPORTED_CONVERTERS:
        ret = settings.get('pyramid_raml.default_mime_type', DEFAULT_MTYPE)
        log.info("Client accepts body of type {} which is not in supported, chosing {}".format(accepted, ret))
        return ret
    return accepted

def find_matching_body(request, resource):
    for body in resource.body:
        if body.mime_type == request.content_type:
            return body
    supported = [b.mime_type for b in resource.body if b.mime_type in SUPPORTED_CONVERTERS]
    raise HTTPBadRequest("Unsupported body content-type: '{}', please use one of the following: {}".format(
        request.content_type,
        ", ".join(supported)))

def prepare_body(request, resource):
    if not request.body:
        raise HTTPBadRequest(u"Empty body!".format(request.body))
    body = find_matching_body(request, resource)
    converter = SUPPORTED_CONVERTERS[body.mime_type]
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


def get_renderer(request, resource, status_code):
    """"Return a renderer depending on Accept header of the request
    and supported mime_types of resource response bodies
    """
    mtype = None
    schema = None
    apidef = request.registry.queryUtility(IRamlApiDefinition)
    default_mtype = apidef.default_mime_type
    if not resource.body:
        # find matching response body definition in resource
        body = None
        for response in resource.responses:
            if response.code == status_code:
                body = response.body
                break
        if body:
            mtype = request.accept.best_match((b.mime_type for b in body))
            for b in body:
                if b.mime_type == mtype:
                    schema = b.schema
                    schema = apidef.get_schema(b, mtype)
                    break
        else:
            mtype = default_mime_type
    else:
        mtype = request.accept.best_match((b.mime_type for b in resource.body))
        for b in resource.body:
            if b.mime_type == mtype:
                schema = apidef.get_schema(b, mtype)
                break

    if mtype not in SUPPORTED_RENDERERS:
        mtype = default_mtype
        schema = None
    return (schema, SUPPORTED_RENDERERS[mtype])

def render_view(request, resource, data, status_code):
    """Render data to response using matching renderer"""
    (schema, renderer) = get_renderer(request, resource, status_code)
    state = RendererState(schema, data)
    response = request.response
    response.status_int = status_code
    return render_to_response(renderer, state, request=request, response=response)

SUPPORTED_RENDERERS = {
    'application/json': 'validating_json',
    'text/xml': 'validating_xml',
    'application/xml': 'validating_xml',
}
