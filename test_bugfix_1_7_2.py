# -*- coding: utf-8 -*-
"""验证 v1.7.2 两个补充修复。用法：
blender --background --python test_bugfix_1_7_2.py
"""
import json
import os
import subprocess
import sys
import tempfile
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
from uv_layer_manager_pro import shortcuts as SH
from uv_layer_manager_pro import constants as C

failures = []


def check(cond, msg):
    if cond:
        print(f"  [OK] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        failures.append(msg)


def cleanup_path(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ============================================================
# 确保测试的是仓库源码，而不是已安装副本
# ============================================================
repo_is_source = False
try:
    resolved = Path(addon_mod.__file__).resolve()
    repo_is_source = str(resolved).startswith(str(REPO_ROOT.resolve()))
except Exception:
    pass
print(f"addon 源码: {addon_mod.__file__}")
check(repo_is_source, "addon 源码来自仓库目录")


# ============================================================
# Bug 2: 快捷键保存强制落盘
# ============================================================
print("\n=== Bug 2: 快捷键保存强制落盘 ===")
check(bool(C._addon_keymaps), f"keymap items 已注册 ({len(C._addon_keymaps)} 个)")

prefs = bpy.context.preferences.addons["uv_layer_manager_pro"].preferences
original_overrides = getattr(prefs, "shortcut_overrides", "")
pref_path = os.path.join(bpy.utils.user_resource("CONFIG"), "userpref.blend")
print(f"  用户偏好文件: {pref_path}")

km, item, label = C._addon_keymaps[0]
item.type = 'A'
item.ctrl = True
bpy.ops.uv_layer_manager.save_shortcuts()

data = json.loads(prefs.shortcut_overrides or "{}")
check(label in data, f"保存后包含槽位 '{label}'")
check(data.get(label, {}).get("type") == "A", "保存的键位为 A")
check(data.get(label, {}).get("ctrl") is True, "保存 ctrl=True")
check(SH._flush_userpref() is True, "save_userpref 调用成功")
check(os.path.exists(pref_path), f"用户偏好文件已写入磁盘 ({pref_path})")

bpy.ops.uv_layer_manager.reset_shortcuts()
reset_data = json.loads(prefs.shortcut_overrides or "{}")
check(not reset_data, "重置后 shortcut_overrides 为空")
check(str(item.type) == "NONE", "重置后 item.type 为 NONE")

# 模拟重启：从 prefs 恢复
prefs.shortcut_overrides = json.dumps({label: {"type": "Q", "value": "PRESS"}})
restored = SH.load_shortcuts_from_prefs()
check(str(item.type) == "Q", f"从 prefs 恢复为 Q (实际 {item.type})")
check(restored >= 1, f"恢复了 {restored} 个已分配快捷键")

# 恢复原偏好值（测试环境配置目录会被丢弃，此处仅保持整洁）
prefs.shortcut_overrides = original_overrides
try:
    bpy.ops.wm.save_userpref()
except Exception:
    pass


# ============================================================
# Bug 1: 清除材质槽清理全部未使用材质（含假用户）
# ============================================================
print("\n=== Bug 1: 清除材质槽清理全部未使用材质（含假用户） ===")

# 用独立 Blender 进程构建外部库文件（同进程内保存再链接会崩溃），再链接 LibOnly
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
try:
    subprocess.run(
        [bpy.app.binary_path, "--background", "--python-expr", helper_code],
        env={**os.environ, "UVLM_LIB_PATH": lib_path},
        check=True,
        capture_output=True,
        text=True,
    )
except subprocess.CalledProcessError as exc:
    print("  [FAIL] 库文件构建失败")
    print(exc.stdout)
    print(exc.stderr)
    failures.append("库文件构建失败")

linked_mat = None
with bpy.data.libraries.load(lib_path, link=True) as (df, dt):
    dt.materials = [name for name in df.materials if name == "LibOnly"]
linked_mat = bpy.data.materials.get("LibOnly")
check(linked_mat is not None and linked_mat.library is not None, "链接库材质已载入")

# 场景材质
mesh = bpy.data.meshes.new("TestMesh")
obj = bpy.data.objects.new("TestObj", mesh)
bpy.context.collection.objects.link(obj)

base_mat = bpy.data.materials.new("Base")     # 清槽前有真实引用
dup_mat = bpy.data.materials.new("Base.001")  # 仅假用户
dup_mat.use_fake_user = True
gold_mat = bpy.data.materials.new("Gold")     # 仅假用户且唯一
gold_mat.use_fake_user = True
mesh.materials.append(base_mat)

mesh2 = bpy.data.meshes.new("KeepMesh")
obj2 = bpy.data.objects.new("KeepObj", mesh2)
bpy.context.collection.objects.link(obj2)
keep_mat = bpy.data.materials.new("Keep")     # 被另一物体引用
mesh2.materials.append(keep_mat)

check(dup_mat.users == 1, f"Base.001 仅假用户 (users={dup_mat.users})")
check(gold_mat.users == 1, f"Gold 仅假用户 (users={gold_mat.users})")

# 先记录名称，操作后材质数据块可能已被删除
base_name, dup_name, gold_name = base_mat.name, dup_mat.name, gold_mat.name
keep_name, linked_name = keep_mat.name, (linked_mat.name if linked_mat else None)

bpy.context.view_layer.objects.active = obj
for o in bpy.context.scene.objects:
    o.select_set(False)
obj.select_set(True)
bpy.ops.uv_layer_manager.clear_material_slots()

remaining = {m.name for m in bpy.data.materials}
check(base_name not in remaining, "清槽后 Base（无真实引用）已删除")
check(dup_name not in remaining, "清槽后 Base.001（假用户）已删除")
check(gold_name not in remaining, "清槽后 Gold（假用户+唯一）已删除")
check(keep_name in remaining, "被其他物体引用的 Keep 保留")
if linked_name is not None:
    check(linked_name in remaining, "链接库材质 LibOnly 被跳过")

cleanup_path(lib_path)


# ============================================================
print("\n" + "=" * 50)
if failures:
    print(f"结果: {len(failures)} 项失败")
    for f in failures:
        print(f"  - {f}")
    raise SystemExit(1)
else:
    print("结果: 全部通过 ✓")
