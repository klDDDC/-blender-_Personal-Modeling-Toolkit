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
# 椤剁偣缁?Enum 鈥?鍔ㄦ€佸垪鍑洪€変腑妯″瀷鐨勯《鐐圭粍
# 濮嬬粓鍖呭惈 scene.close_snap_vertex_group 浠ラ槻楠岃瘉澶辫触
# ============================================================

def _vg_items(self, context):
    items = [('', "锛堟棤锛?, "")]
    seen = set()
    # 濮嬬粓鍖呭惈宸插瓨鍌ㄧ殑鍊硷紝纭繚 EnumProperty 璁惧€间笉浼氶獙璇佸け璐?    try:
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
    bl_label = "鍚堝苟鐩歌繎璁剧疆"
    bl_description = "璁剧疆鍚堝苟鐩歌繎鐨勮窛绂婚槇鍊煎拰椤剁偣缁?
    bl_options = {'REGISTER'}

    distance_cm: bpy.props.FloatProperty(
        name="璺濈 (cm)",
        description="椤剁偣鍦ㄨ璺濈鍐呬細琚Щ鍔ㄥ埌鍚屼竴浣嶇疆锛堝帢绫筹級",
        default=0.1,
        min=0.0,
        precision=2,
        step=0.1,
    )

    vertex_group: bpy.props.EnumProperty(
        name="椤剁偣缁?,
        description='浠呭悎骞惰椤剁偣缁勫唴鐨勯《鐐癸紙閫?锛堟棤锛?鍒欎笉闄愬埗锛?,
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
        self.layout.prop(self, "distance_cm", text="璺濈")
        self.layout.prop(self, "vertex_group", text="椤剁偣缁?)

    def execute(self, context):
        context.scene.close_snap_distance_cm = self.distance_cm
        context.scene.close_snap_vertex_group = self.vertex_group
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_set_uv_naming(bpy.types.Operator):
    bl_idname = "uv_layer_manager.set_uv_naming"
    bl_label = "UV鍛藉悕璁剧疆"
    bl_description = "鑷畾涔塙V鍛藉悕鍓嶇紑鍜屽眰鏁?
    bl_options = {'REGISTER'}

    prefix: bpy.props.StringProperty(
        name="鍓嶇紑",
        description="UV灞傚懡鍚嶅墠缂€锛屽 uvmap 鈫?uvmap1, uvmap2",
        default="uvmap",
    )
    count: bpy.props.IntProperty(
        name="灞傛暟",
        description="淇濈暀鐨刄V灞傛暟閲?,
        default=3,
        min=1,
        max=20,
    )

    def invoke(self, context, event):
        self.prefix = getattr(context.scene, "uv_naming_prefix", "uvmap")
        self.count = getattr(context.scene, "uv_naming_count", 3)
        return context.window_manager.invoke_props_dialog(self, width=240)

    def draw(self, context):
        self.layout.prop(self, "prefix", text="鍓嶇紑")
        self.layout.prop(self, "count", text="灞傛暟")

    def execute(self, context):
        context.scene.uv_naming_prefix = self.prefix
        context.scene.uv_naming_count = self.count
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_set_select_angle(bpy.types.Operator):
    bl_idname = "uv_layer_manager.set_select_angle"
    bl_label = "瑙掑害閫夋嫨闃堝€?
    bl_description = "璁剧疆瑙掑害閫夋嫨鍔熻兘鐨勯潰娉曞悜瑙掑害闃堝€?
    bl_options = {'REGISTER'}

    angle: bpy.props.FloatProperty(
        name="瑙掑害",
        description="闈㈡硶鍚戝す瑙掑皬浜庢垨绛変簬璇ュ€肩殑闈㈤兘浼氳閫変腑",
        default=30.0,
        min=0.0,
        max=180.0,
        step=1.0,
    )

    def invoke(self, context, event):
        self.angle = getattr(context.scene, "uvlm_select_angle_threshold", 30.0)
        return context.window_manager.invoke_props_dialog(self, width=240)

    def draw(self, context):
        self.layout.prop(self, "angle", text="瑙掑害闃堝€?)

    def execute(self, context):
        context.scene.uvlm_select_angle_threshold = self.angle
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_reset_uv_names(bpy.types.Operator):
    bl_idname = "uv_layer_manager.reset_uv_names"
    bl_label = "uv鍛藉悕閲嶇疆"
    bl_description = "鎸夎嚜瀹氫箟鍓嶇紑鍜屾暟閲忛噸缃€変腑妯″瀷鐨刄V鍛藉悕"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "璇烽€夋嫨鑷冲皯涓€涓綉鏍兼ā鍨?)
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

        self.report({'INFO'}, f"宸查噸缃?{updated_count} 涓ā鍨嬬殑UV鍛藉悕锛坽prefix}1~{count}锛?)
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_snap_close_vertices(bpy.types.Operator):
    bl_idname = "uv_layer_manager.snap_close_vertices"
    bl_label = "鍚堝苟鐩歌繎"
    bl_description = "灏嗚竟鐣?閿愯竟/閫変腑鐐?椤剁偣缁勪笂鐨勭浉杩戦《鐐圭Щ鍔ㄥ埌鍚屼竴浣嶇疆锛堜笉鍚紳鍚堣竟锛?
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "璇烽€夋嫨鑷冲皯涓€涓綉鏍兼ā鍨?)
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
            self.report({'WARNING'}, "鍚堝苟鐩歌繎璺濈蹇呴』澶т簬0")
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
                f"鍚堝苟鐩歌繎瀹屾垚锛歿touched} 涓ā鍨嬶紝{vertices} 涓《鐐癸紝{groups} 缁?,
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
    bl_label = "鏃嬭浆澶嶅埗"
    bl_description = "鍏宠仈澶嶅埗閫変腑妯″瀷锛屽苟鎸夋寚瀹氳酱鍚戝拰鎬昏搴︿緷娆℃棆杞?
    bl_options = {'REGISTER', 'UNDO'}

    axis: bpy.props.EnumProperty(
        name="杞村悜",
        description="澶嶅埗瀵硅薄鏃嬭浆浣跨敤鐨勮酱鍚?,
        items=(
            ('X', "X", "缁昘杞存棆杞?),
            ('Y', "Y", "缁昚杞存棆杞?),
            ('Z', "Z", "缁昛杞存棆杞?),
        ),
        default='Z',
    )

    count: bpy.props.IntProperty(
        name="澶嶅埗鏁伴噺",
        description="涓烘瘡涓€変腑妯″瀷鍒涘缓澶氬皯涓叧鑱斿鍒跺璞?,
        default=10,
        min=1,
        soft_max=360,
    )

    total_angle: bpy.props.FloatProperty(
        name="鏃嬭浆瑙掑害",
        description="鏈€鍚庝竴涓鍒跺璞＄浉瀵瑰師妯″瀷鐨勬棆杞搴︼紝鍗曚綅涓哄害",
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
            self.report({'WARNING'}, "璇烽€夋嫨鑷冲皯涓€涓綉鏍兼ā鍨?)
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

        self.report({'INFO'}, f"宸叉棆杞鍒?{len(created_objects)} 涓叧鑱旀ā鍨?)
        return {'FINISHED'}


class UV_LAYER_MANAGER_OT_select_ngons(bpy.types.Operator):
    bl_idname = "uv_layer_manager.select_ngons"
    bl_label = "澶т簬4杈归潰"
    bl_description = "閫変腑鎵€閫夋ā鍨嬩腑椤剁偣鏁板ぇ浜?鐨勯潰"
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
            self.report({'INFO'}, f"宸查€変腑 {ngon_count} 涓ぇ浜?杈圭殑闈?)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"閫夋嫨澶辫触: {str(e)}")
            return {'CANCELLED'}


class UV_LAYER_MANAGER_OT_quadify_ngons(bpy.types.Operator):
    bl_idname = "uv_layer_manager.quadify_ngons"
    bl_label = "澶勭悊澶氳竟闈?
    bl_description = "灏嗛€変腑妯″瀷涓ぇ浜?杈圭殑闈㈠敖閲忚浆鎹负鍥涜竟闈?
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "璇烽€夋嫨鑷冲皯涓€涓綉鏍兼ā鍨?)
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
                self.report({'INFO'}, "鏈彂鐜板ぇ浜?杈归潰")
            elif remaining_ngons:
                self.report(
                    {'INFO'},
                    f"宸插鐞?{original_ngons} 涓杈归潰锛屼粛鍓?{remaining_ngons} 涓ぇ浜?杈归潰",
                )
            else:
                self.report({'INFO'}, f"宸插鐞?{original_ngons} 涓杈归潰锛岀敓鎴?{created_quads} 涓洓杈归潰")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"澶勭悊澶氳竟闈㈠け璐? {str(e)}")
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
    bl_label = "妫€鏌ラ噸鍙犻潰"
    bl_description = "淇濈暀姣忕粍閲嶅彔闈腑鐨勪竴涓甯搁潰锛屽彧閫変腑澶氫綑鐨勯噸澶?閿欒闈?
    bl_options = {'REGISTER', 'UNDO'}

    tolerance: bpy.props.FloatProperty(
        name="浣嶇疆瀹瑰樊",
        description="椤剁偣浣嶇疆鍦ㄨ璺濈鍐呬細琚涓洪噸鍚?,
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
            # 1) 鏈夋晥閭诲眳鏁帮細閿欒閲嶅彔闈㈠懆鍥存病鏈夐潰锛屾纭潰杩炵潃妯″瀷
            ncount = 0
            nscore = 0.0
            for edge_key in polygon.edge_keys:
                for ni in edge_faces.get(tuple(sorted(edge_key)), []):
                    if ni == polygon_index or ni in duplicate_set:
                        continue
                    ncount += 1
                    nscore += max(-1.0, min(1.0, polygon.normal.dot(mesh.polygons[ni].normal)))
            # 2) 闈㈢Н锛氬悓閭诲眳鏁版椂闈㈢Н鏇村ぇ鐨勬洿鍙兘鏄甯搁潰
            # 3) 娉曞悜涓€鑷存€у厹搴?            return (ncount, polygon.area, nscore, -polygon_index)

        return max(indices, key=score_polygon)

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "璇烽€夋嫨鑷冲皯涓€涓綉鏍兼ā鍨?)
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
                self.report({'INFO'}, f"宸查€変腑 {overlap_faces} 涓噸澶嶉潰锛屼繚鐣?{kept_faces} 涓甯搁潰锛坽overlap_groups} 缁勶級")
            else:
                self.report({'INFO'}, f"宸叉鏌?{processed_meshes} 涓ā鍨嬶紝鏈彂鐜伴噸鍙犻潰")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"妫€鏌ラ噸鍙犻潰澶辫触: {str(e)}")
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
    bl_label = "瑙掑害閫夋嫨"
    bl_description = "鍩轰簬褰撳墠閫変腑闈㈢殑娉曞悜瑙掑害閫夋嫨鐩搁偦闈?
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
            self.report({'WARNING'}, "璇峰厛閫変腑鑷冲皯涓€涓弬鑰冮潰")
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
        self.report({'INFO'}, f"瑙掑害鎵╂暎閫変腑 {new_count} 涓浉閭婚潰锛堝叡 {count} 涓潰锛?)
        return {'FINISHED'}


# ============================================================
# Operators - Normals
# ============================================================

class UV_LAYER_MANAGER_OT_clean_normals(bpy.types.Operator):
    bl_idname = "uv_layer_manager.clean_normals"
    bl_label = "娓呯悊娉曞悜"
    bl_description = "瑙ｉ攣閫変腑妯″瀷娉曞悜锛屾坊鍔?Smooth by Angle 淇敼鍣紙淇濈暀宸叉湁閿愯竟锛?
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(U.get_selected_mesh_objects(context)) > 0

    def execute(self, context):
        objects = U.get_selected_mesh_objects(context)
        if not objects:
            self.report({'WARNING'}, "璇烽€夋嫨鑷冲皯涓€涓綉鏍兼ā鍨?)
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

            self.report({'INFO'}, f"宸茶В閿?{len(objects)} 涓ā鍨嬫硶鍚戯紝娣诲姞 Smooth by Angle 淇敼鍣紙{angle_degrees:g}掳锛?)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"娓呯悊娉曞悜澶辫触: {str(e)}")
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
    bl_label = "璁剧疆娉曞悜瑙掑害"
    bl_description = "瑙ｉ攣閫変腑妯″瀷娉曞悜锛屾坊鍔?Smooth by Angle 娉曞悜淇敼鍣紙淇濈暀宸叉湁閿愯竟锛?
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.StringProperty()

    def execute(self, context):
        valid_presets = {'180', '30', '60', '90', C.NORMAL_ANGLE_PRESET_CUSTOM}
        if self.preset not in valid_presets:
            self.report({'WARNING'}, "鏃犳晥鐨勬硶鍚戣搴﹂璁?)
            return {'CANCELLED'}
        context.scene.normal_angle_preset = self.preset
        return bpy.ops.uv_layer_manager.clean_normals()