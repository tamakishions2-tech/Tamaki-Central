import numpy as np, cv2, sys
from PIL import Image
LIM=int(sys.argv[1]); s0,s1=float(sys.argv[2]),float(sys.argv[3]); X0,X1=int(sys.argv[4]),int(sys.argv[5])
c=np.asarray(Image.open('corpo.png'))[...,3]>128
h=np.asarray(Image.open('h_0_0.png'))[...,3].astype(np.float32)/255
H,W=c.shape
def run(sxs,sys_,txs,tys):
    best=(-1,)
    for sx in sxs:
      for sy in sys_:
        hs=cv2.resize(h,None,fx=sx,fy=sy,interpolation=cv2.INTER_AREA)>0.5
        hh,ww=hs.shape
        for tx in txs:
          for ty in tys:
            a=np.zeros((LIM,W),bool); y1=min(ty+hh,LIM); x1=min(tx+ww,W)
            if y1<=ty: continue
            a[ty:y1,tx:x1]=hs[:y1-ty,:x1-tx]
            b=c[:LIM]; iou=(a&b).sum()/((a|b).sum()+1)
            if iou>best[0]: best=(iou,sx,sy,tx,ty)
    return best
b=run(np.arange(s0,s1,0.03),np.arange(s0,s1+0.1,0.03),range(X0,X1,3),range(0,30,3))
print(b)
b=run(np.arange(b[1]-0.03,b[1]+0.031,0.01),np.arange(b[2]-0.03,b[2]+0.031,0.01),range(b[3]-3,b[3]+4),range(max(0,b[4]-3),b[4]+4))
print(b); np.save('pos2.npy',np.array(b[1:]))
