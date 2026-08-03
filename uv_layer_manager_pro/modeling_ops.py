# -*- coding: utf-8 -*-
"""
UV Layer Manager - Modeling Operators
"""
import bpy
import bmesh
import math
import mathutils
from . import constants as C
from . import utils as U
from . import normal_angle as NA
from . import merge_vertices as MV


STRAIGHTEN_DIRECTION_ITEMS = (
    ('MANUAL', "手动控制", "点击按钮后在 3D 视图拖拽鼠标定义拉直方向（类似 FFD 控制点）"),
    ('AUTO', "自动（最远两点）", "用选中顶点中最远的两个点确定方向，端点保持不动"),
    ('EDGE', "沿活动边", "用活动边（最后选中的边）的方向拉直"),
    ('X', "X 轴", "沿世界 X 轴拉直，直线过选中顶点中心"),
    ('Y', "Y 轴", "沿世界 Y 轴拉直，直线过选中顶点中心"),
    ('Z', "Z 轴", "沿世界 Z 轴拉直，直线过选中顶点中心"),
    ('ANGLE', "自定义角度", "按角度绕 Z 轴（俯视平面）拉直，X 正方向为 0°，逆时针"),
)


def project_verts_onto_line(verts, origin, direction):
    """把顶点投影到过 origin、沿 direction 的直线上。返回移动的顶点数。"""
    len_sq = direction.length_squared
    if len_sq <= 1e-12:
        return 0
    for v in verts:
        t = (v.co - origin).dot(direction) / len_sq
        v.co = origin + direction * t
    return len(verts)


# ============================================================
# 顶点组 Enum — 动态列出选中模型的顶点组
# 始终包含 scene.close_snap_vertex_group 以防验证失败
# ============================================================

def _vg_items(self, context):
    items = [('__NONE__', "（无）", "不限制顶点组")]
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
        default=0,
    )

    def invoke(self, context, event):
        self.distance_cm = getattr(context.scene, "close_snap_distance_cm", 0.1)
        stored_vg = getattr(context.scene, "close_snap_vertex_group", "")
        if stored_vg:
            for obj in U.get_selected_mesh_objects(context):
                if obj.type == 'MESH' and obj.vertex_groups.get(stored_vg):
                    self.vertex_group = stored_vg
                    break
        else:
            self.vertex_group = '__NONE__'
        return context.window_manager.invoke_props_dialog(self, width=280)

    def draw(self, context):
        self.layout.prop(self, "distance_cm", text="距离")
        self.layout.prop(self, "vertex_group", text="顶点组")

    def execute(self, context):
        context.scene.close_snap_distance_cm = self.distance_cm
        vertex_group = getattr(self, "vertex_group", "__NONE__")
        context.scene.close_snap_vertex_group = "" if vertex_group == '__NONE__' else vertex_group
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
            for edit_object in context.objects_in_mode_unique_data:
                if edit_object.type != 'MESH':
                    continue
                bm = bmesh.from_edit_mesh(edit_object.data)
                sel = {v.index for v in bm.verts if v.select}
                if sel:
                    selected_map[edit_object.data.as_pointer()] = sel

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


