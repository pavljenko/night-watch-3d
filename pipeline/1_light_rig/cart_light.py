import bpy, os, math, time
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
S=os.environ["S"]; B="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка"; TAG=os.environ.get("TAG","c")
E=float(os.environ.get("E","110")); VARIANTS=[float(x) for x in os.environ.get("VARIANTS","70,110,160").split(",") if x]; OX=int(os.environ.get("OX","1200")); OS=int(os.environ.get("OS","32")); SAVE=os.environ.get("SAVE","0")=="1"; RENDER=os.environ.get("RENDER","1")=="1"
T0=time.time()
def log(*a): print("[%5.0fs]"%(time.time()-T0),*a,flush=True)
bpy.ops.wm.open_mainfile(filepath=B+"/Ночной_дозор_сборка.blend"); sc=bpy.context.scene; vl=bpy.context.view_layer; log("opened")
k=bpy.data.objects["Картуш"]; l=bpy.data.objects["Лицо_Картуш"]; M=k.matrix_world
ok,loc,nor,idx=k.ray_cast(Vector((-0.023,-2.0,0.484)),Vector((0,1,0)))
oc=M@loc; on=(M.to_3x3().inverted().transposed()@nor).normalized()
pos=l.matrix_world.translation.copy(); axis=(l.matrix_world.to_3x3()@Vector((0,0,-1))).normalized(); to=oc-pos
log(f"oval centre {tuple(round(v,3) for v in oc)} normal {tuple(round(v,3) for v in on)} | light at {tuple(round(v,2) for v in pos)} E {l.data.energy:.0f} size {math.degrees(l.data.spot_size):.0f} blend {l.data.spot_blend} shadow {l.data.use_shadow}")
log(f"before: off-axis {math.degrees(axis.angle(to)):.1f} deg, dist {to.length:.2f} m, incidence {math.degrees((-to).angle(on)):.1f} deg")
# re-aim at the oval centre, keep position; cone wide enough for the whole cartouche, soft edge
desired=Matrix.LocRotScale(pos,to.to_track_quat('-Z','Y'),Vector((1,1,1)))
C=l.matrix_world@l.matrix_basis.inverted(); l.matrix_basis=C.inverted()@desired; vl.update()
half=math.degrees(math.atan(0.95/to.length)); l.data.spot_size=math.radians(2*(half+3)); l.data.spot_blend=0.6; l.data.energy=E
axis=(l.matrix_world.to_3x3()@Vector((0,0,-1))).normalized()
log(f"after: off-axis {math.degrees(axis.angle(oc-l.matrix_world.translation)):.2f} deg, spot {math.degrees(l.data.spot_size):.0f} deg, E {E:.0f}")
if SAVE: bpy.ops.wm.save_as_mainfile(filepath=B+"/Ночной_дозор_сборка.blend"); log("SAVED")
if not RENDER: raise SystemExit
prefs=bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type='METAL'; prefs.get_devices()
for d in prefs.devices: d.use=True
sc.render.engine='CYCLES'; sc.cycles.device='GPU'; sc.cycles.use_adaptive_sampling=True; sc.cycles.adaptive_threshold=0.02; sc.cycles.use_denoising=True; sc.cycles.denoiser='OPENIMAGEDENOISE'
sc.render.use_simplify=True; sc.cycles.texture_limit_render='4096'; sc.render.image_settings.file_format='JPEG'; sc.render.image_settings.quality=92; sc.render.use_persistent_data=True
os.makedirs(S+"/s3/r",exist_ok=True)
# cartouche crop box in camera frame
cs=[world_to_camera_view(sc,sc.camera,M@Vector(c)) for c in k.bound_box]
x0=max(min(c.x for c in cs)-0.03,0); x1=min(max(c.x for c in cs)+0.03,1); y0=max(min(c.y for c in cs)-0.03,0); y1=min(max(c.y for c in cs)+0.03,1)
if VARIANTS: log(f"cartouche frame box x {x0:.3f}-{x1:.3f} y {y0:.3f}-{y1:.3f}")
sc.cycles.samples=48; sc.render.resolution_x=2400; sc.render.resolution_y=2000; sc.render.resolution_percentage=100
sc.render.use_border=bool(VARIANTS); sc.render.use_crop_to_border=True; sc.render.border_min_x,sc.render.border_max_x,sc.render.border_min_y,sc.render.border_max_y=x0,x1,y0,y1
for e in VARIANTS:  # crops
    l.data.energy=e; sc.render.filepath=f"{S}/s3/r/cart_{TAG}_{int(e)}W.jpg"; bpy.ops.render.render(write_still=True); log("cartouche crop",e)
l.data.energy=E; sc.render.use_border=False
sc.cycles.samples=OS; sc.render.resolution_x=OX; sc.render.resolution_y=int(OX*1000/1200)
sc.render.filepath=f"{S}/s3/r/overview_{TAG}.jpg"; bpy.ops.render.render(write_still=True); log("overview")
