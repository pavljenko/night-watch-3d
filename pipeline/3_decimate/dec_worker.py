import bpy, os, json, time, glob
C=os.environ["C"]; P="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка/Ночной_дозор_сборка.blend"; WID=os.environ.get("WID","w")
T0=time.time()
def log(*a): print(f"[{WID} {time.time()-T0:5.0f}s]",*a,flush=True)
def claim():
    for f in sorted(glob.glob(C+"/todo/*.json")):
        dst=C+"/doing/"+os.path.basename(f)
        try: os.rename(f,dst); return dst
        except OSError: continue
    return None
while True:
    jf=claim()
    if not jf: break
    job=json.load(open(jf)); name=job["name"]; tgt=job["target"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(P, link=False) as (src,dst): dst.objects=[name]
    ob=dst.objects[0]; sc=bpy.context.scene; sc.collection.objects.link(ob)
    ob.constraints.clear(); ob.parent=None
    for x in sc.objects: x.select_set(False)
    bpy.context.view_layer.objects.active=ob; ob.select_set(True)
    me=ob.data; me.calc_loop_triangles(); n0=len(me.loop_triangles)
    ratio=min(1.0,tgt/n0)
    md=ob.modifiers.new("dec",'DECIMATE'); md.decimate_type='COLLAPSE'; md.ratio=ratio; md.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier="dec")
    n=len(ob.data.polygons)
    # packed source textures -> files for resizing
    imgs=[]
    for m in ob.data.materials:
        if not (m and m.use_nodes): continue
        for nd in m.node_tree.nodes:
            if nd.type=='TEX_IMAGE' and nd.image:
                im=nd.image; rec={"image":im.name,"material":m.name,"colorspace":im.colorspace_settings.name}
                if im.packed_file:
                    ext=os.path.splitext(im.filepath)[1] or ".jpg"; fp=C+"/src_tex/"+im.name.replace("/","_")+ext
                    if not os.path.exists(fp): open(fp,"wb").write(im.packed_file.data)
                    rec["src"]=fp
                else: rec["src"]=bpy.path.abspath(im.filepath)
                imgs.append(rec)
    out=C+"/dec/"+os.path.basename(jf).replace(".json",".blend")
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=False)
    job.update({"tris_before":n0,"tris_after":n,"blend":out,"images":imgs,"object":ob.name})
    json.dump(job,open(C+"/done/"+os.path.basename(jf),"w"),ensure_ascii=False,indent=1); os.remove(jf)
    log(f"{name[:40]:40s} {n0:>8d} -> {n:>7d} tris")
log("worker finished")
