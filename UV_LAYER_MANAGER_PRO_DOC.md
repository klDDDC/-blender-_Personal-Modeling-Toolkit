# UV Layer Manager Pro — 功能文档

> 生成时间: 自动生成，用于快速理解项目结构及全部功能
> Blender 版本: 4.1+ | 插件版本: 1.8.0 | 面板位置: View3D > Sidebar > UV

---

## 本地构建与安装

```powershell
python build_release.py --output dist
python install_addon.py --blender-version 4.1
```

`install_addon.py` 会先生成与 `bl_info` 版本一致的 ZIP，在临时目录校验插件根目录后再替换 Blender 用户插件目录中的旧副本；目标目录会在 Blender 插件根目录中重新创建以继承正确权限，替换失败时会恢复原安装。该流程不执行 Git 提交或推送。

---

## 一、文件结构

```
uv_layer_manager_pro/
├── __init__.py      # 插件入口, bl_info, register/unregister, 所有类+属性注册
├── constants.py     # 常量, 全局状态(operation_lock, managed_layouts, etc.), 快捷键定义, ID调色板参数
├── preferences.py   # AddonPreferences: 布局选项与隐藏快捷键 JSON 配置
├── utils.py         # 工具函数: UV剪贴板, 布局管理, 材质ID/顶点颜色节点注入, 法向角度, 合并相近顶点, 快捷键注册
├── ui.py            # UIList×2, 面板×4, Menu×1, section绘图函数×6, 底部菜单注册
├── uv_ops.py        # UV层操作符: add, delete, select, copy, sync, select_max
├── modeling_ops.py  # 建模操作符: UV/法线、斜向拉直、顶点/面选择与建模工具
├── material_ops.py  # 材质操作符: 材质槽、弹窗替换、按材质选面、ID颜色与安全清理
├── shortcuts.py     # 快捷键注册、稳定键标识、JSON持久化与自动保存
└── view_ops.py      # 布局切换操作符: toggle_uv_editor, toggle_shader_editor (带面积分/并+保护机制)
```

---

## 二、插件级别

### 2.1 `bl_info`
| 字段 | 值 |
|---|---|
| name | UV Layer Manager Pro |
| version | (1, 8, 0) |
| blender | (4, 1, 0) |
| location | View3D > Sidebar > UV |
| category | UV |

### 2.2 Preferences (`preferences.py`)
| 属性 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `confirm_open` | Bool | False | 打开UV编辑器前显示确认对话框 |
| `auto_merge` | Bool | True | 关闭UV编辑器时自动合并回3D视图 |
| `protect_uv_area` | Bool | True | 防止UV编辑器区域被切换为其他类型 |
| `view_split_ratio` | Float | 0.6 | 旧版兼容，现固定30% |
| `uv_on_left` | Bool | True | 旧版兼容，现固定编辑器在左侧 |
| `shortcut_overrides` | String (隐藏) | 空 | 版本化 JSON 快捷键绑定；自动保存并在注册时恢复 |

### 2.3 快捷键定义 (`constants.py` — `SHORTCUT_DEFS`)
数组中有 20 个预定义快捷键槽位（不绑定默认按键），覆盖：UV切换、着色器切换、法向预设×5、UV添加/删除/同步、选中最大模型、uv命名重置、合并相近、旋转复制、新增材质、整理材质、材质ID/顶点颜色/顶点alpha。快捷键面板默认只显示已分配按键，勾选“显示未设置”后才展开全部槽位。

---

## 三、常量 (`constants.py`)

