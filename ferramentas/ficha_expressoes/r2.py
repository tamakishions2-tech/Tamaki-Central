import numpy as np
from PIL import Image
from scipy import ndimage
a=np.asarray(Image.open('sem_fundo.png')).copy()
al=a[...,3]>40
cols=[(518,735),(818,1036),(1118,1339)]
heads={}
for c,(x0,x1) in enumerate(cols):
    prof=al[:,x0:x1].sum(1)
    cuts=[0]
    for exp in (194,388,582,778):
        lo,hi=exp-25,exp+25; cuts.append(lo+int(np.argmin(prof[lo:hi])))
    cuts.append(1024)
    print(c,cuts,[int(prof[k]) for k in cuts[1:-1]])
    for r in range(5):
        sub=a[cuts[r]:cuts[r+1],x0-6:x1+6].copy()
        lab,n=ndimage.label(sub[...,3]>20); tam=ndimage.sum(np.ones_like(lab),lab,range(1,n+1)); big=np.argmax(tam)+1
        sub[...,3][~ndimage.binary_dilation(lab==big,iterations=2)]=0
        Image.fromarray(sub).save(f'h_{r}_{c}.png')
body=a[:, 25:405].copy()
lab,n=ndimage.label(body[...,3]>20); tam=ndimage.sum(np.ones_like(lab),lab,range(1,n+1)); big=np.argmax(tam)+1
body[...,3][~ndimage.binary_dilation(lab==big,iterations=2)]=0
Image.fromarray(body).save('corpo.png')
