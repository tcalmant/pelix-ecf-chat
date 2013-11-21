#!/usr/bin/python3
# -- Content-Encoding: UTF-8 --
"""
Chat entry point
"""

# Module version
__version_info__ = (0, 1, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# -----------------------------------------------------------------------------

# Local
import chat.constants

# Pelix
from pelix.ipopo.constants import use_ipopo
import pelix.framework

# Standard library
import argparse
import sys

# -----------------------------------------------------------------------------

def start_server(context):
    """
    Starts the server component
    """
    # Just start the server bundle
    context.install_bundle('chat.server').start()


def start_client(context, name):
    """
    Starts a client with the given name
    """
    # Start the client bundle
    context.install_bundle('chat.client').start()

    # Instantiate the client component
    with use_ipopo(context) as ipopo:
        ipopo.instantiate(chat.constants.FACTORY_CLIENT, "chat-client",
                          {chat.constants.PROP_CLIENT_HANDLE: name})


def start_remote_services(context):
    """
    Starts remote services components
    """
    # Start bundles
    for bundle in ("pelix.http.basic",
                   "pelix.remote.dispatcher",
                   "pelix.remote.registry",
                   "pelix.remote.json_rpc",
                   "pelix.remote.discovery.multicast",
                   "experiment.mdnssd"):
        context.install_bundle(bundle).start()

    # Instantiate components
    with use_ipopo(context) as ipopo:
        # ... HTTP Service on a random port
        ipopo.instantiate("pelix.http.service.basic.factory",
                          "pelix.http.service.basic",
                          {"pelix.http.port": 0})

        # ... dispatcher servlet
        ipopo.instantiate("pelix-remote-dispatcher-servlet-factory",
                          "pelix-remote-dispatcher-servlet", {})

        # ... multicast discovery
        ipopo.instantiate("pelix-remote-discovery-multicast-factory",
                          "pelix-remote-discovery-multicast", {})

        # ... mDNS discovery
        ipopo.instantiate("experiment-zeroconf-discovery-factory",
                          "experiment-zeroconf-discovery", {})

        # ... JSON-RPC exporter and importer
        ipopo.instantiate("pelix-jsonrpc-exporter-factory",
                          "pelix-jsonrpc-exporter", {})
        ipopo.instantiate("pelix-jsonrpc-importer-factory",
                          "pelix-jsonrpc-importer", {})

# -----------------------------------------------------------------------------

def main(args):
    """
    Entry point
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
                             description="Remote Services demonstration: Chat")
    parser.add_argument("--server", action="store_true", dest="server",
                        help="Run in server mode")
    parser.add_argument("--name", action="store", dest="name",
                        help="Set the client name")
    args = parser.parse_args(args)

    # Start the framework
    framework = pelix.framework.create_framework(("pelix.ipopo.core",
                                                  "pelix.shell.core",
                                                  "pelix.shell.ipopo",
                                                  "pelix.shell.console",
                                                  "chat.constants"))
    framework.start()
    context = framework.get_bundle_context()

    # Start remote services
    start_remote_services(context)

    # Start the server
    if args.server:
        start_server(context)

    else:
        # Start the client
        start_client(context, args.name)

    # Wait for the framework to stop
    framework.wait_for_stop()


if __name__ == "__main__":
    # Script call
    import logging
    logging.basicConfig(level=logging.INFO)

    main(sys.argv[1:])
