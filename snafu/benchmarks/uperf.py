#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper for running the uperf benchmark. See http://uperf.org/ for more information."""
from snafu.wrapper import Benchmark


class Uperf(Benchmark):
    """
    Wrapper for the uperf benchmark.
    """

    tool_name = "uperf"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        """Run uperf benchmark."""

    def emit_metrics(self):
        """Emit uperf metrics."""
