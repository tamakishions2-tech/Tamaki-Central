import numpy as np, cv2
from PIL import Image
L=lambda f: np.asarray(Image.open(f)).astype(np.float32)
H,W=L('c_0_0.png').shape[:2]
yy,xx=np.mgrid[0:H,0:W]
def olhos(cy,ry,cxs=(202,255),rx=15):
    m=np.zeros((H,W),np.float32)
    for cx in cxs: m=np.maximum(m,(((xx-cx)/rx)**2+((yy-cy)/ry)**2<=1).astype(np.float32))
    return cv2.GaussianBlur(m,(0,0),1.3)[...,None]
for r in range(5):
    f=L(f'c_{r}_2.png')
    m=olhos(108,13,(203,257),16) if r==4 else (olhos(112,11) if r==3 else olhos(118,9))
    for c,nome in ((0,'pisca'),(1,'fala_pisca')):
        a=L(f'c_{r}_{c}.png'); out=a.copy(); out[...,:3]=a[...,:3]*(1-m)+f[...,:3]*m
        Image.fromarray(np.clip(out,0,255).astype(np.uint8)).save(f'p_{r}_{nome}.png')
s=Image.new('RGB',(240*5,240*3))
for r in range(5):
  for k,n in enumerate(('c_%d_0','p_%d_pisca','p_%d_fala_pisca')):
    s.paste(Image.open((n%r)+'.png').convert('RGB').crop((160,70,300,210)).resize((240,240)),(r*240,k*240))
s.save('ver_pisca.png')
