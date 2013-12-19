#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Pelix remote services: ECF ZooKeeper discovery and event notification

This module depends on KaZoo and python-javaobj

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
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# iPOPO decorators
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Invalidate, Validate, Property, Instantiate
import pelix.remote
import pelix.remote.beans as beans

# Standard library
import logging

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# KaZoo: ZooKeeper client in Python
try:
    import kazoo.client as kazoo
    import javaobj

except ImportError:
    _logger.error("This bundle requires kazoo (PyPI version is OK), and "
                  "python-javaobj (install the repo version from code.google)")
    raise

# ------------------------------------------------------------------------------

@ComponentFactory("experiment-zookeeper-discovery-factory")
# @Provides(pelix.remote.SERVICE_ENDPOINT_LISTENER, '_controller')
@Requires("_registry", pelix.remote.SERVICE_REGISTRY)
@Property('_hosts', 'zookeeper.hosts', 'disco.ecf-project.org')
# @Property("_listener_flag", pelix.remote.PROP_LISTEN_EXPORTED, True)
@Instantiate('test-zookeeper')
class ZookeeperDiscovery(object):
    """
    Discovery through ZooKeeper
    """
    def __init__(self):
        """
        Sets up the component
        """
        # End point listener flag
        self._listener_flag = True

        # Imported endpoints registry
        self._registry = None

        # Service controller
        self._controller = False

        # Zookeeper hosts
        self._hosts = None

        # Zookeeper connection
        self.__zookeeper = None


    @Invalidate
    def invalidate(self, context):
        """
        Component invalidated
        """
        if self.__zookeeper is not None:
            _logger.debug("Stopping Zookeeper")
            self.__zookeeper.stop()

        self._controller = False


    @Validate
    def validate(self, context):
        """
        Component validated
        """
        if not self._hosts:
            _logger.error("Missing host property")
            return

        # Prepare the connection
        self.__zookeeper = kazoo.KazooClient(hosts=self._hosts)

        # Listen to Zookeeper event
        self.__zookeeper.add_listener(self._zookeeper_event)

        # Connect !
        _logger.debug("Starting zookeeper... %s", self._hosts)
        self.__zookeeper.start()
        _logger.debug("Started.")


    def __print_data(self, uid, data):
        """
        """
        # Load data
        try:
            content = javaobj.loads(data)

        except Exception as ex:
            _logger.exception("Error loading serialized data: %s", ex)
            return

        # Prepare properties
        props = {}

        # Read base values
        for key, value in content.items():
            if isinstance(value, javaobj.JavaObject):
                value = self._from_java(value)

            props[key] = value

        from pprint import pformat
        _logger.debug("Loaded UID %s:\n%s", uid, pformat(props))

        # Convert to an endpoint
        endpoint = beans.EndpointDescription(None, props)
        _logger.debug("Result endpoint: %s", endpoint)


    def _from_java(self, value):
        """
        """
        # FIXME:
        values = {}
        for field in dir(value):
            if field not in ('classdesc', 'annotations') \
            and not field.startswith('_'):
                values[field] = getattr(value, field)

        return values


    def load_content(self):
        """
        """
        # Name of the discovery node
        root = "/zoodiscovery_root"

        try:
            # Look at all of its children
            _logger.debug("Getting children of %s", root)
            uids = self.__zookeeper.get_children(root)
            _logger.debug("Look at %s", uids)
            for uid in uids:
                # Get node data
                _logger.debug("Reading %s...", uid)
                data = self.__zookeeper.get("{0}/{1}".format(root, uid))[0]

                # Print it
                self.__print_data(uid, data)

        except kazoo.NoNodeError:
            _logger.debug("Discovery nodes not found")
            return

        except Exception as ex:
            _logger.exception("Bad: %s", ex)


    def _zookeeper_event(self, state):
        """
        ZooKeeper connection event
        """
        _logger.debug("ZooKeeper changed state: %s", state)

        if state == kazoo.KazooState.LOST:
            # Register somewhere that the session was lost
            self._controller = False
            _logger.debug("Lost !")

        elif state == kazoo.KazooState.SUSPENDED:
            # Handle being disconnected from Zookeeper
            self._controller = False
            _logger.debug("Suspended !")

        else:
            # Handle being connected/reconnected to Zookeeper
            self._controller = True
            _logger.debug("Connected !")

            _logger.debug("Loading...")
            import threading
            thread = threading.Thread(target=self.load_content)
            thread.daemon = True
            thread.start()

