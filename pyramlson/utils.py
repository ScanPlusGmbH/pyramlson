# coding: utf-8
"""
Pyramlson utilities
"""
import jsonschema

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.renderers import render_to_response

from .apidef import IRamlApiDefinition


def prepare_json_body(request, body):
    """ Convert request body to json and validate it. """
    if not request.body:
        raise HTTPBadRequest(u"Empty body!")
    try:
        data = request.json_body
    except ValueError:
        raise HTTPBadRequest(u"Invalid JSON body: {}".format(request.body))
    apidef = request.registry.queryUtility(IRamlApiDefinition)
    schema = apidef.get_schema(body)
    if schema:
        try:
            jsonschema.validate(
                data,
                schema,
                format_checker=jsonschema.draft4_format_checker
            )
        except jsonschema.ValidationError as err:
            raise HTTPBadRequest(str(err))
    return data


def render_view(request, data, status_code):
    """ Render data to response using the correct response status code """
    response = request.response
    response.status_int = status_code
    try:
        return render_to_response('json', data, request=request, response=response)
    except TypeError:
        # 1.5.7 compat
        return render_to_response('json', data, request=request)
