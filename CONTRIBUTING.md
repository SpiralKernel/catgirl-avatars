# 贡献猫猫头

欢迎分享新的猫种、配色或表情配方。

1. 在 `generate.py` 的 `VARIANTS` 中增加配方，复用已有 `TEMPLATE`。
2. 只提交筛选后的成品 PNG，放到 `images/<系列>/`，不要提交模型、缓存或生成过程图。
3. 更新 `catalog.json` 的路径、尺寸、配方名及 SHA-256。图片须为可公开分享的内容。
4. 运行 `python -m unittest discover -s tests -v`。如修改执行逻辑，请同时检查本机 ComfyUI 的 `check` 与一次实际运行。
5. 用 `python scripts/build_gallery.py` 更新画廊；此步需要 `requirements-dev.txt` 中的 Pillow 和支持中文的字体，可用 `CATGIRL_FONT` 指定字体文件。

新配方保留完整正向与负向词、种子及参数差分。不要为只改提示词的版本复制整个工作流。提交说明应包含示例图，以及模型或参数是否改变。
