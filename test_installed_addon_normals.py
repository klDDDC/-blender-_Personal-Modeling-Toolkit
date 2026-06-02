import addon_utils
import bpy
import sys

workspace = r"K:\ai\chajian\chajian01"
sys.path[:] = [path for path in sys.path if workspace not in path]

addon_utils.enable("uv_layer_manager_pro", default_set=False, persistent=False)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
bpy.ops.mesh.primitive_cube_add(size=2)
obj = bpy.context.object
obj.data.edges[0].use_edge_sharp = True

result = bpy.ops.uv_layer_manager.set_normal_angle(preset="60")
print("INSTALLED_NORMAL_RESULT", result)
print("INSTALLED_NORMAL_MODIFIERS", [(mod.name, mod.type, getattr(mod, "node_group", None).name if getattr(mod, "node_group", None) else None) for mod in obj.modifiers])
print("INSTALLED_NORMAL_SHARP_EDGE", obj.data.edges[0].use_edge_sharp)

if result != {"FINISHED"}:
    raise SystemExit(1)
if not obj.modifiers:
    raise SystemExit(2)
if not obj.data.edges[0].use_edge_sharp:
    raise SystemExit(3)
