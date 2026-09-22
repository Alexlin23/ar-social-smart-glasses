# 实时摄像头入口

`run_live_camera.py` 是附加启动入口，不会替换或修改项目原来的任何文件。它复用现有的人脸检测、识别、人物登记和 HUD 代码，将固定视频输入改为实时摄像头。

## 安装位置

将本目录中的 `run_live_camera.py` 复制到项目根目录，即与 `recognize_face.py` 位于同一目录。

项目中还需要存在以下两个模型：

```text
models/face_detection_yunet_2023mar.onnx
models/face_recognition_sface_2021dec.onnx
```

Python 环境至少需要：

```powershell
python -m pip install numpy opencv-contrib-python python-frontmatter
```

## 启动

在项目根目录运行：

```powershell
python run_live_camera.py
```

如果默认摄像头不可用：

```powershell
python run_live_camera.py --camera 1
```

可以指定采集分辨率及识别阈值：

```powershell
python run_live_camera.py --width 1920 --height 1080 --threshold 0.45
```

## 操作方式

- `Space`：暂停或继续。
- `R`：暂停并登记当前画面中的陌生人物；人物信息在运行脚本的终端里输入。
- `Q` 或 `Esc`：退出。

登记结果仍使用原项目的数据结构：

```text
people/<person_id>/profile.md
people/<person_id>/faces/<face_id>.jpg
people/<person_id>/faces/<face_id>.npy
known_faces/<person_id>__<face_id>.jpg
known_faces/<person_id>__<face_id>.npy
```

## 注意事项

- 首次测试只使用明确同意参与的人。
- 不要把 `people/`、`known_faces/` 或测试录像提交到 GitHub。
- 摄像头画面只在内存中处理；该附加脚本本身不保存视频。
- `0.45` 沿用原项目阈值，目前尚未经过正式数据集校准。
