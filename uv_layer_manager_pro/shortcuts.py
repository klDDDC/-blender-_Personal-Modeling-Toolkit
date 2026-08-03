# -*- coding: utf-8 -*-
"""Shortcut keymap registration and persistence."""

import json
import time

import bpy

from . import constants as C
from . import utils as U


_SCHEMA_VERSION = 1
_WATCH_INTERVAL = 0.5
_SAVE_DEBOUNCE = 1.0
_SAVE_RETRY_DELAY = 5.0
_TIMER_NAMESPACE_KEY = "uv_layer_manager_pro.shortcut_persistence_timer"

_last_observed_fingerprint = None
_last_saved_fingerprint = None
_dirty_since = None
_retry_after = 0.0
_pending_serialized = None

_STATE_FIELDS = (
    "type",
    "value",
    "map_type",
    "active",
    "any",
    "shift",
    "ctrl",
    "alt",
    "oskey",
    "key_modifier",
    "direction",
    "repeat",
)


def _default_item_state():
    return {
        "type": "NONE",
        "value": "PRESS",
        "map_type": "KEYBOARD",
        "active": True,
        "any": False,
        "shift": False,
        "ctrl": False,
        "alt": False,
        "oskey": False,
        "key_modifier": "NONE",
        "direction": "ANY",
        "repeat": False,
    }


def _json_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return str(value)


