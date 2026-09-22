# AR Social Smart Glasses

一个面向社交辅助场景的 AR 智能眼镜原型。系统从摄像头或视频中检测、跟踪和识别人脸，读取本地人物档案，并在画面中显示低干扰的人物提示卡。陌生人物可以在运行过程中登记，后续再次出现时会关联到同一人物档案。

当前版本是运行在 Windows/PC 上的眼镜 HUD 与识别链路原型，用来验证人物识别、社交记忆和视觉交互。它尚未绑定具体眼镜 SDK，也不包含空间锚定、眼动追踪或真实光学显示适配。

## 当前功能

- 使用 OpenCV YuNet 检测人脸。
- 使用 OpenCV SFace 提取和比对人脸特征。
- 为画面中的人物分配 `track_id` 并进行基础跟踪。
- 通过 `person_id + face_id` 管理人物和多张人脸样本。
- 使用 Markdown 保存姓名、关系、兴趣、近况和待办等人物信息。
- 区分已知人物与未登记人物。
- 在摄像头或视频画面中显示中文 AR HUD。
- 自动选择靠近画面中心的人物，并支持手动切换焦点。
- 支持紧凑卡片、展开资料、隐藏信息、暂停识别、字体和对比度调节。
- 在安全显示区域中放置卡片，尽量避开人脸框和其他卡片。
- 复用原登记流程，新建人物或给同名人物添加人脸样本。
- 提供合成演示、无窗口测试、模型校验和自动化测试。

## 工作流程

```text
摄像头或视频
    ↓
YuNet 人脸检测
    ↓
基础人物跟踪
    ↓
SFace 特征匹配
    ↓
读取 people/<person_id>/profile.md
    ↓
焦点选择与 HUD 布局
    ↓
人物姓名、提醒和资料卡
```

## 运行环境

- Python 3.10 或以上
- Windows 10/11（当前主要验证平台）
- 支持 OpenCV 的摄像头，可选
- YuNet 和 SFace ONNX 模型

本项目已在 Python 3.12、OpenCV 4.12.0、NumPy 2.2.6 和 Pillow 11.3.0 环境中验证。

## 快速开始

### 1. 克隆仓库

```powershell
git clone https://github.com/Alexlin23/ar-social-smart-glasses.git
cd ar-social-smart-glasses
```

### 2. 自动配置 Windows 环境

如果 `python` 已加入系统路径：

```powershell
.\setup_ar.ps1 -PythonPath "python"
```

也可以提供 Python 可执行文件的完整路径：

```powershell
.\setup_ar.ps1 -PythonPath "C:\Path\To\Python\python.exe"
```

安装脚本将：

1. 创建独立的 `.venv-ar` 虚拟环境；
2. 安装 `requirements-ar.txt` 中的依赖；
3. 从 OpenCV Zoo 下载 YuNet 和 SFace；
4. 校验模型的 SHA-256；
5. 检查原项目模块、中文字体、OpenCV 和模型是否可用。

如果系统策略不允许运行 PowerShell 脚本，可以直接执行等价命令：

```powershell
python -m venv .venv-ar
.\.venv-ar\Scripts\python.exe -m pip install -r requirements-ar.txt
.\.venv-ar\Scripts\python.exe ar_setup_models.py
.\.venv-ar\Scripts\python.exe run_ar_view.py --check
```

### 3. 查看无摄像头演示

```powershell
.\launch_ar.cmd --demo
```

演示模式使用明确标记的合成人物，不打开摄像头、不执行人脸识别，也不会写入人物数据。

### 4. 启动默认摄像头

```powershell
.\launch_ar.cmd
```

如果电脑有多个摄像头：

```powershell
.\launch_ar.cmd --source 1
```

### 5. 使用视频文件

```powershell
.\launch_ar.cmd --source data/demo.mp4
.\launch_ar.cmd --source data/demo.mp4 --loop
```

相对路径以项目根目录为基准，不受当前终端目录影响。

## AR HUD 操作

