#!/usr/bin/env python3
"""Catgirl Avatars: one Anima workflow, named text-to-image recipes. Python 3.10+."""
import argparse
import copy
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_ALIASES = {"anima-base-v1.0.safetensors": ("anima_baseV10.safetensors",)}

# Original Anima graph; the canonical model filename has the same SHA-256.
TEMPLATE = {'1': {'class_type': 'UNETLoader',
       'inputs': {'unet_name': 'anima-base-v1.0.safetensors', 'weight_dtype': 'default'}},
 '2': {'class_type': 'CLIPLoader',
       'inputs': {'clip_name': 'qwen_3_06b_base.safetensors',
                  'type': 'stable_diffusion',
                  'device': 'default'}},
 '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'qwen_image_vae.safetensors'}},
 '4': {'class_type': 'CLIPTextEncode',
       'inputs': {'clip': ['2', 0],
                  'text': 'masterpiece, best quality, score_7, highres, safe, @blade \\(galaxist\\), 1girl, '
                          'solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, '
                          'portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, '
                          'white collar, frills, pink ribbon, light pink background, simple background, '
                          'floating petals, pastel colors, delicate lineart, soft shading, closed eyes, :3, '
                          'blush.\n'
                          '\n'
                          'A cute anime catgirl avatar in a square close-up portrait. She has fluffy '
                          'chocolate-brown bobbed hair and two furry brown cat ears with pale pink '
                          'interiors. A small white frilled maid headband sits between the ears, with one '
                          'small pastel pink bow. She wears a classic black-and-white maid dress: a high '
                          'white frilled collar, a little rose-pink ribbon at her throat, and white shoulder '
                          'frills. Only her neck and the tops of her shoulders appear at the lower edge. Her '
                          'large face occupies most of the picture; the entire head and both cat ears fit '
                          'inside the frame with a very small margin above. Slight three-quarter turn and a '
                          'gentle head tilt, rounded cheeks and delicate facial features. Both eyes are '
                          'completely closed in soft smiling arcs; her small mouth makes a sweet catlike '
                          'smile.\n'
                          '\n'
                          'Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly '
                          'luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black '
                          'and ivory palette. A quiet pale pink background with a few tiny drifting '
                          'cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, '
                          'fully dressed.'}},
 '5': {'class_type': 'CLIPTextEncode',
       'inputs': {'clip': ['2', 0],
                  'text': 'score_1, score_2, score_3, artist name, worst quality, low quality, lowres, '
                          'blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra '
                          'eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, '
                          'logo, full body, distant view, tiny face, cropped head, cropped ears, head out of '
                          'frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, '
                          'green hair, green background, photorealistic, realistic skin, 3d, render, harsh '
                          'lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, '
                          'low neckline, open eyes, half-closed eyes, visible pupils'}},
 '6': {'class_type': 'EmptyLatentImage', 'inputs': {'width': 1024, 'height': 1024, 'batch_size': 1}},
 '7': {'class_type': 'KSampler',
       'inputs': {'model': ['1', 0],
                  'positive': ['4', 0],
                  'negative': ['5', 0],
                  'seed': 3444821748,
                  'sampler_name': 'euler_ancestral',
                  'scheduler': 'simple',
                  'latent_image': ['6', 0],
                  'steps': 36,
                  'cfg': 4.5,
                  'denoise': 1.0}},
 '8': {'class_type': 'VAEDecodeTiled',
       'inputs': {'vae': ['3', 0],
                  'tile_size': 512,
                  'overlap': 64,
                  'temporal_size': 64,
                  'temporal_overlap': 8,
                  'samples': ['7', 0]}},
 '10': {'class_type': 'UpscaleModelLoader', 'inputs': {'model_name': '4x-NMKD-UltraYandere-Lite.pth'}},
 '11': {'class_type': 'ImageUpscaleWithModel', 'inputs': {'upscale_model': ['10', 0], 'image': ['8', 0]}},
 '12': {'class_type': 'ImageScale',
        'inputs': {'image': ['11', 0],
                   'upscale_method': 'lanczos',
                   'width': 1536,
                   'height': 1536,
                   'crop': 'disabled'}},
 '13': {'class_type': 'VAEEncodeTiled',
        'inputs': {'vae': ['3', 0],
                   'tile_size': 512,
                   'overlap': 64,
                   'temporal_size': 64,
                   'temporal_overlap': 8,
                   'pixels': ['12', 0]}},
 '14': {'class_type': 'KSampler',
        'inputs': {'model': ['1', 0],
                   'positive': ['4', 0],
                   'negative': ['5', 0],
                   'seed': 3444821748,
                   'sampler_name': 'euler_ancestral',
                   'scheduler': 'simple',
                   'latent_image': ['13', 0],
                   'steps': 16,
                   'cfg': 4.5,
                   'denoise': 0.3}},
 '15': {'class_type': 'VAEDecodeTiled',
        'inputs': {'vae': ['3', 0],
                   'tile_size': 512,
                   'overlap': 64,
                   'temporal_size': 64,
                   'temporal_overlap': 8,
                   'samples': ['14', 0]}},
 '16': {'class_type': 'SaveImage',
        'inputs': {'images': ['15', 0], 'filename_prefix': 'catgirl-avatars/lingyin/01_closed_smile'}}}

