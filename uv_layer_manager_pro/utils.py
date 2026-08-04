# -*- coding: utf-8 -*-
"""
UV Layer Manager - Shared Utility Functions
"""
from contextlib import contextmanager
import re

import bpy
import bmesh
from . import constants as C


_NUMERIC_MATERIAL_SUFFIX_RE = re.compile(r"\.\d{3}$")


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
    for obj in scene.objects:
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


def get_material_library_path(material):
    """Return the stored library path used to distinguish linked materials."""
    library = getattr(material, "library", None)
    return getattr(library, "filepath", "") if library else ""


def find_material(material_name, library_path=""):
    """Find a material by its exact name and owning library path."""
    for material in bpy.data.materials:
        if material.name != material_name:
            continue
        if get_material_library_path(material) == library_path:
            return material
    return None


def is_same_material(first, second):
    if first is None or second is None:
        return first is second
    try:
        return first.as_pointer() == second.as_pointer()
    except (AttributeError, ReferenceError):
        return first == second


def get_material_base_name(name):
    # Handle multiple suffixes like Material.001.002 → Material
    while re.search(r"\.\d{3}$", name):
        name = re.sub(r"\.\d{3}$", "", name)
    return name


def build_material_display_groups(objects):
    """Group material slots for UI display without modifying datablocks."""
    groups = {}
    for obj in objects:
        for slot_index, slot in enumerate(obj.material_slots):
            material = slot.material
            if material is None:
                continue
            family_name = get_material_base_name(material.name)
            library = getattr(material, "library", None)
            library_path = getattr(library, "filepath", "") if library else ""
            key = f"{library_path}|{family_name.casefold()}"
            group = groups.setdefault(
                key,
                {
                    "key": key,
                    "name": family_name,
                    "library_path": library_path,
                    "members": {},
                    "slots": [],
                },
            )
            group["slots"].append((obj, slot_index))
            member = group["members"].setdefault(
                material.as_pointer(),
                {"material": material, "slots": []},
            )
            member["slots"].append((obj, slot_index))

    result = []
    for group in groups.values():
        group["members"] = sorted(
            group["members"].values(),
            key=lambda member: member["material"].name.casefold(),
        )
        group["object_count"] = len({obj.as_pointer() for obj, _ in group["slots"]})
        group["slot_count"] = len(group["slots"])
        for member in group["members"]:
            member["object_count"] = len({obj.as_pointer() for obj, _ in member["slots"]})
            member["slot_count"] = len(member["slots"])
        result.append(group)
    return sorted(result, key=lambda group: (group["name"].casefold(), group["library_path"]))


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


def _merge_duplicate_material_slots(mesh):
    """合并单个网格中指向同一材质的重复槽位，返回合并数。"""
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

    mesh.update()
    return len(duplicate_indices)


def merge_duplicate_material_slots(obj):
    mesh = obj.data
    merged = _merge_duplicate_material_slots(mesh)
    if merged and obj.active_material_index >= len(mesh.materials):
        obj.active_material_index = max(0, len(mesh.materials) - 1)
    return merged


def replace_material_slots(objects, source_material, target_material):
    """Replace exact source-material slots and preserve slot/face indices."""
    replaced_slots = 0
    changed_objects = set()
    changed_meshes = {}

    for obj in objects:
        if obj is None or obj.type != 'MESH' or obj.data is None:
            continue
        object_changed = False
        for slot in obj.material_slots:
            if not is_same_material(slot.material, source_material):
                continue
            try:
                slot.material = target_material
            except (AttributeError, RuntimeError, TypeError):
                continue
            replaced_slots += 1
            object_changed = True
        if object_changed:
            changed_objects.add(obj.as_pointer())
            changed_meshes[obj.data.as_pointer()] = obj.data

    for mesh in changed_meshes.values():
        mesh.update()
    if replaced_slots:
        invalidate_duplicate_material_cache()
        C._draw_cache.clear()
    return replaced_slots, len(changed_objects)


def _material_slot_indices(obj, material):
    return {
        index
        for index, slot in enumerate(obj.material_slots)
        if is_same_material(slot.material, material)
    }


