import numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
CLARO=np.array([104,156,62.]); ESCURO=np.array([50,90,30.])
OLHOS=[(92,152,165,214),(92,152,214,265)]
SK=np.array([246,169,132.])
def faz(f):
    a=np.asarray(Image.open(f)).astype(np.float32)
    for (Y0,Y1,X0,X1) in OLHOS:
        sub=a[Y0:Y1,X0:X1,:3]; R,G,B=sub[...,0],sub[...,1],sub[...,2]
        lum=sub@[.299,.587,.114]; sat=sub.max(2)-sub.min(2)
        verde=(G>R+4)&(lum<200)
        branco=(lum>165)&(sat<80)
        lv,nv=nd.label(verde)
        if nv==0: continue
        arv=nd.sum(verde,lv,range(1,nv+1)); iris=lv==(np.argmax(arv)+1)
        if iris.sum()<40: continue
        perto=nd.binary_dilation(iris,iterations=4)
        lw,nw=nd.label(branco); ids=np.unique(lw[perto&branco]); ids=ids[ids>0]
        wh=np.isin(lw,ids)
        u=(iris|wh).astype(np.uint8)
        hull=cv2.convexHull(cv2.findNonZero(u)); H=np.zeros_like(u); cv2.fillConvexPoly(H,hull,1); H=H>0
        Hd=nd.binary_dilation(H,iterations=1)
        pele=np.abs(sub-SK).sum(2)<70
        dark=(lum<85)
        borda=H&~nd.binary_erosion(H,iterations=2)
        linha=dark&(borda|~H)
        clarinho=(lum>140)&(sat<95)
        alvo=(H&~linha)|(Hd&~H&~dark&(clarinho|~pele))
        brilho=(lum>225)&H; lbb,nb=nd.label(brilho)
        if nb:
            arb=np.array(nd.sum(brilho,lbb,range(1,nb+1))); keepb=np.zeros(nb+1,bool)
            j=np.argmax(np.where(arb<=16,arb,0)); 
            if arb[j]<=16 and arb[j]>=2: keepb[j+1]=True
            alvo&=~keepb[lbb]
        ys=np.nonzero(H)[0]; y0,y1=ys.min(),ys.max()+1
        t=np.clip((np.arange(sub.shape[0])-y0)/max(1,(y1-y0)),0,1)[:,None,None]
        cor=np.broadcast_to(ESCURO*(1-t)+CLARO*t,sub.shape)
        m=np.maximum(alvo.astype(np.float32),cv2.GaussianBlur(alvo.astype(np.float32),(0,0),0.6)*0.8*(~dark))[...,None]
        a[Y0:Y1,X0:X1,:3]=sub*(1-m)+cor*m
    Image.fromarray(np.clip(a,0,255).astype(np.uint8)).save(f)
for r in range(5):
    for c in range(2): faz(f'c_{r}_{c}.png')
