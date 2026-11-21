import os, numpy as np
os.environ['U2NET_HOME']='/home/claude/modelos'
from PIL import Image
from rembg import new_session, remove
from scipy import ndimage
im=Image.open('/mnt/user-data/uploads/0b7c5bce-image.png').convert('RGB'); print(im.size)
sess=new_session('isnet-anime')
out=np.asarray(remove(im,session=sess)); Image.fromarray(out).save('sem_fundo.png')
al=out[...,3]>40
lab,n=ndimage.label(al); tam=ndimage.sum(np.ones_like(lab),lab,range(1,n+1))
objs=ndimage.find_objects(lab)
for i,(sl,t) in enumerate(zip(objs,tam)):
    if t>3000: print(i+1,int(t),sl[1].start,sl[1].stop,sl[0].start,sl[0].stop)
