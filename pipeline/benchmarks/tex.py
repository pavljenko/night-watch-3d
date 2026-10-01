import numpy as np, os, io, subprocess, glob, json, warnings
from PIL import Image
warnings.filterwarnings("ignore"); Image.MAX_IMAGE_PIXELS=None
B="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/cmp/bol"
src=Image.open("/Users/pavljenko/Desktop/ночной дозор/сцена/сборка/textures/Болхамер_basecolor.JPEG").convert("RGB")
ref=src.resize((2560,2560),Image.LANCZOS); ref.save(B+"/ref.png"); R=np.asarray(ref).astype(np.float64)
def box(x,k=8):
    c=np.cumsum(np.cumsum(np.pad(x,((1,0),(1,0))),0),1); return (c[k:,k:]-c[:-k,k:]-c[k:,:-k]+c[:-k,:-k])/(k*k)
def metrics(img):
    A=np.asarray(img.convert("RGB")).astype(np.float64); mse=((A-R)**2).mean(); psnr=10*np.log10(255**2/mse)
    a=A@[0.299,0.587,0.114]; r=R@[0.299,0.587,0.114]; C1,C2=(0.01*255)**2,(0.03*255)**2
    ma,mr=box(a),box(r); va=box(a*a)-ma**2; vr=box(r*r)-mr**2; cv=box(a*r)-ma*mr
    ssim=((2*ma*mr+C1)*(2*cv+C2)/((ma**2+mr**2+C1)*(va+vr+C2))).mean()
    return round(psnr,2),round(float(ssim),4)
rows=[]
def add(name,path,fmt):
    img=Image.open(path) if fmt!="ktx2" else Image.open(path.replace(".ktx2","_unpacked.png"))
    p,s=metrics(img); rows.append({"name":name,"bytes":os.path.getsize(path),"psnr":p,"ssim":s}); print(f"{name:26s} {os.path.getsize(path)/1e6:6.2f} MB  PSNR {p:5.2f}  SSIM {s:.4f}",flush=True)
for q in (85,90):
    fp=f"{B}/jpg_q{q}.jpg"; ref.save(fp,"JPEG",quality=q,optimize=True); add(f"JPEG q{q}"+(" (сейчас)" if q==85 else ""),fp,"jpg")
for q in (70,75,80,85,90):
    fp=f"{B}/webp_q{q}.webp"; ref.save(fp,"WEBP",quality=q,method=6); add(f"WebP q{q}",fp,"webp")
# KTX2 (Basis): ETC1S (small) and UASTC+zstd (quality); stays compressed in GPU memory
for mode,args in (("etc1s",["-q","255"]),("uastc",["-uastc","-uastc_level","2","-uastc_rdo_l","1.0","-ktx2_zstandard_supercompression","6"])):
    out=f"{B}/tex_{mode}.ktx2"
    subprocess.run(["basisu","-ktx2","-mipmap","-y_flip","-output_file",out,*args,B+"/ref.png"],capture_output=True,cwd=B)
    subprocess.run(["basisu","-unpack","-no_ktx","-format_only","3" if mode=="etc1s" else "12",out],capture_output=True,cwd=B)
    cand=sorted(glob.glob(B+f"/tex_{mode}_unpacked_rgba_*_0000.png")+glob.glob(B+f"/tex_{mode}_unpacked_rgb_*_0000.png"))
    if not os.path.exists(out): print(mode,"failed"); continue
    if cand:
        im=Image.open(cand[0]).transpose(Image.FLIP_TOP_BOTTOM); im.save(out.replace(".ktx2","_unpacked.png")); add(f"KTX2 {mode.upper()}",out,"ktx2")
    else: print(mode,"size",os.path.getsize(out),"(no unpack)",os.listdir(B))
json.dump(rows,open(B+"/tex.json","w"),ensure_ascii=False,indent=1)