# Full positive/negative prompts and seeds are kept here, without per-expression workflow copies.
VARIANTS = {
    'calico/01_smile': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, (multicolored hair:1.3), orange hair, black hair, asymmetrical hair color, fluffy hair, bob cut, bangs, amber eyes, cream cardigan, white collar, orange ribbon, portrait, close-up, headshot, cute, warm cream background, simple background, pastel colors, delicate lineart, soft shading, looking at viewer, smile, closed mouth, blush.

A playful calico-cat-inspired girl with a fluffy chin-length bob in THREE clearly distinct fur colors. The main hair crown, central bangs and several cheek locks are warm ivory-white. A broad marmalade-orange patch covers the viewer-left front fringe and outer sidelock. A separate solid charcoal-black patch covers the viewer-right temple and outer sidelock. These are large clearly separated orange and black sections on white hair, with asymmetrical patch boundaries. The viewer-left cat ear is marmalade-orange outside; the viewer-right cat ear is charcoal-black outside. Both ears have soft ivory inner fluff. Natural pale human facial skin, large warm honey-amber eyes with little sparkling highlights. She wears a simple soft buttercream cardigan over a fully covering white blouse with a narrow white collar, one tiny burnt-orange ribbon at her throat and a small charcoal button. Warm and cozy everyday clothes. A quiet pale warm-cream background with just two tiny apricot sparkle shapes. Ivory, marmalade-orange and charcoal-black with amber eyes, minimal accessories.

Her eyes are normally open and look gently toward the viewer. A tiny warm closed-mouth smile and softly rosy cheeks. Calm and affectionate.

A cute anime catgirl avatar in a square close-up portrait, rounded delicate face and large luminous eyes, natural pale facial skin and subtle rosy cheeks. Her whole fluffy head and both cat ears fit inside the frame with a very small margin above. Her large face occupies most of the picture. Only her neck and the tops of her shoulders appear at the bottom. Slight three-quarter turn and a gentle head tilt. Fine clean anime linework, carefully shaped soft fluffy hair locks, soft cel coloring with restrained shadows and broad calm colors. Minimal accessories, excellent readability at tiny avatar size, polished and expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, animal face, animal muzzle, furry face, fur on facial skin, face paint, literal cat, bird, feather ornament, fox ears, bunny ears, maid, maid headdress, headband, monochrome hair, single hair color, uniform orange hair, uniform black hair, solid white hair, symmetrical hair color, striped hair, green hair, pink hair, blue hair, blue eyes, angry, frown, crying, tears, open mouth''',
            },
        },
        'image': 'images/calico/01_smile.png',
        'final_node': '16',
    },
    'calico/02_wink': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, (multicolored hair:1.3), orange hair, black hair, asymmetrical hair color, fluffy hair, bob cut, bangs, amber eyes, cream cardigan, white collar, orange ribbon, portrait, close-up, headshot, cute, warm cream background, simple background, pastel colors, delicate lineart, soft shading, (wink:1.7), one eye closed, one eye open, looking at viewer, smile, open mouth, blush.

A playful calico-cat-inspired girl with a fluffy chin-length bob in THREE clearly distinct fur colors. The main hair crown, central bangs and several cheek locks are warm ivory-white. A broad marmalade-orange patch covers the viewer-left front fringe and outer sidelock. A separate solid charcoal-black patch covers the viewer-right temple and outer sidelock. These are large clearly separated orange and black sections on white hair, with asymmetrical patch boundaries. The viewer-left cat ear is marmalade-orange outside; the viewer-right cat ear is charcoal-black outside. Both ears have soft ivory inner fluff. Natural pale human facial skin, large warm honey-amber eyes with little sparkling highlights. She wears a simple soft buttercream cardigan over a fully covering white blouse with a narrow white collar, one tiny burnt-orange ribbon at her throat and a small charcoal button. Warm and cozy everyday clothes. A quiet pale warm-cream background with just two tiny apricot sparkle shapes. Ivory, marmalade-orange and charcoal-black with amber eyes, minimal accessories.

One eye is completely closed in a clear playful wink; the other eye remains wide open and sparkling toward the viewer. A cheerful small open-mouth grin with a tiny upper tooth visible, rosy cheeks. Mischievous and adorable.

A cute anime catgirl avatar in a square close-up portrait, rounded delicate face and large luminous eyes, natural pale facial skin and subtle rosy cheeks. Her whole fluffy head and both cat ears fit inside the frame with a very small margin above. Her large face occupies most of the picture. Only her neck and the tops of her shoulders appear at the bottom. Slight three-quarter turn and a gentle head tilt. Fine clean anime linework, carefully shaped soft fluffy hair locks, soft cel coloring with restrained shadows and broad calm colors. Minimal accessories, excellent readability at tiny avatar size, polished and expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, animal face, animal muzzle, furry face, fur on facial skin, face paint, literal cat, bird, feather ornament, fox ears, bunny ears, maid, maid headdress, headband, monochrome hair, single hair color, uniform orange hair, uniform black hair, solid white hair, symmetrical hair color, striped hair, green hair, pink hair, blue hair, blue eyes, both eyes closed, two closed eyes, sleepy, frown, crying''',
            },
        },
        'image': 'images/calico/02_wink.png',
        'final_node': '16',
    },
    'calico/03_shy': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, (multicolored hair:1.3), orange hair, black hair, asymmetrical hair color, fluffy hair, bob cut, bangs, amber eyes, cream cardigan, white collar, orange ribbon, portrait, close-up, headshot, cute, warm cream background, simple background, pastel colors, delicate lineart, soft shading, (embarrassed:1.8), (blush:1.7), looking away, closed mouth.

A playful calico-cat-inspired girl with a fluffy chin-length bob in THREE clearly distinct fur colors. The main hair crown, central bangs and several cheek locks are warm ivory-white. A broad marmalade-orange patch covers the viewer-left front fringe and outer sidelock. A separate solid charcoal-black patch covers the viewer-right temple and outer sidelock. These are large clearly separated orange and black sections on white hair, with asymmetrical patch boundaries. The viewer-left cat ear is marmalade-orange outside; the viewer-right cat ear is charcoal-black outside. Both ears have soft ivory inner fluff. Natural pale human facial skin, large warm honey-amber eyes with little sparkling highlights. She wears a simple soft buttercream cardigan over a fully covering white blouse with a narrow white collar, one tiny burnt-orange ribbon at her throat and a small charcoal button. Warm and cozy everyday clothes. A quiet pale warm-cream background with just two tiny apricot sparkle shapes. Ivory, marmalade-orange and charcoal-black with amber eyes, minimal accessories.

She looks slightly downward and to one side, avoiding eye contact shyly. Both cheeks are visibly rosy with soft blush strokes. A tiny hesitant closed mouth and gently raised inner eyebrows. Sweet and embarrassed.

A cute anime catgirl avatar in a square close-up portrait, rounded delicate face and large luminous eyes, natural pale facial skin and subtle rosy cheeks. Her whole fluffy head and both cat ears fit inside the frame with a very small margin above. Her large face occupies most of the picture. Only her neck and the tops of her shoulders appear at the bottom. Slight three-quarter turn and a gentle head tilt. Fine clean anime linework, carefully shaped soft fluffy hair locks, soft cel coloring with restrained shadows and broad calm colors. Minimal accessories, excellent readability at tiny avatar size, polished and expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, animal face, animal muzzle, furry face, fur on facial skin, face paint, literal cat, bird, feather ornament, fox ears, bunny ears, maid, maid headdress, headband, monochrome hair, single hair color, uniform orange hair, uniform black hair, solid white hair, symmetrical hair color, striped hair, green hair, pink hair, blue hair, blue eyes, looking at viewer, bold smile, open mouth, laughing''',
            },
        },
        'image': 'images/calico/03_shy.png',
        'final_node': '16',
    },
    'calico/04_pout': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, (multicolored hair:1.3), orange hair, black hair, asymmetrical hair color, fluffy hair, bob cut, bangs, amber eyes, cream cardigan, white collar, orange ribbon, portrait, close-up, headshot, cute, warm cream background, simple background, pastel colors, delicate lineart, soft shading, (pout:2.0), (puffed cheeks:1.8), (frown:1.4), looking at viewer, closed mouth, blush.

A playful calico-cat-inspired girl with a fluffy chin-length bob in THREE clearly distinct fur colors. The main hair crown, central bangs and several cheek locks are warm ivory-white. A broad marmalade-orange patch covers the viewer-left front fringe and outer sidelock. A separate solid charcoal-black patch covers the viewer-right temple and outer sidelock. These are large clearly separated orange and black sections on white hair, with asymmetrical patch boundaries. The viewer-left cat ear is marmalade-orange outside; the viewer-right cat ear is charcoal-black outside. Both ears have soft ivory inner fluff. Natural pale human facial skin, large warm honey-amber eyes with little sparkling highlights. She wears a simple soft buttercream cardigan over a fully covering white blouse with a narrow white collar, one tiny burnt-orange ribbon at her throat and a small charcoal button. Warm and cozy everyday clothes. A quiet pale warm-cream background with just two tiny apricot sparkle shapes. Ivory, marmalade-orange and charcoal-black with amber eyes, minimal accessories.

Both cheeks are visibly puffed round. Her tiny mouth is firmly closed in a small stubborn sideways pout. Brows angle slightly down at the middle and her eyes look toward the viewer with mildly annoyed determination. Cute sulking expression, no smile.

A cute anime catgirl avatar in a square close-up portrait, rounded delicate face and large luminous eyes, natural pale facial skin and subtle rosy cheeks. Her whole fluffy head and both cat ears fit inside the frame with a very small margin above. Her large face occupies most of the picture. Only her neck and the tops of her shoulders appear at the bottom. Slight three-quarter turn and a gentle head tilt. Fine clean anime linework, carefully shaped soft fluffy hair locks, soft cel coloring with restrained shadows and broad calm colors. Minimal accessories, excellent readability at tiny avatar size, polished and expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, animal face, animal muzzle, furry face, fur on facial skin, face paint, literal cat, bird, feather ornament, fox ears, bunny ears, maid, maid headdress, headband, monochrome hair, single hair color, uniform orange hair, uniform black hair, solid white hair, symmetrical hair color, striped hair, green hair, pink hair, blue hair, blue eyes, smile, smiling, :3, open mouth, laughing, crying, tears''',
            },
        },
        'image': 'images/calico/04_pout.png',
        'final_node': '16',
    },
    'fairywren/02_blue_catgirl': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, short hair, bob cut, fluffy hair, bangs, black hair, (blue hair:1.3), two-tone hair, blue eyes, feather hair ornament, white blouse, black collar, blue ribbon, portrait, close-up, headshot, head tilt, looking at viewer, smile, closed mouth, blush, light blue background, simple background, pastel colors, delicate lineart, soft shading.