| 按键 | 功能 |
|---|---|
| `N` / `Tab` | 按画面从左到右选择下一个人物 |
| `B` | 选择上一个人物 |
| `E` / `Enter` | 展开或收起当前人物资料 |
| `H` | 隐藏或恢复人物信息，识别继续运行 |
| `Space` | 暂停或恢复识别，人物提示立即清除 |
| `C` | 切换高对比度与半透明卡片 |
| `+` / `-` | 调整文字大小，范围为 16–40 像素 |
| `R` | 登记当前选中的陌生人物 |
| `Q` / `Esc` | 退出并释放摄像头 |

系统默认选择靠近画面中心的人物，然后保持选择，直到人物消失或用户手动切换。该行为是画面位置选择，不是眼动追踪。

焦点人物默认显示“姓名＋一条提醒”，其他人物只显示简短标签。提醒依次读取人物档案中的：

1. 承诺与待办；
2. 近期事件；
3. 历史互动摘要；
4. 兴趣与偏好；
5. 当前状态。

系统不会自动编造提醒。空间不足时会缩减或省略卡片，超长文本会截断，避免大面积遮挡画面。

## 登记人物

1. 使用 `N` 或 `B` 选择未登记人物；
2. 按 `R`；
3. 回到运行程序的终端；
4. 输入姓名、关系和可选社交账号；
5. 完成后识别自动恢复。

姓名留空会取消登记。若存在同名人物，可以选择给已有档案添加一张人脸样本，也可以新建同名人物。

登记过程复用原项目的 `PersonRegistrationService` 和 `register_unknown_person`。数据会保存到原有目录，程序退出时不会自动删除。

## 人物与人脸数据结构

- `person_id`：唯一人物标识，例如 `p_a1b2c3d4`。
- `face_id`：某个人物的一张人脸样本，例如 `face_1234abcd`。
- 同一个人物可以对应多张不同角度或光照条件的人脸样本。

```text
people/
└── <person_id>/
    ├── profile.md
    ├── faces/
    │   ├── <face_id>.jpg
    │   └── <face_id>.npy
    ├── conversations/
    ├── events/
    └── sources/

known_faces/
├── <person_id>__<face_id>.jpg
└── <person_id>__<face_id>.npy
```

`people/<person_id>/profile.md` 是人物长期档案，`known_faces` 是识别索引缓存。

旧版 `enroll_face.py` 保存的 `known_faces/<name>.npy` 不符合当前的 `person_id__face_id` 格式，当前识别索引不会自动加载这类文件。建议通过新的 AR 登记流程重新登记，或先编写迁移工具转换旧数据。

## 常用启动参数

```powershell
.\launch_ar.cmd --width 1280 --height 720
.\launch_ar.cmd --font-size 26 --margin 30
.\launch_ar.cmd --threshold 0.45
.\launch_ar.cmd --font "C:\Windows\Fonts\msyh.ttc"
.\launch_ar.cmd --data-dir "D:\AR-Test-Data"
```

查看所有参数：

```powershell
.\.venv-ar\Scripts\python.exe run_ar_view.py --help
```

重要参数：

| 参数 | 说明 |
|---|---|
| `--source` | 摄像头编号或视频路径 |
| `--demo` | 启动合成 HUD 演示 |
| `--loop` | 循环播放视频，并在回放时清理跟踪状态 |
| `--font-size` | HUD 字体大小 |
| `--margin` | 画面安全边距 |
| `--threshold` | SFace 余弦匹配阈值 |
| `--stale-seconds` | 处理超时后清除人物提示的时间 |
| `--data-dir` | 包含 `people` 和 `known_faces` 的数据根目录 |
| `--models-dir` | ONNX 模型目录 |
| `--snapshot` | 明确要求保存最后一帧截图 |
| `--check` | 检查环境和真实模型，不打开摄像头 |

程序默认不保存摄像头视频或截图。只有显式传入 `--snapshot` 时才会保存最后一帧，并拒绝覆盖已有文件。

## 环境检查与测试

检查依赖、中文字体和两个 ONNX 模型：

```powershell
.\launch_ar.cmd --check
```

运行无窗口演示：

```powershell
.\launch_ar.cmd --demo --headless --frames 30
```

运行自动化测试：

```powershell
.\.venv-ar\Scripts\python.exe -m unittest discover -s tests_ar -v
```

使用一张已获得使用同意的人脸图片运行真实模型联动测试：

