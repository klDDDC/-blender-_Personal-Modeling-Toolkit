# -*- coding: utf-8 -*-
"""
UV Layer Manager - Vertex Color Node Injection
"""
import bpy
from . import constants as C
from . import utils as U


# ============================================================
# VertexColorState — 顶点颜色节点注入的全局状态
# ============================================================

class VertexColorState:
    """封装顶点颜色节点注入前保存的原始连接。"""
    _links = {}  # {mat.as_pointer(): (from_node_name, socket_identifier, from_socket)}

    @classmethod
    def save(cls, mat_ptr, data):
        cls._links[mat_ptr] = data

    @classmethod
    def has(cls, mat_ptr):
        return mat_ptr in cls._links

    @classmethod
    def get(cls, mat_ptr):
        return cls._links.get(mat_ptr)

    @classmethod
    def delete(cls, mat_ptr):
        return cls._links.pop(mat_ptr, None)

    @classmethod
    def clear_all(cls):
        cls._links.clear()


def _find_shader_node(node_tree):
    if node_tree is None:
        return None
    for node in node_tree.nodes:
        if node.type != 'OUTPUT_MATERIAL':
            continue
        surface_socket = node.inputs.get("Surface")
        if surface_socket is None:
            continue
        for link in surface_socket.links:
            return link.from_node
    return None


def _get_color_socket(shader_node):
    if shader_node is None:
        return None
    return shader_node.inputs.get("Base Color")


def _save_original_link(mat, color_socket):
    if color_socket is None:
        return
    mat_ptr = mat.as_pointer()
    if VertexColorState.has(mat_ptr):
        return
    if color_socket.links:
        link = list(color_socket.links)[0]
        from_node = link.from_node
        from_socket = link.from_socket
        socket_identifier = from_socket.identifier if hasattr(from_socket, 'identifier') else ""
        VertexColorState.save(mat_ptr, (from_node.name, socket_identifier, from_socket))


def _remove_uvlm_nodes_from_tree(node_tree, mat_ptr):
    if node_tree is None:
        return
    removed = False
    for node in list(node_tree.nodes):
        if node.name.startswith(C.UVLM_NODE_PREFIX):
            node_tree.nodes.remove(node)
            removed = True
    VertexColorState.delete(mat_ptr)
    return removed


def _inject_vertex_color_node(mat, mode):
    node_tree = mat.node_tree
    if node_tree is None:
        return
    mat_ptr = mat.as_pointer()

    shader_node = _find_shader_node(node_tree)
    if shader_node is None:
        return
    color_socket = _get_color_socket(shader_node)
    if color_socket is None:
        return

    _save_original_link(mat, color_socket)
    _remove_uvlm_nodes_from_tree(node_tree, mat_ptr)

    for link_from in list(color_socket.links):
        node_tree.links.remove(link_from)

    vc_node = node_tree.nodes.new('ShaderNodeVertexColor')
    vc_node.name = f"{C.UVLM_NODE_PREFIX}{mat.name}"
    vc_node.label = mat.name
    vc_node.location = (shader_node.location.x - 300, shader_node.location.y)

    if mode == 'COLOR':
        vc_node.layer_name = "Col"
        node_tree.links.new(vc_node.outputs["Color"], color_socket)
    elif mode == 'ALPHA':
        vc_node.layer_name = "Col"
        separate = node_tree.nodes.new('ShaderNodeSeparateColor')
        separate.name = f"{C.UVLM_NODE_PREFIX}Sep_{mat.name}"
        separate.location = (vc_node.location.x + 150, vc_node.location.y)
        node_tree.links.new(vc_node.outputs["Color"], separate.inputs["Color"])
        node_tree.links.new(separate.outputs["Alpha"], color_socket)
    elif mode == 'ID':
        vc_node.layer_name = "Col"
        separate = node_tree.nodes.new('ShaderNodeSeparateColor')
        separate.name = f"{C.UVLM_NODE_PREFIX}Sep_{mat.name}"
        separate.location = (vc_node.location.x + 150, vc_node.location.y)
        combine = node_tree.nodes.new('ShaderNodeCombineColor')
        combine.name = f"{C.UVLM_NODE_PREFIX}Cmb_{mat.name}"
        combine.location = (separate.location.x + 150, separate.location.y)
        node_tree.links.new(vc_node.outputs["Color"], separate.inputs["Color"])
        node_tree.links.new(separate.outputs["Red"], combine.inputs["Red"])
        node_tree.links.new(separate.outputs["Green"], combine.inputs["Green"])
        node_tree.links.new(separate.outputs["Blue"], combine.inputs["Blue"])
        node_tree.links.new(combine.outputs["Color"], color_socket)


