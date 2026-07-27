# -*- coding: utf-8 -*-
"""GUI-context clickable-entry test for UV Layer Manager Pro.

This script is intentionally separate from the addon source. Run it in Blender
with a visible UI so operators that require VIEW_3D/window context can execute.
"""

import importlib
import json
import os
import sys
import traceback

import bpy
import bmesh


ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

RESULTS = []


def log(name, ok, detail=""):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"UVLM_UI_TEST {'PASS' if ok else 'FAIL'} {name}: {detail}")


def run(name, fn):
    try:
        fn()
    except Exception as exc:
        log(name, False, f"{exc}\n{traceback.format_exc()}")
    else:
        log(name, True, "ok")


def assert_ok(condition, message):
    if not condition:
        raise AssertionError(message)


def reset_scene():
    if bpy.ops.object.mode_set.poll():
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def import_addon():
    addon = importlib.import_module("uv_layer_manager_pro")
    return importlib.reload(addon)


def ensure_registered(addon):
    try:
        addon.unregister()
    except Exception:
        pass
    addon.register()


def view3d_override():
    window = bpy.context.window
    screen = window.screen
    for area in screen.areas:
        if area.type == "VIEW_3D":
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            if region:
                return {
                    "window": window,
                    "screen": screen,
                    "area": area,
                    "region": region,
                    "scene": bpy.context.scene,
                }
    raise RuntimeError("No VIEW_3D area found")


