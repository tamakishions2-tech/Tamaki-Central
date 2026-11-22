import numpy as np, cv2
from PIL import Image
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32)
def flat(a): al=a[...,3:4]/255; return (a[...,:3]*al+255*(1-al)).mean(2).astype(np.float32)
area=flat(corpo[0:260,100:360])
h=np.asarray(Image.open('h_0_0.png')).astype(np.float32)
best=(-1,)
for s in np.arange(0.50,0.85,0.005):
    hs=cv2.resize(h,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    t=flat(hs)[int(95*s):int(190*s), int(60*s):int(200*s)]
    m=cv2.matchTemplate(area,t,cv2.TM_CCOEFF_NORMED); _,v,_,loc=cv2.minMaxLoc(m)
    if v>best[0]: best=(v,round(float(s),3),(loc[0]+100-int(60*s),loc[1]-int(95*s)))
print(best)
np.save('pos.npy',np.array([best[1],best[2][0],best[2][1]]))
