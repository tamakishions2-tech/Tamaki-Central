import numpy as np, cv2
from PIL import Image
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32); H,W=corpo.shape[:2]
res=np.load('alinha.npy',allow_pickle=True).item()
mask=np.asarray(Image.open('mascara.png')).astype(np.float32)/255
def flat(a): al=a[...,3:4]/255; return (a[...,:3]*al+255*(1-al)).mean(2).astype(np.float32)
def coloca(h,s,loc,dx=0,dy=0):
    hs=cv2.resize(h,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    M=np.float32([[1,0,loc[0]+dx],[0,1,loc[1]+dy]])
    return cv2.warpAffine(hs,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
def acha(lay_ref,lay,box,R=22):
    y0,y1,x0,x1=box; T=flat(lay_ref)[y0:y1,x0:x1]; S=flat(lay)[y0-R:y1+R,x0-R:x1+R]
    m=cv2.matchTemplate(S,T,cv2.TM_CCOEFF_NORMED); _,v,_,(x,y)=cv2.minMaxLoc(m); return R-x,R-y,v
NARIZ=(108,132,203,233); BAIXO=(112,158,195,242)
REF=None
for r in range(5):
    s=0.78
    lays={}
    for c in range(3):
        h=np.asarray(Image.open(f'h_{r}_{c}.png')).astype(np.float32)
        lay=coloca(h,s,(124,11))
        if r==0 and c==0: REF=lay; dx=dy=0; v=1
        elif c==0: dx,dy,v=acha(REF,lay,NARIZ)
        elif c==1: dx,dy,v=acha(lays[0],lay,NARIZ)
        else: dx,dy,v=acha(lays[0],lay,BAIXO)
        lay=coloca(h,s,(124,11),dx,dy); lays[c]=lay
        mm=mask[...,None]*(lay[...,3:4]/255)
        comp=corpo.copy(); comp[...,:3]=corpo[...,:3]*(1-mm)+lay[...,:3]*mm
        Image.fromarray(np.clip(comp,0,255).astype(np.uint8)).save(f'c_{r}_{c}.png')
        print(r,c,'ajuste',dx,dy,'conf',round(v,2))