def make_cube(name="UVLM_UI_Cube", loc=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")
    return obj


def make_ngon():
    mesh = bpy.data.meshes.new("UVLM_UI_NgonMesh")
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1.5, 0.5, 0), (0.5, 1.2, 0), (-0.5, 0.5, 0)],
        [],
        [(0, 1, 2, 3, 4)],
    )
    mesh.update()
    obj = bpy.data.objects.new("UVLM_UI_Ngon", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    return obj


def call_view3d(op_callable, mode="EXEC_DEFAULT", **kwargs):
    override = view3d_override()
    with bpy.context.temp_override(**override):
        return op_callable(mode, **kwargs)


def test_layout_buttons():
    reset_scene()
    make_cube()
    result = call_view3d(bpy.ops.uv_layer_manager.toggle_uv_editor, "INVOKE_DEFAULT")
    assert_ok(result in ({"FINISHED"}, {"RUNNING_MODAL"}), f"toggle UV returned {result}")
    result = call_view3d(bpy.ops.uv_layer_manager.toggle_shader_editor, "INVOKE_DEFAULT")
    assert_ok(result in ({"FINISHED"}, {"RUNNING_MODAL"}, {"CANCELLED"}), f"toggle shader returned {result}")
    result = call_view3d(bpy.ops.uv_layer_manager.toggle_shader_editor, "INVOKE_DEFAULT")
    assert_ok(result in ({"FINISHED"}, {"RUNNING_MODAL"}, {"CANCELLED"}), f"toggle shader close returned {result}")


def test_uv_list_clicks():
    reset_scene()
    obj = make_cube()
    assert_ok(bpy.ops.uv_layer_manager.add("INVOKE_DEFAULT") == {"FINISHED"}, "add failed")
    assert_ok(bpy.ops.uv_layer_manager.select("INVOKE_DEFAULT", index=0) == {"FINISHED"}, "select failed")
    assert_ok(bpy.ops.uv_layer_manager.copy("INVOKE_DEFAULT", index=0) == {"FINISHED"}, "copy failed")
    obj.data.uv_layers.active_index = 1
    assert_ok(bpy.ops.uv_layer_manager.sync("INVOKE_DEFAULT") == {"FINISHED"}, "sync failed")
    assert_ok(bpy.ops.uv_layer_manager.delete("INVOKE_DEFAULT") == {"FINISHED"}, "delete failed")
    assert_ok(bpy.ops.uv_layer_manager.select_max("INVOKE_DEFAULT") == {"FINISHED"}, "select_max failed")


def test_modeling_clicks_and_dialogs():
    reset_scene()
    obj = make_cube()
    bpy.context.scene.close_snap_distance_cm = 0.1
    assert_ok(bpy.ops.uv_layer_manager.reset_uv_names("INVOKE_DEFAULT") == {"FINISHED"}, "reset_uv_names failed")
    distance_result = bpy.ops.uv_layer_manager.set_close_snap_distance("INVOKE_DEFAULT")
    if bpy.app.background:
        assert_ok(
            bpy.ops.uv_layer_manager.set_close_snap_distance("EXEC_DEFAULT", distance_cm=0.1, vertex_group='__NONE__') == {"FINISHED"},
            "distance settings did not execute",
        )
    else:
        assert_ok(distance_result == {"RUNNING_MODAL"}, "distance dialog did not open")
    assert_ok(bpy.ops.uv_layer_manager.set_close_snap_distance("EXEC_DEFAULT", distance_cm=0.2, vertex_group='__NONE__') == {"FINISHED"}, "distance execute failed")
    assert_ok(bpy.ops.uv_layer_manager.snap_close_vertices("INVOKE_DEFAULT") == {"FINISHED"}, "snap_close_vertices failed")
    assert_ok(bpy.ops.uv_layer_manager.rotate_linked_duplicate("INVOKE_DEFAULT", axis="Z", count=2, total_angle=120) == {"FINISHED"}, "rotate duplicate failed")
    make_ngon()
    assert_ok(bpy.ops.uv_layer_manager.select_ngons("INVOKE_DEFAULT") == {"FINISHED"}, "select_ngons failed")
    bpy.ops.object.mode_set(mode="OBJECT")
    assert_ok(bpy.ops.uv_layer_manager.quadify_ngons("INVOKE_DEFAULT") == {"FINISHED"}, "quadify_ngons failed")
    reset_scene()
    mesh = bpy.data.meshes.new("UVLM_UI_OverlapMesh")
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        [],
        [(0, 1, 2, 3), (3, 2, 1, 0)],
    )
    mesh.update()
    overlap_obj = bpy.data.objects.new("UVLM_UI_Overlap", mesh)
    bpy.context.collection.objects.link(overlap_obj)
    overlap_obj.select_set(True)
    bpy.context.view_layer.objects.active = overlap_obj
    assert_ok(bpy.ops.uv_layer_manager.select_overlapping_faces("INVOKE_DEFAULT") == {"FINISHED"}, "select overlapping faces failed")
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(bpy.context.object.data)
    for face in bm.faces:
        face.select = True
        break
    bmesh.update_edit_mesh(bpy.context.object.data)
    angle_result = bpy.ops.uv_layer_manager.set_select_angle("INVOKE_DEFAULT")
    if bpy.app.background:
        assert_ok(bpy.ops.uv_layer_manager.set_select_angle("EXEC_DEFAULT", angle=45) == {"FINISHED"}, "angle execute failed")
    else:
        assert_ok(angle_result == {"RUNNING_MODAL"}, "angle dialog did not open")
    assert_ok(bpy.ops.uv_layer_manager.select_by_angle("INVOKE_DEFAULT") == {"FINISHED"}, "select_by_angle failed")
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    normal_obj = make_cube("UVLM_UI_Normal")
    normal_obj.select_set(True)
    bpy.context.view_layer.objects.active = normal_obj
    assert_ok(bpy.ops.uv_layer_manager.set_normal_angle("EXEC_DEFAULT", preset="60") == {"CANCELLED"}, "removed 60 preset is still accepted")
    assert_ok(bpy.ops.uv_layer_manager.set_normal_angle("INVOKE_DEFAULT", preset="90") == {"FINISHED"}, "normal angle failed")
    assert_ok(
        bpy.ops.uv_layer_manager.set_normal_angle("EXEC_DEFAULT", preset="CUSTOM", angle=42.5) == {"FINISHED"},
        "custom normal angle failed",
    )
    assert_ok(abs(bpy.context.scene.normal_angle_custom - 42.5) < 1e-6, "custom normal angle was not stored")


