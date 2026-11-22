import numpy as np, cv2
from PIL import Image
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32); H,W=corpo.shape[:2]
res={}
mask=np.asarray(Image.open('mascara.png')).astype(np.float32)/255
_m=(mask>0.5).astype(np.uint8); _h=cv2.convexHull(cv2.findNonZero(_m)); mask=np.zeros_like(_m); cv2.fillConvexPoly(mask,_h,1); mask=cv2.GaussianBlur(mask.astype(np.float32),(0,0),1.0)
def flat(a): al=a[...,3:4]/255; return (a[...,:3]*al+255*(1-al)).mean(2).astype(np.float32)
def coloca(h,s,loc,dx=0,dy=0):
    hs=cv2.resize(h,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    M=np.float32([[1,0,loc[0]+dx],[0,1,loc[1]+dy]])
    return cv2.warpAffine(hs,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
def acha(lay_ref,lay,box,R=20):
    y0,y1,x0,x1=box; T=flat(lay_ref)[y0:y1,x0:x1]; S=flat(lay)[y0-R:y1+R,x0-R:x1+R]
    m=cv2.matchTemplate(S,T,cv2.TM_CCOEFF_NORMED); _,v,_,(x,y)=cv2.minMaxLoc(m); return R-x,R-y,v
NARIZ=(150,190,150,205); TOPO=(25,85,80,280); BAIXO=(268,330,200,265)
REF=None; OFF={}
BOX=np.zeros(corpo.shape[:2],bool); BOX[110:215,118:230]=True
BANDA=np.zeros(corpo.shape[:2],np.float32); BANDA[122:172,122:228]=1; BANDA=cv2.GaussianBlur(BANDA,(0,0),1.5)
PELE=np.array([242,187,159.],np.float32); NP=(165,173)
for r in range(5):
    s=1.03
    lays={}
    for c in range(3):
        h=np.asarray(Image.open(f'h_{r}_{c}.png')).astype(np.float32)
        lay=coloca(h,s,(38,9))
        if r==0 and c==0: REF=lay; dx=dy=0; v=1
        elif c==0: dx,dy,v=acha(REF,lay,TOPO)
        elif c==1: dx,dy,v=acha(lays[0],lay,TOPO)
        else:
            dx,dy,v=acha(lays[0],lay,TOPO)
        lay=coloca(h,s,(38,9),dx,dy); lays[c]=lay
        if c==0: OFF[r]=(dx,dy)
        sk=np.abs(lay[...,:3]-PELE).sum(2)<75
        from scipy import ndimage as nd
        lb,_=nd.label(sk); ys,xs=np.nonzero(lb); k=np.argmin((ys-NP[0])**2+(xs-NP[1])**2)
        comp_=(sk&BOX).astype(np.uint8); comp_=nd.binary_opening(comp_,iterations=2).astype(np.uint8); pts=cv2.findNonZero(comp_); hull=cv2.convexHull(pts); hf=np.zeros(comp_.shape,np.uint8); cv2.fillConvexPoly(hf,hull,1); hf=nd.binary_erosion(hf>0,iterations=4); hf[122:172,122:228]=True; hf=hf.astype(np.float32)
        hf=cv2.GaussianBlur(hf,(0,0),1.0)
        mm=(np.maximum(mask,BANDA)*hf)[...,None]*(lay[...,3:4]/255)
        comp=corpo.copy(); comp[...,:3]=corpo[...,:3]*(1-mm)+lay[...,:3]*mm
        Image.fromarray(np.clip(comp,0,255).astype(np.uint8)).save(f'c_{r}_{c}.png')
        print(r,c,'ajuste',dx,dy,'conf',round(v,2))
