# AR 社交智能系统 Memory

## 1. 项目目标

本项目旨在构建一个面向 AR 眼镜的社交智能辅助系统。

当前尚未接入真实 AR 眼镜，因此使用本地视频模拟第一视角摄像头输入，优先完成后端视觉处理、人物识别、人物记忆、陌生人登记、实时对话记录和 Agent 分析基座。

目标体验：

1. 检测画面中的人物。
2. 为同一个人物维护稳定的 `track_id`。
3. 通过人脸识别关联人物 Markdown 档案。
4. 从人物位置拉出连线和游戏化人物卡片。
5. 对陌生人物触发登记流程。
6. 关联微信、抖音、X 等社交平台信息。
7. 实时记录和分析当前对话。
8. 给出简短的社交和沟通建议。
9. 将可靠的新信息持续写入人物 Markdown 知识库。

---

## 2. 核心架构原则

### Markdown-first

人物知识以 Markdown 文件作为主要事实源。

数据库、全文搜索和向量库只能作为：

* 搜索索引；
* 运行缓存；
* 可重新生成的派生数据。

任何索引都应能够从 Markdown 文件重新构建。

### 原始信息追加写入

以下数据原则上只追加，不直接覆盖：

* 实时对话转写；
* 微信聊天记录；
* 抖音内容和互动；
* X 内容和互动；
* 人物事件；
* Agent 分析记录；
* 外部数据导入记录。

### 长期画像与原始记录分离

* `profile.md`：人物当前的长期画像。
* `conversations/`：原始对话和对话摘要。
* `events/`：事件、承诺、偏好和关系变化。
* `sources/`：微信、抖音、X 等外部来源。

### 身份标识

* `person_id`：人物永久唯一标识。
* `face_key`：人脸文件和人物档案之间的关联键。
* `display_name`：用于界面显示的名称。
* `track_id`：一次视频会话中的临时跟踪编号。

身份链路：

```text
视频中的人脸
    ↓
track_id
    ↓
SFace 特征匹配
    ↓
face_key
    ↓
person_id
    ↓
people/<person_id>/profile.md
```

---

## 3. 当前 Git 文件结构

```text
.
├── .gitignore
├── agent
│   ├── memory.md
│   ├── system_prompt.md
│   └── tool_list.md
├── ar_face_demo_refactor_phase1
│   ├── face_pipeline.py
│   ├── person_card_ui.py
│   ├── README.md
│   ├── recognize_face.py
│   └── window_ui.py
├── camera_test.py
├── enroll_face.py
├── face_identity_store.py
├── face_pipeline.py
├── people
│   ├── p_319f5a4e
│   │   └── profile.md
│   └── p_lin
│       └── profile.md
├── person_card_ui.py
├── person_memory.py
├── person_registry.py
├── README.md
├── recognize_face.py
├── simple_tracker.py
└── window_ui.py
```

该结构只包含未被 `.gitignore` 排除的文件。

以下运行时目录当前未显示，但项目运行仍依赖它们：

```text
data/
models/
known_faces/
.venv/
```

---

## 4. 根目录文件职责

### `.gitignore`

定义不进入 Git 的文件和目录。

通常应忽略：

* `.venv/`
* `__pycache__/`
* `*.pyc`
* 大型模型文件；
* 测试视频；
* 本地人脸特征；
* 临时输出；
* 隐私人物数据。

需要注意：人物 Markdown 档案是否进入 Git，应根据隐私和部署策略决定。

---

### `README.md`

项目主说明文档。

应包含：

* 项目介绍；
* 当前功能；
* 环境要求；
* 安装命令；
* 目录结构；
* 启动方法；
* 快捷键；
* 当前限制；
* 后续路线。

---

### `recognize_face.py`

当前人脸识别 Demo 的主入口。

职责：

* 打开视频输入；
* 初始化人物记忆；
* 初始化视觉处理管线；
* 管理视频播放循环；
* 处理暂停、继续和退出；
* 调用人物卡片渲染；
* 调用窗口显示模块；
* 编排各功能模块。

