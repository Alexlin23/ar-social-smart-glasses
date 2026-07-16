# Agent Tool List

## 人物识别工具

### `get_visible_people`

获取当前画面中可见的人物。

返回内容可以包括：

* `track_id`
* `person_id`
* `display_name`
* `face_bbox`
* `recognition_score`
* `is_known`

### `register_person`

为陌生人物创建人物档案。

输入内容可以包括：

* 姓名
* 昵称
* 人脸特征
* 与用户的关系
* 社交账号
* 初始备注

## 人物记忆工具

### `read_person_profile`

读取指定人物的 `profile.md`。

### `search_person_memory`

搜索指定人物的对话、事件和社交媒体记录。

### `append_conversation`

将新的对话记录追加到人物的对话文件。

### `append_event`

将新事件、承诺、偏好变化或关系变化写入事件文件。

### `update_person_profile`

根据已有证据更新人物的长期档案。

更新时必须保留：

* 信息来源
* 发生时间
* 写入时间
* 置信度

## 外部信息工具

### `import_social_source`

导入微信、抖音、X 或其他社交平台的数据。

### `link_source_to_person`

将外部记录关联到指定人物。

## 对话分析工具

### `get_live_transcript`

获取当前实时对话转写。

### `analyze_conversation`

分析当前对话中的：

* 主题
* 情绪
* 问题
* 偏好
* 承诺
* 待办事项
* 值得记住的信息

### `generate_live_suggestion`

根据当前人物档案和对话上下文，生成简短的实时交流建议。