class UV_LAYER_MANAGER_OT_straighten_vertices(bpy.types.Operator):
    bl_idname = "uv_layer_manager.straighten_vertices"
    bl_label = "斜向拉直"
    bl_description = "拖拽鼠标手动控制拉直方向（类似 FFD），或按设置使用自动/活动边/轴向/角度；面选择模式下不生效"
    bl_options = {'REGISTER', 'UNDO'}

    _objects = []
    _direction = None
    _draw_handle = None

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'

    def invoke(self, context, event):
        direction_mode = getattr(context.scene, "uvlm_straighten_direction", 'MANUAL')
        if direction_mode == 'MANUAL':
            if context.area is None or context.area.type != 'VIEW_3D':
                self.report({'WARNING'}, "手动控制需要在 3D 视图中使用")
                return {'CANCELLED'}
            if not self._capture(context):
                return {'CANCELLED'}
            self._direction = self._direction_from_mouse(context, event)
            context.window_manager.modal_handler_add(self)
            self._add_draw_handler(context)
            self._apply_preview(context)
            return {'RUNNING_MODAL'}
        return self.execute(context)

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self._direction = self._direction_from_mouse(context, event)
            self._apply_preview(context)
            try:
                context.area.tag_redraw()
            except Exception:
                pass
            return {'RUNNING_MODAL'}
        if event.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            count = sum(len(data["verts"]) for data in self._objects)
            self._remove_draw_handler()
            self._objects = []
            self._direction = None
            self.report({'INFO'}, f"已斜向拉直 {count} 个顶点")
            return {'FINISHED'}
        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._restore_original(context)
            self._remove_draw_handler()
            self._objects = []
            self._direction = None
            self.report({'WARNING'}, "已取消斜向拉直")
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        try:
            self._restore_original(context)
        except Exception:
            pass
        self._remove_draw_handler()
        self._objects = []
        self._direction = None

    def _capture(self, context):
        """收集所有编辑物体的选中顶点、原始坐标和中心点。"""
        select_mode = context.tool_settings.mesh_select_mode
        self._objects = []
        for obj in context.objects_in_mode_unique_data:
            if obj.type != 'MESH' or obj.mode != 'EDIT':
                continue
            bm = bmesh.from_edit_mesh(obj.data)
            if select_mode[2] and any(f.select and not f.hide for f in bm.faces):
                self.report(
                    {'WARNING'},
                    "面选择模式下不会拉直，请切换为顶点或边选择模式",
                )
                return False
            if select_mode[1]:
                # 边选择模式：收集选中边上的顶点（去重）
                selected_map = {}
                for edge in bm.edges:
                    if edge.select and not edge.hide:
                        for v in edge.verts:
                            if not v.hide:
                                selected_map[v.index] = v
                selected = list(selected_map.values())
            else:
                selected = [v for v in bm.verts if v.select and not v.hide]
            if len(selected) < 3:
                continue
            pivot = mathutils.Vector((0.0, 0.0, 0.0))
            for v in selected:
                pivot += v.co
            pivot /= len(selected)
            self._objects.append({
                "obj": obj,
                "verts": selected,
                "originals": [v.co.copy() for v in selected],
                "pivot": pivot,
            })
        if not self._objects:
            self.report({'WARNING'}, "请至少选择 3 个顶点")
            return False
        return True

    def _direction_from_mouse(self, context, event):
        """把鼠标位置映射为穿过选中中心、垂直于视线的 3D 方向。"""
        from bpy_extras import view3d_utils
        area = context.area
        win_region = None
        rv3d = None
        for region in area.regions:
            if region.type == 'WINDOW':
                win_region = region
                rv3d = getattr(region, "data", None)
                break
        if win_region is None or rv3d is None or not hasattr(rv3d, "view_matrix"):
            return self._direction or mathutils.Vector((1.0, 0.0, 0.0))

        mouse = (event.mouse_x - win_region.x, event.mouse_y - win_region.y)
        origin_3d = view3d_utils.region_2d_to_origin_3d(win_region, rv3d, mouse)
        vector_3d = view3d_utils.region_2d_to_vector_3d(win_region, rv3d, mouse)
        pivot_world = self._objects[0]["obj"].matrix_world @ self._objects[0]["pivot"]
        view_dir = rv3d.view_rotation @ mathutils.Vector((0.0, 0.0, -1.0))
        denom = vector_3d.dot(view_dir)
        if abs(denom) < 1e-9:
            return self._direction or mathutils.Vector((1.0, 0.0, 0.0))
        t = (pivot_world - origin_3d).dot(view_dir) / denom
        point = origin_3d + vector_3d * t
        direction = point - pivot_world
        if direction.length_squared < 1e-12:
            return self._direction or mathutils.Vector((1.0, 0.0, 0.0))
        return direction.normalized()

    def _apply_preview(self, context):
        if self._direction is None:
            return
        for data in self._objects:
            obj = data["obj"]
            local_dir = (obj.matrix_world.inverted().to_3x3() @ self._direction).normalized()
            pivot = data["pivot"]
            for v, original in zip(data["verts"], data["originals"]):
                offset = original - pivot
                v.co = pivot + local_dir * offset.dot(local_dir)
            bmesh.update_edit_mesh(obj.data)

    def _restore_original(self, context):
        for data in self._objects:
            obj = data["obj"]
            if obj.name not in bpy.data.objects:
                continue
            bm = bmesh.from_edit_mesh(obj.data)
            for v, original in zip(data["verts"], data["originals"]):
                try:
                    v.co = original
                except Exception:
                    pass
            bmesh.update_edit_mesh(obj.data)

    def _add_draw_handler(self, context):
        if self._draw_handle is not None:
            return
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_straighten_line,
            (self,),
            'WINDOW',
            'POST_VIEW',
        )

    def _remove_draw_handler(self):
        if self._draw_handle is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            except Exception:
                pass
            self._draw_handle = None

    def execute(self, context):
        select_mode = context.tool_settings.mesh_select_mode
        direction_mode = getattr(context.scene, "uvlm_straighten_direction", 'MANUAL')
        if direction_mode == 'MANUAL':
            direction_mode = 'AUTO'
        angle_deg = getattr(context.scene, "uvlm_straighten_angle", 45.0)

        # 前置校验：面选择会把整片面拉成一条线，先检查再修改
        has_direction_edge = False
        for obj in context.objects_in_mode_unique_data:
            if obj.type != 'MESH' or obj.mode != 'EDIT':
                continue
            bm = bmesh.from_edit_mesh(obj.data)
            if select_mode[2] and any(f.select and not f.hide for f in bm.faces):
                self.report(
                    {'WARNING'},
                    "面选择模式下不会拉直，请切换为顶点或边选择模式",
                )
                return {'CANCELLED'}
            if direction_mode == 'EDGE':
                active_edge = getattr(bm.select_history, "active", None)
                if isinstance(active_edge, bmesh.types.BMEdge):
                    has_direction_edge = True
                if any(e.select and not e.hide for e in bm.edges):
                    has_direction_edge = True
        if direction_mode == 'EDGE' and not has_direction_edge:
            self.report({'WARNING'}, "请先选中一条边作为拉直方向参考")
            return {'CANCELLED'}

        straightened = 0
        for obj in context.objects_in_mode_unique_data:
            if obj.type != 'MESH' or obj.mode != 'EDIT':
                continue
            bm = bmesh.from_edit_mesh(obj.data)
            if select_mode[1]:
                # 边选择模式：收集选中边上的顶点（去重）
                selected_map = {}
                for edge in bm.edges:
                    if edge.select and not edge.hide:
                        for v in edge.verts:
                            if not v.hide:
                                selected_map[v.index] = v
                selected = list(selected_map.values())
            else:
                selected = [v for v in bm.verts if v.select and not v.hide]
            if len(selected) < 3:
                continue

            if direction_mode == 'AUTO':
                # 用最远的两个顶点确定拉直方向，端点保持不动
                p0, p1 = None, None
                max_dist_sq = -1.0
                count = len(selected)
                for i in range(count):
                    vi = selected[i]
                    for j in range(i + 1, count):
                        vj = selected[j]
                        dist_sq = (vi.co - vj.co).length_squared
                        if dist_sq > max_dist_sq:
                            max_dist_sq = dist_sq
                            p0, p1 = vi.co, vj.co
                origin = p0
                direction = p1 - p0
            elif direction_mode == 'EDGE':
                active_edge = getattr(bm.select_history, "active", None)
                if not isinstance(active_edge, bmesh.types.BMEdge):
                    active_edge = None
                    for edge in bm.edges:
                        if edge.select and not edge.hide:
                            active_edge = edge
                            break
                if active_edge is None:
                    continue
                origin = active_edge.verts[0].co.copy()
                direction = active_edge.verts[1].co - active_edge.verts[0].co
            elif direction_mode in {'X', 'Y', 'Z'}:
                axis = {'X': (1.0, 0.0, 0.0), 'Y': (0.0, 1.0, 0.0), 'Z': (0.0, 0.0, 1.0)}[direction_mode]
                origin = mathutils.Vector((0.0, 0.0, 0.0))
                for v in selected:
                    origin += v.co
                origin /= len(selected)
                direction = mathutils.Vector(axis)
            else:
                # 自定义角度：绕 Z 轴（俯视平面），X 正方向为 0°，逆时针
                rad = math.radians(angle_deg)
                origin = mathutils.Vector((0.0, 0.0, 0.0))
                for v in selected:
                    origin += v.co
                origin /= len(selected)
                direction = mathutils.Vector((math.cos(rad), math.sin(rad), 0.0))

            moved = project_verts_onto_line(selected, origin, direction)
            if moved == 0:
                continue
            bmesh.update_edit_mesh(obj.data)
            straightened += moved

        if straightened == 0:
            self.report({'WARNING'}, "请至少选择 3 个顶点")
            return {'CANCELLED'}
        self.report({'INFO'}, f"已斜向拉直 {straightened} 个顶点")
        return {'FINISHED'}


