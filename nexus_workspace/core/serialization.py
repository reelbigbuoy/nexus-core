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
# File: serialization.py
# Description: Provides serialization helpers for structured workspace and application state.
#============================================================================

from typing import Any, Dict


class NexusSerializable:
    """Mixin for widgets and platform components that persist state."""

    STATE_VERSION = 1

    def save_state(self) -> Dict[str, Any]:
        return {}

    def load_state(self, state: Dict[str, Any]):
        return None