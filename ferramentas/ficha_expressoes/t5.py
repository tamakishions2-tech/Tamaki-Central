import numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
corpo=np.asarray(Image.open('corpo.png')).astype(np.float32); H,W=corpo.shape[:2]
s,X,Y=np.load('pos.npy'); X=int(X); Y=int(Y)
_c=corpo[...,:3]; _R,_G,_B=_c[...,0],_c[...,1],_c[...,2]
_lar=(_R>180)&(_G>110)&(_B<140)&(_R-_B>90)
_box=np.zeros(_lar.shape,bool); _box[110:185,185:265]=True
_bico=nd.binary_closing(_lar&_box,iterations=2); _bico=nd.binary_fill_holes(_bico); _bico=nd.binary_dilation(_bico,iterations=4)&_box
_inp=_c.copy(); _inp[_bico]=np.array([236,214,190.]); _inp=_c*(1-cv2.GaussianBlur(_bico.astype(np.float32),(0,0),1.2)[...,None])+_inp*cv2.GaussianBlur(_bico.astype(np.float32),(0,0),1.2)[...,None]
corpo=corpo.copy(); corpo[...,:3]=_inp.astype(np.float32)
Image.fromarray(np.clip(corpo,0,255).astype(np.uint8)).save('corpo_sem_bico.png')
def flat(a): al=a[...,3:4]/255; return (a[...,:3]*al+255*(1-al)).mean(2).astype(np.float32)
def coloca(h,dx=0,dy=0):
    hs=cv2.resize(h,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    M=np.float32([[1,0,X+dx],[0,1,Y+dy]])
    return cv2.warpAffine(hs,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
def acha(ref,lay,box,R=12):
    y0,y1,x0,x1=box; T=flat(ref)[y0:y1,x0:x1]; S=flat(lay)[y0-R:y1+R,x0-R:x1+R]
    m=cv2.matchTemplate(S,T,cv2.TM_CCOEFF_NORMED); _,v,_,(x,y)=cv2.minMaxLoc(m); return R-x,R-y,v
CORTE=96
CHAPEU=(40,100,170,290); ROSTO=(122,178,195,255); CORPO=corpo
yy=np.mgrid[0:H,0:W][0]
REF=None
for r in range(5):
    for c in range(3):
        h=np.asarray(Image.open(f'h_{r}_{c}.png')).astype(np.float32)
        lay=coloca(h)
        if r==0 and c==0: dx,dy,v=0,0,1
        elif c==0: dx,dy,v=acha(REF,lay,CHAPEU,R=20)
        else: dx,dy,v=acha(BASEL,lay,CHAPEU)
        lay=coloca(h,dx,dy)
        if c==0: BASEL=lay
        if r==0 and c==0: REF=lay
        m=(nd.binary_erosion(lay[...,3]>128,iterations=6)&(yy>=CORTE)).astype(np.float32)*np.clip((192-yy)/10,0,1)
        m=cv2.GaussianBlur(m,(0,0),1.3)*(lay[...,3]/255)
        comp=corpo.copy(); comp[...,:3]=corpo[...,:3]*(1-m[...,None])+lay[...,:3]*m[...,None]
        Image.fromarray(np.clip(comp,0,255).astype(np.uint8)).save(f'c_{r}_{c}.png')
        print(r,c,dx,dy,round(v,2))
s_=Image.new('RGB',(210*3,230*5))
for r in range(5):
  for c in range(3):
    im=Image.open(f'c_{r}_{c}.png'); b=Image.new('RGBA',im.size,(255,0,255,255)); b.alpha_composite(im); s_.paste(b.convert('RGB').crop((120,0,330,230)),(c*210,r*230))
s_.save('ver_comp.png')
