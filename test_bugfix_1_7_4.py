# -*- coding: utf-8 -*-
"""验证 v1.7.4 场景级重复槽位合并。用法：
blender --background --python test_bugfix_1_7_4.py
"""
import sys
from pathlib import Path

import bpy

REPO_ROOT = Path(__file__).resolve().parent
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
    if cond:
        print(f"  [OK] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        failures.append(msg)


repo_is_source = False
try:
    resolved = Path(addon_mod.__file__).resolve()
    repo_is_source = str(resolved).startswith(str(REPO_ROOT.resolve()))
except Exception:
    pass
print(f"addon 源码: {addon_mod.__file__}")
check(repo_is_source, "addon 源码来自仓库目录")


def make_dual_slot_mesh(name, mat_a, mat_b):
    """两个槽位、两个面的网格：面0 -> 槽0，面1 -> 槽1。"""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (2, 0, 0), (3, 0, 0), (3, 1, 0), (2, 1, 0)],
        [],
        [(0, 1, 2, 3), (4, 5, 6, 7)],
    )
    mesh.update()
    mesh.materials.append(mat_a)
    mesh.materials.append(mat_b)
    mesh.polygons[0].material_index = 0
    mesh.polygons[1].material_index = 1
    return mesh


def make_object(name, mesh):
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def select_only(obj):
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)


def material_names():
    return {m.name for m in bpy.data.materials}


# ============================================================
# 测试 1: organize_materials 合并未选中物体的重复槽位
# ============================================================
print("\n=== 测试 1: organize_materials 场景级合并重复槽位 ===")
metal = bpy.data.materials.new("Metal")
metal_dup = bpy.data.materials.new("Metal.001")
gold = bpy.data.materials.new("Gold")
gold_dup = bpy.data.materials.new("Gold.001")

mesh1 = make_dual_slot_mesh("Mesh1", metal, metal_dup)
obj1 = make_object("Obj1", mesh1)
mesh2 = make_dual_slot_mesh("Mesh2", gold, gold_dup)
obj2 = make_object("Obj2", mesh2)  # 不选中

select_only(obj1)
bpy.ops.uv_layer_manager.organize_materials()

check(len(mesh1.materials) == 1 and mesh1.materials[0] == metal,
      "Obj1 重复槽位已合并为单个 Metal 槽")
check(mesh1.polygons[0].material_index == 0 and mesh1.polygons[1].material_index == 0,
      "Obj1 两个面已统一指向槽 0")
check("Metal.001" not in material_names(), "Metal.001 已删除")
check(len(mesh2.materials) == 1 and mesh2.materials[0] == gold,
      "未选中 Obj2 的重复槽位已合并为单个 Gold 槽")
check(mesh2.polygons[0].material_index == 0 and mesh2.polygons[1].material_index == 0,
      "Obj2 两个面已统一指向槽 0")
check("Gold.001" not in material_names(), "Gold.001 已删除")


# ============================================================
# 测试 2: clear_material_slots 合并未选中物体的重复槽位
# ============================================================
print("\n=== 测试 2: clear_material_slots 场景级合并重复槽位 ===")
steel = bpy.data.materials.new("Steel")
steel_dup = bpy.data.materials.new("Steel.001")
bronze = bpy.data.materials.new("Bronze")
bronze_dup = bpy.data.materials.new("Bronze.001")

mesh3 = make_dual_slot_mesh("Mesh3", steel, steel_dup)
obj3 = make_object("Obj3", mesh3)
mesh4 = make_dual_slot_mesh("Mesh4", bronze, bronze_dup)
obj4 = make_object("Obj4", mesh4)  # 不选中

select_only(obj3)
bpy.ops.uv_layer_manager.clear_material_slots()

check(len(obj3.data.materials) == 0, "Obj3 材质槽已清空")
check(len(mesh4.materials) == 1 and mesh4.materials[0] == bronze,
      "未选中 Obj4 的重复槽位已合并为单个 Bronze 槽")
check(mesh4.polygons[0].material_index == 0 and mesh4.polygons[1].material_index == 0,
      "Obj4 两个面已统一指向槽 0")
check("Bronze.001" not in material_names(), "Bronze.001 已删除")


# ============================================================
# 测试 3: merge_duplicate_materials 合并重复槽位
# ============================================================
print("\n=== 测试 3: merge_duplicate_materials 合并重复槽位 ===")
copper = bpy.data.materials.new("Copper")
copper_dup = bpy.data.materials.new("Copper.001")
mesh5 = make_dual_slot_mesh("Mesh5", copper, copper_dup)
obj5 = make_object("Obj5", mesh5)

select_only(obj5)
bpy.ops.uv_layer_manager.merge_duplicate_materials()

check(len(mesh5.materials) == 1 and mesh5.materials[0] == copper,
      "Obj5 重复槽位已合并为单个 Copper 槽")
check(mesh5.polygons[0].material_index == 0 and mesh5.polygons[1].material_index == 0,
      "Obj5 两个面已统一指向槽 0")
check("Copper.001" not in material_names(), "Copper.001 已删除")


# ============================================================
print("\n" + "=" * 50)
if failures:
    print(f"结果: {len(failures)} 项失败")
    for f in failures:
        print(f"  - {f}")
    raise SystemExit(1)
else:
    print("结果: 全部通过 ✓")
