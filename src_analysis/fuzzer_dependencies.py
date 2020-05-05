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
"""Module for finding dependencies of fuzzers, and fuzzers that are
dependent on given files.
This module assumes that a fuzzer module's imports are done in a sane,
normal way. It will not work on non-toplevel imports.
"""
import importlib
import inspect
import os
import types
from typing import List
import sys

from common import fuzzer_utils

MAX_DEPTH = 10
PY_DEPS_CACHE = {}


def _get_fuzzer_module(fuzzer: str) -> str:
    """Returns the module fuzzer.py module of |fuzzer|."""
    return 'fuzzers.{}.fuzzer'.format(fuzzer)


def is_builtin_module(module) -> bool:
    """Returns True if |module| is a python builtin module."""
    return module.__name__ in sys.builtin_module_names


def is_fuzzers_subpath(path: str) -> bool:
    """Returns True if path is a subpath of the fuzzers/ directory."""
    common_path = os.path.commonpath([path, fuzzer_utils.FUZZERS_DIR])
    return common_path == fuzzer_utils.FUZZERS_DIR


def is_fuzzers_submodule(module) -> bool:
    """Returns True if |module| is a submodule of the fuzzers module."""
    # Builtin modules such as "time" don't have files so attempts to get their
    # files fail.
    if is_builtin_module(module):
        return False

    try:
        module_path = inspect.getfile(module)
        return is_fuzzers_subpath(module_path)
    except TypeError:
        pass
    # This assumes that no __init__ files are used in fuzzers/ and therefore
    # all modules are imported as such: `from fuzzers.afl import fuzzer`.
    return False


def get_fuzzer_dependencies(fuzzer: str) -> List[str]:
    """Return the list of files in fuzzbench that |fuzzer| depends on. This
    includes dockerfiles used to build |fuzzer|, and the Python files it uses to
    build and run fuzz targets."""
    # Don't use modulefinder since it doesn't work without __init__.py files.
    initial_fuzzer = fuzzer
    fuzzer = get_base_fuzzer(fuzzer)
    fuzzer_directory = fuzzer_utils.FuzzerDirectory(fuzzer)
    dependencies = []
    if initial_fuzzer != fuzzer:
        # If fuzzer's base fuzzer is different, fuzzer is a variant, which
        # means changes to variants.yaml can affect it.
        dependencies.append(fuzzer_directory.variants_yaml)
    fuzzer_module = importlib.import_module(_get_fuzzer_module(fuzzer))
    dependencies.extend(_get_python_dependencies(fuzzer_module))
    # The fuzzer is also dependent on dockerfiles.
    dependencies.extend(fuzzer_directory.get_dockerfiles())
    return dependencies


def _get_python_dependencies(module, depth: int = 0) -> List[str]:
    """Returns the python files that |module| is dependent on if module is a
    submodule of fuzzers/. Does not return dependencies that are not submodules
    of fuzzers/, such as std library modules. Has a limit of |MAX_DEPTH| so that
    cyclic imports can easily be detected. Not that this may not work if a
    fuzzer.py imports modules dynamically or within individual functions. That
    is OK because we can prevent this during code review."""
    if depth > MAX_DEPTH:
        # Enforce a depth to catch cyclic imports.
        format_string = ('Depth: {} greater than max: {}. '
                         'Probably a cyclic import in {}.')
        raise Exception(format_string.format(depth, MAX_DEPTH, module))

    module_path = inspect.getfile(module)
    # Just get the dependencies from the cache if we have them.
    if module_path in PY_DEPS_CACHE:
        return PY_DEPS_CACHE[module_path]

    attr_names = dir(module)
    deps = set([module_path])
    for attr_name in attr_names:
        imported_module = getattr(module, attr_name)
        if not isinstance(imported_module, types.ModuleType):
            continue

        if is_fuzzers_submodule(imported_module):
            imported_module_path = inspect.getfile(imported_module)
            deps.add(imported_module_path)
            # Also get the dependencies of the dependency.
            deps = deps.union(
                _get_python_dependencies(imported_module, depth + 1))

    deps = list(deps)
    PY_DEPS_CACHE[module_path] = deps
    return deps


def get_base_fuzzer(fuzzer_name: str) -> str:
    """"Returns the base fuzzer of |fuzzer_name|. For normal fuzzers with
    their own subdirectory in fuzzers/, |fuzzer_name| is returned. For variants,
    it will be the fuzzer that |fuzzer_name| is a variant of."""
    configs = fuzzer_utils.get_fuzzer_configs()
    for config in configs:
        if fuzzer_utils.get_fuzzer_from_config(config) == fuzzer_name:
            return config['fuzzer']
    raise Exception('Base fuzzer for %s not found.' % fuzzer_name)


def get_files_dependent_fuzzers(dependency_files: List[str]) -> List[str]:
    """Returns a list of fuzzers dependent on |dependency_files|."""
    dependent_fuzzers = []
    fuzzer_configs = fuzzer_utils.get_fuzzer_configs()
    for fuzzer_config in fuzzer_configs:
        fuzzer = fuzzer_utils.get_fuzzer_from_config(fuzzer_config)
        fuzzer_dependencies = get_fuzzer_dependencies(fuzzer)
        for dependency in fuzzer_dependencies:
            if dependency in dependency_files:
                dependent_fuzzers.append(fuzzer)
                break

    return dependent_fuzzers
