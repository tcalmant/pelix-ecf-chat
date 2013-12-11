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

# Experiment
import experiment.rsa

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Provides, Instantiate, \
    Validate, Invalidate, Requires

# Standard library
import logging

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

@ComponentFactory()
@Provides(experiment.rsa.SERVICE_ENDPOINT_LISTENER)
@Requires('_rsadmin', experiment.rsa.SERVICE_RS_ADMIN)
@Instantiate('osgi-remote-topology-manager')
class TopologyManager(object):
    """
    Listens to service and endpoint events to tell the remote service admin
    to export and import services
    """
    def __init__(self):
        """
        Sets up members
        """
        # Remove service Admin
        self._rsadmin = None

        # Imported/Exported registrations: Endpoint UID -> [Registrations]
        self.__imported = {}
        self.__exported = {}


    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        pass


    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        # TODO: unregister all endpoints
        pass


    def endpointAdded(self, endpoint, matched_filter):
        """
        :param endpoint: The Endpoint Description to be published
        :param matched_filter: The filter from the ENDPOINT_LISTENER_SCOPE that
                               matched the endpoint, must not be null.
        """
        # TODO: check import/export events
        if matched_filter is None:
            # TODO: normalize the endpoint description before ?
            # TODO: store the registration
            self._rsadmin.import_service(endpoint)


    def endpointRemoved(self, endpoint, matched_filter):
        """
        :param endpoint: The Endpoint Description that is no longer valid.
        :param matched_filter: The filter from the ENDPOINT_LISTENER_SCOPE that
                               matched the endpoint, must not be null.
        """
        pass
