# UV Layer Manager Pro 插件评估报告

- 评估日期：2026-07-24
- 代码基线：`main` / `b3afdd7` / Git 标签 `v1.2`
- 插件声明版本：`1.6.0`
- 验证环境：Blender 4.1.1、Python 静态编译、仓库内置测试、隔离运行时探针
- 规模：17 个插件模块，约 4,263 行 Python

## 基线结论（修复前）

当前版本的基础功能与主要 happy path 能够运行，但存在会改变或丢失用户材质数据的高风险缺陷，以及若干已发布功能无法正常工作的缺陷。综合判断：**暂不建议发布新的重大版本，也不建议把“整理材质”用于重要工程文件**。

| 维度 | 评分 | 结论 |
|---|---:|---|
| 基础功能 | 6/10 | 核心 smoke test 通过，但多项边界和状态转换失败 |
| 数据安全 | 3/10 | 存在全局误合并材质、节点连接及临时颜色无法恢复 |
| Blender 4.1 兼容性 | 5/10 | 主流程可加载，Edit Mode UV 与顶点组 API 使用错误 |
| 测试质量 | 5/10 | 有 Blender 运行测试，但断言偏浅、UI 测试已漂移 |
| 发布准备度 | 3/10 | 版本号不一致，无 CI、CHANGELOG 和标准打包流程 |
| 综合 | **4/10** | 需要先完成数据安全与回归测试修复 |

上表是针对 `main` / `b3afdd7` / `v1.2` 基线的审查结论，后文记录本轮修复及复测结果。它不代表当前工作区的最终状态。

## 主要发现

### P0：按名称后缀全局合并材质会破坏独立材质

位置：`uv_layer_manager_pro/material_ops.py:420-504`

“整理材质”只通过移除 `.001/.002` 后缀判断重复材质，没有比较节点树、参数、贴图或自定义属性。随后代码遍历整个 Blender 文件中的所有对象和 Mesh，将这些材质替换为基础名称材质，并以 `do_unlink=True` 删除原材质。

Blender 会为普通的独立副本自动添加数字后缀，因此 `Wood.001` 完全可能是用户刻意编辑的另一种材质。隔离测试中，蓝色 `Intentional.001` 被替换为红色 `Intentional` 并删除，Operator 仍返回 `FINISHED`。

影响：跨场景、跨对象的外观变化和材质数据丢失。应在修复前禁用该按钮，或至少增加明确确认和备份提示。

修复方向：仅处理选中对象；比较完整材质签名；默认只合并相同数据块的重复槽；不自动关闭 fake user 或强制 unlink。

### P1：顶点颜色模式无法恢复原始 Base Color 节点连接

位置：`uv_layer_manager_pro/vertex_color_nodes.py:59-99`、`158-182`

代码保存原始连接后立即调用 `_remove_uvlm_nodes_from_tree()`，而该函数会删除刚保存的 `VertexColorState`。退出模式时也先删除状态、再检查状态，导致恢复分支不可达。

隔离测试确认：原 RGB 节点到 Principled Base Color 的连接在进入并退出 COLOR 模式后消失。

影响：材质节点树被永久改变，保存 `.blend` 后会保留损坏状态。

修复方向：节点清理与状态删除分离；只在成功恢复后释放状态；用节点名和 socket identifier 重新解析连接，不长期保存易失效的 socket 引用。

### P1：关闭材质 ID 模式不会恢复原始颜色

位置：`uv_layer_manager_pro/vertex_color_nodes.py:185-212`

进入 ID 模式会保存并覆盖材质 diffuse/Base Color；再次点击切回 MATERIAL 时只清理节点并切换视口着色，没有调用 `restore_material_id_colors()`。

隔离测试确认：原始 diffuse `(0.12, 0.34, 0.56, 1)` 与 Base Color `(0.21, 0.43, 0.65, 1)` 均继续保持红色 ID 色。

影响：临时查看功能修改真实材质数据，用户可能无意保存这些临时颜色。

修复方向：所有离开 ID 模式的路径必须在 `finally` 中恢复颜色；把显示模式改为显式状态机并覆盖 ID/COLOR/ALPHA/MATERIAL 的全部转换。

### P1：Edit Mode 的打平与固定功能使用错误的数据接口

位置：`uv_layer_manager_pro/flatten_ops.py:20-217`

