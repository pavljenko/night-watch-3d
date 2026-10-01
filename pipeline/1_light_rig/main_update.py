import bpy, os, math, json, time, numpy as np
from mathutils import Vector, Matrix
S=os.environ["S"]; B="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка"
SAVE=os.environ.get("SAVE","0")=="1"; RENDER=os.environ.get("RENDER","check"); TAG=os.environ.get("TAG","t")
EW=float(os.environ.get("EW","100")); EC=float(os.environ.get("EC","60")); ANDREY_DX=float(os.environ.get("ANDREY_DX","0.30")); FACE=float(os.environ.get("FACE","190")); ANIM=float(os.environ.get("ANIM","110"))
LEFT=float(os.environ.get("LEFT","1.0")); BOY=float(os.environ.get("BOY","0.6"))
T0=time.time()
def log(*a): print("[%5.0fs]"%(time.time()-T0),*a,flush=True)
bpy.ops.wm.open_mainfile(filepath=B+"/Ночной_дозор_сборка.blend"); sc=bpy.context.scene; vl=bpy.context.view_layer; log("opened")
WARM2=(1.0,0.86,0.66)
def look(ob,t): ob.rotation_euler=(Vector(t)-ob.location).to_track_quat('-Z','Y').to_euler()
def texname(o):
    for m in o.data.materials:
        if m and m.use_nodes:
            for nd in m.node_tree.nodes:
                if nd.type=='TEX_IMAGE' and nd.image: return nd.image.name.split('_basecolor')[0]
    return ""
def child_of(lo,target):
    c=lo.constraints.new('CHILD_OF'); c.target=target; c.inverse_matrix=Matrix.Identity(4); vl.update()
    P=lo.matrix_world@lo.matrix_basis.inverted(); c.inverse_matrix=P.inverted(); vl.update()
    return (lo.matrix_world.translation-lo.matrix_basis.translation).length
# ---------- A. scroll texture on "я"
ya=[o for o in sc.objects if o.type=='MESH' and texname(o)=='я'][0]
img=bpy.data.images.load(B+"/textures/я_basecolor_свиток.jpg",check_existing=True); img.colorspace_settings.name='sRGB'
n=0
for m in ya.data.materials:
    for nd in m.node_tree.nodes:
        if nd.type=='TEX_IMAGE' and nd.image and nd.image.name.startswith('я_basecolor'): nd.image=img; n+=1
log("scroll texture set on",ya.name,"nodes",n)
# ---------- B. cartouche textures reload from disk
for im in bpy.data.images:
    if im.name.startswith('Картуш_') and 'цитата' in im.name: im.reload(); log("reloaded",im.name,"<-",bpy.path.abspath(im.filepath).split('/')[-1],tuple(im.size))
# ---------- C0. move Andrey right (camera view) so Bolkhamer's pike clears his head
andrey=[o for o in sc.objects if o.type=='MESH' and texname(o)=='Андрей'][0]
if "andrey_dx_done" not in andrey:
    andrey.location.x+=ANDREY_DX; andrey["andrey_dx_done"]=ANDREY_DX; vl.update()
log("Андрей moved to",tuple(round(v,3) for v in andrey.location))
# ---------- C. face lights
arch=bpy.data.objects.get("Арка_ниша")
if arch: arch.hide_render=True; arch.hide_viewport=True; log("Арка_ниша hidden")
old=bpy.data.objects.get("Оккерсен")
if old and old.name not in sc.objects:
    me=old.data; bpy.data.objects.remove(old)
    if me and me.users==0: bpy.data.meshes.remove(me)
    for nm in ("Лицо_Оккерсен",):
        l=bpy.data.objects.get(nm)
        if l: ld=l.data; bpy.data.objects.remove(l); bpy.data.lights.remove(ld)
    c=bpy.data.collections.get("LL_Оккерсен")
    if c: bpy.data.collections.remove(c)
    log("removed orphan old Оккерсен + its face light")
lit=set()
for l in sc.objects:
    if l.type=='LIGHT' and l.light_linking.receiver_collection:
        lit|={x.name for x in l.light_linking.receiver_collection.objects}
NAMES={"Андрей":"Андрей","Кошка_с_собакой":"Кошка с собакой","я":"я","Чипулька":"Чипулька","Царевна":"Царевна","Тотошка":"Тотошка","Галина_Антоновна":"Галина Антоновна","Девочка_в_голубом":"Девочка в голубом","Рембрандт":"Рембрандт","Статист_2":"Статист 2","Оккерсен_ОК":"Оккерсен","Алла":"Алла"}
new=[o for o in sc.objects if o.type=='MESH' and o.name.startswith('tripo_mesh') and o.name not in lit and not texname(o).startswith('medieval_spear') and o.visible_get()]
new.sort(key=lambda o:o.name)
def world_pts(o,step=15):
    co=np.empty(len(o.data.vertices)*3); o.data.vertices.foreach_get("co",co); co=co.reshape(-1,3)[::step]; W=np.array(o.matrix_world); return co@W[:3,:3].T+W[:3,3]
