"""Enable the installed add-on and run the complete Blender test suite."""
import importlib
import os
from pathlib import Path
import sys

import bpy


EXPECTED_VERSION = (1, 7, 0)
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
addon = importlib.import_module("uv_layer_manager_pro")
addon_path = Path(addon.__file__).resolve()
if addon_path.parent != EXPECTED_ROOT:
    raise SystemExit(f"loaded unexpected add-on path: {addon_path}")
if tuple(addon.bl_info["version"]) != EXPECTED_VERSION:
    raise SystemExit(f"loaded unexpected add-on version: {addon.bl_info['version']}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_uv_layer_manager_pro_blender import main
main()
