# -*- coding: utf-8 -*-
"""
UV Layer Manager - Material Operators
"""
import bpy
from . import constants as C
from . import utils as U
from . import material_id as MID
from . import vertex_color_nodes as VCN
from . import layout as L


class UV_LAYER_MANAGER_OT_assign_material(bpy.types.Operator):
    bl_idname = "uv_layer_manager.assign_material"
    bl_label = "赋予材质"
    bl_description = "将指定材质赋予给选中的模型"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        material = U.get_material_manager_target(context)
        if material is None:
            self.report({'WARNING'}, "请先选择一个材质")
            return {'CANCELLED'}
        objects = U.get_selected_mesh_objects(context)
        assigned_objects, selected_faces = U.assign_material_to_selected_faces_or_object(context, objects, material)
        if selected_faces:
            self.report({'INFO'}, f"已将 {material.name} 赋予 {selected_faces} 个选中面")
        else:
            self.report({'INFO'}, f"已将 {material.name} 赋予 {assigned_objects} 个模型")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_remove_material(bpy.types.Operator):
    bl_idname = "uv_layer_manager.remove_material"
    bl_label = "移除材质"
    bl_description = "从选中模型移除指定材质槽"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        material = U.get_material_manager_target(context)
        if material is None:
            self.report({'WARNING'}, "请先选择一个材质")
            return {'CANCELLED'}
        removed_count = 0
        for obj in U.get_selected_mesh_objects(context):
            removed_count += U.remove_material_from_object(obj, material)
        self.report({'INFO'}, f"已移除 {removed_count} 个材质槽")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_remove_material_by_name(bpy.types.Operator):
    bl_idname = "uv_layer_manager.remove_material_by_name"
    bl_label = "移除材质"
    bl_description = "从当前选中模型中移除指定材质"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        material = bpy.data.materials.get(self.material_name)
        if material is None:
            self.report({'WARNING'}, "找不到材质")
            return {'CANCELLED'}
        removed_count = 0
        for obj in U.get_selected_mesh_objects(context):
            removed_count += U.remove_material_from_object(obj, material)
        self.report({'INFO'}, f"已从选中模型移除 {removed_count} 个 {material.name} 材质槽")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_add_material(bpy.types.Operator):
    bl_idname = "uv_layer_manager.add_material"
    bl_label = "新增材质"
    bl_description = "为当前模型新增一个材质槽和材质"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "请至少选中一个网格模型")
            return {'CANCELLED'}
        active = context.active_object
        obj = active if active and active.type == 'MESH' else objects[0]
        material = bpy.data.materials.new(name=f"{obj.name}_Material")
        material.use_nodes = True
        MID.ensure_material_swatch_order(material)
        for o in objects:
            o.data.materials.append(material)
            o.active_material_index = len(o.data.materials) - 1
        context.scene.material_manager_material = material
        self.report({'INFO'}, f"已为 {len(objects)} 个模型新增材质: {material.name}")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_remove_material_slot(bpy.types.Operator):
    bl_idname = "uv_layer_manager.remove_material_slot"
    bl_label = "移除材质槽"
    bl_description = "移除指定的材质槽"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()
    target_object: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type == 'MESH':
            return len(context.active_object.data.materials) > 0
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        if self.target_object:
            obj = bpy.data.objects.get(self.target_object)
        else:
            obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}
        if not U.remove_material_slot_from_object(obj, self.index):
            self.report({'WARNING'}, "无效的材质槽索引")
            return {'CANCELLED'}
        self.report({'INFO'}, f"已移除 {obj.name} 的材质槽 {self.index}")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_select_material_slot(bpy.types.Operator):
    bl_idname = "uv_layer_manager.select_material_slot"
    bl_label = "选中材质槽"
    bl_description = "选中指定材质槽"
    bl_options = {'REGISTER'}

    index: bpy.props.IntProperty()
    target_object: bpy.props.StringProperty(default="")

    def execute(self, context):
        if self.target_object:
            obj = bpy.data.objects.get(self.target_object)
        else:
            obj = context.active_object
        if obj and obj.type == 'MESH' and 0 <= self.index < len(obj.data.materials):
            obj.active_material_index = self.index
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_assign_material_slot(bpy.types.Operator):
    bl_idname = "uv_layer_manager.assign_material_slot"
    bl_label = "赋予材质槽"
    bl_description = "将指定材质槽赋予选中面"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()
    target_object: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        if self.target_object:
            obj = bpy.data.objects.get(self.target_object)
        else:
            obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}
        if self.index < 0 or self.index >= len(obj.data.materials):
            return {'CANCELLED'}
        material = obj.data.materials[self.index]
        if material is None:
            return {'CANCELLED'}
        context.scene.material_manager_material = material
        return bpy.ops.uv_layer_manager.assign_material('EXEC_DEFAULT')


