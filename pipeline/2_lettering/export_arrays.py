import bpy, os, numpy as np
S=os.environ["S"]; O=S+"/ya"
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.wm.usd_import(filepath="/Users/pavljenko/Desktop/ночной дозор/сцена/герои/я.usdz")
o=[x for x in bpy.context.scene.objects if x.type=='MESH'][0]; me=o.data
N=len(me.vertices); co=np.empty(N*3); me.vertices.foreach_get("co",co)
L=len(me.loops); lv=np.empty(L,dtype=np.int64); me.loops.foreach_get("vertex_index",lv); uv=np.empty(L*2); me.uv_layers["st"].data.foreach_get("uv",uv)
P=len(me.polygons); ls=np.empty(P,dtype=np.int64); me.polygons.foreach_get("loop_start",ls); lt=np.empty(P,dtype=np.int64); me.polygons.foreach_get("loop_total",lt)
fn=np.empty(P*3); me.polygons.foreach_get("normal",fn)
print("mw identity:", [list(r) for r in o.matrix_world], "all tris:", bool((lt==3).all()))
np.savez(O+"/mesh.npz",co=co.reshape(-1,3),lv=lv,uv=uv.reshape(-1,2),ls=ls,lt=lt,fn=fn.reshape(-1,3))
print("EXPORTED",N,P)