count={}; made=[]
for o in new:
    P=world_pts(o); zmin,zmax=P[:,2].min(),P[:,2].max(); small=(zmax-zmin)<1.0
    base=NAMES.get(texname(o),texname(o)); count[base]=count.get(base,0)+1; name=base if count[base]==1 else f"{base} {count[base]}"
    if small: aim=Vector((P[:,0].mean(),P[:,1].mean(),zmin+0.65*(zmax-zmin)))
    else:
        feet=P[P[:,2]<zmin+0.05]; ax=feet[:,:2].mean(axis=0); near=P[np.linalg.norm(P[:,:2]-ax,axis=1)<0.32]
        top=np.percentile(near[:,2],99.3); head=near[near[:,2]>top-0.28]; aim=Vector((head[:,0].mean(),head[:,1].mean(),top-0.17))
    coll=bpy.data.collections.get("LL_"+name) or bpy.data.collections.new("LL_"+name)
    if o.name not in coll.objects: coll.objects.link(o)
    ld=bpy.data.lights.new("Лицо_"+name,'SPOT'); ld.energy=ANIM if small else FACE; ld.spot_size=math.radians(18); ld.spot_blend=0.75; ld.shadow_soft_size=0.35; ld.color=WARM2; ld.use_shadow=False
    lo=bpy.data.objects.new("Лицо_"+name,ld); sc.collection.objects.link(lo); lo.location=aim+Vector((-1.6,-3.2,1.9)); look(lo,aim)
    lo.light_linking.receiver_collection=coll
    err=child_of(lo,o); made.append((lo.name,o.name))
    log(f"face light {lo.name:26s} -> {o.name[:24]:24s} {'small' if small else 'human'} aim ({aim.x:.2f},{aim.y:.2f},{aim.z:.2f}) E {ld.energy:.0f} childof-err {err:.4f}")
# ---------- left faces + boy: spots were missing the heads (9-28 deg off axis, cone half-angle 9) -> re-aim at the head, keep position
def head_of(o):
    P=world_pts(o,8); zmin=P[:,2].min(); feet=P[P[:,2]<zmin+0.05]; ax=feet[:,:2].mean(axis=0); near=P[np.linalg.norm(P[:,:2]-ax,axis=1)<0.32]
    top=np.percentile(near[:,2],99.3); head=near[near[:,2]>top-0.28]; return Vector((head[:,0].mean(),head[:,1].mean(),top-0.17))
for nm,f in (("Энгелен",LEFT),("Бронкхорст",LEFT),("Вормсверк",LEFT),("Виллемсен",LEFT),("Ван дер Хеде",LEFT),("Мальчик",BOY)):
    l=bpy.data.objects.get("Лицо_"+nm); fig=bpy.data.objects.get(nm)
    if not (l and fig): log("missing",nm); continue
    h=head_of(fig); pos=l.matrix_world.translation.copy(); old=math.degrees((l.matrix_world.to_3x3()@Vector((0,0,-1))).angle(h-pos))
    desired=Matrix.LocRotScale(pos,(h-pos).to_track_quat('-Z','Y'),Vector((1,1,1)))
    C=l.matrix_world@l.matrix_basis.inverted(); l.matrix_basis=C.inverted()@desired; vl.update()
    new=math.degrees((l.matrix_world.to_3x3()@Vector((0,0,-1))).angle(h-l.matrix_world.translation))
    base=float(l.get("base_energy",l.data.energy)); l["base_energy"]=base; l.data.energy=base*f
    log(f"face {nm}: off-axis {old:.1f} -> {new:.1f} deg, dist {(h-pos).length:.1f} m, E {base:.0f} -> {l.data.energy:.0f}")
# ---------- D. wall fill, corridor kept dark
bg=bpy.data.objects["Фон_сцена"]
llf=bpy.data.collections.get("LL_фон") or bpy.data.collections.new("LL_фон")
if bg.name not in llf.objects: llf.objects.link(bg)
blk=bpy.data.objects.get("Тень_коридора")
if not blk:
    import bmesh
    me=bpy.data.meshes.new("Тень_коридора"); bm=bmesh.new(); bmesh.ops.create_grid(bm,x_segments=1,y_segments=1,size=0.5); bm.to_mesh(me); bm.free()
    blk=bpy.data.objects.new("Тень_коридора",me); sc.collection.objects.link(blk)
blk.location=(-1.72,2.45,2.80); blk.rotation_euler=(math.radians(90),0,0); blk.scale=(2.5,3.8,1)   # x -2.97..-0.47, z 0.9..4.7
blk.visible_camera=False; blk.visible_diffuse=False; blk.visible_glossy=False; blk.visible_transmission=False; blk.visible_volume_scatter=False; blk.visible_shadow=True
blk.display_type='WIRE'; blk.hide_render=False
bcol=bpy.data.collections.get("Блок_фон") or bpy.data.collections.new("Блок_фон")
for o in (bg,blk):
    if o.name not in bcol.objects: bcol.objects.link(o)
