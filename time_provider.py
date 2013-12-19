#!/usr/bin/python3
# -- Content-Encoding: UTF-8 --
"""
Consumer of the time service example in ECF
"""

# Module version
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# -----------------------------------------------------------------------------

# iPOPO decorators
from pelix.ipopo.decorators import ComponentFactory, Provides, Instantiate, \
    Invalidate, Validate, Property
import pelix.remote

# Standard library
import logging
import time

# -----------------------------------------------------------------------------

TIME_SERVICE = 'com.mycorp.examples.timeservice.ITimeService'

_logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------

@ComponentFactory()
@Provides(TIME_SERVICE)
@Property('_export', pelix.remote.PROP_EXPORTED_INTERFACES, [TIME_SERVICE])
@Property('_pkg1', pelix.remote.PROP_ENDPOINT_PACKAGE_VERSION_ + 'com.mycorp.examples.timeservice', '1.0.0')
@Instantiate('time-provider')
class TimeProvider(object):
    """
    Provider of a time service example
    """
    def getCurrentTime(self):
        """
        """
        return int(time.time() * 1000)

    @Validate
    def validate(self, context):
        """
        Component validated
        """
        _logger.warning("Time provider validated")


    @Invalidate
    def invalidate(self, context):
        """
        Component invalidated
        """
        _logger.warning("Time provider invalidated")