原则：

* 不应包含复杂人脸算法；
* 不应包含大段卡片布局算法；
* 不应直接承担人物档案写入；
* 不应直接实现 Agent 逻辑。

---

### `face_pipeline.py`

人脸检测、识别和跟踪处理管线。

职责：

* 加载 YuNet 人脸检测模型；
* 加载 SFace 人脸识别模型；
* 加载已知人脸特征；
* 检测当前帧中的人脸；
* 对人脸进行对齐裁剪；
* 提取特征向量；
* 与已知人脸进行相似度匹配；
* 调用 `SimpleIoUTracker`；
* 对身份结果进行时间平滑；
* 将 `face_key` 关联到人物档案；
* 返回统一的人物识别结果。

该模块不负责：

* 创建 OpenCV 窗口；
* 处理键盘；
* 绘制复杂人物卡片；
* 修改人物 Markdown。

---

### `simple_tracker.py`

轻量人物跟踪模块。

职责：

* 通过人脸框 IoU 关联前后帧；
* 为人物分配稳定的 `track_id`；
* 记录轨迹暂时丢失的帧数；
* 删除长时间消失的轨迹；
* 保存识别历史；
* 对人物姓名进行简单多数投票；
* 对相似度进行简单时间平均。

当前限制：

* 快速移动时可能丢失；
* 遮挡后可能生成新编号；
* 人物离开画面再返回后通常会获得新的 `track_id`；
* 尚未使用人体 ReID 或人脸特征辅助跟踪。

---

### `person_card_ui.py`

AR 人物卡片渲染模块。

职责：

* 绘制人脸框；
* 绘制人脸到人物卡片的连线；
* 绘制已知人物卡片；
* 绘制陌生人物登记提示；
* 将人物 Markdown 信息转换为显示内容；
* 根据文本数量计算卡片尺寸；
* 对长文本换行；
* 选择卡片显示位置；
* 尽量避免卡片覆盖人脸；
* 控制透明背景、边框和字体样式。

该模块不负责：

* 人脸识别；
* 人物跟踪；
* Markdown 文件写入；
* 视频读取。

---

### `window_ui.py`

视频窗口和显示缩放模块。

职责：

* 创建 OpenCV 可缩放窗口；
* 获取 Windows 屏幕尺寸；
* 根据视频比例计算初始窗口大小；
* 获取当前窗口大小；
* 对视频画面等比例缩放；
* 在比例不一致时填充黑边；
* 防止人物和 UI 被拉伸；
* 显示暂停状态；
* 判断窗口是否被关闭。

---

### `camera_test.py`

视频输入和 YuNet 检测测试程序。

职责：

* 验证视频文件是否能够打开；
* 验证视频 FPS 和画面尺寸；
* 测试 YuNet 人脸检测；
* 显示人脸框和检测置信度；
* 测试暂停、继续和循环播放；
* 用于排查视频和模型基础问题。

该文件属于调试工具，不是正式主入口。

---

### `enroll_face.py`

离线人脸录入工具。

职责：

* 从视频中选择清晰人脸；
* 使用 YuNet 检测人脸；
* 默认选择画面中面积最大的人脸；
* 使用 SFace 对齐人脸；
* 提取人脸特征；
* 保存人脸图片；
* 保存 `.npy` 特征向量；
* 支持暂停后选择最佳帧；
* 支持按 `S` 完成保存。

当前输出通常位于：

```text
known_faces/
├── <face_key>.jpg
└── <face_key>.npy
```

---

### `person_memory.py`

人物 Markdown 读取和索引模块。

职责：

* 扫描 `people/*/profile.md`；
* 解析 YAML Front Matter；
* 解析 Markdown 二级标题；
* 构建 `person_id` 索引；
* 构建 `face_key → person_id` 索引；
* 根据 `person_id` 查询人物；
* 根据 `face_key` 查询人物；
* 为视觉模块和 Agent 提供统一人物档案对象。

