import numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
CLARO=np.array([150,180,82.]); ESCURO=np.array([70,104,36.])
OLHOS=[(78,104,119,150),(78,104,154,186)]
_m=(np.asarray(Image.open('mascara.png'))>128).astype(np.uint8); _h=cv2.convexHull(cv2.findNonZero(_m)); ROSTO=np.zeros_like(_m); cv2.fillConvexPoly(ROSTO,_h,1); ROSTO=ROSTO>0
def faz(f):
    a=np.asarray(Image.open(f)).astype(np.float32)
    for (Y0,Y1,X0,X1) in OLHOS:
        sub=a[Y0:Y1,X0:X1,:3]; R,G,B=sub[...,0],sub[...,1],sub[...,2]
        lum=sub@[.299,.587,.114]; sat=sub.max(2)-sub.min(2)
        pele=(R>G+45)
        branco=(lum>165)&(sat<90)
        iris=((G>B+25)&(G>=R-12)|(G>R+3)&(G>B+10))&~pele
        semente=(branco|iris)&ROSTO[Y0:Y1,X0:X1]
        lb,n=nd.label(semente)
        if n==0: continue
        ar=nd.sum(semente,lb,range(1,n+1)); keep=np.zeros(n+1,bool); keep[1:]=ar>=4
        sem=keep[lb]
        if sem.sum()<10: continue
        # componente principal + vizinhos próximos
        hull=cv2.convexHull(cv2.findNonZero(sem.astype(np.uint8))); H=np.zeros(sem.shape,np.uint8); cv2.fillConvexPoly(H,hull,1); H=H>0
        H=nd.binary_dilation(H,iterations=1)&~pele&ROSTO[Y0:Y1,X0:X1]
        dark=lum<70
        ys_,xs_=np.nonzero(H); cyH=(ys_.min()+ys_.max())/2
        yy_=np.arange(H.shape[0])[:,None]*np.ones((1,H.shape[1]))
        borda=H&~nd.binary_erosion(H,iterations=2)
        alvo=H&~(dark&borda&(yy_<cyH))   # mantém só o contorno escuro de cima
        alvo|=nd.binary_dilation(H,iterations=1)&branco&~pele&ROSTO[Y0:Y1,X0:X1]
        alvo|=H&dark&(G>R+5)                                 # anel escuro esverdeado da íris vira verde
        # brilho: o maior pontinho branco puro dentro
        br=(lum>225)&H; lbb,nb=nd.label(br)
        if nb:
            arb=np.array(nd.sum(br,lbb,range(1,nb+1))); ok=np.where(arb<=10)[0]
            if len(ok): alvo&=~(lbb==(ok[np.argmax(arb[ok])]+1))
        ys=np.nonzero(H)[0]; y0,y1=ys.min(),ys.max()+1
        t=np.clip((np.arange(sub.shape[0])-y0)/max(1,(y1-y0)),0,1)[:,None,None]
        cor=np.broadcast_to(ESCURO*(1-t)+CLARO*t,sub.shape)
        m=alvo.astype(np.float32)[...,None]
        a[Y0:Y1,X0:X1,:3]=sub*(1-m)+cor*m
    Image.fromarray(np.clip(a,0,255).astype(np.uint8)).save(f)
for r in range(5):
    for c in range(2): faz(f'c_{r}_{c}.png')
