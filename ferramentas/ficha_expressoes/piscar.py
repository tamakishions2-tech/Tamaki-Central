import numpy as np, cv2
from PIL import Image, ImageDraw
L=lambda f: np.asarray(Image.open(f)).astype(np.float32)
H,W=L('c_0_0.png').shape[:2]
yy,xx=np.mgrid[0:H,0:W]
def olhos(ry,cy=97,rx=14):
    m=np.zeros((H,W),np.float32)
    for cx in (161,210): m=np.maximum(m,(((xx-cx)/rx)**2+((yy-cy)/ry)**2<=1).astype(np.float32))
    return cv2.GaussianBlur(m,(0,0),1.4)[...,None]
ry={0:9,1:9,2:9,3:9,4:12}
fechado={r:L('c_0_2.png') for r in range(5)}; fechado[1]=L('c_1_2.png')
for r in range(5):
    m=olhos(ry[r],97,15 if r==4 else 14)
    for c,nome in ((0,'pisca'),(1,'fala_pisca')):
        a=L(f'c_{r}_{c}.png'); out=a.copy(); out[...,:3]=a[...,:3]*(1-m)+fechado[r][...,:3]*m
        Image.fromarray(np.clip(out,0,255).astype(np.uint8)).save(f'p_{r}_{nome}.png')
s=Image.new('RGB',(300*5,300*3))
for r in range(5):
  for k,n in enumerate(('c_%d_0','p_%d_pisca','p_%d_fala_pisca')):
    s.paste(Image.open((n%r)+'.png').convert('RGB').crop((130,60,240,170)).resize((300,300)),(r*300,k*300))
s.save('ver_pisca.png')