### 3.1 硬编码常量
| 名称 | 值 | 说明 |
|---|---|---|
| `MAX_UV_LAYERS` | 99 | UV层上限 |
| `UV_BASE_NAME` | `"UVMap"` | UV层基础命名 |
| `LAYOUT_KIND_UV` | `"UV"` | 布局-UV标识 |
| `LAYOUT_KIND_SHADER` | `"SHADER"` | 布局-着色器标识 |
| `EDITOR_SPLIT_FACTOR` | 0.3 | 编辑器占比30% |
| `NORMAL_ANGLE_PRESET_CUSTOM` | `"CUSTOM"` | 自定义法向标识 |
| `ID_COLOR_COLUMNS` | 9 | ID调色板列 |
| `ID_COLOR_ROWS` | 7 | ID调色板行 |
| `ID_COLOR_PRESET_COUNT` | 63 (9×7) | 预设色块总数 |
| `DEFAULT_MATERIAL_ID_COLOR` | (0.95, 0.27, 0.27, 1.0) | 默认ID颜色 |
| `NORMAL_ANGLE_MODIFIER_NAME` | `"UVLM 法向角度"` | Smooth by Angle 修改器名 |
| `UVLM_NODE_PREFIX` | `"_UVLM_"` | 自定义节点前缀 |

### 3.2 全局状态
- `_operation_lock` / `_last_operation_time` / `_OPERATION_COOLDOWN` (0.3s) — 操作冷却锁
- `_managed_layouts` — 管理中的布局（按screen指针）
- `_vertex_color_original_links` — 顶点颜色节点注入前保存的原始连接
- `_material_id_original_colors` — 材质ID颜色修改前的状态备份
- `_id_color_preview_collection` — 预览图标集合
- `_addon_keymaps` — 注册的快捷键列表
- `_duplicate_material_map_cache` / `_duplicate_material_map_version` — 重复材质缓存
- `_draw_cache` / `_draw_cache_frame` — UI帧缓存

---

## 四、Scene/Material/WindowManager 属性 (`__init__.py` register)

### 4.1 Scene 属性
| 属性 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `uv_layout_active` | Bool | False | UV布局是否激活 |
| `shader_layout_active` | Bool | False | 着色器布局是否激活 |
| `show_unassigned_shortcuts` | Bool | False | 快捷键面板是否显示未分配按键的槽位 |
| `material_manager_material` | Pointer(Material) | None | 材质管理目标材质 |
| `material_view_mode` | Enum | MATERIAL | 当前显示模式: MATERIAL/COLOR/ALPHA/ID/SINGLE_ID |
| `normal_angle_preset` | Enum | 180 | 法向预设: 180/30/90/CUSTOM |
| `normal_angle_custom` | Float(0-180) | 180 | 自定义法向角度 |
| `close_snap_distance` | Float(0+) | 0.001 | 合并相近的距离阈值 |
| `uvlm_select_angle_threshold` | Float(0-180) | 30 | 角度选择的面法向阈值 |
| `uvlm_next_swatch_order` | Int | 0 | 为新增材质分配持久色块序号；删除材质不会回退 |

### 4.2 Material 属性
| 属性 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `uvlm_swatch_order` | Int | -1 | 材质首次出现时分配的持久色块序号，显示颜色按50色循环 |
| `uvlm_id_color` | FloatVector(4) | DEFAULT_MATERIAL_ID_COLOR | 材质ID颜色 |
| `uvlm_id_color_is_custom` | Bool | False | 是否使用自定义ID颜色 |

### 4.3 WindowManager 属性
| 属性 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `uvlm_id_edit_color` | FloatVector(4) | (1, 0.24, 0.24, 1) | 编辑中的ID颜色 |
| `uvlm_id_original_color` | FloatVector(4) | (1, 0.24, 0.24, 1) | 原始ID颜色 |
| `uvlm_id_preset_0..62` | FloatVector(4) | 63种颜色 | ID预设颜色（只读） |
| `uvlm_material_replace_target` | Pointer(Material) | None | 材质替换弹窗的临时目标；执行或取消后立即清空 |

### 4.4 注册/反注册生命周期
#### register()
1. 注册所有类（顺序 `classes` 元组）
2. 快捷键注册
3. ID颜色预览图标初始化
4. 延时0.1s预生成材质图标
5. 注册全部 Scene/Material/WindowManager 属性
6. 同步ID预设颜色
7. 全3D视图重绘

#### unregister()
1. 恢复材质ID颜色
2. 清理顶点颜色节点注入缓存
3. 删除Scene/Material/WindowManager属性（带 `hasattr` 安全检查）
4. 反注册所有类（逆序）

---

## 五、UI 层 (`ui.py`)