class UV_LAYER_MANAGER_OT_edit_material_base_color(bpy.types.Operator):
    bl_idname = "uv_layer_manager.edit_material_base_color"
    bl_label = "编辑基色"
    bl_description = "编辑选中材质的基础色"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return U.get_material_manager_target(context) is not None

    def execute(self, context):
        material = U.get_material_manager_target(context)
        if material is None:
            return {'CANCELLED'}
        inputs = MID.get_principled_base_color_inputs(material)
        if not inputs:
            return {'CANCELLED'}
        for base_input in inputs:
            base_input.default_value = (0.8, 0.8, 0.8, 1.0)
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_toggle_material_id_color(bpy.types.Operator):
    bl_idname = "uv_layer_manager.toggle_material_id_color"
    bl_label = "材质ID颜色"
    bl_description = "切换材质ID颜色"
    bl_options = {'REGISTER'}

    index: bpy.props.IntProperty()
    target_object: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        if self.target_object:
            obj = bpy.data.objects.get(self.target_object)
        else:
            obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}
        if self.index >= len(obj.data.materials):
            return {'CANCELLED'}
        material = obj.data.materials[self.index]
        if material is None:
            return {'CANCELLED'}
        MID.toggle_single_material_id_color(context, material, self.index)
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_edit_material_id_color(bpy.types.Operator):
    bl_idname = "uv_layer_manager.edit_material_id_color"
    bl_label = "编辑ID颜色"
    bl_description = "为材质选择材质ID展示颜色"
    bl_options = {'REGISTER'}

    index: bpy.props.IntProperty()

    def invoke(self, context, event):
        obj = context.active_object
        if self.index >= len(obj.data.materials):
            return {'CANCELLED'}
        material = obj.data.materials[self.index]
        if material is None:
            return {'CANCELLED'}
        wm = context.window_manager
        wm.uvlm_id_edit_color = tuple(material.uvlm_id_color)
        wm.uvlm_id_original_color = tuple(material.uvlm_id_color)
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.prop(context.window_manager, "uvlm_id_edit_color", text="")
        layout.separator()
        layout.label(text="预设颜色:")
        material = None
        if self.index < len(context.active_object.data.materials):
            material = context.active_object.data.materials[self.index]
        current_color = tuple(material.uvlm_id_color) if material else tuple(context.window_manager.uvlm_id_edit_color)
        palette = layout.column(align=True)
        for row_index in range(C.ID_COLOR_ROWS):
            row = palette.row(align=True)
            row.scale_x = 1.8
            row.scale_y = 1.18
            for column_index in range(C.ID_COLOR_COLUMNS):
                index = row_index * C.ID_COLOR_COLUMNS + column_index
                color = getattr(context.window_manager, f"uvlm_id_preset_{index}", (1.0, 1.0, 1.0, 1.0))
                preset_color = tuple(color)
                is_selected = all(abs(current_color[i] - preset_color[i]) <= 0.001 for i in range(4))
                op = row.operator(
                    "uv_layer_manager.set_material_id_preset",
                    text="",
                    emboss=True,
                    depress=is_selected,
                    icon_value=MID.get_color_preview_icon(preset_color, f"preset_{index}"),
                )
                op.index = self.index
                op.preset_index = index

        if material:
            layout.separator()
            row = layout.row(align=True)
            row.prop(material, "uvlm_id_color_is_custom", text="使用自定义颜色")

    def execute(self, context):
        obj = context.active_object
        if self.index >= len(obj.data.materials):
            return {'CANCELLED'}
        material = obj.data.materials[self.index]
        if material is None:
            return {'CANCELLED'}
        material.uvlm_id_color = tuple(context.window_manager.uvlm_id_edit_color)
        material.uvlm_id_color_is_custom = True
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_set_material_id_preset(bpy.types.Operator):
    bl_idname = "uv_layer_manager.set_material_id_preset"
    bl_label = "设置材质ID预设"
    bl_description = "选择预设颜色作为材质ID颜色"
    bl_options = {'REGISTER'}

    index: bpy.props.IntProperty()
    preset_index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}
        if self.index < 0 or self.index >= len(obj.data.materials):
            return {'CANCELLED'}
        material = obj.data.materials[self.index]
        if material is None:
            return {'CANCELLED'}
        if self.preset_index < 0 or self.preset_index >= C.ID_COLOR_PRESET_COUNT:
            self.report({'WARNING'}, "无效的材质ID预设索引")
            return {'CANCELLED'}
        color = getattr(context.window_manager, f"uvlm_id_preset_{self.preset_index}", None)
        if color:
            material.uvlm_id_color = tuple(color)
            context.window_manager.uvlm_id_edit_color = tuple(color)
            material.uvlm_id_color_is_custom = False
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_edit_material_id_color_for_target(bpy.types.Operator):
    """多物体模式下的 ID 颜色编辑：先切换 active object 再打开原始对话框."""
    bl_idname = "uv_layer_manager.edit_material_id_color_for_target"
    bl_label = "编辑ID颜色"
    bl_description = "为指定模型的材质选择材质ID展示颜色"
    bl_options = {'REGISTER'}

    index: bpy.props.IntProperty()
    target_object: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        if not self.target_object:
            return bpy.ops.uv_layer_manager.edit_material_id_color('INVOKE_DEFAULT', index=self.index)
        target = bpy.data.objects.get(self.target_object)
        if target is None or target.type != 'MESH':
            return {'CANCELLED'}
        prev_active = context.view_layer.objects.active
        try:
            context.view_layer.objects.active = target
            bpy.ops.uv_layer_manager.edit_material_id_color('INVOKE_DEFAULT', index=self.index)
        finally:
            if prev_active and prev_active.name in context.scene.objects:
                context.view_layer.objects.active = prev_active
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_replace_material(bpy.types.Operator):
    bl_idname = "uv_layer_manager.replace_material"
    bl_label = "材质操作"
    bl_description = "将选中模型中的当前材质替换为另一个材质"
    bl_options = {'REGISTER', 'UNDO'}

    source_material_name: bpy.props.StringProperty(default="")
    source_library_path: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return bool(U.get_selected_mesh_objects(context))

    def _source_material(self):
        return U.find_material(self.source_material_name, self.source_library_path)

    def invoke(self, context, event):
        source_material = self._source_material()
        if source_material is None:
            self.report({'WARNING'}, "源材质已不存在")
            return {'CANCELLED'}
        U.clear_material_replace_target(context)
        return context.window_manager.invoke_props_dialog(
            self,
            width=420,
            title="材质操作",
            confirm_text="替换",
        )

    def draw(self, context):
        layout = self.layout
        source_material = self._source_material()
        source_row = layout.row(align=True)
        try:
            source_icon = MID.get_material_swatch_icon(source_material) if source_material else 0
        except Exception:
            source_icon = 0
        source_row.label(text="", icon_value=source_icon)
        source_row.label(
            text=f"当前材质：{source_material.name}" if source_material else "当前材质已不存在",
        )

        select_operator = layout.operator(
            "uv_layer_manager.select_material_faces",
            text="选中该材质的所有面",
            icon='FACESEL',
        )
        select_operator.material_name = self.source_material_name
        select_operator.material_library_path = self.source_library_path

        layout.separator()
        layout.prop_search(
            context.window_manager,
            "uvlm_material_replace_target",
            bpy.data,
            "materials",
            text="替换为",
        )

    def execute(self, context):
        window_manager = context.window_manager
        target_material = getattr(window_manager, "uvlm_material_replace_target", None)
        try:
            source_material = self._source_material()
            if source_material is None:
                self.report({'WARNING'}, "源材质已不存在")
                return {'CANCELLED'}
            if target_material is None:
                self.report({'WARNING'}, "请选择替换后的材质")
                return {'CANCELLED'}
            if U.is_same_material(source_material, target_material):
                self.report({'INFO'}, "源材质和目标材质相同，未进行替换")
                return {'CANCELLED'}

            replaced_slots, changed_objects = U.replace_material_slots(
                U.get_selected_mesh_objects(context),
                source_material,
                target_material,
            )
            if not replaced_slots:
                self.report({'WARNING'}, "选中模型中没有使用该源材质的槽")
                return {'CANCELLED'}

            L.tag_all_view3d_redraw()
            self.report(
                {'INFO'},
                f"已在 {changed_objects} 个模型中替换 {replaced_slots} 个材质槽",
            )
            return {'FINISHED'}
        finally:
            U.clear_material_replace_target(context)

    def cancel(self, context):
        U.clear_material_replace_target(context)


