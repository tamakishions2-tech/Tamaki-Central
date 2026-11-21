import numpy as np, cv2
from PIL import Image
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32)
def flat(a):  # cinza sobre fundo branco
    al=a[...,3:4]/255; return (a[...,:3]*al+255*(1-al)).mean(2).astype(np.float32)
area=flat(corpo[0:320])
res={}
for r in range(5):
  for c in range(3):
    h=np.asarray(Image.open(f'h_{r}_{c}.png')).astype(np.float32)
    best=(-1,)
    for s in np.arange(0.72,1.10,0.01):
        hs=cv2.resize(h,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
        t=flat(hs)
        if t.shape[0]>area.shape[0] or t.shape[1]>area.shape[1]: continue
        m=cv2.matchTemplate(area,t,cv2.TM_CCOEFF_NORMED); _,v,_,loc=cv2.minMaxLoc(m)
        if v>best[0]: best=(v,round(float(s),2),loc)
    res[(r,c)]=best; print(r,c,best)
np.save('alinha.npy',res,allow_pickle=True)
