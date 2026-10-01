import numpy as np, json, warnings
warnings.filterwarnings("ignore")
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
O="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/ya"
d=np.load(O+"/mesh.npz"); co,lv,uv,ls,fn=d["co"],d["lv"],d["uv"],d["ls"],d["fn"]
fr=json.load(open(O+"/frame.json")); m,n,R,U=[np.array(fr[k]) for k in ("m","n","R","U")]
tri=lv[ls[:,None]+np.arange(3)[None,:]]; cen=co[tri].mean(axis=1)
rr=(cen-m)@R; vv=(cen-m)@U; dp=(cen-m)@n; fc=fn@n
seed=np.load(O+"/inner_faces.npy"); outer=np.load(O+"/paper_faces3.npy")
box=np.where((rr>-0.14)&(rr<0.16)&(vv>-0.17)&(vv<0.07)&(dp>-0.09)&(dp<0.03))[0]
tex=np.array(Image.open(O+"/ya_tex_orig.jpeg").convert("RGB")); H,W,_=tex.shape
q=uv[ls[box][:,None]+np.arange(3)[None,:]]; cs=[]
for ww in ([1/3,1/3,1/3],[0.6,0.2,0.2],[0.2,0.6,0.2],[0.2,0.2,0.6]):
    p_=(q*np.array(ww)[None,:,None]).sum(1); cs.append(tex[((1-p_[:,1])*H).astype(int).clip(0,H-1),(p_[:,0]*W).astype(int).clip(0,W-1)].astype(float))
col=np.mean(cs,axis=0)/255
lum=col@[0.2126,0.7152,0.0722]; rg=col[:,0]-col[:,1]; gb=col[:,1]-col[:,2]
gch=col[:,1]/np.maximum(col.sum(1),1e-6)
brown=(lum<0.62)&(rg>0.17)&(gb>0.14)&(gch>0.29)
ok=brown&(fc[box]<0.35)&~np.isin(box,outer)
pos=np.full(len(fn),-1); pos[box]=np.arange(len(box))
e=np.concatenate([tri[box][:,[0,1]],tri[box][:,[1,2]],tri[box][:,[2,0]]]); e.sort(axis=1); fid=np.concatenate([np.arange(len(box))]*3)
key=e[:,0]*2000000+e[:,1]; o=np.argsort(key,kind='stable'); key=key[o]; fid=fid[o]
same=np.where(key[1:]==key[:-1])[0]; nb={}
for i in same:
    a,b=int(fid[i]),int(fid[i+1]); nb.setdefault(a,[]).append(b); nb.setdefault(b,[]).append(a)
inq=np.zeros(len(box),bool); st=[int(pos[s]) for s in seed if pos[s]>=0]
for s in st: inq[s]=True
while st:
    a=st.pop()
    for b in nb.get(a,()):
        if not inq[b] and ok[b]: inq[b]=True; st.append(b)
grown=box[inq]; add=np.setdiff1d(grown,seed)
print("seed",len(seed),"grown",len(grown),"added",len(add))
if len(add):
    print(" added r",np.percentile(rr[add],[1,50,99]).round(3),"v",np.percentile(vv[add],[1,50,99]).round(3),"dp",np.percentile(dp[add],[1,50,99]).round(3),"fc",np.percentile(fc[add],[1,50,99]).round(2))
    print(" added mean rgb",(col[inq&~np.isin(box,seed)].mean(axis=0)*255).round(0))
np.save(O+"/inner_faces2.npy",grown); np.save(O+"/inner_added.npy",add)
