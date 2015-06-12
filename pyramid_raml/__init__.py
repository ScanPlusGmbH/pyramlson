import os
import venusian
import logging

from inspect import getmembers
from collections import namedtuple, defaultdict

from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPInternalServerError,
    HTTPNoContent,
)
from pyramid.interfaces import IExceptionResponse
from pyramid.renderers import render_to_response

from .apidef import IRamlApiDefinition
from .utils import prepare_body, render_view

log = logging.getLogger(__name__)


DEFAULT_METHOD_MAP = {
    'get': 200,
    'post': 200,
    'put': 201,
    'delete': 204,
    'options': 200,
    'patch': 200,
}

MethodRestConfig = namedtuple('MethodRestConfig', [
    'http_method',
    'permission',
    'subpath',
    'raises',
    'returns'
])

class api_method(object):

    def __init__(self, http_method, permission=None, subpath='', raises=None, returns=None):
        """Configure a resource method corresponding with a RAML resource path

        This decorator must be used to declare REST resources.

        :param http_method: The HTTP method this method maps to.

        :param permission: Permission for this method.

        :param subpath: The subpath of the resource this method is responsible for.

            If no subpath is configured, the method is called for the main path
            of the resource.

        :param raises: A list containing all possible exceptions.

            The list must contain all possible exceptions this method can raise.
            The exceptions MUST have a 'code' property that corresponds to a
            HTTP response code as described in the resource 'responses' map in
            the RAML specification.

        :param returns: A custom HTTP code to return in case of success.

            Configure the HTTP code to return when the method call was successful.
            Per default the codes are expected to match the configured HTTP method:
                - GET/POST/PATCH: 200
                - PUT: 201
                - DELETE: 204

        """
        self.http_method = http_method
        self.permission = permission
        self.subpath = subpath
        self.raises = raises if raises is not None else tuple()
        self.returns = returns if returns is not None else DEFAULT_METHOD_MAP[self.http_method]

    def __call__(self, method):
        method._rest_config = MethodRestConfig(self.http_method,
                self.permission,
                self.subpath,
                self.raises,
                self.returns)
        return method


class api_service(object):
    """Configures a resource by its REST path.

    This decorator configures a class as a REST resource. All endpoints
    must be defined in a RAML file.
    """

    def __init__(self, resource_path):
        log.debug("Resource path: {}".format(resource_path))
        self.resource_path = resource_path
        self.resources = []

    def callback(self, scanner, name, cls):
        config = scanner.config.with_package(self.module)
        apidef = config.registry.queryUtility(IRamlApiDefinition)
        self.create_routes(config)
        log.debug("registered routes with base route '{}'".format(apidef.base_path))
        self.create_views(config)

    def create_routes(self, config):
        log.debug("Creating routes for {}".format(self.resource_path))
        self.routes = []
        supported_methods = defaultdict(set)
        apidef = config.registry.queryUtility(IRamlApiDefinition)
        for resource in apidef.get_resources(self.resource_path):
            method = resource.method.upper()
            path = resource.path
            if apidef.base_path:
                path = "{}{}".format(apidef.base_path, resource.path)
            supported_methods[path].add(method)
            log.debug("Registering route with path {}, method {}".format(path, method))
            route_name = "{}-{}-{}".format(resource.display_name, method, path)
            config.add_route(route_name, path, factory=self.cls, request_method=method)
            self.resources.append((route_name, method, resource, None))
        # add a default OPTIONS route if none was defined by the resource
        opts_meth = 'OPTIONS'
        for path in supported_methods:
            if opts_meth not in supported_methods[path]:
                log.debug("Registering OPTIONS route for {}".format(path))
                route_name = "{}-{}-{}".format(resource.display_name, opts_meth, path)
                config.add_route(route_name, path, factory=self.cls, request_method=opts_meth)
                methods = list(supported_methods[path]) + [opts_meth]
                self.resources.append((route_name, opts_meth, resource, create_options_view(methods)))

    def create_views(self, config):
        for (route_name, method, resource, default_view) in self.resources:
            log.debug("Creating view {}".format(route_name))
            if default_view:
                config.add_view(default_view,
                    route_name=route_name,
                    context=self.cls,
                    request_method=method)
                continue
            (view, permission) = self.create_view(resource)
            log.debug("Registering view {} for route name '{}', resource {}".format(view, route_name, resource))
            config.add_view(view,
                    route_name=route_name,
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
            # URI parameters have the highest prio
            if resource.uri_params:
                for param in resource.uri_params:
                    # pyramid router makes sure the URI params are all
                    # set, otherwise the view isn't called all, because
                    # a NotFound error is triggered before the request
                    # can be routed to this view
                    required_params.append(request.matchdict[param.name])
            # If there's a body defined - include it before traits or query params
            if resource.body:
                required_params.append(prepare_body(request, resource))
            # FIXME: handle traits
            #for (name, trait) in self.apidef.get_resource_traits(resource).items():
            if resource.query_params:
                for param in resource.query_params:
                    # query params are always named (i.e. not positional)
                    # so they effectively become keyword agruments in a
                    # method call, we just make sure they are present
                    # in the request if marked as 'required'
                    if param.required and param.name not in request.params:
                        raise HTTPBadRequest("{} ({}) is required".format(param.name, param.type))
                    else:
                        optional_params[param.name] = request.params.get(param.name, param.default)
            try:
                result = meth(*required_params, **optional_params)
                return render_view(request, resource, result, cfg.returns)
            except Exception as exc:
                code = getattr(exc, 'code', None)
                if code is None:
                    raise exc
                if cfg.raises:
                    for err in cfg.raises:
                        if err.code == code:
                            request.response.status_int = code
                            data = dict(success=False, message=str(exc))
                            return render_view(request, resource, data, code)
                raise exc

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

def create_options_view(supported_methods):
    def view(context, request):
        response = HTTPNoContent()
        response.headers['Access-Control-Allow-Methods'] =\
            ', '.join(supported_methods)
        return response
    return view


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
    from pyramid_raml.renderers import (
        ValidatingXmlRenderer,
        ValidatingJsonRenderer
    )
    settings = config.registry.settings
    settings['pyramid_raml.debug'] = \
            settings.get('debug_all') or \
            settings.get('pyramid.debug_all') or \
            settings.get('pyramid_raml.debug')
    config.add_view('pyramid_raml.error.generic', context=Exception, renderer='json')
    config.add_view('pyramid_raml.error.http_error', context=IExceptionResponse, renderer='json')
    config.add_notfound_view('pyramid_raml.error.notfound', renderer='json')
    config.add_forbidden_view('pyramid_raml.error.forbidden', renderer='json')

    config.add_renderer('validating_xml', ValidatingXmlRenderer())
    config.add_renderer('validating_json', ValidatingJsonRenderer())

    if 'pyramid_raml.apidef_path' not in settings:
        raise ValueError("Cannot create RamlApiDefinition without a RAML file.")
    apidef = RamlApiDefinition(settings['pyramid_raml.apidef_path'])
    config.registry.registerUtility(apidef, IRamlApiDefinition)


__all__ = ['api_method', 'api_service']
