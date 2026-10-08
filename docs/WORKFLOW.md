# 工作流与复现

## 一张头像如何生成

1. 加载 Anima Base v1.0、Qwen3 编码器、Qwen Image VAE。
2. 正向与负向提示词分别编码，从 `1024 × 1024` 的空 latent 生成基础图：36 步、CFG 4.5、Euler ancestral / simple、降噪 1.0。
3. Tiled VAE 解码，使用 NMKD UltraYandere Lite 放大 4 倍。
4. Lanczos 缩放到 `1536 × 1536`，不裁剪画面。
5. Tiled VAE 编码，再用同一模型和提示词细化：16 步、CFG 4.5、Euler ancestral / simple、降噪 0.30。
6. Tiled VAE 解码，仅保存最终 PNG。

高清细化的输入来自本轮文生图结果。没有外部图片输入节点，也没有需要额外安装的自定义节点。

## 配方与文件的对应

`generate.py` 的 `TEMPLATE` 是唯一 API 节点结构；`VARIANTS` 记录每个成品的完整提示词差分、种子和最终保存节点。`build()` 将两者合成完整执行图，同时同步 ComfyUI 界面控件。

```bash
# 查看实际提示词和所有执行参数
python generate.py show lingyin/03_wink

# ComfyUI 界面格式
python generate.py export lingyin/03_wink --out exports/wink.workflow.json

# ComfyUI API 图格式
python generate.py export lingyin/03_wink --format api --out exports/wink.api.json
```

导出完全离线，不启动绘图。导出文件若已存在会报错；请换文件名或自行处理旧文件。API 图是 `/prompt` 请求的 `prompt` 字段，不是完整请求信封。

## 批量生成

```bash
python generate.py run \
  lingyin/01_closed_smile lingyin/02_open_smile lingyin/03_wink lingyin/04_pout
```

每个配方依次运行。脚本先检查全部所选配方依赖，再提交任务；不自动下载、不悄悄替换权重。使用 `--seed` 会同时修改基础与细化阶段种子；不传则使用存档种子。

生成文件从 ComfyUI 的 `/view` API 下载到 `outputs/`，不要求客户端和 ComfyUI 共享磁盘。ComfyUI 自身的 `output/` 中也会保存服务器端生成图。新图包含本次执行的提示词及界面流程元数据；仓库中的历史样图已移除冗余元数据，配方保存在脚本中。

## 常见问题

| 现象 | 处理 |
|---|---|
| 连不上 `127.0.0.1:8188` | 先启动 ComfyUI，或用 `--url` 指向实际地址。 |
| 文件存在但模型名不匹配 | 检查加载器目录、子目录和大小写；使用 `--model KEY=FILENAME` 指定实际名称。 |
| `UNETLoader` 存在但 Anima 加载失败 | 旧版 ComfyUI 可能尚未支持模型架构，先更新。 |
| 找不到 `4x-NMKD-UltraYandere-Lite.pth` | 放大模型也需要单独下载；放在 `models/upscale_models/`。 |
| 显存不足 | 先确认本机 ComfyUI 的显存管理设置；本流程有 1536 高清细化。更改尺寸或去掉细化会改变原配方效果。 |
| 同种子仍与样图有差别 | 对比模型 SHA-256、ComfyUI 版本、PyTorch/设备、采样器与全部提示词；跨环境不保证逐像素一致。 |
| 等待超过 30 分钟 | 可用 `--timeout` 修改客户端等待秒数。超时不会自动取消服务器任务，先在 ComfyUI 查看对应任务 ID。 |

表情差分是独立生成的插画，面部和发丝不会严格逐帧对齐。做表情包可以使用整张图；做骨骼动画或 Live2D 需要另行拆层与修整。
