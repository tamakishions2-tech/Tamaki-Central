import numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32)
def flat(a): al=a[...,3:4]/255; return (a[...,:3]*al+255*(1-al)).mean(2).astype(np.float32)
area=flat(corpo[150:360,100:380])
h=np.asarray(Image.open('h_0_0.png')).astype(np.float32)
best=(-1,)
for s in np.arange(1.10,1.50,0.01):
    hs=cv2.resize(h,None,fx=s,fy=s,interpolation=cv2.INTER_CUBIC)
    t=flat(hs)[int(100*s):int(200*s), int(55*s):int(185*s)]   # sobrancelhas, olhos, bico
    m=cv2.matchTemplate(area,t,cv2.TM_CCOEFF_NORMED); _,v,_,loc=cv2.minMaxLoc(m)
    if v>best[0]: best=(v,round(float(s),2),(loc[0]+100-int(55*s),loc[1]+150-int(100*s)))
print(best)
np.save('pos.npy',np.array([best[1],best[2][0],best[2][1]]))
# máscara do rosto do corpo
c=corpo[...,:3]; skin=c[215,238]; print('creme',skin)
d=np.abs(c-skin).sum(2); cand=(d<70)&(corpo[...,3]>200)
lab,_=nd.label(cand); face=lab==lab[215,238]
ys,xs=np.nonzero(face); print('face',xs.min(),xs.max(),ys.min(),ys.max())
face=nd.binary_fill_holes(face)
Image.fromarray((face*255).astype(np.uint8)).save('face_corpo.png')
