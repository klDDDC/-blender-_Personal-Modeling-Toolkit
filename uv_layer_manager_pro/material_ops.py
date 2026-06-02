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
    bl_label = "璧嬩簣鏉愯川"
    bl_description = "灏嗘寚瀹氭潗璐ㄨ祴浜堢粰閫変腑鐨勬ā鍨?
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        material = U.get_material_manager_target(context)
        if material is None:
            self.report({'WARNING'}, "璇峰厛閫夋嫨涓€涓潗璐?)
            return {'CANCELLED'}
        objects = U.get_selected_mesh_objects(context)
        assigned_objects, selected_faces = U.assign_material_to_selected_faces_or_object(context, objects, material)
        if selected_faces:
            self.report({'INFO'}, f"宸插皢 {material.name} 璧嬩簣 {selected_faces} 涓€変腑闈?)
        else:
            self.report({'INFO'}, f"宸插皢 {material.name} 璧嬩簣 {assigned_objects} 涓ā鍨?)
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_remove_material(bpy.types.Operator):
    bl_idname = "uv_layer_manager.remove_material"
    bl_label = "绉婚櫎鏉愯川"
    bl_description = "浠庨€変腑妯″瀷绉婚櫎鎸囧畾鏉愯川妲?
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        material = U.get_material_manager_target(context)
        if material is None:
            self.report({'WARNING'}, "璇峰厛閫夋嫨涓€涓潗璐?)
            return {'CANCELLED'}
        removed_count = 0
        for obj in U.get_selected_mesh_objects(context):
            removed_count += U.remove_material_from_object(obj, material)
        self.report({'INFO'}, f"宸茬Щ闄?{removed_count} 涓潗璐ㄦЫ")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_remove_material_by_name(bpy.types.Operator):
    bl_idname = "uv_layer_manager.remove_material_by_name"
    bl_label = "绉婚櫎鏉愯川"
    bl_description = "浠庡綋鍓嶉€変腑妯″瀷涓Щ闄ゆ寚瀹氭潗璐?
    bl_options = {'REGISTER', 'UNDO'}

    material_name: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        material = bpy.data.materials.get(self.material_name)
        if material is None:
            self.report({'WARNING'}, "鎵句笉鍒版潗璐?)
            return {'CANCELLED'}
        removed_count = 0
        for obj in U.get_selected_mesh_objects(context):
            removed_count += U.remove_material_from_object(obj, material)
        self.report({'INFO'}, f"宸蹭粠閫変腑妯″瀷绉婚櫎 {removed_count} 涓?{material.name} 鏉愯川妲?)
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_add_material(bpy.types.Operator):
    bl_idname = "uv_layer_manager.add_material"
    bl_label = "鏂板鏉愯川"
    bl_description = "涓哄綋鍓嶆ā鍨嬫柊澧炰竴涓潗璐ㄦЫ鍜屾潗璐?
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "璇疯嚦灏戦€変腑涓€涓綉鏍兼ā鍨?)
            return {'CANCELLED'}
        active = context.active_object
        obj = active if active and active.type == 'MESH' else objects[0]
        material = bpy.data.materials.new(name=f"{obj.name}_Material")
        material.use_nodes = True
        for o in objects:
            o.data.materials.append(material)
            o.active_material_index = len(o.data.materials) - 1
        context.scene.material_manager_material = material
        self.report({'INFO'}, f"宸蹭负 {len(objects)} 涓ā鍨嬫柊澧炴潗璐? {material.name}")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_remove_material_slot(bpy.types.Operator):
    bl_idname = "uv_layer_manager.remove_material_slot"
    bl_label = "绉婚櫎鏉愯川妲?
    bl_description = "绉婚櫎鎸囧畾鐨勬潗璐ㄦЫ"
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
        self.report({'INFO'}, f"宸茬Щ闄?{obj.name} 鐨勬潗璐ㄦЫ {self.index}")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_select_material_slot(bpy.types.Operator):
    bl_idname = "uv_layer_manager.select_material_slot"
    bl_label = "閫変腑鏉愯川妲?
    bl_description = "閫変腑鎸囧畾鏉愯川妲?
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
    bl_label = "璧嬩簣鏉愯川妲?
    bl_description = "灏嗘寚瀹氭潗璐ㄦЫ璧嬩簣閫変腑闈?
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
    bl_label = "缂栬緫鍩鸿壊"
    bl_description = "缂栬緫閫変腑鏉愯川鐨勫熀纭€鑹?
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
    bl_label = "鏉愯川ID棰滆壊"
    bl_description = "鍒囨崲鏉愯川ID棰滆壊"
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
    bl_label = "缂栬緫ID棰滆壊"
    bl_description = "涓烘潗璐ㄩ€夋嫨鏉愯川ID灞曠ず棰滆壊"
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
        layout.label(text="棰勮棰滆壊:")
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
            row.prop(material, "uvlm_id_color_is_custom", text="浣跨敤鑷畾涔夐鑹?)

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
    bl_label = "璁剧疆鏉愯川ID棰勮"
    bl_description = "閫夋嫨棰勮棰滆壊浣滀负鏉愯川ID棰滆壊"
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
            self.report({'WARNING'}, "鏃犳晥鐨勬潗璐↖D棰勮绱㈠紩")
            return {'CANCELLED'}
        color = getattr(context.window_manager, f"uvlm_id_preset_{self.preset_index}", None)
        if color:
            material.uvlm_id_color = tuple(color)
            context.window_manager.uvlm_id_edit_color = tuple(color)
            material.uvlm_id_color_is_custom = False
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_edit_material_id_color_for_target(bpy.types.Operator):
    """澶氱墿浣撴ā寮忎笅鐨?ID 棰滆壊缂栬緫锛氬厛鍒囨崲 active object 鍐嶆墦寮€鍘熷瀵硅瘽妗?"""
    bl_idname = "uv_layer_manager.edit_material_id_color_for_target"
    bl_label = "缂栬緫ID棰滆壊"
    bl_description = "涓烘寚瀹氭ā鍨嬬殑鏉愯川閫夋嫨鏉愯川ID灞曠ず棰滆壊"
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
    bl_label = "娓呴櫎鏉愯川妲?
    bl_description = "娓呴櫎閫変腑妯″瀷鐨勫叏閮ㄦ潗璐ㄦЫ"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        for obj in U.get_selected_mesh_objects(context):
            obj.data.materials.clear()
            obj.data.update()
        self.report({'INFO'}, "宸叉竻闄ゆ潗璐ㄦЫ")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_clean_unused_material_slots(bpy.types.Operator):
    bl_idname = "uv_layer_manager.clean_unused_material_slots"
    bl_label = "娓呯悊鏈敤鏉愯川妲?
    bl_description = "浠庨€変腑妯″瀷绉婚櫎鎵€鏈夋湭浣跨敤鐨勬潗璐ㄦЫ"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        removed = 0
        for obj in U.get_selected_mesh_objects(context):
            removed += U.remove_unused_material_slots(obj)
        self.report({'INFO'}, f"娓呯悊浜?{removed} 涓湭浣跨敤鐨勬潗璐ㄦЫ")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_merge_duplicate_materials(bpy.types.Operator):
    bl_idname = "uv_layer_manager.merge_duplicate_materials"
    bl_label = "鍚堝苟閲嶅鏉愯川"
    bl_description = "鍚堝苟鍦烘櫙涓悓鍚嶇殑閲嶅鏉愯川"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        merged = 0
        for obj in U.get_selected_mesh_objects(context):
            merged += U.merge_duplicate_material_slots(obj)
        self.report({'INFO'}, f"鍚堝苟浜?{merged} 涓噸澶嶆潗璐ㄦЫ")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_organize_materials(bpy.types.Operator):
    bl_idname = "uv_layer_manager.organize_materials"
    bl_label = "鏁寸悊鏉愯川"
    bl_description = "娓呯悊閫変腑妯″瀷鏈娇鐢ㄦ潗璐ㄦЫ锛屽垹闄?.001/.002 绛夐噸澶嶆潗璐?
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import re

        suffix_re = re.compile(r"(\.\d{3})+$")

        def base_name(name):
            while suffix_re.search(name):
                name = suffix_re.sub("", name)
            return name

        # 鈹€鈹€ 绗竴姝ワ細娓呯悊閫変腑妯″瀷鏈娇鐢ㄧ殑鏉愯川妲?鈹€鈹€
        removed_slots = 0
        for obj in U.get_selected_mesh_objects(context):
            removed_slots += U.remove_unused_material_slots(obj)

        # 鈹€鈹€ 绗簩姝ワ細鎶婃墍鏈?.001 .002 鏉愯川鎸?basename 鍒嗙粍 鈹€鈹€
        groups = {}
        for mat in list(bpy.data.materials):
            clean = base_name(mat.name)
            if clean == mat.name:
                continue
            groups.setdefault(clean, []).append(mat)

        # 鈹€鈹€ 绗笁姝ワ細姣忕粍閫変竴涓?canonical锛屽叾浣?鈫?replace_map 鈹€鈹€
        replace_map = {}
        canonical_set = set()
        for clean_name, candlist in groups.items():
            # 鏈?exact 鍚嶅瓧鐨勪紭鍏?            canonical = bpy.data.materials.get(clean_name)
            if canonical is None:
                canonical = sorted(candlist, key=lambda m: len(m.name))[0]
            canonical_set.add(canonical)
            for m in candlist:
                if m != canonical:
                    replace_map[m] = canonical

        if replace_map:
            for dup, canon in replace_map.items():
        else:

        replaced_slots = 0
        if replace_map:
            # 鈹€鈹€ 绗洓姝ワ細鏇挎崲鎵€鏈夊璞℃潗璐ㄦЫ 鈹€鈹€
            for obj in bpy.data.objects:
                for slot in obj.material_slots:
                    if slot.material in replace_map:
                        slot.material = replace_map[slot.material]
                        replaced_slots += 1

            # 鈹€鈹€ 绗簲姝ワ細鏇挎崲鎵€鏈?mesh 鏁版嵁鍧楁潗璐ㄦЫ 鈹€鈹€
            for mesh in bpy.data.meshes:
                for i, mat in enumerate(mesh.materials):
                    if mat in replace_map:
                        mesh.materials[i] = replace_map[mat]
                        replaced_slots += 1


        # 鈹€鈹€ 绗叚姝ワ細鍚堝苟閫変腑妯″瀷鍐呴噸澶嶆潗璐ㄦЫ 鈹€鈹€
        merged_slots = 0
        for obj in U.get_selected_mesh_objects(context):
            merged_slots += U.merge_duplicate_material_slots(obj)
            removed_slots += U.remove_unused_material_slots(obj)

        # 鈹€鈹€ 绗竷姝ワ細鍒犻櫎閲嶅鏉愯川锛堢函鏁版嵁 API锛屼笉璋?bpy.ops锛?鈹€鈹€
        removed_materials = 0
        # 鏀堕泦鎵€鏈夐渶瑕佹鏌ョ殑鏉愯川锛歳eplace_map 鐨?keys锛堣鏇挎崲鐨勯噸澶嶆潗璐級+
        # canonical_set 涓?users==0 鐨勶紙娌℃湁 base 鏉愯川鏃?canonical 涔熸槸娈嬬暀锛?        all_to_check = set(replace_map.keys())
        for canon in canonical_set:
            if canon.users == 0:
                all_to_check.add(canon)

        for mat in all_to_check:
            if mat.name not in bpy.data.materials:
                continue
            if mat.use_fake_user:
                mat.use_fake_user = False
            # 涓よ疆灏濊瘯
            try:
                bpy.data.materials.remove(mat, do_unlink=True)
                removed_materials += 1
            except TypeError:
                try:
                    bpy.data.materials.remove(mat)
                    removed_materials += 1
                except RuntimeError as e:
            except RuntimeError as e:


        total_mats = len(bpy.data.materials)
        grouped = sum(1 for l in groups.values() if len(l) >= 2)
        self.report(
            {'INFO'},
            f"鎵弿 {total_mats} 涓潗璐紝{len(groups)} 缁勫悗缂€锛寋grouped} 缁勨墺2 | 鏇挎崲 {replaced_slots} 妲?鍒犻櫎 {removed_materials} 鏉愯川",
        )
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_toggle_vertex_color_view(bpy.types.Operator):
    bl_idname = "uv_layer_manager.toggle_vertex_color_view"
    bl_label = "椤剁偣棰滆壊鏄剧ず"
    bl_description = "鍒囨崲椤剁偣棰滆壊銆侀《鐐筧lpha鍜屾潗璐ㄦ樉绀?
    bl_options = {'REGISTER'}

    mode: bpy.props.EnumProperty(
        items=(
            ('COLOR', "椤剁偣棰滆壊", "鏄剧ず椤剁偣棰滆壊"),
            ('ALPHA', "椤剁偣alpha", "鏄剧ず椤剁偣棰滆壊alpha閫氶亾"),
            ('ID', "鏉愯川ID", "鐢ㄧ函鑹叉樉绀洪€変腑妯″瀷鏉愯川鍒嗛厤"),
        ),
        default='COLOR',
    )

    def execute(self, context):
        # 鈹€鈹€ 鏉愯川ID 鈹€鈹€
        if self.mode == 'ID':
            updated, next_mode = VCN.set_material_view_mode(context, self.mode)
            label = "鏉愯川鏄剧ず" if next_mode == 'MATERIAL' else "鏉愯川ID"
            self.report({'INFO'}, f"宸插垏鎹㈠埌{label}锛屾洿鏂?{updated} 涓?D瑙嗗浘")
            return {'FINISHED'}

        # 鈹€鈹€ 椤剁偣棰滆壊 / 椤剁偣alpha 鈹€鈹€
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "璇烽€変腑涓€涓綉鏍兼ā鍨?)
            return {'CANCELLED'}

        if VCN.has_uvlm_vertex_color_nodes(obj):
            # 宸叉湁娉ㄥ叆鑺傜偣 鈫?娓呴櫎骞舵仮澶嶅師杩炴帴
            VCN._clear_selected_vertex_color_nodes(context)
            MID.restore_material_id_colors(context)
            L.tag_all_view3d_redraw()
            self.report({'INFO'}, "宸叉仮澶嶆潗璐ㄦ樉绀?)
        else:
            # 鏃犺妭鐐?鈫?娉ㄥ叆
            MID.restore_material_id_colors(context)
            VCN._clear_selected_vertex_color_nodes(context)
            VCN._apply_vertex_color_nodes(context, self.mode)
            L.tag_all_view3d_redraw()
            label = "椤剁偣alpha" if self.mode == 'ALPHA' else "椤剁偣棰滆壊"
            self.report({'INFO'}, f"宸插垏鎹㈠埌{label}")

        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_set_color_attribute(bpy.types.Operator):
    bl_idname = "uv_layer_manager.set_color_attribute"
    bl_label = "鍒囨崲棰滆壊灞炴€?
    bl_description = "鍒囨崲褰撳墠妯″瀷姝ｅ湪鏌ョ湅鐨勯鑹插睘鎬?
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
        self.report({'WARNING'}, f"鎵句笉鍒伴鑹插睘鎬? {self.name}")
        return {'CANCELLED'}


# ============================================================
# Property registration
# ============================================================

def register_properties():
    bpy.types.Scene.material_manager_material = bpy.props.PointerProperty(
        name="鏉愯川",
        description="鏉愯川绠＄悊宸ュ叿浣跨敤鐨勭洰鏍囨潗璐?,
        type=bpy.types.Material,
    )
    bpy.types.Scene.material_view_mode = bpy.props.EnumProperty(
        name="鏉愯川鏌ョ湅妯″紡",
        items=(
            ('MATERIAL', "鏉愯川", "姝ｅ父鏉愯川鏄剧ず"),
            ('COLOR', "椤剁偣棰滆壊", "鏄剧ず椤剁偣棰滆壊"),
            ('ALPHA', "椤剁偣alpha", "鏄剧ず椤剁偣alpha"),
            ('ID', "鏉愯川ID", "鐢ㄧ函鑹叉樉绀烘潗璐ㄥ垎閰?),
            ('SINGLE_ID', "鍗曟潗璐↖D", "鍙樉绀洪儴鍒嗘潗璐↖D鑹?),
        ),
        default='MATERIAL',
    )


def unregister_properties():
    if hasattr(bpy.types.Scene, 'material_manager_material'):
        del bpy.types.Scene.material_manager_material
    if hasattr(bpy.types.Scene, 'material_view_mode'):
        del bpy.types.Scene.material_view_mode