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
from pelix.ipopo.decorators import ComponentFactory, Requires, Instantiate, \
    Invalidate, Validate

# Standard library
import logging

# -----------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------

@ComponentFactory()
@Requires('_time', 'com.mycorp.examples.timeservice.ITimeService')
@Instantiate('time-consumer')
class TimeConsumer(object):
    """
    Consumer of a time service example
    """
    def __init__(self):
        """
        Sets up members
        """
        # Injected time
        self._time = None


    @Validate
    def validate(self, context):
        """
        Component validated
        """
        _logger.warning("Time consumer validated")
        _logger.info("Time according to Java: %s", self._time.getCurrentTime())


    @Invalidate
    def invalidate(self, context):
        """
        Component invalidated
        """
        _logger.warning("Time consumer invalidated")