def _mesh_selection_groups(objects, material):
    groups = {}
    for obj in objects:
        if obj is None or obj.type != 'MESH' or obj.data is None:
            continue
        mesh = obj.data
        group = groups.setdefault(
            mesh.as_pointer(),
            {"mesh": mesh, "objects": [], "indices": set()},
        )
        indices = _material_slot_indices(obj, material)
        group["objects"].append((obj, indices))
        group["indices"].update(indices)
    return list(groups.values())


def _clear_mesh_selection(mesh):
    for vertex in mesh.vertices:
        vertex.select = False
    for edge in mesh.edges:
        edge.select = False
    for polygon in mesh.polygons:
        polygon.select = False
    mesh.update()


def select_material_faces(context, objects, material):
    """Select faces using an exact material across selected mesh objects.

    Shared meshes are processed once. If object-level material links differ,
    the shared mesh uses the union of matching slot indices because Blender
    cannot store a different edit-mode face selection per object instance.
    """
    groups = _mesh_selection_groups(objects, material)
    if not groups:
        return 0, 0

    matching_objects = set()
    matching_active = None
    estimated_faces = 0
    for group in groups:
        mesh = group["mesh"]
        matching_indices = group["indices"]
        matching_face_indices = {
            polygon.index
            for polygon in mesh.polygons
            if polygon.material_index in matching_indices
        }
        estimated_faces += len(matching_face_indices)
        if not matching_face_indices:
            continue
        for obj, object_indices in group["objects"]:
            if any(mesh.polygons[index].material_index in object_indices for index in matching_face_indices):
                matching_objects.add(obj.as_pointer())
                if matching_active is None:
                    matching_active = obj

    active_object = context.view_layer.objects.active
    was_edit_mode = bool(active_object and active_object.mode == 'EDIT')

    if estimated_faces and not was_edit_mode and matching_active is not None:
        context.view_layer.objects.active = matching_active
        context.tool_settings.mesh_select_mode = (False, False, True)
        try:
            bpy.ops.object.mode_set(mode='EDIT')
        except RuntimeError:
            pass

    selected_faces = 0
    context.tool_settings.mesh_select_mode = (False, False, True)
    for group in groups:
        mesh = group["mesh"]
        matching_indices = group["indices"]
        edit_object = next((obj for obj, _ in group["objects"] if obj.mode == 'EDIT'), None)
        if edit_object is not None:
            try:
                bm = bmesh.from_edit_mesh(mesh)
                for vertex in bm.verts:
                    vertex.select_set(False)
                for edge in bm.edges:
                    edge.select_set(False)
                for face in bm.faces:
                    face.select_set(False)
                for face in bm.faces:
                    if face.material_index in matching_indices:
                        face.select_set(True)
                        selected_faces += 1
                bm.select_flush_mode()
                bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
                continue
            except (ReferenceError, RuntimeError):
                pass

        _clear_mesh_selection(mesh)
        for polygon in mesh.polygons:
            if polygon.material_index in matching_indices:
                polygon.select = True
                selected_faces += 1
        mesh.update()

    if selected_faces and matching_active is not None:
        context.view_layer.objects.active = matching_active
    C._draw_cache.clear()
    return selected_faces, len(matching_objects)


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


def clear_material_replace_target(context=None):
    """Release all plugin-owned temporary material ID pointers."""
    context = context or bpy.context
    cleared = False
    window_managers = list(getattr(bpy.data, "window_managers", ()))
    current_window_manager = getattr(context, "window_manager", None)
    if current_window_manager is not None and current_window_manager not in window_managers:
        window_managers.append(current_window_manager)
    for window_manager in window_managers:
        if not hasattr(window_manager, "uvlm_material_replace_target"):
            continue
        try:
            if window_manager.uvlm_material_replace_target is not None:
                window_manager.uvlm_material_replace_target = None
                cleared = True
        except (AttributeError, ReferenceError, TypeError):
            continue
    return cleared


