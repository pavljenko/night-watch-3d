import numpy as np, json, warnings
warnings.filterwarnings("ignore")
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
O="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/ya"
d=np.load(O+"/mesh.npz"); co,lv,uv,ls,fn=d["co"],d["lv"],d["uv"],d["ls"],d["fn"]
fr=json.load(open(O+"/frame.json")); m,n,R,U=[np.array(fr[k]) for k in ("m","n","R","U")]
tri=lv[ls[:,None]+np.arange(3)[None,:]]; cen=co[tri].mean(axis=1)
rr=(cen-m)@R; vv=(cen-m)@U; dp=(cen-m)@n; fc=fn@n
sel0=np.load(O+"/paper_faces3.npy"); r0,v0,d0=rr[sel0],vv[sel0],dp[sel0]
RB,VB=0.004,0.004; rl,rh=r0.min()-0.012,r0.max()+0.012; vl,vh=v0.min()-0.012,v0.max()+0.012
nr=int((rh-rl)/RB)+1; nv=int((vh-vl)/VB)+1
g=np.full((nv,nr),np.nan); acc={}
for a,b,c in zip(((v0-vl)/VB).astype(int),((r0-rl)/RB).astype(int),d0): acc.setdefault((a,b),[]).append(c)
for (a,b),vals in acc.items(): g[a,b]=np.max(vals)
# fill holes of outer grid (for inner lookups near hands)
for j in range(nv):
    row=g[j]; ok=np.isfinite(row)
    if ok.sum()>=2: g[j]=np.where(ok,row,np.interp(np.arange(nr),np.where(ok)[0],row[ok]))
for i in range(nr):
    col=g[:,i]; ok=np.isfinite(col)
    if ok.sum()>=2: g[:,i]=np.where(ok,col,np.interp(np.arange(nv),np.where(ok)[0],col[ok]))
inside=(rr>rl)&(rr<rh)&(vv>vl)&(vv<vh); I=np.where(inside)[0]
gi=g[((vv[I]-vl)/VB).astype(int).clip(0,nv-1),((rr[I]-rl)/RB).astype(int).clip(0,nr-1)]
delta=dp[I]-gi
tex=np.array(Image.open(O+"/ya_tex_orig.jpeg").convert("RGB").reduce(2)); H,W,_=tex.shape
uvc=uv[ls[I][:,None]+np.arange(3)[None,:]].mean(axis=1)
col=tex[((1-uvc[:,1])*H).astype(int).clip(0,H-1),(uvc[:,0]*W).astype(int).clip(0,W-1)].astype(float)/255
cand=(fc[I]<-0.1)&(delta>-0.018)&(delta<0.013)
print("candidates",cand.sum())
# colour clusters among candidates: paper-inner (orange-brown) vs skin (pinkish, lighter)
c=col[cand]; lum=c@[0.3,0.59,0.11]; rg=c[:,0]-c[:,1]; gb=c[:,1]-c[:,2]
print("lum pct",np.percentile(lum,[5,25,50,75,95]).round(2)," r-g",np.percentile(rg,[5,25,50,75,95]).round(2)," g-b",np.percentile(gb,[5,25,50,75,95]).round(2))
C=I[cand]
# connected components by shared edges; keep largest
e=np.concatenate([tri[C][:,[0,1]],tri[C][:,[1,2]],tri[C][:,[2,0]]]); e.sort(axis=1); fid=np.concatenate([np.arange(len(C))]*3)
key=e[:,0]*2000000+e[:,1]; o=np.argsort(key,kind='stable'); key=key[o]; fid=fid[o]
same=np.where(key[1:]==key[:-1])[0]
par=np.arange(len(C))
def f(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
for i in same:
    a,b=f(int(fid[i])),f(int(fid[i+1]))
    if a!=b: par[a]=b
roots=np.array([f(i) for i in range(len(C))]); u_,cnt=np.unique(roots,return_counts=True); order=np.argsort(-cnt)
print("components",len(u_),"top sizes",cnt[order[:8]])
keep=np.isin(roots,u_[order[:1]])
for j in order[1:8]:
    k=roots==u_[j]; print("  comp",cnt[j],"r",rr[C[k]].mean().round(3),"v",vv[C[k]].mean().round(3),"delta",delta[cand][k].mean().round(4),"rgb",(col[cand][k].mean(axis=0)*255).round(0))
inner=C[keep]
print("inner faces",len(inner),"r",rr[inner].min().round(3),rr[inner].max().round(3),"v",vv[inner].min().round(3),vv[inner].max().round(3))
print("inner mean rgb",(col[cand][keep].mean(axis=0)*255).round(0))
np.save(O+"/inner_faces.npy",inner)
