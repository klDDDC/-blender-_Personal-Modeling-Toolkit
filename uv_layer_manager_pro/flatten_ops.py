# -*- coding: utf-8 -*-
"""
UV Layer Manager - Flatten & Pin Operators
"""
import bpy
from . import utils as U


# ============================================================
# Operators - Flatten UV
# ============================================================

class UV_LAYER_MANAGER_OT_flatten_u(bpy.types.Operator):
    """将选中面的UV顶点沿U轴打平（U坐标设为平均值）"""
    bl_idname = "uv_layer_manager.flatten_u"
    bl_label = "打平U"
    bl_description = "将选中UV面的顶点U坐标设为平均值"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
            return False
        mesh = obj.data
        if mesh.uv_layers.active is None:
            return False
        return True

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        uv_layer = mesh.uv_layers.active
        if uv_layer is None or len(uv_layer.data) == 0:
            self.report({'WARNING'}, "没有UV数据")
            return {'CANCELLED'}
        uv_data = uv_layer.data

        # Collect UV loop indices from selected polygons
        selected_loops = []
        for poly in mesh.polygons:
            if not poly.select:
                continue
            for loop_idx in poly.loop_indices:
                selected_loops.append(loop_idx)

        if not selected_loops:
            self.report({'WARNING'}, "没有选中的面")
            return {'CANCELLED'}

        # Filter out pinned and unselected UV verts
        valid_loops = []
        total_u = 0.0
        for loop_idx in selected_loops:
            uv_loop = uv_data[loop_idx]
            if uv_loop.pin_select:
                continue
            if not uv_loop.select:
                continue
            valid_loops.append(loop_idx)
            total_u += uv_loop.uv.x

        if not valid_loops:
            self.report({'WARNING'}, "没有可操作的UV顶点")
            return {'CANCELLED'}

        avg_u = total_u / len(valid_loops)

        for loop_idx in valid_loops:
            uv_data[loop_idx].uv.x = avg_u

        mesh.update()
        self.report({'INFO'}, f"已将 {len(valid_loops)} 个顶点的U坐标打平到 {avg_u:.4f}")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_flatten_v(bpy.types.Operator):
    """将选中面的UV顶点沿V轴打平（V坐标设为平均值）"""
    bl_idname = "uv_layer_manager.flatten_v"
    bl_label = "打平V"
    bl_description = "将选中UV面的顶点V坐标设为平均值"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
            return False
        mesh = obj.data
        if mesh.uv_layers.active is None:
            return False
        return True

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        uv_layer = mesh.uv_layers.active
        if uv_layer is None or len(uv_layer.data) == 0:
            self.report({'WARNING'}, "没有UV数据")
            return {'CANCELLED'}
        uv_data = uv_layer.data

        # Collect UV loop indices from selected polygons
        selected_loops = []
        for poly in mesh.polygons:
            if not poly.select:
                continue
            for loop_idx in poly.loop_indices:
                selected_loops.append(loop_idx)

        if not selected_loops:
            self.report({'WARNING'}, "没有选中的面")
            return {'CANCELLED'}

        # Filter out pinned and unselected UV verts
        valid_loops = []
        total_v = 0.0
        for loop_idx in selected_loops:
            uv_loop = uv_data[loop_idx]
            if uv_loop.pin_select:
                continue
            if not uv_loop.select:
                continue
            valid_loops.append(loop_idx)
            total_v += uv_loop.uv.y

        if not valid_loops:
            self.report({'WARNING'}, "没有可操作的UV顶点")
            return {'CANCELLED'}

        avg_v = total_v / len(valid_loops)

        for loop_idx in valid_loops:
            uv_data[loop_idx].uv.y = avg_v

        mesh.update()
        self.report({'INFO'}, f"已将 {len(valid_loops)} 个顶点的V坐标打平到 {avg_v:.4f}")
        return {'FINISHED'}


# ============================================================
# Operators - Pin / Unpin UV Vertices
# ============================================================

class UV_LAYER_MANAGER_OT_pin_verts(bpy.types.Operator):
    """固定选中的UV顶点"""
    bl_idname = "uv_layer_manager.pin_verts"
    bl_label = "固定顶点"
    bl_description = "固定选中的UV顶点（pin_select = True）"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
            return False
        mesh = obj.data
        if mesh.uv_layers.active is None:
            return False
        return True

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        uv_layer = mesh.uv_layers.active
        uv_data = uv_layer.data

        pinned = 0
        for uv_loop in uv_data:
            if uv_loop.select:
                uv_loop.pin_select = True
                pinned += 1

        if pinned == 0:
            self.report({'WARNING'}, "没有选中的UV顶点")
            return {'CANCELLED'}

        mesh.update()
        self.report({'INFO'}, f"已固定 {pinned} 个UV顶点")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_unpin_verts(bpy.types.Operator):
    """取消固定选中的UV顶点"""
    bl_idname = "uv_layer_manager.unpin_verts"
    bl_label = "取消固定"
    bl_description = "取消固定选中的UV顶点（pin_select = False）"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
            return False
        mesh = obj.data
        if mesh.uv_layers.active is None:
            return False
        return True

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        uv_layer = mesh.uv_layers.active
        uv_data = uv_layer.data

        unpinned = 0
        for uv_loop in uv_data:
            if uv_loop.select:
                uv_loop.pin_select = False
                unpinned += 1

        if unpinned == 0:
            self.report({'WARNING'}, "没有选中的UV顶点")
            return {'CANCELLED'}

        mesh.update()
        self.report({'INFO'}, f"已取消固定 {unpinned} 个UV顶点")
        return {'FINISHED'}