### 5.1 UIList
| 类名 | 用途 |
|---|---|
| `UV_LAYER_MANAGER_UL_uv_layers` | 显示UV层列表，每行有 选中指示器(✔) / 名称 / 复制按钮 |
| `UV_LAYER_MANAGER_UL_material_slots` | 材质槽列表，每行有 调色板色块 / ID开关 / ID编辑 / 材质名称 / 赋予按钮 / 移除按钮；**选中面材质槽高亮（`row.alert = True`）** |

### 5.2 Section绘图函数
| 函数 | 位置 | 内容 |
|---|---|---|
| `draw_empty_uv_list` | 空态 | 4行空白占位 |
| **`draw_uv_section`** | UV面板 | → 剪贴板状态 → 列表 → 添加/删除按钮(带上限禁用) → 同步/选中最大 |
| **`draw_modeling_tools_section`** | 建模面板 | → 单行法向角度预设/只读自定义值/自定义按钮 → 两列建模操作 |
| **`draw_material_management_section`** | 材质面板 | → 固定50色循环材质色块/名称列表 → 添加(+) → 整理材质 → 材质ID → 顶点颜色/alpha → 颜色属性列表(≤6个) |
| **`draw_shortcut_section`** | 快捷键面板 | → 每个快捷键槽位: 标签 + 按键映射元(U.draw_shortcut_keymap_item) |
| **`draw_layout_section`** | 布局面板 | → UV/着色器切换按钮(带depress)与当前编辑器状态 |

### 5.3 面板 (Panel)
| 类名 | bl_idname | 排序 | 说明 |
|---|---|---|---|
| `UV_LAYER_MANAGER_PT_panel` | UV_LAYER_MANAGER_PT_panel | 0 | 编辑器布局切换 |
| `UV_LAYER_MANAGER_PT_uv_panel` | UV_LAYER_MANAGER_PT_uv_panel | 1 | UV层管理（独立面板） |
| `UV_LAYER_MANAGER_PT_modeling_panel` | UV_LAYER_MANAGER_PT_modeling_panel | 2 | 建模工具（独立面板） |
| `UV_LAYER_MANAGER_PT_material_panel` | UV_LAYER_MANAGER_PT_material_panel | 3 | 材质管理（独立面板） |
| `UV_LAYER_MANAGER_PT_shortcut_panel` | UV_LAYER_MANAGER_PT_shortcut_panel | 4 | 快捷键（独立面板，默认折叠） |

### 5.4 菜单 (Menu)
| 类名 | 说明 |
|---|---|
| `UV_LAYER_MANAGER_MT_shortcut_menu` | 右键菜单，包含全部功能快捷入口 |

### 5.5 底部菜单注册
`draw_uv_layer_manager_shortcut_menu` 注入到 `VIEW_3D_MT_object_context_menu`，用户右键物体时显示插件菜单。

---

## 六、操作符详解

所有操作符集中在中缀 `uv_layer_manager.` 命名空间下。

### 6.1 UV 层操作 (`uv_ops.py`)

| 操作符 | bl_idname | 快捷键名 | 说明 |
|---|---|---|---|
| `OT_add` | `uv_layer_manager.add` | "UV 添加" | 自动命名添加UV层，上限99层 |
| `OT_delete` | `uv_layer_manager.delete` | "UV 删除" | 删除当前层，最少保留1层 |
| `OT_select` | `uv_layer_manager.select` | — | 选中某个UV层并设为active |
| `OT_copy` | `uv_layer_manager.copy` | — | 复制当前UV数据到剪贴板（`UVClipboard`），保存源层名和循环点计数 |
| `OT_sync` | `uv_layer_manager.sync` | "同步 UV" | 将剪贴板中的UV数据粘贴到目标，**校验拓扑一致性** (loop count) |
| `OT_select_max` | `uv_layer_manager.select_max` | "选中最大模型" | 选中场景中UV层最多的网格对象 |

### 6.2 建模工具 (`modeling_ops.py`)

