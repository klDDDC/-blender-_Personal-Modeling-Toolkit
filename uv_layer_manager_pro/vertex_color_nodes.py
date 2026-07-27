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
    _links = {}  # {mat.as_pointer(): (from_node_name, socket_identifier, socket_name)}

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
    if not color_socket.links:
        VertexColorState.save(mat_ptr, (None, "", ""))
        return
    link = list(color_socket.links)[0]
    from_socket = link.from_socket
    VertexColorState.save(
        mat_ptr,
        (
            link.from_node.name,
            getattr(from_socket, "identifier", ""),
            getattr(from_socket, "name", ""),
        ),
    )


def _remove_uvlm_nodes_from_tree(node_tree):
    if node_tree is None:
        return
    removed = False
    for node in list(node_tree.nodes):
        if node.name.startswith(C.UVLM_NODE_PREFIX):
            node_tree.nodes.remove(node)
            removed = True
    return removed


def _inject_vertex_color_node(mat, mode, attribute_name):
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
    _remove_uvlm_nodes_from_tree(node_tree)

    for link_from in list(color_socket.links):
        node_tree.links.remove(link_from)

    vc_node = node_tree.nodes.new('ShaderNodeVertexColor')
    vc_node.name = f"{C.UVLM_NODE_PREFIX}{mat.name}"
    vc_node.label = mat.name
    vc_node.location = (shader_node.location.x - 300, shader_node.location.y)

    vc_node.layer_name = attribute_name or ""

    if mode == 'COLOR':
        node_tree.links.new(vc_node.outputs["Color"], color_socket)
    elif mode == 'ALPHA':
        node_tree.links.new(vc_node.outputs["Alpha"], color_socket)
    elif mode == 'ID':
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
    touched_materials = set()
    for obj in U.get_selected_mesh_objects(context):
        attribute = get_active_color_attribute(obj.data)
        attribute_name = attribute.name if attribute is not None else ""
        for mat_slot in obj.material_slots:
            mat = mat_slot.material
            if mat is None:
                continue
            if not mat.use_nodes:
                continue
            mat_ptr = mat.as_pointer()
            if mat_ptr in touched_materials:
                continue
            touched_materials.add(mat_ptr)
            _inject_vertex_color_node(mat, mode, attribute_name)


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


def _find_output_socket(node, identifier, name):
    if node is None:
        return None
    for socket in node.outputs:
        if identifier and getattr(socket, "identifier", "") == identifier:
            return socket
    return node.outputs.get(name) if name else None


def _restore_material_vertex_color_nodes(mat):
    if mat is None or not mat.use_nodes or mat.node_tree is None:
        return False
    mat_ptr = mat.as_pointer()
    state = VertexColorState.get(mat_ptr)
    removed = _remove_uvlm_nodes_from_tree(mat.node_tree)
    if state is None:
        return bool(removed)

    shader_node = _find_shader_node(mat.node_tree)
    color_socket = _get_color_socket(shader_node)
    if color_socket is not None:
        for link in list(color_socket.links):
            mat.node_tree.links.remove(link)
        from_node_name, socket_identifier, socket_name = state
        from_node = mat.node_tree.nodes.get(from_node_name) if from_node_name else None
        from_socket = _find_output_socket(from_node, socket_identifier, socket_name)
        if from_socket is not None:
            try:
                mat.node_tree.links.new(from_socket, color_socket)
            except (RuntimeError, ReferenceError):
                pass
    VertexColorState.delete(mat_ptr)
    return True


def _clear_selected_vertex_color_nodes(context):
    touched_materials = set()
    for obj in U.get_selected_mesh_objects(context):
        for mat_slot in obj.material_slots:
            mat = mat_slot.material
            if mat is None:
                continue
            mat_ptr = mat.as_pointer()
            if mat_ptr in touched_materials:
                continue
            touched_materials.add(mat_ptr)
            _restore_material_vertex_color_nodes(mat)


def restore_all_vertex_color_nodes():
    for mat in bpy.data.materials:
        if mat is not None:
            _restore_material_vertex_color_nodes(mat)
    VertexColorState.clear_all()


def set_material_view_mode(context, mode, force=False):
    from . import material_id as MID

    scene = context.scene
    current_mode = getattr(scene, "material_view_mode", 'MATERIAL')
    next_mode = mode if force or current_mode != mode else 'MATERIAL'

    MID.restore_material_id_colors(context)
    _clear_selected_vertex_color_nodes(context)

    if next_mode == 'MATERIAL':
        pass
    elif next_mode == 'ID':
        MID.prepare_material_id_colors(context)
    elif next_mode in ('COLOR', 'ALPHA'):
        _apply_vertex_color_nodes(context, next_mode)
    else:
        next_mode = 'MATERIAL'

    updated = U.set_material_color_view(context)
    scene.material_view_mode = next_mode
    return updated, next_mode


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
