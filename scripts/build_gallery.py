#!/usr/bin/env python3
"""Build README contact sheets from the real sample images. Requires Pillow."""
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets'
INK, MUTED, PAPER = '#483746', '#8c7582', '#fffaf7'
FONT_CANDIDATES = [
    os.environ.get('CATGIRL_FONT', ''),
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    'C:/Windows/Fonts/msyh.ttc',
    '/System/Library/Fonts/PingFang.ttc',
]


def font(size):
    for candidate in FONT_CANDIDATES:
        if candidate and Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    raise SystemExit('Set CATGIRL_FONT to a Chinese-capable TTF/TTC/OTF font.')


def rounded_image(canvas, path, box, radius=18):
    x, y, size = box
    with Image.open(ROOT / path) as image:
        # All avatars are square; preserve the entire image and both ears.
        image = image.convert('RGB').resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius, fill=255)
    canvas.paste(image, (x, y), mask)


def sheet(filename, title, subtitle, cards, columns, size=300, hero=False):
    pad, gap, top, caption = 44, 20, 174 if hero else 144, 76
    width = pad * 2 + columns * size + (columns - 1) * gap
    rows = (len(cards) + columns - 1) // columns
    height = top + rows * (size + caption + gap) + 26
    canvas = Image.new('RGB', (width, height), PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((pad, 28, pad + 150, 59), 15, fill='#f6dfe6')
    draw.text((pad + 16, 31), 'ANIMA / COMFYUI', font=font(16), fill='#906371')
    draw.text((pad, 72), title, font=font(47 if hero else 35), fill=INK)
    draw.text((pad, 133 if hero else 116), subtitle, font=font(20 if hero else 17), fill=MUTED)
    for index, (path, label, detail) in enumerate(cards):
        x = pad + (index % columns) * (size + gap)
        y = top + (index // columns) * (size + caption + gap)
        draw.rounded_rectangle((x - 1, y - 1, x + size + 1, y + size + caption), 20,
                               fill='#ffffff', outline='#eadfe4', width=1)
        rounded_image(canvas, path, (x, y, size))
        draw.text((x + 16, y + size + 12), label, font=font(24), fill=INK)
        draw.text((x + 16, y + size + 46), detail, font=font(15), fill=MUTED)
    path = ASSETS / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, 'WEBP', quality=90, method=6)
    print(path.relative_to(ROOT), canvas.size)


def main():
    sheet('hero.webp', '猫猫头 · Catgirl Avatars',
          '柔和配色 / 毛茸茸猫耳 / 31 套可复用配方 / 一个 Anima 工作流', [
              ('images/lingyin/03_wink.png', '粉色女仆猫', 'PINK / a little wink'),
              ('images/green-cat/anima/02_open_smile.png', '薄荷挑染猫', 'MINT / soft and fresh'),
              ('images/ragdoll/03_shy.png', '布偶猫', 'RAGDOLL / fluffy blue eyes'),
              ('images/calico/02_wink.png', '三花猫', 'CALICO / warm little patches'),
              ('images/red-hoodie/01_smile.png', '红卫衣猫', 'CRIMSON / twin ponytails'),
          ], 5, 280, hero=True)
    labels = [('01_closed_smile', '闭眼笑', 'content'), ('02_open_smile', '微笑', 'gentle'),
              ('03_wink', '眨眼', 'playful'), ('04_pout', '撅嘴', 'pouting'),
              ('05_happy', '开心', 'happy'), ('06_surprised', '惊讶', 'surprised'),
              ('07_shy', '害羞', 'shy'), ('08_sleepy', '困困', 'sleepy'),
              ('09_smug', '得意', 'smug'), ('10_angry', '生气', 'angry'),
              ('11_teary', '委屈', 'teary'), ('12_neutral', '平静', 'neutral')]
    sheet('expressions.webp', '一只猫，十二种心情',
          '同一角色设定与流程，逐张文生图生成；不是对同一张底图做局部编辑。',
          [(f'images/lingyin/{slug}.png', f'{i:02d}  {cn}', en)
           for i, (slug, cn, en) in enumerate(labels, 1)], 4)
    sheet('green.webp', '白发一点绿', '白发 / 绿色挑染 / 翡翠瞳 / 薄荷背景',
          [(f'images/green-cat/anima/{slug}.png', cn, en) for slug, cn, en in labels[:4]], 4)
    sheet('breeds.webp', '把猫的花色，变成角色设定', '布偶猫的奶油白与蓝眼睛，三花猫的橘、白、深色发块。', [
        (f'images/{breed}/{slug}.png', title + ' / ' + cn, detail)
        for breed, title, detail in [('ragdoll', '布偶', 'cream / seal points / blue'),
                                     ('calico', '三花', 'orange / ivory / charcoal')]
        for slug, cn in [('01_smile', '微笑'), ('02_wink', '眨眼'), ('03_shy', '害羞'), ('04_pout', '鼓脸')]
    ], 4)
    sheet('random.webp', '同一画风，五种新搭配', '发型 × 主题色 × 瞳色 × 表情 × 服装', [
        ('images/random-cat-avatars/01_mint.png', '薄荷绿 / 开心', '编辫 · 粉瞳 · 高领毛衣'),
        ('images/random-cat-avatars/02_butter-yellow.png', '奶油黄 / 困困', '侧马尾 · 青绿瞳 · 背带裙'),
        ('images/random-cat-avatars/03_lavender.png', '薰衣草 / 害羞', '银灰短发 · 金瞳 · 开衫'),
        ('images/random-cat-avatars/04_peach.png', '蜜桃橙 / 鼓脸', '双丸子 · 蓝瞳 · 卫衣'),
        ('images/random-cat-avatars/05_sky-blue.png', '天空蓝 / 眨眼', '灰紫卷发 · 紫瞳 · 水手领'),
    ], 5, 280)
    catalog = json.loads((ROOT / 'catalog.json').read_text())
    grouped = {}
    for asset in catalog['assets']:
        thumb = ASSETS / 'thumbs' / (asset['variant'] + '.webp')
        thumb.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(ROOT / asset['path']) as image:
            image.convert('RGB').resize((256, 256), Image.Resampling.LANCZOS).save(thumb, 'WEBP', quality=85)
        grouped.setdefault(asset['variant'].split('/')[0], []).append(asset)
    gallery = ['# 全部猫猫头', '', '31 张原尺寸成品；点击缩略图查看 PNG。对应配方名可直接传给 `generate.py`。', '']
    for group, assets in grouped.items():
        gallery.extend([f'## {group}', '', '| 预览 | 配方 | 尺寸 |', '|---|---|---|'])
        for asset in assets:
            name = asset['variant']
            gallery.append(f'| [<img src="assets/thumbs/{name}.webp" width="150" alt="{name}">](../{asset["path"]}) | `{name}` | 1536 × 1536 |')
        gallery.append('')
    (ROOT / 'docs/GALLERY.md').write_text('\n'.join(gallery), encoding='utf-8')


if __name__ == '__main__':
    main()
