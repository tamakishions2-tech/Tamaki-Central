import sys
from PIL import Image
import numpy as np
d=sys.argv[1]; out=sys.argv[2]; pasta=sys.argv[3]
fs=['c_0_0','c_1_1','c_2_0','c_3_0','c_4_1']
B=np.asarray(Image.open(f'{d}/corpo.png'))
ims=[np.asarray(Image.open(f'{d}/{pasta}/{f}.png')) for f in fs]
D=np.zeros(B.shape[:2],bool)
for im in ims: D|=np.abs(im.astype(int)-B.astype(int)).sum(-1)>30
yy,xx=np.nonzero(D); cx,cy=int(xx.mean()),int(yy.mean()); S=int(max(np.ptp(yy),np.ptp(xx))*0.6)+10
o=Image.new('RGB',(5*240,240))
for i,im in enumerate(ims):
    t=Image.fromarray(im).crop((cx-S,cy-S,cx+S,cy+S)); bg=Image.new('RGBA',t.size,(60,55,90,255)); bg.alpha_composite(t); o.paste(bg.convert('RGB').resize((240,240)),(i*240,0))
o.save(out)