| 操作符 | bl_idname | 快捷键名 | 说明 |
|---|---|---|---|
| `OT_reset_uv_names` | `uv_layer_manager.reset_uv_names` | "uv命名重置" | 将选中模型的UV层重置为3层并重命名为 `uvmap1`/`2`/`3` |
| `OT_snap_close_vertices` | `uv_layer_manager.snap_close_vertices` | "合并相近" | 世界空间下处理边界/锐边/选中顶点；指定顶点组时严格限制在该对象的正权重组成员内，按距离阈值移动到平均位置 |
| `OT_set_close_snap_distance` | `uv_layer_manager.set_close_snap_distance` | — | 弹出对话框设置合并距离阈值 |
| `OT_rotate_linked_duplicate` | `uv_layer_manager.rotate_linked_duplicate` | "旋转复制" | 以游标为圆心120°旋转复制选中模型并关联UV |
| `OT_select_ngons` | `uv_layer_manager.select_ngons` | "大于4边面" | 选中网格中边数>4的面 |
| `OT_select_by_angle` | `uv_layer_manager.select_by_angle` | "角度选择" | 选中面法向夹角≤阈值的相连面 |
| `OT_set_select_angle` | `uv_layer_manager.set_select_angle` | — | 弹出对话框设置角度选择阈值 |
| `OT_clean_normals` | `uv_layer_manager.clean_normals` | — | 解锁自定义法向 + 添加Smooth by Angle修改器（保留已有锐边） |
| `OT_set_normal_angle` | `uv_layer_manager.set_normal_angle` | "法向XXX/自定义" | 设置法向角度预设→调用clean_normals |

### 6.3 材质管理 (`material_ops.py`)

| 操作符 | bl_idname | 快捷键名 | 说明 |
|---|---|---|---|
| `OT_assign_material` | `uv_layer_manager.assign_material` | — | 将目标材质赋予选中模型的面（面选中时只赋予面，未选面时赋予整模型） |
| `OT_remove_material` | `uv_layer_manager.remove_material` | — | 从选中模型移除指定材质的所有材质槽，受影响面重置到index 0 |
| `OT_add_material` | `uv_layer_manager.add_material` | "新增材质" | 为当前模型新建材质("`{模型名}_Material`")，自动启用节点 |
| `OT_remove_material_slot` | `uv_layer_manager.remove_material_slot` | — | 删除指定索引的材质槽 |
| `OT_select_material_slot` | `uv_layer_manager.select_material_slot` | — | 选中材质槽→同步激活材质索引 |
| `OT_assign_material_slot` | `uv_layer_manager.assign_material_slot` | — | 面模式下选中面赋予指定材质槽；非面模式全物体赋予 |
| `OT_edit_material_base_color` | `uv_layer_manager.edit_material_base_color` | — | 对话框编辑材质Base Color |
| `OT_toggle_material_id_color` | `uv_layer_manager.toggle_material_id_color` | — | 切换单材质ID颜色显示（保存/恢复原始状态） |
| `OT_edit_material_id_color` | `uv_layer_manager.edit_material_id_color` | — | 弹出预设色盘(63色)，可选预设或自定义颜色，自动将颜色施加到材质ID |
| `OT_set_material_id_preset` | `uv_layer_manager.set_material_id_preset` | — | 直接设置材质ID为某个预设颜色索引 |
| `OT_replace_material` | `uv_layer_manager.replace_material` | — | 从材质色块打开弹窗，按精确材质数据块替换当前选中网格中的槽，保留槽顺序和面索引 |
| `OT_select_material_faces` | `uv_layer_manager.select_material_faces` | — | 在当前选中网格中按精确材质数据块选择全部面，支持多物体编辑模式 |
| `OT_clear_material_slots` | `uv_layer_manager.clear_material_slots` | — | 清除选中模型全部材质槽，并清理真正无用户的数字后缀重复材质 |
| `OT_clean_unused_material_slots` | `uv_layer_manager.clean_unused_material_slots` | — | 从选中模型移除所有未使用的材质槽 |
| `OT_merge_duplicate_materials` | `uv_layer_manager.merge_duplicate_materials` | — | 只合并同一模型内指向同一个材质数据块的重复槽，不按名称重定向材质 |
| `OT_organize_materials` | `uv_layer_manager.organize_materials` | — | **一键整理**：清理未用槽 → 合并同数据块槽 → 删除全文件中真正无用户的数字后缀重复材质；保留 Fake User、Asset、链接库和仍被引用的数据 |
| `OT_toggle_vertex_color_view` | `uv_layer_manager.toggle_vertex_color_view` | 材质ID/顶点颜色/alpha | 在3D视图中显示顶点颜色(COLOR)、顶点alpha(ALPHA)、或材质ID(ID)，再次点击恢复 |
| `OT_set_color_attribute` | `uv_layer_manager.set_color_attribute` | — | 切换当前查看的颜色属性（更新active_color_index+重注入节点） |

