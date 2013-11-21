#!/usr/bin/python3
# -- Content-Encoding: UTF-8 --
"""
Server bundle
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
    Instantiate, BindField, UnbindField, Validate, Invalidate, Property

# Pelix
import pelix.remote
import pelix.threadpool

# Standard library
import bisect
import threading
import time

# ------------------------------------------------------------------------------

@ComponentFactory()
@Requires('_listeners', chat.constants.SPEC_CHAT_LISTENER,
          aggregate=True, optional=True)
@Provides(chat.constants.SPEC_CHAT_SERVER)
@Property('_export', pelix.remote.PROP_EXPORTED_INTERFACES, '*')
@Instantiate('chat-server')
class ChatServer(object):
    """
    Implementation of the chat server
    """
    def __init__(self):
        """
        Sets up members
        """
        # Chat listeners (injected)
        self._listeners = []

        # Export property
        self._export = None

        # Messages: time -> messages
        self.__messages = {}

        # Time stamps (speeds up look up)
        self.__times = []

        # Notification thread
        self.__pool = pelix.threadpool.ThreadPool(1, logname="ChatServer")

        # Add some locking
        self.__lock = threading.Lock()

        # Validation flag
        self.__validated = False


    def getMessages(self, time):
        """
        Gets messages received after the given time
        """
        with self.__lock:
            # Get left index, to retrieve strict equality times
            base_idx = bisect.bisect_left(self.__times, time)
            return [message
                    for message in self.__messages[time]
                    for time in self.__times[base_idx:]]


    def getHandles(self):
        """
        Returns the handle (string) of each listener
        """
        if self._listeners:
            return [listener.getHandle() for listener in self._listeners]

        else:
            return []


    def post(self, message):
        """
        Posts a message to the listeners
        """
        with self.__lock:
            # Store the message
            timestamp = time.time()
            try:
                # Already got a message at the exact same time
                self.__messages[timestamp].append(message)

            except KeyError:
                # New message
                bisect.insort_right(self.__times, timestamp)
                self.__messages[timestamp] = [message]

            # Notify listeners
            if self._listeners:
                self.__pool.enqueue(self.__notify_message,
                                    self._listeners[:], timestamp)


    def __notify_message(self, listeners, timestamp):
        """
        Notifies the given listeners that a message has been received
        """
        for listener in listeners:
            try:
                listener.messageReceived(timestamp)

            except Exception as ex:
                print("Something went wrong: ", ex)


    def __notify_handle(self, listeners):
        """
        Notifies the given listeners that a new one appeared
        """
        timestamp = time.time()
        for listener in listeners:
            try:
                listener.handleReceived(timestamp)

            except Exception as ex:
                print("Something went wrong: ", ex)


    @BindField('_listeners')
    def _bind_listener(self, field, listener, svc_ref):
        """
        A new chat listener has been bound
        """
        if self.__validated and self._listeners:
            self.__pool.enqueue(self.__notify_handle, self._listeners[:])


    @UnbindField('_listeners')
    def _unbind_listener(self, field, listener, svc_ref):
        """
        A chat listener has gone away
        """
        if self.__validated and self._listeners:
            # Avoid to notify the listener that has gone
            listeners = self._listeners[:]

            try:
                listeners.remove(listener)

            except ValueError:
                # Wasn't there...
                pass

            else:
                self.__pool.enqueue(self.__notify_handle, listeners)


    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Start the pool
        self.__pool.start()

        # Component validated
        self.__validated = True


    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        self.__validated = False
        self.__pool.stop()
