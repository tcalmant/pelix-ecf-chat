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