四个 Operator 强制要求 Edit Mode，却直接读取和写入 `Mesh.uv_layers.active.data`。Edit Mode 的权威数据在 edit BMesh 中，应通过 `bmesh.from_edit_mesh()` 和 UV loop layer 操作。

Blender 4.1.1 隔离测试中，存在 24 个已选 UV loop 时 `flatten_u` 仍返回 `CANCELLED` 和“没有 UV 数据”，UV 值完全未变化。Pin/Unpin 使用同一数据路径，风险相同。

修复方向：改为 BMesh UV layer；使用 `bmesh.update_edit_mesh()`；补充 U/V、Pin/Unpin、同步/非同步 UV 选择模式测试。

### P2：颜色属性切换始终读取硬编码的 `Col`

位置：`uv_layer_manager_pro/vertex_color_nodes.py:104-131`、`material_ops.py:587-597`

UI 会改变活动颜色属性，但注入的 `ShaderNodeVertexColor.layer_name` 在所有模式中都固定为 `Col`。隔离测试选择 `CustomAttr` 后，节点仍读取 `Col`。

影响：非 `Col` 属性会显示错误或空白结果，而 Operator 报告成功。

修复方向：把所选属性名传入注入函数；测试节点 `layer_name` 与渲染输出，而不只是检查节点存在。

### P2：顶点组过滤访问了不存在的 `Mesh.vertex_groups`

位置：`uv_layer_manager_pro/merge_vertices.py:22-49`、`81-109`

顶点组属于 `Object`，代码却在 Mesh 上调用 `vertex_groups.get()`。Blender 4.1.1 实测只要设置顶点组过滤就抛出 `AttributeError`。

修复方向：将 Object 传入筛选函数，并按对象解析 group index；共享 Mesh 的多个对象需要分别处理对象级顶点组。

### P2：多场景“选中最大模型”可能直接报错

位置：`uv_layer_manager_pro/utils.py:40-50`、`uv_ops.py:240-250`

`get_scene_max_uv_info(scene)` 忽略传入的 scene，扫描 `bpy.data.objects` 全局对象。若最大对象属于其他场景，当前 View Layer 无法选中它。

隔离测试确认：Operator 选择其他场景对象并抛出 `Object ... can't be selected because it is not in View Layer`。

修复方向：只遍历 `context.view_layer.objects` 或 `scene.objects`，并在设置 active 前验证成员关系。

### P2：预览缓存清理同时清除了材质恢复状态

位置：`uv_layer_manager_pro/material_id.py:61-69`、`265-305`

预览图失效时调用 `clear_id_color_previews()`，最终执行 `MaterialIdState.clear_all()`。该方法不仅删除预览，还清空 `_original_colors`。

隔离测试确认，调用预览清理后 `has_original(mat)` 从 `True` 变为 `False`。

影响：预览资源错误可能让 ID 模式再也无法恢复原材质。

修复方向：拆分 `clear_preview_resources()` 与 `clear_material_overrides()`；前者不得改变材质恢复状态。

### P2：打开确认偏好未生效

位置：`uv_layer_manager_pro/layout.py:284-296`、`view_ops.py:24-28`、`54-58`

`LayoutManager.invoke()` 正确检查 `confirm_open`，但两个 Operator 没有使用它，而是直接调用不检查偏好的 `should_confirm_open()`。

影响：即使默认配置为不确认，首次打开布局仍可能出现确认对话框。

### P2：注册过程只有类注册阶段具备回滚

位置：`uv_layer_manager_pro/__init__.py:141-200`

类注册后，快捷键、预览、timer 和五组 RNA 属性依次注册；任何一步失败都没有统一回滚。可能留下部分注册状态，导致重新启用失败或必须重启 Blender。

修复方向：把注册步骤记录为栈，在异常时逆序清理；`unregister()` 取消未执行 timer，并对每个阶段保持幂等。

## 次要问题