def _apply_vertex_color_nodes(context, mode):
    for obj in U.get_selected_mesh_objects(context):
        for mat_slot in obj.material_slots:
            mat = mat_slot.material
            if mat is None:
                continue
            if not mat.use_nodes:
                continue
            _inject_vertex_color_node(mat, mode)


def has_uvlm_vertex_color_nodes(obj):
    if obj.type != 'MESH':
        return False
    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if mat is None or not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.name.startswith(C.UVLM_NODE_PREFIX):
                return True
    return False


def _clear_selected_vertex_color_nodes(context):
    for obj in U.get_selected_mesh_objects(context):
        if obj.type != 'MESH':
            continue
        for mat_slot in obj.material_slots:
            mat = mat_slot.material
            if mat is None or not mat.use_nodes:
                continue
            mat_ptr = mat.as_pointer()
            _remove_uvlm_nodes_from_tree(mat.node_tree, mat_ptr)
            if VertexColorState.has(mat_ptr):
                from_node_name, socket_identifier, from_socket = VertexColorState.get(mat_ptr)
                shader_node = _find_shader_node(mat.node_tree)
                if shader_node is not None:
                    color_socket = _get_color_socket(shader_node)
                    if color_socket is not None:
                        for link in list(color_socket.links):
                            mat.node_tree.links.remove(link)
                        from_node = mat.node_tree.nodes.get(from_node_name)
                        if from_node and from_socket:
                            try:
                                mat.node_tree.links.new(from_socket, color_socket)
                            except (RuntimeError, ReferenceError):
                                pass
                VertexColorState.delete(mat_ptr)


def set_material_view_mode(context, mode):
    scene = context.scene
    current_mode = getattr(scene, "material_view_mode", 'MATERIAL')
    next_mode = 'MATERIAL' if current_mode == mode else mode

    if next_mode == 'MATERIAL':
        from . import material_id as MID
        MID.restore_material_id_colors(context)
        _clear_selected_vertex_color_nodes(context)
        U.set_material_color_view(context)
    elif next_mode == 'ID':
        from . import material_id as MID
        MID.restore_material_id_colors(context)
        MID.prepare_material_id_colors(context)
        U.set_material_color_view(context)
    elif next_mode in ('COLOR', 'ALPHA'):
        from . import material_id as MID
        MID.restore_material_id_colors(context)
        _clear_selected_vertex_color_nodes(context)
        _apply_vertex_color_nodes(context, next_mode)
        U.set_material_color_view(context)
    else:
        # Fallback: MATERIAL
        _clear_selected_vertex_color_nodes(context)
        U.set_material_color_view(context)
        next_mode = 'MATERIAL'

    scene.material_view_mode = next_mode
    # 不在此处调用 tag_all_view3d_redraw — 由调用者负责
    return 0, next_mode


def get_active_color_attribute(mesh):
    try:
        for attr in mesh.attributes:
            if attr.domain == 'CORNER' and attr.data_type == 'FLOAT_COLOR' and attr.active_color_attribute:
                return attr
    except Exception:
        pass
    try:
        color_attributes = getattr(mesh, "color_attributes", None)
        if color_attributes is not None:
            return getattr(color_attributes, "active_color", None) or getattr(color_attributes, "active", None)
    except Exception:
        pass
    return None
