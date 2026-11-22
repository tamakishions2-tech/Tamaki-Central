import numpy as np, json, sys
from PIL import Image, ImageDraw
from scipy import ndimage as nd
def achar(x, MN=190, FR=0.55, SZ=4):
    rgb=x[...,:3].astype(int); al=x[...,3]
    wh=(al>100)&(rgb.min(-1)>MN)&((rgb.max(-1)-rgb.min(-1))<35)
    lab,n=nd.label(wh); res=[]
    dark=(rgb.max(-1)<80)&(al>100)
    for i,sl in enumerate(nd.find_objects(lab),1):
        y0,y1=max(0,sl[0].start-3),sl[0].stop+3; x0,x1=max(0,sl[1].start-3),sl[1].stop+3
        m=lab[y0:y1,x0:x1]==i
        if m.sum()<SZ: continue
        ring=nd.binary_dilation(m,iterations=2)&~m
        f=dark[y0:y1,x0:x1][ring].mean()
        if f>=FR: res.append((i,f,int(m.sum()),(x0,y0,x1,y1)))
    return lab,res
if __name__=='__main__':
    d=json.load(open('indice.json')); tiles=[]
    for a in d:
        if a['nome']=='Tamaki': continue
        p=a['pasta'].replace('atores/',''); f=a['arquivos'][0]
        x=np.array(Image.open(f'{p}/{f}').convert('RGBA'))
        lab,res=achar(x)
        print(a['nome'],len(res))
        bg=np.zeros(x.shape[:2]+(3,)); bg[:]=[255,0,255]; al=x[...,3:]/255
        o=(x[...,:3]*al+bg*(1-al)).astype(np.uint8)
        for i,fr,s,(x0,y0,x1,y1) in res[:12]:
            cx,cy=(x0+x1)//2,(y0+y1)//2
            t=Image.fromarray(o).crop((cx-25,cy-25,cx+25,cy+25)).resize((100,100),Image.NEAREST)
            ImageDraw.Draw(t).text((2,2),f"{a['nome'][:5]}{fr:.1f}",fill=(0,255,0)); tiles.append(t)
    cols=16; rows=(len(tiles)+cols-1)//cols
    G=Image.new('RGB',(cols*102,rows*102),(40,40,40))
    for i,t in enumerate(tiles): G.paste(t,((i%cols)*102,(i//cols)*102))
    G.save(sys.argv[1])
