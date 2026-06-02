# -*- coding: utf-8 -*-
"""
UV Layer Manager - UV Clipboard
"""
import bpy


class UVClipboard:
    _uv_data = None
    _source_name = ""
    _source_mesh = ""
    _loop_count = 0

    @classmethod
    def copy(cls, source_name, source_mesh, loop_count, uv_flat):
        cls._uv_data = list(uv_flat)
        cls._source_name = source_name
        cls._source_mesh = source_mesh
        cls._loop_count = loop_count

    @classmethod
    def has_data(cls):
        return cls._uv_data is not None and cls._loop_count > 0

    @classmethod
    def clear(cls):
        cls._uv_data = None
        cls._source_name = ""
        cls._source_mesh = ""
        cls._loop_count = 0

    @classmethod
    def get_uv_data(cls):
        return cls._uv_data

    @classmethod
    def get_source_name(cls):
        return cls._source_name

    @classmethod
    def get_source_mesh(cls):
        return cls._source_mesh

    @classmethod
    def get_loop_count(cls):
        return cls._loop_count
