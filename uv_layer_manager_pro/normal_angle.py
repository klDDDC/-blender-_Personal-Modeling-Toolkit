# -*- coding: utf-8 -*-
"""
UV Layer Manager - Normal Angle & Snap Close Vertices
"""
import math
import os

import bpy
from . import constants as C


# ============================================================
# Normal Angle
# ============================================================

def get_normal_angle_degrees(scene):
    preset = scene.normal_angle_preset
    if preset == C.NORMAL_ANGLE_PRESET_CUSTOM:
        return scene.normal_angle_custom
    try:
        return float(preset)
    except (ValueError, TypeError):
        return 180.0


def _set_modifier_angle(mod, angle_rad, angle_deg):
    """鍦ㄦ硶鍚戜慨鏀瑰櫒涓婅缃搴︼紝鑷姩鎺㈡祴姝ｇ‘鐨勫睘鎬у悕鍜屽崟浣嶃€?""
    candidate_attrs = [
        'angle',
        'input_angle',
        'smooth_angle',
        'Input_1',
        'Input_2',
    ]

    for attr in candidate_attrs:
        try:
            cur = getattr(mod, attr, None)
            if cur is not None:
                if cur <= 7.0:
                    setattr(mod, attr, angle_rad)
                else:
                    setattr(mod, attr, angle_deg)
                return True
        except (AttributeError, TypeError):
            continue

    if mod.type == 'NODES' and mod.node_group:
        ng = mod.node_group
        try:
            items = ng.interface.items_tree
        except AttributeError:
            items = getattr(ng, 'inputs', []) or []

        for item in items:
            if getattr(item, 'in_out', None) != 'INPUT':
                continue
            if getattr(item, 'item_type', 'SOCKET') == 'SOCKET' and \
               item.name and 'angle' in item.name.lower():
                try:
                    mod[item.identifier] = angle_rad
                    return True
                except (KeyError, TypeError, AttributeError):
                    continue

        for item in items:
            if getattr(item, 'in_out', None) != 'INPUT':
                continue
            socket_type = getattr(item, 'socket_type', '')
            if socket_type in ('NodeSocketFloat', 'NodeSocketFloatAngle',
                               'NodeSocketFloatFactor'):
                try:
                    mod[item.identifier] = angle_rad
                    return True
                except (KeyError, TypeError, AttributeError):
                    continue

    for key in ('Input_1', 'Input_2', 'Socket_1', 'Socket_2'):
        try:
            mod[key] = angle_rad
            return True
        except (KeyError, TypeError):
            continue

    return False


def _build_smooth_by_angle_node_group(angle_rad):
    """鍔犺浇 Blender 鍐呯疆 Smooth by Angle 鑺傜偣缁勩€?""
    ng = bpy.data.node_groups.get("Smooth by Angle")
    if ng is not None:
        return ng

    blender_dir = os.path.dirname(bpy.app.binary_path)
    version = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
    asset_path = os.path.join(
        blender_dir,
        version,
        "datafiles",
        "assets",
        "geometry_nodes",
        "smooth_by_angle.blend",
    )
    if not os.path.exists(asset_path):
        return None

    try:
        with bpy.data.libraries.load(asset_path, link=False) as (data_from, data_to):
            if "Smooth by Angle" not in data_from.node_groups:
                return None
            data_to.node_groups = ["Smooth by Angle"]
    except Exception:
        return None
    return bpy.data.node_groups.get("Smooth by Angle")


def _set_smooth_by_angle_modifier_inputs(mod, angle_rad):
    if mod is None or mod.type != 'NODES' or mod.node_group is None:
        return
    try:
        items = mod.node_group.interface.items_tree
    except AttributeError:
        items = []
    for item in items:
        if getattr(item, "in_out", None) != "INPUT" or getattr(item, "item_type", None) != "SOCKET":
            continue
        name = getattr(item, "name", "")
        identifier = getattr(item, "identifier", "")
        try:
            if name == "Angle":
                mod[identifier] = angle_rad
            elif name == "Ignore Sharpness":
                mod[identifier] = False
        except (KeyError, TypeError, AttributeError):
            continue


