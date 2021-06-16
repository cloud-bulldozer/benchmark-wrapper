#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Holds function for automagically importing all benchmark modules in ``snafu.benchmarks``"""
import os
import pkgutil
import importlib
import logging
from typing import Tuple, List


def load_benchmarks(logger: logging.Logger = None) -> Tuple[List[str], List[str]]:
    """
    Autodetect modules in same directory as source file (``__file__``) and automatically import them.

    When importing a benchmark module, ``ImportError`s are ignored. This allows for auto-detection of
    supported benchmarks, as those which cannot be imported due to missing dependencies will not
    be populated into the registry.

    Returns
    -------
    tuple
        Return a tuple containing two items. The first item is a list of imported modules,
        the second a list of modules that failed to import due to an ImportError.
    """

    if logger is None:
        logger = logging.getLogger("snafu")

    imported, failed = [], []
    # __file__ is full path to this module
    module_name = f".{os.path.basename(__file__).replace('.py', '')}"
    # __name__ is module name with full package hierarchy
    package = __name__.replace(module_name, "")
    module_dir = os.path.dirname(__file__)
    logger.debug(f"Looking for benchmarks in {module_dir}")

    for _, module, _ in pkgutil.iter_modules([module_dir]):
        if not module.startswith("_"):
            logger.debug(f"Trying to import module {module}")
            try:
                # specify relative import using dot notation
                importlib.import_module(f".{module}", package=package)
                imported.append(module)
                logger.debug(f"Successfully imported benchmark: {module}")
            except ImportError as exception:
                logger.warning(f"Unable to import {module} benchmark: {exception}", exc_info=True)
                failed.append(module)

    return imported, failed
