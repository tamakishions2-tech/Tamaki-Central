import numpy as np, sys
from PIL import Image
from scipy import ndimage as nd
im=np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.float32)
mn=im.min(2)
W=mn>232
lab,n=nd.label(W)
borda=np.unique(np.r_[lab[0],lab[-1],lab[:,0],lab[:,-1]])
bg=np.isin(lab,borda[borda>0])
ar=nd.sum(W,lab,range(1,n+1))
puro=nd.mean(mn,lab,range(1,n+1))
fech=np.zeros(n+1,bool); cx=nd.center_of_mass(W,lab,range(1,n+1)); cxs=np.array([c[1] for c in cx])
fech[1:]=((ar>=120)|((ar>=8)&(cxs<480)))&(puro>242)
bg|=fech[lab]
fg=~bg

# suaviza beira
anel=fg&nd.binary_dilation(bg,np.ones((3,3)))
al=np.where(fg,255.,0.)
al[anel]=np.clip((252-mn[anel])/(252-150)*255,60,255)
out=np.dstack([im,al]).astype(np.uint8)
Image.fromarray(out,'RGBA').save(sys.argv[2])
