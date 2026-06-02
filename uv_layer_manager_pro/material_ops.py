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
        U.remove_material_slot_from_object(obj, self.index)
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
        if obj and obj.type == 'MESH' and self.index < len(obj.data.materials):
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


class UV_LAYER_MANAGER_OT_clear_material_slots(bpy.types.Operator):
    bl_idname = "uv_layer_manager.clear_material_slots"
    bl_label = "清除材质槽"
    bl_description = "清除选中模型的全部材质槽"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        for obj in U.get_selected_mesh_objects(context):
            obj.data.materials.clear()
            obj.data.update()
        self.report({'INFO'}, "已清除材质槽")
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
    bl_description = "合并场景中同名的重复材质"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        merged = 0
        for obj in U.get_selected_mesh_objects(context):
            merged += U.merge_duplicate_material_slots(obj)
        self.report({'INFO'}, f"合并了 {merged} 个重复材质槽")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_organize_materials(bpy.types.Operator):
    bl_idname = "uv_layer_manager.organize_materials"
    bl_label = "整理材质"
    bl_description = "清理选中模型未使用材质槽，删除 .001/.002 等重复材质"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import re

        suffix_re = re.compile(r"(\.\d{3})+$")

        def base_name(name):
            while suffix_re.search(name):
                name = suffix_re.sub("", name)
            return name

        # ── 第一步：清理选中模型未使用的材质槽 ──
        removed_slots = 0
        for obj in U.get_selected_mesh_objects(context):
            removed_slots += U.remove_unused_material_slots(obj)

        # ── 第二步：把所有 .001 .002 材质按 basename 分组 ──
        groups = {}
        for mat in list(bpy.data.materials):
            clean = base_name(mat.name)
            if clean == mat.name:
                continue
            groups.setdefault(clean, []).append(mat)

        # ── 第三步：每组选一个 canonical，其余 → replace_map ──
        replace_map = {}
        canonical_set = set()
        for clean_name, candlist in groups.items():
            # 有 exact 名字的优先
            canonical = bpy.data.materials.get(clean_name)
            if canonical is None:
                canonical = sorted(candlist, key=lambda m: len(m.name))[0]
            canonical_set.add(canonical)
            for m in candlist:
                if m != canonical:
                    replace_map[m] = canonical

        print(f"[UVLM] 检测到重复材质: {len(replace_map)} 个")
        if replace_map:
            for dup, canon in replace_map.items():
                print(f"  {dup.name} (users={dup.users}) → {canon.name}")
        else:
            print(f"[UVLM] 无重复材质，跳过")

        replaced_slots = 0
        if replace_map:
            # ── 第四步：替换所有对象材质槽 ──
            for obj in bpy.data.objects:
                for slot in obj.material_slots:
                    if slot.material in replace_map:
                        print(f"[UVLM] 替换 {obj.name} 的材质槽: {slot.material.name} → {replace_map[slot.material].name}")
                        slot.material = replace_map[slot.material]
                        replaced_slots += 1

            # ── 第五步：替换所有 mesh 数据块材质槽 ──
            for mesh in bpy.data.meshes:
                for i, mat in enumerate(mesh.materials):
                    if mat in replace_map:
                        print(f"[UVLM] 替换 {mesh.name} mesh[{i}]: {mat.name} → {replace_map[mat].name}")
                        mesh.materials[i] = replace_map[mat]
                        replaced_slots += 1

            print(f"[UVLM] 替换完成: {replaced_slots} 个槽")

        # ── 第六步：合并选中模型内重复材质槽 ──
        merged_slots = 0
        for obj in U.get_selected_mesh_objects(context):
            merged_slots += U.merge_duplicate_material_slots(obj)
            removed_slots += U.remove_unused_material_slots(obj)

        # ── 第七步：删除重复材质（纯数据 API，不调 bpy.ops） ──
        removed_materials = 0
        # 收集所有需要检查的材质：replace_map 的 keys（被替换的重复材质）+
        # canonical_set 中 users==0 的（没有 base 材质时 canonical 也是残留）
        all_to_check = set(replace_map.keys())
        for canon in canonical_set:
            if canon.users == 0:
                all_to_check.add(canon)

        for mat in all_to_check:
            if mat.name not in bpy.data.materials:
                continue
            print(f"[UVLM] 尝试删除 {mat.name} (users={mat.users}, fake_user={mat.use_fake_user})")
            if mat.use_fake_user:
                mat.use_fake_user = False
            # 两轮尝试
            try:
                bpy.data.materials.remove(mat, do_unlink=True)
                removed_materials += 1
                print(f"  → 成功")
            except TypeError:
                try:
                    bpy.data.materials.remove(mat)
                    removed_materials += 1
                    print(f"  → 成功 (fallback)")
                except RuntimeError as e:
                    print(f"  → 失败: {e}")
            except RuntimeError as e:
                print(f"  → 失败: {e}")

        print(f"[UVLM] 删除完成: {removed_materials} 个材质")

        total_mats = len(bpy.data.materials)
        grouped = sum(1 for l in groups.values() if len(l) >= 2)
        self.report(
            {'INFO'},
            f"扫描 {total_mats} 个材质，{len(groups)} 组后缀，{grouped} 组≥2 | 替换 {replaced_slots} 槽 删除 {removed_materials} 材质",
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
        # ── 材质ID ──
        if self.mode == 'ID':
            updated, next_mode = VCN.set_material_view_mode(context, self.mode)
            label = "材质显示" if next_mode == 'MATERIAL' else "材质ID"
            self.report({'INFO'}, f"已切换到{label}，更新 {updated} 个3D视图")
            return {'FINISHED'}

        # ── 顶点颜色 / 顶点alpha ──
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "请选中一个网格模型")
            return {'CANCELLED'}

        if VCN.has_uvlm_vertex_color_nodes(obj):
            # 已有注入节点 → 清除并恢复原连接
            VCN._clear_selected_vertex_color_nodes(context)
            MID.restore_material_id_colors(context)
            L.tag_all_view3d_redraw()
            self.report({'INFO'}, "已恢复材质显示")
        else:
            # 无节点 → 注入
            MID.restore_material_id_colors(context)
            VCN._clear_selected_vertex_color_nodes(context)
            VCN._apply_vertex_color_nodes(context, self.mode)
            L.tag_all_view3d_redraw()
            label = "顶点alpha" if self.mode == 'ALPHA' else "顶点颜色"
            self.report({'INFO'}, f"已切换到{label}")

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
                scene = context.scene
                scene.material_view_mode = 'COLOR'
                VCN._clear_selected_vertex_color_nodes(context)
                VCN._apply_vertex_color_nodes(context, 'COLOR')
                L.tag_all_view3d_redraw()
                return {'FINISHED'}
        self.report({'WARNING'}, f"找不到颜色属性: {self.name}")
        return {'CANCELLED'}


# ============================================================
# Property registration
# ============================================================

def register_properties():
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
    if hasattr(bpy.types.Scene, 'material_manager_material'):
        del bpy.types.Scene.material_manager_material
    if hasattr(bpy.types.Scene, 'material_view_mode'):
        del bpy.types.Scene.material_view_mode
