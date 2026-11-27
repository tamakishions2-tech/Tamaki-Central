# limpa_rosto.py <pasta_ator> <saida> [opções json]
# 1) pele da expressão com a mesma cor da pele do corpo (tira manchas e mudança de cor)
# 2) apaga linhas de queixo duplas e rebarbas perto da borda de baixo do rosto
import sys, os, json, numpy as np, cv2
from PIL import Image
from scipy import ndimage as nd
pasta, out = sys.argv[1], sys.argv[2]; op = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
os.makedirs(out, exist_ok=True)
fs = sorted(f for f in os.listdir(pasta) if f.endswith('.webp'))
base_nome = op.get('base') or [f for f in fs if '_' not in f][0]
L = lambda f: np.asarray(Image.open(f'{pasta}/{f}').convert('RGBA')).astype(np.float32)
Fr = {f: L(f) for f in fs}; N = Fr[base_nome]; H, W = N.shape[:2]
lab = lambda a: cv2.cvtColor(np.clip(a[..., :3], 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
D = np.zeros((H, W), bool)
for a in Fr.values(): D |= np.abs(a - N).sum(-1) > op.get('dif', 30)
D &= N[..., 3] > 200
D = nd.binary_closing(D, iterations=4); D = nd.binary_fill_holes(D); D = nd.binary_opening(D, iterations=2)
lb, n = nd.label(D); sz = nd.sum(D, lb, range(1, n + 1)); F = lb == (1 + int(np.argmax(sz)))
if 'caixa' in op: x0_, y0_, x1_, y1_ = op['caixa']; F[:y0_] = 0; F[y1_:] = 0; F[:, :x0_] = 0; F[:, x1_:] = 0
F = nd.binary_fill_holes(nd.binary_dilation(F, iterations=op.get('dil', 4))) & (N[..., 3] > 200)
NL = lab(N); px = NL[F]
q = (px // 6).astype(int); u, c = np.unique(q, axis=0, return_counts=True); pk = u[c.argmax()] * 6 + 3
pele = px[np.linalg.norm(px - pk, axis=1) < 14].mean(0)
TP = op.get('tp', 16)   # até onde ainda é pele
# rosto inteiro (pele do corpo ligada ao rosto que muda)
def rosto_de(a):
    S = (np.linalg.norm(lab(a) - pele, axis=2) < op.get('tr', 26)) & (a[..., 3] > 200)
    S = nd.binary_opening(S, iterations=1)
    lb, n = nd.label(S | F); k = np.bincount(lb[F].ravel()); k[0] = 0
    R = lb == k.argmax(); return nd.binary_fill_holes(R)
R = rosto_de(N)
ys, xs = np.nonzero(R); ry0, ry1 = ys.min(), ys.max()
distR = nd.distance_transform_edt(R)
fy0, fy1 = np.nonzero(F)[0].min(), np.nonzero(F)[0].max()
corte = fy0 + (fy1 - fy0) * op.get('meio', .55)    # só da metade do rosto para baixo (queixo e bochechas)
distF = nd.distance_transform_edt(F)
fxs_ = np.nonzero(F)[1]; cx_, lw_ = (fxs_.min() + fxs_.max()) / 2, (fxs_.max() - fxs_.min())
xx_ = np.arange(W)[None, :]; centro_ = (np.abs(xx_ - cx_) < lw_ * .2) & (np.arange(H)[:, None] > corte)
def boca_dist(a_):
    fe_ = (np.linalg.norm(lab(a_) - pele, axis=2) > op.get('tb', 26)) & F
    lb_, n_ = nd.label(fe_, structure=np.ones((3, 3))); mb = 99.0
    for i_, sl_ in enumerate(nd.find_objects(lb_), 1):
        c_ = lb_[sl_] == i_; yy_, xx_ = np.nonzero(c_); yy_ = yy_ + sl_[0].start; xx_ = xx_ + sl_[1].start
        if len(yy_) < 12 or distF[yy_, xx_].min() < 2.5 or not centro_[yy_, xx_].any(): continue
        mb = min(mb, float(distF[yy_, xx_][centro_[yy_, xx_]].min()))
    return mb
def faixa_de(a_):
    b_ = op.get('borda', 14) if op.get('boca_livre') else min(op.get('borda', 14), boca_dist(a_) - 3)
    lado = ~(np.abs(np.arange(W)[None, :] - cx_) < lw_ * .2)
    lim = np.where(lado, op.get('lados', 22), max(b_, 0))
    fx = F & (distF <= lim) & (np.arange(H)[:, None] > corte)
    return fx, b_
# traços do quadro normal que não encostam na borda (olhos, boca): nunca vão para as outras expressões
feN = (np.linalg.norm(lab(N) - pele, axis=2) > op.get('tb', 26)) & F
lbN, _ = nd.label(feN, structure=np.ones((3, 3))); NF = np.zeros_like(F)
for i_, sl_ in enumerate(nd.find_objects(lbN), 1):
    c_ = lbN[sl_] == i_; yy_, xx_ = np.nonzero(c_); yy_ = yy_ + sl_[0].start; xx_ = xx_ + sl_[1].start
    lg_ = xx_.max() - xx_.min() + 1; fn_ = len(yy_) / max(lg_, yy_.max() - yy_.min() + 1) < op.get('fino', 7)
    eh_queixo = fn_ and lg_ > np.ptp(np.nonzero(F)[1]) * .3 and yy_.mean() > fy0 + (fy1 - fy0) * .45
    pequeno_ = lg_ < np.ptp(np.nonzero(F)[1]) * .45 and (yy_.max() - yy_.min()) < (fy1 - fy0) * .35
    if len(yy_) >= 8 and not eh_queixo and pequeno_ and (distF[yy_, xx_].min() >= 2.5 or yy_.mean() < fy0 + (fy1 - fy0) * .62): NF[yy_, xx_] = 1
NF = nd.binary_dilation(NF, iterations=4)
faixa, borda = faixa_de(N)
print('faixa do queixo no normal:', round(borda, 1))
def linhas_ruins(a):
    l = lab(a)[..., 0]
    esc = (l < op.get('lmax', 110)) & faixa
    grosso = nd.binary_dilation(nd.binary_opening(esc, iterations=op.get('grosso', 2)), iterations=2)
    fino = esc & ~grosso
    lb, n = nd.label(fino, structure=np.ones((3, 3))); sz = nd.sum(fino, lb, range(1, n + 1))
    return np.isin(lb, 1 + np.nonzero(sz >= op.get('min', 5))[0])
Nfix = N.copy()
if op.get('limpa_normal'):
    X0 = nd.binary_dilation(linhas_ruins(N), iterations=1) & F
    Nfix[..., :3] = cv2.inpaint(np.clip(N[..., :3], 0, 255).astype(np.uint8), X0.astype(np.uint8) * 255, 4, cv2.INPAINT_TELEA).astype(np.float32)
bonito = {}
for f, a in Fr.items():
    o = a.copy()
    # 1) cor: diferença de pele (expressão - corpo) suavizada e tirada dentro do rosto que muda
    al = lab(a); d = np.linalg.norm(al - pele, axis=2)
    S = (d < TP) & F
    Sb = nd.binary_erosion(S, iterations=1)
    ref = lab(N)   # pele do corpo perto: usa o quadro normal fora do F e a pele média dentro
    alvo = np.where(F[..., None], pele[None, None], ref)
    w = Sb.astype(np.float32)
    dif = (al - alvo) * w[..., None]
    s = op.get('sig', 10)
    num = np.stack([cv2.GaussianBlur(dif[..., k], (0, 0), s) for k in range(3)], -1); den = cv2.GaussianBlur(w, (0, 0), s)[..., None]
    corr = num / np.maximum(den, 1e-3)
    corr[..., 0] *= op.get('luz', .7)   # mantém um pouco da sombra/blush
    fade = np.clip(cv2.GaussianBlur(F.astype(np.float32), (0, 0), 2), 0, 1)[..., None]
    nl = al - corr * fade * op.get('forca', 1.0)
    rgb = cv2.cvtColor(np.clip(nl, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
    o[..., :3] = np.where(F[..., None], rgb, a[..., :3])
    # 2) queixo: a faixa perto da borda de baixo vem do quadro normal (um contorno só, igual em todas)
    X, bq = faixa_de(a); X = X & ~NF
    # traços desta expressão que não encostam na borda (boca, bico, olhos): protegidos
    fe = (np.linalg.norm(lab(a) - pele, axis=2) > op.get('tb', 26)) & F
    lbm, nm = nd.label(fe, structure=np.ones((3, 3))); PM = np.zeros_like(F)
    for i, sl in enumerate(nd.find_objects(lbm), 1):
        cc = lbm[sl] == i; yy, xx = np.nonzero(cc); yy = yy + sl[0].start; xx = xx + sl[1].start
        larg = xx.max() - xx.min() + 1; fino = len(yy) / max(larg, yy.max() - yy.min() + 1) < op.get('fino', 7)
        queixo = fino and larg > lw_ * .3 and yy.mean() > corte
        boca = larg < lw_ * .6 and (yy.max() - yy.min()) < (fy1 - fy0) * .4 and abs(xx.mean() - cx_) < lw_ * .3
        if len(yy) >= 8 and distF[yy, xx].min() >= op.get('toca', 2.5) and not queixo and boca: PM[yy, xx] = 1
    X &= ~nd.binary_dilation(PM, iterations=3)
    pena = np.clip(cv2.GaussianBlur(X.astype(np.float32), (0, 0), op.get('pena', 1.5)), 0, 1)[..., None]
    if f != base_nome: o[..., :3] = o[..., :3] * (1 - pena) + Nfix[..., :3] * pena
    else: o[..., :3] = Nfix[..., :3]
    bonito[f] = int(X.sum())
    if op.get('debug') and op['debug'] in f: Image.fromarray((X*255).astype(np.uint8)).save(f'{out}/_X.png'); Image.fromarray((PM*255).astype(np.uint8)).save(f'{out}/_PM.png'); Image.fromarray((NF*255).astype(np.uint8)).save(f'{out}/_NF.png'); Image.fromarray((faixa_de(a)[0]*255).astype(np.uint8)).save(f'{out}/_FX.png')
    Image.fromarray(np.clip(o, 0, 255).astype(np.uint8)).save(f'{out}/{f[:-5]}.png')
x0, x1 = np.nonzero(R)[1].min(), np.nonzero(R)[1].max()
json.dump({'F': [int(x0), int(ry0), int(x1), int(ry1)], 'apagado': bonito}, open(f'{out}/info.json', 'w'))
Image.fromarray((R * 255).astype(np.uint8)).save(f'{out}/_rosto.png'); Image.fromarray((F * 255).astype(np.uint8)).save(f'{out}/_F.png')
print('ok', base_nome, 'pele', pele.round(1), 'apagado normal', bonito[base_nome])