- COLOR 与 ALPHA 之间切换时，只要检测到 UVLM 节点就直接关闭显示，而不是切换到目标模式：`material_ops.py:550-571`。
- 预览视图实际被更新时，状态消息仍固定显示“更新 0 个 3D 视图”：`vertex_color_nodes.py:185-212`。
- 删除无效材质槽索引仍报告成功；单材质 ID 开关允许负索引：`material_ops.py:125-134`、`220-232`。
- 合并相近在多对象 Edit Mode 下只记录活动对象的顶点选择：`modeling_ops.py:210-237`。
- 预生成图标 timer 没有在卸载时显式取消：`__init__.py:157`、`205-240`。
- 源码版本 `1.6.0` 与 Git 标签/GitHub Release `v1.2` 不一致：`uv_layer_manager_pro/__init__.py:6`。

## 测试结果

| 检查 | 结果 |
|---|---|
| Python 全模块编译 | 通过 |
| 核心 Blender smoke test | 11/11 通过 |
| 63 个材质 ID 预设 | 全部通过 |
| 无效预设索引 | `-1`、`63`、`73` 均正确 `CANCELLED` |
| UI/交互测试 | 3/5 通过 |
| 隔离缺陷探针 | 6 项候选问题全部复现 |
| Git diff 检查 | 通过，插件源码未修改 |

UI 测试失败包含测试本身的问题：仍写入旧属性 `close_snap_distance`，且后台模式下期待弹出 modal 对话框。布局测试还在两次着色器切换失败时判定通过。因此当前测试不能作为发布门禁。

## 测试缺口

- 没有验证临时显示模式退出后材质数据完全恢复。
- 没有验证已有 Base Color 节点连接的保存与恢复。
- 没有验证实际颜色属性名和节点输出。
- 没有测试独立的 `.001` 材质、跨场景对象或共享 Mesh。
- 没有测试顶点组过滤与多对象 Edit Mode。
- 没有测试 flatten/pin/unpin 四个新增 Operator。
- 没有 GitHub Actions、Blender 版本矩阵或可重复打包检查。

## 修复与发布顺序

1. 立即禁用或限制“整理材质”，修复名称后缀误合并。
2. 修复 Vertex Color 与 Material ID 的状态保存、切换和恢复，并补数据不变性测试。
3. 用 Edit BMesh 重写 Flatten/Pin/Unpin。
4. 修复 Object/Scene/View Layer 范围错误及顶点组 API。
5. 拆分预览资源状态与材质覆盖状态，完善注册/卸载事务。
6. 修复并强化 UI 测试，建立 Blender 4.1 与当前 LTS 的 CI 运行矩阵。
7. 统一版本号、标签、CHANGELOG 和 ZIP 文件名后，再准备下一个正式版本。

在 P0/P1 项全部修复、针对性回归测试通过之前，发布结论为：**不通过**。

## 补充评估：材质栏、法向切线与菜单 UI

### 1. 多物体材质显示不合并

根因在 `uv_layer_manager_pro/ui.py:377-389`：多选列表使用 `mat.as_pointer()` 分组。只有多个物体共享同一个材质数据块时才会合并；`Wood`、`Wood.001`、`Wood.002` 这种独立数据块即使用户认为它们是同一材质系列，也会各自显示。

解决方案应分成两层：

1. **只改显示，不改数据。** 使用 `U.get_material_base_name()` 生成显示分组键，并同时带上 library 路径，避免不同库中的同名材质误聚合。组标题显示“Wood · 3 个材质 · 5 个物体 · 9 个槽”，展开后仍列出真实的 `Wood`、`Wood.001`、`Wood.002`。
2. **真实合并另设明确命令。** 只有用户主动确认、且比较节点树、贴图、颜色、粗糙度、金属度、fake user 和自定义属性完全一致时，才允许替换材质槽。显示分组不能隐式调用当前的 `organize_materials()`，否则会把 UI 聚合变成破坏性操作。

建议的数据结构：

```text
DisplayGroup
  key: (normalized_name, library_path)
  members: [MaterialMember]
  object_count / slot_count
```

组内操作应针对具体成员；“移除”不能对整个名称组执行。另加搜索框和“只显示活动/重复组”过滤，避免多物体场景出现几十行材质。

### 2. 材质名称被图标挤压

单物体 UI 在 `uv_layer_manager_pro/ui.py:50-114` 中把预览色、ID 开关、ID 设置、材质图标、名称、赋予和删除全部放在一行。名称是唯一的弹性控件，所以侧栏变窄时必然先被裁切。多物体行 `ui.py:391-406` 还把名称和“对象/槽数量”放在同一行。

建议改成以下布局：

