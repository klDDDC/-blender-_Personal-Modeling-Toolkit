# -*- coding: utf-8 -*-
"""
UV Layer Manager - Modeling Operators
"""
import bpy
import bmesh
import math
from . import constants as C
from . import utils as U
from . import normal_angle as NA
from . import merge_vertices as MV


# ============================================================
# 顶点组 Enum — 动态列出选中模型的顶点组
# 始终包含 scene.close_snap_vertex_group 以防验证失败
# ============================================================

def _vg_items(self, context):
    items = [('', "（无）", "")]
    seen = set()
    # 始终包含已存储的值，确保 EnumProperty 设值不会验证失败
    try:
        stored = getattr(context.scene, "close_snap_vertex_group", "")
        if stored:
            items.append((stored, stored, ""))
            seen.add(stored)
    except Exception:
        pass
    for obj in U.get_selected_mesh_objects(context):
        if obj.type == 'MESH':
            for vg in obj.vertex_groups:
                if vg.name not in seen:
                    seen.add(vg.name)
                    items.append((vg.name, vg.name, ""))
    return items


class UV_LAYER_MANAGER_OT_set_close_snap_distance(bpy.types.Operator):
    bl_idname = "uv_layer_manager.set_close_snap_distance"
    bl_label = "合并相近设置"
    bl_description = "设置合并相近的距离阈值和顶点组"
    bl_options = {'REGISTER'}

    distance_cm: bpy.props.FloatProperty(
        name="距离 (cm)",
        description="顶点在该距离内会被移动到同一位置（厘米）",
        default=0.1,
        min=0.0,
        precision=2,
        step=0.1,
    )

    vertex_group: bpy.props.EnumProperty(
        name="顶点组",
        description='仅合并该顶点组内的顶点（选"（无）"则不限制）',
        items=_vg_items,
    )

    def invoke(self, context, event):
        self.distance_cm = getattr(context.scene, "close_snap_distance_cm", 0.1)
        stored_vg = getattr(context.scene, "close_snap_vertex_group", "")
        if stored_vg:
            for obj in U.get_selected_mesh_objects(context):
                if obj.type == 'MESH' and obj.vertex_groups.get(stored_vg):
                    self.vertex_group = stored_vg
                    break
        return context.window_manager.invoke_props_dialog(self, width=280)

    def draw(self, context):
        self.layout.prop(self, "distance_cm", text="距离")
        self.layout.prop(self, "vertex_group", text="顶点组")

    def execute(self, context):
        context.scene.close_snap_distance_cm = self.distance_cm
        context.scene.close_snap_vertex_group = self.vertex_group
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_set_uv_naming(bpy.types.Operator):
    bl_idname = "uv_layer_manager.set_uv_naming"
    bl_label = "UV命名设置"
    bl_description = "自定义UV命名前缀和层数"
    bl_options = {'REGISTER'}

    prefix: bpy.props.StringProperty(
        name="前缀",
        description="UV层命名前缀，如 uvmap → uvmap1, uvmap2",
        default="uvmap",
    )
    count: bpy.props.IntProperty(
        name="层数",
        description="保留的UV层数量",
        default=3,
        min=1,
        max=20,
    )

    def invoke(self, context, event):
        self.prefix = getattr(context.scene, "uv_naming_prefix", "uvmap")
        self.count = getattr(context.scene, "uv_naming_count", 3)
        return context.window_manager.invoke_props_dialog(self, width=240)

    def draw(self, context):
        self.layout.prop(self, "prefix", text="前缀")
        self.layout.prop(self, "count", text="层数")

    def execute(self, context):
        context.scene.uv_naming_prefix = self.prefix
        context.scene.uv_naming_count = self.count
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_set_select_angle(bpy.types.Operator):
    bl_idname = "uv_layer_manager.set_select_angle"
    bl_label = "角度选择阈值"
    bl_description = "设置角度选择功能的面法向角度阈值"
    bl_options = {'REGISTER'}

    angle: bpy.props.FloatProperty(
        name="角度",
        description="面法向夹角小于或等于该值的面都会被选中",
        default=30.0,
        min=0.0,
        max=180.0,
        step=1.0,
    )

    def invoke(self, context, event):
        self.angle = getattr(context.scene, "uvlm_select_angle_threshold", 30.0)
        return context.window_manager.invoke_props_dialog(self, width=240)

    def draw(self, context):
        self.layout.prop(self, "angle", text="角度阈值")

    def execute(self, context):
        context.scene.uvlm_select_angle_threshold = self.angle
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_reset_uv_names(bpy.types.Operator):
    bl_idname = "uv_layer_manager.reset_uv_names"
    bl_label = "uv命名重置"
    bl_description = "按自定义前缀和数量重置选中模型的UV命名"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "请选择至少一个网格模型")
            return {'CANCELLED'}

        prefix = getattr(context.scene, "uv_naming_prefix", "uvmap")
        count = getattr(context.scene, "uv_naming_count", 3)
        count = max(count, 1)

        touched_meshes = set()
        updated_count = 0

        for obj in objects:
            mesh = obj.data
            if mesh is None or mesh.as_pointer() in touched_meshes:
                continue

            uv_layers = mesh.uv_layers

            while len(uv_layers) < count:
                uv_layers.new(name=f"{prefix}{len(uv_layers) + 1}")

            while len(uv_layers) > count:
                uv_layers.remove(uv_layers[len(uv_layers) - 1])

            for index, uv_layer in enumerate(uv_layers):
                uv_layer.name = f"__uv_layer_manager_tmp_{index + 1}"

            for index, uv_layer in enumerate(uv_layers):
                uv_layer.name = f"{prefix}{index + 1}"

            uv_layers.active_index = 0
            mesh.update()
            touched_meshes.add(mesh.as_pointer())
            updated_count += 1

        self.report({'INFO'}, f"已重置 {updated_count} 个模型的UV命名（{prefix}1~{count}）")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_snap_close_vertices(bpy.types.Operator):
    bl_idname = "uv_layer_manager.snap_close_vertices"
    bl_label = "合并相近"
    bl_description = "将边界/锐边/选中点/顶点组上的相近顶点移动到同一位置（不含缝合边）"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "请选择至少一个网格模型")
            return {'CANCELLED'}

        vg_name = getattr(context.scene, "close_snap_vertex_group", "") or None

        # --- Capture edit-mode selection BEFORE mode switch ---
        selected_map = {}
        active_object = context.view_layer.objects.active
        original_mode = active_object.mode if active_object else 'OBJECT'

        if original_mode == 'EDIT' and active_object and active_object.type == 'MESH':
            import bmesh
            bm = bmesh.from_edit_mesh(active_object.data)
            sel = {v.index for v in bm.verts if v.select}
            if sel:
                selected_map[active_object.data.as_pointer()] = sel

        # --- Convert cm to BU ---
        distance_cm = getattr(context.scene, "close_snap_distance_cm", 0.1)
        distance_bu = distance_cm * 0.01
        if distance_bu <= 0.0:
            self.report({'WARNING'}, "合并相近距离必须大于0")
            return {'CANCELLED'}

        try:
            if original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            touched, vertices, groups = MV.snap_close_vertices_in_objects(
                objects, distance_bu,
                selected_map=selected_map,
                vertex_group_name=vg_name,
            )

            self.report(
                {'INFO'},
                f"合并相近完成：{touched} 个模型，{vertices} 个顶点，{groups} 组",
            )
            return {'FINISHED'}
        finally:
            if active_object and active_object.name in bpy.data.objects:
                context.view_layer.objects.active = active_object
                if original_mode != 'OBJECT':
                    try:
                        bpy.ops.object.mode_set(mode=original_mode)
                    except Exception:
                        pass


