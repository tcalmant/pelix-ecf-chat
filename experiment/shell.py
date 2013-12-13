#!/usr/bin/python3
# -- Content-Encoding: UTF-8 --
"""
Shell commands for ECF compatibility tests
"""

# Module version
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# -----------------------------------------------------------------------------

# Local
import experiment.edef as edef

# Shell constants
from pelix.shell import SHELL_COMMAND_SPEC

# iPOPO Decorators
from pelix.ipopo.decorators import ComponentFactory, Provides, Instantiate, \
    Validate, Invalidate, Requires
import pelix.remote
import pelix.remote.beans as beans

# ------------------------------------------------------------------------------

@ComponentFactory()
@Requires('_dispatcher', pelix.remote.SERVICE_DISPATCHER)
@Provides(SHELL_COMMAND_SPEC)
@Instantiate("experiment-ecf-shell")
class ECFCommands(object):
    """
    ECF shell commands
    """
    def __init__(self):
        """
        Sets up members
        """
        self._reader = None
        self._writer = None
        self._context = None
        self._dispatcher = None


    @Validate
    def validate(self, context):
        """
        Component validated
        """
        self._context = context
        self._reader = edef.EDEFReader()
        self._writer = edef.EDEFWriter()


    @Invalidate
    def invalidate(self, context):
        """
        Component invalidated
        """
        self._reader = None
        self._writer = None
        self._context = None


    def get_namespace(self):
        """
        Shell namespace
        """
        return "ecf"


    def get_methods(self):
        """
        Shells commands
        """
        return [("write", self.write)]


    def write(self, io_handler, service_id, filename=None):
        """
        Writes the EDEF description of the given service
        """
        # Get the service reference
        svc_ref = self._context.get_service_reference(None, "({0}={1})" \
                                .format(pelix.constants.SERVICE_ID, service_id))

        # Find the matching export end points and convert'em to
        # EndpointDescription beans
        endpoints = [beans.from_export(exp_endpoint)
                     for exp_endpoint in self._dispatcher.get_endpoints()
                     if exp_endpoint.reference is svc_ref]

        if not endpoints:
            io_handler.write_line("No matching export endpoint")
            return

        # Write it
        if filename is not None:
            self._writer.write(endpoints, filename)
            io_handler.write_line("{0} endpoints written to {1}",
                                  len(endpoints), filename)

        else:
            xml_str = self._writer.to_string(endpoints)
            io_handler.write_line(xml_str)