### 6.4 布局切换 (`view_ops.py`)

| 操作符 | bl_idname | 快捷键名 | 说明 |
|---|---|---|---|
| `OT_toggle_uv_editor` | `uv_layer_manager.toggle_uv_editor` | "UV" | 切换UV编辑器布局（垂直分割，编辑器固定左侧30%） |
| `OT_toggle_shader_editor` | `uv_layer_manager.toggle_shader_editor` | "着色器" | 切换着色器编辑器布局（分割规则同上） |

**`WorkspaceLayoutToggleMixin`** 基类逻辑：
1. `invoke` → 检查 `confirm_open` 偏好
2. `execute` → 操作冷却锁检查
3. `toggle_layout`:
   - 已有管理中的编辑器 → 同类型：关闭；不同类型：切换
   - 有匹配的现有编辑器 → 标记激活，不关闭非插件创建的
   - 有其他类型编辑器 → 切换类型
   - 无 → 调用 `create_layout`（`area_split` 垂直分割）
4. `create_layout` → 分割区域、配置编辑区、保存管理状态
5. `close_layout` → 根据 `auto_merge` 关闭区域或仅清除管理状态

---

## 七、utils.py 工具函数体系

### 7.1 UVClipboard（类）
全局UV数据剪贴板：`copy()` / `has_data()` / `clear()` / `get_uv_data()` / `get_source_name()` / `get_loop_count()`

### 7.2 布局管理工具
| 函数 | 用途 |
|---|---|
| `get_layout_prefs()` | 获取偏好 |
| `get_split_factor(kind)` | 返回分割因子（固定0.3） |
| `get_editor_on_left(kind)` | 是否编辑器在左（固定True） |
| `should_auto_merge()` / `should_protect_managed_area()` | 偏好查询 |
| `get_screen_key(screen)` | 生成screen缓存键 |
| `remember_managed_layout()` | 记录管理的布局area |
| `clear_managed_layout()` | 清除管理记录 |
| `find_area_by_pointer()` | 按指针找area |
| `get_managed_editor_area()` / `get_managed_view_area()` | 获取管理中的area |
| `get_managed_kind()` | 获取管理中的布局类型 |
| `area_matches_kind()` | 判断area是否匹配类型 |
| `get_editor_areas()` | 查找场景中指定类型的编辑器area |
| `tag_screen_redraw()` / `tag_all_view3d_redraw()` | 强制重绘 |
| `sync_scene_layout_flags()` | 同步Scene属性标记 |
| `get_window_region()` | 获取WINDOW region |
| `capture_view_state()` / `restore_view_state()` | 视口状态快照+恢复 |
| `configure_editor_area()` | 设置area类型(IMAGE_EDITOR/NODE_EDITOR)及子参数 |
| `get_layout_areas_after_split()` / `get_fixed_editor_layout_areas_after_split()` | 分割后识别编辑器/视图区域 |

