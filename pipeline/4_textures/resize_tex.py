import json, glob, os, re, hashlib
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
C="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/cmp"
OUT="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка/сжатая_сцена_200k_2.5K/textures"
SIZE=2560
mapf=C+"/texmap.json"; texmap=json.load(open(mapf)) if os.path.exists(mapf) else {}
hashes={v["sha"]:v["out"] for v in texmap.values() if "sha" in v}
for jf in sorted(glob.glob(C+"/done/*.json")):
    job=json.load(open(jf))
    for rec in job["images"]:
        key=rec["image"]
        if key in texmap: continue
        data=open(rec["src"],"rb").read(); sha=hashlib.sha1(data).hexdigest()
        if sha in hashes: texmap[key]={"out":hashes[sha],"sha":sha,"colorspace":rec["colorspace"]}; continue
        base=re.sub(r"\.(jpe?g|png)(\.\d+)?$","",key,flags=re.I); base=re.sub(r"\.\d+$","",base)
        out=f"{base}_{SIZE}.jpg"
        im=Image.open(rec["src"]); w,h=im.size
        im=im.convert("RGB")
        if max(w,h)>SIZE: im=im.resize((SIZE,round(h*SIZE/w)) if w>=h else (round(w*SIZE/h),SIZE),Image.LANCZOS)
        q=95 if rec["colorspace"]!="sRGB" else 85
        im.save(OUT+"/"+out,"JPEG",quality=q,optimize=True)
        texmap[key]={"out":out,"sha":sha,"colorspace":rec["colorspace"],"src_size":[w,h]}; hashes[sha]=out
        print(f"{key[:44]:44s} {w}x{h} -> {out} {os.path.getsize(OUT+'/'+out)//1024} KB",flush=True)
json.dump(texmap,open(mapf,"w"),ensure_ascii=False,indent=1)
print("textures mapped",len(texmap),"files",len(set(v['out'] for v in texmap.values())))
