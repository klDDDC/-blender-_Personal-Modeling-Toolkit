# -*- coding: utf-8 -*-
"""
UV Layer Manager - Material ID Color System
"""
import colorsys
import math
import os
import shutil
import struct
import tempfile
import zlib

import bpy
from . import constants as C
from . import utils as U


# ============================================================
# MaterialIdState — 材质 ID 颜色系统全局状态
# ============================================================

class MaterialIdState:
    """封装材质 ID 颜色修改、预览图标、ID 快照等全局状态。"""
    _original_colors = {}          # {mat.as_pointer(): captured_state}
    _preview_collection = None     # bpy.utils.previews 集合
    _preview_dir = ""

    @classmethod
    def save_original(cls, material, state):
        cls._original_colors[material.as_pointer()] = state

    @classmethod
    def has_original(cls, material):
        return material.as_pointer() in cls._original_colors

    @classmethod
    def pop_original(cls, material):
        return cls._original_colors.pop(material.as_pointer(), None)

    @classmethod
    def get_original_keys(cls):
        return list(cls._original_colors.keys())

    @classmethod
    def get_preview_collection(cls):
        return cls._preview_collection

    @classmethod
    def set_preview_collection(cls, col):
        cls._preview_collection = col

    @classmethod
    def get_preview_dir(cls):
        return cls._preview_dir

    @classmethod
    def set_preview_dir(cls, d):
        cls._preview_dir = d

    @classmethod
    def clear_all(cls):
        cls._original_colors.clear()
        if cls._preview_collection is not None:
            import bpy.utils.previews
            bpy.utils.previews.remove(cls._preview_collection)
            cls._preview_collection = None
        if cls._preview_dir:
            shutil.rmtree(cls._preview_dir, ignore_errors=True)
            cls._preview_dir = ""


def get_principled_base_color_inputs(material):
    if material is None or not material.use_nodes or material.node_tree is None:
        return []
    inputs = []
    for node in material.node_tree.nodes:
        if node.type != 'BSDF_PRINCIPLED':
            continue
        base_input = node.inputs.get("Base Color")
        if base_input is not None:
            inputs.append(base_input)
    return inputs


def capture_material_id_state(material):
    state = {
        "diffuse": tuple(material.diffuse_color),
        "base_inputs": [],
    }
    node_tree = material.node_tree if material and material.use_nodes else None
    if node_tree is None:
        return state

    for base_input in get_principled_base_color_inputs(material):
        links = [(link.from_socket, link.to_socket) for link in list(base_input.links)]
        state["base_inputs"].append(
            {
                "input": base_input,
                "default": tuple(base_input.default_value),
                "links": links,
            }
        )
        for link in list(base_input.links):
            node_tree.links.remove(link)
    return state


def restore_material_id_state(material, state):
    if isinstance(state, (tuple, list)):
        material.diffuse_color = tuple(state)
        return

    material.diffuse_color = tuple(state.get("diffuse", material.diffuse_color))
    node_tree = material.node_tree if material and material.use_nodes else None
    if node_tree is None:
        return

    for item in state.get("base_inputs", []):
        base_input = item.get("input")
        if base_input is None:
            continue
        try:
            base_input.default_value = tuple(item.get("default", base_input.default_value))
        except ReferenceError:
            continue

        for from_socket, to_socket in item.get("links", []):
            try:
                if not any(link.from_socket == from_socket and link.to_socket == to_socket for link in node_tree.links):
                    node_tree.links.new(from_socket, to_socket)
            except (ReferenceError, RuntimeError):
                continue


def _srgb_to_linearrgb(rgb):
    """sRGB 转 Linear 空间（Blender 4.0+ 已移除 bpy.utils.srgb_to_linearrgb）"""
    result = []
    for c in rgb:
        if c <= 0.04045:
            result.append(c / 12.92)
        else:
            result.append(pow((c + 0.055) / 1.055, 2.4))
    return tuple(result)


def apply_material_id_color(material, color):
    if not MaterialIdState.has_original(material):
        MaterialIdState.save_original(material, capture_material_id_state(material))
    linear_color = _srgb_to_linearrgb(tuple(color[:3])) + (color[3],)
    material.diffuse_color = linear_color
    for base_input in get_principled_base_color_inputs(material):
        base_input.default_value = linear_color


def prepare_material_id_colors(context):
    materials = []
    seen = set()
    for obj in U.get_selected_mesh_objects(context):
        for material in obj.data.materials:
            if material is None:
                continue
            key = material.as_pointer()
            if key in seen:
                continue
            seen.add(key)
            materials.append(material)

    for index, material in enumerate(materials):
        apply_material_id_color(material, get_material_id_color(material, index))


