# -*- coding: utf-8 -*-
"""Background smoke tests for UV Layer Manager Pro in Blender 4.1."""

import importlib
import json
import math
import os
import sys
import traceback

import bpy


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
    if bpy.context.preferences.addons.get("uv_layer_manager_pro") is not None:
        return addon
    addon = importlib.reload(addon)
    return addon


ADDON = import_addon()


def test_register_properties():
    reset_scene()
    try:
        ADDON.unregister()
    except Exception:
        pass
    ADDON.register()
    scene = bpy.context.scene
    wm = bpy.context.window_manager
    mat = bpy.data.materials.new("UVLM_RegisterMaterial")
    assert_true(hasattr(bpy.types.Scene, "uv_layout_active"), "Scene.uv_layout_active missing")
    assert_true(hasattr(bpy.types.Scene, "show_unassigned_shortcuts"), "shortcut visibility property missing")
    assert_true(hasattr(bpy.types.Scene, "uvlm_next_swatch_order"), "swatch sequence property missing")
    assert_true(hasattr(bpy.types.Material, "uvlm_id_color"), "Material.uvlm_id_color missing")
    assert_true(hasattr(bpy.types.Material, "uvlm_swatch_order"), "material swatch property missing")
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
    base.diffuse_color = (1.0, 0.0, 0.0, 1.0)
    dup.diffuse_color = (0.0, 0.0, 1.0, 1.0)
    obj.data.materials.append(base)
    obj.data.materials.append(dup)
    for poly in obj.data.polygons:
        poly.material_index = 1
    result = bpy.ops.uv_layer_manager.organize_materials()
    assert_true(result == {"FINISHED"}, f"organize_materials returned {result}")
    assert_true("UVLM_Mat.001" in bpy.data.materials, "independent suffixed material was deleted")
    assert_true(obj.data.materials[0] == dup, "used independent material was replaced")
    assert_true(tuple(dup.diffuse_color) == (0.0, 0.0, 1.0, 1.0), "independent material color changed")
    assert_true(all(poly.material_index == 0 for poly in obj.data.polygons), "polygon material indices not remapped")


def test_material_display_groups():
    reset_scene()
    first = create_cube("UVLM_Group_A")
    second = create_cube("UVLM_Group_B", location=(3, 0, 0))
    base = bpy.data.materials.new("UVLM_Display")
    variant = bpy.data.materials.new("UVLM_Display.001")
    first.data.materials.append(base)
    second.data.materials.append(variant)
    from uv_layer_manager_pro import utils as U

    groups = U.build_material_display_groups([first, second])
    display_group = next(group for group in groups if group["name"] == "UVLM_Display")
    assert_true(len(display_group["members"]) == 2, "name-family materials were not grouped for display")
    assert_true(display_group["object_count"] == 2, "display-group object count mismatch")
    assert_true(display_group["slot_count"] == 2, "display-group slot count mismatch")


