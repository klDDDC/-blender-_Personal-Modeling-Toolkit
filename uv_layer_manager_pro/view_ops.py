# -*- coding: utf-8 -*-
"""
UV Layer Manager - View Layout Toggle Operators
"""
import bpy
from . import constants as C
from . import layout as L


class UV_LAYER_MANAGER_OT_toggle_uv_editor(bpy.types.Operator):
    bl_idname = "uv_layer_manager.toggle_uv_editor"
    bl_label = "切换UV布局"
    bl_description = "切换UV编辑器布局：Shift+T"
    bl_options = {'REGISTER'}

    split_factor: bpy.props.FloatProperty(
        name="分割比例",
        default=0.4,
        min=0.2,
        max=0.8,
        description="兼容旧版调用；实际分割比例优先使用插件偏好设置"
    )

    def invoke(self, context, event):
        mgr = L.LayoutManager(C.LAYOUT_KIND_UV, "UV编辑器")
        if mgr.should_confirm_open(context):
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        mgr = L.LayoutManager(C.LAYOUT_KIND_UV, "UV编辑器")
        result = mgr.execute(context)
        if result == {'FINISHED'}:
            self.report({'INFO'}, "已切换UV布局")
        elif result == {'CANCELLED'}:
            self.report({'WARNING'}, "UV布局切换失败")
        return result


class UV_LAYER_MANAGER_OT_toggle_shader_editor(bpy.types.Operator):
    bl_idname = "uv_layer_manager.toggle_shader_editor"
    bl_label = "切换着色器布局"
    bl_description = "切换着色器编辑器布局"
    bl_options = {'REGISTER'}

    split_factor: bpy.props.FloatProperty(
        name="分割比例",
        default=0.4,
        min=0.2,
        max=0.8,
        description="兼容旧版调用；实际分割比例优先使用插件偏好设置"
    )

    def invoke(self, context, event):
        mgr = L.LayoutManager(C.LAYOUT_KIND_SHADER, "着色器编辑器")
        if mgr.should_confirm_open(context):
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        mgr = L.LayoutManager(C.LAYOUT_KIND_SHADER, "着色器编辑器")
        result = mgr.execute(context)
        if result == {'FINISHED'}:
            self.report({'INFO'}, "已切换着色器布局")
        elif result == {'CANCELLED'}:
            self.report({'WARNING'}, "着色器布局切换失败")
        return result