for nm,loc,tgt,E in (("Свет_стены_лево",(-6.0,-3.0,5.6),(-5.3,2.7,3.6),EW),("Свет_стены_право",(2.9,-3.0,5.6),(2.6,2.3,3.6),EW),("Свет_стены_центр",(-1.6,-3.5,7.0),(-1.7,2.1,4.9),EC)):
    lo=bpy.data.objects.get(nm)
    if not lo:
        ld=bpy.data.lights.new(nm,'SPOT'); lo=bpy.data.objects.new(nm,ld); sc.collection.objects.link(lo)
    ld=lo.data; ld.energy=E; ld.spot_size=math.radians(75); ld.spot_blend=1.0; ld.shadow_soft_size=1.5; ld.color=(1.0,0.84,0.64)
    lo.location=loc; look(lo,tgt); lo.light_linking.receiver_collection=llf; lo.light_linking.blocker_collection=bcol
    log(f"wall light {nm} E {E:.0f}")
vl.update()
if SAVE:
    bpy.ops.wm.save_as_mainfile(filepath=B+"/Ночной_дозор_сборка.blend"); log("SAVED")
# ---------- renders (nothing below is saved)
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='METAL'; prefs.get_devices()
    for d in prefs.devices: d.use=True
except Exception as e: log("gpu",e)
sc.render.engine='CYCLES'; sc.cycles.device='GPU'; sc.cycles.use_adaptive_sampling=True; sc.cycles.adaptive_threshold=0.02; sc.cycles.use_denoising=True; sc.cycles.denoiser='OPENIMAGEDENOISE'
sc.render.use_simplify=True; sc.cycles.texture_limit_render='4096'; sc.render.image_settings.file_format='JPEG'; sc.render.image_settings.quality=92
os.makedirs(S+"/s3/r",exist_ok=True); sc.render.use_persistent_data=True
if RENDER in ("check","final"):
    import shutil
    sc.cycles.samples=32 if RENDER=="check" else 96; X=900 if RENDER=="check" else 1500
    sc.render.resolution_x=X; sc.render.resolution_y=int(X*1000/1200); sc.render.resolution_percentage=100
    sc.render.filepath=f"{S}/s3/r/overview_{TAG}.jpg"; bpy.ops.render.render(write_still=True); log("overview rendered")
    if RENDER=="check":
        sc.render.resolution_x=1800; sc.render.resolution_y=1500; sc.render.use_border=True; sc.render.use_crop_to_border=True
        for nm,(x0,x1,y0,y1) in {"left":(0.0,0.38,0.2,0.62),"andrey":(0.45,0.72,0.42,0.72)}.items():
            sc.render.border_min_x,sc.render.border_max_x,sc.render.border_min_y,sc.render.border_max_y=x0,x1,y0,y1
            sc.render.filepath=f"{S}/s3/r/crop_{nm}_{TAG}.jpg"; bpy.ops.render.render(write_still=True); log("crop",nm)
        sc.render.use_border=False
if RENDER in ("final","close"):
    cam=sc.camera; cd=cam.data; dg=bpy.context.evaluated_depsgraph_get()
    sc.cycles.samples=64; sc.render.resolution_x=sc.render.resolution_y=1000
    k=bpy.data.objects["Картуш"]; M=k.matrix_world; fwd=(M.to_3x3()@Vector((0,-1,0))).normalized(); ctr=M@Vector((-0.023,-0.06,0.484))
    cd.lens=85; cam.location=ctr+fwd*2.3; look(cam,ctr); sc.render.filepath=f"{S}/s3/r/cartouche_scene.jpg"; bpy.ops.render.render(write_still=True); log("cartouche scene")
    fr=json.load(open(S+"/ya/frame.json")); Mw=ya.matrix_world; sca=Mw.to_scale()[0]
    mL,nL,UL,RL=(Vector(fr[k]) for k in ("m","n","U","R"))
    pc=Mw@(mL+UL*(-0.042)); eye=Mw@(mL-nL*0.15+Vector((0,0,0.10))+RL*0.015)
    cd.lens=40; cd.clip_start=0.09*sca; cam.location=eye; look(cam,pc); sc.render.filepath=f"{S}/s3/r/scroll_scene.jpg"; bpy.ops.render.render(write_still=True); log("scroll scene (reader eye)")
    hl=bpy.data.lights.new("tmp_help",'AREA'); hl.energy=12; hl.size=0.4; hl.color=(1,0.93,0.82); ho=bpy.data.objects.new("tmp_help",hl); sc.collection.objects.link(ho)
    ho.location=Mw@(mL-nL*0.22+Vector((0,0,0.30))); look(ho,pc); sc.render.filepath=f"{S}/s3/r/scroll_lit.jpg"; bpy.ops.render.render(write_still=True); log("scroll lit")
    cd.clip_start=0.1
    hl.energy=120; hl.size=1.2; ho.location=ctr+fwd*1.8+Vector((0,0,0.6)); look(ho,ctr)
    cam.location=ctr+fwd*2.3; look(cam,ctr); sc.render.filepath=f"{S}/s3/r/cartouche_lit.jpg"; bpy.ops.render.render(write_still=True); log("cartouche lit")