def test_material_swatch_palette():
    reset_scene()
    from uv_layer_manager_pro import constants as C
    from uv_layer_manager_pro import material_id as MID

    external_material = bpy.data.materials.new("UVLM_Swatch_External")
    assert_true(MID.precache_material_icons() == 1.0, "material monitor interval mismatch")
    assert_true(external_material.uvlm_swatch_order >= 0, "external material did not receive a swatch order")

    materials = [bpy.data.materials.new(f"UVLM_Swatch_{index:02d}") for index in range(C.MATERIAL_SWATCH_COUNT + 2)]
    orders = [MID.ensure_material_swatch_order(material) for material in materials]
    colors = [MID.get_material_swatch_color(order) for order in orders]
    assert_true(all(b > a for a, b in zip(orders, orders[1:])), "swatch orders are not monotonic")
    assert_true(len({tuple(round(channel, 6) for channel in color) for color in colors[:C.MATERIAL_SWATCH_COUNT]}) == C.MATERIAL_SWATCH_COUNT, "palette colors are not unique")
    assert_true(colors[C.MATERIAL_SWATCH_COUNT] == colors[0], "palette did not cycle at 50 materials")
    assert_true(colors[C.MATERIAL_SWATCH_COUNT + 1] == colors[1], "palette cycle order mismatch")
    adjacent_distances = [
        math.dist(colors[index][:3], colors[index + 1][:3])
        for index in range(C.MATERIAL_SWATCH_COUNT - 1)
    ]
    assert_true(min(adjacent_distances) > 0.75, "adjacent palette colors are too similar")

    before = {
        material.name: (MID.ensure_material_swatch_order(material), MID.get_material_swatch_color(material.uvlm_swatch_order))
        for material in materials
    }
    removed = materials[10]
    removed_name = removed.name
    remaining_materials = materials[:10] + materials[11:]
    bpy.data.materials.remove(removed)
    for material in remaining_materials:
        order, color = before[material.name]
        assert_true(material.uvlm_swatch_order == order, f"swatch order changed after deleting {removed_name}")
        assert_true(MID.get_material_swatch_color(material.uvlm_swatch_order) == color, "swatch color changed after deletion")

    target = materials[0]
    stable_color = MID.get_material_swatch_color(target.uvlm_swatch_order)
    target.diffuse_color = (0.1, 0.2, 0.3, 1.0)
    target.uvlm_id_color = (0.8, 0.2, 0.1, 1.0)
    target.name = "UVLM_Swatch_Renamed"
    assert_true(MID.get_material_swatch_color(target.uvlm_swatch_order) == stable_color, "swatch color changed after material edits")

    new_material = bpy.data.materials.new("UVLM_Swatch_New")
    new_order = MID.ensure_material_swatch_order(new_material)
    assert_true(new_order > max(orders), "new material did not receive a new persistent order")


def test_material_view_round_trip():
    reset_scene()
    obj = create_cube()
    mat = bpy.data.materials.new("UVLM_ViewState")
    mat.use_nodes = True
    obj.data.materials.append(mat)
    bsdf = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    rgb = mat.node_tree.nodes.new("ShaderNodeRGB")
    mat.node_tree.links.new(rgb.outputs["Color"], bsdf.inputs["Base Color"])
    attr = obj.data.color_attributes.new(name="UVLM_CustomColor", type="BYTE_COLOR", domain="CORNER")
    obj.data.color_attributes.active_color_index = list(obj.data.color_attributes).index(attr)

    result = bpy.ops.uv_layer_manager.toggle_vertex_color_view(mode="COLOR")
    assert_true(result == {"FINISHED"}, f"enter COLOR returned {result}")
    injected = [node for node in mat.node_tree.nodes if node.name.startswith("_UVLM_") and node.type == "VERTEX_COLOR"]
    assert_true(injected and injected[0].layer_name == attr.name, "injected node ignored active color attribute")
    result = bpy.ops.uv_layer_manager.toggle_vertex_color_view(mode="COLOR")
    assert_true(result == {"FINISHED"}, f"leave COLOR returned {result}")
    assert_true(any(link.from_node == rgb for link in bsdf.inputs["Base Color"].links), "original Base Color link was not restored")

    mat.diffuse_color = (0.12, 0.34, 0.56, 1.0)
    bsdf.inputs["Base Color"].default_value = (0.21, 0.43, 0.65, 1.0)
    original_diffuse = tuple(mat.diffuse_color)
    original_base = tuple(bsdf.inputs["Base Color"].default_value)
    bpy.ops.uv_layer_manager.toggle_vertex_color_view(mode="ID")
    from uv_layer_manager_pro import material_id as MID
    MID.clear_id_color_previews()
    assert_true(MID.MaterialIdState.has_original(mat), "preview cleanup discarded ID color snapshot")
    bpy.ops.uv_layer_manager.toggle_vertex_color_view(mode="ID")
    assert_true(close_enough(tuple(mat.diffuse_color), original_diffuse), "diffuse color was not restored after ID mode")
    assert_true(close_enough(tuple(bsdf.inputs["Base Color"].default_value), original_base), "Base Color was not restored after ID mode")


