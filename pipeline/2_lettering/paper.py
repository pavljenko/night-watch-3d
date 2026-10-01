import numpy as np, json
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
O="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/ya"
d=np.load(O+"/mesh.npz"); co,lv,uv,ls,fn=d["co"],d["lv"],d["uv"],d["ls"],d["fn"]
tex=np.array(Image.open(O+"/ya_tex_orig.jpeg").convert("RGB")); H,W,_=tex.shape
F=len(ls); tri_l=ls[:,None]+np.arange(3)[None,:]; tri_v=lv[tri_l]; tri_uv=uv[tri_l]
# face colour: sample texture at triangle UV centroid
c=tri_uv.mean(axis=1); xi=np.clip((c[:,0]*W).astype(int),0,W-1); yi=np.clip(((1-c[:,1])*H).astype(int),0,H-1); col=tex[yi,xi].astype(float)/255
lum=col@np.array([0.3,0.59,0.11]); sat=col.max(axis=1)-col.min(axis=1)
cen=co[tri_v].mean(axis=1)
cand=(lum>0.42)&(sat<0.28)&(cen[:,2]>0.55)&(cen[:,2]<0.83)&(cen[:,1]<-0.02)&(fn[:,1]<-0.15)
print("candidate faces",cand.sum())
# largest connected component via shared vertices
idx=np.where(cand)[0]; par={int(i):int(i) for i in idx}
def f(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
vmap={}
for i in idx:
    for v in tri_v[i]:
        v=int(v)
        if v in vmap:
            ra,rb=f(int(i)),f(vmap[v])
            if ra!=rb: par[ra]=rb
        else: vmap[v]=int(i)
roots=np.array([f(int(i)) for i in idx]); u_,cnt=np.unique(roots,return_counts=True); big=u_[np.argmax(cnt)]
sel=idx[roots==big]; print("largest component faces",len(sel),"of",len(idx),"components",len(u_),"sizes top",sorted(cnt)[-5:])
pts=cen[sel]; area=0.5*np.linalg.norm(np.cross(co[tri_v[sel,1]]-co[tri_v[sel,0]],co[tri_v[sel,2]]-co[tri_v[sel,0]]),axis=1)
m=np.average(pts,axis=0,weights=area); Q=(pts-m)*np.sqrt(area)[:,None]; _,_,vt=np.linalg.svd(Q,full_matrices=False)
n=vt[2]; n=n if n[1]<0 else -n
Z=np.array([0,0,1.0]); U=Z-(Z@n)*n; U/=np.linalg.norm(U); R=np.cross(-n,U)
r=(pts-m)@R; v=(pts-m)@U; dd=(pts-m)@n
print("normal",n.round(3),"R",R.round(3),"U",U.round(3)); print("r range",r.min().round(3),r.max().round(3),"v range",v.min().round(3),v.max().round(3),"depth range",dd.min().round(3),dd.max().round(3))
# UV area covered -> texel density
uva=0.5*np.abs(np.cross(tri_uv[sel,1]-tri_uv[sel,0],tri_uv[sel,2]-tri_uv[sel,0]))
print("paper 3D area",area.sum().round(5),"model^2 ; UV area",uva.sum().round(6),"-> texels",int(uva.sum()*W*H),"; texels per model unit",round(float(np.sqrt(uva.sum()*W*H/area.sum())),0))
json.dump({"m":m.tolist(),"n":n.tolist(),"R":R.tolist(),"U":U.tolist()},open(O+"/frame.json","w")); np.save(O+"/paper_faces.npy",sel)
