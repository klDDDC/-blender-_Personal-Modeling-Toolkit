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
        item_col = layout.column(align=True)
        selected_face_material_index = U.get_selected_face_material_index_cached(context, data)
        if selected_face_material_index == index:
            item_col.alert = True

        material = item.material
        if material is not None:
            try:
                icon_value = MID.get_material_swatch_icon(material)
            except Exception:
                icon_value = 0
            name_row = item_col.row(align=True)
            name_row.scale_y = 1.05
            name_row.label(
                text="",
                icon_value=icon_value,
            )
            name_row.prop(material, "name", text="", emboss=False)
        else:
            empty_row = item_col.row(align=True)
            op_select = empty_row.operator(
                "uv_layer_manager.select_material_slot",
                text="空材质槽",
                icon='BLANK1',
                emboss=False,
            )
            op_select.index = index
            op_remove = empty_row.operator(
                "uv_layer_manager.remove_material_slot",
                text="",
                icon='REMOVE',
                emboss=False,
            )
            op_remove.index = index


class UV_LAYER_MANAGER_OT_toggle_material_group(bpy.types.Operator):
    bl_idname = "uv_layer_manager.toggle_material_group"
    bl_label = "展开材质组"
    bl_description = "展开或折叠同名材质组；不会合并或修改材质数据"
    bl_options = {'INTERNAL'}

    group_key: bpy.props.StringProperty()

    def execute(self, context):
        if self.group_key in C._material_group_expanded:
            C._material_group_expanded.remove(self.group_key)
        else:
            C._material_group_expanded.add(self.group_key)
        L.tag_all_view3d_redraw()
        return {'FINISHED'}


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


# ============================================================
# Section draw functions
# ============================================================

def draw_uv_section(layout, context, obj, mesh):
    layout.operator_context = 'INVOKE_DEFAULT'
    scene = context.scene
    scene_max_count, _ = U.get_scene_max_uv_info(scene)
    uv_count = len(mesh.uv_layers) if mesh and mesh.uv_layers else 0

    col = layout.column(align=True)
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


