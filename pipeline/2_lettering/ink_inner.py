# Text on the INNER side of the scroll (facing the reader), mirrored so it reads from the figure's eyes.
# The inner layer is Tripo-tinted orange-brown -> recolour it to paper tone (keeping its luminance detail), then ink.
import numpy as np, json, warnings, os, time
from PIL import Image, ImageFilter
warnings.filterwarnings("ignore"); Image.MAX_IMAGE_PIXELS=None
O="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/ya"
FILL_H=float(os.environ.get("FILL_H","0.76")); FILL_W=float(os.environ.get("FILL_W","0.78")); INK_K=float(os.environ.get("INK_K","0.88"))
PAPER=np.array([float(x) for x in os.environ.get("PAPER","238,201,168").split(",")],np.float32); FEATHER=float(os.environ.get("FEATHER","0.004"))
VSHIFT=float(os.environ.get("VSHIFT","0.0")); USHIFT=float(os.environ.get("USHIFT","0.0")); OUT=os.environ.get("OUT",O+"/ya_basecolor_svitok.jpg")
T0=time.time()
d=np.load(O+"/mesh.npz"); co,lv,uv,ls=d["co"],d["lv"],d["uv"],d["ls"]
fr=json.load(open(O+"/frame.json")); m,n,R,U=[np.array(fr[k]) for k in ("m","n","R","U")]
sel=np.load(O+"/inner_faces2.npy"); core_f=np.load(O+"/inner_faces.npy")
tri_l=ls[sel][:,None]+np.arange(3)[None,:]; tv=lv[tri_l]; tuv=uv[tri_l]
verts=np.unique(tv); vid=np.full(len(co),-1,np.int64); vid[verts]=np.arange(len(verts)); P=co[verts]
r=(P-m)@R; v=(P-m)@U; dpt=(P-m)@n
incore=np.zeros(len(P),bool); incore[vid[np.unique(lv[ls[core_f][:,None]+np.arange(3)[None,:]])]]=True
# --- feather weight: distance to selection boundary
e=np.concatenate([tv[:,[0,1]],tv[:,[1,2]],tv[:,[2,0]]]); e.sort(axis=1); key=e[:,0]*2000000+e[:,1]
uk,cnt=np.unique(key,return_counts=True); bk=uk[cnt==1]; bverts=np.unique(np.concatenate([bk//2000000,bk%2000000]))
BP=co[bverts]; dist=np.full(len(P),np.inf)
for i in range(0,len(P),4000):
    dd=np.sqrt(((P[i:i+4000,None,:]-BP[None,:,:])**2).sum(-1)).min(axis=1); dist[i:i+4000]=dd
wv=np.clip(dist/FEATHER,0,1); wv=wv*wv*(3-2*wv)
print("inner verts",len(P),"boundary verts",len(bverts),"fully-weighted",int((wv>0.999).sum()))
# --- height-field unroll of the inner surface along R
RB=0.001; VB=0.004
r_lo,r_hi=r[incore].min()-0.005,r[incore].max()+0.005; v_lo,v_hi=v[incore].min()-0.005,v[incore].max()+0.005
nr=int((r_hi-r_lo)/RB)+1; nv=int((v_hi-v_lo)/VB)+1
ri=((r-r_lo)/RB).astype(int).clip(0,nr-1); vi_=((v-v_lo)/VB).astype(int).clip(0,nv-1)
grid=np.full((nv,nr),np.nan); lin=vi_*nr+ri; o_=np.argsort(lin); ls_=lin[o_]; bnd=np.r_[0,np.where(np.diff(ls_))[0]+1,len(ls_)]
for a,b in zip(bnd[:-1],bnd[1:]):
    ids=o_[a:b]; ids=ids[incore[ids]]
    if len(ids): grid.flat[ls_[a]]=np.median(dpt[ids])
for j in range(nv):
    row=grid[j]; g=np.isfinite(row)
    if g.sum()>=2: grid[j]=np.interp(np.arange(nr),np.where(g)[0],row[g])
for i in range(nr):
    col=grid[:,i]; g=np.isfinite(col)
    if g.sum()>=2: grid[:,i]=np.interp(np.arange(nv),np.where(g)[0],col[g])
grid=np.nan_to_num(grid,nan=float(np.nanmedian(grid)))
kr=np.ones(7)/7; kv=np.ones(3)/3
grid=np.apply_along_axis(lambda x: np.convolve(np.pad(x,3,mode='edge'),kr,'valid'),1,grid)
grid=np.apply_along_axis(lambda x: np.convolve(np.pad(x,1,mode='edge'),kv,'valid'),0,grid)
slope=np.gradient(grid,RB,axis=1); ds=np.sqrt(1+slope**2)*RB
ic=int(nr/2); U_=np.cumsum(ds,axis=1); U_=U_-U_[:,[ic]]
def lookup(rr,vv):
    x=(rr-r_lo)/RB; y=(vv-v_lo)/VB; x0=np.clip(np.floor(x).astype(int),0,nr-2); y0=np.clip(np.floor(y).astype(int),0,nv-2); fx=np.clip(x-x0,0,1); fy=np.clip(y-y0,0,1)
    return U_[y0,x0]*(1-fx)*(1-fy)+U_[y0,x0+1]*fx*(1-fy)+U_[y0+1,x0]*(1-fx)*fy+U_[y0+1,x0+1]*fx*fy
u=-lookup(r,v)          # reader's right = -R  -> mirrored relative to the outer side
print("inner unroll grid",nr,"x",nv,"max slope",round(float(np.abs(slope).max()),2),"u",round(float(u.min()),4),round(float(u.max()),4))
core=incore&(wv>0.5)
ul,uh=np.percentile(u[core],[3,97]); vl,vh=np.percentile(v[core],[3,97])
uc,vc=(ul+uh)/2+USHIFT,(vl+vh)/2+VSHIFT; aw,ah=(uh-ul)*FILL_W,(vh-vl)*FILL_H
txt=Image.open(O+"/../s3/Цитата_на_свиток_crop.png").convert("RGBA"); asp=txt.width/txt.height
bh=ah; bw=bh*asp
if bw>aw: bw=aw; bh=bw/asp
print(f"inner paper u[{ul:.4f},{uh:.4f}] v[{vl:.4f},{vh:.4f}] -> block {bw:.4f} x {bh:.4f} at ({uc:.4f},{vc:.4f})")
s=(u-(uc-bw/2))/bw; t=(v-(vc-bh/2))/bh; ST=np.stack([s,t],axis=1)
tex=np.array(Image.open(O+"/ya_tex_orig.jpeg").convert("RGB")); H,W,_=tex.shape
uva=0.5*np.abs((tuv[:,1,0]-tuv[:,0,0])*(tuv[:,2,1]-tuv[:,0,1])-(tuv[:,2,0]-tuv[:,0,0])*(tuv[:,1,1]-tuv[:,0,1])).sum()
a3=0.5*np.linalg.norm(np.cross(co[tv[:,1]]-co[tv[:,0]],co[tv[:,2]]-co[tv[:,0]]),axis=1).sum(); dens=np.sqrt(uva*W*H/a3)
th=int(bh*dens*1.6); tw=int(th*asp); al=np.array(txt.split()[3].resize((tw,th),Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32)/255
print("texel density",int(dens),"/unit; text raster",tw,"x",th)
def sample(ss,tt):
    x=ss*(tw-1); y=(1-tt)*(th-1); x0=np.floor(x).astype(int); y0=np.floor(y).astype(int); fx=x-x0; fy=y-y0
    inside=(x0>=0)&(y0>=0)&(x0<tw-1)&(y0<th-1); x0c=np.clip(x0,0,tw-2); y0c=np.clip(y0,0,th-2)
    val=(al[y0c,x0c]*(1-fx)*(1-fy)+al[y0c,x0c+1]*fx*(1-fy)+al[y0c+1,x0c]*(1-fx)*fy+al[y0c+1,x0c+1]*fx*fy)
    return np.where(inside,val,0.0)
e3=np.linalg.norm(co[tv[:,1]]-co[tv[:,0]],axis=1)+np.linalg.norm(co[tv[:,2]]-co[tv[:,1]],axis=1)+np.linalg.norm(co[tv[:,0]]-co[tv[:,2]],axis=1)
tp=tuv*[W,H]; e2=np.linalg.norm(tp[:,1]-tp[:,0],axis=1)+np.linalg.norm(tp[:,2]-tp[:,1],axis=1)+np.linalg.norm(tp[:,0]-tp[:,2],axis=1)
ratio=e2/np.maximum(e3,1e-9); rmed=np.median(ratio); bad=(ratio>2.5*rmed)|(ratio<rmed/2.5); print("UV-stretched triangles (no ink)",int(bad.sum()))
Wmap=np.zeros((H,W),np.float32); Amap=np.zeros((H,W),np.float32); cov=np.zeros((H,W),bool); DIL=1.5
incore_f=np.isin(sel,core_f)
def tri_pix(k,dil):
    q=tuv[k]*[W,H]; q[:,1]=H-q[:,1]
    x0=max(int(np.floor(q[:,0].min()-dil)),0); x1=min(int(np.ceil(q[:,0].max()+dil)),W-1); y0=max(int(np.floor(q[:,1].min()-dil)),0); y1=min(int(np.ceil(q[:,1].max()+dil)),H-1)
    xs,ys=np.meshgrid(np.arange(x0,x1+1)+0.5,np.arange(y0,y1+1)+0.5)
    (ax,ay),(bx,by),(cx,cy)=q; den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
    if abs(den)<1e-9: return None
    l1=((by-cy)*(xs-cx)+(cx-bx)*(ys-cy))/den; l2=((cy-ay)*(xs-cx)+(ax-cx)*(ys-cy))/den; l3=1-l1-l2
    area2=abs(den); ha=area2/max(np.hypot(bx-cx,by-cy),1e-9); hb=area2/max(np.hypot(ax-cx,ay-cy),1e-9); hc=area2/max(np.hypot(ax-bx,ay-by),1e-9)
    od=np.maximum(np.maximum(-l1*ha,-l2*hb),-l3*hc)          # pixel distance outside the triangle (<=0 inside)
    L1,L2=np.clip(l1,0,1),np.clip(l2,0,1); L3=np.clip(1-L1-L2,0,1); sm=np.maximum(L1+L2+L3,1e-9)
    return (ys-0.5).astype(int),(xs-0.5).astype(int),od,L1/sm,L2/sm,L3/sm
def shade(k,Y,X,msk,L1,L2,L3,only_uncovered):
    ia,ib,ic=vid[tv[k]]
    if only_uncovered: msk=msk&~cov[Y,X]
    if not msk.any(): return
    Y,X,L1,L2,L3=Y[msk],X[msk],L1[msk],L2[msk],L3[msk]
    w=L1*wv[ia]+L2*wv[ib]+L3*wv[ic]; Wmap[Y,X]=np.maximum(Wmap[Y,X],w)
    if bad[k] or not incore_f[k]: return
    stv=ST[[ia,ib,ic]]
    if stv[:,0].max()<0 or stv[:,0].min()>1 or stv[:,1].max()<0 or stv[:,1].min()>1: return
    ss=L1*stv[0,0]+L2*stv[1,0]+L3*stv[2,0]; tt=L1*stv[0,1]+L2*stv[1,1]+L3*stv[2,1]
    a=sample(ss,tt)*np.clip(w*1.5,0,1); Amap[Y,X]=np.maximum(Amap[Y,X],a)
for k in range(len(sel)):
    r_=tri_pix(k,0)
    if r_ is None: continue
    Y,X,od,L1,L2,L3=r_; msk=od<=0.02
    shade(k,Y,X,msk,L1,L2,L3,False)
    cov[Y[msk],X[msk]]=True
for k in range(len(sel)):
    r_=tri_pix(k,DIL)
    if r_ is None: continue
    Y,X,od,L1,L2,L3=r_; msk=(od>0.02)&(od<=DIL)
    shade(k,Y,X,msk,L1,L2,L3,True)
print("covered texels",int(cov.sum()))
orig=tex.astype(np.float32)
Yl=orig@np.array([0.2126,0.7152,0.0722],np.float32)
inside=Wmap>0.9; Ymed=float(np.median(Yl[inside])); print("inner texels",int((Wmap>0.01).sum()),"median luminance",round(Ymed,1),"mean rgb",orig[inside].mean(axis=0).round(0))
f=np.clip((np.maximum(Yl,1)/Ymed)**0.8,0.6,1.15)[:,:,None]
paper=PAPER[None,None,:]*f
Wm=Wmap[:,:,None]; rec=orig*(1-Wm)+paper*Wm
ink=np.array([28,20,14],np.float32); A=(Amap*INK_K)[:,:,None]; res=rec*(1-A)+ink*A
print("texels inked",int((Amap>0.05).sum()),f"{time.time()-T0:.0f}s")
Image.fromarray(res.clip(0,255).astype(np.uint8)).save(OUT,quality=95)
np.save(O+"/inner_masks.npy",np.stack([Wmap[::4,::4],Amap[::4,::4]]))
print("saved",OUT.split('/')[-1],os.path.getsize(OUT)//1024,"KB")
