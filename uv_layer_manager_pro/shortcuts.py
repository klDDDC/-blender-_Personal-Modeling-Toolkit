# -*- coding: utf-8 -*-
"""
UV Layer Manager - Shortcut Keymap Registration
"""
import bpy
from . import constants as C


def register_shortcut_keymaps():
    wm = bpy.context.window_manager
    if wm is None or wm.keyconfigs.addon is None:
        return

    keymap = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    for label, operator_id, properties in C.SHORTCUT_DEFS:
        item = None
        try:
            item = keymap.keymap_items.new(operator_id, type='NONE', value='PRESS')
            for prop_name, prop_value in properties.items():
                setattr(item.properties, prop_name, prop_value)
        except Exception:
            if item is not None:
                try:
                    keymap.keymap_items.remove(item)
                except Exception:
                    pass
            continue
        C._addon_keymaps.append((keymap, item, label))


def unregister_shortcut_keymaps():
    for keymap, item, _label in reversed(C._addon_keymaps):
        try:
            keymap.keymap_items.remove(item)
        except Exception:
            pass
    C._addon_keymaps.clear()


def draw_shortcut_keymap_item(layout, context, keymap, item):
    try:
        import rna_keymap_ui
        keyconfig = context.window_manager.keyconfigs.addon
        rna_keymap_ui.draw_kmi([], keyconfig, keymap, item, layout, 0)
    except Exception:
        row = layout.row(align=True)
        row.label(text=item.name or item.idname)
        row.prop(item, "type", text="")
        row.prop(item, "value", text="")
