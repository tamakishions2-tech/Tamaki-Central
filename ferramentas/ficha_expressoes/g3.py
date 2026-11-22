import numpy as np, cv2
from PIL import Image
c=np.asarray(Image.open('corpo.png'))[...,3]>128
h=np.asarray(Image.open('h_0_0.png'))[...,3].astype(np.float32)/255
H,W=c.shape; LIM=185
best=(-1,)
for sx in np.arange(0.80,1.0,0.02):
  for sy in np.arange(0.80,1.06,0.02):
    hs=cv2.resize(h,None,fx=sx,fy=sy,interpolation=cv2.INTER_AREA)>0.5
    hh,ww=hs.shape
    for tx in range(50,130,2):
      for ty in range(0,20,1):
        a=np.zeros((LIM,W),bool); y1=min(ty+hh,LIM); x1=min(tx+ww,W); a[ty:y1,tx:x1]=hs[:y1-ty,:x1-tx]
        b=c[:LIM]
        iou=(a&b).sum()/((a|b)[:, :].sum()+1)
        if iou>best[0]: best=(iou,sx,sy,tx,ty)
print(best)
np.save('pos2.npy',np.array(best[1:]))