class UV_LAYER_MANAGER_OT_rotate_linked_duplicate(bpy.types.Operator):
    bl_idname = "uv_layer_manager.rotate_linked_duplicate"
    bl_label = "旋转复制"
    bl_description = "关联复制选中模型，并按指定轴向和总角度依次旋转"
    bl_options = {'REGISTER', 'UNDO'}

    axis: bpy.props.EnumProperty(
        name="轴向",
        description="复制对象旋转使用的轴向",
        items=(
            ('X', "X", "绕X轴旋转"),
            ('Y', "Y", "绕Y轴旋转"),
            ('Z', "Z", "绕Z轴旋转"),
        ),
        default='Z',
    )

    count: bpy.props.IntProperty(
        name="复制数量",
        description="为每个选中模型创建多少个关联复制对象",
        default=10,
        min=1,
        soft_max=360,
    )

    total_angle: bpy.props.FloatProperty(
        name="旋转角度",
        description="最后一个复制对象相对原模型的旋转角度，单位为度",
        default=360.0,
        soft_min=-3600.0,
        soft_max=3600.0,
    )

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        source_objects = U.get_selected_mesh_objects(context)
        if not source_objects:
            self.report({'WARNING'}, "请选择至少一个网格模型")
            return {'CANCELLED'}

        is_closed_rotation = abs(self.total_angle) > 0.0 and math.isclose(
            abs(self.total_angle) % 360.0,
            0.0,
            abs_tol=1e-6,
        )
        angle_steps = self.count + 1 if is_closed_rotation else self.count
        step_angle = math.radians(self.total_angle) / angle_steps
        created_objects = []

        for obj in source_objects:
            target_collections = obj.users_collection or [context.collection]
            for index in range(1, self.count + 1):
                duplicate = obj.copy()
                duplicate.data = obj.data
                duplicate.animation_data_clear()
                duplicate.name = f"{obj.name}_rot_{index:03d}"
                duplicate.rotation_euler = obj.rotation_euler.copy()
                duplicate.rotation_euler.rotate_axis(self.axis, step_angle * index)

                for collection in target_collections:
                    collection.objects.link(duplicate)
                created_objects.append(duplicate)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in source_objects:
            obj.select_set(True)
        for obj in created_objects:
            obj.select_set(True)
        if created_objects:
            context.view_layer.objects.active = created_objects[-1]

        self.report({'INFO'}, f"已旋转复制 {len(created_objects)} 个关联模型")
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_select_ngons(bpy.types.Operator):
    bl_idname = "uv_layer_manager.select_ngons"
    bl_label = "大于4边面"
    bl_description = "选中所选模型中顶点数大于4的面"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        active_object = context.view_layer.objects.active

        try:
            with U.temporary_object_mode(context, 'EDIT', active_object):
                bpy.ops.mesh.select_all(action='DESELECT')

                for obj in context.objects_in_mode_unique_data:
                    if obj.type != 'MESH':
                        continue
                    bm = bmesh.from_edit_mesh(obj.data)
                    for face in bm.faces:
                        if len(face.verts) > 4:
                            face.select = True
                    bmesh.update_edit_mesh(obj.data)

                ngon_count = sum(
                    1 for obj in context.objects_in_mode_unique_data
                    if obj.type == 'MESH'
                    for face in bmesh.from_edit_mesh(obj.data).faces
                    if face.select
                )
            self.report({'INFO'}, f"已选中 {ngon_count} 个大于4边的面")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"选择失败: {str(e)}")
            return {'CANCELLED'}


