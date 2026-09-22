# AR 显示模式使用说明

这套新增模块复用原项目的 `FaceRecognitionPipeline`、`PersonMemoryStore`、`PersonRegistrationService`、`register_unknown_person` 和窗口工具。旧入口继续可用；新入口是 `run_ar_view.py`。它提供带显示眼镜的桌面交互原型，尚未对接某一款眼镜 SDK，不提供头部定位、眼动追踪或空间锚定。

## Windows 启动

若本机已经完成部署，直接在项目目录执行：

```powershell
.\launch_ar.cmd --demo
.\launch_ar.cmd
```

第一个命令显示明确标记的合成演示，不打开摄像头、不做人脸识别、不写人物数据；第二个打开默认摄像头并使用真实模型。

在新电脑上，先安装 Python 3.10 或以上（本次验证版本为 3.12），然后执行：

```powershell
.\setup_ar.ps1 -PythonPath "C:\path\to\python.exe"
```

脚本在项目内建立独立的 `.venv-ar`，安装 `requirements-ar.txt`，从 OpenCV Zoo 下载模型并核对 Git LFS SHA-256，最后执行环境检查。若安装了 Codex 的捆绑 Python，可省略 `-PythonPath`。不要提交 `.venv-ar` 或个人数据；新增的 `.venv-ar/.gitignore` 已忽略环境内容。

如果系统策略禁止运行 PowerShell 脚本，可直接在终端依次执行等价命令，无须更改系统策略：

```powershell
python -m venv .venv-ar
.\.venv-ar\Scripts\python.exe -m pip install -r requirements-ar.txt
.\.venv-ar\Scripts\python.exe ar_setup_models.py
.\.venv-ar\Scripts\python.exe run_ar_view.py --check
```

## 摄像头和视频

```powershell
.\launch_ar.cmd --source 1
.\launch_ar.cmd --source data/demo.mp4
.\launch_ar.cmd --source data/demo.mp4 --loop
.\launch_ar.cmd --width 1280 --height 720 --font-size 26 --margin 30
```

数字表示摄像头编号。相对视频、模型、数据路径以项目目录为基准，不受终端工作目录影响；摄像头实际分辨率由设备决定。`--data-dir` 可切换独立测试数据根目录，下面仍使用原项目的 `people/` 和 `known_faces/`。

## 操作

| 按键 | 行为 |
|---|---|
| N / Tab | 按画面从左到右循环选择人物 |
| B | 选择上一个人物 |
| E / Enter | 展开或收起当前人物资料 |
| H | 隐藏或恢复人物信息；识别继续运行 |
| 空格 | 暂停或恢复识别；摄像头画面继续，人物提示清除 |
| C | 切换高对比度与半透明卡片 |
| + / - | 调整文字大小，16–40 像素 |
| R | 登记当前选中的陌生人 |
| Q / Esc | 退出并释放设备 |

启动后选择靠近画面中心的人物，之后保持选择直到目标消失或用户手动切换；这不是眼动追踪。短暂丢失期间立即隐藏卡片，约 0.6 秒后才选择其他人物。身份和追踪精度仍由原识别库决定。

默认只给焦点人物显示“姓名＋一条提醒”，其他人物仅显示简短标签，同时最多展示五人的标签。提醒依次读取档案中的承诺与待办、近期事件、历史互动摘要、兴趣与偏好、当前状态；不会编造提醒。展开后增加关系、兴趣与近况。空间不足时先退回紧凑卡，再省略无法放置的卡片，保证卡片不与已检测的人脸框或其他卡片重叠。超长文本以省略号截断。

顶部显示识别/暂停/隐藏状态，底部保留提示或字幕区域。`HudRenderer.render(..., subtitle=文本)` 支持外部字幕文本，但这一批不包含麦克风或语音转写。

登记复用原库的终端交互：先 N 切到陌生人，再按 R，回到终端输入姓名和资料；姓名留空取消。同名人物可以选择添加样本或新建。输入期间识别暂停，窗口暂不接受快捷键；完成后摄像头重新打开以丢弃旧缓存，识别自动恢复。登记会写入原有的人物目录；关闭程序不会自动删除登记信息。演示模式禁止登记合成数据。

## 运行前检查和测试

```powershell
.\launch_ar.cmd --check
.\launch_ar.cmd --demo --headless --frames 30
.\.venv-ar\Scripts\python.exe -m unittest discover -s tests_ar -v
.\.venv-ar\Scripts\python.exe tests_ar/real_model_smoke.py --image "你的已获同意的测试人脸照片.jpg"
```

`--check` 检查旧模块导入、中文字体、OpenCV 和两个实际 ONNX 模型的加载，不打开摄像头。普通测试不需要模型或摄像头；真实模型测试需要模型与指定图片，所有登记只写临时目录，测试结束清理，不影响正式人物库。照片重识别通过只能证明联动正确，不能代替不同角度、光照、多人的准确率评估。

可用 `--snapshot output.png` 显式保存最后一帧；默认不保存视频或截图。截图已存在时拒绝覆盖。画面处理超过 `--stale-seconds`（默认 1.5 秒）时不显示该帧的人物信息；输入断开则退出、关闭窗口并释放设备。

## 新增文件

| 文件 | 职责 |
|---|---|
| `run_ar_view.py` | 摄像头/视频/演示入口、原库联动、生命周期管理 |
| `ar_controls.py` | 通用操作枚举、按键映射和显示状态，可供硬件适配器调用 |
| `ar_hud/focus_manager.py` | 单人选择、循环切换、丢失后的焦点处理 |
| `ar_hud/layout.py` | 安全区域、避开人脸与卡片的布局计算 |
| `ar_hud/renderer.py` | 中文文本、精简/展开卡片、对比度、状态与字幕区域 |
| `ar_setup_models.py` | 官方模型下载及 SHA-256 校验，不覆盖已有不匹配模型 |
| `requirements-ar.txt` | 本次实测的依赖版本 |
| `setup_ar.ps1` / `launch_ar.cmd` | Windows 安装与启动 |
| `tests_ar/` | 布局、交互、旧库联动及真实模型回归验证 |

Windows 默认使用系统微软雅黑或黑体；其他平台可通过 `--font` 指定支持中文的字体。遇到 `cv2` 导入错误时，确认使用 `.venv-ar` 的 Python；避免在同一环境里混装多个 OpenCV 包或 headless 版。

模型来源与许可说明见官方仓库：
- https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
- https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface
