#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Pelix remote services: Zeroconf discovery and event notification

This module depends on the pyzeroconf project by Mike Fletcher
(https://github.com/mcfletch/pyzeroconf).

:author: Thomas Calmant
:copyright: Copyright 2013, isandlaTech
:license: Apache License 2.0
:version: 0.1
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
__version_info__ = (0, 2, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Zeroconf
import zeroconf.mdns as mdns

# Remote services
import pelix.remote
from pelix.utilities import is_string, to_str

# iPOPO decorators
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Invalidate, Validate, Property

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
        self._infos = {}


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
        self._infos.clear()
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

        # Listen to our types
        self._browsers.append(mdns.ServiceBrowser(self._zeroconf,
                                        ZeroconfDiscovery.DNS_DISPATCHER_TYPE,
                                        self))
        self._browsers.append(mdns.ServiceBrowser(self._zeroconf,
                                        ZeroconfDiscovery.DNS_RS_TYPE,
                                        self))

        # Register the dispatcher servlet as a service
        self.__register_servlet()

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


    def endpoint_added(self, endpoint):
        """
        A new service is exported
        """
        # Get the dispatcher servlet access
        access = self._access.get_access()

        # Add access properties
        properties = endpoint.reference.get_properties()
        properties[pelix.remote.PROP_ENDPOINT_FRAMEWORK_UUID] = self._fw_uid
        properties["pelix.access.port"] = access[0]
        properties["pelix.access.path"] = access[1]

        # TODO: add missing information to properties (UID, kind, URL, ...)
        # (see addService)

        # Convert properties to be stored as strings
        properties = self._serialize_properties(properties)

        # Prepare the mDNS entry
        info = mdns.ServiceInfo(ZeroconfDiscovery.DNS_RS_TYPE,  # Type
                                "{0}.{1}".format(endpoint.uid,  # Name
                                                 ZeroconfDiscovery.DNS_RS_TYPE),
                                self._address,  # Access address
                                access[0],  # Access port
                                properties=properties  # Properties
                                )

        self._infos[endpoint.uid] = info

        # Register the service
        self._zeroconf.registerService(info, ZeroconfDiscovery.TTL)


    def endpoint_updated(self, endpoint, old_properties):
        """
        An end point is updated
        """
        # Not available...
        pass


    def endpoint_removed(self, endpoint):
        """
        An end point is removed
        """
        try:
            # Get the associated service info
            info = self._infos.pop(endpoint.uid)

        except KeyError:
            # Unknown service
            pass

        else:
            # Unregister the service
            self._zeroconf.unregisterService(info)


    def addService(self, zeroconf, svc_type, name):
        """
        Called by Zeroconf when a record is updated

        :param zeroconf: The Zeroconf instance than notifies of the modification
        :param svc_type: Service type
        :param name: Service name
        """
        # Get information about the service
        info = None
        retries = 0
        while not info and retries < 10:
            # Try to get information about the service...
            info = self._zeroconf.getServiceInfo(svc_type, name)
            if not info:
                _logger.debug("Timeout reading info about %s", name)

            retries += 1

        # Get access info
        address = to_str(socket.inet_ntoa(info.getAddress()))
        port = info.getPort()

        # Read properties
        properties = self._deserialize_properties(info.getProperties())

        try:
            sender_uid = properties['pelix.framework.uid']
            if sender_uid == self._fw_uid:
                # We sent this message
                _logger.info("Loop back message")
                return

        except KeyError:
            # Not a Pelix message
            _logger.warning("Not a Pelix record")
            return

        if svc_type == ZeroconfDiscovery.DNS_DISPATCHER_TYPE:
            # Dispatcher servlet found
            self._access.send_discovered(address, port,
                                         properties['pelix.access.path'])

        else:
            # Remote service
            _logger.info("New service %s at %s:%d", properties['objectClass'],
                          address, port)

            # TODO: add missing information (see endpoint_added)
            endpoint = {'sender': sender_uid,
                        'properties': properties,
                        'url': None,
                        'uid': None,
                        'name': None,
                        'kind': None,
                        'specifications': properties['objectClass']}

            _logger.info("Endpoint data: %s", endpoint)


    def removeService(self, zeroconf, type_, name):
        """
        Called by Zeroconf when a record is removed

        :param zeroconf: The Zeroconf instance than notifies of the modification
        :param svc_type: Service type
        :param name: Service name
        """
        _logger.info("Service %s removed", name)
