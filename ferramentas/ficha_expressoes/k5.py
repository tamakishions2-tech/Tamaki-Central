import numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32); H,W=corpo.shape[:2]
s,X,Y=np.load('pos.npy'); X=int(X); Y=int(Y)
fc=np.asarray(Image.open('face_corpo.png'))>0
fcu=fc.astype(np.uint8); hc=cv2.convexHull(cv2.findNonZero(fcu)); fc=np.zeros_like(fcu); cv2.fillConvexPoly(fc,hc,1); fc=fc>0
CREME=np.array([241,215,187.],np.float32)
def flat(a): al=a[...,3:4]/255; return (a[...,:3]*al+255*(1-al)).mean(2).astype(np.float32)
def coloca(h,dx=0,dy=0):
    hs=cv2.resize(h,None,fx=s,fy=s,interpolation=cv2.INTER_CUBIC)
    M=np.float32([[1,0,X+dx],[0,1,Y+dy]])
    return cv2.warpAffine(hs,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
def acha(ref,lay,box,R=30):
    y0,y1,x0,x1=box; T=flat(ref)[y0:y1,x0:x1]; S=flat(lay)[y0-R:y1+R,x0-R:x1+R]
    m=cv2.matchTemplate(S,T,cv2.TM_CCOEFF_NORMED); _,v,_,(x,y)=cv2.minMaxLoc(m); return R-x,R-y,v
BICO=(255,295,205,272); TOPO=(105,205,140,340)
def rosto(lay):
    d=np.abs(lay[...,:3]-CREME).sum(2); cand=(d<80)&(lay[...,3]>200)
    lb,_=nd.label(cand); ys,xs=np.nonzero(lb); k=np.argmin((ys-215)**2+(xs-238)**2)
    f=(lb==lb[ys[k],xs[k]]).astype(np.uint8); hull=cv2.convexHull(cv2.findNonZero(f)); o=np.zeros_like(f); cv2.fillConvexPoly(o,hull,1); return o>0
REF=None; OFF={}
for r in range(5):
    for c in range(3):
        h=np.asarray(Image.open(f'h_{r}_{c}.png')).astype(np.float32)
        lay=coloca(h)
        if REF is None: dx=dy=0; v=1
        else:
            dx,dy,v=acha(REF,lay,TOPO)
        lay=coloca(h,dx,dy)
        if REF is None: REF=lay
        if c==0: OFF[r]=(dx,dy)
        m=nd.binary_dilation(fc|rosto(lay),iterations=2).astype(np.float32)
        dentro=nd.binary_erosion(lay[...,3]>128,iterations=7).astype(np.float32)
        m=cv2.GaussianBlur(m*dentro,(0,0),1.2)*(lay[...,3]/255)
        comp=corpo.copy(); comp[...,:3]=corpo[...,:3]*(1-m[...,None])+lay[...,:3]*m[...,None]
        Image.fromarray(np.clip(comp,0,255).astype(np.uint8)).save(f'c_{r}_{c}.png')
        print(r,c,dx,dy,round(v,2))
s_=Image.new('RGB',(260*3,260*5))
for r in range(5):
  for c in range(3):
    im=Image.open(f'c_{r}_{c}.png'); b=Image.new('RGBA',im.size,(255,0,255,255)); b.alpha_composite(im); s_.paste(b.convert('RGB').crop((110,100,370,360)),(c*260,r*260))
s_.save('ver_comp.png')