- 第一行只放颜色色板、材质名称和简短数量；名称使用 `prop(material, "name")`，占据主要宽度。
- 第二行放赋予、ID 预览、编辑、删除等次要图标；或统一收进一个 overflow 菜单。
- 删除重复的“颜色预览 + 材质图标”其中一个，避免占用两个固定宽度。
- 多物体组标题使用两行：第一行名称，第二行“3 个材质 / 5 个物体 / 9 个槽”。
- 给图标按钮补充稳定 tooltip，不能依赖用户猜测 `BACK`、`CHECKBOX`、`PREFERENCES` 的含义。

不要用更小字体解决裁切；应减少同一行的固定控件，并让名称成为主控件。

### 3. “解锁法线”没有清除法向和切线数据

当前实现位于 `uv_layer_manager_pro/normal_angle.py:142-147`，只调用 `normals_split_custom_set()` 写入零向量。Blender 4.1.1 实测：

| 状态 | `has_custom_normals` | tangent |
|---|---:|---|
| 清理前 | `True` | 非零 |
| 当前插件清理后 | `True` | 原值仍在 |
| 官方 API 清理后 | `False` | `(0, 0, 0)` |

建议把“解锁”拆成两个语义清晰的动作：

- **清除自定义法向/切线**：在 Object Mode 下，对每个唯一 Mesh 调用 `bpy.ops.mesh.customdata_custom_splitnormals_clear()`，随后调用实例方法 `mesh.free_tangents()`，再 `mesh.update()`。
- **应用平滑角度**：只负责设置 `poly.use_smooth` 和 Smooth by Angle 修改器，不再暗含清除数据。

执行时保存并恢复活动对象、选择集和原始模式；完成后验证 `has_custom_normals`，报告“清除多少个 Mesh、释放多少个 tangent 缓存”。如果对象上还有 Weighted Normal、Data Transfer 等修改器，应单独列出“修改器生成的法向”并提供显式、二次确认的移除选项，不能默默删除。

### 4. 菜单和侧栏 UI 评判

#### 当前问题

- `UV_LAYER_MANAGER_MT_shortcut_menu` 虽在 `__init__.py:81`、`130-137` 注册，但没有任何 `VIEW3D_MT_*.append(...)`；`ui.py:746-747` 的绘制函数也未被使用。因此所谓右键快捷菜单没有真实入口。
- 侧栏已经绘制布局、快捷键、UV、建模和材质内容，`ui.py:597-693` 又把它们拆成多个独立 Panel，每个 Panel 内部再套 `box()`，层级和边框过多，挤占有效空间。
- 右键菜单 `ui.py:700-743` 与侧栏重复列出相同命令，维护成本高；没有按 Object/Edit Mode 分流。
- `constants.py:45-64` 的 20 个快捷键默认类型均为 `NONE`，侧栏会显示一长串空槽位。用户没有配置时，这部分信息密度低、噪声高。
- 由于 Blender 窗口捕获接口在当前环境不可用，本轮未把空白截图当作视觉证据；上述 UI 判断来自代码结构和用户实际反馈。

#### 建议的 UI 结构

1. 使用一个主面板加原生子面板：布局、UV、材质、建模、快捷键分别作为可折叠子面板，去掉内部 `box()` 套 `box()`。
2. 主面板只保留最高频动作和当前状态；低频设置（法向角度、布局偏好、快捷键编辑）放到 Preferences 或 popover。
3. 注册真实菜单入口：Object Mode 挂到 `VIEW3D_MT_object_context_menu`，Edit Mesh 挂到 `VIEW3D_MT_edit_mesh_context_menu`，并在 `unregister()` 对称 remove。菜单内再分“UV / 建模 / 材质 / 法向”子菜单，只显示当前模式可用的命令。
4. 把“整理材质”从高频按钮降级为明确的高级操作，按钮旁显示风险提示或先打开预览对话框。
5. 快捷键区域只显示已分配项目和冲突警告，提供一个“打开快捷键设置”入口，而不是渲染 20 个空槽位。
6. 用统一的图标+tooltip 规范：赋予、预览、编辑、删除和危险操作使用不同的语义图标；危险操作必须有确认或撤销提示。

### 5. 建议的验收标准

