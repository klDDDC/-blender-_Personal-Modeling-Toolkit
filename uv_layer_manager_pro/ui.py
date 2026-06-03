# -*- coding: utf-8 -*-
"""
UV Layer Manager - UI (UIList, Panel, Menu, draw functions)
"""
import bpy
from . import constants as C
from . import utils as U
from . import clipboard as CB
from . import layout as L
from . import material_id as MID
from . import shortcuts as SH
from . import vertex_color_nodes as VCN


# ============================================================
# UIList
# ============================================================

class UV_LAYER_MANAGER_UL_uv_layers(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.operator_context = 'INVOKE_DEFAULT'
        row = layout.row(align=True)
        row.scale_y = 1.05

        split = row.split(factor=0.88, align=True)
        left = split.row(align=True)
        right = split.row(align=True)

        if getattr(data.uv_layers, "active_index", -1) == index:
            left.label(text="", icon='CHECKBOX_HLT')
        else:
            left.label(text="", icon='BLANK1')

        op_select = left.operator(
            "uv_layer_manager.select",
            text=item.name,
            emboss=False,
        )
        op_select.index = index

        op_copy = right.operator(
            "uv_layer_manager.copy",
            text="",
            icon='COPYDOWN',
            emboss=False,
        )
        op_copy.index = index


class UV_LAYER_MANAGER_UL_material_slots(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.operator_context = 'INVOKE_DEFAULT'
        row = layout.row(align=True)
        selected_face_material_index = U.get_selected_face_material_index_cached(context, data)
        if selected_face_material_index == index:
            row.alert = True
        row.scale_y = 1.18

        material = item.material
        if material is not None:
            try:
                icon_value = MID.get_color_preview_icon(tuple(material.diffuse_color), f"dclr_{material.as_pointer()}")
            except Exception:
                icon_value = 0
            row.label(
                text="",
                icon_value=icon_value,
            )
            id_enabled = MID.MaterialIdState.has_original(material)
            op_toggle_id = row.operator(
                "uv_layer_manager.toggle_material_id_color",
                text="",
                icon='CHECKBOX_HLT' if id_enabled else 'CHECKBOX_DEHLT',
                emboss=False,
                depress=id_enabled,
            )
            op_toggle_id.index = index
            op_edit_id = row.operator(
                "uv_layer_manager.edit_material_id_color",
                text="",
                icon='PREFERENCES',
                emboss=False,
            )
            op_edit_id.index = index
            row.label(
                text="",
                icon_value=layout.icon(material),
            )
            name_row = row.row(align=True)
            name_row.prop(material, "name", text="", emboss=False)

            op_assign = row.operator(
                "uv_layer_manager.assign_material_slot",
                text="",
                icon='BACK',
                emboss=False,
            )
            op_assign.index = index
        else:
            op_select = row.operator(
                "uv_layer_manager.select_material_slot",
                text="空材质槽",
                icon='BLANK1',
                emboss=False,
            )
            op_select.index = index

        op_remove = row.operator(
            "uv_layer_manager.remove_material_slot",
            text="",
            icon='REMOVE',
            emboss=False,
        )
        op_remove.index = index


# ============================================================
# Drawing helpers
# ============================================================

def draw_empty_uv_list(layout):
    box = layout.box()
    col = box.column(align=True)
    for _ in range(4):
        row = col.row(align=True)
        row.scale_y = 1.1
        row.label(text="", icon='BLANK1')


def draw_status_card(layout, title, value, icon='BLANK1'):
    card = layout.box()
    col = card.column(align=True)
    col.scale_y = 0.92
    col.label(text=title, icon=icon)
    value_row = col.row(align=True)
    value_row.scale_y = 0.85
    value_row.label(text=str(value))


def draw_top_dashboard(layout, context):
    scene = context.scene
    objects = U.get_selected_mesh_objects(context)
    obj, mesh = U.get_active_mesh(context)
    uv_count = len(mesh.uv_layers) if mesh and mesh.uv_layers else 0
    scene_max_count, _ = U.get_scene_max_uv_info(scene)
    material_count = len(obj.material_slots) if obj else 0

    row = layout.row(align=True)
    row.scale_y = 1.05
    draw_status_card(row, "当前网格", len(objects), 'MESH_DATA')
    draw_status_card(row, "UV层", f"{uv_count} / {scene_max_count}", 'UV')
    draw_status_card(row, "材质槽", material_count, 'MATERIAL')


def draw_section_header(layout, scene, scene_prop, title, icon, right_text=""):
    header = layout.row(align=True)
    header.scale_y = 1.05
    is_open = getattr(scene, scene_prop)
    disclosure = 'DISCLOSURE_TRI_DOWN' if is_open else 'DISCLOSURE_TRI_RIGHT'
    header.prop(scene, scene_prop, text="", icon=disclosure, emboss=False)
    header.label(text=title, icon=icon)
    if right_text:
        right = header.row(align=True)
        right.alignment = 'RIGHT'
        right.label(text=right_text)
    return is_open


def draw_empty_state(layout, message, icon='INFO'):
    box = layout.box()
    col = box.column(align=True)
    col.scale_y = 1.5
    col.label(text=message, icon=icon)


# ============================================================
# Section draw functions
# ============================================================

def draw_uv_section(layout, context, obj, mesh):
    layout.operator_context = 'INVOKE_DEFAULT'
    scene = context.scene
    scene_max_count, _ = U.get_scene_max_uv_info(scene)
    uv_count = len(mesh.uv_layers) if mesh and mesh.uv_layers else 0

    box = layout.box()
    if not draw_section_header(box, scene, "show_uv_section", "UV 层管理", 'UV', f"当前: {uv_count} / 场景最大: {scene_max_count}"):
        return

    col = box.column(align=True)
    if obj is None or mesh is None or not obj.select_get():
        draw_empty_uv_list(col)
        col.separator()
        row_edit = col.row(align=True)
        row_edit.scale_y = 1.2
        row_edit.enabled = False
        row_edit.operator("uv_layer_manager.add", text="+ 添加", icon='ADD')
        row_edit.operator("uv_layer_manager.delete", text="- 删除", icon='REMOVE')

        row_tools = col.row(align=True)
        row_tools.scale_y = 1.15
        row_tools.enabled = False
        row_tools.operator("uv_layer_manager.sync", text="同步 UV", icon='PASTEDOWN')
        row_tools.operator("uv_layer_manager.select_max", text="选中最大模型", icon='OBJECT_DATA')
        return

    uv_layers = mesh.uv_layers
    if uv_layers is None:
        return

    if CB.UVClipboard.has_data():
        row_clip = col.row(align=True)
        row_clip.label(text="剪贴板", icon='COPYDOWN')
        row_clip.label(text=CB.UVClipboard.get_source_name())
        row_clip.label(text=f"({CB.UVClipboard.get_loop_count()}点)")

    col.separator()
    col.template_list(
        "UV_LAYER_MANAGER_UL_uv_layers",
        "",
        mesh,
        "uv_layers",
        uv_layers,
        "active_index",
        rows=4,
        maxrows=4,
    )

    col.separator()
    row_edit = col.row(align=True)
    row_edit.scale_y = 1.2

    col_add = row_edit.column()
    col_add.operator("uv_layer_manager.add", text="+ 添加", icon='ADD')
    if uv_count >= C.MAX_UV_LAYERS:
        col_add.enabled = False

    col_del = row_edit.column()
    col_del.operator("uv_layer_manager.delete", text="- 删除", icon='REMOVE')
    if uv_count <= 1:
        col_del.enabled = False

    if uv_count >= C.MAX_UV_LAYERS:
        row_warn = col.row()
        row_warn.alert = True
        row_warn.label(text=f"已达上限（{C.MAX_UV_LAYERS}）", icon='ERROR')

    row_tools = col.row(align=True)
    row_tools.scale_y = 1.15

    col_sync = row_tools.column()
    col_sync.operator("uv_layer_manager.sync", text="同步 UV", icon='PASTEDOWN')
    if not CB.UVClipboard.has_data():
        col_sync.enabled = False

    col_sel_max = row_tools.column()
    col_sel_max.operator("uv_layer_manager.select_max", text="选中最大模型", icon='OBJECT_DATA')
    if scene_max_count == 0:
        col_sel_max.enabled = False

    col.separator()
    row = col.row(align=True)
    row.scale_y = 1.2
    row.operator("uv_layer_manager.flatten_u", text="打平U", icon='ALIGN_CENTER')
    row.operator("uv_layer_manager.flatten_v", text="打平V", icon='ALIGN_MIDDLE')

    row = col.row(align=True)
    row.scale_y = 1.2
    row.operator("uv_layer_manager.pin_verts", text="固定顶点", icon='PINNED')
    row.operator("uv_layer_manager.unpin_verts", text="取消固定", icon='UNPINNED')


def draw_modeling_tools_section(layout, context):
    try:
        layout.operator_context = 'INVOKE_DEFAULT'
        scene = context.scene
        selected_mesh_count = len(U.get_selected_mesh_objects(context))

        box = layout.box()
        if not draw_section_header(box, scene, "show_modeling_section", "建模工具", 'TOOL_SETTINGS', f"{selected_mesh_count} 个工具"):
            return

        col = box.column(align=True)

        action_row = col.row(align=True)
        action_row.scale_y = 1.25
        action_main = action_row.row(align=True)
        action_main.operator("uv_layer_manager.reset_uv_names", text="uv命名重置", icon='UV')
        action_settings = action_row.row(align=True)
        action_settings.operator("uv_layer_manager.set_uv_naming", text="", icon='PREFERENCES')
        if selected_mesh_count == 0:
            action_main.enabled = False

        close_row = col.row(align=True)
        close_row.scale_y = 1.25
        close_main = close_row.row(align=True)
        close_main.operator("uv_layer_manager.snap_close_vertices", text="合并相近", icon='AUTOMERGE_OFF')
        close_settings = close_row.row(align=True)
        close_settings.operator("uv_layer_manager.set_close_snap_distance", text="", icon='PREFERENCES')
        if selected_mesh_count == 0:
            close_main.enabled = False

        rotate_row = col.row(align=True)
        rotate_row.scale_y = 1.25
        rotate_row.operator("uv_layer_manager.rotate_linked_duplicate", text="旋转复制", icon='DUPLICATE')
        if selected_mesh_count == 0:
            rotate_row.enabled = False

        col.separator()

        ngon_row = col.row(align=True)
        ngon_row.scale_y = 1.25
        ngon_row.operator("uv_layer_manager.select_ngons", text="大于4边面", icon='SNAP_FACE')
        ngon_row.operator("uv_layer_manager.quadify_ngons", text="处理多边面", icon='MOD_TRIANGULATE')
        if selected_mesh_count == 0:
            ngon_row.enabled = False

        overlap_row = col.row(align=True)
        overlap_row.scale_y = 1.25
        overlap_row.operator("uv_layer_manager.select_overlapping_faces", text="检查重叠面", icon='FACESEL')
        if selected_mesh_count == 0:
            overlap_row.enabled = False

        angle_row = col.row(align=True)
        angle_row.scale_y = 1.25
        angle_main = angle_row.row(align=True)
        angle_main.operator("uv_layer_manager.select_by_angle", text="角度选择", icon='ORIENTATION_NORMAL')
        angle_settings = angle_row.row(align=True)
        angle_threshold = getattr(scene, "uvlm_select_angle_threshold", 30.0)
        angle_settings.operator("uv_layer_manager.set_select_angle", text=f"{angle_threshold:g}°", icon='PREFERENCES')
        if selected_mesh_count == 0:
            angle_main.enabled = False

        return
    except Exception as e:
        layout.label(text=f"UI绘制错误: {str(e)[:30]}", icon='ERROR')


def draw_material_management_section(layout, context):
    try:
        U.begin_draw_frame()
        layout.operator_context = 'INVOKE_DEFAULT'
        scene = context.scene
        objects = U.get_selected_mesh_objects(context)
        active_obj = context.active_object if context.active_object and context.active_object.type == 'MESH' else None

        box = layout.box()
        mode = "单" if len(objects) <= 1 else "多"
        if not draw_section_header(box, scene, "show_material_section", "材质管理", 'MATERIAL', f"{mode}选 | {len(objects)}个模型"):
            return

        col = box.column(align=True)

        material_row = col.row(align=True)
        if len(objects) == 0:
            empty_col = material_row.column(align=True)
            empty_col.enabled = False
            empty_col.label(text="未选中模型", icon='MATERIAL')
            for _ in range(3):
                empty_col.label(text="")
        elif len(objects) == 1:
            ao = objects[0]
            material_row.template_list(
                "UV_LAYER_MANAGER_UL_material_slots",
                "",
                ao,
                "material_slots",
                ao,
                "active_material_index",
                rows=4,
                maxrows=6,
            )
        else:
            # 多选：按材质去重显示，避免多个模型共享同一材质时重复刷屏。
            sub = material_row.column(align=True)
            sub.scale_y = 1.15
            material_groups = {}
            empty_objects = []
            for obj in objects:
                if not obj.material_slots:
                    empty_objects.append(obj)
                    continue
                for slot_index, slot in enumerate(obj.material_slots):
                    mat = slot.material
                    if mat is None:
                        continue
                    key = mat.as_pointer()
                    group = material_groups.setdefault(key, {"material": mat, "slots": []})
                    group["slots"].append((obj, slot_index))

            for group in material_groups.values():
                mat = group["material"]
                slots = group["slots"]
                first_obj, first_slot_index = slots[0]
                object_count = len({obj.as_pointer() for obj, _slot_index in slots})
                row = sub.row(align=True)
                ico = 0
                try:
                    ico = mat.preview.icon_id
                except Exception:
                    pass
                row.label(text="", icon_value=ico)
                row.label(text=mat.name)
                op_remove = row.operator("uv_layer_manager.remove_material_by_name", text="", icon='X')
                op_remove.material_name = mat.name
                row.label(text=f"{object_count}物体/{len(slots)}槽")

            if empty_objects:
                row = sub.row(align=True)
                row.label(text=f"{len(empty_objects)} 个选中模型无材质槽", icon='BLANK1')
            if not material_groups:
                row = sub.row(align=True)
                row.label(text="所有选中模型均无材质", icon='MATERIAL')

        material_tools = material_row.column(align=True)
        material_tools.scale_x = 0.82
        material_tools.operator("uv_layer_manager.add_material", text="", icon='ADD')
        if len(objects) == 0:
            material_tools.enabled = False

        duplicate_count = len(U.get_duplicate_material_map())
        compact_row = col.row(align=True)
        compact_row.scale_y = 1.2
        compact_row.operator(
            "uv_layer_manager.organize_materials",
            text=f"整理材质 ({duplicate_count})",
            icon='BRUSH_DATA',
        )
        op_id = compact_row.operator(
            "uv_layer_manager.toggle_vertex_color_view",
            text="材质ID",
            icon='COLOR',
            depress=scene.material_view_mode == 'ID',
        )
        op_id.mode = 'ID'

        col.separator()

        view_row = col.row(align=True)
        view_row.scale_y = 1.15
        op_color = view_row.operator(
            "uv_layer_manager.toggle_vertex_color_view",
            text="顶点颜色",
            icon='GROUP_VCOL',
        )
        op_color.mode = 'COLOR'
        op_alpha = view_row.operator(
            "uv_layer_manager.toggle_vertex_color_view",
            text="顶点alpha",
            icon='IMAGE_ALPHA',
        )
        op_alpha.mode = 'ALPHA'

        if active_obj and hasattr(active_obj.data, "color_attributes"):
            active_attribute = VCN.get_active_color_attribute(active_obj.data)
            color_count = len(active_obj.data.color_attributes)
            info_row = col.row(align=True)
            active_name = active_attribute.name if active_attribute else "无"
            info_row.label(text=f"颜色属性: {active_name} / {color_count}", icon='GROUP_VCOL')

            for index, attribute in enumerate(active_obj.data.color_attributes):
                if index >= 6:
                    break
                attr_row = col.row(align=True)
                op = attr_row.operator(
                    "uv_layer_manager.set_color_attribute",
                    text=attribute.name,
                    icon='CHECKBOX_HLT' if active_attribute and attribute.name == active_attribute.name else 'BLANK1',
                    emboss=False,
                )
                op.name = attribute.name
        else:
            info_row = col.row(align=True)
            info_row.label(text="当前模型没有顶点颜色", icon='INFO')
    except Exception as e:
        layout.label(text=f"材质UI错误: {str(e)[:40]}", icon='ERROR')


def draw_shortcut_section(layout, context):
    try:
        scene = context.scene
        box = layout.box()
        if not draw_section_header(box, scene, "show_shortcut_section", "快捷键", 'KEYINGSET', "直接修改"):
            return

        col = box.column(align=True)
        col.label(text="空白表示未设置，点击按键框可录入快捷键", icon='INFO')
        if not C._addon_keymaps:
            col.label(text="快捷键槽位未注册，请重新启用插件", icon='ERROR')
            return

        for keymap, item, label in C._addon_keymaps:
            row = col.row(align=True)
            row.label(text=label)
            SH.draw_shortcut_keymap_item(row, context, keymap, item)
    except Exception as e:
        layout.label(text=f"快捷键UI错误: {str(e)[:40]}", icon='ERROR')


def draw_layout_section(layout, context):
    try:
        layout.operator_context = 'INVOKE_DEFAULT'
        scene = context.scene

        box = layout.box()
        if not draw_section_header(box, scene, "show_layout_section", "布局切换", 'WORKSPACE', "编辑器"):
            return

        col = box.column(align=True)

        uv_active = False
        shader_active = False
        managed_uv = False
        managed_shader = False
        has_editor = False

        if context.screen and context.screen.areas:
            managed_uv = L.get_managed_editor_area(context.screen, C.LAYOUT_KIND_UV) is not None
            managed_shader = L.get_managed_editor_area(context.screen, C.LAYOUT_KIND_SHADER) is not None
            uv_active = U.is_uv_edit_active(context)
            shader_active = U.is_shader_edit_active(context)
            has_editor = uv_active or shader_active

        row_buttons = col.row(align=True)
        row_buttons.scale_y = 1.35

        uv_text = "关闭UV" if managed_uv else "UV"
        shader_text = "关闭着色器" if managed_shader else "着色器"

        row_buttons.operator(
            "uv_layer_manager.toggle_uv_editor",
            text=uv_text,
            icon='X' if uv_active else 'UV',
            depress=managed_uv
        )

        row_buttons.operator(
            "uv_layer_manager.toggle_shader_editor",
            text=shader_text,
            icon='X' if shader_active else 'NODETREE',
            depress=managed_shader
        )

        if managed_uv:
            status_row = col.row(align=True)
            status_row.label(text="UV编辑器", icon='CHECKBOX_HLT')
            status_row.label(text="(点击关闭或切换)", icon='INFO')
        elif managed_shader:
            status_row = col.row(align=True)
            status_row.label(text="着色器编辑器", icon='CHECKBOX_HLT')
            status_row.label(text="(点击关闭或切换)", icon='INFO')
        elif uv_active:
            status_row = col.row(align=True)
            status_row.label(text="检测到现有UV编辑器", icon='INFO')
        elif shader_active:
            status_row = col.row(align=True)
            status_row.label(text="检测到现有着色器编辑器", icon='INFO')

        col.separator()

        normal_row = col.row(align=True)
        normal_row.scale_y = 1.18
        for preset, label in (
            ('180', "180"),
            ('30', "30"),
            ('60', "60"),
            ('90', "90"),
        ):
            op = normal_row.operator(
                "uv_layer_manager.set_normal_angle",
                text=label,
                depress=scene.normal_angle_preset == preset,
            )
            op.preset = preset

        custom_row = col.row(align=True)
        custom_row.prop(scene, "normal_angle_custom", text="")
        op_custom = custom_row.operator(
            "uv_layer_manager.set_normal_angle",
            text="自定义",
            depress=scene.normal_angle_preset == C.NORMAL_ANGLE_PRESET_CUSTOM,
        )
        op_custom.preset = C.NORMAL_ANGLE_PRESET_CUSTOM

        if len(U.get_selected_mesh_objects(context)) == 0:
            normal_row.enabled = False
            custom_row.enabled = False

    except Exception as e:
        layout.label(text=f"UI绘制错误: {str(e)[:30]}", icon='ERROR')


# ============================================================
# Panel
# ============================================================

class UV_LAYER_MANAGER_PT_panel(bpy.types.Panel):
    bl_label = "UV Layer Manager"
    bl_idname = "UV_LAYER_MANAGER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV"
    bl_order = 0

    def draw_header(self, context):
        self.layout.label(text="", icon='UV')

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        try:
            draw_layout_section(layout, context)
            draw_shortcut_section(layout, context)
        except Exception as e:
            layout.label(text=f"绘制错误: {e}", icon='ERROR')


class UV_LAYER_MANAGER_PT_uv_panel(bpy.types.Panel):
    bl_label = "UV层管理"
    bl_idname = "UV_LAYER_MANAGER_PT_uv_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV"
    bl_order = 1

    def draw_header(self, context):
        selected_mesh_count = len(U.get_selected_mesh_objects(context))
        self.layout.label(text=f"选中网格: {selected_mesh_count}", icon='MESH_DATA')

    def draw(self, context):
        layout = self.layout
        try:
            obj, mesh = U.get_active_mesh(context)
            if obj is None or mesh is None:
                col = layout.column(align=True)
                scene_max_count, _ = U.get_scene_max_uv_info(context.scene)

                row_info = col.row(align=True)
                row_info.label(text="当前: 0")
                row_info.label(text="/")
                row_info.label(text=f"场景最大: {scene_max_count}")

                col.separator()
                draw_empty_uv_list(col)
                col.separator()

                row_edit = col.row(align=True)
                row_edit.scale_y = 1.2
                row_edit.enabled = False
                row_edit.operator("uv_layer_manager.add", text="添加", icon='ADD')
                row_edit.operator("uv_layer_manager.delete", text="删除", icon='REMOVE')

                row_tools = col.row(align=True)
                row_tools.scale_y = 1.2
                row_tools.enabled = False
                row_tools.operator("uv_layer_manager.sync", text="同步UV", icon='PASTEDOWN')
                row_tools.operator("uv_layer_manager.select_max", text="选中最大模型", icon='OBJECT_DATA')
                return
            draw_uv_section(layout, context, obj, mesh)
        except Exception as e:
            layout.label(text=f"绘制错误: {e}", icon='ERROR')


class UV_LAYER_MANAGER_PT_modeling_panel(bpy.types.Panel):
    bl_label = "建模工具"
    bl_idname = "UV_LAYER_MANAGER_PT_modeling_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV"
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        try:
            draw_modeling_tools_section(layout, context)
        except Exception as e:
            layout.label(text=f"绘制错误: {e}", icon='ERROR')


class UV_LAYER_MANAGER_PT_material_panel(bpy.types.Panel):
    bl_label = "材质管理"
    bl_idname = "UV_LAYER_MANAGER_PT_material_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV"
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        try:
            draw_material_management_section(layout, context)
        except Exception as e:
            layout.label(text=f"绘制错误: {e}", icon='ERROR')


# ============================================================
# Menu
# ============================================================

class UV_LAYER_MANAGER_MT_shortcut_menu(bpy.types.Menu):
    bl_label = "UV Layer Manager"
    bl_idname = "UV_LAYER_MANAGER_MT_shortcut_menu"

    def draw(self, context):
        layout = self.layout

        layout.operator("uv_layer_manager.toggle_uv_editor", text="UV", icon='UV')
        layout.operator("uv_layer_manager.toggle_shader_editor", text="着色器", icon='NODETREE')

        layout.separator()

        for preset, label in (
            ('180', "法向 180"),
            ('30', "法向 30"),
            ('60', "法向 60"),
            ('90', "法向 90"),
        ):
            op = layout.operator("uv_layer_manager.set_normal_angle", text=label, icon='NORMALS_FACE')
            op.preset = preset

        layout.separator()

        layout.operator("uv_layer_manager.add", text="UV 添加", icon='ADD')
        layout.operator("uv_layer_manager.delete", text="UV 删除", icon='REMOVE')
        layout.operator("uv_layer_manager.sync", text="同步 UV", icon='PASTEDOWN')
        layout.operator("uv_layer_manager.select_max", text="选中最大模型", icon='OBJECT_DATA')

        layout.separator()

        layout.operator("uv_layer_manager.reset_uv_names", text="uv命名重置", icon='UV')
        layout.operator("uv_layer_manager.snap_close_vertices", text="合并相近", icon='AUTOMERGE_OFF')
        layout.operator("uv_layer_manager.rotate_linked_duplicate", text="旋转复制", icon='DUPLICATE')

        layout.separator()

        layout.operator("uv_layer_manager.add_material", text="新增材质", icon='ADD')
        layout.operator("uv_layer_manager.organize_materials", text="整理材质", icon='BRUSH_DATA')
        op_id = layout.operator("uv_layer_manager.toggle_vertex_color_view", text="材质ID", icon='COLOR')
        op_id.mode = 'ID'
        op_color = layout.operator("uv_layer_manager.toggle_vertex_color_view", text="顶点颜色", icon='GROUP_VCOL')
        op_color.mode = 'COLOR'
        op_alpha = layout.operator("uv_layer_manager.toggle_vertex_color_view", text="顶点alpha", icon='IMAGE_ALPHA')
        op_alpha.mode = 'ALPHA'


def draw_uv_layer_manager_shortcut_menu(self, context):
    self.layout.menu("UV_LAYER_MANAGER_MT_shortcut_menu", icon='UV')
