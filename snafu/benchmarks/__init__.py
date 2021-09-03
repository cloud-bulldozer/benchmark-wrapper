#!/usr/bin/env python3
"""snafu benchmark wrappers."""
# -*- coding: utf-8 -*-
# flake8: noqa
# pylint: disable=W0611
from snafu.benchmarks._benchmark import Benchmark, BenchmarkResult
from snafu.benchmarks._load_benchmarks import load_benchmarks

DETECTED_BENCHMARKS = load_benchmarks()