def _draw_straighten_line(op):
    """在视口中绘制拉直方向的参考线。"""
    import gpu
    from gpu.types import GPUBatch, GPUVertBuf, GPUVertFormat
    if op._direction is None or not op._objects:
        return
    pivot_world = op._objects[0]["obj"].matrix_world @ op._objects[0]["pivot"]
    direction = op._direction
    length = 1000.0
    coords = (
        (pivot_world - direction * length).to_tuple(),
        (pivot_world + direction * length).to_tuple(),
    )
    fmt = GPUVertFormat()
    fmt.attr_add(id="pos", comp='3', dtype='f32')
    vbuf = GPUVertBuf(fmt, 2)
    vbuf.attribute_fill(0, coords)
    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    batch = GPUBatch(type='LINES', buf=vbuf)
    shader.bind()
    shader.uniform_float("color", (1.0, 0.45, 0.1, 1.0))
    batch.draw(shader)


class UV_LAYER_MANAGER_OT_set_straighten_direction(bpy.types.Operator):
    bl_idname = "uv_layer_manager.set_straighten_direction"
    bl_label = "斜向拉直设置"
    bl_description = "设置斜向拉直的方向来源和自定义角度"
    bl_options = {'REGISTER'}

    direction: bpy.props.EnumProperty(
        name="方向来源",
        items=STRAIGHTEN_DIRECTION_ITEMS,
        default='MANUAL',
    )
    angle: bpy.props.FloatProperty(
        name="角度°",
        description="绕 Z 轴（俯视平面）的角度，X 正方向为 0°，逆时针",
        default=45.0,
        min=-360.0,
        max=360.0,
        step=5,
        precision=1,
    )

    def invoke(self, context, event):
        scene = context.scene
        self.direction = getattr(scene, "uvlm_straighten_direction", 'MANUAL')
        self.angle = getattr(scene, "uvlm_straighten_angle", 45.0)
        if context.area is None:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        self.layout.prop(self, "direction", text="方向来源")
        if self.direction == 'ANGLE':
            self.layout.prop(self, "angle", text="角度°")
        self.layout.separator()
        hint = (
            "手动控制：点按钮后拖拽鼠标定义方向（类似 FFD）；"
            "自动：最远两点，端点不动；"
            "沿活动边：需先选一条边作为方向；"
            "X/Y/Z 与自定义角度：直线过选中顶点中心"
        )
        self.layout.label(text=hint, icon='INFO')

    def execute(self, context):
        context.scene.uvlm_straighten_direction = self.direction
        if self.direction == 'ANGLE':
            context.scene.uvlm_straighten_angle = self.angle
        label = {item[0]: item[1] for item in STRAIGHTEN_DIRECTION_ITEMS}.get(
            self.direction, self.direction
        )
        self.report({'INFO'}, f"斜向拉直方向已设为：{label}")
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
    bl_label = "清理法向与切线"
    bl_description = "清除选中模型的自定义法向和切线缓存，再添加 Smooth by Angle（保留锐边）"
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

            self.report({'INFO'}, f"已清理 {len(touched_meshes)} 个网格的法向与切线，应用 Smooth by Angle（{angle_degrees:g}°）")
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
    angle: bpy.props.FloatProperty(
        name="自定义法向角度",
        description="自定义清理后的法向角度",
        default=180.0,
        min=0.0,
        max=180.0,
    )

    def invoke(self, context, event):
        if self.preset != C.NORMAL_ANGLE_PRESET_CUSTOM:
            return self.execute(context)
        self.angle = context.scene.normal_angle_custom
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "angle", text="角度")

    def execute(self, context):
        valid_presets = {'180', '30', '90', C.NORMAL_ANGLE_PRESET_CUSTOM}
        if self.preset not in valid_presets:
            self.report({'WARNING'}, "无效的法向角度预设")
            return {'CANCELLED'}
        if self.preset == C.NORMAL_ANGLE_PRESET_CUSTOM:
            context.scene.normal_angle_custom = self.angle
        context.scene.normal_angle_preset = self.preset
        return bpy.ops.uv_layer_manager.clean_normals()


# ============================================================
# Property registration
# ============================================================

def register_properties():
    bpy.types.Scene.uvlm_straighten_direction = bpy.props.EnumProperty(
        name="斜向拉直方向",
        description="斜向拉直的方向来源",
        items=STRAIGHTEN_DIRECTION_ITEMS,
        default='MANUAL',
    )
    bpy.types.Scene.uvlm_straighten_angle = bpy.props.FloatProperty(
        name="斜向拉直角度",
        description="自定义角度模式：绕 Z 轴（俯视平面），X 正方向为 0°，逆时针",
        default=45.0,
        min=-360.0,
        max=360.0,
        step=5,
        precision=1,
    )


def unregister_properties():
    if hasattr(bpy.types.Scene, 'uvlm_straighten_direction'):
        del bpy.types.Scene.uvlm_straighten_direction
    if hasattr(bpy.types.Scene, 'uvlm_straighten_angle'):
        del bpy.types.Scene.uvlm_straighten_angle