### 7.3 网格和材质工具
| 函数 | 用途 |
|---|---|
| `get_selected_mesh_objects(context)` | 获取选中的网格对象列表 |
| `get_material_base_name(name)` | 提取材质基名（去掉.001等后缀） |
| `ensure_material_slot(obj, material)` | 确保材质槽存在，返回索引 |
| `get_used_material_indices(mesh)` | 获取多边形实际使用的材质索引 |
| `remove_unused_material_slots(obj)` | 清理未用槽 |
| `merge_duplicate_material_slots(obj)` | 合并同一网格中指向同一数据块的重复材质槽 |
| `replace_material_slots(objects, source, target)` | 在选中网格中按精确数据块替换材质槽 |
| `select_material_faces(context, objects, material)` | 跨选中网格按精确数据块选择全部面，共享 Mesh 只处理一次 |
| `assign_material_to_object(obj, material)` | 赋予材质（全部面） |
| `get_selected_polygon_indices(obj)` | 获取选中面的索引 |
| `get_selected_face_material_index(obj)` | 获取选中面的材质索引 |
| `sync_active_material_to_selected_face(context)` | 同步活动材质到当前选面 |
| `get_selected_face_material_index_cached(context, obj)` | 带缓存的版本（UI绘制用） |
| `begin_draw_frame()` | 帧开始，清空绘图缓存 |
| `assign_material_to_selected_faces_or_object()` | 赋予材质：优先面→整物体 |
| `remove_material_from_object()` | 从物体移除某材质所有槽 |
| `remove_material_slot_from_object(obj, index)` | 移除指定索引材质槽 |
| `get_material_manager_target(context)` | 获取材质管理器当前目标材质 |
| `purge_unused_duplicate_materials(context)` | 删除已确认名称族中真正无用户的本地数字后缀材质，保护 Fake User、Asset 与链接库 |
| `get_duplicate_material_map()` | 检测全部场景中的重复材质（基名相同） |
| `invalidate_duplicate_material_cache()` | 使重复材质缓存失效 |
| `set_material_color_view(context)` | 设置所有3D视图为SOLID+MATERIAL模式 |

### 7.4 材质ID颜色工具
| 函数 | 用途 |
|---|---|
| `get_principled_base_color_inputs(material)` | 获取Principled BSDF的Base Color输入 |
| `capture_material_id_state(material)` | 保存材质当前颜色状态（diffuse + Base Color连接+默认值） |
| `restore_material_id_state(material, state)` | 恢复材质颜色 |
| `_srgb_to_linearrgb(rgb)` | 颜色空间转换（Blender 4.0+兼容） |
| `apply_material_id_color(material, color)` | 施加材质ID颜色到diffuse+节点基色 |
| `prepare_material_id_colors(context)` | 为选中模型的所有材质预计算并施加ID颜色 |
| `get_material_id_color(material, index)` | 获取材质ID颜色（优先自定义→黄金比例渐进色） |
| `get_id_color_preset(index)` | 生成63色预设色板（9列×7行） |
| `write_solid_png(path, color, size=24)` | 手动创建纯色PNG（无第三方库依赖） |
| `ensure_id_color_previews()` | 创建/获取预览图标集合 |
| `get_color_preview_icon(color, name)` | 获取颜色预览图标ID（自动缓存） |
| `precache_material_icons()` | 预生成全部材质的颜色预览图标 |
| `clear_id_color_previews()` | 清理预览图标 |
| `sync_id_color_preset_props()` | 同步预设颜色到WindowManager属性 |
| `restore_material_id_colors(context=None)` | 恢复材质ID颜色（接受context只恢复选中物体，None恢复全部） |
| `toggle_single_material_id_color(context, material, index)` | 切换单个材质ID颜色显示 |

### 7.5 顶点颜色节点注入工具
| 函数 | 用途 |
|---|---|
| `_find_shader_node(node_tree)` | 查找连接到Output Surface的着色器节点 |
| `_get_color_socket(shader_node)` | 获取着色器上的颜色输入接口 |
| `_save_original_link(mat, color_socket)` | 保存Base Color原始连接 |
| `_remove_uvlm_nodes_from_tree(node_tree, mat_ptr)` | 删除 `_UVLM_` 前缀节点+恢复原始连接 |
| `_inject_vertex_color_node(mat, mode)` | 注入ShaderNodeVertexColor（COLOR/ALPHA模式） |
| `_apply_vertex_color_nodes(context, mode)` | 对选中物体的所有材质注入节点 |
| `has_uvlm_vertex_color_nodes(obj)` | 检查物体是否有 `_UVLM_` 节点（UI高亮用） |
| `_clear_selected_vertex_color_nodes(context)` | 清理选中物体的 `_UVLM_` 节点（仅选中的） |
| `set_material_view_mode(context, mode)` | **核心**：切换四种显示模式（MATERIAL/COLOR/ALPHA/ID） |
| `update_material_id_color(self, context)` | Material.uvlm_id_color 属性的update回调 |
| `get_active_color_attribute(mesh)` | 获取当前激活的颜色属性 |

