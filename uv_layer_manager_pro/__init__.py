# -*- coding: utf-8 -*-

bl_info = {
    "name": "UV Layer Manager Pro",
    "author": "Developer",
    "version": (1, 6, 0),
    "blender": (4, 1, 0),
    "location": "View3D > Sidebar > UV",
    "description": "管理模型的UV层，支持添加、删除、复制和同步UV层",
    "category": "UV",
}

import bpy

from . import utils as U
from . import shortcuts as SH
from . import material_id as MID
from . import layout as L
from . import normal_angle as NA
from . import merge_vertices as MV
from . import material_ops as MOPS
from .uv_ops import (
    UV_LAYER_MANAGER_OT_add,
    UV_LAYER_MANAGER_OT_delete,
    UV_LAYER_MANAGER_OT_select,
    UV_LAYER_MANAGER_OT_copy,
    UV_LAYER_MANAGER_OT_sync,
    UV_LAYER_MANAGER_OT_select_max,
)
from .modeling_ops import (
    UV_LAYER_MANAGER_OT_clean_normals,
    UV_LAYER_MANAGER_OT_set_normal_angle,
    UV_LAYER_MANAGER_OT_reset_uv_names,
    UV_LAYER_MANAGER_OT_snap_close_vertices,
    UV_LAYER_MANAGER_OT_set_close_snap_distance,
    UV_LAYER_MANAGER_OT_set_uv_naming,
    UV_LAYER_MANAGER_OT_rotate_linked_duplicate,
    UV_LAYER_MANAGER_OT_select_ngons,
    UV_LAYER_MANAGER_OT_quadify_ngons,
    UV_LAYER_MANAGER_OT_select_overlapping_faces,
    UV_LAYER_MANAGER_OT_select_by_angle,
    UV_LAYER_MANAGER_OT_set_select_angle,
)
from .material_ops import (
    UV_LAYER_MANAGER_OT_assign_material,
    UV_LAYER_MANAGER_OT_remove_material,
    UV_LAYER_MANAGER_OT_remove_material_by_name,
    UV_LAYER_MANAGER_OT_add_material,
    UV_LAYER_MANAGER_OT_remove_material_slot,
    UV_LAYER_MANAGER_OT_select_material_slot,
    UV_LAYER_MANAGER_OT_assign_material_slot,
    UV_LAYER_MANAGER_OT_edit_material_base_color,
    UV_LAYER_MANAGER_OT_toggle_material_id_color,
    UV_LAYER_MANAGER_OT_edit_material_id_color,
    UV_LAYER_MANAGER_OT_edit_material_id_color_for_target,
    UV_LAYER_MANAGER_OT_set_material_id_preset,
    UV_LAYER_MANAGER_OT_clear_material_slots,
    UV_LAYER_MANAGER_OT_clean_unused_material_slots,
    UV_LAYER_MANAGER_OT_merge_duplicate_materials,
    UV_LAYER_MANAGER_OT_organize_materials,
    UV_LAYER_MANAGER_OT_toggle_vertex_color_view,
    UV_LAYER_MANAGER_OT_set_color_attribute,
)
from .view_ops import (
    UV_LAYER_MANAGER_OT_toggle_uv_editor,
    UV_LAYER_MANAGER_OT_toggle_shader_editor,
)
from .flatten_ops import (
    UV_LAYER_MANAGER_OT_flatten_u,
    UV_LAYER_MANAGER_OT_flatten_v,
    UV_LAYER_MANAGER_OT_pin_verts,
    UV_LAYER_MANAGER_OT_unpin_verts,
)
from .ui import (
    UV_LAYER_MANAGER_UL_uv_layers,
    UV_LAYER_MANAGER_UL_material_slots,
    UV_LAYER_MANAGER_PT_panel,
    UV_LAYER_MANAGER_PT_uv_panel,
    UV_LAYER_MANAGER_PT_modeling_panel,
    UV_LAYER_MANAGER_PT_material_panel,
    UV_LAYER_MANAGER_MT_shortcut_menu,
)
from .preferences import UV_LAYER_MANAGER_prefs