A cute anime girl avatar in a square close-up portrait. A rounded delicate face, large sparkling blue eyes, natural pale skin, subtle rosy cheeks and a tiny gentle closed-mouth smile. Her fluffy chin-length bob has a vivid sky-blue crown and bright azure-blue locks framing both cheeks, contrasting with a deep blue-black underlayer and dark navy hair at the back. The head and cheek hair is blue; only the underside and back are dark. Thin dark upper lash lines echo a small blue bird's black eye stripe, while the facial skin remains natural. Two small fluffy cat ears have dark navy-blue fur outside and soft light-blue fur within. One tiny blue feather hair clip sits beside the ear. Both complete cat ears fit inside the image with a narrow margin above. She wears a simple ivory-white blouse with a narrow black collar band and one small azure-blue bow. The neck and only the tops of shoulders are visible along the bottom. Her large face occupies most of the frame, with the whole head visible. A slight three-quarter turn and a gentle head tilt.

Fine clean anime linework, delicately shaped fluffy hair locks, soft flat cel coloring with restrained shading, the same adorable rounded face proportions across the series. Vivid blue accents balanced with deep navy and ivory. A quiet pale powder-blue background with just two or three tiny flat drifting feather silhouettes. Very few accessories, excellent readability as a profile icon. Fully dressed. The small blue bird is a color and shape inspiration, not an animal drawn in the picture.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, head out of frame, large jewelry, elaborate accessories, maid, maid headdress, pink hair, brown hair, blonde hair, pink background, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, bird, bird beak, animal face, black facial skin, feathered body, wings, fox ears, bunny ears, extra ears''',
            },
        },
        'image': 'images/fairywren/02_blue_catgirl.png',
        'final_node': '16',
    },
    'green-cat/anima/01_closed_smile': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, streaked hair, green inner hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, white blouse, frilled collar, green ribbon, leaf hair ornament, mint green background, simple background, floating leaves, pastel colors, delicate lineart, soft shading, closed eyes, :3, gentle smile, blush.

A cute anime catgirl avatar in a square close-up portrait. She has a fluffy white bob, two narrow emerald-green streaks framing her face and a light mint-green underlayer. Her hair is predominantly white. Two furry white cat ears with pale pink interiors, one tiny green leaf hair clip, and a small green ribbon on the high frilled collar of a white blouse. Her face fills most of the picture, with only the neck and the tops of her shoulders at the lower edge. Her complete head and both cat ears fit inside the frame with a small margin above them. A slight three-quarter turn and gentle head tilt, soft round cheeks and delicate facial features. Both eyes are completely closed, shown as soft curved eyelash lines. Her tiny mouth forms a relaxed catlike smile.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring and luminous white hair highlights. A fresh green and ivory palette. Simple pale mint-green background with a few small drifting leaf shapes, ample quiet space around the face, minimal accessories. Polished, cute and expressive.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, normal quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, hat, large jewelry, elaborate accessories, blonde hair, pink hair, blue hair, cyan hair, pink background, red background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, red outlines, neon outlines, thick outlines, rough sketch, busy background, open eyes, half-closed eyes, visible pupils''',
            },
        },
        'image': 'images/green-cat/anima/01_closed_smile.png',
        'final_node': '16',
    },
    'green-cat/anima/02_open_smile': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, streaked hair, green inner hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, white blouse, frilled collar, green ribbon, leaf hair ornament, mint green background, simple background, floating leaves, pastel colors, delicate lineart, soft shading, green eyes, looking at viewer, smile, closed mouth, blush.

A cute anime catgirl avatar in a square close-up portrait. She has a fluffy white bob, two narrow emerald-green streaks framing her face and a light mint-green underlayer. Her hair is predominantly white. Two furry white cat ears with pale pink interiors, one tiny green leaf hair clip, and a small green ribbon on the high frilled collar of a white blouse. Her face fills most of the picture, with only the neck and the tops of her shoulders at the lower edge. Her complete head and both cat ears fit inside the frame with a small margin above them. A slight three-quarter turn and gentle head tilt, soft round cheeks and delicate facial features. Her large round emerald-green eyes look at the viewer, with clear sparkling highlights. She gives a small gentle closed-mouth smile.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring and luminous white hair highlights. A fresh green and ivory palette. Simple pale mint-green background with a few small drifting leaf shapes, ample quiet space around the face, minimal accessories. Polished, cute and expressive.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, normal quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, hat, large jewelry, elaborate accessories, blonde hair, pink hair, blue hair, cyan hair, pink background, red background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, red outlines, neon outlines, thick outlines, rough sketch, busy background''',
            },
        },
        'image': 'images/green-cat/anima/02_open_smile.png',
        'final_node': '16',
    },
    'green-cat/anima/03_wink': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, streaked hair, green inner hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, white blouse, frilled collar, green ribbon, leaf hair ornament, mint green background, simple background, floating leaves, pastel colors, delicate lineart, soft shading, green eyes, one eye closed, looking at viewer, :3, playful, blush.

A cute anime catgirl avatar in a square close-up portrait. She has a fluffy white bob, two narrow emerald-green streaks framing her face and a light mint-green underlayer. Her hair is predominantly white. Two furry white cat ears with pale pink interiors, one tiny green leaf hair clip, and a small green ribbon on the high frilled collar of a white blouse. Her face fills most of the picture, with only the neck and the tops of her shoulders at the lower edge. Her complete head and both cat ears fit inside the frame with a small margin above them. A slight three-quarter turn and gentle head tilt, soft round cheeks and delicate facial features. She playfully winks with one eye fully closed and the other emerald-green eye wide open, looking at the viewer. Her mouth makes a tiny catlike smile.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring and luminous white hair highlights. A fresh green and ivory palette. Simple pale mint-green background with a few small drifting leaf shapes, ample quiet space around the face, minimal accessories. Polished, cute and expressive.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, normal quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, hat, large jewelry, elaborate accessories, blonde hair, pink hair, blue hair, cyan hair, pink background, red background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, red outlines, neon outlines, thick outlines, rough sketch, busy background''',
            },
        },
        'image': 'images/green-cat/anima/03_wink.png',
        'final_node': '16',
    },
    'green-cat/anima/04_pout': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, streaked hair, green inner hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, white blouse, frilled collar, green ribbon, leaf hair ornament, mint green background, simple background, floating leaves, pastel colors, delicate lineart, soft shading, green eyes, looking at viewer, pout, puffed cheeks, closed mouth, blush.