当前以读取为主。

后续可以扩展：

* 重新加载；
* 增量刷新；
* 目录监听；
* 搜索人物事件和对话；
* 生成可重建索引。

---

### `person_registry.py`

人物 Markdown 档案创建模块。

职责：

* 生成唯一 `person_id`；
* 检查 `face_key` 是否重复；
* 创建人物目录；
* 创建 `profile.md`；
* 初始化人物子目录；
* 写入姓名、关系和社交账号；
* 初始化微信、抖音、X 和其他来源目录。

当前限制：

* 只创建人物档案；
* 不会保存实际人脸图片；
* 不会保存 SFace 特征；
* 还没有和人脸登记形成原子操作。

---

### `face_identity_store.py`

人脸身份文件存储模块。

职责：

* 根据 `face_key` 保存人脸图片；
* 保存人脸特征向量；
* 检查人脸身份是否已经存在；
* 阻止默认覆盖已有身份；
* 校验图片和特征是否为空；
* 维护 `known_faces/` 快速识别索引。

典型输出：

```text
known_faces/
├── <face_key>.jpg
└── <face_key>.npy
```

该模块只保存人脸文件，不创建人物 Markdown 档案。


---

## 5. Agent 目录职责

### `agent/system_prompt.md`

Agent 的系统提示词。

应定义：

* 项目背景；
* Agent 身份；
* Agent 职责；
* 信息可信度原则；
* Markdown-first 原则；
* 隐私要求；
* 档案更新约束；
* 实时建议的长度和优先级。

---

### `agent/tool_list.md`

Agent 工具清单。

计划覆盖：

* 获取当前可见人物；
* 读取人物档案；
* 搜索人物记忆；
* 追加实时对话；
* 追加人物事件；
* 更新长期画像；
* 导入微信记录；
* 导入抖音记录；
* 导入 X 记录；
* 关联来源和人物；
* 登记陌生人物；
* 生成实时社交建议。

工具清单表示预期能力，不代表所有工具已经实现。

---

### `agent/memory.md`

保存项目长期稳定的架构记忆。

应记录：

* 项目目标；
* 核心约定；
* 当前目录结构；
* 每个文件职责；
* 当前完成状态；
* 已知限制；
* 下一阶段任务。

不应记录：

* 临时命令输出；
* 一次性报错；
* 无长期价值的调试细节。

---

## 6. 人物目录

### `people/p_lin/profile.md`

当前已知人物 `lin` 的长期 Markdown 档案。

包含：

* `person_id`；
* `display_name`；
* `face_key`；
* 人物关系；
* 社交账号；
* 兴趣和偏好；
* 当前状态；
* 近期事件；
* 历史互动；
* AI 交互建议。

该档案应与：

```text
known_faces/lin.npy
```

使用相同 `face_key`。

---

### `people/p_319f5a4e/profile.md`

通过 `person_registry.py` 创建的测试人物档案。

当前可能只有 Markdown 档案，没有对应的人脸图片和特征。

因此该人物目前不一定能够被人脸识别。

需要确认是否存在：

```text
known_faces/<face_key>.jpg
known_faces/<face_key>.npy
```

若不存在，该人物属于“已建档但未录入人脸”的状态。

---

## 7. 临时重复目录

### `ar_face_demo_refactor_phase1/`

这是第一阶段重构压缩包解压后留下的副本。

目录内包含：

* `face_pipeline.py`
* `person_card_ui.py`
* `recognize_face.py`
* `window_ui.py`
* `README.md`

正式程序当前使用的是项目根目录中的同名文件。

该目录不应作为正式代码依赖，否则容易出现：

* 修改错文件；
* 根目录和副本版本不一致；
* 导入路径混乱；
* Git 中保存重复代码。

确认根目录版本可以正常运行后，可以删除该目录。

---

## 8. 被 `.gitignore` 隐藏的运行时目录

### `data/`

