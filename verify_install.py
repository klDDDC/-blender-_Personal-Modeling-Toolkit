"""Verify installed addon loads correctly."""
import bpy
bpy.ops.preferences.addon_enable(module="uv_layer_manager_pro")
mod = bpy.context.preferences.addons.get("uv_layer_manager_pro")
print("ADDON LOADED OK" if mod else "ADDON NOT FOUND")
if mod:
    print("Module:", mod.module)