class UV_LAYER_MANAGER_OT_quadify_ngons(bpy.types.Operator):
    bl_idname = "uv_layer_manager.quadify_ngons"
    bl_label = "处理多边面"
    bl_description = "将选中模型中大于4边的面尽量转换为四边面"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "请选择至少一个网格模型")
            return {'CANCELLED'}

        active_object = context.view_layer.objects.active
        original_mode = active_object.mode if active_object else 'OBJECT'
        touched_meshes = set()
        processed_meshes = 0
        original_ngons = 0
        created_quads = 0
        remaining_ngons = 0

        try:
            if active_object and original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            for obj in objects:
                mesh = obj.data
                if mesh is None or mesh.as_pointer() in touched_meshes:
                    continue
                touched_meshes.add(mesh.as_pointer())

                bm = bmesh.new()
                bm.from_mesh(mesh)
                bm.faces.ensure_lookup_table()

                ngon_faces = [face for face in bm.faces if len(face.verts) > 4]
                if not ngon_faces:
                    bm.free()
                    continue

                original_ngons += len(ngon_faces)
                triangulated = bmesh.ops.triangulate(
                    bm,
                    faces=ngon_faces,
                    quad_method='BEAUTY',
                    ngon_method='BEAUTY',
                )
                tri_faces = [
                    elem for elem in triangulated.get("faces", [])
                    if isinstance(elem, bmesh.types.BMFace) and elem.is_valid and len(elem.verts) == 3
                ]
                if tri_faces:
                    bmesh.ops.join_triangles(
                        bm,
                        faces=tri_faces,
                        angle_face_threshold=math.radians(180.0),
                        angle_shape_threshold=math.radians(180.0),
                        cmp_seam=True,
                        cmp_sharp=True,
                        cmp_uvs=True,
                        cmp_vcols=True,
                        cmp_materials=True,
                    )

                bm.faces.ensure_lookup_table()
                created_quads += sum(1 for face in bm.faces if len(face.verts) == 4)
                remaining_ngons += sum(1 for face in bm.faces if len(face.verts) > 4)
                bm.to_mesh(mesh)
                bm.free()
                mesh.update()
                processed_meshes += 1

            if original_ngons == 0:
                self.report({'INFO'}, "未发现大于4边面")
            elif remaining_ngons:
                self.report(
                    {'INFO'},
                    f"已处理 {original_ngons} 个多边面，仍剩 {remaining_ngons} 个大于4边面",
                )
            else:
                self.report({'INFO'}, f"已处理 {original_ngons} 个多边面，生成 {created_quads} 个四边面")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"处理多边面失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            if active_object and active_object.name in bpy.data.objects:
                context.view_layer.objects.active = active_object
                if original_mode != 'OBJECT':
                    try:
                        bpy.ops.object.mode_set(mode=original_mode)
                    except Exception:
                        pass


