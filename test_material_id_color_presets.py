# -*- coding: utf-8 -*-
"""Check every Material ID color preset operator in Blender."""

import importlib
import json
import os
import sys
import traceback

import bpy


ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def close_enough(a, b, eps=1e-5):
    return all(abs(float(x) - float(y)) <= eps for x, y in zip(a, b))


def main():
    addon = importlib.import_module("uv_layer_manager_pro")
    addon = importlib.reload(addon)
    try:
        addon.unregister()
    except Exception:
        pass
    addon.register()

    from uv_layer_manager_pro import constants as C

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.mesh.primitive_cube_add(size=2)
    obj = bpy.context.object
    mat = bpy.data.materials.new("UVLM_ID_Color_Test")
    mat.use_nodes = True
    obj.data.materials.append(mat)
    bpy.context.scene.material_manager_material = mat

    failures = []
    unchanged = []
    previous = tuple(mat.uvlm_id_color)

    for index in range(C.ID_COLOR_PRESET_COUNT):
        expected = tuple(getattr(bpy.context.window_manager, f"uvlm_id_preset_{index}"))
        try:
            result = bpy.ops.uv_layer_manager.set_material_id_preset(
                "EXEC_DEFAULT",
                index=0,
                preset_index=index,
            )
            actual = tuple(mat.uvlm_id_color)
            edit_color = tuple(bpy.context.window_manager.uvlm_id_edit_color)
            if result != {"FINISHED"} or not close_enough(actual, expected) or not close_enough(edit_color, expected):
                failures.append(
                    {
                        "index": index,
                        "result": sorted(result),
                        "expected": expected,
                        "actual": actual,
                        "edit_color": edit_color,
                    }
                )
            if index > 0 and close_enough(actual, previous):
                unchanged.append(index)
            previous = actual
        except Exception as exc:
            failures.append({"index": index, "error": str(exc), "traceback": traceback.format_exc()})

    # Invalid index probes: these should ideally cancel, but current operator finishes silently.
    invalid_results = {}
    for invalid_index in (-1, C.ID_COLOR_PRESET_COUNT, C.ID_COLOR_PRESET_COUNT + 10):
        try:
            invalid_results[str(invalid_index)] = sorted(
                bpy.ops.uv_layer_manager.set_material_id_preset(
                    "EXEC_DEFAULT",
                    index=0,
                    preset_index=invalid_index,
                )
            )
        except Exception as exc:
            invalid_results[str(invalid_index)] = str(exc)

    summary = {
        "preset_count": C.ID_COLOR_PRESET_COUNT,
        "columns": C.ID_COLOR_COLUMNS,
        "rows": C.ID_COLOR_ROWS,
        "operator_failures": failures,
        "unchanged_after_previous": unchanged,
        "invalid_preset_results": invalid_results,
    }
    print("UVLM_ID_COLOR_PRESET_SUMMARY " + json.dumps(summary, ensure_ascii=False))

    addon.unregister()
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
