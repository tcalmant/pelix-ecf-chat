#!/usr/bin/python3
# -- Content-Encoding: UTF-8 --
"""
Definition of constants
"""

# Module version
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# -----------------------------------------------------------------------------

SPEC_CHAT_SERVER = 'org.eclipse.ecf.example.chat.model.IChatServer'
""" Specification of the chat server """

SPEC_CHAT_LISTENER = 'org.eclipse.ecf.example.chat.model.IChatServerListener'
""" Specification of the chat server listener """

# -----------------------------------------------------------------------------

FACTORY_CLIENT = "chat-client-factory"
""" Name of the component client factory """

PROP_CLIENT_HANDLE = 'chat.handle'
""" Client handle string property """

# ------------------------------------------------------------------------------

class Message(object):
    """
    The message transmitted over network
    """
    def __init__(self, message, handle):
        """
        Sets up members
        """
        self._message = message
        self._handle = handle


    def __str__(self):
        """
        Pretty string
        """
        return "{0} said '{1}'".format(self._handle, self._message)


    def __repr__(self):
        """
        String representation
        """
        return 'Message({0:r}, {1:r})'.format(self._message, self._handle)


    def _serialize(self):
        """
        jsonrpclib custom serialization method
        """
        return [self._message, self._handle], {}


    def getHandle(self):
        """
        The message sender
        """
        return self._handle


    def getMessage(self):
        """
        The message text
        """
        return self._message