class UV_LAYER_MANAGER_OT_select_overlapping_faces(bpy.types.Operator):
    bl_idname = "uv_layer_manager.select_overlapping_faces"
    bl_label = "检查重叠面"
    bl_description = "保留每组重叠面中的一个正常面，只选中多余的重复/错误面"
    bl_options = {'REGISTER', 'UNDO'}

    tolerance: bpy.props.FloatProperty(
        name="位置容差",
        description="顶点位置在该距离内会被视为重合",
        default=0.00001,
        min=0.0,
        precision=6,
    )

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def _face_key(self, mesh, polygon):
        tolerance = max(self.tolerance, 1e-12)

        def quantize(value):
            return round(value / tolerance)

        coords = []
        for vertex_index in polygon.vertices:
            co = mesh.vertices[vertex_index].co
            coords.append((quantize(co.x), quantize(co.y), quantize(co.z)))
        return (len(coords), tuple(sorted(coords)))

    def _build_edge_neighbors(self, mesh):
        edge_faces = {}
        for polygon in mesh.polygons:
            for edge_key in polygon.edge_keys:
                edge_faces.setdefault(tuple(sorted(edge_key)), []).append(polygon.index)
        return edge_faces

    def _choose_face_to_keep(self, mesh, indices, duplicate_indices, edge_faces):
        duplicate_set = set(duplicate_indices)

        def score_polygon(polygon_index):
            polygon = mesh.polygons[polygon_index]
            # 1) 有效邻居数：错误重叠面周围没有面，正确面连着模型
            ncount = 0
            nscore = 0.0
            for edge_key in polygon.edge_keys:
                for ni in edge_faces.get(tuple(sorted(edge_key)), []):
                    if ni == polygon_index or ni in duplicate_set:
                        continue
                    ncount += 1
                    nscore += max(-1.0, min(1.0, polygon.normal.dot(mesh.polygons[ni].normal)))
            # 2) 面积：同邻居数时面积更大的更可能是正常面
            # 3) 法向一致性兜底
            return (ncount, polygon.area, nscore, -polygon_index)

        return max(indices, key=score_polygon)

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "请选择至少一个网格模型")
            return {'CANCELLED'}

        active_object = context.view_layer.objects.active
        original_mode = active_object.mode if active_object else 'OBJECT'
        touched_meshes = set()
        selected_faces_by_mesh = {}
        overlap_faces = 0
        overlap_groups = 0
        kept_faces = 0
        processed_meshes = 0

        try:
            if active_object and original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            for obj in objects:
                mesh = obj.data
                if mesh is None or mesh.as_pointer() in touched_meshes:
                    continue
                touched_meshes.add(mesh.as_pointer())
                processed_meshes += 1

                groups = {}
                for polygon in mesh.polygons:
                    polygon.select = False
                    groups.setdefault(self._face_key(mesh, polygon), []).append(polygon.index)

                edge_faces = self._build_edge_neighbors(mesh)
                duplicate_indices = {
                    polygon_index
                    for indices in groups.values()
                    if len(indices) > 1
                    for polygon_index in indices
                }

                for indices in groups.values():
                    if len(indices) <= 1:
                        continue
                    overlap_groups += 1
                    keep_index = self._choose_face_to_keep(mesh, indices, duplicate_indices, edge_faces)
                    kept_faces += 1
                    error_indices = [polygon_index for polygon_index in indices if polygon_index != keep_index]
                    overlap_faces += len(error_indices)
                    selected_faces_by_mesh.setdefault(mesh.as_pointer(), set()).update(error_indices)
                    for polygon_index in error_indices:
                        mesh.polygons[polygon_index].select = True
                mesh.update()

            if overlap_faces:
                if active_object and active_object.name in bpy.data.objects:
                    context.view_layer.objects.active = active_object
                    try:
                        bpy.ops.object.mode_set(mode='EDIT')
                        bpy.ops.mesh.select_mode(type='FACE')
                        for obj in context.objects_in_mode_unique_data:
                            if obj.type != 'MESH':
                                continue
                            selected_indices = selected_faces_by_mesh.get(obj.data.as_pointer(), set())
                            bm = bmesh.from_edit_mesh(obj.data)
                            bm.faces.ensure_lookup_table()
                            for face in bm.faces:
                                face.select_set(face.index in selected_indices)
                            bmesh.update_edit_mesh(obj.data)
                    except Exception:
                        pass
                self.report({'INFO'}, f"已选中 {overlap_faces} 个重复面，保留 {kept_faces} 个正常面（{overlap_groups} 组）")
            else:
                self.report({'INFO'}, f"已检查 {processed_meshes} 个模型，未发现重叠面")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"检查重叠面失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            if not overlap_faces and active_object and active_object.name in bpy.data.objects:
                context.view_layer.objects.active = active_object
                if original_mode != 'OBJECT':
                    try:
                        bpy.ops.object.mode_set(mode=original_mode)
                    except Exception:
                        pass