def get_material_id_color(material, index=0):
    custom_color = getattr(material, "uvlm_id_color", None)
    custom_enabled = bool(getattr(material, "uvlm_id_color_is_custom", False))
    if custom_color and len(custom_color) == 4 and (
        custom_enabled
        or any(abs(custom_color[i] - C.DEFAULT_MATERIAL_ID_COLOR[i]) > 0.001 for i in range(4))
    ):
        return tuple(custom_color)
    hue = (index * 0.61803398875) % 1.0
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.72, 0.95)
    return (red, green, blue, 1.0)


def get_id_color_preset(index):
    row = index // C.ID_COLOR_COLUMNS
    column = index % C.ID_COLOR_COLUMNS

    if column == C.ID_COLOR_COLUMNS - 1:
        gray_values = (0.95, 0.78, 0.62, 0.46, 0.32, 0.18, 0.05)
        gray = gray_values[row % len(gray_values)]
        return (gray, gray, gray, 1.0)

    hues = (
        0.0,      # red
        0.33,     # green
        0.62,     # blue
        0.16,     # yellow
        0.50,     # cyan
        0.90,     # magenta
        0.08,     # orange
        0.78,     # purple
    )
    row_styles = (
        (1.00, 1.00),  # pure, brightest ID colors
        (1.00, 0.84),
        (1.00, 0.68),
        (0.88, 0.56),
        (0.76, 0.44),
        (0.64, 0.32),
        (0.52, 0.22),  # darkest, least saturated
    )
    saturation, value = row_styles[row % len(row_styles)]
    red, green, blue = colorsys.hsv_to_rgb(hues[column], saturation, value)
    return (red, green, blue, 1.0)


def write_solid_png(path, color, size=24):
    red, green, blue, alpha = [max(0, min(255, int(component * 255))) for component in color]
    raw_rows = []
    for _ in range(size):
        raw_rows.append(bytes([0]) + bytes([red, green, blue, alpha]) * size)
    raw = b"".join(raw_rows)

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as handle:
        handle.write(png)


def ensure_id_color_previews():
    pc = MaterialIdState.get_preview_collection()
    if pc is not None:
        return pc

    import bpy.utils.previews

    preview_dir = os.path.join(tempfile.gettempdir(), "uv_layer_manager_id_colors")
    os.makedirs(preview_dir, exist_ok=True)
    MaterialIdState.set_preview_dir(preview_dir)
    MaterialIdState.set_preview_collection(bpy.utils.previews.new())

    for index in range(C.ID_COLOR_PRESET_COUNT):
        color = get_id_color_preset(index)
        red, green, blue, alpha = [max(0, min(255, int(component * 255))) for component in color]
        filepath = os.path.join(MaterialIdState._preview_dir, f"id_color_{index:02d}_{red:02x}{green:02x}{blue:02x}{alpha:02x}.png")
        write_solid_png(filepath, color)
        MaterialIdState._preview_collection.load(f"id_color_{index:02d}", filepath, 'IMAGE')

    return MaterialIdState._preview_collection


def get_color_preview_icon(color, name):
    """返回实色预览图标 ID；预览集合失效时自动重建，最坏情况返回 0 避免崩溃"""
    try:
        preview_collection = ensure_id_color_previews()
        red, green, blue, alpha = [max(0, min(255, int(component * 255))) for component in color]
        key = f"{name}_{red:02x}{green:02x}{blue:02x}{alpha:02x}"
        if key not in preview_collection:
            filepath = os.path.join(MaterialIdState._preview_dir, f"{key}.png")
            write_solid_png(filepath, color)
            preview_collection.load(key, filepath, 'IMAGE')
        return preview_collection[key].icon_id
    except (ReferenceError, KeyError, RuntimeError):
        # Preview collection was invalidated — rebuild and retry once
        clear_id_color_previews()
        try:
            preview_collection = ensure_id_color_previews()
            red, green, blue, alpha = [max(0, min(255, int(component * 255))) for component in color]
            key = f"{name}_{red:02x}{green:02x}{blue:02x}{alpha:02x}"
            filepath = os.path.join(MaterialIdState._preview_dir, f"{key}.png")
            write_solid_png(filepath, color)
            preview_collection.load(key, filepath, 'IMAGE')
            return preview_collection[key].icon_id
        except Exception:
            return 0
    except Exception:
        return 0


