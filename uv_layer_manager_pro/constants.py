# -*- coding: utf-8 -*-
"""
UV Layer Manager - Constants and Global State
"""
import time


# ============================================================
# Constants
# ============================================================

MAX_UV_LAYERS = 99

UV_BASE_NAME = "UVMap"

LAYOUT_KIND_UV = "UV"
LAYOUT_KIND_SHADER = "SHADER"
EDITOR_SPLIT_FACTOR = 0.3

NORMAL_ANGLE_PRESET_CUSTOM = "CUSTOM"
ID_COLOR_COLUMNS = 9
ID_COLOR_ROWS = 7
ID_COLOR_PRESET_COUNT = ID_COLOR_COLUMNS * ID_COLOR_ROWS
MATERIAL_SWATCH_COUNT = 50
DEFAULT_MATERIAL_ID_COLOR = (0.95, 0.27, 0.27, 1.0)
NORMAL_ANGLE_MODIFIER_NAME = "UVLM 法向角度"

UVLM_NODE_PREFIX = '_UVLM_'

# ============================================================
# Global State
# ============================================================

_operation_lock = False
_last_operation_time = 0
_OPERATION_COOLDOWN = 0.3

_addon_keymaps = []
_duplicate_material_map_cache = None
_duplicate_material_map_version = -1
_draw_cache = {}
_draw_cache_frame = -1
_material_group_expanded = set()
_material_swatch_known_pointers = set()


SHORTCUT_DEFS = (
    ("UV", "uv_layer_manager.toggle_uv_editor", {}),
    ("着色器", "uv_layer_manager.toggle_shader_editor", {}),
    ("法向 180", "uv_layer_manager.set_normal_angle", {"preset": "180"}),
    ("法向 90", "uv_layer_manager.set_normal_angle", {"preset": "90"}),
    ("法向 30", "uv_layer_manager.set_normal_angle", {"preset": "30"}),
    ("法向 自定义", "uv_layer_manager.set_normal_angle", {"preset": NORMAL_ANGLE_PRESET_CUSTOM}),
    ("UV 添加", "uv_layer_manager.add", {}),
    ("UV 删除", "uv_layer_manager.delete", {}),
    ("同步 UV", "uv_layer_manager.sync", {}),
    ("选中最大模型", "uv_layer_manager.select_max", {}),
    ("uv命名重置", "uv_layer_manager.reset_uv_names", {}),
    ("合并相近", "uv_layer_manager.snap_close_vertices", {}),
    ("旋转复制", "uv_layer_manager.rotate_linked_duplicate", {}),
    ("斜向拉直", "uv_layer_manager.straighten_vertices", {}),
    ("新增材质", "uv_layer_manager.add_material", {}),
    ("整理材质", "uv_layer_manager.organize_materials", {}),
    ("材质ID", "uv_layer_manager.toggle_vertex_color_view", {"mode": "ID"}),
    ("顶点颜色", "uv_layer_manager.toggle_vertex_color_view", {"mode": "COLOR"}),
    ("顶点alpha", "uv_layer_manager.toggle_vertex_color_view", {"mode": "ALPHA"}),
)


def check_operation_lock():
    global _operation_lock, _last_operation_time
    if _operation_lock:
        return False
    current_time = time.time()
    if current_time - _last_operation_time < _OPERATION_COOLDOWN:
        return False
    return True


def set_operation_lock():
    global _operation_lock, _last_operation_time
    _operation_lock = True
    _last_operation_time = time.time()


def release_operation_lock():
    global _operation_lock
    _operation_lock = False
