import os
import json
import venusian
import jsonschema
import logging

from inspect import getmembers
from collections import namedtuple

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.interfaces import IExceptionResponse

from .apidef import IRamlApiDefinition

log = logging.getLogger(__name__)


MethodRestConfig = namedtuple('MethodRestConfig', ['http_method', 'permission', 'subpath'])

class api_method(object):

    def __init__(self, http_method, permission=None, subpath=""):
        self.http_method = http_method
        self.permission = permission
        self.subpath = subpath

    def __call__(self, method):
        method._rest_config = MethodRestConfig(self.http_method,
                self.permission,
                self.subpath)
        return method


class api_service(object):
    """Configure a resource """

    def __init__(self, resource_path):
        self.resource_path = resource_path
        self.resources = []

    def callback(self, scanner, name, cls):
        config = scanner.config.with_package(self.module)
        self.apidef = config.registry.queryUtility(IRamlApiDefinition)
        config.include(self.create_routes, route_prefix=self.apidef.base_path)
        log.debug("registered routes with base route '{}'".format(self.apidef.base_path))
        self.create_views(config)

    def create_routes(self, config):
        self.routes = []
        log.debug("Creating routes")
        for resource in self.apidef.get_resources(self.resource_path):
            method = resource.method.upper()
            log.debug("Registering route with relative path {}, method {}".format(resource.path, method))
            route_name = "{}-{}-{}".format(resource.display_name, method, resource.path)
            config.add_route(route_name, resource.path, factory=self.cls, request_method=method)
            self.resources.append((route_name, method, resource))

    def create_views(self, config):
        for (route_name, method, resource) in self.resources:
            log.debug("Creating route {}".format(route_name))
            (view, permission) = self.create_view(resource)
            log.debug("Registering view {} for route name '{}', resource {}".format(view, route_name, resource))
            config.add_view(view,
                    route_name=route_name,
                    renderer='json',
                    context=self.cls,
                    request_method=method,
                    permission=permission)

    def __call__(self, cls):
        self.cls = cls
        info = venusian.attach(cls, self.callback, 'pyramid', depth=1)
        self.module = info.module
        return cls

    def create_view(self, resource):
        (meth, cfg) = self.get_service_class_method(resource)
        log.debug("Got method {} for resource {}".format(meth, resource))
        if not meth:
            raise ValueError("Could not find a method in class {} suitable for resource {}.".format(self.cls, resource))
        def view(context, request):
            required_params = [context]
            optional_params = dict()
            if resource.body:
                required_params.append(prepare_json_body(request, resource))
            if resource.uri_params:
                for param in resource.uri_params:
                    if param.required:
                        if param.name in request.matchdict:
                            required_params.append(request.matchdict[param.name])
                        else:
                            HTTPBadRequest("{} ({}) is required".format(param.name, param.type))
                    else:
                        optional_params[param.name] = request.matchdict.get(param.name, param.default)
            for (name, trait) in self.apidef.get_resource_traits(resource).items():
                print("TRAIT", name, trait)
            if resource.query_params:
                for param in resource.query_params:
                    # FIXME not sure about this one, since query params may come unsorted
                    if param.required:
                        if param.name in request.params:
                            required_params.append(request.params[param.name])
                        else:
                            HTTPBadRequest("{} ({}) is required".format(param.name, param.type))
                    else:
                        optional_params[param.name] = request.params.get(param.name, param.default)
            return meth(*required_params, **optional_params)
        return (view, cfg.permission)

    def get_service_class_method(self, resource):
        rel_path = resource.path[len(self.resource_path):]
        log.debug("Relative path for {}: '{}'".format(resource, rel_path))
        http_method = resource.method.lower()
        for (name, member) in getmembers(self.cls):
            if not hasattr(member, '_rest_config'):
                continue
            cfg = member._rest_config
            if cfg.subpath == rel_path and (cfg.http_method.lower() == http_method) and callable(member):
                return (member, cfg)
        return (None, None)

def prepare_json_body(request, resource):
    if not resource.body:
        return None
    data = None
    for body in resource.body:
        # only json is supported as of now
        if body.mime_type != 'application/json':
            continue
        try:
            data = request.json_body
        except ValueError as e:
            raise HTTPBadRequest(e.message)
        schema = request.registry.apidef.get_schema(resource)
        if schema:
            try:
                jsonschema.validate(data, schema, format_checker=jsonschema.draft4_format_checker)
            except jsonschema.ValidationError as e:
                raise HTTPBadRequest(e.message)
        return data
    return None

def includeme(config):
    """Configure basic RAML REST settings for a Pyramid application.

    You should not call this function directly, but use
    :py:func:`pyramid.config.Configurator.include` to initialise
    the RAML routing.

    .. code-block:: python
       :linenos:
       config = Configurator()
       config.include('pyramid_raml')
    """
    from pyramid_raml.apidef import RamlApiDefinition, IRamlApiDefinition
    settings = config.registry.settings
    settings['pyramid_raml.debug'] = \
            settings.get('debug_all') or \
            settings.get('pyramid.debug_all') or \
            settings.get('pyramid_raml.debug')
    config.add_view('pyramid_raml.error.generic', context=Exception, renderer='json')
    config.add_view('pyramid_raml.error.http_error', context=IExceptionResponse, renderer='json')
    config.add_notfound_view('pyramid_raml.error.notfound', renderer='json')
    config.add_forbidden_view('pyramid_raml.error.forbidden', renderer='json')

    if 'pyramid_raml.apidef_path' not in settings:
        raise ValueError("Cannot create RamlApiDefinition without a RAML file.")
    apidef = RamlApiDefinition(settings['pyramid_raml.apidef_path'])
    config.registry.registerUtility(apidef, IRamlApiDefinition)


__all__ = ['api_method', 'api_service']
