import numpy as np, json, warnings
from PIL import Image
warnings.filterwarnings("ignore")
Image.MAX_IMAGE_PIXELS=None
O="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/ya"
d=np.load(O+"/mesh.npz"); co,lv,uv,ls,fn=d["co"],d["lv"],d["uv"],d["ls"],d["fn"]
fr=json.load(open(O+"/frame.json")); m,n,R,U=[np.array(fr[k]) for k in ("m","n","R","U")]
tex=np.array(Image.open(O+"/ya_tex_orig.jpeg").convert("RGB")); H,W,_=tex.shape
tri_l=ls[:,None]+np.arange(3)[None,:]; tri_v=lv[tri_l]; tri_uv=uv[tri_l]; cen=co[tri_v].mean(axis=1)
box=(cen[:,2]>0.45)&(cen[:,2]<0.95)&(cen[:,1]<0.05)&(cen[:,0]>-0.32)&(cen[:,0]<0.2)
B=np.where(box)[0]; print("faces in box",len(B))
c=tri_uv[B].mean(axis=1); xi=np.clip((c[:,0]*W).astype(int),0,W-1); yi=np.clip(((1-c[:,1])*H).astype(int),0,H-1); col=tex[yi,xi].astype(float)/255
r_=col[:,0];g_=col[:,1];b_=col[:,2]; lum=col@np.array([0.3,0.59,0.11]); sat=col.max(axis=1)-col.min(axis=1)
skin=(r_>g_+0.08)&(g_>b_)&(sat>0.18)&(lum<0.75)
dep=(cen[B]-m)@n; facing=fn[B]@n
ok=(facing>-0.05)&(dep>-0.09)&(dep<0.02)&(~skin)
seed=set(np.load(O+"/paper_faces.npy").tolist())
# adjacency via shared edges among B
e=np.concatenate([tri_v[B][:,[0,1]],tri_v[B][:,[1,2]],tri_v[B][:,[2,0]]]); e.sort(axis=1); fid=np.concatenate([np.arange(len(B))]*3)
key=e[:,0]*2000000+e[:,1]; o=np.argsort(key); key=key[o]; fid=fid[o]
same=np.where(key[1:]==key[:-1])[0]; nbr={}
for i in same:
    a,b=int(fid[i]),int(fid[i+1]); nbr.setdefault(a,[]).append(b); nbr.setdefault(b,[]).append(a)
pos={int(f):i for i,f in enumerate(B)}
inq=np.zeros(len(B),bool); stack=[pos[s] for s in seed if s in pos]
for s in stack: inq[s]=True
while stack:
    a=stack.pop()
    for b in nbr.get(a,()):
        if not inq[b] and ok[b]: inq[b]=True; stack.append(b)
sel=B[inq]; print("grown paper faces",len(sel),"(seed",len(seed),")")
pts=cen[sel]; r=(pts-m)@R; v=(pts-m)@U; dd=(pts-m)@n
print("r",r.min().round(3),r.max().round(3),"v",v.min().round(3),v.max().round(3),"depth",dd.min().round(3),dd.max().round(3))
np.save(O+"/paper_faces3.npy",sel)
# UV coverage image of selection (for visual check)
cov=np.zeros((H//8,W//8),np.uint8)
t=tri_uv[sel]; px=(t[:,:,0]*W/8).astype(int).clip(0,W//8-1); py=((1-t[:,:,1])*H/8).astype(int).clip(0,H//8-1)
for k in range(3): cov[py[:,k],px[:,k]]=255
ys,xs=np.where(cov>0); print("UV bbox px(8K)",xs.min()*8,xs.max()*8,ys.min()*8,ys.max()*8)
