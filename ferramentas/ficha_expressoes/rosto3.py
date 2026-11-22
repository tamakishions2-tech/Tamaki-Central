# rosto3.py <dir> <spec.json> : refaz os 15 quadros com alinhamento constante pelo cabelo da grade
# saída em <dir>/r3/c_r_c.png e p_r_pisca.png / p_r_fala_pisca.png  + <dir>/r3/info.json
import sys, json, os, numpy as np, cv2
from PIL import Image, ImageDraw
from scipy import ndimage as nd
d=sys.argv[1]; spec=json.load(open(sys.argv[2])); os.makedirs(f'{d}/r3',exist_ok=True)
L=lambda f: np.asarray(Image.open(f'{d}/{f}').convert('RGBA')).astype(np.float32)
B=L('corpo.png'); H,W=B.shape[:2]
def poly(pts):
    im=Image.new('L',(W,H),0); ImageDraw.Draw(im).polygon([tuple(p) for p in pts],fill=255); return np.asarray(im)>127
if 'mascara' in spec: MF=nd.binary_fill_holes(np.asarray(Image.open(f'{d}/{spec["mascara"]}').convert('L'))>127)
else: MF=poly(spec['poligono'])
if 'casco_faixa' in spec:
    ys,xs=np.nonzero(MF); h_=cv2.convexHull(np.stack([xs,ys],1).astype(np.int32)); C=np.zeros((H,W),np.uint8); cv2.fillPoly(C,[h_],1)
    y0,y1=spec['casco_faixa']; C[:y0]=0; C[y1:]=0; MF|=C>0
if 'dentro' in spec: MF&=nd.binary_erosion(B[...,3]>200,iterations=spec['dentro'])
MF&=B[...,3]>200
def gray(a):
    al=a[...,3:]/255; g=(a[...,:3]*al+128*(1-al)).mean(2); return cv2.GaussianBlur(g.astype(np.float32),(0,0),1.0)