A cute anime catgirl avatar in a square close-up portrait. She has a fluffy white bob, two narrow emerald-green streaks framing her face and a light mint-green underlayer. Her hair is predominantly white. Two furry white cat ears with pale pink interiors, one tiny green leaf hair clip, and a small green ribbon on the high frilled collar of a white blouse. Her face fills most of the picture, with only the neck and the tops of her shoulders at the lower edge. Her complete head and both cat ears fit inside the frame with a small margin above them. A slight three-quarter turn and gentle head tilt, soft round cheeks and delicate facial features. Her emerald-green eyes look at the viewer while she puffs up her round cheeks and puckers her tiny closed mouth in an adorably sulky pout.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring and luminous white hair highlights. A fresh green and ivory palette. Simple pale mint-green background with a few small drifting leaf shapes, ample quiet space around the face, minimal accessories. Polished, cute and expressive.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, normal quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, hat, large jewelry, elaborate accessories, blonde hair, pink hair, blue hair, cyan hair, pink background, red background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, red outlines, neon outlines, thick outlines, rough sketch, busy background''',
            },
        },
        'image': 'images/green-cat/anima/04_pout.png',
        'final_node': '16',
    },
    'lingyin/01_closed_smile': {
        'changes': {
        },
        'image': 'images/lingyin/01_closed_smile.png',
        'final_node': '16',
    },
    'lingyin/02_open_smile': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, pink eyes, looking at viewer, smile, closed mouth, blush.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. Her large rose-pink eyes look at the viewer, with bright little sparkling highlights, and she has a gentle closed-mouth smile.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline''',
            },
        },
        'image': 'images/lingyin/02_open_smile.png',
        'final_node': '16',
    },
    'lingyin/03_wink': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, pink eyes, one eye closed, looking at viewer, :3, blush.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. She playfully winks, one eye fully closed and the other rose-pink eye open. Her mouth makes a tiny catlike smile.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline''',
            },
        },
        'image': 'images/lingyin/03_wink.png',
        'final_node': '16',
    },
    'lingyin/04_pout': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, pink eyes, looking at viewer, (pout:2), (puffed cheeks:1.8), frown, closed mouth, blush.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. Her eyebrows angle upward at their inner ends in a slightly sulky expression. Both cheeks are visibly puffed out with air. Her tiny lips protrude forward in an obvious small puckered pout.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, smile, smiling, :3, open mouth''',
            },
        },
        'image': 'images/lingyin/04_pout.png',
        'final_node': '16',
    },
    'lingyin/05_happy': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, closed eyes, (happy:1.8), (laughing:1.8), (smile:1.8), (open mouth:1.3), blush.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. Both eyes are completely closed in cheerful smiling arcs. Her mouth is wide open in a clear broad U-shaped joyful smile with both mouth corners lifted high, a little upper teeth visible. She is laughing happily.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, surprised, round mouth, o_o, open eyes, visible pupils''',
            },
        },
        'image': 'images/lingyin/05_happy.png',
        'final_node': '16',
    },
    'lingyin/06_surprised': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, (surprised:1.8), (wide-eyed:1.6), pink eyes, raised eyebrows, (open mouth:1.8).

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. Her rose-pink eyes are wide open in surprise, eyebrows raised. Her tiny open mouth forms a clear round O shape. A startled but adorable expression.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, smile, smiling, :3, frown''',
            },
        },
        'image': 'images/lingyin/06_surprised.png',
        'final_node': '16',
    },
    'lingyin/07_shy': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, pink eyes, (embarrassed:1.8), (blush:1.7), looking away, closed mouth.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. She looks slightly downward and to one side, avoiding eye contact with a shy embarrassed expression. Both cheeks are visibly rosy. A tiny hesitant closed mouth and gently raised inner eyebrows.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, looking at viewer, bold smile, open mouth''',
            },
        },
        'image': 'images/lingyin/07_shy.png',
        'final_node': '16',
    },
    'lingyin/08_sleepy': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, (sleepy:1.8), (half-closed eyes:1.7), pink eyes, (yawning:1.8), open mouth.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. Her eyelids droop heavily, leaving her rose-pink eyes half closed. She is caught in a small sleepy yawn, mouth open vertically with relaxed eyebrows. Drowsy and adorable. No hands appear.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, wide-eyed, surprised, smile, smiling, hands''',
            },
        },
        'image': 'images/lingyin/08_sleepy.png',
        'final_node': '16',
    },
    'lingyin/09_smug': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, (smug:1.8), pink eyes, half-closed eyes, smirk, raised eyebrow, closed mouth, looking at viewer, blush.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. She looks at the viewer with half-lidded pink eyes, one eyebrow raised. One corner of her tiny closed mouth lifts into a mischievous confident smirk. A playful self-satisfied expression.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, crying, tears, sad, open mouth''',
            },
        },
        'image': 'images/lingyin/09_smug.png',
        'final_node': '16',
    },
    'lingyin/10_angry': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, (angry:1.7), (furrowed eyebrows:1.7), pink eyes, (pout:1.7), closed mouth, blush.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. Her eyebrows angle sharply down toward the middle in a little angry V, and her pink eyes narrow slightly. She has a tiny firmly closed pouting mouth and flushed cheeks. An adorable mildly annoyed face.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, smile, smiling, :3, tears, crying''',
            },
        },
        'image': 'images/lingyin/10_angry.png',
        'final_node': '16',
    },
    'lingyin/11_teary': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, (teary eyes:1.8), pink eyes, (sad:1.6), (crying:1.4), closed mouth, blush.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. Her large pink eyes glisten with clearly visible tears pooled on the lower eyelids, and one tiny tear runs down a cheek. Her inner eyebrows lift in sadness. Her small closed mouth bends gently downward. A tender, cute, tearful expression.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, smile, smiling, :3, happy, laughing, open mouth''',
            },
        },
        'image': 'images/lingyin/11_teary.png',
        'final_node': '16',
    },
    'lingyin/12_neutral': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, maid, maid headdress, black dress, white collar, frills, pink ribbon, light pink background, simple background, floating petals, pastel colors, delicate lineart, soft shading, pink eyes, looking at viewer, (expressionless:1.7), closed mouth.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy chocolate-brown bobbed hair and two furry brown cat ears with pale pink interiors. A small white frilled maid headband sits between the ears, with one small pastel pink bow. She wears a classic black-and-white maid dress: a high white frilled collar, a little rose-pink ribbon at her throat, and white shoulder frills. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and a gentle head tilt, rounded cheeks and delicate facial features. She stares softly toward the viewer with a blank absent-minded expression. Both eyes are normally open, eyebrows relaxed. Her tiny closed mouth is a short neutral line, with no smile. Calm, slightly dazed, and cute.

Fine clean anime linework, carefully drawn hair locks, soft cel coloring, subtly luminous brown hair highlights. Dusty rose, blush pink, chocolate brown, black and ivory palette. A quiet pale pink background with a few tiny drifting cherry-blossom petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, smile, smiling, :3, open mouth, tears, crying, angry, heavy blush''',
            },
        },
        'image': 'images/lingyin/12_neutral.png',
        'final_node': '16',
    },
    'ragdoll/01_smile': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, two-tone hair, brown sidelocks, brown cat ears, fluffy hair, bob cut, bangs, blue eyes, maid, maid headdress, black dress, white collar, white frills, black ribbon, portrait, close-up, headshot, cute, light grey background, simple background, pastel colors, delicate lineart, soft shading, looking at viewer, smile, closed mouth, blush.

