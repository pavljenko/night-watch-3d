import bpy, os, json, glob, math, time
from mathutils import Vector
C="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/cmp"
P="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка/Ночной_дозор_сборка.blend"
OUT="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка/сжатая_сцена_200k_2.5K"; NAME="Ночной_дозор_200k_2.5K"
T0=time.time()
def log(*a): print("[%5.0fs]"%(time.time()-T0),*a,flush=True)
bpy.ops.wm.open_mainfile(filepath=P, load_ui=False); sc=bpy.context.scene; log("opened original")
texmap=json.load(open(C+"/texmap.json"))
jobs=[json.load(open(f)) for f in sorted(glob.glob(C+"/done/*.json"))]
tot0=tot1=0
for job in jobs:
    ob=bpy.data.objects[job["name"]]; old=ob.data
    with bpy.data.libraries.load(job["blend"], link=False) as (src,dst): dst.meshes=list(src.meshes)
    new=[m for m in dst.meshes if m][0]
    for i in range(len(old.materials)):
        if i < len(new.materials): new.materials[i]=old.materials[i]
        else: new.materials.append(old.materials[i])
    new.name=old.name+"_200k"; ob.data=new
    tot0+=job["tris_before"]; tot1+=job["tris_after"]
log(f"meshes swapped: {len(jobs)} objects, {tot0:,} -> {tot1:,} tris")
# textures -> resized files
loaded={}
for m in bpy.data.materials:
    if not (m.use_nodes and m.users): continue
    for nd in m.node_tree.nodes:
        if nd.type=='TEX_IMAGE' and nd.image and nd.image.name in texmap:
            t=texmap[nd.image.name]; fp=OUT+"/textures/"+t["out"]
            if fp not in loaded:
                im=bpy.data.images.load(fp,check_existing=True); im.colorspace_settings.name=t["colorspace"]; loaded[fp]=im
            nd.image=loaded[fp]
log("textures relinked:",len(loaded),"files")
# drop hidden helper geometry and USD scope empties
for n in ("Продление_площадки","Пол_дополнительный"):
    o=bpy.data.objects.get(n)
    if o: bpy.data.objects.remove(o)
for o in [o for o in bpy.data.objects if o.name.startswith("_materials")]: bpy.data.objects.remove(o)
col=bpy.data.collections.get("Продление пола")
if col: bpy.data.collections.remove(col)
bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
heavy=[(o.name,len(o.data.polygons)) for o in bpy.data.objects if o.type=='MESH' and len(o.data.polygons)>260000]
log("remaining meshes over 260k tris:",heavy)
os.makedirs(OUT,exist_ok=True)
sc.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/{NAME}.blend", relative_remap=True, compress=True)
log("saved blend", round(os.path.getsize(f"{OUT}/{NAME}.blend")/1e6,1),"MB")
# ---- lights / camera for the web viewer (glTF Y-up: x, z, -y)
dg=bpy.context.evaluated_depsgraph_get()
def yup(v): return [round(v.x,4),round(v.z,4),round(-v.y,4)]
def bbox(o):
    pts=[o.matrix_world@Vector(c) for c in o.bound_box]; mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)]); return mn,mx
L=[]
for o in sc.objects:
    if o.type!='LIGHT' or o.hide_render: continue
    M=o.matrix_world; pos=M.translation; d=(M.to_3x3()@Vector((0,0,-1))).normalized(); ld=o.data
    rc=o.light_linking.receiver_collection; bc=o.light_linking.blocker_collection
    rec=[x.name for x in rc.all_objects] if rc else []
    e={"name":o.name,"type":ld.type,"energy":ld.energy,"color":list(ld.color),"pos":yup(pos),"dir":yup(d),"receivers":rec,"blockers":[x.name for x in bc.all_objects] if bc else [],"shadow":bool(ld.use_shadow)}
    if ld.type=='SPOT': e.update(angle=ld.spot_size/2,blend=ld.spot_blend)
    if ld.type=='AREA': e.update(size=ld.size)
    if rec:
        c=Vector((0,0,0)); r=0
        for x in rc.all_objects:
            if x.type=='MESH': mn,mx=bbox(x); c+=(mn+mx)/2; r=max(r,(mx-mn).length/2)
        c/=max(1,len([x for x in rc.all_objects if x.type=='MESH']))
        e.update(aim_dist=round(max(0.5,(c-pos).dot(d)),3),recv_radius=round(r,3))
    L.append(e)
cam=sc.camera; Mc=cam.matrix_world; cd=cam.data
camj={"pos":yup(Mc.translation),"dir":yup((Mc.to_3x3()@Vector((0,0,-1))).normalized()),"up":yup((Mc.to_3x3()@Vector((0,1,0))).normalized()),
      "lens":cd.lens,"sensor":cd.sensor_width,"res":[sc.render.resolution_x,sc.render.resolution_y]}
blk=bpy.data.objects.get("Тень_коридора"); bj=None
if blk:
    corners=[blk.matrix_world@Vector((sx*0.5,sy*0.5,0)) for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1))]; bj=[yup(c) for c in corners]
vs=sc.view_settings
json.dump({"lights":L,"camera":camj,"blocker":bj,"exposure":vs.exposure,"look":vs.look,"world":[list(sc.world.node_tree.nodes["Background"].inputs[0].default_value)[:3],sc.world.node_tree.nodes["Background"].inputs[1].default_value] if sc.world and sc.world.use_nodes and "Background" in sc.world.node_tree.nodes else None},
          open(C+"/scene_lights.json","w"),ensure_ascii=False,indent=1)
log("lights json:",len(L),"lights")
log("done (GLB already built from the same meshes)")