def draw_modeling_tools_section(layout, context):
    try:
        layout.operator_context = 'INVOKE_DEFAULT'
        scene = context.scene
        selected_mesh_count = len(U.get_selected_mesh_objects(context))

        col = layout.column(align=True)

        normal_title = col.row(align=True)
        normal_title.label(text="法向角度", icon='NORMALS_FACE')

        normal_row = col.row(align=True)
        normal_row.scale_y = 1.18
        for preset, label in (
            ('180', "180"),
            ('30', "30"),
            ('90', "90"),
        ):
            op = normal_row.operator(
                "uv_layer_manager.set_normal_angle",
                text=label,
                depress=scene.normal_angle_preset == preset,
            )
            op.preset = preset

        custom_value = normal_row.row(align=True)
        custom_value.alignment = 'CENTER'
        custom_value.label(text=f"{scene.normal_angle_custom:g}")
        op_custom = normal_row.operator(
            "uv_layer_manager.set_normal_angle",
            text="自定义",
            depress=scene.normal_angle_preset == C.NORMAL_ANGLE_PRESET_CUSTOM,
        )
        op_custom.preset = C.NORMAL_ANGLE_PRESET_CUSTOM

        if selected_mesh_count == 0:
            normal_row.enabled = False

        col.separator()

        tools_title = col.row(align=True)
        tools_title.label(text="建模操作", icon='TOOL_SETTINGS')

        tools = col.grid_flow(
            row_major=True,
            columns=2,
            even_columns=True,
            even_rows=True,
            align=True,
        )

        action_cell = tools.row(align=True)
        action_cell.scale_y = 1.25
        action_split = action_cell.split(factor=0.82, align=True)
        action_main = action_split.row(align=True)
        action_main.operator("uv_layer_manager.reset_uv_names", text="UV 命名重置", icon='UV')
        action_settings = action_split.row(align=True)
        action_settings.operator("uv_layer_manager.set_uv_naming", text="", icon='PREFERENCES')
        if selected_mesh_count == 0:
            action_main.enabled = False

        close_cell = tools.row(align=True)
        close_cell.scale_y = 1.25
        close_split = close_cell.split(factor=0.82, align=True)
        close_main = close_split.row(align=True)
        close_main.operator("uv_layer_manager.snap_close_vertices", text="合并相近", icon='AUTOMERGE_OFF')
        close_settings = close_split.row(align=True)
        close_settings.operator("uv_layer_manager.set_close_snap_distance", text="", icon='PREFERENCES')
        if selected_mesh_count == 0:
            close_main.enabled = False

        rotate_cell = tools.row(align=True)
        rotate_cell.scale_y = 1.25
        rotate_cell.operator("uv_layer_manager.rotate_linked_duplicate", text="旋转复制", icon='DUPLICATE')
        if selected_mesh_count == 0:
            rotate_cell.enabled = False

        ngon_cell = tools.row(align=True)
        ngon_cell.scale_y = 1.25
        ngon_cell.operator("uv_layer_manager.select_ngons", text="大于4边面", icon='SNAP_FACE')
        if selected_mesh_count == 0:
            ngon_cell.enabled = False

        quadify_cell = tools.row(align=True)
        quadify_cell.scale_y = 1.25
        quadify_cell.operator("uv_layer_manager.quadify_ngons", text="处理多边面", icon='MOD_TRIANGULATE')
        if selected_mesh_count == 0:
            quadify_cell.enabled = False

        overlap_cell = tools.row(align=True)
        overlap_cell.scale_y = 1.25
        overlap_cell.operator("uv_layer_manager.select_overlapping_faces", text="检查重叠面", icon='FACESEL')
        if selected_mesh_count == 0:
            overlap_cell.enabled = False

        angle_cell = tools.row(align=True)
        angle_cell.scale_y = 1.25
        angle_cell.operator("uv_layer_manager.select_by_angle", text="角度选择", icon='ORIENTATION_NORMAL')
        if selected_mesh_count == 0:
            angle_cell.enabled = False

        angle_settings = tools.row(align=True)
        angle_settings.scale_y = 1.25
        angle_threshold = getattr(scene, "uvlm_select_angle_threshold", 30.0)
        angle_settings.operator("uv_layer_manager.set_select_angle", text=f"{angle_threshold:g}°", icon='PREFERENCES')

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

        col = layout.column(align=True)

        toolbar = col.row(align=True)
        toolbar.label(text="材质槽", icon='MATERIAL')
        add_col = toolbar.column(align=True)
        add_col.operator("uv_layer_manager.add_material", text="", icon='ADD')
        add_col.enabled = bool(objects)

        material_row = col.column(align=True)
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
            # 多选：按显示名称族折叠；底层材质数据保持独立。
            sub = material_row.column(align=True)
            empty_objects = []
            for obj in objects:
                if not obj.material_slots:
                    empty_objects.append(obj)
            material_groups = U.build_material_display_groups(objects)

            for group in material_groups:
                members = group["members"]
                grouped = len(members) > 1
                group_col = sub.column(align=True)
                name_row = group_col.row(align=True)
                if grouped:
                    expanded = group["key"] in C._material_group_expanded
                    op_expand = name_row.operator(
                        "uv_layer_manager.toggle_material_group",
                        text="",
                        icon='DISCLOSURE_TRI_DOWN' if expanded else 'DISCLOSURE_TRI_RIGHT',
                        emboss=False,
                    )
                    op_expand.group_key = group["key"]
                    name_row.label(text=group["name"], icon='MATERIAL')
                else:
                    mat = members[0]["material"]
                    try:
                        group_icon = MID.get_material_swatch_icon(mat)
                    except Exception:
                        group_icon = 0
                    name_row.label(text="", icon_value=group_icon)
                    name_row.prop(mat, "name", text="", emboss=False)
                    op_remove = name_row.operator("uv_layer_manager.remove_material_by_name", text="", icon='X', emboss=False)
                    op_remove.material_name = mat.name

                if grouped and expanded:
                    for member in members:
                        mat = member["material"]
                        member_row = group_col.row(align=True)
                        member_row.separator(factor=1.0)
                        try:
                            member_icon = MID.get_material_swatch_icon(mat)
                        except Exception:
                            member_icon = 0
                        member_row.label(text="", icon_value=member_icon)
                        member_row.prop(mat, "name", text="", emboss=False)
                        member_row.label(text=f"{member['object_count']}物体/{member['slot_count']}槽")
                        op_remove = member_row.operator(
                            "uv_layer_manager.remove_material_by_name",
                            text="",
                            icon='X',
                            emboss=False,
                        )
                        op_remove.material_name = mat.name

            if empty_objects:
                row = sub.row(align=True)
                row.label(text=f"{len(empty_objects)} 个选中模型无材质槽", icon='BLANK1')
            if not material_groups:
                row = sub.row(align=True)
                row.label(text="所有选中模型均无材质", icon='MATERIAL')

        col.separator()
        view_title = col.row(align=True)
        view_title.label(text="显示与颜色", icon='COLOR')

        compact_row = col.row(align=True)
        compact_row.scale_y = 1.2
        compact_row.operator(
            "uv_layer_manager.organize_materials",
            text="清理材质槽",
            icon='BRUSH_DATA',
        )
        op_id = compact_row.operator(
            "uv_layer_manager.toggle_vertex_color_view",
            text="材质ID",
            icon='COLOR',
            depress=scene.material_view_mode == 'ID',
        )
        op_id.mode = 'ID'

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
        col = layout.column(align=True)
        if not C._addon_keymaps:
            col.label(text="快捷键槽位未注册，请重新启用插件", icon='ERROR')
            return

        assigned = [
            entry for entry in C._addon_keymaps
            if getattr(entry[1], "type", "NONE") != "NONE"
        ]
        summary_row = col.row(align=True)
        summary_row.label(text=f"已设置 {len(assigned)} / {len(C._addon_keymaps)}", icon='KEYINGSET')
        summary_row.prop(
            scene,
            "show_unassigned_shortcuts",
            text="显示未设置",
            toggle=True,
        )

        show_all = getattr(scene, "show_unassigned_shortcuts", False)
        visible = C._addon_keymaps if show_all else assigned
        if not visible:
            col.label(text="尚未设置快捷键，可勾选“显示未设置”后录入", icon='INFO')
            return

        for keymap, item, label in visible:
            row = col.row(align=True)
            row.label(text=label)
            SH.draw_shortcut_keymap_item(row, context, keymap, item)
    except Exception as e:
        layout.label(text=f"快捷键UI错误: {str(e)[:40]}", icon='ERROR')


