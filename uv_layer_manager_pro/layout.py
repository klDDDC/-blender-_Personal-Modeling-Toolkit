# -*- coding: utf-8 -*-
"""
UV Layer Manager - Layout Management
"""
import bpy
from . import constants as C


# ============================================================
# LayoutState — 已管理布局的全局状态
# ============================================================

class LayoutState:
    """封装已管理编辑器布局的全局状态。"""
    _managed_layouts = {}

    @classmethod
    def remember(cls, screen, view_area, editor_area, kind):
        screen_key = screen.as_pointer()
        cls._managed_layouts[screen_key] = {
            "editor_pointer": editor_area.as_pointer(),
            "view_pointer": view_area.as_pointer(),
            "kind": kind,
        }

    @classmethod
    def clear(cls, screen):
        screen_key = screen.as_pointer()
        cls._managed_layouts.pop(screen_key, None)

    @classmethod
    def clear_all(cls):
        cls._managed_layouts.clear()

    @classmethod
    def get(cls, screen):
        screen_key = screen.as_pointer()
        data = cls._managed_layouts.get(screen_key)
        if data is None:
            return None
        return data

    @classmethod
    def get_editor_area(cls, screen, kind=None):
        data = cls.get(screen)
        if data is None:
            return None
        if kind is not None and data.get("kind") != kind:
            return None
        area_pointer = data.get("editor_pointer")
        if area_pointer is None:
            return None
        for s in bpy.data.screens:
            for area in s.areas:
                if area.as_pointer() == area_pointer:
                    return area
        return None

    @classmethod
    def get_view_area(cls, screen):
        data = cls.get(screen)
        if data is None:
            return None
        area_pointer = data.get("view_pointer")
        if area_pointer is None:
            return None
        for s in bpy.data.screens:
            for area in s.areas:
                if area.as_pointer() == area_pointer:
                    return area
        return None

    @classmethod
    def get_kind(cls, screen):
        data = cls.get(screen)
        if data is None:
            return None
        return data.get("kind")


# ============================================================
# Layout management helpers
# ============================================================

def get_layout_prefs():
    try:
        return bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return None


def should_auto_merge():
    prefs = get_layout_prefs()
    return prefs is not None and getattr(prefs, "auto_merge", True)


def should_protect_managed_area():
    prefs = get_layout_prefs()
    return prefs is not None and getattr(prefs, "protect_uv_area", True)


def get_split_factor(kind=None):
    return C.EDITOR_SPLIT_FACTOR


def get_editor_on_left(kind=None):
    return True


def get_screen_key(screen):
    return screen.as_pointer()


def remember_managed_layout(screen, view_area, editor_area, kind):
    LayoutState.remember(screen, view_area, editor_area, kind)


def clear_managed_layout(screen):
    LayoutState.clear(screen)


def find_area_by_pointer(area_pointer):
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.as_pointer() == area_pointer:
                return area
    return None


def get_managed_editor_area(screen, kind=None):
    return LayoutState.get_editor_area(screen, kind)


def get_managed_view_area(screen):
    return LayoutState.get_view_area(screen)


def get_managed_kind(screen):
    return LayoutState.get_kind(screen)


def area_matches_kind(area, kind):
    space = area.spaces.active if area.spaces else None
    if space is None:
        return False
    if kind == C.LAYOUT_KIND_UV:
        return area.type == 'IMAGE_EDITOR' and getattr(space, "mode", None) == 'UV'
    if kind == C.LAYOUT_KIND_SHADER:
        return area.type == 'NODE_EDITOR' and getattr(space, "tree_type", None) == 'ShaderNodeTree'
    return False


def get_editor_areas(screen, kind):
    return [area for area in screen.areas if area_matches_kind(area, kind)]


def tag_screen_redraw(screen):
    if not screen:
        return
    for area in screen.areas:
        if hasattr(area, 'tag_redraw'):
            try:
                area.tag_redraw()
            except Exception:
                pass


def tag_all_view3d_redraw():
    try:
        wm = bpy.data.window_managers[0]
    except Exception:
        return
    for window in wm.windows:
        screen = getattr(window, "screen", None)
        if screen:
            tag_screen_redraw(screen)


def sync_scene_layout_flags(scene, kind=None):
    scene.uv_layout_active = kind == C.LAYOUT_KIND_UV
    scene.shader_layout_active = kind == C.LAYOUT_KIND_SHADER