classes = (
    UV_LAYER_MANAGER_OT_add,
    UV_LAYER_MANAGER_OT_delete,
    UV_LAYER_MANAGER_OT_select,
    UV_LAYER_MANAGER_OT_copy,
    UV_LAYER_MANAGER_OT_sync,
    UV_LAYER_MANAGER_OT_select_max,
    UV_LAYER_MANAGER_OT_clean_normals,
    UV_LAYER_MANAGER_OT_set_normal_angle,
    UV_LAYER_MANAGER_OT_reset_uv_names,
    UV_LAYER_MANAGER_OT_snap_close_vertices,
    UV_LAYER_MANAGER_OT_set_close_snap_distance,
    UV_LAYER_MANAGER_OT_set_uv_naming,
    UV_LAYER_MANAGER_OT_rotate_linked_duplicate,
    UV_LAYER_MANAGER_OT_select_ngons,
    UV_LAYER_MANAGER_OT_quadify_ngons,
    UV_LAYER_MANAGER_OT_select_overlapping_faces,
    UV_LAYER_MANAGER_OT_select_by_angle,
    UV_LAYER_MANAGER_OT_set_select_angle,
    UV_LAYER_MANAGER_OT_assign_material,
    UV_LAYER_MANAGER_OT_remove_material,
    UV_LAYER_MANAGER_OT_remove_material_by_name,
    UV_LAYER_MANAGER_OT_add_material,
    UV_LAYER_MANAGER_OT_remove_material_slot,
    UV_LAYER_MANAGER_OT_select_material_slot,
    UV_LAYER_MANAGER_OT_assign_material_slot,
    UV_LAYER_MANAGER_OT_edit_material_base_color,
    UV_LAYER_MANAGER_OT_toggle_material_id_color,
    UV_LAYER_MANAGER_OT_edit_material_id_color,
    UV_LAYER_MANAGER_OT_edit_material_id_color_for_target,
    UV_LAYER_MANAGER_OT_set_material_id_preset,
    UV_LAYER_MANAGER_OT_clear_material_slots,
    UV_LAYER_MANAGER_OT_clean_unused_material_slots,
    UV_LAYER_MANAGER_OT_merge_duplicate_materials,
    UV_LAYER_MANAGER_OT_organize_materials,
    UV_LAYER_MANAGER_OT_toggle_vertex_color_view,
    UV_LAYER_MANAGER_OT_set_color_attribute,
    UV_LAYER_MANAGER_OT_toggle_uv_editor,
    UV_LAYER_MANAGER_OT_toggle_shader_editor,
    UV_LAYER_MANAGER_OT_flatten_u,
    UV_LAYER_MANAGER_OT_flatten_v,
    UV_LAYER_MANAGER_OT_pin_verts,
    UV_LAYER_MANAGER_OT_unpin_verts,
    UV_LAYER_MANAGER_UL_uv_layers,
    UV_LAYER_MANAGER_UL_material_slots,
    UV_LAYER_MANAGER_prefs,
    UV_LAYER_MANAGER_MT_shortcut_menu,
    UV_LAYER_MANAGER_PT_panel,
    UV_LAYER_MANAGER_PT_uv_panel,
    UV_LAYER_MANAGER_PT_modeling_panel,
    UV_LAYER_MANAGER_PT_material_panel,
)


def register():
    registered_classes = []
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
            registered_classes.append(cls)
        except Exception as e:
            for registered_cls in reversed(registered_classes):
                try:
                    bpy.utils.unregister_class(registered_cls)
                except Exception:
                    pass
            raise RuntimeError(f"[UV Layer Manager] 注册 {cls.__name__} 失败: {e}") from e

    SH.register_shortcut_keymaps()
    MID.ensure_id_color_previews()
    bpy.app.timers.register(MID.precache_material_icons, first_interval=0.1)

    # ---- Properties ----
    L.register_properties()
    MOPS.register_properties()
    MV.register_properties()
    NA.register_properties()
    MID.register_properties()

    # ---- UV Naming props ----
    bpy.types.Scene.uv_naming_prefix = bpy.props.StringProperty(
        name="UV命名前缀",
        description="UV层命名前缀，如 uvmap → uvmap1, uvmap2",
        default="uvmap",
    )
    bpy.types.Scene.uv_naming_count = bpy.props.IntProperty(
        name="UV层数",
        description="保留的UV层数量",
        default=3,
        min=1,
        max=20,
    )

    # ---- Scene section-fold props (stays in __init__) ----
    bpy.types.Scene.show_uv_section = bpy.props.BoolProperty(
        name="显示UV管理",
        description="展开/折叠UV层管理面板",
        default=True,
    )
    bpy.types.Scene.show_modeling_section = bpy.props.BoolProperty(
        name="显示建模工具",
        description="展开/折叠建模工具面板",
        default=False,
    )
    bpy.types.Scene.show_material_section = bpy.props.BoolProperty(
        name="显示材质管理",
        description="展开/折叠材质管理面板",
        default=True,
    )
    bpy.types.Scene.show_shortcut_section = bpy.props.BoolProperty(
        name="显示快捷键",
        description="展开/折叠插件快捷键设置面板",
        default=False,
    )

    L.tag_all_view3d_redraw()


def unregister():
    # ---- Restore state ----
    MID.restore_material_id_colors()
    MID.clear_id_color_previews()
    SH.unregister_shortcut_keymaps()
    L.LayoutState.clear_all()

    # ---- Clean up properties ----
    L.unregister_properties()
    MOPS.unregister_properties()
    MV.unregister_properties()
    NA.unregister_properties()
    MID.unregister_properties()

    # ---- UV Naming props ----
    if hasattr(bpy.types.Scene, 'uv_naming_prefix'):
        del bpy.types.Scene.uv_naming_prefix
    if hasattr(bpy.types.Scene, 'uv_naming_count'):
        del bpy.types.Scene.uv_naming_count

    # ---- Scene section-fold props ----
    if hasattr(bpy.types.Scene, 'show_uv_section'):
        del bpy.types.Scene.show_uv_section
    if hasattr(bpy.types.Scene, 'show_modeling_section'):
        del bpy.types.Scene.show_modeling_section
    if hasattr(bpy.types.Scene, 'show_material_section'):
        del bpy.types.Scene.show_material_section
    if hasattr(bpy.types.Scene, 'show_shortcut_section'):
        del bpy.types.Scene.show_shortcut_section

    # ---- Unregister classes ----
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


if __name__ == "__main__":
    register()
