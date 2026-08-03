# -*- coding: utf-8 -*-
"""验证布局分割后区域识别：新区域作为编辑器、原区域保留为 3D 视图。

用法（需在隔离的 Blender 用户配置下运行，避免加载真实插件）：
blender --background --python test_layout_split_areas.py
"""
import sys
from pathlib import Path

import bpy

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from uv_layer_manager_pro import layout as L

wm = bpy.context.window_manager
if not wm.windows:
    raise SystemExit("后台模式下无窗口，无法测试布局分割")

win = wm.windows[0]
screen = win.screen
areas3d = [a for a in screen.areas if a.type == 'VIEW_3D']
if not areas3d:
    raise SystemExit("找不到 3D 视图区域")

original = areas3d[0]
regions = [r for r in original.regions if r.type == 'WINDOW']
if not regions:
    raise SystemExit("3D 视图区域没有 WINDOW 区域")

previous_pointers = {a.as_pointer() for a in screen.areas}
with bpy.context.temp_override(window=win, area=original, region=regions[0]):
    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.3)

new_areas = [a for a in screen.areas if a.as_pointer() not in previous_pointers]
editor_area, view_area = L.get_fixed_editor_layout_areas_after_split(
    screen, original, previous_pointers)

failures = []


def check(cond, msg):
    print(f"  [{'OK' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


check(len(new_areas) == 1, f"分割后新增 1 个区域 (实际 {len(new_areas)})")
check(
    editor_area is not None and editor_area.as_pointer() == new_areas[-1].as_pointer(),
    "编辑器区域 = 新分割出的区域",
)
check(
    view_area is not None and view_area.as_pointer() == original.as_pointer(),
    "3D 视图区域 = 原区域",
)
check(original.type == 'VIEW_3D', "原区域仍为 VIEW_3D（未被转换）")

print("=" * 50)
if failures:
    raise SystemExit(1)
print("结果: 全部通过 ✓")
