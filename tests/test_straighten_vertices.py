# -*- coding: utf-8 -*-
"""验证「斜向拉直」操作符：选中顶点投影到最远两点连成的直线。用法：
blender --background --python tests/test_straighten_vertices.py
"""
import sys
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    bpy.ops.preferences.addon_enable(module="uv_layer_manager_pro")
except Exception as exc:
    print(f"[WARN] addon_enable 失败: {exc}")
    raise

import uv_layer_manager_pro as addon_mod

failures = []


def check(cond, msg):
    print(f"  [{'OK' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


repo_is_source = False
try:
    resolved = Path(addon_mod.__file__).resolve()
    repo_is_source = str(resolved).startswith(str(REPO_ROOT.resolve()))
except Exception:
    pass
print(f"addon 源码: {addon_mod.__file__}")
check(repo_is_source, "addon 源码来自仓库目录")

# 准备一个 16 顶点圆形，选中右侧弧线顶点 0~4
bpy.context.scene.uvlm_straighten_direction = 'AUTO'
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.mesh.primitive_circle_add(vertices=16, enter_editmode=False, location=(0, 0, 0))
obj = bpy.context.active_object
obj.select_set(True)
assert obj.type == 'MESH'

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
bm = bmesh.from_edit_mesh(obj.data)
selected_indices = (0, 1, 2, 3, 4)
selected = [v for v in bm.verts if v.index in selected_indices]
for v in selected:
    v.select = True
bmesh.update_edit_mesh(obj.data)
before = {v.index: v.co.copy() for v in selected}

# ============================================================
print("\n=== 测试 1: 编辑模式下列表 + 弧形顶点斜向拉直 ===")
check(
    hasattr(bpy.ops.uv_layer_manager, "straighten_vertices"),
    "操作符 uv_layer_manager.straighten_vertices 已注册",
)
result = bpy.ops.uv_layer_manager.straighten_vertices()
check(result == {'FINISHED'}, f"操作符执行成功 ({result})")

after = {v.index: v.co.copy() for v in bm.verts if v.index in selected_indices}
p0, p1 = before[0], before[4]
line = p1 - p0
all_on_line = True
for index in selected_indices:
    cross = (after[index] - p0).cross(line)
    if cross.length > 1e-5:
        all_on_line = False
check(all_on_line, "所有选中顶点已投影到首尾连线 (0→4)")
check(
    (after[0] - before[0]).length < 1e-6 and (after[4] - before[4]).length < 1e-6,
    "端点顶点 0 和 4 保持不动",
)

# ============================================================
print("\n=== 测试 2: 少于 3 个顶点时取消 ===")
bpy.ops.mesh.select_all(action='DESELECT')
for v in bm.verts:
    if v.index in (0, 1):
        v.select = True
bmesh.update_edit_mesh(obj.data)
bpy.context.scene.uvlm_straighten_direction = 'AUTO'
result = bpy.ops.uv_layer_manager.straighten_vertices()
check(result == {'CANCELLED'}, f"2 个顶点时取消执行 ({result})")

# ============================================================
print("\n=== 测试 3: poll 只在网格编辑模式可用 ===")
class_poll = addon_mod.modeling_ops.UV_LAYER_MANAGER_OT_straighten_vertices.poll
check(class_poll(bpy.context), "编辑模式下 poll 为 True")
bpy.ops.object.mode_set(mode='OBJECT')
check(not class_poll(bpy.context), "物体模式下 poll 为 False")

# ============================================================
print("\n=== 测试 4: 面选择模式下不拉直 ===")
bpy.ops.object.mode_set(mode='EDIT')
context = bpy.context
context.tool_settings.mesh_select_mode = (False, False, True)
bpy.ops.mesh.select_all(action='DESELECT')
bm = bmesh.from_edit_mesh(obj.data)
for f in bm.faces:
    if f.index < 4:
        f.select = True
bmesh.update_edit_mesh(obj.data)
before_all = {v.index: v.co.copy() for v in bm.verts}
bpy.context.scene.uvlm_straighten_direction = 'AUTO'
result = bpy.ops.uv_layer_manager.straighten_vertices()
check(result == {'CANCELLED'}, f"面选择时取消执行 ({result})")
after_all = {v.index: v.co.copy() for v in bm.verts}
check(
    all((after_all[i] - before_all[i]).length < 1e-6 for i in before_all),
    "面选择时几何未被修改",
)
context.tool_settings.mesh_select_mode = (True, False, False)

# ============================================================
print("\n=== 测试 5: 边选择模式下拉直边路径 ===")
bpy.ops.mesh.select_all(action='DESELECT')
context.tool_settings.mesh_select_mode = (False, True, False)
bm = bmesh.from_edit_mesh(obj.data)
chain_verts = {0, 1, 2, 3, 4}
for edge in bm.edges:
    if all(v.index in chain_verts for v in edge.verts):
        edge.select = True
bmesh.update_edit_mesh(obj.data)
bpy.context.scene.uvlm_straighten_direction = 'AUTO'
result = bpy.ops.uv_layer_manager.straighten_vertices()
check(result == {'FINISHED'}, f"边路径拉直成功 ({result})")
after_chain = {v.index: v.co.copy() for v in bm.verts if v.index in chain_verts}
p0, p1 = after_chain[0], after_chain[4]
line = p1 - p0
all_on_line = True
for index in chain_verts:
    cross = (after_chain[index] - p0).cross(line)
    if cross.length > 1e-5:
        all_on_line = False
check(all_on_line, "边路径顶点已投影到首尾连线 (0→4)")
check(
    (after_chain[0] - before[0]).length < 1e-6 and (after_chain[4] - before[4]).length < 1e-6,
    "边路径端点保持不动",
)

# ============================================================
print("\n=== 测试 6: X 轴模式 ===")
context = bpy.context
context.tool_settings.mesh_select_mode = (True, False, False)
bpy.ops.mesh.select_all(action='DESELECT')
bm = bmesh.from_edit_mesh(obj.data)
for v in bm.verts:
    if v.index in (0, 1, 2, 3, 4):
        v.select = True
bmesh.update_edit_mesh(obj.data)
context.scene.uvlm_straighten_direction = 'X'
result = bpy.ops.uv_layer_manager.straighten_vertices()
check(result == {'FINISHED'}, f"X 轴拉直成功 ({result})")
pts_x = [v.co.copy() for v in bm.verts if v.index in (0, 1, 2, 3, 4)]
check(
    all(abs(v.y - pts_x[0].y) < 1e-6 and abs(v.z - pts_x[0].z) < 1e-6 for v in pts_x),
    "X 轴模式下所有顶点对齐到过中心的 X 直线",
)

# ============================================================
print("\n=== 测试 7: 自定义角度 45° ===")
bpy.ops.mesh.select_all(action='DESELECT')
bm = bmesh.from_edit_mesh(obj.data)
for v in bm.verts:
    if v.index in (0, 1, 2, 3, 4):
        v.select = True
bmesh.update_edit_mesh(obj.data)
context.scene.uvlm_straighten_direction = 'ANGLE'
context.scene.uvlm_straighten_angle = 45.0
result = bpy.ops.uv_layer_manager.straighten_vertices()
check(result == {'FINISHED'}, f"45° 拉直成功 ({result})")
pts_angle = [v.co.copy() for v in bm.verts if v.index in (0, 1, 2, 3, 4)]
origin = Vector((0.0, 0.0, 0.0))
for p in pts_angle:
    origin += p
origin /= len(pts_angle)
rad = math.radians(45.0)
dirv = Vector((math.cos(rad), math.sin(rad), 0.0))
check(
    all((p - origin).cross(dirv).length < 1e-5 for p in pts_angle),
    "所有顶点位于 45° 直线上",
)

# ============================================================
print("\n=== 测试 8: 沿活动边方向 ===")
context.tool_settings.mesh_select_mode = (False, True, False)
bpy.ops.mesh.select_all(action='DESELECT')
bm = bmesh.from_edit_mesh(obj.data)
edge_chain = []
for edge in bm.edges:
    if all(v.index in chain_verts for v in edge.verts):
        edge.select = True
        edge_chain.append(edge)
if edge_chain:
    bm.select_history.add(edge_chain[0])
bmesh.update_edit_mesh(obj.data)
context.scene.uvlm_straighten_direction = 'EDGE'
result = bpy.ops.uv_layer_manager.straighten_vertices()
check(result == {'FINISHED'}, f"沿活动边拉直成功 ({result})")
pts_edge = {v.index: v.co.copy() for v in bm.verts if v.index in chain_verts}
p0, p1 = pts_edge[0], pts_edge[1]
line = p1 - p0
check(
    all((pts_edge[i] - p0).cross(line).length < 1e-5 for i in chain_verts),
    "所有顶点位于活动边 (0→1) 的直线上",
)

# ============================================================
print("\n=== 测试 9: 设置操作符写入场景属性 ===")
context.scene.uvlm_straighten_direction = 'AUTO'
bpy.ops.uv_layer_manager.set_straighten_direction(direction='Z')
check(context.scene.uvlm_straighten_direction == 'Z', "设置后场景方向为 Z")

print("=" * 50)
if failures:
    print(f"结果: {len(failures)} 项失败")
    for f in failures:
        print(f"  - {f}")
    raise SystemExit(1)
print("结果: 全部通过 ✓")
