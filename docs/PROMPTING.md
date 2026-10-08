# 做一只自己的猫

## 先固定风格与构图

最初好看的女仆猫和绿猫，共用的画风词是：

```text
@blade \(galaxist\), pastel colors, delicate lineart, soft shading
fine clean anime linework, carefully drawn fluffy hair locks,
soft cel coloring, subtly luminous hair highlights
```

构图描述也值得保留：

```text
Her large face occupies most of the picture;
the entire head and both cat ears fit inside the frame
with a very small margin above.
Slight three-quarter turn and a gentle head tilt,
rounded cheeks and delicate facial features.
```

标签描述概念，自然语言描述相互关系。例如“白发为主，脸侧两道绿色挑染”比单独混写 `white hair, green hair` 更清楚。完整配方仍以脚本实际字符串为准；上述是便于理解的摘录。

## 一次改一组内容

| 维度 | 可以尝试 | 描述要点 |
|---|---|---|
| 发型 | 波波头、侧辫、双马尾、双丸子、中长卷发 | 说明两侧结构和脸旁发束，避免绑发部位被耳朵遮住。 |
| 主题色 | 薄荷、奶油黄、薰衣草、蜜桃、天空蓝 | 同时约束背景、服装、少量配饰；让发色与肤色保持柔和。 |
| 瞳色 | 琥珀、粉色、青绿、紫罗兰、湖蓝 | 写明眼睛颜色和是否睁眼，闭眼时无需强调瞳色。 |
| 表情 | 微笑、眨眼、鼓脸、困倦、害羞 | 描述眼睑、嘴形、腮红；负向词不要与目标表情冲突。 |
| 服装 | 女仆装、高领毛衣、开衫、水手领、卫衣 | 头像只露衣领和肩部，把识别点放在领口。 |

## 加入自己的配方

在 `generate.py` 的 `VARIANTS` 中复制最接近的配方，换一个名称，例如 `my-cat/01_smile`。修改 `changes` 下的 `4.text`（正向）和 `5.text`（负向），以及 `image` 保存路径。

```python
'my-cat/01_smile': {
    'changes': {
        '4': {'text': '在这里写完整正向提示词'},
        '5': {'text': '在这里写完整负向提示词'},
        '7': {'seed': 20261008},
        '14': {'seed': 20261008},
    },
    'image': 'images/my-cat/01_smile.png',
    'final_node': '16',
},
```

省略某项会继承 `TEMPLATE` 的默认值。特别是默认女仆猫的负向词包含 `open eyes`、`visible pupils`，做睁眼表情时应完整替换负向词，不能只换正向词。

先导出并检查文本节点，再画一张：

```bash
python generate.py export my-cat/01_smile --out exports/my-cat.workflow.json
python generate.py run my-cat/01_smile
```

满意后再复制出表情差分。保持发型、配色、服装描述和基础种子不变，只调整表情及对应负向词，通常更容易得到属于同一角色的一组头像。
