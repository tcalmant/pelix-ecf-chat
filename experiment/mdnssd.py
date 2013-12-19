#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Pelix remote services: Zeroconf discovery and event notification

This module depends on the pyzeroconf project by Mike Fletcher
(https://github.com/mcfletch/pyzeroconf).

To work with ECF, the '.local.' checking in zeroconf.mdns.DNSQuestion must be
removed (around line 220)

:author: Thomas Calmant
:copyright: Copyright 2013, isandlaTech
:license: Apache License 2.0
:version: 0.3
:status: Alpha

..

    Copyright 2013 isandlaTech

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

# Module version
__version_info__ = (0, 3, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Zeroconf
import zeroconf.mdns as mdns

# Remote services
import pelix.remote
import pelix.remote.beans as beans
from pelix.utilities import is_string, to_str

# iPOPO decorators
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Invalidate, Validate, Property
import pelix.constants

# Standard library
import json
import logging
import socket

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

@ComponentFactory("experiment-zeroconf-discovery-factory")
@Provides(pelix.remote.SERVICE_ENDPOINT_LISTENER)
@Requires("_dispatcher", pelix.remote.SERVICE_DISPATCHER)
@Requires('_access', pelix.remote.SERVICE_DISPATCHER_SERVLET)
@Requires("_registry", pelix.remote.SERVICE_REGISTRY)
@Property("_listener_flag", pelix.remote.PROP_LISTEN_EXPORTED, True)
class ZeroconfDiscovery(object):
    """
    Remote services discovery and notification using the module zeroconf
    """
    DNS_RS_TYPE = '_ecfosgirsvc._default.default.'
    DNS_DISPATCHER_TYPE = '_pelix_dispatcher_servlet._tcp.local.'
    TTL = 60  # 1 minute TTL

    def __init__(self):
        """
        Sets up the component
        """
        # End point listener flag
        self._listener_flag = True

        # End points registry
        self._dispatcher = None
        self._registry = None

        # Dispatcher access
        self._access = None

        # Framework UID
        self._fw_uid = None

        # Zeroconf
        self._zeroconf = None
        self._browsers = []

        # Endpoint UID -> ServiceInfo
        self._export_infos = {}

        # mDNS name -> Endpoint UID
        self._imported_endpoints = {}


    @Invalidate
    def invalidate(self, context):
        """
        Component invalidated
        """
        # Stop listeners
        for browser in self._browsers:
            browser.cancel()

        # Close Zeroconf
        self._zeroconf.unregisterAllServices()
        self._zeroconf.close()

        # Clean up
        self._export_infos.clear()
        self._zeroconf = None
        self._fw_uid = None

        _logger.debug("Zeroconf discovery invalidated")


    @Validate
    def validate(self, context):
        """
        Component validated
        """
        # Get the framework UID
        self._fw_uid = context.get_property(pelix.framework.FRAMEWORK_UID)

        # Get the host address
        self._address = socket.inet_aton(socket.gethostbyname(
                                                          socket.gethostname()))

        # Prepare Zeroconf
        self._zeroconf = mdns.Zeroconf("0.0.0.0")

        # Register the dispatcher servlet as a service
        self.__register_servlet()

        # Listen to our types
        self._browsers.append(mdns.ServiceBrowser(self._zeroconf,
                                        ZeroconfDiscovery.DNS_DISPATCHER_TYPE,
                                        self))
        self._browsers.append(mdns.ServiceBrowser(self._zeroconf,
                                        ZeroconfDiscovery.DNS_RS_TYPE,
                                        self))

        _logger.debug("Zeroconf discovery validated")


    def _serialize_properties(self, props):
        """
        Converts properties values into strings
        """
        new_props = {}

        for key, value in props.items():
            if is_string(value):
                new_props[key] = value

            else:
                try:
                    new_props[key] = json.dumps(value)

                except ValueError:
                    new_props[key] = "pelix-type:{0}:{1}" \
                                     .format(type(value).__name__, repr(value))

        # FIXME: for use with ECF
        try:
            new_props[pelix.constants.OBJECTCLASS] = props[pelix.constants.OBJECTCLASS][0]
            new_props[pelix.remote.PROP_IMPORTED_CONFIGS] = props[pelix.remote.PROP_IMPORTED_CONFIGS][0]
        except KeyError:
            pass

        return new_props


    def _deserialize_properties(self, props):
        """
        Converts properties values into their type
        """
        new_props = {}

        for key, value in props.items():
            try:
                try:
                    new_props[key] = json.loads(value)

                except ValueError:
                    if value.startswith("pelix-type:"):
                        # Pseudo-serialized
                        value_type, value = value.split(":", 3)[2:]
                        if '.' in value_type:
                            # Not a builtin type...
                            if value_type not in value:
                                _logger.debug("Won't work: %s (%s)",
                                              value, value_type)

                        new_props[key] = eval(value)

                    else:
                        # String
                        new_props[key] = value

            except Exception as ex:
                _logger.error("Can't deserialize %s: %s", value, ex)

        return new_props


    def __register_servlet(self):
        """
        Registers the Pelix Remote Services dispatcher servlet as a service via
        mDNS
        """
        # Get the dispatcher servlet access
        access = self._access.get_access()

        # Convert properties to be stored as strings
        properties = {"pelix.version": pelix.__version__,
                      pelix.remote.PROP_ENDPOINT_FRAMEWORK_UUID: self._fw_uid,
                      "pelix.access.port": access[0],
                      "pelix.access.path": access[1]}
        properties = self._serialize_properties(properties)

        # Prepare the mDNS entry
        info = mdns.ServiceInfo(ZeroconfDiscovery.DNS_DISPATCHER_TYPE,  # Type
                                "{0}.{1}".format(self._fw_uid,
                                        ZeroconfDiscovery.DNS_DISPATCHER_TYPE),
                                self._address,  # Access address
                                access[0],  # Access port
                                properties=properties
                                )

        # Register the service
        self._zeroconf.registerService(info, ZeroconfDiscovery.TTL)


    def endpoints_added(self, endpoints):
        """
        Multiple endpoints have been added

        :param endpoint: A list of ExportEndpoint beans
        """
        # Get the dispatcher servlet port
        access_port = self._access.get_access()[0]

        # Handle each one separately
        for endpoint in endpoints:
            self._endpoint_added(endpoint, access_port)


    def _endpoint_added(self, exp_endpoint, access_port):
        """
        A new service is exported

        :param exp_endpoint: An ExportEndpoint bean
        :param access_port: The dispatcher access port
        """
        # Convert the export endpoint into an EndpointDescription bean
        endpoint = beans.from_export(exp_endpoint)

        # Get its properties
        properties = endpoint.get_properties()

        # Convert properties to be stored as strings
        properties = self._serialize_properties(properties)

        # Prepare the service name
        svc_name = "{0}.{1}.{2}".format(endpoint.get_id(),
                                        endpoint.get_framework_uuid(),
                                        ZeroconfDiscovery.DNS_RS_TYPE)

        # Prepare the mDNS entry
        info = mdns.ServiceInfo(ZeroconfDiscovery.DNS_RS_TYPE,  # Type
                                svc_name,  # Name
                                self._address,  # Access address
                                access_port,  # Access port
                                properties=properties  # Properties
                                )

        self._export_infos[exp_endpoint.uid] = info

        # Register the service
        self._zeroconf.registerService(info, ZeroconfDiscovery.TTL)


    def endpoint_updated(self, endpoint, old_properties):
        """
        An end point is updated
        """
        # Not available...
        return


    def endpoint_removed(self, endpoint):
        """
        An end point is removed
        """
        try:
            # Get the associated service info
            info = self._export_infos.pop(endpoint.uid)

        except KeyError:
            # Unknown service
            _logger.debug("Unknown removed endpoint: %s", endpoint)

        else:
            # Unregister the service
            self._zeroconf.unregisterService(info)


    def _get_service_info(self, svc_type, name, max_retries=10):
        """
        Tries to get information about the given mDNS service

        :param svc_type: Service type
        :param name: Service name
        :param max_retries: Number of retries before timeout
        :return: A ServiceInfo bean
        """
        info = None
        retries = 0
        while self._zeroconf is not None \
        and info is None \
        and retries < max_retries:
            # Try to get information about the service...
            info = self._zeroconf.getServiceInfo(svc_type, name)
            retries += 1

        return info


    def addService(self, zeroconf, svc_type, name):
        """
        Called by Zeroconf when a record is updated

        :param zeroconf: The Zeroconf instance than notifies of the modification
        :param svc_type: Service type
        :param name: Service name
        """
        # Get information about the service
        info = self._get_service_info(svc_type, name)
        if info is None:
            _logger.warning("Timeout reading service information: %s - %s",
                            svc_type, name)
            return

        # Read properties
        properties = self._deserialize_properties(info.getProperties())

        try:
            sender_uid = properties[pelix.remote.PROP_ENDPOINT_FRAMEWORK_UUID]
            if sender_uid == self._fw_uid:
                # We sent this message
                return

        except KeyError:
            # Not a Pelix message
            _logger.warning("Not a Pelix record: %s", properties)
            return

        if svc_type == ZeroconfDiscovery.DNS_DISPATCHER_TYPE:
            # Dispatcher servlet found, get source info
            address = to_str(socket.inet_ntoa(info.getAddress()))
            port = info.getPort()

            self._access.send_discovered(address, port,
                                         properties['pelix.access.path'])

        elif svc_type == ZeroconfDiscovery.DNS_RS_TYPE:
            # Remote service

            # Get the first available configuration
            configuration = properties[pelix.remote.PROP_IMPORTED_CONFIGS]
            if not is_string(configuration):
                configuration = configuration[0]

            # Ensure we have a list of specifications
            specs = properties[pelix.constants.OBJECTCLASS]
            if is_string(specs):
                specs = [specs]

            try:
                # Make an import bean
                endpoint = beans.ImportEndpoint(
                                properties[pelix.remote.PROP_ENDPOINT_ID],
                                properties[pelix.remote.\
                                            PROP_ENDPOINT_FRAMEWORK_UUID],
                                [configuration], None, specs, properties)

            except KeyError as ex:
                # Log a warning on incomplete endpoints
                _logger.warning("Incomplete endpoint description, "
                                "missing %s: %s", ex, properties)
                return

            else:
                # Register the endpoint
                if self._registry.add(endpoint):
                    # Associate the mDNS name to the endpoint on success
                    self._imported_endpoints[name] = endpoint.uid


    def removeService(self, zeroconf, svc_type, name):
        """
        Called by Zeroconf when a record is removed

        :param zeroconf: The Zeroconf instance than notifies of the modification
        :param svc_type: Service type
        :param name: Service name
        """
        if svc_type == ZeroconfDiscovery.DNS_RS_TYPE:
            # Get information about the service
            try:
                # Get the stored endpoint UID
                uid = self._imported_endpoints.pop(name)

            except KeyError:
                # Unknown service
                return

            else:
                # Remove it
                self._registry.remove(uid)
