#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Holds function for automagically importing all benchmark modules in ``snafu.benchmarks``"""
import os
import pkgutil
import importlib
from typing import Tuple, List


def load_benchmarks() -> Tuple[List[str], List[str]]:
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

    imported, failed = [], []
    for _, module, _ in pkgutil.iter_modules([os.path.dirname(__file__)]):
        try:
            importlib.import_module(module, package=__name__)
            imported.append(module)
        except ImportError as e:
            failed.append(module)
            raise e
            pass

    return imported, failed
