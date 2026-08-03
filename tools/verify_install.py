"""Verify Blender loads the expected add-on from its user add-ons directory."""
import importlib
import json
import os
from pathlib import Path

import bpy


EXPECTED_VERSION = (1, 8, 0)
EXPECTED_ROOT = (
    Path(os.environ["APPDATA"])
    / "Blender Foundation"
    / "Blender"
    / "4.1"
    / "scripts"
    / "addons"
    / "uv_layer_manager_pro"
).resolve()

bpy.ops.preferences.addon_enable(module="uv_layer_manager_pro")
entry = bpy.context.preferences.addons.get("uv_layer_manager_pro")
module = importlib.import_module("uv_layer_manager_pro")
module_path = Path(module.__file__).resolve()
version = tuple(module.bl_info["version"])

result = {
    "enabled": entry is not None,
    "module": entry.module if entry else None,
    "version": version,
    "path": str(module_path),
    "expected_root": str(EXPECTED_ROOT),
}
print("UVLM_INSTALL_VERIFY " + json.dumps(result, ensure_ascii=False))

if entry is None:
    raise SystemExit("installed add-on is not enabled")
if version != EXPECTED_VERSION:
    raise SystemExit(f"expected version {EXPECTED_VERSION}, loaded {version}")
if module_path.parent != EXPECTED_ROOT:
    raise SystemExit(f"loaded unexpected add-on path: {module_path}")