def _clear_transient_material_references(material):
    """Drop plugin UI pointers that should not count as real material use."""
    for scene in bpy.data.scenes:
        if not hasattr(scene, "material_manager_material"):
            continue
        try:
            if is_same_material(scene.material_manager_material, material):
                scene.material_manager_material = None
        except (AttributeError, ReferenceError, TypeError):
            continue

    for window_manager in getattr(bpy.data, "window_managers", ()):
        if not hasattr(window_manager, "uvlm_material_replace_target"):
            continue
        try:
            if is_same_material(window_manager.uvlm_material_replace_target, material):
                window_manager.uvlm_material_replace_target = None
        except (AttributeError, ReferenceError, TypeError):
            continue


def purge_unused_duplicate_materials(context=None):
    """Delete only unused, local numeric-suffix materials from known families."""
    local_materials = [
        material
        for material in bpy.data.materials
        if getattr(material, "library", None) is None
    ]
    families = {}
    for material in local_materials:
        families.setdefault(get_material_base_name(material.name), []).append(material)

    candidates = []
    for base_name, family in families.items():
        suffixed = [material for material in family if _NUMERIC_MATERIAL_SUFFIX_RE.search(material.name)]
        if not suffixed:
            continue
        has_base_material = any(material.name == base_name for material in family)
        if not has_base_material and len(suffixed) < 2:
            continue
        for material in suffixed:
            if getattr(material, "use_fake_user", False):
                continue
            if getattr(material, "asset_data", None) is not None:
                continue
            _clear_transient_material_references(material)
            if material.users != 0:
                continue
            candidates.append(material)

    deleted = 0
    for material in candidates:
        try:
            bpy.data.materials.remove(material, do_unlink=False)
            deleted += 1
        except (ReferenceError, RuntimeError, TypeError):
            continue
    if deleted:
        invalidate_duplicate_material_cache()
        C._draw_cache.clear()
    return deleted


def purge_orphan_materials(context=None):
    """Compatibility wrapper for the narrowed duplicate-material cleanup."""
    return purge_unused_duplicate_materials(context)


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


def unify_duplicate_materials(context=None):
    """Compatibility wrapper delegating to the named-family unification."""
    return unify_named_material_families(context)


def unify_named_material_families(context=None):
    """全文件同名族材质统一：Material.001/002 -> Material。

    - 以去掉 .001/.002 等数字后缀的基础名分组（仅本地材质）；
    - 每组保留“无后缀基础名”材质（找不到时取名字最短者）为唯一材质；
    - 所有网格的材质槽（无论物体是否选中）引用重复材质时重定向到唯一材质；
    - 重定向后合并所有网格中指向同一材质的重复槽位；
    - 删除重复材质（含假用户或已赋给物体的），链接库材质不参与，Asset 材质只重定向不删除。
    返回 (重定向槽位数, 合并槽位数, 删除材质数)。
    """
    local_materials = [
        material
        for material in bpy.data.materials
        if getattr(material, "library", None) is None
    ]
    groups = {}
    for material in local_materials:
        groups.setdefault(get_material_base_name(material.name), []).append(material)

    dup_map = {}
    for base_name, materials in groups.items():
        if len(materials) < 2:
            continue
        canonical = None
        for material in materials:
            if material.name == base_name:
                canonical = material
                break
        if canonical is None:
            canonical = sorted(materials, key=lambda item: (len(item.name), item.name))[0]
        for material in materials:
            if material != canonical:
                dup_map[material] = canonical

    if not dup_map:
        return 0, 0, 0

    remapped_slots = 0
    for mesh in bpy.data.meshes:
        for index, material in enumerate(mesh.materials):
            canonical = dup_map.get(material)
            if canonical is not None:
                try:
                    mesh.materials[index] = canonical
                except Exception:
                    continue
                remapped_slots += 1

    merged_slots = 0
    for mesh in bpy.data.meshes:
        merged_slots += _merge_duplicate_material_slots(mesh)

    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data is not None:
            slot_count = len(obj.data.materials)
            if obj.active_material_index >= slot_count:
                obj.active_material_index = max(0, slot_count - 1)

    deleted = 0
    for material in list(dup_map):
        if getattr(material, "asset_data", None) is not None:
            continue
        try:
            bpy.data.materials.remove(material)
            deleted += 1
        except (ReferenceError, RuntimeError, TypeError):
            pass

    invalidate_duplicate_material_cache()
    C._draw_cache.clear()
    return remapped_slots, merged_slots, deleted


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