def apply_normal_angle_modifier(obj, angle_degrees):
    """瑙ｉ攣鑷畾涔夋硶绾匡紝淇濈暀閿愯竟锛屽苟娣诲姞/鏇存柊 Smooth by Angle 淇敼鍣ㄣ€?""
    mesh = obj.data

    # 瑙ｉ攣鑷畾涔夋硶绾匡紝涓嶄富鍔ㄦ敼宸叉湁閿愯竟銆?    if hasattr(mesh, "has_custom_normals") and mesh.has_custom_normals:
        try:
            mesh.normals_split_custom_set([(0.0, 0.0, 0.0)] * len(mesh.loops))
        except Exception:
            pass

    # 骞虫粦鐫€鑹诧細鍙缃潰涓?smooth锛屼笉鍐欏叆鎴栨竻闄ゅ凡鏈夐攼杈广€?    for poly in mesh.polygons:
        poly.use_smooth = True

    angle_rad = math.radians(angle_degrees)
    mod_name = C.NORMAL_ANGLE_MODIFIER_NAME

    # 绉绘棫
    old_mod = obj.modifiers.get(mod_name)
    if old_mod is not None:
        obj.modifiers.remove(old_mod)

    # 鏃х増鏈吋瀹癸細灏濊瘯鍘熺敓 SMOOTH_BY_ANGLE 淇敼鍣ㄣ€?    try:
        mod = obj.modifiers.new(mod_name, 'SMOOTH_BY_ANGLE')
        if mod is not None:
            _set_modifier_angle(mod, angle_rad, angle_degrees)
            mesh.update()
            return
    except TypeError:
        pass

    # Blender 4.1+锛氫娇鐢ㄥ唴缃?Smooth by Angle 鑺傜偣璧勪骇锛屼笉淇敼宸叉湁閿愯竟銆?    ng = _build_smooth_by_angle_node_group(angle_rad)
    if ng is not None:
        mod = obj.modifiers.new(mod_name, 'NODES')
        mod.node_group = ng
        _set_smooth_by_angle_modifier_inputs(mod, angle_rad)
        mod.show_viewport = True
        mesh.update()
        return

    # 鏈€鍚庝繚搴曪細鍙闈㈠钩婊戯紝涓嶅啓鍏?淇敼閿愯竟銆?    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()



# ============================================================
# Snap close vertices helpers
# ============================================================




# ============================================================
# Property registration
# ============================================================

def register_properties():
    bpy.types.Scene.normal_angle_preset = bpy.props.EnumProperty(
        name="娉曞悜瑙掑害",
        description="娓呯悊閿佸畾娉曞悜鍚庡簲鐢ㄧ殑骞虫粦瑙掑害",
        items=(
            ('180', "180", "榛樿锛氭渶澶х▼搴︽斁鏉炬硶鍚戣搴?),
            ('30', "30", "纭〃闈㈠父鐢ㄩ攼鍒╄搴?),
            ('60', "60", "涓瓑骞虫粦瑙掑害"),
            ('90', "90", "杈冨鏉剧殑纭竟瑙掑害"),
            (C.NORMAL_ANGLE_PRESET_CUSTOM, "鑷畾涔?, "浣跨敤涓嬫柟婊戝潡鎸囧畾瑙掑害"),
        ),
        default='180',
    )
    bpy.types.Scene.normal_angle_custom = bpy.props.FloatProperty(
        name="鑷畾涔夋硶鍚戣搴?,
        description="鑷畾涔夋竻鐞嗗悗鐨勬硶鍚戣搴?,
        default=180.0,
        min=0.0,
        max=180.0,
    )
    bpy.types.Scene.uvlm_select_angle_threshold = bpy.props.FloatProperty(
        name="瑙掑害閫夋嫨闃堝€?,
        description="瑙掑害閫夋嫨鍔熻兘鐨勯潰娉曞悜瑙掑害闃堝€硷紙搴︼級",
        default=30.0,
        min=0.0,
        max=180.0,
        step=1.0,
    )


def unregister_properties():
    if hasattr(bpy.types.Scene, 'normal_angle_preset'):
        del bpy.types.Scene.normal_angle_preset
    if hasattr(bpy.types.Scene, 'normal_angle_custom'):
        del bpy.types.Scene.normal_angle_custom
    if hasattr(bpy.types.Scene, 'uvlm_select_angle_threshold'):
        del bpy.types.Scene.uvlm_select_angle_threshold