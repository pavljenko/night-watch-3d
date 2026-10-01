import json, glob, os, time
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
Image.MAX_IMAGE_PIXELS=None
C="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/cmp"
OUT="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка/сжатая_сцена_200k_2.5K/textures"
texmap=json.load(open(C+"/texmap.json")); src={}
for jf in sorted(glob.glob(C+"/done/*.json")):
    for r in json.load(open(jf))["images"]:
        o=texmap[r["image"]]["out"]
        src.setdefault(o,(r["src"],texmap[r["image"]]["colorspace"]))
def conv(item):
    out,(sp,cs)=item; im=Image.open(sp).convert("RGB"); w,h=im.size
    if max(w,h)>2560: im=im.resize((2560,round(h*2560/w)) if w>=h else (round(w*2560/h),2560),Image.LANCZOS)
    fn=out.replace(".jpg",".webp"); im.save(f"{OUT}/{fn}","WEBP",quality=95 if cs!="sRGB" else 87,method=6)
    return out,fn,os.path.getsize(f"{OUT}/{out}"),os.path.getsize(f"{OUT}/{fn}")
if __name__=='__main__':
    t0=time.time()
    with ProcessPoolExecutor(4) as ex: res=list(ex.map(conv,sorted(src.items())))
    wm={o:f for o,f,_,_ in res}
    for k,v in texmap.items(): v["webp"]=wm[v["out"]]
    json.dump(texmap,open(C+"/texmap.json","w"),ensure_ascii=False,indent=1)
    j=sum(r[2] for r in res); w=sum(r[3] for r in res)
    print(f"{len(res)} textures: JPEG {j/1e6:.1f} MB -> WebP {w/1e6:.1f} MB ({(w/j-1)*100:+.0f}%), {time.time()-t0:.0f}s")