```powershell
.\.venv-ar\Scripts\python.exe tests_ar/real_model_smoke.py `
  --image "D:\Test\consented-face.jpg"
```

真实模型测试使用临时人物目录，结束后自动清理，不影响正式人物库。测试验证“检测→陌生人→登记→索引重载→重新识别→HUD→重启读取”链路，但同一照片重识别不能代表真实环境中的识别准确率。

当前验证详情见 [AR_VALIDATION.md](AR_VALIDATION.md)。

## 项目结构

```text
.
├── run_ar_view.py                  # 推荐入口：摄像头、视频和演示
├── launch_ar.cmd                   # Windows 启动器
├── setup_ar.ps1                    # Windows 环境配置
├── ar_setup_models.py              # 官方模型下载与校验
├── requirements-ar.txt             # 已验证的依赖版本
├── ar_controls.py                  # 通用操作和显示状态
├── ar_hud/
│   ├── focus_manager.py            # 人物焦点选择
│   ├── layout.py                   # 安全区域和卡片避让
│   └── renderer.py                 # 中文 HUD 渲染
├── tests_ar/                       # 自动化与真实模型测试
├── face_pipeline.py                # 人脸检测、识别和人物关联
├── simple_tracker.py               # 基础 IoU 跟踪
├── person_memory.py                # 人物档案读取
├── person_registration_service.py  # 人物和人脸样本登记
├── person_card_ui.py               # 原始桌面人物卡片
├── recognize_face.py               # 原始视频识别入口
├── run_live_camera.py              # 简化实时摄像头入口
└── agent/                          # Agent 设计说明和预期工具
```

## 隐私与数据管理

人脸照片、特征、人物关系、社交账号和对话记录都属于敏感数据。测试和演示时应遵守以下原则：

- 只登记明确同意参与的人；
- 不将 `people/`、`known_faces/` 或私人测试视频提交到 GitHub；
- 默认在本地处理数据；
- 不将模型、虚拟环境、缓存和测试输出提交到仓库；
- 分享截图或演示视频前检查人物信息和背景内容；
- 面向真实用户部署前增加授权、加密、删除、导出和保存期限机制。

项目的 `.gitignore` 已忽略人物数据、识别缓存、输入视频、ONNX 模型和 Python 缓存。`.venv-ar/.gitignore` 用于避免提交本地 AR 虚拟环境。

## 当前限制

- 目前提供的是 PC 上的 AR HUD 原型，尚未连接具体智能眼镜 SDK。
- 没有空间锚定、头部姿态跟踪、眼动追踪或光学标定。
- `SimpleIoUTracker` 仅使用框重叠率，多人交叉或快速移动时可能交换 `track_id`。
- 人脸阈值沿用当前配置，尚未使用正式数据集完成系统校准。
- 登记界面仍在终端输入，登记期间窗口暂不接受快捷键。
- 尚未实现语音转写、说话人关联和 LLM 实时建议。
- 人脸数据和人物档案目前以本地明文文件保存，尚未实现加密。

## 后续方向

- 为指定眼镜平台实现摄像头、显示和按键适配器；
- 使用 ByteTrack、BoT-SORT 或身份特征改善多人跟踪；
- 通过多帧采集和人脸质量检查提高登记质量；
- 增加人物档案的编辑、合并、删除和导出界面；
- 增加本地加密、同意状态和数据保存期限；
- 接入 VAD、流式语音识别和短字幕；
- 在用户确认后生成并写入对话摘要或社交提醒。

## 更多文档

- [AR 显示模式使用说明](AR_VIEW_GUIDE.md)
- [AR 第一批功能验证记录](AR_VALIDATION.md)
- [简化摄像头入口说明](CAMERA_QUICKSTART.md)
- [Agent 系统提示词](agent/system_prompt.md)
- [Agent 预期工具清单](agent/tool_list.md)

YuNet 与 SFace 模型由安装脚本从 OpenCV Zoo 下载，模型来源和许可信息请查看：

- [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
- [OpenCV Zoo SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface)

## 许可证

当前仓库尚未包含 `LICENSE` 文件。代码的使用、复制和分发权限需要由项目维护者明确。准备对外开放协作或发布版本前，请先选择并添加合适的开源许可证。