def test_material_clicks_and_dialogs():
    reset_scene()
    obj = make_cube()
    assert_ok(bpy.ops.uv_layer_manager.add_material("INVOKE_DEFAULT") == {"FINISHED"}, "add_material failed")
    mat = obj.data.materials[0]
    bpy.context.scene.material_manager_material = mat
    assert_ok(bpy.ops.uv_layer_manager.assign_material("INVOKE_DEFAULT") == {"FINISHED"}, "assign_material failed")
    assert_ok(bpy.ops.uv_layer_manager.select_material_slot("INVOKE_DEFAULT", index=0) == {"FINISHED"}, "select material slot failed")
    assert_ok(bpy.ops.uv_layer_manager.assign_material_slot("INVOKE_DEFAULT", index=0) == {"FINISHED"}, "assign slot failed")
    assert_ok(bpy.ops.uv_layer_manager.edit_material_base_color("INVOKE_DEFAULT") == {"FINISHED"}, "edit base color failed")
    id_dialog_result = bpy.ops.uv_layer_manager.edit_material_id_color("INVOKE_DEFAULT", index=0)
    if not bpy.app.background:
        assert_ok(id_dialog_result == {"RUNNING_MODAL"}, "ID color dialog did not open")
    assert_ok(bpy.ops.uv_layer_manager.set_material_id_preset("INVOKE_DEFAULT", index=0, preset_index=3) == {"FINISHED"}, "ID preset failed")
    assert_ok(bpy.ops.uv_layer_manager.edit_material_id_color("EXEC_DEFAULT", index=0) == {"FINISHED"}, "ID color execute failed")
    assert_ok(bpy.ops.uv_layer_manager.toggle_material_id_color("INVOKE_DEFAULT", index=0) == {"FINISHED"}, "single material ID toggle failed")
    attr = obj.data.color_attributes.new(name="UVLM_UI_Color", type="BYTE_COLOR", domain="CORNER")
    obj.data.color_attributes.active_color_index = list(obj.data.color_attributes).index(attr)
    assert_ok(bpy.ops.uv_layer_manager.toggle_vertex_color_view("INVOKE_DEFAULT", mode="COLOR") == {"FINISHED"}, "vertex color toggle failed")
    assert_ok(bpy.ops.uv_layer_manager.set_color_attribute("INVOKE_DEFAULT", name=attr.name) == {"FINISHED"}, "set color attribute failed")
    assert_ok(bpy.ops.uv_layer_manager.toggle_vertex_color_view("INVOKE_DEFAULT", mode="ALPHA") == {"FINISHED"}, "vertex alpha toggle failed")
    assert_ok(bpy.ops.uv_layer_manager.toggle_vertex_color_view("INVOKE_DEFAULT", mode="ID") == {"FINISHED"}, "material ID view failed")
    assert_ok(bpy.ops.uv_layer_manager.clean_unused_material_slots("INVOKE_DEFAULT") == {"FINISHED"}, "clean unused failed")
    dup = bpy.data.materials.new(f"{mat.name}.001")
    obj.data.materials.append(dup)
    assert_ok(bpy.ops.uv_layer_manager.organize_materials("INVOKE_DEFAULT") == {"FINISHED"}, "organize failed")
    if obj.data.materials:
        assert_ok(bpy.ops.uv_layer_manager.remove_material_slot("INVOKE_DEFAULT", index=0) == {"FINISHED"}, "remove slot failed")
    assert_ok(bpy.ops.uv_layer_manager.clear_material_slots("INVOKE_DEFAULT") == {"FINISHED"}, "clear slots failed")


def test_right_click_menu_and_shortcut_entries():
    import uv_layer_manager_pro.constants as C

    assert_ok(len(C._addon_keymaps) == len(C.SHORTCUT_DEFS), "shortcut entries not registered")
    menu_cls = bpy.types.UV_LAYER_MANAGER_MT_shortcut_menu
    assert_ok(menu_cls.bl_idname == "UV_LAYER_MANAGER_MT_shortcut_menu", "menu class missing")
    assert_ok(hasattr(bpy.types, "UV_LAYER_MANAGER_PT_shortcut_panel"), "shortcut panel missing")
    shortcut_panel = bpy.types.UV_LAYER_MANAGER_PT_shortcut_panel
    assert_ok("DEFAULT_CLOSED" in shortcut_panel.bl_options, "shortcut panel should be closed by default")
    assert_ok(all(label != "法向 60" for label, _operator, _props in C.SHORTCUT_DEFS), "60-degree shortcut still registered")
    for prop_name in (
        "show_layout_section",
        "show_uv_section",
        "show_modeling_section",
        "show_material_section",
        "show_shortcut_section",
    ):
        assert_ok(not hasattr(bpy.types.Scene, prop_name), f"obsolete nested-fold property remains: {prop_name}")
    for class_name in (
        "UV_LAYER_MANAGER_OT_flatten_u",
        "UV_LAYER_MANAGER_OT_flatten_v",
        "UV_LAYER_MANAGER_OT_pin_verts",
        "UV_LAYER_MANAGER_OT_unpin_verts",
    ):
        assert_ok(not hasattr(bpy.types, class_name), f"removed class still registered: {class_name}")


def finish(addon):
    passed = sum(1 for item in RESULTS if item["ok"])
    failed = len(RESULTS) - passed
    print("UVLM_UI_TEST_SUMMARY " + json.dumps({"passed": passed, "failed": failed, "results": RESULTS}, ensure_ascii=False))
    try:
        addon.unregister()
    except Exception:
        traceback.print_exc()
    if failed:
        bpy.ops.wm.quit_blender()
        raise SystemExit(1)
    bpy.ops.wm.quit_blender()


def main():
    addon = import_addon()
    ensure_registered(addon)
    for fn in (
        test_layout_buttons,
        test_uv_list_clicks,
        test_modeling_clicks_and_dialogs,
        test_material_clicks_and_dialogs,
        test_right_click_menu_and_shortcut_entries,
    ):
        run(fn.__name__, fn)
    finish(addon)


if __name__ == "__main__":
    main()