class UV_LAYER_MANAGER_OT_select_material_faces(bpy.types.Operator):
    bl_idname = "uv_layer_manager.select_material_faces"
    bl_label = "选中材质的所有面"
    bl_description = "在当前选中的所有网格模型中选择使用该材质的面"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: bpy.props.StringProperty(default="")
    material_library_path: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return bool(U.get_selected_mesh_objects(context))

    def execute(self, context):
        material = U.find_material(self.material_name, self.material_library_path)
        if material is None:
            self.report({'WARNING'}, "材质已不存在")
            return {'CANCELLED'}

        selected_faces, matched_objects = U.select_material_faces(
            context,
            U.get_selected_mesh_objects(context),
            material,
        )
        L.tag_all_view3d_redraw()
        if not selected_faces:
            self.report({'INFO'}, "选中模型中没有使用该材质的面")
            return {'FINISHED'}
        self.report(
            {'INFO'},
            f"已在 {matched_objects} 个模型中选中 {selected_faces} 个面",
        )
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_clear_material_slots(bpy.types.Operator):
    bl_idname = "uv_layer_manager.clear_material_slots"
    bl_label = "清除材质槽"
    bl_description = "清除选中模型的全部材质槽"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        cleared_slots = 0
        processed_meshes = set()
        for obj in objects:
            mesh_pointer = obj.data.as_pointer()
            if mesh_pointer in processed_meshes:
                continue
            processed_meshes.add(mesh_pointer)
            cleared_slots += len(obj.data.materials)
            obj.data.materials.clear()
            obj.data.update()
        deleted_materials = U.purge_unused_duplicate_materials(context)
        U.invalidate_duplicate_material_cache()
        self.report(
            {'INFO'},
            f"已清除 {cleared_slots} 个材质槽，删除 {deleted_materials} 个未使用重复材质",
        )
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_clean_unused_material_slots(bpy.types.Operator):
    bl_idname = "uv_layer_manager.clean_unused_material_slots"
    bl_label = "清理未用材质槽"
    bl_description = "从选中模型移除所有未使用的材质槽"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        removed = 0
        for obj in U.get_selected_mesh_objects(context):
            removed += U.remove_unused_material_slots(obj)
        self.report({'INFO'}, f"清理了 {removed} 个未使用的材质槽")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_merge_duplicate_materials(bpy.types.Operator):
    bl_idname = "uv_layer_manager.merge_duplicate_materials"
    bl_label = "合并重复材质"
    bl_description = "合并选中模型中指向同一个材质数据块的重复材质槽"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        merged_slots = 0
        processed_meshes = set()
        for obj in U.get_selected_mesh_objects(context):
            mesh_pointer = obj.data.as_pointer()
            if mesh_pointer in processed_meshes:
                continue
            processed_meshes.add(mesh_pointer)
            merged_slots += U.merge_duplicate_material_slots(obj)
        U.invalidate_duplicate_material_cache()
        self.report({'INFO'}, f"合并了 {merged_slots} 个重复材质槽")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_organize_materials(bpy.types.Operator):
    bl_idname = "uv_layer_manager.organize_materials"
    bl_label = "整理材质"
    bl_description = "清理选中模型的未使用/重复材质槽，并删除全文件中真正未使用的数字后缀重复材质"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(U.get_selected_mesh_objects(context))

    def execute(self, context):
        removed_slots = 0
        merged_slots = 0
        processed_meshes = set()
        for obj in U.get_selected_mesh_objects(context):
            mesh_pointer = obj.data.as_pointer()
            if mesh_pointer in processed_meshes:
                continue
            processed_meshes.add(mesh_pointer)
            removed_slots += U.remove_unused_material_slots(obj)
            merged_slots += U.merge_duplicate_material_slots(obj)
            removed_slots += U.remove_unused_material_slots(obj)
        deleted_materials = U.purge_unused_duplicate_materials(context)
        U.invalidate_duplicate_material_cache()
        self.report(
            {'INFO'},
            f"安全清理完成：移除 {removed_slots} 个未使用槽，"
            f"合并 {merged_slots} 个重复槽，删除 {deleted_materials} 个未使用重复材质",
        )
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_toggle_vertex_color_view(bpy.types.Operator):
    bl_idname = "uv_layer_manager.toggle_vertex_color_view"
    bl_label = "顶点颜色显示"
    bl_description = "切换顶点颜色、顶点alpha和材质显示"
    bl_options = {'REGISTER'}

    mode: bpy.props.EnumProperty(
        items=(
            ('COLOR', "顶点颜色", "显示顶点颜色"),
            ('ALPHA', "顶点alpha", "显示顶点颜色alpha通道"),
            ('ID', "材质ID", "用纯色显示选中模型材质分配"),
        ),
        default='COLOR',
    )

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "请选中一个网格模型")
            return {'CANCELLED'}

        updated, next_mode = VCN.set_material_view_mode(context, self.mode)
        labels = {'MATERIAL': '材质显示', 'ID': '材质ID', 'COLOR': '顶点颜色', 'ALPHA': '顶点alpha'}
        L.tag_all_view3d_redraw()
        self.report({'INFO'}, f"已切换到{labels[next_mode]}，更新 {updated} 个3D视图")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_set_color_attribute(bpy.types.Operator):
    bl_idname = "uv_layer_manager.set_color_attribute"
    bl_label = "切换颜色属性"
    bl_description = "切换当前模型正在查看的颜色属性"
    bl_options = {'REGISTER'}

    name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and hasattr(obj.data, "color_attributes")

    def execute(self, context):
        mesh = context.active_object.data
        color_attributes = mesh.color_attributes
        for index, attribute in enumerate(color_attributes):
            if attribute.name == self.name:
                color_attributes.active_color_index = index
                VCN.set_material_view_mode(context, 'COLOR', force=True)
                L.tag_all_view3d_redraw()
                return {'FINISHED'}
        self.report({'WARNING'}, f"找不到颜色属性: {self.name}")
        return {'CANCELLED'}


