# exporta2.py Nome pasta src_dir [suave] -- usa os quadros "so/" e tira buracos brancos do fundo
import numpy as np, sys, os, json
from PIL import Image
from scipy import ndimage as nd
sys.path.insert(0,'/home/claude/scripts')
from limpa_borda import limpa
nome0,pasta,src=sys.argv[1],sys.argv[2],sys.argv[3]; suave='suave' in sys.argv[4:]
bur=json.load(open('/home/claude/v2/buracos.json')).get(pasta,{})
al=np.asarray(Image.open('corpo.png'))[...,3]
ys,xs=np.nonzero(al>20); box=(max(xs.min()-4,0),max(ys.min()-4,0),min(xs.max()+5,al.shape[1]),min(ys.max()+5,al.shape[0]))
if pasta=='kaoro': box=(max(box[0]-2,0),max(box[1]-2,0),min(box[2]+2,al.shape[1]),min(box[3]+2,al.shape[0]))
dest=f'/home/claude/tamaki-central/atores/{pasta}/'
for f in os.listdir(dest): os.remove(dest+f)
# máscara de buracos no corpo (recortado)
B=np.asarray(Image.open('corpo.png').convert('RGBA').crop(box)).astype(int)
rgb=B[...,:3]; mn=bur.get('mn',235); sat=bur.get('sat',14)
wh=(B[...,3]>100)&(rgb.min(-1)>mn)&((rgb.max(-1)-rgb.min(-1))<sat)
lab,n=nd.label(wh); buraco=np.zeros(wh.shape,bool)
for i,sl in enumerate(nd.find_objects(lab),1):
    m=lab==i; yy,xx=np.nonzero(m); cx,cy=xx.mean(),yy.mean()
    ok=False
    for (px,py) in bur.get('pontos',[]):
        if abs(px-cx)<8 and abs(py-cy)<8: ok=True
    for (x0,y0,x1,y1) in bur.get('areas',[]):
        if x0<=cx<=x1 and y0<=cy<=y1: ok=True
    for (x0,y0,x1,y1) in bur.get('fora',[]):
        if x0<=cx<=x1 and y0<=cy<=y1: ok=False
    if ok: buraco|=m
if buraco.any():
    # inclui a borda anti-aliasing clara em volta
    viz=nd.binary_dilation(buraco,iterations=2)&(rgb.min(-1)>170)&((rgb.max(-1)-rgb.min(-1))<40)
    buraco|=viz
print(pasta,'pixels de buraco:',int(buraco.sum()))
emos={0:'',1:'_feliz',2:'_bravo',3:'_triste',4:'_surpreso'}
arqs=[]
for r,e in emos.items():
    fontes={'':f'c_{r}_0.png','_fala':f'c_{r}_1.png','_fala2':f'c_{r}_1.png','_pisca':f'p_{r}_pisca.png','_fala_pisca':f'p_{r}_fala_pisca.png'}
    for suf,s in fontes.items():
        nome=f'{nome0}{e}{suf}.webp'
        im=np.array(Image.open(f'{src}/{s}').convert('RGBA').crop(box))
        im[...,3][buraco]=0
        im=Image.fromarray(im)
        (limpa(im,peel=1,maxman=20) if suave else limpa(im)).save(dest+nome,'WEBP',quality=92,method=6); arqs.append(nome)
open('arqs.txt','w').write('\n'.join(sorted(arqs)))