def inv(T): A=np.vstack([T,[0,0,1]]); return np.linalg.inv(A)[:2]
def comp(T1,T2): return (np.vstack([T1,[0,0,1]])@np.vstack([T2,[0,0,1]]))[:2]   # T1∘T2
def para_corpo(img,T): return cv2.warpAffine(img,T,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
heads={(r,c):L(f'h_{r}_{c}.png') for r in range(5) for c in range(3)}
# 1) transformação antiga de cada quadro (cabeça da grade -> corpo), achada no próprio c_r_c
ys,xs=np.nonzero(nd.binary_dilation(MF,iterations=4)); R=(xs.min(),ys.min(),xs.max()+1,ys.max()+1)
Mt=nd.binary_erosion(MF,iterations=3)[R[1]:R[3],R[0]:R[2]].astype(np.uint8)
def acha_old(cimg, keys, escalas):
    P=(np.abs(cimg[...,:3]-B[...,:3]).sum(-1)>12)&MF; P=nd.binary_erosion(P,iterations=1)
    Mt=P[R[1]:R[3],R[0]:R[2]].astype(np.uint8)
    T=gray(cimg)[R[1]:R[3],R[0]:R[2]]; best=None
    for k in keys:
        hg=gray(heads[k])
        for s in escalas:
            hs=cv2.resize(hg,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
            if hs.shape[0]<T.shape[0] or hs.shape[1]<T.shape[1]: continue
            m=cv2.matchTemplate(hs,T,cv2.TM_SQDIFF,mask=Mt)
            v,_,(x,y),_=cv2.minMaxLoc(m); v/=Mt.sum()
            if best is None or v<best[0]: best=(v,k,s,x,y)
    v,k,s,x,y=best
    Tm=np.float32([[s,0,R[0]-x],[0,s,R[1]-y]])   # h -> corpo
    # refina com ECC (afim) dentro do rosto
    try:
        crit=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,200,1e-6)
        _,Tm=cv2.findTransformECC(gray(heads[k]),gray(cimg),Tm.astype(np.float32),cv2.MOTION_AFFINE,crit,P.astype(np.uint8),5)
    except cv2.error: pass
    return v,k,Tm
info={}; old={}; src={}
for r in range(5):
    for c in range(3):
        cimg=L(f'c_{r}_{c}.png')
        if (0,0) in old: s0=float(np.sqrt(abs(np.linalg.det(old[(0,0)][:, :2])))); esc=np.arange(s0-.06,s0+.061,.01)
        else: esc=np.arange(.5,1.8,.02)
        v,k,Tm=acha_old(cimg,[(r,c)],esc)
        if v>150:   # quadro remapeado? procura em todas
            v2,k2,T2=acha_old(cimg,list(heads),esc)
            if v2<v*0.6: v,k,Tm=v2,k2,T2
        old[(r,c)]=Tm; src[(r,c)]=k; info[f'{r}{c}']={'fonte':list(k),'erro':round(float(v),1)}
# 2) cada cabeça alinhada à cabeça de referência (0,0) pelo cabelo/contorno (fora do rosto)
_y,_x=np.nonzero(MF); CX,CY=_x.mean(),_y.mean()
k0=src[(0,0)]; h0=heads[k0]; T0=old[(0,0)]
face_h0=cv2.warpAffine(MF.astype(np.uint8),T0,(h0.shape[1],h0.shape[0]),flags=cv2.INTER_NEAREST|cv2.WARP_INVERSE_MAP)>0
cab=(h0[...,3]>128)&~nd.binary_dilation(face_h0,iterations=6)
cab=nd.binary_erosion(h0[...,3]>128,iterations=2)&cab
crit=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,300,1e-6)
novo={}
for rc in old:
    k=src[rc]
    if k==k0: novo[rc]=T0; continue
    A=comp(inv(T0),old[rc]).astype(np.float32)   # h_k -> h0 (chute inicial)
    try:
        cc,A=cv2.findTransformECC(gray(heads[k]),gray(h0),A,cv2.MOTION_AFFINE,crit,cab.astype(np.uint8),5)
    except cv2.error as e:
        cc=-1; print('ECC falhou',rc,str(e)[-120:])
    # força semelhança (sem cisalhamento): tira escala média e rotação
    M=A[:, :2]; U,S,Vt=np.linalg.svd(M); Rm=U@Vt; s=S.mean(); A2=np.hstack([Rm*s,A[:,2:]])
    novo[rc]=comp(T0,A2.astype(np.float32))  # h_k -> h0 -> corpo
    info[f'{rc[0]}{rc[1]}']['cc']=round(float(cc),3)
    d_old=comp(novo[rc],inv(old[rc]))  # quanto mexeu (no centro do rosto)
    q=np.array([CX,CY,1.]); mv=d_old@q-q[:2]; info[f'{rc[0]}{rc[1]}']['mexeu']=[round(float(v),1) for v in mv]
    if cc<spec.get('cc_min',0.6) or np.abs(mv).max()>spec.get('max_mexe',12): novo[rc]=old[rc]; info[f'{rc[0]}{rc[1]}']['manteve']=1
