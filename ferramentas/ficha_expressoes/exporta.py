import numpy as np, sys, os
from PIL import Image
sys.path.insert(0,'/home/claude/scripts')
from limpa_borda import limpa
nome0,pasta=sys.argv[1],sys.argv[2]; suave=len(sys.argv)>3
al=np.asarray(Image.open('corpo.png'))[...,3]
ys,xs=np.nonzero(al>20); box=(max(xs.min()-4,0),max(ys.min()-4,0),min(xs.max()+5,al.shape[1]),min(ys.max()+5,al.shape[0]))
dest=f'/home/claude/tamaki-central/atores/{pasta}/'
for f in os.listdir(dest): os.remove(dest+f)
emos={0:'',1:'_feliz',2:'_bravo',3:'_triste',4:'_surpreso'}
arqs=[]
for r,e in emos.items():
    fontes={'':f'c_{r}_0.png','_fala':f'c_{r}_1.png','_fala2':f'c_{r}_1.png','_pisca':f'p_{r}_pisca.png','_fala_pisca':f'p_{r}_fala_pisca.png'}
    for suf,src in fontes.items():
        nome=f'{nome0}{e}{suf}.webp'
        im=Image.open(src).crop(box)
        (limpa(im,peel=1,maxman=20) if suave else limpa(im)).save(dest+nome,'WEBP',quality=92,method=6); arqs.append(nome)
open('arqs.txt','w').write('\n'.join(sorted(arqs)))
fs=[f'{nome0}.webp',f'{nome0}_feliz_fala.webp',f'{nome0}_bravo.webp',f'{nome0}_triste_pisca.webp',f'{nome0}_surpreso_fala.webp']
w,h=Image.open(dest+fs[0]).size
o=Image.new('RGB',(w*5,h))
for k,f in enumerate(fs):
  im=Image.open(dest+f); b=Image.new('RGBA',im.size,(255,0,255,255)); b.alpha_composite(im); o.paste(b.convert('RGB'),(k*w,0))
o.resize((w*5//2,h//2)).save('final.png'); print(w,h)
