# 模型准备

主流程固定使用 **Anima Base v1.0**。为了保留最喜欢的画风，没有替换成 Turbo、其他微调版或别的模型。

## 四个文件

| 组件 | 工作流文件名 | 放到 ComfyUI 的哪个目录 | 来源 |
|---|---|---|---|
| Anima Base v1.0 | `anima-base-v1.0.safetensors` | `models/diffusion_models/` | [作者仓库](https://huggingface.co/circlestone-labs/Anima/blob/main/split_files/diffusion_models/anima-base-v1.0.safetensors) |
| Qwen3 0.6B 编码器 | `qwen_3_06b_base.safetensors` | `models/text_encoders/` | [作者文件](https://huggingface.co/circlestone-labs/Anima/blob/main/split_files/text_encoders/qwen_3_06b_base.safetensors) |
| Qwen Image VAE | `qwen_image_vae.safetensors` | `models/vae/` | [作者文件](https://huggingface.co/circlestone-labs/Anima/blob/main/split_files/vae/qwen_image_vae.safetensors) |
| NMKD 4× 放大器 | `4x-NMKD-UltraYandere-Lite.pth` | `models/upscale_models/` | [模型页面 / 下载入口](https://openmodeldb.info/models/4x-NMKD-UltraYandere-Lite) |

文件结构与 [ComfyUI 官方 Anima 模板](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_anima_base_v1.json) 一致；本项目额外使用放大器和高清细化。本流程使用 `CLIPLoader` 的 `stable_diffusion` 类型，保持原项目设置。

从 **ComfyUI 根目录** 下载前三个文件，可使用 `wget`：

```bash
mkdir -p models/diffusion_models models/text_encoders models/vae models/upscale_models

wget -c -P models/diffusion_models \
  https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/diffusion_models/anima-base-v1.0.safetensors
wget -c -P models/text_encoders \
  https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/text_encoders/qwen_3_06b_base.safetensors
wget -c -P models/vae \
  https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/vae/qwen_image_vae.safetensors
```

在 NMKD 模型页面下载 **UltraYandere Lite**，放进表格对应目录。不要把 `YandereNeo` 或其他放大器当作同一个文件。

下载后刷新模型列表或重启 ComfyUI，再运行：

```bash
python generate.py check
```

## 文件名与校验

原项目中的主模型文件名是 `anima_baseV10.safetensors`。它与这里采用的作者文件名 `anima-base-v1.0.safetensors` 有相同 SHA-256：

```text
bd43b7cffe1ed1153d9c41e7beb2f18cb1273eafbaa3af3edd6a173dc90a006e
```

脚本检查和运行时会自动识别这两个文件名。直接使用界面 JSON 时，在模型加载器选择本机实际文件名即可。其他命名可显式传入：

```bash
python generate.py run lingyin/03_wink \
  --model unet_name=ANIMA/my-base-v1.safetensors \
  --model clip_name=qwen_3_06b_base.safetensors
```

`--model` 可使用的键为 `unet_name`、`clip_name`、`vae_name`、`model_name`。这些选项只指定文件名，不下载权重。

[`models.json`](../models.json) 保存了四个本机实际使用文件的完整 SHA-256 与字节数。示例图片的哈希另见 [`catalog.json`](../catalog.json)。

## 环境记录

发布整理时检查的本机环境：

- ComfyUI 版本字段：`0.33.0`；Git commit：`a1079ba16f2674734b065eb036fbfdddaa321a4d`。
- ComfyUI frontend：`1.49.6`。
- 工作流使用 ComfyUI 原生节点，包括 `UNETLoader`、`CLIPLoader`、`VAEDecodeTiled` 与 `VAEEncodeTiled`。
- 脚本客户端：Python 3.10+，无需额外 Python 包；生成环境由 ComfyUI 自身管理。

这是已检查环境的记录，不是最低版本或所有图片的历史运行环境。若旧版 ComfyUI 无法加载 Anima，应先按 [ComfyUI 更新说明](https://docs.comfy.org/installation/update_comfyui) 更新。

模型权重不在仓库内。使用前请查看 [Anima 上游许可](https://huggingface.co/circlestone-labs/Anima/blob/main/LICENSE.md) 和各下载页面的使用条款。
