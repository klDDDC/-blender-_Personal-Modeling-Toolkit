import addon_utils
import bpy

addon_utils.enable("uv_layer_manager_pro", default_set=False, persistent=False)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
bpy.ops.mesh.primitive_cube_add(size=2)
obj = bpy.context.object
obj.data.edges[0].use_edge_sharp = True

removed_result = bpy.ops.uv_layer_manager.set_normal_angle(preset="60")
result = bpy.ops.uv_layer_manager.set_normal_angle(preset="90")
custom_result = bpy.ops.uv_layer_manager.set_normal_angle(preset="CUSTOM", angle=42.5)
print("INSTALLED_NORMAL_REMOVED_60", removed_result)
print("INSTALLED_NORMAL_RESULT", result)
print("INSTALLED_NORMAL_CUSTOM_RESULT", custom_result)
print("INSTALLED_NORMAL_CUSTOM_VALUE", bpy.context.scene.normal_angle_custom)
print("INSTALLED_NORMAL_MODIFIERS", [(mod.name, mod.type, getattr(mod, "node_group", None).name if getattr(mod, "node_group", None) else None) for mod in obj.modifiers])
print("INSTALLED_NORMAL_SHARP_EDGE", obj.data.edges[0].use_edge_sharp)

if removed_result != {"CANCELLED"}:
    raise SystemExit(1)
if result != {"FINISHED"}:
    raise SystemExit(2)
if custom_result != {"FINISHED"} or abs(bpy.context.scene.normal_angle_custom - 42.5) > 1e-6:
    raise SystemExit(3)
if not obj.modifiers:
    raise SystemExit(4)
if not obj.data.edges[0].use_edge_sharp:
    raise SystemExit(5)
