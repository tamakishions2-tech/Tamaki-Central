import numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32); H,W=corpo.shape[:2]
sx,sy,X,Y=np.load('pos2.npy'); X=int(X); Y=int(Y)
def flat(a): al=a[...,3:4]/255; return (a[...,:3]*al+255*(1-al)).mean(2).astype(np.float32)
def coloca(h,dx=0,dy=0):
    hs=cv2.resize(h,None,fx=sx,fy=sy,interpolation=cv2.INTER_AREA)
    M=np.float32([[1,0,X+dx],[0,1,Y+dy]])
    return cv2.warpAffine(hs,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
def acha(ref,lay,box,R=12):
    y0,y1,x0,x1=box; T=flat(ref)[y0:y1,x0:x1]; S=flat(lay)[y0-R:y1+R,x0-R:x1+R]
    m=cv2.matchTemplate(S,T,cv2.TM_CCOEFF_NORMED); _,v,_,(x,y)=cv2.minMaxLoc(m); return R-x,R-y,v
TOPO=(20,80,110,300); OCULOS=(140,175,160,230)
yy=np.mgrid[0:H,0:W][0]
corpo_al=corpo[...,3]>128
REF=None
for r in range(5):
    for c in range(3):
        h=np.asarray(Image.open(f'h_{r}_{c}.png')).astype(np.float32)
        lay=coloca(h)
        if REF is None: dx=dy=0; v=1
        elif c==0: dx,dy,v=acha(REF,lay,TOPO)
        elif c==1: dx,dy,v=acha(BASE,lay,TOPO)
        else: dx,dy,v=acha(BASE,lay,OCULOS)
        lay=coloca(h,dx,dy)
        if REF is None: REF=lay
        if c==0: BASE=lay
        m=(nd.binary_erosion((lay[...,3]>128)&corpo_al,iterations=5)).astype(np.float32)*np.clip((200-yy)/10,0,1)
        m=cv2.GaussianBlur(m,(0,0),1.2)
        comp=corpo.copy(); comp[...,:3]=corpo[...,:3]*(1-m[...,None])+lay[...,:3]*m[...,None]
        Image.fromarray(np.clip(comp,0,255).astype(np.uint8)).save(f'c_{r}_{c}.png')
        print(r,c,dx,dy,round(v,2))
s_=Image.new('RGB',(260*3,240*5))
for r in range(5):
  for c in range(3):
    im=Image.open(f'c_{r}_{c}.png'); b=Image.new('RGBA',im.size,(255,0,255,255)); b.alpha_composite(im); s_.paste(b.convert('RGB').crop((70,0,330,240)),(c*260,r*240))
s_.save('ver_comp.png')