def precache_material_icons():
    """预生成所有材质的 ID 颜色图标，避免 UI draw 时逐帧生成 PNG"""
    try:
        for material in bpy.data.materials:
            if material is None:
                continue
            get_color_preview_icon(get_material_id_color(material), f"mat_{material.as_pointer()}")
    except Exception:
        pass


def clear_id_color_previews():
    MaterialIdState.clear_all()


def sync_id_color_preset_props():
    wm = bpy.context.window_manager
    for index in range(C.ID_COLOR_PRESET_COUNT):
        setattr(wm, f"uvlm_id_preset_{index}", get_id_color_preset(index))


def restore_material_id_colors(context=None):
    """恢复材质ID颜色到原始状态。
    传入 context 时只恢复当前选中物体的材质，不碰其他物体。
    不传 context 时（如 unregister）恢复全部。"""
    if context is not None:
        selected = set()
        for obj in U.get_selected_mesh_objects(context):
            for mat_slot in obj.material_slots:
                mat = mat_slot.material
                if mat is not None:
                    selected.add(mat.as_pointer())
        for mat_ptr in MaterialIdState.get_original_keys():
            if mat_ptr in selected:
                for mat in bpy.data.materials:
                    if mat.as_pointer() == mat_ptr:
                        state = MaterialIdState._original_colors.pop(mat_ptr, None)
                        if state is not None:
                            restore_material_id_state(mat, state)
                        break
        return

    for material in bpy.data.materials:
        state = MaterialIdState._original_colors.pop(material.as_pointer(), None)
        if state is not None:
            restore_material_id_state(material, state)


def update_material_id_color(self, context):
    pass


def toggle_single_material_id_color(context, material, index):
    if material is None:
        return
    if MaterialIdState.has_original(material):
        state = MaterialIdState.pop_original(material)
        # Handle both dict (new) and tuple (legacy) state formats
        if isinstance(state, dict):
            material.diffuse_color = state.get('diffuse_color', (0.8, 0.8, 0.8, 1.0))
            if 'node_tree' in state and material.node_tree:
                # Restore node connections if needed
                pass
        elif isinstance(state, (list, tuple)):
            material.diffuse_color = state
        else:
            material.diffuse_color = (0.8, 0.8, 0.8, 1.0)
        return
    color = get_material_id_color(material, index)
    apply_material_id_color(material, color)


# ============================================================
# Property registration
# ============================================================

def register_properties():
    bpy.types.Material.uvlm_id_color = bpy.props.FloatVectorProperty(
        name="材质ID颜色",
        description="材质管理面板使用的ID显示颜色",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=C.DEFAULT_MATERIAL_ID_COLOR,
        update=update_material_id_color,
    )
    bpy.types.Material.uvlm_id_color_is_custom = bpy.props.BoolProperty(
        name="使用自定义材质ID颜色",
        description="这个材质是否使用用户选择的材质ID颜色",
        default=False,
    )
    bpy.types.WindowManager.uvlm_id_edit_color = bpy.props.FloatVectorProperty(
        name="编辑ID颜色",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 0.24, 0.24, 1.0),
    )
    bpy.types.WindowManager.uvlm_id_original_color = bpy.props.FloatVectorProperty(
        name="原始ID颜色",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 0.24, 0.24, 1.0),
    )
    for index in range(C.ID_COLOR_PRESET_COUNT):
        setattr(
            bpy.types.WindowManager,
            f"uvlm_id_preset_{index}",
            bpy.props.FloatVectorProperty(
                name=f"ID预设{index + 1:02d}",
                subtype='COLOR',
                size=4,
                min=0.0,
                max=1.0,
                default=get_id_color_preset(index),
            ),
        )
    sync_id_color_preset_props()


def unregister_properties():
    if hasattr(bpy.types.Material, 'uvlm_id_color'):
        del bpy.types.Material.uvlm_id_color
    if hasattr(bpy.types.Material, 'uvlm_id_color_is_custom'):
        del bpy.types.Material.uvlm_id_color_is_custom
    if hasattr(bpy.types.WindowManager, 'uvlm_id_edit_color'):
        del bpy.types.WindowManager.uvlm_id_edit_color
    if hasattr(bpy.types.WindowManager, 'uvlm_id_original_color'):
        del bpy.types.WindowManager.uvlm_id_original_color
    for index in range(C.ID_COLOR_PRESET_COUNT):
        prop_name = f"uvlm_id_preset_{index}"
        if hasattr(bpy.types.WindowManager, prop_name):
            delattr(bpy.types.WindowManager, prop_name)