A sweet ragdoll-cat-inspired girl with a fluffy chin-length bob. Her hair crown and wide central forelock are creamy ivory-white, forming a soft white inverted-V wedge; the two outer locks framing the sides of her face and the underlayer at the back are deep cocoa-brown. Her two plush cat ears have chocolate-brown fur outside and soft ivory inner fluff. Her facial skin is normal pale human skin. Large clear sapphire-blue eyes with delicate sparkling highlights. A small white frilled maid headband sits neatly between the cat ears, with one tiny black bow. She wears a classic black-and-white maid dress: an opaque high white frilled collar, one small black ribbon at the throat, black fabric and narrow white shoulder frills. A quiet pale pearl-grey background with two tiny light-blue sparkle dots. Ivory, cocoa-brown, black and white palette with bright blue eyes as the main color accent.

Her eyes are normally open and look gently toward the viewer. A tiny warm closed-mouth smile and softly rosy cheeks. Calm and affectionate.

A cute anime catgirl avatar in a square close-up portrait, rounded delicate face and large luminous eyes, natural pale facial skin and subtle rosy cheeks. Her whole fluffy head and both cat ears fit inside the frame with a very small margin above. Her large face occupies most of the picture. Only her neck and the tops of her shoulders appear at the bottom. Slight three-quarter turn and a gentle head tilt. Fine clean anime linework, carefully shaped soft fluffy hair locks, soft cel coloring with restrained shadows and broad calm colors. Minimal accessories, excellent readability at tiny avatar size, polished and expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, animal face, animal muzzle, furry face, fur on facial skin, face paint, literal cat, bird, feather ornament, fox ears, bunny ears, orange hair, orange ears, green hair, pink hair, calico, amber eyes, yellow eyes, brown eyes, colored maid dress, dark facial skin, black face, angry, frown, crying, tears, open mouth''',
            },
        },
        'image': 'images/ragdoll/01_smile.png',
        'final_node': '16',
    },
    'ragdoll/02_wink': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, two-tone hair, brown sidelocks, brown cat ears, fluffy hair, bob cut, bangs, blue eyes, maid, maid headdress, black dress, white collar, white frills, black ribbon, portrait, close-up, headshot, cute, light grey background, simple background, pastel colors, delicate lineart, soft shading, (wink:1.7), one eye closed, one eye open, looking at viewer, smile, open mouth, blush.

A sweet ragdoll-cat-inspired girl with a fluffy chin-length bob. Her hair crown and wide central forelock are creamy ivory-white, forming a soft white inverted-V wedge; the two outer locks framing the sides of her face and the underlayer at the back are deep cocoa-brown. Her two plush cat ears have chocolate-brown fur outside and soft ivory inner fluff. Her facial skin is normal pale human skin. Large clear sapphire-blue eyes with delicate sparkling highlights. A small white frilled maid headband sits neatly between the cat ears, with one tiny black bow. She wears a classic black-and-white maid dress: an opaque high white frilled collar, one small black ribbon at the throat, black fabric and narrow white shoulder frills. A quiet pale pearl-grey background with two tiny light-blue sparkle dots. Ivory, cocoa-brown, black and white palette with bright blue eyes as the main color accent.

One eye is completely closed in a clear playful wink; the other eye remains wide open and sparkling toward the viewer. A cheerful small open-mouth grin with a tiny upper tooth visible, rosy cheeks. Mischievous and adorable.

A cute anime catgirl avatar in a square close-up portrait, rounded delicate face and large luminous eyes, natural pale facial skin and subtle rosy cheeks. Her whole fluffy head and both cat ears fit inside the frame with a very small margin above. Her large face occupies most of the picture. Only her neck and the tops of her shoulders appear at the bottom. Slight three-quarter turn and a gentle head tilt. Fine clean anime linework, carefully shaped soft fluffy hair locks, soft cel coloring with restrained shadows and broad calm colors. Minimal accessories, excellent readability at tiny avatar size, polished and expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, animal face, animal muzzle, furry face, fur on facial skin, face paint, literal cat, bird, feather ornament, fox ears, bunny ears, orange hair, orange ears, green hair, pink hair, calico, amber eyes, yellow eyes, brown eyes, colored maid dress, dark facial skin, black face, both eyes closed, two closed eyes, sleepy, frown, crying''',
            },
        },
        'image': 'images/ragdoll/02_wink.png',
        'final_node': '16',
    },
    'ragdoll/03_shy': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, two-tone hair, brown sidelocks, brown cat ears, fluffy hair, bob cut, bangs, blue eyes, maid, maid headdress, black dress, white collar, white frills, black ribbon, portrait, close-up, headshot, cute, light grey background, simple background, pastel colors, delicate lineart, soft shading, (embarrassed:1.8), (blush:1.7), looking away, closed mouth.

A sweet ragdoll-cat-inspired girl with a fluffy chin-length bob. Her hair crown and wide central forelock are creamy ivory-white, forming a soft white inverted-V wedge; the two outer locks framing the sides of her face and the underlayer at the back are deep cocoa-brown. Her two plush cat ears have chocolate-brown fur outside and soft ivory inner fluff. Her facial skin is normal pale human skin. Large clear sapphire-blue eyes with delicate sparkling highlights. A small white frilled maid headband sits neatly between the cat ears, with one tiny black bow. She wears a classic black-and-white maid dress: an opaque high white frilled collar, one small black ribbon at the throat, black fabric and narrow white shoulder frills. A quiet pale pearl-grey background with two tiny light-blue sparkle dots. Ivory, cocoa-brown, black and white palette with bright blue eyes as the main color accent.

She looks slightly downward and to one side, avoiding eye contact shyly. Both cheeks are visibly rosy with soft blush strokes. A tiny hesitant closed mouth and gently raised inner eyebrows. Sweet and embarrassed.