class UV_LAYER_MANAGER_OT_select_by_angle(bpy.types.Operator):
    bl_idname = "uv_layer_manager.select_by_angle"
    bl_label = "角度选择"
    bl_description = "基于当前选中面的法向角度选择相邻面"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return {'CANCELLED'}

        threshold_degrees = getattr(context.scene, "uvlm_select_angle_threshold", 30.0)
        cos_threshold = math.cos(math.radians(threshold_degrees))

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        # Seeds = already selected faces
        seeds = [face for face in bm.faces if face.select]
        if not seeds:
            self.report({'WARNING'}, "请先选中至少一个参考面")
            return {'CANCELLED'}

        reference_normal = seeds[0].normal.copy()
        visited = {face.index for face in seeds}
        queue = list(seeds)
        count = len(seeds)

        while queue:
            current = queue.pop()
            for edge in current.edges:
                for linked_face in edge.link_faces:
                    if linked_face.index in visited:
                        continue
                    if linked_face.normal.dot(reference_normal) >= cos_threshold:
                        linked_face.select = True
                        visited.add(linked_face.index)
                        queue.append(linked_face)
                        count += 1

        bmesh.update_edit_mesh(obj.data)
        new_count = count - len(seeds)
        self.report({'INFO'}, f"角度扩散选中 {new_count} 个相邻面（共 {count} 个面）")
        return {'FINISHED'}


# ============================================================
# Operators - Normals
# ============================================================

class UV_LAYER_MANAGER_OT_clean_normals(bpy.types.Operator):
    bl_idname = "uv_layer_manager.clean_normals"
    bl_label = "清理法向"
    bl_description = "解锁选中模型法向，添加 Smooth by Angle 修改器（保留已有锐边）"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "请选择至少一个网格模型")
            return {'CANCELLED'}

        angle_degrees = NA.get_normal_angle_degrees(context.scene)
        active_object = context.view_layer.objects.active
        selected_objects = list(context.selected_objects)
        original_mode = active_object.mode if active_object else 'OBJECT'

        try:
            if active_object and original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            context.view_layer.objects.active = objects[0]

            touched_meshes = set()
            for obj in objects:
                mesh = obj.data
                if mesh.as_pointer() in touched_meshes:
                    continue
                touched_meshes.add(mesh.as_pointer())
                NA.apply_normal_angle_modifier(obj, angle_degrees)

            self.report({'INFO'}, f"已解锁 {len(objects)} 个模型法向，添加 Smooth by Angle 修改器（{angle_degrees:g}°）")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"清理法向失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in selected_objects:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if active_object and active_object.name in bpy.data.objects:
                context.view_layer.objects.active = active_object
                if original_mode != 'OBJECT':
                    try:
                        bpy.ops.object.mode_set(mode=original_mode)
                    except Exception:
                        pass


class UV_LAYER_MANAGER_OT_set_normal_angle(bpy.types.Operator):
    bl_idname = "uv_layer_manager.set_normal_angle"
    bl_label = "设置法向角度"
    bl_description = "解锁选中模型法向，添加 Smooth by Angle 法向修改器（保留已有锐边）"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.StringProperty()

    def execute(self, context):
        valid_presets = {'180', '30', '60', '90', C.NORMAL_ANGLE_PRESET_CUSTOM}
        if self.preset not in valid_presets:
            self.report({'WARNING'}, "无效的法向角度预设")
            return {'CANCELLED'}
        context.scene.normal_angle_preset = self.preset
        return bpy.ops.uv_layer_manager.clean_normals()