def get_window_region(area):
    if area is None:
        return None
    for region in area.regions:
        if region.type == 'WINDOW':
            return region
    return None


def capture_view_state(area):
    state = {
        "show_region_ui": True,
        "shading_type": 'SOLID',
        "clip_start": 0.01,
        "clip_end": 1000.0,
        "view_matrix": None,
    }
    if area is None or not area.spaces:
        return state
    space = area.spaces.active
    if space is None:
        return state
    state["show_region_ui"] = getattr(space, 'show_region_ui', True)
    if hasattr(space, 'shading'):
        state["shading_type"] = getattr(space.shading, 'type', 'SOLID')
    state["clip_start"] = getattr(space, 'clip_start', 0.01)
    state["clip_end"] = getattr(space, 'clip_end', 1000.0)
    if hasattr(space, 'region_3d') and space.region_3d:
        state["view_matrix"] = space.region_3d.view_matrix.copy()
    return state


def restore_view_state(area, state):
    if area is None or not area.spaces:
        return
    area.type = 'VIEW_3D'
    space = area.spaces.active
    if space is None:
        return
    space.show_region_ui = state.get("show_region_ui", True)
    if hasattr(space, 'shading'):
        space.shading.type = state.get("shading_type", 'SOLID')
    space.clip_start = state.get("clip_start", 0.01)
    space.clip_end = state.get("clip_end", 1000.0)
    view_matrix = state.get("view_matrix")
    if view_matrix and hasattr(space, 'region_3d') and space.region_3d:
        space.region_3d.view_matrix = view_matrix


def configure_editor_area(area, kind):
    if kind == C.LAYOUT_KIND_UV:
        area.type = 'IMAGE_EDITOR'
        space = area.spaces.active
        if space:
            space.mode = 'UV'
            space.show_region_toolbar = True
            space.show_region_ui = False
        return
    if kind == C.LAYOUT_KIND_SHADER:
        area.type = 'NODE_EDITOR'
        space = area.spaces.active
        if space:
            space.tree_type = 'ShaderNodeTree'
            space.show_region_toolbar = True
            space.show_region_ui = False


def get_layout_areas_after_split(screen, original_area, previous_pointers):
    """返回 (新分割出的区域, 原区域)。

    不能按 area.x 排序：area_split 后新区域的坐标尚未更新，
    排序结果不稳定，可能把原区域误当成新区域。
    """
    new_areas = [area for area in screen.areas if area.as_pointer() not in previous_pointers]
    if not new_areas:
        return None, None
    return new_areas[-1], original_area


def get_fixed_editor_layout_areas_after_split(screen, original_area, previous_pointers):
    """返回 (编辑器区域=新分割区域, 3D视图区域=原区域)。

    保证原 3D 视图不被转换，新分割出的区域作为 UV/着色器编辑器。
    """
    new_areas = [area for area in screen.areas if area.as_pointer() not in previous_pointers]
    if not new_areas:
        return None, None
    return new_areas[-1], original_area


# ============================================================
# LayoutManager — 统一布局切换服务
# ============================================================