A cute anime catgirl avatar in a square close-up portrait, rounded delicate face and large luminous eyes, natural pale facial skin and subtle rosy cheeks. Her whole fluffy head and both cat ears fit inside the frame with a very small margin above. Her large face occupies most of the picture. Only her neck and the tops of her shoulders appear at the bottom. Slight three-quarter turn and a gentle head tilt. Fine clean anime linework, carefully shaped soft fluffy hair locks, soft cel coloring with restrained shadows and broad calm colors. Minimal accessories, excellent readability at tiny avatar size, polished and expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, animal face, animal muzzle, furry face, fur on facial skin, face paint, literal cat, bird, feather ornament, fox ears, bunny ears, orange hair, orange ears, green hair, pink hair, calico, amber eyes, yellow eyes, brown eyes, colored maid dress, dark facial skin, black face, looking at viewer, bold smile, open mouth, laughing''',
            },
        },
        'image': 'images/ragdoll/03_shy.png',
        'final_node': '16',
    },
    'ragdoll/04_pout': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, white hair, two-tone hair, brown sidelocks, brown cat ears, fluffy hair, bob cut, bangs, blue eyes, maid, maid headdress, black dress, white collar, white frills, black ribbon, portrait, close-up, headshot, cute, light grey background, simple background, pastel colors, delicate lineart, soft shading, (pout:2.0), (puffed cheeks:1.8), (frown:1.4), looking at viewer, closed mouth, blush.

A sweet ragdoll-cat-inspired girl with a fluffy chin-length bob. Her hair crown and wide central forelock are creamy ivory-white, forming a soft white inverted-V wedge; the two outer locks framing the sides of her face and the underlayer at the back are deep cocoa-brown. Her two plush cat ears have chocolate-brown fur outside and soft ivory inner fluff. Her facial skin is normal pale human skin. Large clear sapphire-blue eyes with delicate sparkling highlights. A small white frilled maid headband sits neatly between the cat ears, with one tiny black bow. She wears a classic black-and-white maid dress: an opaque high white frilled collar, one small black ribbon at the throat, black fabric and narrow white shoulder frills. A quiet pale pearl-grey background with two tiny light-blue sparkle dots. Ivory, cocoa-brown, black and white palette with bright blue eyes as the main color accent.

Both cheeks are visibly puffed round. Her tiny mouth is firmly closed in a small stubborn sideways pout. Brows angle slightly down at the middle and her eyes look toward the viewer with mildly annoyed determination. Cute sulking expression, no smile.

A cute anime catgirl avatar in a square close-up portrait, rounded delicate face and large luminous eyes, natural pale facial skin and subtle rosy cheeks. Her whole fluffy head and both cat ears fit inside the frame with a very small margin above. Her large face occupies most of the picture. Only her neck and the tops of her shoulders appear at the bottom. Slight three-quarter turn and a gentle head tilt. Fine clean anime linework, carefully shaped soft fluffy hair locks, soft cel coloring with restrained shadows and broad calm colors. Minimal accessories, excellent readability at tiny avatar size, polished and expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, animal face, animal muzzle, furry face, fur on facial skin, face paint, literal cat, bird, feather ornament, fox ears, bunny ears, orange hair, orange ears, green hair, pink hair, calico, amber eyes, yellow eyes, brown eyes, colored maid dress, dark facial skin, black face, smile, smiling, :3, open mouth, laughing, crying, tears''',
            },
        },
        'image': 'images/ragdoll/04_pout.png',
        'final_node': '16',
    },
    'random-cat-avatars/01_mint': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, honey blonde hair, side braid, long hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, turtleneck, sweater, warm rose-pink eyes, happy, open mouth, smile, blush, simple background, pastel colors, delicate lineart, soft shading.

A cute anime catgirl avatar in a square close-up portrait. She has long softly waved hair gathered into a loose side braid beside her cheek, with curved bangs and soft sidelocks, in honey blonde. Two furry cat ears match her hair color and have pale pink interiors. She wears a cozy sage green knitted turtleneck sweater with soft subtle fabric folds. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and gentle head tilt, rounded cheeks and delicate facial features. Her iris color is warm rose-pink. Both sparkling eyes are open, looking at the viewer, with a bright small open-mouth smile, a single tiny fang and rosy cheeks.

Fine clean anime linework, carefully drawn fluffy hair locks, soft cel coloring, subtly luminous hair highlights. A gentle mint green, sage and ivory theme with harmoniously subdued hair colors. A quiet pale mint-green background with a few tiny drifting leaf shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, hat, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, hood up''',
            },
            '7': {
                'seed': 1964743067,
            },
            '14': {
                'seed': 1964743067,
            },
        },
        'image': 'images/random-cat-avatars/01_mint.png',
        'final_node': '16',
        'design': {'theme': '薄荷绿', 'hairstyle': '侧编辫', 'hair_color': '蜜金', 'eyes': '玫瑰粉', 'expression': '开心', 'outfit': '针织高领'},
    },
    'random-cat-avatars/02_butter-yellow': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, creamy white hair, side ponytail, long hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, pinafore dress, white blouse, clear teal-green eyes, half-closed eyes, sleepy, closed mouth, blush, simple background, pastel colors, delicate lineart, soft shading.

A cute anime catgirl avatar in a square close-up portrait. She has a fluffy side ponytail tied with one tiny ribbon, with curved bangs and soft curled sidelocks, in creamy white. Two furry cat ears match her hair color and have pale pink interiors. She wears a butter yellow pinafore dress over an ivory blouse with a small round collar. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and gentle head tilt, rounded cheeks and delicate facial features. Her iris color is clear teal-green. Her eyelids are gently half lowered, with both colored irises still visible; a tiny relaxed closed-mouth smile gives her an adorably sleepy look.

Fine clean anime linework, carefully drawn fluffy hair locks, soft cel coloring, subtly luminous hair highlights. A gentle butter yellow, warm honey and ivory theme with harmoniously subdued hair colors. A quiet pale butter-yellow background with a few tiny star-shaped sparkles. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, hat, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, hood up''',
            },
            '7': {
                'seed': 3801040457,
            },
            '14': {
                'seed': 3801040457,
            },
        },
        'image': 'images/random-cat-avatars/02_butter-yellow.png',
        'final_node': '16',
        'design': {'theme': '奶油黄', 'hairstyle': '侧马尾', 'hair_color': '奶白', 'eyes': '青绿', 'expression': '困困', 'outfit': '背带裙'},
    },
    'random-cat-avatars/03_lavender': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, soft silver-gray hair, bob cut, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, cardigan, white shirt, warm amber-gold eyes, shy, smile, closed mouth, blush, simple background, pastel colors, delicate lineart, soft shading.

A cute anime catgirl avatar in a square close-up portrait. She has a fluffy softly rounded short bob, with curved bangs and curled sidelocks, in soft silver-gray. Two furry cat ears match her hair color and have pale pink interiors. She wears a soft dusty lavender cardigan over an ivory high-neck shirt, with one tiny bow at the neckline. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and gentle head tilt, rounded cheeks and delicate facial features. Her iris color is warm amber-gold. Both sparkling eyes are open, glancing slightly toward the viewer, with a tiny shy closed-mouth smile and warm rosy blush.

Fine clean anime linework, carefully drawn fluffy hair locks, soft cel coloring, subtly luminous hair highlights. A gentle dusty lavender, lilac and ivory theme with harmoniously subdued hair colors. A quiet pale lilac background with a few tiny lavender petals. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, hat, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, hood up''',
            },
            '7': {
                'seed': 49838739,
            },
            '14': {
                'seed': 49838739,
            },
        },
        'image': 'images/random-cat-avatars/03_lavender.png',
        'final_node': '16',
        'design': {'theme': '薰衣草紫', 'hairstyle': '柔软短波波头', 'hair_color': '银灰', 'eyes': '琥珀金', 'expression': '害羞', 'outfit': '开衫'},
    },
    'random-cat-avatars/04_peach': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, chestnut brown hair, double bun, hair bun, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, hoodie, hood down, clear lake-blue eyes, pout, puffed cheeks, closed mouth, blush, simple background, pastel colors, delicate lineart, soft shading.

A cute anime catgirl avatar in a square close-up portrait. She has two small fluffy hair buns, one on each side, with curved bangs and long curled face-framing sidelocks, in chestnut brown. Two furry cat ears match her hair color and have pale pink interiors. She wears a soft soft apricot hoodie with its hood down and ivory drawstrings. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and gentle head tilt, rounded cheeks and delicate facial features. Her iris color is clear lake-blue. Both eyes are open looking at the viewer, with gently puffed cheeks and a tiny closed-mouth pout; cute and mildly sulky.

Fine clean anime linework, carefully drawn fluffy hair locks, soft cel coloring, subtly luminous hair highlights. A gentle soft peach, apricot and ivory theme with harmoniously subdued hair colors. A quiet pale peach background with a few tiny apricot petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, hat, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, hood up''',
            },
            '7': {
                'seed': 2311903254,
            },
            '14': {
                'seed': 2311903254,
            },
        },
        'image': 'images/random-cat-avatars/04_peach.png',
        'final_node': '16',
        'design': {'theme': '蜜桃橙', 'hairstyle': '双丸子头', 'hair_color': '栗棕', 'eyes': '湖蓝', 'expression': '鼓脸', 'outfit': '卫衣'},
    },
    'random-cat-avatars/05_sky-blue': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, muted ash-lavender hair, medium hair, wavy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, sailor collar, sailor uniform, soft violet eyes, one eye closed, wink, :3, blush, simple background, pastel colors, delicate lineart, soft shading.

