# -*- coding: utf-8 -*-
"""
UV Layer Manager - Shared Utility Functions
"""
from contextlib import contextmanager
import re

import bpy
import bmesh
from . import constants as C


# ============================================================
# Preferences helpers
# ============================================================

def get_prefs():
    try:
        return bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return None


def get_prefs_props():
    prefs = get_prefs()
    if prefs is None:
        return {}
    return {
        "confirm_open": getattr(prefs, "confirm_open", False),
        "auto_merge": getattr(prefs, "auto_merge", True),
        "protect_uv_area": getattr(prefs, "protect_uv_area", True),
        "uv_on_left": getattr(prefs, "uv_on_left", True),
    }


# ============================================================
# Scene/Mesh helpers
# ============================================================

def get_scene_max_uv_info(scene):
    max_count = 0
    max_name = ""
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.data is None:
            continue
        uv_count = len(obj.data.uv_layers)
        if uv_count > max_count:
            max_count = uv_count
            max_name = obj.name
    return max_count, max_name


def get_active_mesh(context):
    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return None, None
    mesh = obj.data
    if mesh is None:
        return obj, None
    return obj, mesh


def generate_uv_name(uv_layers):
    max_index = 0
    for layer in uv_layers:
        name = layer.name
        prefix = f"{C.UV_BASE_NAME}."
        if name.startswith(prefix):
            try:
                index = int(name[len(prefix):])
                max_index = max(max_index, index)
            except (ValueError, IndexError):
                continue
        elif name.startswith(C.UV_BASE_NAME) and len(name) > len(C.UV_BASE_NAME):
            try:
                index = int(name[len(C.UV_BASE_NAME):])
                max_index = max(max_index, index)
            except (ValueError, IndexError):
                continue
    return f"{C.UV_BASE_NAME}.{max_index + 1:03d}"


def is_uv_edit_active(context):
    space = getattr(context, "space_data", None)
    if space is None:
        return False
    for area in getattr(context.screen, "areas", []):
        if area.type == 'IMAGE_EDITOR':
            space = area.spaces.active
            if space and getattr(space, "mode", None) == 'UV':
                return True
    return False


def is_shader_edit_active(context):
    space = getattr(context, "space_data", None)
    if space is None:
        return False
    for area in getattr(context.screen, "areas", []):
        if area.type == 'NODE_EDITOR':
            space = area.spaces.active
            if space is not None and getattr(space, "tree_type", None) == 'ShaderNodeTree':
                return True
    return False


# ============================================================
# Mesh/Material helpers
# ============================================================

def get_selected_mesh_objects(context):
    return [obj for obj in context.selected_objects if obj.type == 'MESH' and obj.data is not None]


def get_material_base_name(name):
    # Handle multiple suffixes like Material.001.002 → Material
    while re.search(r"\.\d{3}$", name):
        name = re.sub(r"\.\d{3}$", "", name)
    return name


def ensure_material_slot(obj, material):
    mesh = obj.data
    for index, slot_material in enumerate(mesh.materials):
        if slot_material == material:
            return index
    mesh.materials.append(material)
    return len(mesh.materials) - 1


def get_used_material_indices(mesh):
    slot_count = len(mesh.materials)
    return {
        polygon.material_index
        for polygon in mesh.polygons
        if 0 <= polygon.material_index < slot_count
    }


def remove_unused_material_slots(obj):
    mesh = obj.data
    used_indices = get_used_material_indices(mesh)
    removed_count = 0
    for index in reversed(range(len(mesh.materials))):
        if index not in used_indices:
            mesh.materials.pop(index=index)
            removed_count += 1
    if removed_count:
        mesh.update()
    return removed_count


def merge_duplicate_material_slots(obj):
    mesh = obj.data
    first_slot_by_material = {}
    duplicate_indices = []

    for index, material in enumerate(mesh.materials):
        if material is None:
            continue
        key = material.as_pointer()
        first_index = first_slot_by_material.get(key)
        if first_index is None:
            first_slot_by_material[key] = index
            continue
        duplicate_indices.append(index)
        for polygon in mesh.polygons:
            if polygon.material_index == index:
                polygon.material_index = first_index

    if not duplicate_indices:
        return 0

    for remove_index in reversed(duplicate_indices):
        mesh.materials.pop(index=remove_index)
        for polygon in mesh.polygons:
            if polygon.material_index > remove_index:
                polygon.material_index -= 1

    if obj.active_material_index >= len(mesh.materials):
        obj.active_material_index = max(0, len(mesh.materials) - 1)
    mesh.update()
    return len(duplicate_indices)


def assign_material_to_object(obj, material):
    material_index = ensure_material_slot(obj, material)
    for polygon in obj.data.polygons:
        polygon.material_index = material_index
    obj.data.update()


def get_selected_polygon_indices(obj):
    return [polygon.index for polygon in obj.data.polygons if polygon.select]


def get_selected_face_material_index(obj):
    selected_polygons = get_selected_polygon_indices(obj)
    if not selected_polygons:
        return None
    material_indices = [obj.data.polygons[index].material_index for index in selected_polygons]
    if not material_indices:
        return None
    return material_indices[0]


