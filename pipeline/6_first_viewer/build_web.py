import json, os, struct, base64, math
C="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/cmp"
OUT="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка/сжатая_сцена_200k_2.5K"; NAME="Ночной_дозор_200k_2.5K"
W=C+"/web"; os.makedirs(W+"/scene",exist_ok=True)
for f in os.listdir(W+"/scene"): os.remove(W+"/scene/"+f)
glb=open(f"{OUT}/{NAME}_webp.glb","rb").read() if os.path.exists(f"{OUT}/{NAME}_webp.glb") else open(f"{OUT}/{NAME}.glb","rb").read()
import hashlib
H=hashlib.sha1(glb).hexdigest()[:8]
jl=struct.unpack_from("<I",glb,12)[0]; js=json.loads(glb[20:20+jl]); bin0=20+jl+8
prims=sum(1 for m in js["meshes"] for p in m["primitives"] if "KHR_draco_mesh_compression" in p.get("extensions",{}))
models=len([n for n in js["nodes"] if "mesh" in n]); bvs=js["bufferViews"]
imgs=sorted(((bin0+bvs[im["bufferView"]].get("byteOffset",0), bvs[im["bufferView"]]["byteLength"], im.get("mimeType","image/jpeg")) for im in js.get("images",[])))
# images -> .jpg files (exact bytes); everything else -> one base64 text stream
images=[]; rest_ranges=[]; cur=0
for i,(off,ln,mt) in enumerate(imgs):
    if off>cur: rest_ranges.append([cur,off-cur])
    fn=f"scene/{H}_tex_{i:02d}."+("webp" if mt=="image/webp" else "jpg"); open(f"{W}/{fn}","wb").write(glb[off:off+ln]); images.append({"url":fn,"offset":off,"size":ln}); cur=off+ln
if cur<len(glb): rest_ranges.append([cur,len(glb)-cur])
rest=b"".join(glb[o:o+l] for o,l in rest_ranges); b64=base64.b64encode(rest)
n=math.ceil(len(b64)/12_000_000); step=math.ceil(len(b64)/n/4)*4; rest_files=[]
for k in range(n):
    fn=f"scene/{H}_geo_{k}.txt"; chunk=b64[k*step:(k+1)*step]; open(f"{W}/{fn}","wb").write(chunk); rest_files.append({"url":fn,"size":len(chunk)})
L=json.load(open(C+"/scene_lights.json"))
tune=json.load(open(C+"/tune.json"))
layout={"total":len(glb),"images":images,"rest":{"files":rest_files,"ranges":rest_ranges,"bytes":len(rest)}}
data={"layout":layout,"lights":L["lights"],"camera":L["camera"],"blocker":L["blocker"],"exposure":L["exposure"],"stats":{"meshes":prims,"images":len(images),"models":models,"glb":len(glb)},"tune":tune}
t=open(C+"/viewer_template.html",encoding="utf-8").read()
for k in ("draco-wrapper","draco-js","draco-wasm"): t=t.replace("__%s__"%k.upper().replace("-","_"),open(f"{C}/{k}.txt",encoding="utf-8").read())
t=t.replace("__SCENE_DATA__",json.dumps(data,ensure_ascii=False).replace("</","<\\/"))
open(W+"/index.html","w",encoding="utf-8").write(t)
dl=sum(i["size"] for i in images)+sum(f["size"] for f in rest_files)
print(f"GLB {len(glb)/1e6:.1f} MB -> {len(images)} jpg ({sum(i['size'] for i in images)/1e6:.1f} MB) + {len(rest_files)} txt ({sum(f['size'] for f in rest_files)/1e6:.1f} MB b64 of {len(rest)/1e6:.1f} MB); download {dl/1e6:.1f} MB; page {os.path.getsize(W+'/index.html')/1e6:.2f} MB; lights {len(L['lights'])}")
