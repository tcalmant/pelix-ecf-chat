#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Implementation of the core remote service admin service
"""

# Module version
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Experimental
import experiment.beans as beans
import experiment.rsa
import experiment.rsa.beans as rsa_beans

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Provides, Instantiate, \
    Validate, Invalidate, Requires
import pelix.remote
from pelix.utilities import use_service

# Standard library
import logging
import threading

# ------------------------------------------------------------------------------

# Configuration handler service
SERVICE_CONFIG_HANDLER = 'config.handler'

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

@ComponentFactory()
@Provides(experiment.rsa.SERVICE_RS_ADMIN)
@Requires('_listeners', experiment.rsa.SERVICE_RS_ADMIN_LISTENER,
          aggregate=True, optional=True)
@Instantiate('osgi-remote-service-admin')
class RemoteServiceAdmin(object):
    """
    A Remote Service Admin manages the import and export of services.
    """
    def __init__(self):
        """
        Sets up members
        """
        # Listeners
        self._listeners = []

        # Bundle context
        self._context = None

        # Lists
        self.__exported_regs = []
        self.__imported_regs = []

        # Locks
        self.__export_lock = threading.Lock()
        self.__import_lock = threading.Lock()


    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        self._context = context


    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        self._context = None


    def __publish_import_event(self, event_type, registration):
        """
        TODO: Publishes an import event
        """
        pass


    def __publish_export_event(self, event_type, registration):
        """
        TODO: Publishes an export event
        """
        pass


    def _find_config_handler(self, configs):
        """
        Retrieves the first configuration handler that matches the given
        configurations
        """
        for config in configs:
            svc_ref = self._context.get_service_reference(
                                SERVICE_CONFIG_HANDLER,
                                '({0}={1})'.format(
                                    pelix.remote.PROP_REMOTE_CONFIGS_SUPPORTED,
                                    config))
            if svc_ref is not None:
                return svc_ref


    def export_service(self, svc_ref, properties):
        """
        Export a service to the given end point.

        :param svc_ref: ServiceReference to export
        :param properties: Properties to create local Endpoint. If None,
                           RSA will use SvcRef properties; else they override
                           SvcRef properties except service.id and objectClass
        :return A list of ExportRegistration beans (never None)
        :raise ValueError: Invalid property found, or no
                           SERVICE_EXPORTED_INTERFACES entry in service or given
                           properties
        """
        # Set up properties
        props = svc_ref.get_properties()
        props.update(properties)

        # Avoid some properties to be overridden
        for key in (pelix.constants.OBJECTCLASS, pelix.constants.SERVICE_ID):
            props[key] = svc_ref.get_property(key)

        with self.__export_lock:
            # Get matching configurations
            prop_configs = props.get(pelix.remote.PROP_EXPORTED_CONFIGS)
            if not prop_configs:
                # No configuration specified, use the first matching one
                svc_ref = self._context.get_service_reference(
                                                        SERVICE_CONFIG_HANDLER)
                if svc_ref is None:
                    _logger.warning("No configuration handler registered")
                    return

                else:
                    # We will use a list later
                    handlers_refs = [svc_ref]

            else:
                # Find the matching configuration handlers
                svc_refs = self._context.get_all_service_references(
                                                        SERVICE_CONFIG_HANDLER)
                if not svc_refs:
                    _logger.warning("No configuration handler registered")
                    return

                handlers_refs = set()
                required_configs = set(prop_configs)
                handled_configs = set()

                for svc_ref in svc_refs:
                    # Get handled configurations
                    svc_configs = set(svc_ref.get_property(
                                    pelix.remote.PROP_REMOTE_CONFIGS_SUPPORTED))

                    # Check if there is a match
                    intersection = required_configs.intersection(svc_configs)
                    if intersection:
                        # Update handled configurations
                        handlers_refs.add(svc_ref)
                        handled_configs.update(intersection)
                        required_configs.difference_update(intersection)

                        if not required_configs:
                            # No more configuration to check
                            break

            if not handlers_refs:
                _logger.warning("No configuration handler for: %s",
                                prop_configs)
                return

            # Prepare the endpoint description bean
            endpoint = beans.EndpointDescription(svc_ref, props)

            # Prepare the export reference
            exp_ref = rsa_beans.ExportReference(endpoint, svc_ref)

            # Register endpoints
            registrations = []
            for handler_ref in handlers_refs:
                try:
                    with use_service(self._context, handler_ref) as handler:
                        # Export the service
                        handler.export(svc_ref, props)

                        # Make a registration bean
                        exp_reg = rsa_beans.ExportRegistration(exp_ref)

                        # Notify listeners
                        self.__publish_export_event(
                                                rsa_beans.EXPORT_REGISTRATION,
                                                exp_reg)

                except Exception as ex:
                    # Config Handler error
                    exp_reg = rsa_beans.ExportRegistration(exp_ref, ex)

                    # Notify listeners
                    self.__publish_export_event(rsa_beans.EXPORT_ERROR, exp_reg)

            return registrations


    def import_service(self, endpoint):
        """
        Import a service from an Endpoint. The Remote Service Admin must use the
        given Endpoint to create a proxy. This method can return null if the
        service could not be imported.

        :param endpoint: The Endpoint Description to be used for import.
        :return: An Import Registration that combines the Endpoint Description
                 and the Service Reference or null if the Endpoint could not be
                 imported.
        """
        # Construct the import registration
        try:
            with self.__import_lock:
                # Get the service that handles endpoint with the given configs
                configs = endpoint.get_configuration_types()
                handler_ref = self._find_config_handler(configs)
                if handler_ref is None:
                    _logger.warning("No configuration handler for: %s", configs)
                    return None

                # Request the handler to make a proxy
                with use_service(self._context, handler_ref) as config_handler:
                    proxy = config_handler.make_proxy(endpoint)

                # Register the service
                svc_reg = self._context.register_service(
                                                    endpoint.get_interfaces(),
                                                    proxy,
                                                    endpoint.get_properties())
                svc_ref = svc_reg.get_service_reference()

                # Prepare an import reference bean
                imp_ref = rsa_beans.ImportReference(endpoint, svc_ref)

                # Prepare an import registration bean
                imp_reg = rsa_beans.ImportRegistration(imp_ref)

                # Store it
                self.__imported_regs.append(imp_reg)

            # Publish event
            self.__publish_import_event(rsa_beans.IMPORT_REGISTRATION, imp_reg)

            # Done
            return imp_reg

        except Exception as ex:
            # An error occurred
            registration = rsa_beans.ImportRegistration(None, ex)

            # Publish an event anyway
            self.__publish_import_event(rsa_beans.IMPORT_ERROR, registration)
            return registration


    def get_exported_services(self):
        """
        Return the currently active Export References

        :return: A list of ExportReference beans
        """
        with self.__export_lock:
            return [reg.get_export_reference() for reg in self.__exported_regs]


    def get_imported_endpoints(self):
        """
        Return the currently active Import References.

        :return: A list of ImportReference beans
        """
        with self.__import_lock:
            return [reg.get_import_reference() for reg in self.__imported_regs]
