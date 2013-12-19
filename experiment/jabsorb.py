#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
COHORTE Remote Services: Utility methods and classes from JABSORB-RPC

:author: Thomas Calmant
:copyright: Copyright 2013, isandlaTech
:license: Apache License 2.0
:version: 1.0
:status: Beta

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

# Documentation strings format
__docformat__ = "restructuredtext en"

# Module version
__version_info__ = (1, 0, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# ------------------------------------------------------------------------------

# Standard library
import inspect
import re

# ------------------------------------------------------------------------------

JSON_CLASS = '__jsonclass__'
"""
Tuple used by jsonrpclib to indicate wich Python class corresponds to its
content
"""

JAVA_CLASS = "javaClass"
"""
Dictionary key used by Jabsorb to indicate which Java class corresponds to its
content
"""

JAVA_MAPS_PATTERN = re.compile(r"java\.util\.(.*Map|Properties)")
""" Pattern to detect standard Java classes for maps """

JAVA_LISTS_PATTERN = re.compile(r"java\.util\..*List")
""" Pattern to detect standard Java classes for lists """

JAVA_SETS_PATTERN = re.compile(r"java\.util\..*Set")
""" Pattern to detect standard Java classes for sets """

# ------------------------------------------------------------------------------

class __hashabledict(dict):
    """
    Small workaround because dictionaries are not hashable in Python
    """
    def __hash__(self):
        """
        Computes the hash of the dictionary
        """
        return hash(str(sorted(self.items())))


class __hashableset(set):
    """
    Small workaround because sets are not hashable in Python
    """
    def __hash__(self):
        """
        Computes the hash of the set
        """
        return hash(str(sorted(self)))


class __hashablelist(list):
    """
    Small workaround because lists are not hashable in Python
    """
    def __hash__(self):
        """
        Computes the hash of the list
        """
        return hash(str(sorted(self)))

# ------------------------------------------------------------------------------

def _compute_jsonclass(obj):
    """
    Compute the content of the __jsonclass__ field for the given object

    :param obj: An object
    :return: The content of the __jsonclass__ field
    """
    # It's not a standard type, so it needs __jsonclass__
    module_name = inspect.getmodule(obj).__name__
    json_class = obj.__class__.__name__
    if module_name not in ('', '__main__'):
        json_class = '{0}.{1}'.format(module_name, json_class)

    return [json_class, []]


def _is_builtin(obj):
    """
    Checks if the type of the given object is a built-in one or not

    :param obj: An object
    :return: True if the object is of a built-in type
    """
    module = inspect.getmodule(obj)
    if module is None:
        return True

    else:
        return module.__name__ in ('', '__main__')

# ------------------------------------------------------------------------------

def to_jabsorb(value):
    """
    Adds information for Jabsorb, if needed.

    Converts maps and lists to a jabsorb form.
    Keeps tuples as is, to let them be considered as arrays.

    :param value: A Python result to send to Jabsorb
    :return: The result in a Jabsorb map format (not a JSON object)
    """
    # None ?
    if value is None:
        return None

    # Map ?
    elif isinstance(value, dict):

        if JAVA_CLASS in value or JSON_CLASS in value:
            # Bean representation
            converted_result = {}

            for key, content in value.items():
                converted_result[key] = to_jabsorb(content)

            try:
                # Keep the raw jsonrpclib information
                converted_result[JSON_CLASS] = value[JSON_CLASS]
            except KeyError:
                pass

        else:
            # Needs the whole transformation
            converted_result = {JAVA_CLASS: "java.util.HashMap"}
            converted_result["map"] = map_pairs = {}
            for key, content in value.items():
                map_pairs[key] = to_jabsorb(content)

            try:
                # Keep the raw jsonrpclib information
                map_pairs[JSON_CLASS] = value[JSON_CLASS]
            except KeyError:
                pass


    # List ? (consider tuples as an array)
    elif isinstance(value, list):
        converted_result = {JAVA_CLASS: "java.util.ArrayList"}
        converted_result["list"] = [to_jabsorb(entry) for entry in value]

    # Set ?
    elif isinstance(value, (set, frozenset)):
        converted_result = {JAVA_CLASS: "java.util.HashSet"}
        converted_result["set"] = [to_jabsorb(entry) for entry in value]

    # Tuple ? (used as array, except if it is empty)
    elif isinstance(value, tuple):
        converted_result = [to_jabsorb(entry) for entry in value]

    elif hasattr(value, JAVA_CLASS):
        # Class with a Java class hint: convert into a dictionary
        converted_result = __hashabledict((name, to_jabsorb(content))
                                          for name, content
            in map(lambda name: (name, getattr(value, name)), dir(value))
            if not name.startswith('_') and not inspect.ismethod(content))

        # Do not forget the Java class
        converted_result[JAVA_CLASS] = getattr(value, JAVA_CLASS)

        # Also add a __jsonclass__ entry
        converted_result[JSON_CLASS] = _compute_jsonclass(value)

    # Other ?
    else:
        converted_result = value

    return converted_result


def from_jabsorb(request):
    """
    Transforms a jabsorb request into a more Python data model (converts maps
    and lists)

    :param request: Data coming from Jabsorb
    :return: A Python representation of the given data
    """
    if isinstance(request, (list, set, frozenset, tuple)):
        # Special case : JSON arrays (Python lists)
        return [from_jabsorb(element) for element in request]

    elif isinstance(request, dict):
        # Dictionary
        java_class = request.get(JAVA_CLASS)

        if java_class:
            # Java Map ?
            if JAVA_MAPS_PATTERN.match(java_class) is not None:
                return __hashabledict((from_jabsorb(key), from_jabsorb(value))
                                      for key, value in request["map"].items())

            # Java List ?
            elif JAVA_LISTS_PATTERN.match(java_class) is not None:
                return __hashablelist(from_jabsorb(element)
                                      for element in request["list"])

            # Java Set ?
            elif JAVA_SETS_PATTERN.match(java_class) is not None:
                return __hashableset(from_jabsorb(element)
                                     for element in request["set"])

        # Any other case
        return __hashabledict((from_jabsorb(key), from_jabsorb(value))
                              for key, value in request.items())

    elif not _is_builtin(request):
        # Bean
        for attr in dir(request):
            # Only convert public fields
            if not attr[0] == '_':
                # Field conversion
                setattr(request, attr, from_jabsorb(getattr(request, attr)))

        return request

    else:
        # Any other case
        return request
