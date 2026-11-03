from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets'
OUT.mkdir(exist_ok=True)
# Same simple geometry as web/translator.svg, drawn at 4x for smooth ICO edges.
scale = 16
image = Image.new('RGBA', (64 * scale, 64 * scale))
draw = ImageDraw.Draw(image)
def box(coords, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(tuple(v * scale for v in coords), radius * scale, fill, outline, width * scale)
def line(points, fill, width):
    draw.line([(x * scale, y * scale) for x, y in points], fill, width * scale, joint='curve')
green, cream = '#237c60', '#f4f6e9'
box((1, 1, 63, 63), 17, green)
box((9, 10, 38, 43), 7, cream)
line([(16, 20), (31, 20), (31, 32), (16, 32), (16, 20)], green, 3)
line([(23.5, 15), (23.5, 38)], green, 3)
box((30, 24, 55, 54), 6, '#80b99a', green, 2)
line([(36, 47), (42.5, 30), (49, 47)], '#fffef0', 3)
line([(38, 41), (47, 41)], '#fffef0', 3)
for pts in [[(43,13),(52,13),(52,20)],[(49,17),(52,20),(55,17)],[(24,52),(15,52),(15,46)],[(12,49),(15,46),(18,49)]]:
    line(pts, '#d6e8cd', 2)
image = image.resize((256, 256), Image.Resampling.LANCZOS)
image.save(OUT / 'translator.png')
image.save(OUT / 'translator.ico', sizes=[(n,n) for n in (16,24,32,48,64,128,256)])
print('Generated PNG and multi-resolution ICO.')
