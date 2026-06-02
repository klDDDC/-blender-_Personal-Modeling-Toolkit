# -*- coding: utf-8 -*-
"""Background smoke tests for UV Layer Manager Pro in Blender 4.1."""

import importlib
import json
import math
import os
import sys
import traceback

import bpy
import bmesh


ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": detail})
    status = "PASS" if ok else "FAIL"
    print(f"UVLM_TEST {status} {name}: {detail}")


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def run_test(name, func):
    try:
        func()
    except Exception as exc:
        record(name, False, f"{exc}\n{traceback.format_exc()}")
    else:
        record(name, True, "ok")


def reset_scene():
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.ops.object.mode_set.poll() else None
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for datablock_collection in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.node_groups,
        bpy.data.images,
    ):
        for datablock in list(datablock_collection):
            if datablock.users == 0:
                datablock_collection.remove(datablock)


def create_cube(name="UVLM_TestCube", location=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=2, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if len(obj.data.uv_layers) == 0:
        obj.data.uv_layers.new(name="UVMap")
    return obj


def import_addon():
    addon = importlib.import_module("uv_layer_manager_pro")
    addon = importlib.reload(addon)
    return addon


ADDON = import_addon()


def test_register_properties():
    reset_scene()
    ADDON.register()
    scene = bpy.context.scene
    wm = bpy.context.window_manager
    mat = bpy.data.materials.new("UVLM_RegisterMaterial")
    assert_true(hasattr(bpy.types.Scene, "uv_layout_active"), "Scene.uv_layout_active missing")
    assert_true(hasattr(bpy.types.Material, "uvlm_id_color"), "Material.uvlm_id_color missing")
    assert_true(hasattr(wm, "uvlm_id_preset_0"), "WindowManager preset missing")
    assert_true(hasattr(mat, "uvlm_id_color"), "material ID color property unavailable")
    assert_true(scene.material_view_mode == "MATERIAL", "default material_view_mode mismatch")


def test_uv_layer_ops():
    reset_scene()
    obj = create_cube()
    start_count = len(obj.data.uv_layers)
    result = bpy.ops.uv_layer_manager.add()
    assert_true(result == {"FINISHED"}, f"add returned {result}")
    assert_true(len(obj.data.uv_layers) == start_count + 1, "UV layer was not added")
    bpy.ops.uv_layer_manager.select(index=0)
    assert_true(obj.data.uv_layers.active_index == 0, "UV select did not set active index")
    result = bpy.ops.uv_layer_manager.copy(index=0)
    assert_true(result == {"FINISHED"}, f"copy returned {result}")
    obj.data.uv_layers.active_index = 1
    result = bpy.ops.uv_layer_manager.sync()
    assert_true(result == {"FINISHED"}, f"sync returned {result}")
    result = bpy.ops.uv_layer_manager.delete()
    assert_true(result == {"FINISHED"}, f"delete returned {result}")
    assert_true(len(obj.data.uv_layers) == start_count, "UV layer was not deleted")


def test_uv_select_max_and_reset_names():
    reset_scene()
    small = create_cube("UVLM_Small")
    large = create_cube("UVLM_Large", location=(3, 0, 0))
    bpy.context.view_layer.objects.active = large
    for _ in range(3):
        bpy.ops.uv_layer_manager.add()
    bpy.ops.object.select_all(action="DESELECT")
    result = bpy.ops.uv_layer_manager.select_max()
    assert_true(result == {"FINISHED"}, f"select_max returned {result}")
    assert_true(bpy.context.object == large, "select_max did not activate object with most UV layers")
    small.select_set(True)
    large.select_set(True)
    bpy.context.view_layer.objects.active = large
    result = bpy.ops.uv_layer_manager.reset_uv_names()
    assert_true(result == {"FINISHED"}, f"reset_uv_names returned {result}")
    assert_true([uv.name for uv in large.data.uv_layers] == ["uvmap1", "uvmap2", "uvmap3"], "UV names not reset")


def test_material_ops():
    reset_scene()
    obj = create_cube()
    result = bpy.ops.uv_layer_manager.add_material()
    assert_true(result == {"FINISHED"}, f"add_material returned {result}")
    assert_true(len(obj.data.materials) == 1, "material not appended")
    mat = obj.data.materials[0]
    bpy.context.scene.material_manager_material = mat
    result = bpy.ops.uv_layer_manager.assign_material()
    assert_true(result == {"FINISHED"}, f"assign_material returned {result}")
    result = bpy.ops.uv_layer_manager.set_material_id_preset(index=0, preset_index=5)
    assert_true(result == {"FINISHED"}, f"set_material_id_preset returned {result}")
    assert_true(not mat.uvlm_id_color_is_custom, "preset should mark color as non-custom")
    result = bpy.ops.uv_layer_manager.toggle_material_id_color(index=0)
    assert_true(result == {"FINISHED"}, f"toggle_material_id_color returned {result}")
    result = bpy.ops.uv_layer_manager.toggle_vertex_color_view(mode="ID")
    assert_true(result == {"FINISHED"}, f"toggle_vertex_color_view ID returned {result}")
    result = bpy.ops.uv_layer_manager.clear_material_slots()
    assert_true(result == {"FINISHED"}, f"clear_material_slots returned {result}")
    assert_true(len(obj.data.materials) == 0, "material slots not cleared")


def test_multi_object_shared_material_remove():
    reset_scene()
    mat = bpy.data.materials.new("UVLM_Shared_Material")
    objects = [create_cube("UVLM_Shared_A"), create_cube("UVLM_Shared_B", location=(3, 0, 0))]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.data.materials.append(mat)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    result = bpy.ops.uv_layer_manager.remove_material_by_name(material_name=mat.name)
    assert_true(result == {"FINISHED"}, f"remove_material_by_name returned {result}")
    assert_true(all(mat.name not in [slot_mat.name for slot_mat in obj.data.materials if slot_mat] for obj in objects), "shared material not removed from all selected objects")


def test_duplicate_material_organize():
    reset_scene()
    obj = create_cube()
    base = bpy.data.materials.new("UVLM_Mat")
    dup = bpy.data.materials.new("UVLM_Mat.001")
    obj.data.materials.append(base)
    obj.data.materials.append(dup)
    for poly in obj.data.polygons:
        poly.material_index = 1
    result = bpy.ops.uv_layer_manager.organize_materials()
    assert_true(result == {"FINISHED"}, f"organize_materials returned {result}")
    assert_true("UVLM_Mat.001" not in bpy.data.materials, "duplicate material was not removed")
    assert_true(all(poly.material_index == 0 for poly in obj.data.polygons), "polygon material indices not remapped")


def test_modeling_ops():
    reset_scene()
    obj = create_cube()
    obj.data.edges[0].use_edge_sharp = True
    result = bpy.ops.uv_layer_manager.set_normal_angle(preset="60")
    assert_true(result == {"FINISHED"}, f"set_normal_angle returned {result}")
    assert_true(any("法向" in mod.name or "Smooth" in mod.name for mod in obj.modifiers), "normal angle modifier not added")
    assert_true(obj.data.edges[0].use_edge_sharp, "existing sharp edge was changed")
    result = bpy.ops.uv_layer_manager.rotate_linked_duplicate(axis="Z", count=2, total_angle=120.0)
    assert_true(result == {"FINISHED"}, f"rotate_linked_duplicate returned {result}")
    linked = [candidate for candidate in bpy.data.objects if candidate.type == "MESH" and candidate.data == obj.data]
    assert_true(len(linked) >= 3, "linked duplicates were not created")


def test_color_attribute_view():
    reset_scene()
    obj = create_cube()
    mat = bpy.data.materials.new("UVLM_ColorMat")
    mat.use_nodes = True
    obj.data.materials.append(mat)
    attr = obj.data.color_attributes.new(name="UVLM_Color", type="BYTE_COLOR", domain="CORNER")
    obj.data.color_attributes.active_color_index = list(obj.data.color_attributes).index(attr)
    result = bpy.ops.uv_layer_manager.toggle_vertex_color_view(mode="COLOR")
    assert_true(result == {"FINISHED"}, f"toggle COLOR returned {result}")
    has_uvlm_node = any(
        node.name.startswith("_UVLM_")
        for node in mat.node_tree.nodes
    )
    assert_true(has_uvlm_node, "vertex color node was not injected")
    result = bpy.ops.uv_layer_manager.toggle_vertex_color_view(mode="COLOR")
    assert_true(result == {"FINISHED"}, f"toggle COLOR restore returned {result}")


def test_ngon_select():
    reset_scene()
    mesh = bpy.data.meshes.new("UVLM_NgonMesh")
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1.5, 0.5, 0), (0.5, 1.2, 0), (-0.5, 0.5, 0)],
        [],
        [(0, 1, 2, 3, 4)],
    )
    mesh.update()
    obj = bpy.data.objects.new("UVLM_Ngon", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    result = bpy.ops.uv_layer_manager.select_ngons()
    assert_true(result == {"FINISHED"}, f"select_ngons returned {result}")


def test_quadify_ngons():
    reset_scene()
    mesh = bpy.data.meshes.new("UVLM_QuadifyNgonMesh")
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1.6, 0.5, 0), (1, 1.1, 0), (0, 1.1, 0), (-0.6, 0.5, 0)],
        [],
        [(0, 1, 2, 3, 4, 5)],
    )
    mesh.update()
    obj = bpy.data.objects.new("UVLM_QuadifyNgon", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    result = bpy.ops.uv_layer_manager.quadify_ngons()
    assert_true(result == {"FINISHED"}, f"quadify_ngons returned {result}")
    assert_true(not any(len(poly.vertices) > 4 for poly in obj.data.polygons), "ngons remain after quadify")
    assert_true(any(len(poly.vertices) == 4 for poly in obj.data.polygons), "no quads created")


def test_select_overlapping_faces():
    reset_scene()
    mesh = bpy.data.meshes.new("UVLM_OverlapMesh")
    verts = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (2, 0, 0), (3, 0, 0), (3, 1, 0), (2, 1, 0)]
    mesh.from_pydata(
        verts,
        [],
        [
            (0, 1, 2, 3),
            (3, 2, 1, 0),
            (4, 5, 6, 7),
        ],
    )
    mesh.update()
    obj = bpy.data.objects.new("UVLM_Overlap", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    result = bpy.ops.uv_layer_manager.select_overlapping_faces()
    assert_true(result == {"FINISHED"}, f"select_overlapping_faces returned {result}")
    bpy.ops.object.mode_set(mode="OBJECT")
    selected = [poly.index for poly in obj.data.polygons if poly.select]
    assert_true(selected == [1], f"expected duplicate face [1], got {selected}")


def main():
    tests = [
        test_register_properties,
        test_uv_layer_ops,
        test_uv_select_max_and_reset_names,
        test_material_ops,
        test_multi_object_shared_material_remove,
        test_duplicate_material_organize,
        test_modeling_ops,
        test_color_attribute_view,
        test_ngon_select,
        test_quadify_ngons,
        test_select_overlapping_faces,
    ]
    for test in tests:
        run_test(test.__name__, test)
    try:
        ADDON.unregister()
    except Exception:
        traceback.print_exc()
    passed = sum(1 for result in RESULTS if result["ok"])
    failed = len(RESULTS) - passed
    print("UVLM_TEST_SUMMARY " + json.dumps({"passed": passed, "failed": failed, "results": RESULTS}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
