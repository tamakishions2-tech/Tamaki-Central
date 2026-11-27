# oculos.py <pasta> <cx1> <cx2> <cy> <r> : óculos redondos firmes iguais em todos os quadros (por baixo da franja)
import sys, glob, os, numpy as np, cv2
from PIL import Image, ImageDraw
d = sys.argv[1]; cx1, cx2, cy, r = map(float, sys.argv[2:6]); S = 6
for f in sorted(glob.glob(f'{d}/*.png')):
    if os.path.basename(f).startswith('_'): continue
    A = Image.open(f).convert('RGBA'); W, H = A.size
    L = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0)); g = ImageDraw.Draw(L)
    cor = (112, 72, 34, 255); lw = int(2.3 * S)
    for cx in (cx1, cx2):
        g.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], outline=cor, width=lw)
        # brilho na lente
        g.arc([(cx - r + 4) * S, (cy - r + 4) * S, (cx + r - 4) * S, (cy + r - 4) * S], 200, 245, fill=(255, 255, 255, 170), width=int(1.6 * S))
    g.arc([(cx1 + r - 2) * S, (cy - 9) * S, (cx2 - r + 2) * S, (cy + 3) * S], 200, 340, fill=cor, width=lw)   # ponte
    L = L.resize((W, H), Image.LANCZOS)
    a = np.asarray(A).astype(np.float32); o = np.asarray(L).astype(np.float32)
    lab = cv2.cvtColor(a[..., :3].astype(np.uint8), cv2.COLOR_RGB2LAB)
    cabelo = (lab[..., 0] < 70) & (np.arange(H)[:, None] < cy - r * .3)   # franja escura por cima dos óculos
    w = o[..., 3:] / 255 * (~cabelo)[..., None] * (a[..., 3:] > 200)
    a[..., :3] = a[..., :3] * (1 - w) + o[..., :3] * w
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(f)
print('ok')