def draw_layout_section(layout, context):
    try:
        layout.operator_context = 'INVOKE_DEFAULT'
        col = layout.column(align=True)

        uv_active = False
        shader_active = False
        managed_uv = False
        managed_shader = False
        if context.screen and context.screen.areas:
            managed_uv = L.get_managed_editor_area(context.screen, C.LAYOUT_KIND_UV) is not None
            managed_shader = L.get_managed_editor_area(context.screen, C.LAYOUT_KIND_SHADER) is not None
            uv_active = U.is_uv_edit_active(context)
            shader_active = U.is_shader_edit_active(context)
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
        _obj, mesh = U.get_active_mesh(context)
        uv_count = len(mesh.uv_layers) if mesh and mesh.uv_layers else 0
        scene_max_count, _ = U.get_scene_max_uv_info(context.scene)
        self.layout.label(text=f"{uv_count} / {scene_max_count}")

    def draw(self, context):
        layout = self.layout
        try:
            obj, mesh = U.get_active_mesh(context)
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

    def draw_header(self, context):
        selected_mesh_count = len(U.get_selected_mesh_objects(context))
        self.layout.label(text=f"已选 {selected_mesh_count} 个网格")

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

    def draw_header(self, context):
        objects = U.get_selected_mesh_objects(context)
        mode = "单" if len(objects) <= 1 else "多"
        self.layout.label(text=f"{mode}选 | {len(objects)}个模型")

    def draw(self, context):
        layout = self.layout
        try:
            draw_material_management_section(layout, context)
        except Exception as e:
            layout.label(text=f"绘制错误: {e}", icon='ERROR')


class UV_LAYER_MANAGER_PT_shortcut_panel(bpy.types.Panel):
    bl_label = "快捷键"
    bl_idname = "UV_LAYER_MANAGER_PT_shortcut_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV"
    bl_order = 4
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        self.layout.label(text="直接修改")

    def draw(self, context):
        layout = self.layout
        try:
            draw_shortcut_section(layout, context)
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
        if context.mode == 'EDIT_MESH':
            layout.operator("uv_layer_manager.select_by_angle", text="角度选择", icon='ORIENTATION_NORMAL')
            layout.operator("uv_layer_manager.select_ngons", text="选择多边面", icon='SNAP_FACE')
            return

        layout.operator("uv_layer_manager.toggle_uv_editor", text="UV 编辑布局", icon='UV')
        layout.operator("uv_layer_manager.toggle_shader_editor", text="着色器布局", icon='NODETREE')
        layout.separator()
        layout.operator("uv_layer_manager.reset_uv_names", text="重置 UV 命名", icon='UV')
        layout.operator("uv_layer_manager.snap_close_vertices", text="合并相近", icon='AUTOMERGE_OFF')
        layout.operator("uv_layer_manager.rotate_linked_duplicate", text="旋转复制", icon='DUPLICATE')
        layout.separator()
        layout.operator("uv_layer_manager.clean_normals", text="清理法向与切线", icon='NORMALS_FACE')
        layout.operator("uv_layer_manager.add_material", text="新增材质", icon='ADD')
        layout.operator("uv_layer_manager.organize_materials", text="安全清理材质槽", icon='BRUSH_DATA')


def draw_uv_layer_manager_shortcut_menu(self, context):
    self.layout.menu("UV_LAYER_MANAGER_MT_shortcut_menu", icon='UV')
