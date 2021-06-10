#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implement a global tool registry that automatically maps tool names to their classes.

This works by having a metaclass (added onto ```wrapper.Wrapper``), add tool classes to into the
registry dict when the class is created. For more information on metaclasses, see:
https://www.geeksforgeeks.org/python-metaclasses/.

After snafu loads up and all the classes are created, the registry dict can be accessed at
``registry.TOOLS``. Key names will be tool names, values will be their wrapper classes.
"""
from typing import Dict


TOOLS: Dict[str, object] = dict()


class ToolRegistryMeta(type):
    """
    Metaclass which automatically populates ``registry.REGISTRY`` with a ``cls.tool_name: cls`` mapping.

    Note that any class which uses this metaclass *must* have the ``tool_name`` class attribute. This must
    be a class attribute rather than an instance attribute, due to how the tool_name shouldn't change
    depending on the instance- it should be global to all instances of the class.

    Examples
    --------
    >>> import snafu.registry
    >>> class Example(metaclass=snafu.registry.ToolRegistryMeta):
    ...     tool_name = "my_awesome_tool"
    ...
    >>> snafu.registry.TOOLS["my_awesome_tool"]().tool_name
    'my_awesome_tool'
    """

    def __new__(cls, clsname, superclasses, attributedict):
        """Called when a new class is created."""

        new_class = super().__new__(cls, clsname, superclasses, attributedict)
        TOOLS[attributedict["tool_name"]] = new_class

        return new_class
