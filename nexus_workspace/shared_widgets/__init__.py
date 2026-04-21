# ============================================================================
#
#
# Copyright (c) 2026 Reel Big Buoy Company
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Nexus Core
# File: __init__.py
# Description: Package initializer for shared widget modules.
#============================================================================

from importlib import import_module

__all__ = ['PropertyGridWidget']


def __getattr__(name):
    if name != 'PropertyGridWidget':
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module('nexus_workspace.shared_widgets.property_grid')
    value = getattr(module, name)
    globals()[name] = value
    return value