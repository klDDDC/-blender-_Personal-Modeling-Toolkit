# -*- coding: utf-8 -*-
"""
UV Layer Manager - Addon Preferences
"""
import bpy


class UV_LAYER_MANAGER_prefs(bpy.types.AddonPreferences):
    bl_idname = "uv_layer_manager_pro"

    confirm_open: bpy.props.BoolProperty(
        name="打开时确认",
        description="打开UV编辑器前显示确认对话框",
        default=False,
    )

    auto_merge: bpy.props.BoolProperty(
        name="自动合并视图",
        description="关闭UV编辑器时自动合并回单一3D视图",
        default=True,
    )

    protect_uv_area: bpy.props.BoolProperty(
        name="保护UV编辑区域",
        description="防止UV编辑器区域被意外切换为其他编辑器类型",
        default=True,
    )

    view_split_ratio: bpy.props.FloatProperty(
        name="主视图占比",
        description="兼容旧版设置；UV和着色器布局现在固定为编辑器左侧30%",
        default=0.6,
        min=0.3,
        max=0.7,
        step=0.05,
    )

    uv_on_left: bpy.props.BoolProperty(
        name="编辑器在左侧",
        description="兼容旧版设置；UV和着色器布局现在固定为编辑器左侧30%",
        default=True,
    )

    shortcut_overrides: bpy.props.StringProperty(
        name="快捷键配置",
        description="自动持久化保存的版本化快捷键配置（JSON）",
        default="",
        options={'HIDDEN'},
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="UV Editor")
        box.prop(self, "confirm_open")
        box.prop(self, "auto_merge")
        box.prop(self, "protect_uv_area")

        box = layout.box()
        box.label(text="Layout")
        box.prop(self, "uv_on_left")
        box.prop(self, "view_split_ratio")
