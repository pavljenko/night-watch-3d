import bpy, bmesh, numpy as np, os, json, time
from mathutils import Vector
C="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/cmp"
P="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка/Ночной_дозор_сборка.blend"
YA="tripo_mesh_67259b69_695e_4bcf_9f4a_dee6aa3dfd99"; REST=200000; FACTOR=float(os.environ.get("FACTOR","1000"))
def verts_np(me):
    a=np.empty(len(me.vertices)*3); me.vertices.foreach_get("co",a); return a.reshape(-1,3)
def tris_np(me):
    lv=np.empty(len(me.loops),np.int64); me.loops.foreach_get("vertex_index",lv); ls=np.empty(len(me.polygons),np.int64); me.polygons.foreach_get("loop_start",ls)
    return lv[ls[:,None]+np.arange(3)[None,:]]
out={}
for name,jid in ((YA,"030"),("Картуш","043")):
    bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
    with bpy.data.libraries.load(P, link=False) as (s,d): d.objects=[name]
    ob=d.objects[0]; sc.collection.objects.link(ob); ob.constraints.clear(); ob.parent=None
    bpy.context.view_layer.objects.active=ob; ob.select_set(True)
    me=ob.data; co=verts_np(me); tri=tris_np(me); N0=len(tri)
    if name==YA: pv=np.load(C+"/prot/ya_verts.npy")
    else:
        CX,CZ,HH,ASP=-0.023,0.484,0.2085,0.5333; HW=HH*ASP
        fn=np.empty(N0*3); me.polygons.foreach_get("normal",fn); fn=fn.reshape(-1,3); cen=co[tri].mean(axis=1)
        f=(np.abs(cen[:,0]-CX)<HW*1.12)&(np.abs(cen[:,2]-CZ)<HH*1.08)&(fn[:,1]<-0.2)&(cen[:,1]<-0.02)
        vs=set(np.unique(tri[f]).tolist())
        for ring in range(2):
            mk=np.isin(tri,list(vs)).any(axis=1); vs=set(np.unique(tri[mk]).tolist())
        pv=np.array(sorted(vs)); print("cartouche protected faces",int(f.sum()))
    inside=np.isin(tri,pv).all(axis=1); Pf=int(inside.sum())
    vg=ob.vertex_groups.new(name="text"); vg.add(pv.tolist(),1.0,'REPLACE')
    md=ob.modifiers.new("dec",'DECIMATE'); md.decimate_type='COLLAPSE'; md.use_collapse_triangulate=True
    md.ratio=(REST+Pf)/N0; md.vertex_group="text"; md.invert_vertex_group=True; md.vertex_group_factor=FACTOR
    bpy.ops.object.modifier_apply(modifier="dec")
    me2=ob.data; co2=verts_np(me2); n=len(me2.polygons)
    key=lambda a: set(map(tuple,np.round(a,6)))
    kept=len(key(co[pv]) & key(co2)); 
    out[name]={"tris_before":N0,"tris_after":n,"protected_faces":Pf,"protected_verts":len(pv),"protected_verts_kept":kept}
    print(name,out[name],flush=True)
    ob.vertex_groups.clear()
    bpy.ops.wm.save_as_mainfile(filepath=f"{C}/prot/{jid}.blend", compress=False)
json.dump(out,open(C+"/prot/result.json","w"),ensure_ascii=False)