def shortcut_binding_key(operator_id, properties):
    """Return the locale-independent identity of a shortcut definition."""
    fixed_properties = _json_value(dict(properties or {}))
    encoded = json.dumps(
        fixed_properties,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{operator_id}|{encoded}"


def _definition_records():
    return tuple(
        (
            label,
            operator_id,
            properties,
            shortcut_binding_key(operator_id, properties),
        )
        for label, operator_id, properties in C.SHORTCUT_DEFS
    )


def _binding_key_for_label(label):
    for def_label, _operator_id, _properties, binding_key in _definition_records():
        if def_label == label:
            return binding_key
    return None


def _normalize_item_state(saved):
    state = _default_item_state()
    if not isinstance(saved, dict):
        return state

    for name in ("type", "value", "map_type", "key_modifier", "direction"):
        value = saved.get(name)
        if value is not None:
            state[name] = str(value)
    for name in ("active", "any", "shift", "ctrl", "alt", "oskey", "repeat"):
        if name in saved:
            state[name] = bool(saved[name])
    return state


def _parse_overrides(raw):
    """Load current or legacy preferences and return stable-key bindings."""
    if not raw:
        return {}, False
    try:
        decoded = json.loads(raw)
    except (ValueError, TypeError):
        return {}, True
    if not isinstance(decoded, dict):
        return {}, True

    is_envelope = isinstance(decoded.get("bindings"), dict)
    source = decoded.get("bindings", {}) if is_envelope else decoded
    records = _definition_records()
    current_keys = {record[3] for record in records}
    label_to_key = {record[0]: record[3] for record in records}
    bindings = {}
    migrated = not is_envelope or decoded.get("version") != _SCHEMA_VERSION

    for source_key, value in source.items():
        binding_key = source_key if source_key in current_keys else label_to_key.get(source_key)
        if binding_key is None or not isinstance(value, dict):
            migrated = True
            continue
        normalized = _normalize_item_state(value)
        bindings[binding_key] = normalized
        if set(value) != set(_STATE_FIELDS) or value != normalized:
            migrated = True

    if set(bindings) != current_keys:
        migrated = True
    return bindings, migrated


def _load_overrides():
    prefs = U.get_prefs()
    if prefs is None:
        return {}, False
    return _parse_overrides(getattr(prefs, "shortcut_overrides", ""))


def _serialize_bindings(bindings):
    payload = {
        "version": _SCHEMA_VERSION,
        "bindings": {
            key: _normalize_item_state(value)
            for key, value in sorted(bindings.items())
        },
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _set_serialized_overrides(serialized):
    prefs = U.get_prefs()
    if prefs is None:
        return False
    try:
        prefs.shortcut_overrides = serialized
    except Exception:
        return False
    return True


def _flush_userpref():
    try:
        result = bpy.ops.wm.save_userpref()
    except Exception:
        return False
    return result is None or "FINISHED" in result


def _set_item_attribute(item, name, value):
    try:
        setattr(item, name, value)
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def _apply_item(item, saved):
    """Apply a complete saved state without letting one invalid field abort restore."""
    state = _normalize_item_state(saved)

    # map_type supplies a valid event family, then type selects the exact event.
    if not _set_item_attribute(item, "map_type", state["map_type"]):
        _set_item_attribute(item, "map_type", "KEYBOARD")
    if not _set_item_attribute(item, "type", state["type"]):
        _set_item_attribute(item, "type", "NONE")

    for name in ("value", "key_modifier", "direction", "repeat", "active"):
        if not _set_item_attribute(item, name, state[name]):
            _set_item_attribute(item, name, _default_item_state()[name])

    # Setting `any` to true changes Blender's modifier flags to their ANY state.
    _set_item_attribute(item, "any", False)
    for name in ("shift", "ctrl", "alt", "oskey"):
        _set_item_attribute(item, name, state[name])
    if state["any"]:
        _set_item_attribute(item, "any", True)


def _item_to_dict(item):
    defaults = _default_item_state()
    state = {}
    for name in _STATE_FIELDS:
        try:
            value = getattr(item, name)
        except (AttributeError, ReferenceError):
            value = defaults[name]
        if name in ("active", "any", "shift", "ctrl", "alt", "oskey", "repeat"):
            state[name] = bool(value)
        else:
            state[name] = str(value)
    return state


def _current_bindings():
    bindings = {}
    for _keymap, item, label in C._addon_keymaps:
        binding_key = _binding_key_for_label(label)
        if binding_key is not None:
            bindings[binding_key] = _item_to_dict(item)
    return bindings


def _bindings_fingerprint(bindings):
    return json.dumps(bindings, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _current_fingerprint():
    return _bindings_fingerprint(_current_bindings())


def _persisted_fingerprint(bindings):
    complete = {}
    for _label, _operator_id, _properties, binding_key in _definition_records():
        complete[binding_key] = _normalize_item_state(bindings.get(binding_key, {}))
    return _bindings_fingerprint(complete)


def _item_matches_definition(item, operator_id, properties):
    try:
        if item.idname != operator_id:
            return False
        for prop_name, expected in properties.items():
            actual = getattr(item.properties, prop_name)
            if _json_value(actual) != _json_value(expected):
                return False
    except (AttributeError, ReferenceError):
        return False
    return True


def _owned_entries_are_complete():
    records = _definition_records()
    if len(C._addon_keymaps) != len(records):
        return False
    for entry, record in zip(C._addon_keymaps, records):
        keymap, item, label = entry
        def_label, operator_id, properties, _binding_key = record
        if label != def_label or keymap is None:
            return False
        if not _item_matches_definition(item, operator_id, properties):
            return False
    return True


def _remove_owned_items():
    for keymap, item, _label in reversed(C._addon_keymaps):
        try:
            keymap.keymap_items.remove(item)
        except (AttributeError, ReferenceError, RuntimeError):
            pass
    C._addon_keymaps.clear()


def _capture_owned_states():
    states = {}
    for _keymap, item, label in C._addon_keymaps:
        binding_key = _binding_key_for_label(label)
        if binding_key is not None:
            states[binding_key] = _item_to_dict(item)
    return states


def _initialize_persistence_monitor(persisted_bindings, rewrite=False):
    global _last_observed_fingerprint, _last_saved_fingerprint
    global _dirty_since, _retry_after, _pending_serialized

    current_bindings = _current_bindings()
    current_fingerprint = _bindings_fingerprint(current_bindings)
    persisted_fingerprint = _persisted_fingerprint(persisted_bindings)
    _last_observed_fingerprint = current_fingerprint
    _last_saved_fingerprint = persisted_fingerprint
    _retry_after = 0.0
    _pending_serialized = None

    if rewrite or current_fingerprint != persisted_fingerprint:
        _pending_serialized = _serialize_bindings(current_bindings)
        _set_serialized_overrides(_pending_serialized)
        _dirty_since = time.monotonic()
    else:
        _dirty_since = None


def _mark_current_state_saved():
    global _last_observed_fingerprint, _last_saved_fingerprint
    global _dirty_since, _retry_after, _pending_serialized

    fingerprint = _current_fingerprint()
    _last_observed_fingerprint = fingerprint
    _last_saved_fingerprint = fingerprint
    _dirty_since = None
    _retry_after = 0.0
    _pending_serialized = None


def _stage_current_state_for_save():
    global _last_observed_fingerprint, _dirty_since, _retry_after, _pending_serialized

    bindings = _current_bindings()
    _last_observed_fingerprint = _bindings_fingerprint(bindings)
    _pending_serialized = _serialize_bindings(bindings)
    _dirty_since = time.monotonic()
    _retry_after = 0.0
    return _set_serialized_overrides(_pending_serialized), len(bindings)


def _attempt_pending_save():
    global _last_saved_fingerprint, _dirty_since, _retry_after, _pending_serialized

    serialized = _pending_serialized
    if serialized is None:
        serialized = _serialize_bindings(_current_bindings())
    if not _set_serialized_overrides(serialized) or not _flush_userpref():
        _retry_after = time.monotonic() + _SAVE_RETRY_DELAY
        return False

    _last_saved_fingerprint = _current_fingerprint()
    _dirty_since = None
    _retry_after = 0.0
    _pending_serialized = None
    return True


def _shortcut_persistence_timer():
    global _last_observed_fingerprint, _dirty_since, _retry_after, _pending_serialized

    try:
        if not C._addon_keymaps:
            return _WATCH_INTERVAL

        now = time.monotonic()
        fingerprint = _current_fingerprint()
        if _last_observed_fingerprint is None:
            _last_observed_fingerprint = fingerprint
        elif fingerprint != _last_observed_fingerprint:
            _last_observed_fingerprint = fingerprint
            _pending_serialized = None
            _dirty_since = now
            _retry_after = 0.0

        if fingerprint == _last_saved_fingerprint and _pending_serialized is None:
            _dirty_since = None
        elif _dirty_since is None:
            _dirty_since = now

        if (
            _dirty_since is not None
            and now - _dirty_since >= _SAVE_DEBOUNCE
            and now >= _retry_after
        ):
            _attempt_pending_save()
    except Exception:
        # A timer must never destabilize Blender's event loop.
        _retry_after = time.monotonic() + _SAVE_RETRY_DELAY
    return _WATCH_INTERVAL


def _register_persistence_timer():
    timers = bpy.app.timers
    namespace = bpy.app.driver_namespace
    previous = namespace.get(_TIMER_NAMESPACE_KEY)
    if previous is not None and previous is not _shortcut_persistence_timer:
        try:
            if timers.is_registered(previous):
                timers.unregister(previous)
        except (AttributeError, RuntimeError, ValueError):
            pass
    namespace[_TIMER_NAMESPACE_KEY] = _shortcut_persistence_timer
    try:
        if not timers.is_registered(_shortcut_persistence_timer):
            timers.register(
                _shortcut_persistence_timer,
                first_interval=_WATCH_INTERVAL,
                persistent=True,
            )
    except (AttributeError, RuntimeError, ValueError):
        pass


def _unregister_persistence_timer():
    timers = bpy.app.timers
    namespace = bpy.app.driver_namespace
    callback = namespace.get(_TIMER_NAMESPACE_KEY)
    if callback is not None:
        try:
            if timers.is_registered(callback):
                timers.unregister(callback)
        except (AttributeError, RuntimeError, ValueError):
            pass
    if namespace.get(_TIMER_NAMESPACE_KEY) is callback:
        namespace.pop(_TIMER_NAMESPACE_KEY, None)


def register_shortcut_keymaps():
    wm = bpy.context.window_manager
    if wm is None or wm.keyconfigs.addon is None:
        return

    persisted_bindings, rewrite = _load_overrides()
    if _owned_entries_are_complete():
        _initialize_persistence_monitor(persisted_bindings, rewrite=rewrite)
        _register_persistence_timer()
        return

    live_states = _capture_owned_states()
    _remove_owned_items()

    keymaps = wm.keyconfigs.addon.keymaps
    keymap = keymaps.get("3D View")
    if keymap is None:
        keymap = keymaps.new(name="3D View", space_type="VIEW_3D")
    adopted_pointers = set()

    for label, operator_id, properties, binding_key in _definition_records():
        item = None
        created_item = False
        try:
            for candidate in keymap.keymap_items:
                pointer = candidate.as_pointer()
                if pointer in adopted_pointers:
                    continue
                if _item_matches_definition(candidate, operator_id, properties):
                    item = candidate
                    adopted_pointers.add(pointer)
                    break

            if item is None:
                item = keymap.keymap_items.new(operator_id, type="NONE", value="PRESS")
                created_item = True
                adopted_pointers.add(item.as_pointer())
                for prop_name, prop_value in properties.items():
                    setattr(item.properties, prop_name, prop_value)

            saved = live_states.get(binding_key, persisted_bindings.get(binding_key, {}))
            _apply_item(item, saved)
        except Exception:
            if item is not None and created_item:
                try:
                    keymap.keymap_items.remove(item)
                except Exception:
                    pass
            continue
        C._addon_keymaps.append((keymap, item, label))

    _initialize_persistence_monitor(persisted_bindings, rewrite=rewrite)
    _register_persistence_timer()


def unregister_shortcut_keymaps():
    _unregister_persistence_timer()
    if C._addon_keymaps:
        written, _count = _stage_current_state_for_save()
        if written and _flush_userpref():
            _mark_current_state_saved()
    _remove_owned_items()


def save_shortcuts_to_prefs():
    """Copy current keymap items into the versioned AddonPreferences payload."""
    written, count = _stage_current_state_for_save()
    return count if written else 0


def load_shortcuts_from_prefs():
    """Apply saved bindings to the currently registered keymap items."""
    bindings, rewrite = _load_overrides()
    applied = 0
    for _keymap, item, label in C._addon_keymaps:
        binding_key = _binding_key_for_label(label)
        saved = bindings.get(binding_key, {}) if binding_key is not None else {}
        _apply_item(item, saved)
        if str(getattr(item, "type", "NONE")) != "NONE":
            applied += 1
    _initialize_persistence_monitor(bindings, rewrite=rewrite)
    return applied


def get_shortcut_save_status():
    """Return the user-facing persistence state for the shortcut panel."""
    if not C._addon_keymaps:
        return "快捷键未注册", 'ERROR'

    try:
        current_fingerprint = _current_fingerprint()
    except Exception:
        return "无法读取快捷键状态", 'ERROR'

    if current_fingerprint == _last_saved_fingerprint and _pending_serialized is None:
        return "快捷键已自动保存", 'CHECKMARK'
    if _retry_after > time.monotonic():
        return "保存失败，正在自动重试", 'ERROR'
    return "快捷键修改等待自动保存", 'TIME'


class UV_LAYER_MANAGER_OT_save_shortcuts(bpy.types.Operator):
    bl_idname = "uv_layer_manager.save_shortcuts"
    bl_label = "保存快捷键"
    bl_description = "立即保存当前快捷键；后续修改也会自动保存"
    bl_options = {"REGISTER"}

    def execute(self, context):
        count = save_shortcuts_to_prefs()
        if count == 0 or not _flush_userpref():
            self.report({"WARNING"}, "快捷键已写入本次会话，但保存到磁盘失败，将自动重试")
        else:
            _mark_current_state_saved()
            self.report({"INFO"}, f"已保存 {count} 个快捷键并写入磁盘")
        return {"FINISHED"}


class UV_LAYER_MANAGER_OT_reset_shortcuts(bpy.types.Operator):
    bl_idname = "uv_layer_manager.reset_shortcuts"
    bl_label = "重置快捷键"
    bl_description = "清除已保存的快捷键设置并恢复为未分配状态"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global _last_observed_fingerprint, _dirty_since, _retry_after, _pending_serialized

        for _keymap, item, _label in C._addon_keymaps:
            _apply_item(item, _default_item_state())

        fingerprint = _current_fingerprint()
        _last_observed_fingerprint = fingerprint
        _pending_serialized = ""
        _dirty_since = time.monotonic()
        _retry_after = 0.0
        written = _set_serialized_overrides("")
        if not written or not _flush_userpref():
            self.report({"WARNING"}, "快捷键已重置，但保存到磁盘失败，将自动重试")
        else:
            _mark_current_state_saved()
            self.report({"INFO"}, "已重置快捷键")
        return {"FINISHED"}


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
