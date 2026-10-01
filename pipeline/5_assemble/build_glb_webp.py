import bpy, os, json, glob, time
C="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/cmp"
OUT="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка/сжатая_сцена_200k_2.5K"; NAME="Ночной_дозор_200k_2.5K"
T0=time.time()
def log(*a): print("[%5.0fs]"%(time.time()-T0),*a,flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
texmap=json.load(open(C+"/texmap.json")); loaded={}
def tex(key):
    t=texmap[key]; fp=OUT+"/textures/"+t["webp"]
    if fp not in loaded:
        im=bpy.data.images.load(fp,check_existing=True); im.colorspace_settings.name=t["colorspace"]; loaded[fp]=im
    return loaded[fp]
for jf in sorted(glob.glob(C+"/done/*.json")):
    job=json.load(open(jf))
    with bpy.data.libraries.load(job["blend"], link=False) as (src,dst): dst.objects=list(src.objects)
    ob=[o for o in dst.objects if o and o.type=='MESH'][0]; sc.collection.objects.link(ob)
    recs=iter(job["images"])
    for m in ob.data.materials:
        if not (m and m.use_nodes): continue
        for nd in m.node_tree.nodes:
            if nd.type=='TEX_IMAGE' and nd.image:
                r=next(recs); nd.image=tex(r["image"])
    ob.name=job["name"]
bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
tris=sum(len(o.data.polygons) for o in sc.objects if o.type=='MESH')
log("objects",len(sc.objects),"tris",tris,"images",len(loaded))
os.makedirs(OUT,exist_ok=True)
for o in sc.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=f"{OUT}/{NAME}_webp.glb", export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7, export_draco_position_quantization=14, export_draco_normal_quantization=10, export_draco_texcoord_quantization=14,
    export_image_format='AUTO', export_materials='EXPORT', export_normals=True, export_texcoords=True, export_tangents=False, export_lights=False, export_cameras=False, export_animations=False, export_skins=False, export_morph=False, export_extras=False)
log("GLB", round(os.path.getsize(f"{OUT}/{NAME}_webp.glb")/1e6,1),"MB")
bpy.ops.wm.save_as_mainfile(filepath=C+"/meshes_only_webp.blend", compress=False); log("saved meshes_only.blend")
