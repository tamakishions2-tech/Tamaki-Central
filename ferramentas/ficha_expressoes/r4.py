import numpy as np, cv2, sys
from PIL import Image
from scipy import ndimage
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32); H,W=corpo.shape[:2]
cy,cx=100,185
skin=corpo[cy,cx,:3]; print('pele',skin)
d=np.abs(corpo[...,:3]-skin).sum(2)
cand=(d<60)&(corpo[...,3]>200); cand[175:]=False
lab,_=ndimage.label(cand); face=lab==lab[cy,cx]
face=ndimage.binary_fill_holes(face)
ys,xs=np.where(face); print('rosto px',face.sum(),xs.min(),xs.max(),ys.min(),ys.max())
mask=ndimage.binary_dilation(face,iterations=3).astype(np.float32)
mask=cv2.GaussianBlur(mask,(0,0),1.2)
Image.fromarray((mask*255).astype(np.uint8)).save('mascara.png')
b=Image.new('RGBA',(W,H),(255,0,255,255)); c=Image.open('corpo.png').copy(); b.alpha_composite(c)
v=np.array(b.convert('RGB')); v[mask>0.5]=(v[mask>0.5]*0.5+np.array([0,255,0])*0.5)
Image.fromarray(v.astype(np.uint8)).crop((80,0,300,220)).resize((440,440),Image.NEAREST).save('ver_mascara.png')
