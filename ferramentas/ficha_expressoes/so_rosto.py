# Refaz os quadros colando SÓ o rosto da expressão em cima da cabeça do corpo inteiro.
# Uso: so_rosto.py <dir> <spec.json> [previa.png]
# spec: {"mascara":"mascara.png","erode":3}  ou  {"poligono":[[x,y],...]}  (+ "soma":[poligonos], "tira":[poligonos], "suave":2)
import sys, json, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as nd
d=sys.argv[1]; spec=json.load(open(sys.argv[2])); prev=sys.argv[3] if len(sys.argv)>3 else None
B=np.asarray(Image.open(f'{d}/corpo.png').convert('RGBA')).astype(float)
H,W=B.shape[:2]
def poly(pts):
    im=Image.new('L',(W,H),0); ImageDraw.Draw(im).polygon([tuple(p) for p in pts],fill=255); return np.asarray(im)>127
if 'auto' in spec:
    import cv2
    L=lambda f: np.asarray(Image.open(f'{d}/{f}').convert('RGBA')).astype(float)[...,:3]
    D=np.zeros((H,W),bool)
    for r in range(5):
        a=L(f'c_{r}_0.png')
        for f in (f'c_{r}_1.png',f'p_{r}_pisca.png'):
            D|=np.abs(L(f)-a).sum(-1)>60
    D=nd.binary_opening(D,iterations=1)
    if 'limite' in spec: D&=poly(spec['limite'])
    lab,n=nd.label(D); sz=nd.sum(D,lab,range(1,n+1)); D=np.isin(lab,1+np.nonzero(sz>=30)[0])
    ys,xs=np.nonzero(D); h=cv2.convexHull(np.stack([xs,ys],1).astype(np.int32))
    M=np.zeros((H,W),np.uint8); cv2.fillPoly(M,[h],1); M=M>0
    a=spec['auto']; M=nd.binary_dilation(M,iterations=a.get('cresce',12))
    if 'sobe' in a:
        sh=a['sobe']; M2=M.copy()
        for k in range(1,sh+1): M2[:-k]|=M[k:]
        M=M2
    if 'desce' in a:
        sh=a['desce']; M2=M.copy()
        for k in range(1,sh+1): M2[k:]|=M[:-k]
        M=M2
elif 'mascara' in spec:
    M=np.asarray(Image.open(f'{d}/{spec["mascara"]}').convert('L'))>127
    M=nd.binary_fill_holes(M)
else:
    M=poly(spec['poligono'])
if 'casco_faixa' in spec:
    import cv2
    ys,xs=np.nonzero(M); pts=np.stack([xs,ys],1).astype(np.int32)
    h=cv2.convexHull(pts); C=np.zeros((H,W),np.uint8); cv2.fillPoly(C,[h],1)
    y0,y1=spec['casco_faixa']; C[:y0]=0; C[y1:]=0; M|=C>0
for p in spec.get('soma',[]): M|=poly(p)
for p in spec.get('tira',[]): M&=~poly(p)
if 'limite' in spec and spec.get('corta',1): M&=poly(spec['limite'])
if 'dentro' in spec: M&=nd.binary_erosion(B[...,3]>200,iterations=spec['dentro'])
e=spec.get('erode',3)
if e>0: M=nd.binary_erosion(M,iterations=e)
M&=B[...,3]>200
s=spec.get('suave',1.5)
Mf=nd.gaussian_filter(M.astype(float),s) if s>0 else M.astype(float)
Mf=np.clip(Mf*1.0,0,1)[...,None]
fontes=[f'c_{r}_{c}.png' for r in range(5) for c in (0,1)]+[f'p_{r}_{k}.png' for r in range(5) for k in ('pisca','fala_pisca')]
out=f'{d}/so'; import os; os.makedirs(out,exist_ok=True)
res={}
for f in fontes:
    F=np.asarray(Image.open(f'{d}/{f}').convert('RGBA')).astype(float)
    fa=F[...,3:]/255
    frgb=F[...,:3]*fa+B[...,:3]*(1-fa)   # onde a expressão é transparente, fica o corpo
    m=Mf*(F[...,3:]>0)
    rgb=B[...,:3]*(1-m)+frgb*m
    o=np.dstack([rgb,B[...,3]]).clip(0,255).astype(np.uint8)
    Image.fromarray(o).save(f'{out}/{f}'); res[f]=o
if prev:
    ys,xs=np.nonzero(M); cy0=max(0,ys.min()-60); cx=int(xs.mean())
    box=(max(0,cx-130),cy0,min(W,cx+130),cy0+260)
    cont=M^nd.binary_erosion(M,iterations=1)
    tiles=[]
    for f in [f'c_{r}_{c}.png' for r in range(5) for c in (0,1)]+['p_0_pisca.png','p_1_pisca.png']:
        o=res[f].astype(float); a=o[...,3:]/255
        rgb=o[...,:3]*a+np.array([255,0,255])*(1-a)
        t=Image.fromarray(rgb.astype(np.uint8)).crop(box); tiles.append(t)
    b=B.copy(); a=b[...,3:]/255; rgb=b[...,:3]*a+np.array([255,0,255])*(1-a); rgb[cont]=[0,255,0]
    tiles.insert(0,Image.fromarray(rgb.astype(np.uint8)).crop(box))
    tw,th=tiles[0].size; cols=7
    G=Image.new('RGB',(tw*cols,th*2),(30,30,30))
    for i,t in enumerate(tiles): G.paste(t,((i%cols)*tw,(i//cols)*th))
    G.save(prev)
