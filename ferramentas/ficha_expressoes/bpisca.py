import numpy as np, cv2, sys
from PIL import Image
# uso: bpisca.py cxE cxD cy ry rx cyS ryS rxS crop
cxE,cxD,cy,ry,rx,cyS,ryS,rxS=[float(v) for v in sys.argv[1:9]]; box=tuple(int(v) for v in sys.argv[9].split(','))
L=lambda f: np.asarray(Image.open(f)).astype(np.float32)
H,W=L('c_0_0.png').shape[:2]; yy,xx=np.mgrid[0:H,0:W]
def olhos(cy,ry,rx):
    m=np.zeros((H,W),np.float32)
    for cx in (cxE,cxD): m=np.maximum(m,(((xx-cx)/rx)**2+((yy-cy)/ry)**2<=1).astype(np.float32))
    return cv2.GaussianBlur(m,(0,0),1.3)[...,None]
for r in range(5):
    f=L(f'c_{r}_2.png'); m=olhos(cyS,ryS,rxS) if r==4 else olhos(cy,ry,rx)
    for c,nome in ((0,'pisca'),(1,'fala_pisca')):
        a=L(f'c_{r}_{c}.png'); out=a.copy(); out[...,:3]=a[...,:3]*(1-m)+f[...,:3]*m
        Image.fromarray(np.clip(out,0,255).astype(np.uint8)).save(f'p_{r}_{nome}.png')
s=Image.new('RGB',(240*5,240*3))
for r in range(5):
  for k,n in enumerate(('c_%d_0','p_%d_pisca','p_%d_fala_pisca')):
    s.paste(Image.open((n%r)+'.png').convert('RGB').crop(box).resize((240,240)),(r*240,k*240))
s.save('ver_pisca.png')
