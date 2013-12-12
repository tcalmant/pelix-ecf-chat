#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Pelix remote services: EDEF file discovery

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

# Local
import experiment.edef as edef

# Remote services
import pelix.remote
import pelix.remote.beans as beans
import pelix.services

# iPOPO decorators
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Invalidate, Validate, Property

# Standard library
import logging
import os

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

@ComponentFactory("experiment-discovery-file")
@Provides(pelix.services.SERVICE_FILEINSTALL_LISTENERS)
@Property('_watched_folder', pelix.services.PROP_FILEINSTALL_FOLDER)
@Requires("_registry", pelix.remote.SERVICE_REGISTRY)
class FileDiscovery(object):
    """
    Discovery using EDEF files and FileInstall
    """
    def __init__(self):
        """
        Sets up members
        """
        # Import registry
        self._registry = None

        # File name -> end point
        self._endpoints = {}

        # EDEF Parser
        self._parser = None


    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        self._parser = edef.EDEFReader()


    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        self._parser = None
        self._endpoints.clear()


    def __filter_names(self, folder, names):
        """
        Generator that returns a tuple (name, full_path) of all files ending
        with .xml

        :param folder: Parent folder
        :param names: List of file names
        """
        for name in names:
            if name.endswith('.xml'):
                yield name, os.path.join(folder, name)


    def _load_endpoint(self, path):
        """
        Loads the EDEF file at the given path

        :param path: Path to the EDEF file
        :return: The loaded endpoint file
        :raise ValueError: Invalid EDEF file
        :raise IOError: Error reading file
        """
        # Read the file content
        with open(path, 'r') as filep:
            xml_content = filep.read()

        # Parse the end point
        edef_endpoint = self._parser.parse(xml_content)

        # Convert it to the Pelix format
        import_endpoint = beans.to_import(edef_endpoint)

        return import_endpoint


    def folder_change(self, folder, added, updated, deleted):
        """
        The configuration folder has been modified

        :param folder: Modified folder
        :param added: List of added files
        :param updated: List of modified files
        :param deleted: List of deleted files
        """
        for name, path in self.__filter_names(folder, added):
            try:
                # Add new endpoint
                endpoint = self._load_endpoint(path)
                self._registry.add(endpoint)
                self._endpoints[name] = endpoint

            except (IOError, ValueError):
                # Not an EDEF file
                pass

        for name, path in self.__filter_names(folder, updated):
            # TODO: Update end point
            pass

        for name, _ in self.__filter_names(folder, deleted):
            try:
                # Remove endpoints
                endpoint = self._endpoints.pop(name)
                self._registry.remove(endpoint)

            except KeyError:
                # Wasn't an EDEF file
                pass