保存测试视频和未来的音频输入。

当前视频文件用于模拟 AR 眼镜第一视角摄像头。

---

### `models/`

保存本地视觉和语音模型。

当前包括：

* YuNet 人脸检测模型；
* SFace 人脸识别模型。

---

### `known_faces/`

保存快速人脸识别索引。

规则：

```text
<face_key>.jpg
<face_key>.npy
```

该目录当前属于 Demo 运行缓存和身份索引。

---

### `.venv/`

Python 虚拟环境。

不应提交到 Git。

---

## 9. 当前运行链路

```text
视频文件
    ↓
recognize_face.py
    ↓
face_pipeline.py
    ├── YuNet 人脸检测
    ├── SimpleIoUTracker 跟踪
    ├── SFace 特征提取
    ├── known_faces 特征匹配
    └── PersonMemoryStore 档案关联
    ↓
person_card_ui.py
    ├── 人脸框
    ├── AR 连线
    └── 人物卡片
    ↓
window_ui.py
    ├── 等比例缩放
    ├── 黑边填充
    └── 窗口显示
```

---

## 10. 当前已完成功能

* Python 虚拟环境；
* RTX 5070 GPU 环境验证；
* 本地视频模拟摄像头；
* 视频循环播放；
* 暂停、继续和退出；
* YuNet 人脸检测；
* SFace 特征提取；
* 离线人脸录入；
* 已知和陌生人物判断；
* 余弦相似度显示；
* IoU 人物跟踪；
* 稳定 `track_id`；
* 身份时间平滑；
* Markdown 人物档案；
* `face_key → person_id` 映射；
* AR 人脸框；
* AR 人物连线；
* 人物资料卡；
* 等比例窗口缩放；
* 人物档案创建；
* 人脸身份文件存储；
* 第一阶段代码解耦。

---

## 11. 当前已知问题

### 人物登记不是原子操作

目前：

* `PersonRegistry` 创建 Markdown；
* `FaceIdentityStore` 保存人脸文件。

两者尚未组成统一流程。

可能产生：

* 有档案但没有人脸；
* 有人脸但没有档案；
* 部分创建成功、部分失败；
* 内存索引没有及时刷新。

### 重复代码目录尚未清理

`ar_face_demo_refactor_phase1/` 与根目录存在重复文件。

### 当前一个身份通常只有单个人脸样本

对侧脸、光线、距离和遮挡的鲁棒性有限。

### 当前跟踪器只依赖 IoU

快速运动和遮挡可能导致 `track_id` 变化。

### 尚未实现对话系统

当前没有：

* 麦克风输入；
* 实时语音识别；
* 说话人分离；
* 人脸与说话人绑定；
* 实时对话分析；
* Markdown 增量写入；
* Agent 社交建议。

---

## 12. 下一阶段任务

优先顺序：

2. 删除重复的 `ar_face_demo_refactor_phase1/`。
3. 实现 `PersonRegistrationService`。
4. 将人物档案和人脸存储合并为一个原子操作。
5. 将陌生人物的 `R` 键接入登记流程。
6. 登记成功后刷新人物和人脸索引。
7. 支持单个人物多个人脸样本。
8. 建立 Markdown 追加写入服务。
9. 设计实时对话 Markdown 格式。
10. 接入实时语音转写。
11. 实现 Agent 对话分析。
12. 将可靠事实增量写入人物事件和长期画像。

---

## 13. 开发约束

* 每轮最多提供三条命令或三块文本编辑。
* 优先完成可运行、可验证的垂直功能。
* 大文件继续增长前必须优先解耦。
* 新 Python 模块必须通过 `python -m py_compile`。
* Markdown 是人物事实源。
* 数据库不能替代 Markdown。
* Agent 不得无依据修改人物画像。
* 长期事实更新必须保留来源、时间和置信度。
* 原始聊天和社交媒体记录不得无痕覆盖。
* UI、视觉识别、存储和 Agent 逻辑必须保持解耦。