# ============================================================
# Property registration
# ============================================================

def register_properties():
    bpy.types.WindowManager.uvlm_material_replace_target = bpy.props.PointerProperty(
        name="替换材质",
        description="材质操作弹窗中临时选择的目标材质",
        type=bpy.types.Material,
    )
    bpy.types.Scene.material_manager_material = bpy.props.PointerProperty(
        name="材质",
        description="材质管理工具使用的目标材质",
        type=bpy.types.Material,
    )
    bpy.types.Scene.material_view_mode = bpy.props.EnumProperty(
        name="材质查看模式",
        items=(
            ('MATERIAL', "材质", "正常材质显示"),
            ('COLOR', "顶点颜色", "显示顶点颜色"),
            ('ALPHA', "顶点alpha", "显示顶点alpha"),
            ('ID', "材质ID", "用纯色显示材质分配"),
            ('SINGLE_ID', "单材质ID", "只显示部分材质ID色"),
        ),
        default='MATERIAL',
    )


def unregister_properties():
    U.clear_material_replace_target()
    if hasattr(bpy.types.WindowManager, 'uvlm_material_replace_target'):
        del bpy.types.WindowManager.uvlm_material_replace_target
    if hasattr(bpy.types.Scene, 'material_manager_material'):
        del bpy.types.Scene.material_manager_material
    if hasattr(bpy.types.Scene, 'material_view_mode'):
        del bpy.types.Scene.material_view_mode
