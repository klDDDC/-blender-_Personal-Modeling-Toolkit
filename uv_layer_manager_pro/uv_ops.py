# -*- coding: utf-8 -*-
"""
UV Layer Manager - UV Layer Operators
"""
import bpy
from . import constants as C
from . import utils as U
from . import clipboard as CB


# ============================================================
# Operators - UV Layer Management
# ============================================================

class UV_LAYER_MANAGER_OT_add(bpy.types.Operator):
    bl_idname = "uv_layer_manager.add"
    bl_label = "添加UV层"
    bl_description = "添加新的UV层"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}
        mesh = obj.data
        uv_layers = mesh.uv_layers

        if len(uv_layers) >= C.MAX_UV_LAYERS:
            self.report({'WARNING'}, f"已达到最大UV层数限制（{C.MAX_UV_LAYERS}）")
            return {'CANCELLED'}

        new_name = U.generate_uv_name(uv_layers)
        new_uv = uv_layers.new(name=new_name)
        uv_layers.active_index = len(uv_layers) - 1

        self.report({'INFO'}, f"已添加UV层: {new_uv.name}")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_delete(bpy.types.Operator):
    bl_idname = "uv_layer_manager.delete"
    bl_label = "删除UV层"
    bl_description = "删除当前选中的UV层"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        return len(obj.data.uv_layers) > 1

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}
        mesh = obj.data
        uv_layers = mesh.uv_layers

        if len(uv_layers) <= 1:
            self.report({'WARNING'}, "至少需要保留一个UV层")
            return {'CANCELLED'}

        active_index = uv_layers.active_index
        active_name = uv_layers.active.name

        uv_layers.remove(uv_layers.active)

        if active_index >= len(uv_layers):
            uv_layers.active_index = len(uv_layers) - 1

        self.report({'INFO'}, f"已删除UV层: {active_name}")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_select(bpy.types.Operator):
    bl_idname = "uv_layer_manager.select"
    bl_label = "选择UV层"
    bl_description = "切换当前选中的UV层"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}
        mesh = obj.data
        uv_layers = mesh.uv_layers

        if self.index < 0 or self.index >= len(uv_layers):
            self.report({'WARNING'}, "无效的UV层索引")
            return {'CANCELLED'}

        target_name = uv_layers[self.index].name
        switched = 0
        skipped = 0
        touched_meshes = set()
        for selected_obj in U.get_selected_mesh_objects(context):
            selected_mesh = selected_obj.data
            if selected_mesh is None or selected_mesh.as_pointer() in touched_meshes:
                continue
            touched_meshes.add(selected_mesh.as_pointer())
            selected_uv_layers = selected_mesh.uv_layers
            if selected_uv_layers is None or len(selected_uv_layers) == 0:
                skipped += 1
                continue

            target_index = selected_uv_layers.find(target_name)
            if target_index < 0 and self.index < len(selected_uv_layers):
                target_index = self.index
            if target_index < 0:
                skipped += 1
                continue

            selected_uv_layers.active_index = target_index
            switched += 1

        if skipped:
            self.report({'INFO'}, f"已切换 {switched} 个模型UV层，跳过 {skipped} 个")
        else:
            self.report({'INFO'}, f"已切换 {switched} 个模型UV层")
        return {'FINISHED'}


# ============================================================
# Operators - UV Copy & Sync
# ============================================================

class UV_LAYER_MANAGER_OT_copy(bpy.types.Operator):
    bl_idname = "uv_layer_manager.copy"
    bl_label = "复制UV"
    bl_description = "复制此UV层的UV数据到剪贴板"
    bl_options = {'REGISTER'}

    index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}
        mesh = obj.data
        uv_layers = mesh.uv_layers

        if self.index < 0 or self.index >= len(uv_layers):
            self.report({'WARNING'}, "无效的UV层索引")
            return {'CANCELLED'}

        source = uv_layers[self.index]
        loop_count = len(mesh.loops)

        if loop_count == 0:
            self.report({'WARNING'}, "该网格没有循环数据")
            return {'CANCELLED'}

        uv_flat = [0.0] * (loop_count * 2)
        source.data.foreach_get("uv", uv_flat)

        CB.UVClipboard.copy(source.name, mesh.name, loop_count, uv_flat)

        self.report({'INFO'}, f"已复制UV层: {source.name}（{loop_count}个循环点）")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_sync(bpy.types.Operator):
    bl_idname = "uv_layer_manager.sync"
    bl_label = "同步UV"
    bl_description = "将剪贴板中的UV数据同步到当前选中的UV层"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return False
        if obj.data is None or obj.data.uv_layers is None:
            return False
        return CB.UVClipboard.has_data()

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}
        mesh = obj.data
        uv_layers = mesh.uv_layers
        target = uv_layers.active

        if target is None:
            self.report({'WARNING'}, "没有选中的UV层")
            return {'CANCELLED'}

        if not CB.UVClipboard.has_data():
            self.report({'WARNING'}, "剪贴板中没有UV数据，请先复制一个UV层")
            return {'CANCELLED'}

        if len(mesh.loops) != CB.UVClipboard.get_loop_count():
            self.report(
                {'ERROR'},
                f"拓扑结构不兼容！目标: {len(mesh.loops)} 循环点，源: {CB.UVClipboard.get_loop_count()} 循环点",
            )
            return {'CANCELLED'}

        source_name = CB.UVClipboard.get_source_name()
        target.data.foreach_set("uv", CB.UVClipboard.get_uv_data())
        mesh.update()

        self.report({'INFO'}, f"已将 {source_name} 的UV数据同步到 {target.name}")
        return {'FINISHED'}


# ============================================================
# Operators - Scene
# ============================================================

class UV_LAYER_MANAGER_OT_select_max(bpy.types.Operator):
    bl_idname = "uv_layer_manager.select_max"
    bl_label = "选中最大UV层模型"
    bl_description = "选中场景中拥有最多UV层的模型"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return U.get_scene_max_uv_info(context.scene)[0] > 0

    def execute(self, context):
        _, max_obj_name = U.get_scene_max_uv_info(context.scene)
        obj = bpy.data.objects.get(max_obj_name)
        if obj is None:
            self.report({'WARNING'}, f"未找到模型: {max_obj_name}")
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        self.report({'INFO'}, f"已选中模型: {max_obj_name}")
        return {'FINISHED'}