class LayoutManager:
    """管理 UV/Shader 编辑器布局的创建、切换、关闭。

    将 WorkspaceLayoutToggleMixin 的逻辑提取为独立服务类，
    使 Operator 只做编排，不包含布局算法。
    """

    def __init__(self, kind, label):
        self.target_kind = kind
        self.target_label = label

    def invoke(self, context, event):
        """处理 confirm_open 偏好后的进入点"""
        prefs = get_layout_prefs()
        if prefs is not None and prefs.confirm_open and self.should_confirm_open(context):
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def should_confirm_open(self, context):
        screen = context.screen
        managed_kind = get_managed_kind(screen)
        if managed_kind == self.target_kind or get_managed_editor_area(screen) is not None:
            return False
        return not get_editor_areas(screen, self.target_kind)

    def execute(self, context):
        """检查操作锁后执行布局切换"""
        if not C.check_operation_lock():
            return {'CANCELLED'}

        C.set_operation_lock()
        try:
            if context.area is None or context.area.type != 'VIEW_3D':
                return {'CANCELLED'}
            return self.toggle_layout(context, self.target_kind)
        except Exception:
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            C.release_operation_lock()

    def toggle_layout(self, context, kind):
        """布局切换决策树 — 关闭 / 切换 / 创建"""
        screen = context.screen
        managed_area = get_managed_editor_area(screen)
        managed_kind = get_managed_kind(screen)

        if managed_area is not None:
            if managed_kind == kind:
                return self.close_layout(context, screen, managed_area, managed_kind)
            return self.switch_layout(context, screen, managed_area, kind)

        matching_areas = get_editor_areas(screen, kind)
        if matching_areas:
            sync_scene_layout_flags(context.scene, kind)
            tag_screen_redraw(screen)
            return {'FINISHED'}

        other_kind = C.LAYOUT_KIND_SHADER if kind == C.LAYOUT_KIND_UV else C.LAYOUT_KIND_UV
        other_areas = get_editor_areas(screen, other_kind)
        if other_areas and not should_protect_managed_area():
            area = other_areas[-1]
            configure_editor_area(area, kind)
            remember_managed_layout(screen, context.area, area, kind)
            sync_scene_layout_flags(context.scene, kind)
            tag_screen_redraw(screen)
            return {'FINISHED'}

        return self.create_layout(context, kind)

    def create_layout(self, context, kind):
        """垂直分割 3D 视图，创建 UV 或 Shader 编辑器"""
        original_area = context.area
        window = context.window
        screen = context.screen

        if original_area is None or not hasattr(original_area, 'spaces') or not original_area.spaces:
            return {'CANCELLED'}

        region = get_window_region(original_area)
        if region is None:
            return {'CANCELLED'}

        previous_pointers = {area.as_pointer() for area in screen.areas}
        view_state = capture_view_state(original_area)
        with bpy.context.temp_override(window=window, area=original_area, region=region):
            bpy.ops.screen.area_split(direction='VERTICAL', factor=get_split_factor(kind))

        if kind in {C.LAYOUT_KIND_UV, C.LAYOUT_KIND_SHADER}:
            editor_area, view_area = get_fixed_editor_layout_areas_after_split(
                screen, original_area, previous_pointers)
        else:
            left_area, right_area = get_layout_areas_after_split(
                screen, original_area, previous_pointers)
            if get_editor_on_left(kind):
                editor_area = left_area
                view_area = right_area
            else:
                view_area = left_area
                editor_area = right_area

        if editor_area is None or view_area is None:
            return {'CANCELLED'}

        configure_editor_area(editor_area, kind)
        restore_view_state(view_area, view_state)
        remember_managed_layout(screen, view_area, editor_area, kind)
        sync_scene_layout_flags(context.scene, kind)
        tag_screen_redraw(screen)
        return {'FINISHED'}

    def switch_layout(self, context, screen, editor_area, kind):
        """将已有编辑器区域切换为另一种类型"""
        configure_editor_area(editor_area, kind)
        view_area = get_managed_view_area(screen) or context.area
        remember_managed_layout(screen, view_area, editor_area, kind)
        sync_scene_layout_flags(context.scene, kind)
        tag_screen_redraw(screen)
        return {'FINISHED'}

    def close_layout(self, context, screen, editor_area, kind):
        """关闭插件创建的编辑器区域，合并回 3D 视图"""
        if not should_auto_merge():
            view_area = get_managed_view_area(screen) or context.area
            restore_view_state(editor_area, capture_view_state(view_area))
            clear_managed_layout(screen)
            sync_scene_layout_flags(context.scene, None)
            tag_screen_redraw(screen)
            return {'FINISHED'}

        region = get_window_region(editor_area)
        if region is None:
            return {'CANCELLED'}

        with bpy.context.temp_override(window=context.window, area=editor_area, region=region):
            bpy.ops.screen.area_close()

        clear_managed_layout(screen)
        sync_scene_layout_flags(context.scene, None)
        tag_screen_redraw(screen)
        return {'FINISHED'}


# ============================================================
# Property registration
# ============================================================

def register_properties():
    bpy.types.Scene.uv_layout_active = bpy.props.BoolProperty(
        name="UV布局激活",
        description="UV编辑器布局是否激活",
        default=False,
    )
    bpy.types.Scene.shader_layout_active = bpy.props.BoolProperty(
        name="着色器布局激活",
        description="着色器编辑器布局是否激活",
        default=False,
    )


def unregister_properties():
    if hasattr(bpy.types.Scene, 'uv_layout_active'):
        del bpy.types.Scene.uv_layout_active
    if hasattr(bpy.types.Scene, 'shader_layout_active'):
        del bpy.types.Scene.shader_layout_active
