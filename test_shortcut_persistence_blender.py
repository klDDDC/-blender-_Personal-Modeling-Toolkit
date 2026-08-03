# -*- coding: utf-8 -*-
"""One stage of the isolated two-process shortcut persistence test."""

import importlib
import json
import os
from pathlib import Path
import time

import bpy


ADDON_MODULE = "uv_layer_manager_pro"
STAGE = os.environ.get("UVLM_SHORTCUT_STAGE", "")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def enable_addon():
    result = bpy.ops.preferences.addon_enable(module=ADDON_MODULE)
    require(result == {"FINISHED"}, f"addon_enable returned {result}")
    addon = importlib.import_module(ADDON_MODULE)
    shortcuts = importlib.import_module(f"{ADDON_MODULE}.shortcuts")
    constants = importlib.import_module(f"{ADDON_MODULE}.constants")
    prefs = bpy.context.preferences.addons[ADDON_MODULE].preferences
    require(tuple(addon.bl_info["version"]) == (1, 8, 0), "unexpected add-on version")
    require(len(constants._addon_keymaps) == len(constants.SHORTCUT_DEFS), "shortcut registration is incomplete")
    return shortcuts, constants, prefs


def binding_state(item):
    return {
        "type": str(item.type),
        "value": str(item.value),
        "map_type": str(item.map_type),
        "active": bool(item.active),
        "any": bool(item.any),
        "shift": bool(item.shift),
        "ctrl": bool(item.ctrl),
        "alt": bool(item.alt),
        "oskey": bool(item.oskey),
        "key_modifier": str(item.key_modifier),
        "direction": str(item.direction),
        "repeat": bool(item.repeat),
    }


EXPECTED_KEYBOARD = {
    "type": "B",
    "value": "PRESS",
    "map_type": "KEYBOARD",
    "active": False,
    "any": False,
    "shift": True,
    "ctrl": True,
    "alt": False,
    "oskey": False,
    "key_modifier": "SPACE",
    "direction": "ANY",
    "repeat": True,
}

EXPECTED_MOUSE = {
    "type": "MIDDLEMOUSE",
    "value": "PRESS",
    "map_type": "MOUSE",
    "active": True,
    "any": False,
    "shift": False,
    "ctrl": False,
    "alt": True,
    "oskey": False,
    "key_modifier": "NONE",
    "direction": "ANY",
    "repeat": False,
}


def write_stage():
    shortcuts, constants, prefs = enable_addon()
    require(all(str(item.type) == "NONE" for _km, item, _label in constants._addon_keymaps), "fresh install is not unbound")

    keyboard = constants._addon_keymaps[0][1]
    keyboard.map_type = "KEYBOARD"
    keyboard.type = "B"
    keyboard.value = "PRESS"
    keyboard.active = False
    keyboard.any = False
    keyboard.shift = True
    keyboard.ctrl = True
    keyboard.alt = False
    keyboard.oskey = False
    keyboard.key_modifier = "SPACE"
    keyboard.direction = "ANY"
    keyboard.repeat = True

    mouse = constants._addon_keymaps[1][1]
    mouse.map_type = "MOUSE"
    mouse.type = "MIDDLEMOUSE"
    mouse.value = "PRESS"
    mouse.active = True
    mouse.any = False
    mouse.shift = False
    mouse.ctrl = False
    mouse.alt = True
    mouse.oskey = False
    mouse.key_modifier = "NONE"
    mouse.direction = "ANY"
    mouse.repeat = False

    shortcuts._shortcut_persistence_timer()
    time.sleep(1.1)
    shortcuts._shortcut_persistence_timer()

    payload = json.loads(prefs.shortcut_overrides)
    require(payload.get("version") == 1, "versioned shortcut JSON was not written")
    require(len(payload.get("bindings", {})) == len(constants.SHORTCUT_DEFS), "not all bindings were serialized")
    require(binding_state(keyboard) == EXPECTED_KEYBOARD, "keyboard test state was not applied")
    require(binding_state(mouse) == EXPECTED_MOUSE, "mouse test state was not applied")
    status_text, _status_icon = shortcuts.get_shortcut_save_status()
    require("已自动保存" in status_text, f"unexpected save status: {status_text}")
    pref_path = Path(bpy.utils.user_resource("CONFIG")) / "userpref.blend"
    require(pref_path.is_file(), f"user preferences were not written: {pref_path}")
    print("UVLM_SHORTCUT_TEST WRITE PASS")


def read_stage():
    shortcuts, constants, prefs = enable_addon()
    keyboard = constants._addon_keymaps[0][1]
    mouse = constants._addon_keymaps[1][1]
    require(binding_state(keyboard) == EXPECTED_KEYBOARD, f"keyboard binding was not restored: {binding_state(keyboard)}")
    require(binding_state(mouse) == EXPECTED_MOUSE, f"mouse binding was not restored: {binding_state(mouse)}")

    pointers_before = [item.as_pointer() for _km, item, _label in constants._addon_keymaps]
    shortcuts.register_shortcut_keymaps()
    pointers_after = [item.as_pointer() for _km, item, _label in constants._addon_keymaps]
    require(pointers_after == pointers_before, "repeat registration created duplicate keymap items")

    legacy_label = constants.SHORTCUT_DEFS[0][0]
    prefs.shortcut_overrides = json.dumps({legacy_label: {"type": "Q", "value": "PRESS"}})
    shortcuts.load_shortcuts_from_prefs()
    require(str(keyboard.type) == "Q", "legacy label-keyed shortcut was not restored")
    migrated = json.loads(prefs.shortcut_overrides)
    require(migrated.get("version") == 1 and isinstance(migrated.get("bindings"), dict), "legacy shortcut JSON was not migrated")

    result = bpy.ops.uv_layer_manager.reset_shortcuts()
    require(result == {"FINISHED"}, f"reset_shortcuts returned {result}")
    require(all(str(item.type) == "NONE" for _km, item, _label in constants._addon_keymaps), "reset did not clear all shortcuts")
    require(prefs.shortcut_overrides == "", "reset did not clear persisted shortcut JSON")
    print("UVLM_SHORTCUT_TEST READ PASS")


if STAGE == "write":
    write_stage()
elif STAGE == "read":
    read_stage()
else:
    raise SystemExit("UVLM_SHORTCUT_STAGE must be 'write' or 'read'")
