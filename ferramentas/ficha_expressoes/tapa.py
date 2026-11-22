import numpy as np, sys, os, json
from PIL import Image
from scipy import ndimage as nd
pasta,nome=sys.argv[1],sys.argv[2]; pts=json.loads(sys.argv[3])
x=np.array(Image.open(f'{pasta}/{nome}.webp').convert('RGBA')).astype(int); rgb=x[...,:3]
wh=(x[...,3]>60)&(rgb.min(-1)>190)&((rgb.max(-1)-rgb.min(-1))<40)
lab,n=nd.label(wh); M=np.zeros(wh.shape,bool)
for px,py in pts:
    best=None
    for dy in range(-7,8):
        for dx in range(-7,8):
            l=lab[py+dy,px+dx]
            if l and (best is None or dx*dx+dy*dy<best[0]): best=(dx*dx+dy*dy,l)
    if best: M|=lab==best[1]
M|=nd.binary_dilation(M,iterations=2)&(rgb.min(-1)>160)&((rgb.max(-1)-rgb.min(-1))<45)
print(pasta,int(M.sum()))
for f in os.listdir(pasta):
    im=np.array(Image.open(f'{pasta}/{f}').convert('RGBA')); im[...,3][M]=0
    Image.fromarray(im).save(f'{pasta}/{f}','WEBP',quality=92,method=6)
