#!/usr/bin/env python3
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module for finding dependencies of benchmarks, and benchmarks that are
dependent on given files."""
import os

from common import benchmark_utils


def is_subpath_of_benchmark(path, benchmark):
    """Return True if |path| is a subpath of |benchmark|."""
    benchmark_path = os.path.join(benchmark_utils.BENCHMARKS_DIR, benchmark)
    common_path = os.path.commonpath([path, os.path.abspath(benchmark_path)])
    return common_path == benchmark_path


def get_files_dependent_benchmarks(dependency_files):
    """Return the list of benchmarks that are dependent on any file in
    dependency_files."""
    dependent_benchmarks = []
    benchmarks = benchmark_utils.get_all_benchmarks()
    for dependency_file in dependency_files:
        for benchmark in benchmarks:
            if not is_subpath_of_benchmark(dependency_file, benchmark):
                continue
            if not benchmark_utils.is_oss_fuzz(benchmark):
                dependent_benchmarks.append(benchmark)
                break
            # OSS-Fuzz benchmarks only have an oss-fuzz.yaml file as a
            # dependency.
            if os.path.basename(dependency_file) == 'oss-fuzz.yaml':
                dependent_benchmarks.append(benchmark)
                break

    return dependent_benchmarks