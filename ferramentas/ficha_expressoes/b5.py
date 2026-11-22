import numpy as np, cv2, sys
from PIL import Image
from scipy import ndimage as nd
CORTE,FUNDO=int(sys.argv[1]),int(sys.argv[2]); TOPO=tuple(int(v) for v in sys.argv[3].split(','))
ERO=int(sys.argv[4]) if len(sys.argv)>4 else 5
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32); H,W=corpo.shape[:2]
sx,sy,X,Y=np.load('pos2.npy'); X=int(X); Y=int(Y)
def flat(a): al=a[...,3:4]/255; return (a[...,:3]*al+255*(1-al)).mean(2).astype(np.float32)
def coloca(h,dx=0,dy=0):
    hs=cv2.resize(h,None,fx=sx,fy=sy,interpolation=cv2.INTER_AREA)
    M=np.float32([[1,0,X+dx],[0,1,Y+dy]])
    return cv2.warpAffine(hs,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
def acha(ref,lay,box,R=14):
    y0,y1,x0,x1=box; T=flat(ref)[y0:y1,x0:x1]; S=flat(lay)[max(0,y0-R):y1+R,x0-R:x1+R]
    m=cv2.matchTemplate(S,T,cv2.TM_CCOEFF_NORMED); _,v,_,(x,y)=cv2.minMaxLoc(m); return R-x,(min(R,y0))-y,v
yy=np.mgrid[0:H,0:W][0]
REF=None
for r in range(5):
    for c in range(3):
        h=np.asarray(Image.open(f'h_{r}_{c}.png')).astype(np.float32)
        lay=coloca(h)
        if REF is None: dx=dy=0; v=1
        else: dx,dy,v=acha(REF,lay,TOPO)
        lay=coloca(h,dx,dy)
        if REF is None: REF=lay
        m=nd.binary_erosion(lay[...,3]>128,iterations=ERO).astype(np.float32)*np.clip((yy-CORTE)/6,0,1)*np.clip((FUNDO-yy)/8,0,1)
        m=cv2.GaussianBlur(m,(0,0),1.2)
        comp=corpo.copy(); comp[...,:3]=corpo[...,:3]*(1-m[...,None])+lay[...,:3]*m[...,None]
        comp[...,3]=np.maximum(corpo[...,3],255*np.clip(m*2,0,1))
        Image.fromarray(np.clip(comp,0,255).astype(np.uint8)).save(f'c_{r}_{c}.png')
        print(r,c,dx,dy,round(v,2),end=' | ')
