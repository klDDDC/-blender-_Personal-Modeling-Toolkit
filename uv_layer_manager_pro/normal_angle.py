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
    """在法向修改器上设置角度，自动探测正确的属性名和单位。"""
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
    """加载 Blender 内置 Smooth by Angle 节点组。"""
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
    """解锁自定义法线，保留锐边，并添加/更新 Smooth by Angle 修改器。"""
    mesh = obj.data

    # 解锁自定义法线，不主动改已有锐边。
    if hasattr(mesh, "has_custom_normals") and mesh.has_custom_normals:
        try:
            mesh.normals_split_custom_set([(0.0, 0.0, 0.0)] * len(mesh.loops))
        except Exception:
            pass

    # 平滑着色：只设置面为 smooth，不写入或清除已有锐边。
    for poly in mesh.polygons:
        poly.use_smooth = True

    angle_rad = math.radians(angle_degrees)
    mod_name = C.NORMAL_ANGLE_MODIFIER_NAME

    # 移旧
    old_mod = obj.modifiers.get(mod_name)
    if old_mod is not None:
        obj.modifiers.remove(old_mod)

    # 旧版本兼容：尝试原生 SMOOTH_BY_ANGLE 修改器。
    try:
        mod = obj.modifiers.new(mod_name, 'SMOOTH_BY_ANGLE')
        if mod is not None:
            _set_modifier_angle(mod, angle_rad, angle_degrees)
            mesh.update()
            return
    except TypeError:
        pass

    # Blender 4.1+：使用内置 Smooth by Angle 节点资产，不修改已有锐边。
    ng = _build_smooth_by_angle_node_group(angle_rad)
    if ng is not None:
        mod = obj.modifiers.new(mod_name, 'NODES')
        mod.node_group = ng
        _set_smooth_by_angle_modifier_inputs(mod, angle_rad)
        mod.show_viewport = True
        mesh.update()
        return

    # 最后保底：只设面平滑，不写入/修改锐边。
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()


def _set_sharp_edges_by_angle(mesh, angle_rad):
    """基于面夹角角度，直接设置 mesh.edges 的锐边标志"""
    edge_face_map = {}
    edge_key_to_index = {tuple(sorted(edge.vertices)): edge.index for edge in mesh.edges}
    for poly in mesh.polygons:
        for local_index, _loop_idx in enumerate(poly.loop_indices):
            edge_idx = edge_key_to_index.get(tuple(sorted(poly.edge_keys[local_index])))
            if edge_idx is None:
                continue
            if edge_idx not in edge_face_map:
                edge_face_map[edge_idx] = []
            edge_face_map[edge_idx].append(poly.index)

    for edge_idx, poly_indices in edge_face_map.items():
        if len(poly_indices) != 2:
            continue
        if edge_idx >= len(mesh.edges):
            continue
        n0 = mesh.polygons[poly_indices[0]].normal
        n1 = mesh.polygons[poly_indices[1]].normal
        dot = max(-1.0, min(1.0, n0.dot(n1)))
        angle = math.acos(dot)
        if angle > angle_rad:
            mesh.edges[edge_idx].use_edge_sharp = True


# ============================================================
# Snap close vertices helpers
# ============================================================




# ============================================================
# Property registration
# ============================================================

def register_properties():
    bpy.types.Scene.normal_angle_preset = bpy.props.EnumProperty(
        name="法向角度",
        description="清理锁定法向后应用的平滑角度",
        items=(
            ('180', "180", "默认：最大程度放松法向角度"),
            ('30', "30", "硬表面常用锐利角度"),
            ('60', "60", "中等平滑角度"),
            ('90', "90", "较宽松的硬边角度"),
            (C.NORMAL_ANGLE_PRESET_CUSTOM, "自定义", "使用下方滑块指定角度"),
        ),
        default='180',
    )
    bpy.types.Scene.normal_angle_custom = bpy.props.FloatProperty(
        name="自定义法向角度",
        description="自定义清理后的法向角度",
        default=180.0,
        min=0.0,
        max=180.0,
    )
    bpy.types.Scene.uvlm_select_angle_threshold = bpy.props.FloatProperty(
        name="角度选择阈值",
        description="角度选择功能的面法向角度阈值（度）",
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
