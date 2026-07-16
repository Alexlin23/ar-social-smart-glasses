# person_id + face_id 重构

覆盖项目根目录中的六个文件：

- person_memory.py
- person_registry.py
- face_identity_store.py
- person_registration_service.py
- face_pipeline.py
- recognize_face.py

新身份规则：

- `person_id`：唯一人物。
- `face_id`：该人物的一张人脸样本。
- 人物样本：`people/<person_id>/faces/<face_id>.jpg/.npy`
- 识别缓存：`known_faces/<person_id>__<face_id>.jpg/.npy`
- 新登记不再输入 `face_key`。
- 旧 `known_faces/lin.npy` 仍可借助旧 `profile.md` 中的 `face_key` 兼容读取。
