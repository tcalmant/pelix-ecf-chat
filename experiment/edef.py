#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Pelix remote services: EDEF file handler

Endpoint Description Extender Format (EDEF) is specified in OSGi Compendium
specifications, section 122.8.

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
import experiment.beans as beans

# Standard library
import threading
import xml.etree.ElementTree as ElementTree

# ------------------------------------------------------------------------------

# EDEF tags
TAG_ENDPOINT_DESCRIPTIONS = "endpoint-descriptions"
TAG_ENDPOINT_DESCRIPTION = "endpoint-description"
TAG_PROPERTY = "property"
TAG_ARRAY = "array"
TAG_LIST = "list"
TAG_SET = "set"
TAG_XML = "xml"
TAG_VALUE = "value"

# Property attributes
ATTR_NAME = "name"
ATTR_VALUE_TYPE = "value-type"
ATTR_VALUE = TAG_VALUE

# Value types
TYPE_STRING = "String"
TYPES_BOOLEAN = ("boolean", "Boolean")
TYPES_CHAR = ("char", "Character")
TYPES_FLOAT = ("float", "Float", "double", "Double")
TYPES_INT = ("int", "Integer", "long", "Long", "short", "Short",
             "bytes", "Bytes")

# ------------------------------------------------------------------------------

class EDEFReader(object):
    """
    Reads an EDEF XML data. Inspired from EndpoitnDescriptionParser from ECF
    """
    def __init__(self):
        """
        Sets up members
        """
        # Lock the parser
        self.__lock = threading.Lock()
        self.__parser = None


    def _convert_value(self, vtype, value):
        """
        Converts the given value string according to the given type

        :param vtype: Type of the value
        :param value: String form of the value
        :return: The converted value
        :raise ValueError: Conversion failed
        """
        # Normalize value
        value = value.strip()

        if vtype == TYPE_STRING:
            # Nothing to do
            return value

        elif vtype in TYPES_INT:
            return int(value)

        elif vtype in TYPES_FLOAT:
            return float(value)

        elif vtype in TYPES_BOOLEAN:
            # Compare lower-case value
            return value.lower() not in ("false", "0")

        elif vtype in TYPES_CHAR:
            return value[0]

        # No luck
        raise ValueError("Unknown value type: {0}".format(vtype))


    def _parse_description(self, node):
        """
        Parse an endpoint description node

        :param node: The endpoint description node
        :return: The parsed EndpointDescription bean
        :raise KeyError: Attribute missing
        :raise ValueError: Invalid description
        """
        endpoint = {}
        for prop_node in node.findall(TAG_PROPERTY):
            name, value = self._parse_property(prop_node)
            endpoint[name] = value

        return beans.EndpointDescription(endpoint)


    def _parse_property(self, node):
        """
        Parses a property node

        :param node: The property node
        :return: A (name, value) tuple
        :raise KeyError: Attribute missing
        """
        # Get informations
        name = node.attrib[ATTR_NAME]
        vtype = node.attrib.get(ATTR_VALUE_TYPE, TYPE_STRING)

        # Look for a value as a single child node
        try:
            value_node = next(iter(node))
            value = self._parse_value_node(vtype, value_node)

        except StopIteration:
            # Value is an attribute
            value = self._convert_value(vtype, node.attrib[ATTR_VALUE])

        return name, value


    def _parse_value_node(self, vtype, node):
        """
        Parses a value node

        :param vtype: The value type
        :param node: The value node
        :return: The parsed value
        """
        kind = node.tag
        if kind == TAG_XML:
            # Raw XML value (string)
            xml_root = next(iter(node))
            return ElementTree.tostring(xml_root, encoding=str, method='xml')

        elif kind in (TAG_ARRAY, TAG_LIST):
            # List
            return [self._convert_value(vtype, value_node.text)
                    for value_node in node.find(TAG_VALUE)]

        elif kind == TAG_SET:
            # Set
            return set(self._convert_value(vtype, value_node.text)
                       for value_node in node.find(TAG_VALUE))

        else:
            # Unknown
            raise ValueError("Unknown value tag: {0}".format(kind))


    def parse(self, xml_str):
        """
        Parses an EDEF XML string

        :param xml_str: An XML string
        :return: The list of parsed EndpointDescription
        """
        # Parse the document
        root = ElementTree.fromstring(xml_str)
        if root.tag != TAG_ENDPOINT_DESCRIPTIONS:
            raise ValueError("Not an EDEF XML: {0}".format(root.tag))

        # Parse content
        return [self._parse_description(node)
                for node in root.findall(TAG_ENDPOINT_DESCRIPTION)]

# ------------------------------------------------------------------------------

class EDEFWriter(object):
    pass

# ------------------------------------------------------------------------------

if __name__ == "__main__":
    with open("edef_test.xml", "r") as fp:
        xml_str = fp.read()

    reader = EDEFReader()
    endpoints = reader.parse(xml_str)
    for endpoint in endpoints:
        print("Endpoint:", str(endpoint))
        print("Properties:")
        from pprint import pprint
        pprint(endpoint.get_properties())
