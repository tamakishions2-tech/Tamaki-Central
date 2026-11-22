import numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32); H,W=corpo.shape[:2]
S,ANG,X,Y=0.805,2,125,1
def flat(a): al=a[...,3:4]/255; return (a[...,:3]*al+255*(1-al)).mean(2).astype(np.float32)
def coloca(h,dx=0,dy=0):
    hs=cv2.resize(h,None,fx=S,fy=S,interpolation=cv2.INTER_AREA)
    M=cv2.getRotationMatrix2D((hs.shape[1]/2,hs.shape[0]/2),ANG,1); M[0,2]+=X+dx; M[1,2]+=Y+dy
    return cv2.warpAffine(hs,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
def acha(ref,lay,box,R=12):
    y0,y1,x0,x1=box; T=flat(ref)[y0:y1,x0:x1]; Sx=flat(lay)[max(0,y0-R):y1+R,x0-R:x1+R]
    m=cv2.matchTemplate(Sx,T,cv2.TM_CCOEFF_NORMED); _,v,_,(x,y)=cv2.minMaxLoc(m); return R-x,min(R,y0)-y,v
TOPO=(14,50,150,330)
# máscara: rosto do corpo (oval laranja liso) dilatado, dentro da silhueta do corpo
c=corpo[...,:3]; p=c[85,243]; d=np.abs(c-p).sum(2)<60
lab,_=nd.label(d&(corpo[...,3]>200)); face=nd.binary_fill_holes(lab==lab[85,243])
ys,xs=np.nonzero(face); print('face',xs.min(),xs.max(),ys.min(),ys.max())
cy,cx=(ys.min()+ys.max())/2+6,(xs.min()+xs.max())/2
ry,rx=(ys.max()-ys.min())/2+22,(xs.max()-xs.min())/2+34
yy,xx=np.mgrid[0:H,0:W]
ell=(((xx-cx)/rx)**2+((yy-cy)/ry)**2<=1)&(yy>48)
REF=None
for r in range(5):
    for cc in range(3):
        h=np.asarray(Image.open(f'h_{r}_{cc}.png')).astype(np.float32)
        lay=coloca(h)
        if REF is None: dx=dy=0; v=1
        else: dx,dy,v=acha(REF,lay,TOPO)
        lay=coloca(h,dx,dy)
        if REF is None: REF=lay
        m=(ell&(lay[...,3]>128)&(corpo[...,3]>128)).astype(np.float32)
        m=cv2.GaussianBlur(m,(0,0),2.0)
        comp=corpo.copy(); comp[...,:3]=corpo[...,:3]*(1-m[...,None])+lay[...,:3]*m[...,None]
        Image.fromarray(np.clip(comp,0,255).astype(np.uint8)).save(f'c_{r}_{cc}.png')
        print(r,cc,dx,dy,round(v,2),end=' | ')
s_=Image.new('RGB',(220*3,200*5))
for r in range(5):
  for cc in range(3):
    im=Image.open(f'c_{r}_{cc}.png'); b=Image.new('RGBA',im.size,(255,0,255,255)); b.alpha_composite(im); s_.paste(b.convert('RGB').crop((130,0,350,200)),(cc*220,r*200))
s_.save('ver_comp.png')
