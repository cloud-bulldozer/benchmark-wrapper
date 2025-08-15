#!/usr/bin/env python3
"""
Implement a global tool registry that automatically maps tool names to their classes.

This works by having a metaclass (added onto ```wrapper.Wrapper``), add tool classes to into the
registry dict when the class is created.

After snafu loads up and all the classes are created, the registry dict can be accessed at
``registry.TOOLS``. Key names will be tool names, values will be their wrapper classes.
"""
from abc import ABCMeta

TOOLS: dict[str, object] = {}


class ToolRegistryMeta(ABCMeta):
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

    def __new__(mcs, name, bases, namespace, **kwargs):
        """Called when a new class is created."""

        new_class = super().__new__(mcs, name, bases, namespace)
        if namespace.get("tool_name", None) is None:
            raise KeyError("When using ToolRegistryMeta, please set the 'tool_name' class attribute.")
        TOOLS[namespace["tool_name"]] = new_class

        return new_class
