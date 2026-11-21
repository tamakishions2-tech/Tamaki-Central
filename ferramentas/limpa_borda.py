import sys, numpy as np
from PIL import Image
from scipy import ndimage as nd
ST=np.ones((3,3),bool)
def sobra_grande(op,minarea=150):
    lab,n=nd.label(op,ST)
    if n<=1: return op
    ar=nd.sum(op,lab,range(1,n+1)); keep=np.zeros(n+1,bool)
    keep[1:]=ar>=max(minarea,ar.max()*0.002); return keep[lab]
def limpa(im, peel=4, perto=12, maxman=90):
    a=np.array(im.convert('RGBA')).astype(np.float32)
    rgb=a[...,:3]; al=a[...,3]
    mx=rgb.max(-1); mn=rgb.min(-1); lum=rgb@[.299,.587,.114]
    W=((lum>105)&((mx-mn)<60))|(lum>205)
    op=sobra_grande((al>=100)&~((al<245)&W))
    fora=~op
    dE=nd.distance_transform_edt(~fora)
    # manchinhas claras perto da borda (dentro do contorno preto)
    cand=W&(dE<=perto)&(al>0)
    lab,n=nd.label(cand,ST)
    ruim=np.zeros_like(cand)
    if n:
        ar=nd.sum(cand,lab,range(1,n+1))
        # tamanho total da mancha clara (mesmo fora da faixa) p/ não comer áreas brancas grandes
        labW,nW=nd.label(W&(al>0),ST); arW=nd.sum(W,labW,range(1,nW+1))
        j=np.asarray(nd.maximum(labW,lab,range(1,n+1))).astype(int)
        tot=np.where(j>0,arW[np.maximum(j-1,0)],0)
        okc=np.zeros(n+1,bool); okc[1:]=tot<=maxman
        ruim|=okc[lab]
    # halo branco colado no transparente
    o2=op.copy()
    for _ in range(peel):
        b=o2&nd.binary_dilation(~o2,ST)&W
        if not b.any(): break
        o2&=~b
    ruim|=(op&~o2)
    # pixels ruins: semitransparentes ou na beira somem; os de dentro pegam a cor escura vizinha
    some=ruim&((al<230)|nd.binary_dilation(fora,ST))
    op&=~some
    pinta=ruim&op
    bom=op&~W
    if pinta.any():
        _,(iy,ix)=nd.distance_transform_edt(~bom,return_indices=True)
        rgb[pinta]=rgb[iy[pinta],ix[pinta]]
    op=sobra_grande(op)
    # beira: cor do sólido mais perto + alfa um pouco mais firme
    dentro=nd.binary_erosion(op,ST)&(al>=250)
    _,(iy,ix)=nd.distance_transform_edt(~dentro,return_indices=True)
    anel=op&~dentro
    alf=np.where(op,np.clip((al-40)/(255-40)*255,0,255),0)
    alf[dentro]=255
    out=np.dstack([rgb,alf]).clip(0,255).astype(np.uint8)
    return Image.fromarray(out,'RGBA')
if __name__=='__main__':
    for p in sys.argv[1:]:
        r=limpa(Image.open(p)); r.save(p,'WEBP',quality=92,method=6); print('ok',p)