A cute anime catgirl avatar in a square close-up portrait. She has soft shoulder-length wavy hair with gently curled ends, curved bangs and airy sidelocks, in muted ash-lavender. Two furry cat ears match her hair color and have pale pink interiors. She wears a fully closed ivory sailor blouse with a powder blue sailor collar and one tiny matching ribbon. Only her neck and the tops of her shoulders appear at the lower edge. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Slight three-quarter turn and gentle head tilt, rounded cheeks and delicate facial features. Her iris color is soft violet. She playfully winks with one eye completely closed and the other eye open, looking at the viewer; a tiny catlike smile and soft blush.

Fine clean anime linework, carefully drawn fluffy hair locks, soft cel coloring, subtly luminous hair highlights. A gentle powder blue, soft navy and ivory theme with harmoniously subdued hair colors. A quiet pale powder-blue background with a few tiny airy sparkle shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, hat, large jewelry, elaborate accessories, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, hood up''',
            },
            '7': {
                'seed': 2498879535,
            },
            '14': {
                'seed': 2498879535,
            },
        },
        'image': 'images/random-cat-avatars/05_sky-blue.png',
        'final_node': '16',
        'design': {'theme': '天空蓝', 'hairstyle': '中长卷发', 'hair_color': '灰紫', 'eyes': '紫罗兰', 'expression': '眨眼', 'outfit': '水手领'},
    },
    'red-hoodie/01_smile': {
        'changes': {
            '4': {
                'text': r'''masterpiece, best quality, score_7, highres, safe, @blade \(galaxist\), 1girl, solo, cat girl, cat ears, brown hair, long hair, twintails, fluffy hair, bangs, sidelocks, portrait, close-up, headshot, head tilt, cute, red hoodie, hood down, red hair ribbons, red eyes, looking at viewer, smile, closed mouth, blush, light red background, simple background, floating petals, pastel colors, delicate lineart, soft shading.

A cute anime catgirl avatar in a square close-up portrait. She has fluffy warm chestnut-brown hair tied into two long, clearly separated ponytails, one on each side of her head, with two small dark red ribbon ties. Curved bangs and soft curled sidelocks frame her rounded cheeks. Two furry brown cat ears with warm pale pink interiors sit naturally on top of her head. She wears a cozy oversized muted crimson-red pullover hoodie with its hood resting down behind her neck, an ivory drawstring and soft fabric folds. Her upper shoulders and hoodie neckline are visible at the bottom of the image. Her large face occupies most of the picture; the entire head and both cat ears fit inside the frame with a very small margin above. Both ponytail roots and the upper sections of both ponytails are clearly visible beside her face. Slight three-quarter turn and a gentle head tilt. Large warm garnet-red eyes look at the viewer, with bright little sparkling highlights, a gentle closed-mouth smile and soft rosy blush.

