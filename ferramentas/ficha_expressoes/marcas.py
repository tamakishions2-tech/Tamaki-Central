# marcas.py <pasta_saida> <base.png> [verde] : copia as marcas douradas do normal para todos os quadros (só sobre pele) e, com "verde", pinta o branco dos olhos verdes
import sys, os, glob, numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
d, base = sys.argv[1], sys.argv[2]; verde = 'verde' in sys.argv[3:]
lab = lambda a: cv2.cvtColor(a[..., :3].astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
N = np.asarray(Image.open(f'{d}/{base}').convert('RGBA')).astype(np.float32); NL = lab(N)
F = np.asarray(Image.open(f'{d}/_F.png')) > 0
Fd = nd.binary_dilation(F, iterations=2)
px = NL[F]; q = (px // 6).astype(int); u, c = np.unique(q, axis=0, return_counts=True); pk = u[c.argmax()] * 6 + 3
pele = px[np.linalg.norm(px - pk, axis=1) < 14].mean(0)
ouro = (NL[..., 0] > pele[0] + 10) & (NL[..., 2] > pele[2] + 4) & (NL[..., 1] < pele[1] + 3) & Fd

lb_, n_ = nd.label(ouro, structure=np.ones((3,3))); sz_ = nd.sum(ouro, lb_, range(1, n_+1)); ouro = np.isin(lb_, 1 + np.nonzero(sz_ >= 4)[0])
ouro = nd.binary_dilation(ouro, iterations=1) & Fd
print('marcas:', int(ouro.sum()), 'px')
al = cv2.GaussianBlur(ouro.astype(np.float32), (0, 0), .7)
for f in sorted(glob.glob(f'{d}/*.png')):
    if os.path.basename(f).startswith('_'): continue
    A = np.asarray(Image.open(f).convert('RGBA')).astype(np.float32); AL = lab(A)
    pode = (np.linalg.norm(AL - pele, axis=2) < 30) | ((AL[..., 0] > pele[0] + 5) & (AL[..., 2] > pele[2]))   # pele ou marca torta
    pode = pode & Fd
    w = (al * pode)[..., None]
    A[..., :3] = A[..., :3] * (1 - w) + N[..., :3] * w
    if verde:
        AL = lab(A); g = (AL[..., 1] < 112) & (AL[..., 0] > 60) & F
        lb, n = nd.label(nd.binary_closing(g, iterations=2))
        for i, sl in enumerate(nd.find_objects(lb), 1):
            cc = lb == i
            if cc.sum() < 40: continue
            ys, xs = np.nonzero(cc); h = cv2.convexHull(np.stack([xs, ys], 1).astype(np.int32)); C = np.zeros(F.shape, np.uint8); cv2.fillPoly(C, [h], 1)
            C = C.astype(bool); cor = np.median(A[..., :3][cc & (AL[..., 1] < 112)], axis=0)
            branco = C & (AL[..., 0] > 150) & (np.abs(AL[..., 1] - 128) < 14) & (np.abs(AL[..., 2] - 128) < 22)
            branco &= nd.binary_erosion(C, iterations=1)
            A[..., :3][branco] = cor
    Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)).save(f)
print('ok')