### 7.6 法向角度工具
| 函数 | 用途 |
|---|---|
| `get_normal_angle_degrees(scene)` | 获取法向角度值（根据预设或自定义） |
| `_set_modifier_angle(mod, angle_rad, angle_deg)` | 在修改器上设置角度（自动探测属性名和单位） |
| `apply_normal_angle_modifier(obj, angle_degrees)` | **核心**：清理自定义法向 → 全部面smooth → 添加Smooth by Angle修改器（或节点组" Smooth by Angle"） |

### 7.7 合并相近顶点工具
| 函数 | 用途 |
|---|---|
| `get_close_snap_distance(scene)` | 获取合并距离阈值 |
| `get_eligible_close_snap_vertices(obj)` | 获取合格顶点；指定顶点组时按对象级正权重成员严格过滤 |
| `snap_close_vertices_in_objects(objects, distance)` | **核心算法**：世界空间3D格网空间哈希聚类合并（只合并边界/锐边/缝合边顶点，不影响内部网格） |

### 7.8 快捷键工具
| 函数 | 用途 |
|---|---|
| `register_shortcut_keymaps()` | 注册并恢复快捷键（基于 `constants.SHORTCUT_DEFS`，默认不绑定按键） |
| `unregister_shortcut_keymaps()` | 保存最后状态并反注册快捷键 |
| `save_shortcuts_to_prefs()` / `load_shortcuts_from_prefs()` | 写入或恢复版本化 JSON 快捷键配置 |
| `get_shortcut_save_status()` | 返回面板显示的自动保存状态 |
| `draw_shortcut_keymap_item(layout, context, keymap, item)` | UI绘制快捷键按键映射行 |

---

## 八、操作锁与冷却机制

全局操作锁 `_operation_lock`（0.3秒冷却）用于保护：
- 布局切换操作（`view_ops.py` 中的 `WorkspaceLayoutToggleMixin`）
- 防止连续快速操作导致状态不一致

---

## 九、关键设计决策

1. **颜色预览**：手动生成纯色PNG（`write_solid_png`）避免依赖外部图像库
2. **材质ID颜色恢复**：使用快照机制（`capture_material_id_state`）而非简单属性覆盖，保证包括节点连接在内的完整恢复
3. **顶点颜色节点注入**：使用 `_UVLM_` 命名前缀，方便在场景中识别和管理
4. **拓扑一致性校验**：UV同步操作会校验源和目标模型的loop count是否一致
5. **缓存体系**：`_draw_cache`（UI帧缓存）、`_duplicate_material_map_cache`（重复材质检测）、`_id_color_preview_collection`（图标预览）
6. **布局管理器**：跟踪插件创建的编辑器区域，支持打开/关闭/切换三种布局（UV / 着色器），保护非插件创建的现有编辑器
7. **材质的"整理"功能**：`organize_materials` 是组合操作：清理未用材质槽 → 合并同一数据块的重复槽 → 删除确认无用户的数字后缀材质；不按名称强制替换仍在使用的独立材质。

---

## 十、1.8.0 新增行为

- 材质色块现在是操作入口。弹窗中的“替换为”使用 Blender 材质搜索，替换范围是当前选中的全部网格模型，匹配按材质数据块和库路径精确判断，不按 `Wood.001` 这类名称族扩大范围。
- 弹窗可直接调用“选中该材质的所有面”。Object Mode 会进入多物体 Edit Mode，Edit Mode 保持当前模式；共享 Mesh 只处理一次，并保留对象选择集合。
- “清除材质槽”和“整理材质”都会扫描全文件，只删除本地、无用户、无 Fake User/Asset、属于已确认数字后缀族的材质；链接库材质和任何仍被引用的数据均保留。
- 快捷键配置以版本化 JSON 写入 AddonPreferences，使用 Operator ID 与固定参数作为稳定键。编辑后会自动防抖保存，面板同时提供立即保存、重置和当前保存状态。