Fine clean anime linework, carefully drawn fluffy hair locks, soft cel coloring, subtly luminous brown hair highlights. A soft red-themed palette of dusty coral, muted crimson, warm chestnut brown and creamy ivory. A quiet pale coral-pink background with a few tiny drifting red petal shapes. Minimal accessories. Polished, cute, expressive, fully dressed.''',
            },
            '5': {
                'text': r'''score_1, score_2, score_3, artist name, worst quality, low quality, lowres, blurry, jpeg artifacts, chromatic aberration, bad anatomy, deformed face, extra eyes, extra ears, multiple girls, duplicate, hands, text, watermark, signature, logo, full body, distant view, tiny face, cropped head, cropped ears, head out of frame, large jewelry, elaborate accessories, white hair, blonde hair, pink hair, green hair, blue background, green background, photorealistic, realistic skin, 3d, render, harsh lighting, oversaturated, thick outlines, rough sketch, busy background, cleavage, low neckline, maid, maid headdress, maid apron, frills, bob cut, short hair, single ponytail, hood up''',
            },
        },
        'image': 'images/red-hoodie/01_smile.png',
        'final_node': '16',
    },
}

# Widget order for ComfyUI's UI JSON, including the sampler seed control.
WIDGETS = {
    'UNETLoader': ('unet_name', 'weight_dtype'),
    'CLIPLoader': ('clip_name', 'type', 'device'),
    'VAELoader': ('vae_name',),
    'CLIPTextEncode': ('text',),
    'EmptyLatentImage': ('width', 'height', 'batch_size'),
    'KSampler': ('seed', None, 'steps', 'cfg', 'sampler_name', 'scheduler', 'denoise'),
    'VAEDecodeTiled': ('tile_size', 'overlap', 'temporal_size', 'temporal_overlap'),
    'UpscaleModelLoader': ('model_name',),
    'ImageUpscaleWithModel': (),
    'ImageScale': ('upscale_method', 'width', 'height', 'crop'),
    'VAEEncodeTiled': ('tile_size', 'overlap', 'temporal_size', 'temporal_overlap'),
    'SaveImage': ('filename_prefix',),
}
MODEL_KEYS = {'unet_name', 'clip_name', 'vae_name', 'model_name'}


def is_link(value, graph):
    return (isinstance(value, list) and len(value) == 2 and
            isinstance(value[0], str) and value[0] in graph and isinstance(value[1], int))


def parse_models(items):
    result = {}
    for item in items:
        key, sep, value = item.partition('=')
        if not sep or key not in MODEL_KEYS or not value:
            raise ValueError('--model expects KEY=FILENAME; KEY is one of ' + ', '.join(sorted(MODEL_KEYS)))
        result[key] = value
    return result


def to_ui(graph, variant_id):
    ui = json.loads((ROOT / 'workflows/anima-avatar-hd.workflow.json').read_text())
    for node in ui['nodes']:
        key = str(node['id'])
        if key in graph:
            values = graph[key]['inputs']
            node['widgets_values'] = [values[name] if name is not None else 'fixed'
                                      for name in WIDGETS[graph[key]['class_type']]]
        elif node['type'] == 'Note':
            node['widgets_values'] = [
                'CATGIRL AVATARS · ANIMA\nRecipe: ' + variant_id + '\n'
                'Prompts and parameters: generate.py → VARIANTS\n'
                '1024² → NMKD upscale → 1536² → low-denoise refinement\n'
                'No external image input. See README.md and docs/MODELS.md.']
    return ui


def build(variant_id, seed=None, models=None):
    recipe = VARIANTS[variant_id]
    graph = copy.deepcopy(TEMPLATE)
    for key, changes in recipe['changes'].items():
        graph[key]['inputs'].update(copy.deepcopy(changes))
    graph[recipe['final_node']]['inputs']['filename_prefix'] = 'catgirl-avatars/' + variant_id
    for node in graph.values():
        if node['class_type'].startswith('LoadImage'):
            raise ValueError('This project only supports text-to-image workflows.')
        for name in node['inputs']:
            if seed is not None and name == 'seed':
                node['inputs'][name] = seed
            if models and name in models:
                node['inputs'][name] = models[name]
    return graph, to_ui(graph, variant_id)


def connection(url):
    # Local requests must not go through a desktop HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def fetch(route, data=None, binary=False):
        request = urllib.request.Request(
            url.rstrip('/') + route,
            data=None if data is None else json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'})
        try:
            with opener.open(request, timeout=60) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors='replace')
            raise RuntimeError(f'ComfyUI HTTP {error.code}: {detail}') from error
        return raw if binary else json.loads(raw)
    return fetch


def validate_graph(graph, definitions):
    """Resolve known filename aliases, then validate actual server model options."""
    problems = []
    for key, node in graph.items():
        cls = node['class_type']
        if cls not in definitions:
            problems.append(f'node {key}: missing node {cls}')
            continue
        specs = dict(definitions[cls]['input'].get('required', {}))
        specs.update(definitions[cls]['input'].get('optional', {}))
        for name, value in node['inputs'].items():
            if is_link(value, graph):
                continue
            spec = specs.get(name)
            if not spec or not isinstance(spec[0], list) or value in spec[0]:
                continue
            alias = next((a for a in MODEL_ALIASES.get(value, ()) if a in spec[0]), None)
            if name in MODEL_KEYS and alias:
                node['inputs'][name] = alias
            else:
                problems.append(f'node {key}: unsupported {name}={value!r}')
    if problems:
        raise ValueError('\n'.join(problems) + '\nSee docs/MODELS.md; use --model for different filenames.')
    return graph


def checked_graphs(fetch, ids, seed=None, models=None):
    definitions = fetch('/object_info')
    graphs = {}
    for name in ids:
        graph, _ = build(name, seed, models)
        graphs[name] = validate_graph(graph, definitions)
    return graphs


def save_output(fetch, image, wanted):
    query = urllib.parse.urlencode({
        'filename': image['filename'], 'subfolder': image.get('subfolder', ''),
        'type': image.get('type', 'output')})
    raw = fetch('/view?' + query, binary=True)
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('ComfyUI returned non-PNG output; nothing was written.')
    wanted.parent.mkdir(parents=True, exist_ok=True)
    target = wanted
    while True:
        try:
            with target.open('xb') as stream:
                stream.write(raw)
            return target
        except FileExistsError:
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            target = wanted.with_name(wanted.stem + '-' + stamp + '-' + uuid.uuid4().hex[:6] + '.png')


def run(fetch, variant_id, graph, out_dir, timeout):
    output_node = VARIANTS[variant_id]['final_node']
    # A unique server prefix makes simultaneous runs independent.
    graph = copy.deepcopy(graph)
    graph[output_node]['inputs']['filename_prefix'] = 'catgirl-avatars/' + uuid.uuid4().hex + '/' + variant_id
    ui = to_ui(graph, variant_id)
    result = fetch('/prompt', {'prompt': graph, 'client_id': uuid.uuid4().hex,
                              'extra_data': {'extra_pnginfo': {'workflow': ui}}})
    if result.get('node_errors') or 'prompt_id' not in result:
        raise RuntimeError('ComfyUI rejected the workflow: ' + json.dumps(result))
    prompt_id = result['prompt_id']
    print(f'Queued {variant_id}: {prompt_id}', flush=True)
    started, last_report = time.monotonic(), -1
    while True:
        histories = fetch('/history/' + urllib.parse.quote(prompt_id, safe=''))
        if prompt_id in histories:
            history = histories[prompt_id]
            status = history.get('status', {})
            if status.get('status_str') != 'success':
                raise RuntimeError('Generation failed: ' + json.dumps(status, ensure_ascii=False))
            break
        elapsed = int(time.monotonic() - started)
        if elapsed >= timeout:
            raise TimeoutError(f'Timed out waiting for {prompt_id}. The job may still be running in ComfyUI.')
        if elapsed // 30 != last_report:
            print(f'Generating {variant_id}: {elapsed}s', flush=True)
            last_report = elapsed // 30
        time.sleep(2)
    images = history.get('outputs', {}).get(output_node, {}).get('images', [])
    if not images:
        raise RuntimeError('ComfyUI reported success without a final image.')
    paths = []
    for image in images:
        # Download through the API: ComfyUI can run on another machine.
        target = save_output(fetch, image, out_dir / (variant_id + '.png'))
        paths.append(target)
        print('Saved ' + str(target), flush=True)
    return paths


def nonnegative_seed(text):
    value = int(text)
    if not 0 <= value <= 0xffffffffffffffff:
        raise argparse.ArgumentTypeError('seed must be in [0, 2**64 - 1]')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    listing = sub.add_parser('list', help='List named recipes')
    listing.add_argument('--filter', default='')
    showing = sub.add_parser('show', help='Print a recipe as a complete API graph')
    showing.add_argument('variant', choices=sorted(VARIANTS))
    exporting = sub.add_parser('export', help='Export a UI workflow or API graph (offline)')
    exporting.add_argument('variant', choices=sorted(VARIANTS))
    exporting.add_argument('--out', type=Path, required=True)
    exporting.add_argument('--format', choices=('ui', 'api'), default='ui')
    checking = sub.add_parser('check', help='Check ComfyUI models and nodes without generating')
    checking.add_argument('--filter', default='')
    running = sub.add_parser('run', help='Generate one or more recipes via ComfyUI')
    running.add_argument('variants', nargs='+', choices=sorted(VARIANTS))
    running.add_argument('--out-dir', type=Path, default=ROOT / 'outputs')
    running.add_argument('--timeout', type=int, default=1800)
    for command in (showing, exporting, checking, running):
        command.add_argument('--model', action='append', default=[], metavar='KEY=FILENAME')
    for command in (showing, exporting, running):
        command.add_argument('--seed', type=nonnegative_seed)
    for command in (checking, running):
        command.add_argument('--url', default='http://127.0.0.1:8188')
    args = parser.parse_args()
    try:
        models = parse_models(getattr(args, 'model', []))
        if args.action == 'list':
            for name in VARIANTS:
                if args.filter in name:
                    print(name)
        elif args.action == 'show':
            graph, _ = build(args.variant, args.seed, models)
            print(json.dumps(graph, ensure_ascii=False, indent=2))
        elif args.action == 'export':
            graph, ui = build(args.variant, args.seed, models)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('x', encoding='utf-8') as stream:
                json.dump(ui if args.format == 'ui' else graph, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
            print(args.out)
        elif args.action == 'check':
            ids = [name for name in VARIANTS if args.filter in name]
            if not ids:
                raise ValueError('No recipes match the filter.')
            checked_graphs(connection(args.url), ids, models=models)
            print(f'Dependencies ready: {len(ids)} recipes (no images generated).')
        else:
            if args.timeout <= 0:
                raise ValueError('--timeout must be positive.')
            fetch = connection(args.url)
            graphs = checked_graphs(fetch, args.variants, args.seed, models)
            for name in args.variants:
                run(fetch, name, graphs[name], args.out_dir, args.timeout)
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