- 多选 10 个物体、3 个独立同名材质时，列表显示一个可展开组，展开后数据块仍保持独立。
- 侧栏宽度缩到 Blender 默认窄宽时，材质名称仍完整显示，图标不覆盖文字。
- 清理法向后 `mesh.has_custom_normals is False`，已计算 tangent 被释放；锐边标记按用户选择保留。
- Object Mode 右键能看到 UV Layer Manager 菜单，Edit Mesh 右键只看到 Edit Mode 合法操作；禁用插件后菜单入口消失。
- 颜色模式、ID 模式、法向清理和材质分组均有 Blender 4.1.1 回归测试，并在当前 LTS 上跑 CI。

## 2026-07-25 实施状态

本轮已将上述方案落实到插件代码：

- 多物体材质按标准化名称族折叠显示，展开后保留真实材质成员；“清理材质槽”不再按 `.001/.002` 替换或删除材质。
- 材质名称改为单行主控件，移除其下方 ID/编辑/赋予/删除图标行；新增材质按钮移出列表宽度竞争区。
- 材质名前色块使用独立的 50 色高区分度调色板；材质首次分配的色块序号持久保存，删除材质不会重排其他颜色，第 51 个材质开始循环复用。
- COLOR/ALPHA/ID 状态切换会恢复前一状态；原 Base Color 连接、ID 颜色快照和预览缓存状态可恢复；Alpha 使用 Blender 4.1.1 的 Vertex Color Alpha 输出。
- 用户确认不再需要 Flatten U/V、Pin/Unpin，相关 Operator、菜单、源码和测试已完整移除；顶点组、场景选择和动态枚举问题已修复。
- 清理法向与切线现在调用 `customdata_custom_splitnormals_clear()` 和 `mesh.free_tangents()`，再应用 Smooth by Angle。
- Object/Edit Mesh 右键菜单已注册并按模式显示合法操作；注册异常和卸载 timer 也具备清理路径。
- 顶点组筛选现在是硬限制：指定组时只处理该对象中正权重的组成员；缺失组返回空候选集，不会意外退化为全局处理。
- 快捷键面板默认只显示已分配按键，并提供“显示未设置”开关，避免 20 个空槽位挤占侧栏。
- 法向角度预设和自定义角度控件已从布局区移到建模工具顶部；多物体材质组不再显示冗余的组级数量统计行。

验证结果：Blender 4.1.1 核心回归 `17/17` 通过，UI/交互回归 `5/5` 通过，63 个材质 ID 预设及越界检查全部通过，Python 编译和 `git diff --check` 通过。当前工作区保留本报告、文档、构建脚本和代码改动，尚未提交或发布版本。

## 最终评估结论（2026-07-25）

本轮针对用户反馈的三项问题已经落实：

- 多物体材质列表按去除 Blender 数字后缀后的名称族折叠显示，展开后仍展示每个真实材质数据块，不会因为显示分组而合并材质。
- 单物体材质行只保留固定色块和名称，图标不再与材质名称争夺宽度；新增材质按钮也移出列表行。
- 清理法向与切线会调用 `bpy.ops.mesh.customdata_custom_splitnormals_clear()` 和 `mesh.free_tangents()`，再应用 Smooth by Angle，并保留已有锐边标记。

复测证据：Blender 4.1.1 核心回归 `17/17`、UI/交互回归 `5/5`、63 个材质 ID 预设和越界检查全部通过；50 色循环、删除稳定性、材质编辑稳定性、原生新增材质监测及 `.blend` 保存重开均已验证；逐文件 `py_compile` 与 `git diff --check` 通过。由于当前环境无法取得有效 Blender 主窗口截图，UI 的视觉结论基于实际注册/操作回归和代码布局检查，不宣称完成像素级截图验收。

发布基础设施已补充：`build_release.py` 会从 `bl_info` 读取版本并生成可复现 ZIP；`install_addon.py` 会先分阶段解压和校验，再以继承 Blender 插件目录权限、失败可回滚的方式替换旧副本；`推送.bat` 已改为调用本地安装流程，不再切换硬编码路径或直接推送 `main`。剩余发布风险是仓库仍缺少 CI 矩阵，且插件声明版本 `1.6.0` 与远端标签 `v1.2` 不一致。因此正式重大版本仍需先统一版本元数据、运行 CI 并由我在明确授权后提交和推送。
