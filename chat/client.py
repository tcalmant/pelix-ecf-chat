#!/usr/bin/python3
# -- Content-Encoding: UTF-8 --
"""
Client bundle
"""

# Module version
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# -----------------------------------------------------------------------------

# Local
import chat.constants

# iPOPO Decorators
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Validate, Invalidate, Property

# Remote services
import pelix.remote
import pelix.shell

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

# ------------------------------------------------------------------------------

@ComponentFactory(chat.constants.FACTORY_CLIENT)
@Requires('_server', chat.constants.SPEC_CHAT_SERVER)
@Provides(chat.constants.SPEC_CHAT_LISTENER)
@Provides(pelix.shell.SHELL_COMMAND_SPEC)
@Property('_handle', chat.constants.PROP_CLIENT_HANDLE, 'John Doe')
@Property('_export', pelix.remote.PROP_EXPORTED_INTERFACES,
          [chat.constants.SPEC_CHAT_LISTENER])
class ChatClient(object):
    """
    Basic chat client: publishes a shell command chat.post <message> and
    prints received messages on the standard output
    """
    def __init__(self):
        """
        Sets up members
        """
        # Chat server (injected)
        self._server = None

        # Client name
        self._handle = None

        # Export property
        self._export = None

        # Chat members
        self._participants = set()


    def getHandle(self):
        """
        Returns the handle (ID) of the listener
        """
        return self._handle


    def handleReceived(self, timestamp):
        """
        Notification of a changed handle
        """
        # Get modifications
        handles = set(self._server.getHandles())

        removed = self._participants.difference(handles)
        added = handles.difference(self._participants)

        self._participants.difference_update(removed)
        self._participants.update(added)

        # Removed listeners
        for handle in removed:
            print("{0} is gone".format(handle))

        # Added ones
        for handle in added:
            print('{0} has entered the chat'.format(handle))


    def messageReceived(self, timestamp):
        """
        Notification of a received message
        """
        messages = self._server.getMessages(timestamp)
        for message in messages:
            print("> {0}: {1}".format(message.getHandle(),
                                      message.getMessage()))


    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Get actual handles
        handles = self._server.getHandles()
        self._participants.update(handles)

        for handle in handles:
            print("{0} is here".format(handle))


    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        # Clear handles
        self._participants.clear()


    def get_namespace(self):
        """
        Shell command name space
        """
        return "chat"


    def get_methods(self):
        """
        Shell commands
        """
        return [('post', self.post)]


    def post(self, io_handler, *args):
        """
        Posts a message to the server
        """
        if args:
            self._server.post(Message(' '.join(args), self._handle))

        else:
            io_handler.write_line("Nothing to say ?")