# 3) conteúdo: o próprio c_r_c (já com olhos pintados, remapeado) levado para a posição nova
ys,xs=np.nonzero(MF); cy0,cy1=ys.min(),ys.max()
# pele do corpo e camada da frente (franja/mechas por cima do rosto)
e=spec.get('erode',3)
MP=nd.binary_erosion(MF,iterations=e) if e>0 else MF.copy()
pele=np.median(B[...,:3][nd.binary_erosion(MF,iterations=8)],0)
dist=np.abs(B[...,:3]-pele).sum(-1)
naop=(dist>spec.get('pele_tol',70))&MP
lab,n=nd.label(naop); borda=MP&~nd.binary_erosion(MP,iterations=2)
toca=np.unique(lab[borda&naop]); toca=toca[toca>0]
FR=np.isin(lab,toca) if spec.get('frente',1) else np.zeros((H,W),bool)
FR=nd.binary_dilation(FR,iterations=1)&MP if FR.any() else FR
mP=cv2.GaussianBlur(MP.astype(np.float32),(0,0),spec.get('suave',1.5))[...,None]
mF=cv2.GaussianBlur(FR.astype(np.float32),(0,0),0.7)[...,None]
def monta(rc):
    c=L(f'c_{rc[0]}_{rc[1]}.png')
    M=comp(old[rc],inv(novo[rc]))           # corpo novo -> h -> corpo antigo
    cont=cv2.warpAffine(c,M.astype(np.float32),(W,H),flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE)
    P=((np.abs(c[...,:3]-B[...,:3]).sum(-1)>12)&MF).astype(np.float32)
    P=nd.binary_closing(P>0,iterations=2).astype(np.float32)
    Pv=cv2.warpAffine(P,M.astype(np.float32),(W,H),flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP)
    Pv=cv2.GaussianBlur(Pv,(0,0),1.0)[...,None]
    cont[...,:3]=cont[...,:3]*Pv+B[...,:3]*(1-Pv)
    # tira da expressão o cabelo/contorno dela que encosta na borda do rosto
    if spec.get('limpa_borda_rosto',1):
        dc=np.abs(cont[...,:3]-pele).sum(-1)>spec.get('pele_tol',70)
        bb=MP&~nd.binary_erosion(MP,iterations=spec.get('faixa_borda',7))
        X=nd.binary_dilation(dc&bb,iterations=1)&bb
        xm=cv2.GaussianBlur(X.astype(np.float32),(0,0),0.8)[...,None]
        cont[...,:3]=cont[...,:3]*(1-xm)+B[...,:3]*xm
    out=B.copy(); out[...,:3]=B[...,:3]*(1-mP)+cont[...,:3]*mP
    out[...,:3]=out[...,:3]*(1-mF)+B[...,:3]*mF
    return out
res={rc:monta(rc) for rc in old}
for rc,o in res.items(): Image.fromarray(np.clip(o,0,255).astype(np.uint8)).save(f'{d}/r3/c_{rc[0]}_{rc[1]}.png')
# 4) piscar: olhos da coluna 3 nas colunas 1 e 2 (máscara dos olhos a partir da linha normal)
semp=spec.get('sem_piscar',[])
faixa=np.zeros((H,W),bool); faixa[cy0:int(cy0+(cy1-cy0)*spec.get('olho_ate',.6))]=True
def dif(a,f):
    D=np.abs(a[...,:3]-f[...,:3]).sum(-1)>70
    D&=MP&faixa&~FR; return nd.binary_opening(D,iterations=1)
def cascos(D,minimo=25):
    lab,n=nd.label(D); o=np.zeros((H,W),bool)
    for i in range(1,n+1):
        m=lab==i
        if m.sum()<minimo: continue
        yy,xx=np.nonzero(m); h_=cv2.convexHull(np.stack([xx,yy],1).astype(np.int32)); t=np.zeros((H,W),np.uint8); cv2.fillPoly(t,[h_],1); o|=t>0
    return o
base=cascos(dif(res[(0,0)],res[(0,2)]))
lab,n=nd.label(base)
if n>2:   # fica com os 2 maiores (os olhos)
    sz=nd.sum(base,lab,range(1,n+1)); keep=np.argsort(sz)[-2:]+1; base=np.isin(lab,keep)
area=nd.binary_dilation(base,iterations=spec.get('olho_folga',6))
for r in range(5):
    f=res[(r,2)]
    if r in semp: olhos=np.zeros((H,W),bool)
    else:
        D=dif(res[(r,0)],f)&area
        olhos=(cascos(D,15)|base)&area
        olhos=nd.binary_dilation(olhos,iterations=2)&MP
    mo=cv2.GaussianBlur(olhos.astype(np.float32),(0,0),1.5)[...,None]
    for c,nome in ((0,'pisca'),(1,'fala_pisca')):
        o=res[(r,c)].copy(); o[...,:3]=o[...,:3]*(1-mo)+f[...,:3]*mo
        if r in spec.get('pisca_propria',[]): o=res[(r,c)].copy()
        Image.fromarray(np.clip(o,0,255).astype(np.uint8)).save(f'{d}/r3/p_{r}_{nome}.png')
json.dump(info,open(f'{d}/r3/info.json','w'))
print(d,'ok', {k:(v['fonte'],v['erro'],v.get('mexeu')) for k,v in info.items()})