def close_enough(a, b, eps=1e-5):
    return all(abs(float(x) - float(y)) <= eps for x, y in zip(a, b))


def test_vertex_group_snap():
    reset_scene()
    obj = create_cube()
    group = obj.vertex_groups.new(name="UVLM_Group")
    group.add([0, 1], 1.0, "REPLACE")
    from uv_layer_manager_pro import merge_vertices as MV

    eligible = MV.get_eligible_close_snap_vertices(
        obj,
        selected_indices=set(range(len(obj.data.vertices))),
        vertex_group_name=group.name,
    )
    assert_true(eligible == {0, 1}, f"vertex-group filter leaked vertices: {eligible}")
    assert_true(
        MV.get_eligible_close_snap_vertices(obj, vertex_group_name="missing") == set(),
        "missing vertex-group filter should not fall back to unrestricted snapping",
    )
    bpy.context.scene.close_snap_vertex_group = group.name
    bpy.context.scene.close_snap_distance_cm = 0.1
    result = bpy.ops.uv_layer_manager.snap_close_vertices()
    assert_true(result == {"FINISHED"}, f"vertex-group snap returned {result}")


def test_normal_cleanup_data():
    reset_scene()
    obj = create_cube()
    mesh = obj.data
    mesh.normals_split_custom_set([(1.0, 0.0, 0.0)] * len(mesh.loops))
    mesh.calc_tangents()
    mesh.edges[0].use_edge_sharp = True
    assert_true(mesh.has_custom_normals, "custom normal setup failed")
    result = bpy.ops.uv_layer_manager.clean_normals()
    assert_true(result == {"FINISHED"}, f"clean_normals returned {result}")
    assert_true(not mesh.has_custom_normals, "custom split normals were not cleared")
    assert_true(tuple(mesh.loops[0].tangent) == (0.0, 0.0, 0.0), "tangent cache was not released")
    assert_true(mesh.edges[0].use_edge_sharp, "sharp edge was not preserved")


def test_select_max_current_scene():
    reset_scene()
    local_obj = create_cube("UVLM_CurrentScene")
    other_scene = bpy.data.scenes.new("UVLM_OtherScene")
    other_mesh = bpy.data.meshes.new("UVLM_OtherMesh")
    other_mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    other_obj = bpy.data.objects.new("UVLM_OtherObject", other_mesh)
    other_scene.collection.objects.link(other_obj)
    for index in range(3):
        other_mesh.uv_layers.new(name=f"OtherUV{index}")

    result = bpy.ops.uv_layer_manager.select_max()
    assert_true(result == {"FINISHED"}, f"select_max returned {result}")
    assert_true(bpy.context.view_layer.objects.active == local_obj, "select_max escaped the current scene")


def test_modeling_ops():
    reset_scene()
    obj = create_cube()
    obj.data.edges[0].use_edge_sharp = True
    result = bpy.ops.uv_layer_manager.set_normal_angle(preset="60")
    assert_true(result == {"CANCELLED"}, f"removed 60-degree preset returned {result}")
    result = bpy.ops.uv_layer_manager.set_normal_angle(preset="90")
    assert_true(result == {"FINISHED"}, f"set_normal_angle returned {result}")
    assert_true(any("法向" in mod.name or "Smooth" in mod.name for mod in obj.modifiers), "normal angle modifier not added")
    assert_true(obj.data.edges[0].use_edge_sharp, "existing sharp edge was changed")
    result = bpy.ops.uv_layer_manager.set_normal_angle(preset="CUSTOM", angle=47.5)
    assert_true(result == {"FINISHED"}, f"custom normal angle returned {result}")
    assert_true(bpy.context.scene.normal_angle_preset == "CUSTOM", "custom preset was not selected")
    assert_true(abs(bpy.context.scene.normal_angle_custom - 47.5) < 1e-6, "custom angle was not stored")
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
        test_material_display_groups,
        test_material_swatch_palette,
        test_material_view_round_trip,
        test_vertex_group_snap,
        test_normal_cleanup_data,
        test_select_max_current_scene,
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
