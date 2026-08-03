"""验证 v1.7.1 两个 bug 修复。用法：
blender --background --python tests/test_bugfix_1_7_1.py
"""
import bpy

bpy.ops.preferences.addon_enable(module="uv_layer_manager_pro")

import json
import importlib
from uv_layer_manager_pro import shortcuts as SH
from uv_layer_manager_pro import constants as C

failures = []


def check(cond, msg):
    if cond:
        print(f"  [OK] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        failures.append(msg)


# ============================================================
# Bug 1: clear_material_slots 清理孤儿材质
# ============================================================
print("\n=== Bug 1: clear_material_slots 清理孤儿材质 ===")
bpy.ops.wm.read_factory_settings(use_empty=True)

mesh = bpy.data.meshes.new("TestMesh")
obj = bpy.data.objects.new("TestObj", mesh)
bpy.context.collection.objects.link(obj)

base_mat = bpy.data.materials.new("Base")
orphan_mat = bpy.data.materials.new("Base.001")  # 孤儿（users==0）
mesh.materials.append(base_mat)

before_count = len(bpy.data.materials)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.uv_layer_manager.clear_material_slots()
after_count = len(bpy.data.materials)

check(after_count < before_count, f"材质总数减少 {before_count} -> {after_count}")
check(orphan_mat.name not in [m.name for m in bpy.data.materials], "孤儿材质 Base.001 已删除")
check(base_mat.name not in [m.name for m in bpy.data.materials], "清槽后未引用的 Base 也已删除")

# 验证：被其他物体引用的材质不会被误删
mesh2 = bpy.data.meshes.new("KeepMesh")
obj2 = bpy.data.objects.new("KeepObj", mesh2)
bpy.context.collection.objects.link(obj2)
keep_mat = bpy.data.materials.new("Keep")
mesh2.materials.append(keep_mat)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
obj2.select_set(False)
bpy.ops.uv_layer_manager.clear_material_slots()
check(keep_mat.name in [m.name for m in bpy.data.materials], "被其他物体引用的材质未被误删")


# ============================================================
# Bug 2: 快捷键持久化
# ============================================================
print("\n=== Bug 2: 快捷键持久化 ===")
check(bool(C._addon_keymaps), f"keymap items 已注册 ({len(C._addon_keymaps)} 个)")

prefs = bpy.context.preferences.addons["uv_layer_manager_pro"].preferences
check(hasattr(prefs, "shortcut_overrides"), "AddonPreferences 有 shortcut_overrides 属性")

# 初始应为空
check(not prefs.shortcut_overrides, "初始 shortcut_overrides 为空")

# 给第一个 item 分配按键，保存
km, item, label = C._addon_keymaps[0]
item.type = 'A'
item.ctrl = True
saved_count = SH.save_shortcuts_to_prefs()
data = json.loads(prefs.shortcut_overrides or "{}")
check(label in data, f"保存后包含槽位 '{label}'")
check(data.get(label, {}).get("type") == "A", "保存的键位为 A")
check(data.get(label, {}).get("ctrl") is True, "保存 ctrl=True")
print(f"  保存了 {saved_count} 个快捷键")

# 模拟重启：清除 item，再从 prefs 恢复
item.type = 'NONE'
item.ctrl = False
check(str(item.type) == "NONE", "清除后 item.type 为 NONE")
restored = SH.load_shortcuts_from_prefs()
check(str(item.type) == "A", f"恢复后 item.type 回到 A (实际 {item.type})")
check(item.ctrl is True, "恢复后 ctrl=True")
print(f"  恢复了 {restored} 个已分配快捷键")

# 重置
bpy.ops.uv_layer_manager.reset_shortcuts()
check(not prefs.shortcut_overrides, "重置后 shortcut_overrides 清空")
check(str(item.type) == "NONE", "重置后 item.type 为 NONE")

# register 时自动恢复：重新加载验证
prefs.shortcut_overrides = json.dumps({label: {"type": "Q", "value": "PRESS"}})
SH.load_shortcuts_from_prefs()
check(str(item.type) == "Q", f"从 prefs 恢复为 Q (实际 {item.type})")

# ============================================================
print("\n" + "=" * 50)
if failures:
    print(f"结果: {len(failures)} 项失败")
    for f in failures:
        print(f"  - {f}")
    raise SystemExit(1)
else:
    print("结果: 全部通过 ✓")
