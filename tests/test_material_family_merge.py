# -*- coding: utf-8 -*-
"""验证 1.8.1「清理材质」场景级同名族材质统一。用法：
blender --background --python tests/test_material_family_merge.py
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy

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


def cleanup_path(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


repo_is_source = False
try:
    resolved = Path(addon_mod.__file__).resolve()
    repo_is_source = str(resolved).startswith(str(REPO_ROOT.resolve()))
except Exception:
    pass
print(f"addon 源码: {addon_mod.__file__}")
check(repo_is_source, "addon 源码来自仓库目录")


def make_quad_mesh(name, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update()
    if material is not None:
        mesh.materials.append(material)
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
# 链接库材质（独立进程构建，避免同进程链接崩溃）
# ============================================================
lib_path = os.path.join(tempfile.gettempdir(), "uvlm_test_library.blend")
cleanup_path(lib_path)
helper_code = (
    "import os, bpy\n"
    "lib_path = os.environ.get('UVLM_LIB_PATH')\n"
    "mesh = bpy.data.meshes.new('LibMesh')\n"
    "obj = bpy.data.objects.new('LibObj', mesh)\n"
    "bpy.context.scene.collection.objects.link(obj)\n"
    "mat = bpy.data.materials.new('LibOnly')\n"
    "mesh.materials.append(mat)\n"
    "bpy.ops.wm.save_as_mainfile(filepath=lib_path)\n"
)
subprocess.run(
    [bpy.app.binary_path, "--background", "--python-expr", helper_code],
    env={**os.environ, "UVLM_LIB_PATH": lib_path},
    check=True,
    capture_output=True,
    text=True,
)
with bpy.data.libraries.load(lib_path, link=True) as (df, dt):
    dt.materials = [name for name in df.materials if name == "LibOnly"]
linked_mat = bpy.data.materials.get("LibOnly")
check(linked_mat is not None and linked_mat.library is not None, "链接库材质已载入")

# ============================================================
print("\n=== 清理材质：场景级同名族统一 ===")

# Metal 赋给选中的 Obj1；Metal.001 赋给未选中的 Obj2；Metal.002 仅假用户
metal = bpy.data.materials.new("Metal")
metal_dup1 = bpy.data.materials.new("Metal.001")
metal_dup2 = bpy.data.materials.new("Metal.002")
metal_dup2.use_fake_user = True
gold = bpy.data.materials.new("Gold")

mesh1 = make_quad_mesh("Mesh1", metal)
obj1 = make_object("Obj1", mesh1)
mesh2 = make_quad_mesh("Mesh2", metal_dup1)
obj2 = make_object("Obj2", mesh2)
mesh3 = make_quad_mesh("Mesh3", gold)
obj3 = make_object("Obj3", mesh3)

select_only(obj1)
bpy.ops.uv_layer_manager.organize_materials()

names = material_names()
check("Metal.001" not in names, "已赋给未选中物体的 Metal.001 已删除")
check("Metal.002" not in names, "假用户的 Metal.002 已删除")
check(metal.name in names, "Metal 保留")
check(gold.name in names, "Gold 保留")
check(linked_mat.name in names, "链接库材质 LibOnly 保留")
check(
    len(mesh2.materials) == 1 and mesh2.materials[0] == metal,
    "未选中物体 Obj2 的槽已重定向为 Metal",
)
check(mesh2.polygons[0].material_index == 0, "Obj2 面的 material_index 未改变")

cleanup_path(lib_path)

print("=" * 50)
if failures:
    print(f"结果: {len(failures)} 项失败")
    for f in failures:
        print(f"  - {f}")
    raise SystemExit(1)
print("结果: 全部通过 ✓")