def sync_active_material_to_selected_face(context):
    obj = context.active_object
    if obj is None or obj.type != 'MESH' or obj.data is None:
        return False

    material_index = None
    if obj.mode == 'EDIT':
        try:
            bm = bmesh.from_edit_mesh(obj.data)
            selected_faces = [face for face in bm.faces if face.select]
            if selected_faces:
                material_index = selected_faces[0].material_index
        except Exception:
            material_index = None
    else:
        material_index = get_selected_face_material_index(obj)

    if material_index is None:
        return False
    if 0 <= material_index < len(obj.material_slots):
        obj.active_material_index = material_index
        return True
    return False


def get_selected_face_material_index_for_ui(context, obj):
    if obj is None or obj.type != 'MESH' or obj.data is None:
        return None
    if context.active_object != obj:
        return None

    if obj.mode == 'EDIT':
        try:
            bm = bmesh.from_edit_mesh(obj.data)
            selected_faces = [face for face in bm.faces if face.select]
            if selected_faces:
                return selected_faces[0].material_index
        except Exception:
            return None
    return get_selected_face_material_index(obj)


def get_selected_face_material_index_cached(context, obj):
    cache_key = (obj.as_pointer() if obj else 0,)
    if cache_key in C._draw_cache:
        return C._draw_cache[cache_key]
    result = get_selected_face_material_index_for_ui(context, obj)
    C._draw_cache[cache_key] = result
    return result


def begin_draw_frame():
    C._draw_cache_frame += 1
    C._draw_cache.clear()


@contextmanager
def temporary_object_mode(context, mode='OBJECT', active_object=None, restore=True):
    active_object = active_object or context.view_layer.objects.active
    original_mode = active_object.mode if active_object else 'OBJECT'
    switched_mode = False

    if active_object and original_mode != mode:
        context.view_layer.objects.active = active_object
        bpy.ops.object.mode_set(mode=mode)
        switched_mode = True

    try:
        yield active_object, original_mode, switched_mode
    finally:
        if restore and switched_mode and active_object and active_object.name in bpy.data.objects:
            context.view_layer.objects.active = active_object
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except Exception:
                pass


def assign_material_to_selected_faces_or_object(context, objects, material):
    active_object = context.view_layer.objects.active
    with temporary_object_mode(context, 'OBJECT', active_object):
        total_faces = 0
        assigned_objects = 0
        selected_faces_by_object = {}
        for obj in objects:
            selected_faces = get_selected_polygon_indices(obj)
            selected_faces_by_object[obj] = selected_faces
            total_faces += len(selected_faces)

        for obj in objects:
            material_index = ensure_material_slot(obj, material)
            selected_faces = selected_faces_by_object[obj]
            if selected_faces:
                for polygon_index in selected_faces:
                    obj.data.polygons[polygon_index].material_index = material_index
            elif total_faces == 0:
                for polygon in obj.data.polygons:
                    polygon.material_index = material_index
            else:
                continue
            obj.active_material_index = material_index
            obj.data.update()
            assigned_objects += 1

        return assigned_objects, total_faces


def remove_material_from_object(obj, material):
    mesh = obj.data
    removed_count = 0
    for index in reversed(range(len(mesh.materials))):
        if mesh.materials[index] != material:
            continue
        for polygon in mesh.polygons:
            if polygon.material_index == index:
                polygon.material_index = 0
        mesh.materials.pop(index=index)
        removed_count += 1
    if removed_count:
        mesh.update()
    return removed_count


def remove_material_slot_from_object(obj, index):
    if index < 0 or index >= len(obj.data.materials):
        return False
    obj.data.materials.pop(index=index)
    if obj.active_material_index >= len(obj.data.materials):
        obj.active_material_index = max(0, len(obj.data.materials) - 1)
    obj.data.update()
    return True


def get_material_manager_target(context):
    obj = context.active_object
    if obj is not None and obj.type == 'MESH' and obj.active_material is not None:
        return obj.active_material
    return getattr(context.scene, "material_manager_material", None)


def get_duplicate_material_map():
    version = len(bpy.data.materials)
    if C._duplicate_material_map_cache is not None and C._duplicate_material_map_version == version:
        return C._duplicate_material_map_cache

    groups = {}
    for material in bpy.data.materials:
        groups.setdefault(get_material_base_name(material.name), []).append(material)

    duplicate_map = {}
    for base_name, materials in groups.items():
        if len(materials) < 2:
            continue
        canonical = bpy.data.materials.get(base_name) or sorted(materials, key=lambda item: (len(item.name), item.name))[0]
        for material in materials:
            if material != canonical:
                duplicate_map[material] = canonical

    C._duplicate_material_map_cache = duplicate_map
    C._duplicate_material_map_version = version
    return duplicate_map


def invalidate_duplicate_material_cache():
    C._duplicate_material_map_cache = None
    C._duplicate_material_map_version = -1


def set_material_color_view(context):
    if context.screen is None:
        return 0
    updated = 0
    for area in context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for space in area.spaces:
            if space.type != 'VIEW_3D':
                continue
            space.shading.type = 'SOLID'
            space.shading.color_type = 'MATERIAL'
            updated += 1
    return updated
