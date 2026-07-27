# -*- coding: utf-8 -*-
"""
UV Layer Manager - Merge Close Vertices
"""
import math
import bpy
from . import constants as C
from . import utils as U


# ============================================================
# Public helpers
# ============================================================

def get_close_snap_distance(scene):
    """Read distance in cm from scene property, return Blender Units."""
    value = getattr(scene, "close_snap_distance_cm", 0.1)
    # Convert cm -> BU (Blender 1 BU = 1 m, so 1 cm = 0.01 BU)
    return max(value * 0.01, 0.0)


def get_eligible_close_snap_vertices(obj, selected_indices=None, vertex_group_name=None):
    """
    Return set of vertex indices eligible for merge.
    Without a vertex-group filter, conditions are OR: boundary edge, sharp edge,
    or selected vertex. When a group is specified, it is a hard filter and the
    result is intersected with that object's positively weighted group members.
    Seam edges are intentionally excluded.
    """
    mesh = obj.data
    # Edge-face count for boundary detection
    edge_face_counts = {}
    for polygon in mesh.polygons:
        for edge_key in polygon.edge_keys:
            key = tuple(sorted(edge_key))
            edge_face_counts[key] = edge_face_counts.get(key, 0) + 1

    # Sharp edge attribute (from data-transfer etc.)
    sharp_edge_data = None
    try:
        sharp_attr = mesh.attributes.get("sharp_edge")
        if sharp_attr is not None:
            sharp_edge_data = sharp_attr.data
    except Exception:
        sharp_edge_data = None

    # Vertex group lookup
    eligible = set()

    # --- Boundary / Sharp edges (seam excluded) ---
    for edge_index, edge in enumerate(mesh.edges):
        v1, v2 = edge.vertices
        key = tuple(sorted((v1, v2)))
        is_boundary = edge_face_counts.get(key, 0) <= 1
        is_sharp = bool(getattr(edge, "use_edge_sharp", False) or getattr(edge, "use_sharp", False))
        if sharp_edge_data is not None and edge_index < len(sharp_edge_data):
            is_sharp = is_sharp or bool(getattr(sharp_edge_data[edge_index], "value", False))
        # Note: edge.use_seam is intentionally IGNORED
        if is_boundary or is_sharp:
            eligible.add(v1)
            eligible.add(v2)

    # --- Selected vertices (edit mode) ---
    if selected_indices:
        eligible.update(selected_indices)

    # --- Vertex group filter ---
    if vertex_group_name:
        vg = obj.vertex_groups.get(vertex_group_name)
        if vg is None:
            return set()
        group_vertices = {
            vert.index
            for vert in mesh.vertices
            if any(g.group == vg.index and g.weight > 0 for g in vert.groups)
        }
        eligible.intersection_update(group_vertices)

    return eligible


def snap_close_vertices_in_objects(objects, distance_bu, selected_map=None, vertex_group_name=None):
    """
    Merge eligible vertices across objects by moving them to group center.
    Does NOT delete topology (no remove_doubles).

    Args:
        objects: list of bpy.types.Object (mesh)
        distance_bu: merge threshold in Blender Units
        selected_map: dict {mesh.as_pointer(): set(vertex_indices)} from edit mode
        vertex_group_name: str, optional vertex group filter

    Returns:
        (touched_mesh_count, total_vertex_count, total_group_count)
    """
    if distance_bu <= 0.0:
        return 0, 0, 0

    candidates = []
    seen_mesh_vertices = set()

    for obj in objects:
        mesh = obj.data
        if mesh is None:
            continue

        mesh_key = mesh.as_pointer()
        sel = (selected_map or {}).get(mesh_key)
        eligible = get_eligible_close_snap_vertices(obj, sel, vertex_group_name)
        if not eligible:
            continue

        matrix_world = obj.matrix_world.copy()
        matrix_world_inverted = matrix_world.inverted()

        for vertex_index in sorted(eligible):
            vkey = (mesh_key, vertex_index)
            if vkey in seen_mesh_vertices:
                continue
            seen_mesh_vertices.add(vkey)

            candidates.append({
                "obj": obj,
                "mesh": mesh,
                "vertex_index": vertex_index,
                "world_co": matrix_world @ mesh.vertices[vertex_index].co,
                "matrix_world_inverted": matrix_world_inverted,
            })

    if len(candidates) < 2:
        return 0, 0, 0

    cell_size = distance_bu
    dist_sq = distance_bu * distance_bu
    grid = {}

    def cell_key(co):
        return (
            math.floor(co.x / cell_size),
            math.floor(co.y / cell_size),
            math.floor(co.z / cell_size),
        )

    for idx, cand in enumerate(candidates):
        key = cell_key(cand["world_co"])
        grid.setdefault(key, []).append(idx)

    parents = list(range(len(candidates)))

    def find(x):
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parents[rb] = ra

    neighbor_offsets = tuple(
        (dx, dy, dz)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        for dz in (-1, 0, 1)
    )

    for key, indices in grid.items():
        for dx, dy, dz in neighbor_offsets:
            nk = (key[0] + dx, key[1] + dy, key[2] + dz)
            others = grid.get(nk)
            if not others:
                continue
            for i in indices:
                co = candidates[i]["world_co"]
                for j in others:
                    if j <= i:
                        continue
                    if (co - candidates[j]["world_co"]).length_squared <= dist_sq:
                        union(i, j)

    groups = {}
    for i in range(len(candidates)):
        groups.setdefault(find(i), []).append(i)

    touched_meshes = set()
    snapped_vertices = 0
    snapped_groups = 0

    for group in groups.values():
        if len(group) < 2:
            continue

        center = candidates[group[0]]["world_co"].copy()
        for idx in group[1:]:
            center += candidates[idx]["world_co"]
        center /= len(group)

        for idx in group:
            cand = candidates[idx]
            mesh = cand["mesh"]
            vi = cand["vertex_index"]
            mesh.vertices[vi].co = cand["matrix_world_inverted"] @ center
            touched_meshes.add(mesh)

        snapped_vertices += len(group)
        snapped_groups += 1

    for mesh in touched_meshes:
        mesh.update()

    return len(touched_meshes), snapped_vertices, snapped_groups


# ============================================================
# Property registration (new cm-based attribute)
# ============================================================

def register_properties():
    bpy.types.Scene.close_snap_distance_cm = bpy.props.FloatProperty(
        name="距离 (cm)",
        description="合并相近时顶点之间的最大距离（厘米）",
        default=0.1,
        min=0.0,
        precision=2,
        step=0.1,
    )
    bpy.types.Scene.close_snap_vertex_group = bpy.props.StringProperty(
        name="顶点组",
        description="仅合并该顶点组内的顶点（空则不限制）",
        default="",
    )


def unregister_properties():
    if hasattr(bpy.types.Scene, 'close_snap_distance_cm'):
        del bpy.types.Scene.close_snap_distance_cm
    if hasattr(bpy.types.Scene, 'close_snap_vertex_group'):
        del bpy.types.Scene.close_snap_vertex_group
