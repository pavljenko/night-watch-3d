import bpy, os, numpy as np
S=os.environ["S"]; C=S+"/cart"; K="/Users/pavljenko/Desktop/ночной дозор/сцена/герои/Картуш_с_цитатой"
CX,CZ,HH,ASP,DARK=-0.023,0.484,0.2085,0.5333,float(os.environ.get("DARK","0.70")); HW=HH*ASP
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath="/Users/pavljenko/Desktop/ночной дозор/сцена/герои/Картуш.usdz", import_textures_mode='IMPORT_COPY', import_textures_dir=C+"/src_tex/")
o=[x for x in bpy.context.scene.objects if x.type=='MESH'][0]; o.name="Картуш"; me=o.data
for x in list(bpy.context.scene.objects):
    if x.type!='MESH': bpy.data.objects.remove(x)
N=len(me.vertices); co=np.empty(N*3); me.vertices.foreach_get("co",co); co=co.reshape(-1,3)
L=len(me.loops); vi=np.empty(L,dtype=np.int32); me.loops.foreach_get("vertex_index",vi)
uv=np.empty((L,2)); uv[:,0]=(co[vi,0]-(CX-HW))/(2*HW); uv[:,1]=(co[vi,2]-(CZ-HH))/(2*HH)
pr=me.uv_layers.new(name="Proj"); pr.data.foreach_set("uv",uv.ravel()); me.uv_layers["st"].active=True; me.uv_layers["st"].active_render=True
orig=[nd.image for nd in me.materials[0].node_tree.nodes if nd.type=='TEX_IMAGE' and nd.image][0]; print("orig tex",orig.name,orig.size[:])
mk=bpy.data.images.load(C+"/mask_proj.png"); mk.colorspace_settings.name='Non-Color'
nm=bpy.data.images.load(C+"/normal_proj.png"); nm.colorspace_settings.name='Non-Color'
R=4096
bcol=bpy.data.images.new("Картуш_basecolor_цитата",R,R); bcol.colorspace_settings.name='sRGB'
bnrm=bpy.data.images.new("Картуш_normal_цитата",R,R,is_data=True); bnrm.colorspace_settings.name='Non-Color'
bm=bpy.data.materials.new("bake"); bm.use_nodes=True; t=bm.node_tree; t.nodes.clear()
def nd(tp,**kw):
    n=t.nodes.new(tp)
    for k,v in kw.items(): setattr(n,k,v)
    return n
out=nd('ShaderNodeOutputMaterial'); ust=nd('ShaderNodeUVMap',uv_map="st"); upr=nd('ShaderNodeUVMap',uv_map="Proj")
to=nd('ShaderNodeTexImage',image=orig); t.links.new(ust.outputs[0],to.inputs[0])
tm=nd('ShaderNodeTexImage',image=mk,extension='CLIP'); t.links.new(upr.outputs[0],tm.inputs[0])
tn=nd('ShaderNodeTexImage',image=nm,extension='EXTEND'); t.links.new(upr.outputs[0],tn.inputs[0])
geo=nd('ShaderNodeNewGeometry'); sn=nd('ShaderNodeSeparateXYZ'); t.links.new(geo.outputs['Normal'],sn.inputs[0])
f1=nd('ShaderNodeMath',operation='LESS_THAN'); f1.inputs[1].default_value=-0.25; t.links.new(sn.outputs['Y'],f1.inputs[0])
sp=nd('ShaderNodeSeparateXYZ'); t.links.new(geo.outputs['Position'],sp.inputs[0])
f2=nd('ShaderNodeMath',operation='LESS_THAN'); f2.inputs[1].default_value=-0.03; t.links.new(sp.outputs['Y'],f2.inputs[0])
fm=nd('ShaderNodeMath',operation='MULTIPLY'); t.links.new(f1.outputs[0],fm.inputs[0]); t.links.new(f2.outputs[0],fm.inputs[1])
mask=nd('ShaderNodeMath',operation='MULTIPLY'); t.links.new(tm.outputs['Alpha'],mask.inputs[0]); t.links.new(fm.outputs[0],mask.inputs[1])
dk=nd('ShaderNodeMath',operation='MULTIPLY'); dk.inputs[1].default_value=DARK; t.links.new(mask.outputs[0],dk.inputs[0])
iv=nd('ShaderNodeMath',operation='SUBTRACT'); iv.inputs[0].default_value=1.0; t.links.new(dk.outputs[0],iv.inputs[1])
mix=nd('ShaderNodeMixRGB',blend_type='MULTIPLY'); mix.inputs['Fac'].default_value=1.0; t.links.new(to.outputs['Color'],mix.inputs['Color1']); t.links.new(iv.outputs[0],mix.inputs['Color2'])
em=nd('ShaderNodeEmission'); t.links.new(mix.outputs[0],em.inputs['Color'])
nmap=nd('ShaderNodeNormalMap',space='TANGENT',uv_map="Proj"); t.links.new(tn.outputs['Color'],nmap.inputs['Color']); t.links.new(mask.outputs[0],nmap.inputs['Strength'])
bs=nd('ShaderNodeBsdfPrincipled'); t.links.new(nmap.outputs[0],bs.inputs['Normal'])
tgt=nd('ShaderNodeTexImage',image=bcol); t.links.new(ust.outputs[0],tgt.inputs[0])
me.materials.clear(); me.materials.append(bm)
sc=bpy.context.scene; sc.render.engine='CYCLES'
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='METAL'; prefs.get_devices()
    for d in prefs.devices: d.use=True
    sc.cycles.device='GPU'
except Exception as e: print("gpu",e)
sc.render.bake.margin=12; sc.render.bake.use_clear=True
bpy.context.view_layer.objects.active=o; o.select_set(True)
t.links.new(em.outputs[0],out.inputs['Surface']); t.nodes.active=tgt; sc.cycles.samples=8
bpy.ops.object.bake(type='EMIT'); bcol.filepath_raw=K+"/Картуш_basecolor_цитата.png"; bcol.file_format='PNG'; bcol.save(); print("baked colour")
t.links.new(bs.outputs[0],out.inputs['Surface']); tgt.image=bnrm; t.nodes.active=tgt; sc.render.bake.normal_space='TANGENT'; sc.cycles.samples=4
bpy.ops.object.bake(type='NORMAL'); bnrm.filepath_raw=K+"/Картуш_normal_цитата.png"; bnrm.file_format='PNG'; bnrm.save(); print("baked normal")
# final material + USDZ
fmat=bpy.data.materials.new("Картуш_с_цитатой"); fmat.use_nodes=True; t2=fmat.node_tree; t2.nodes.clear()
o2=t2.nodes.new('ShaderNodeOutputMaterial'); p=t2.nodes.new('ShaderNodeBsdfPrincipled'); t2.links.new(p.outputs[0],o2.inputs[0])
p.inputs['Roughness'].default_value=0.72; p.inputs['Specular IOR Level'].default_value=0.25
ci=bpy.data.images.load(K+"/Картуш_basecolor_цитата.png"); ni=bpy.data.images.load(K+"/Картуш_normal_цитата.png"); ni.colorspace_settings.name='Non-Color'
a=t2.nodes.new('ShaderNodeTexImage'); a.image=ci; t2.links.new(a.outputs['Color'],p.inputs['Base Color'])
b=t2.nodes.new('ShaderNodeTexImage'); b.image=ni; nn=t2.nodes.new('ShaderNodeNormalMap'); nn.uv_map="st"; t2.links.new(b.outputs['Color'],nn.inputs['Color']); t2.links.new(nn.outputs[0],p.inputs['Normal'])
me.materials.clear(); me.materials.append(fmat); me.uv_layers.remove(me.uv_layers["Proj"])
bpy.ops.wm.usd_export(filepath=K+"/Картуш_с_цитатой.usdz", export_materials=True, export_textures=True, overwrite_textures=True, export_uvmaps=True, export_normals=True, convert_orientation=True, export_global_forward_selection='NEGATIVE_Z', export_global_up_selection='Y')
print("usdz",os.path.getsize(K+"/Картуш_с_цитатой.usdz")//(1<<20),"MB")
# previews: flat front and lit front
sc.world=bpy.data.worlds.new("W"); sc.render.image_settings.file_format='JPEG'
import math
from mathutils import Vector
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type='ORTHO'; cd.ortho_scale=1.05; cam.location=(0,-3,0.5); cam.rotation_euler=(math.radians(90),0,0)
sc.render.engine='BLENDER_WORKBENCH'; sc.display.shading.light='FLAT'; sc.display.shading.color_type='TEXTURE'; sc.view_settings.view_transform='Standard'
sc.render.resolution_x=700; sc.render.resolution_y=1050; sc.render.filepath=C+"/front_flat.jpg"; bpy.ops.render.render(write_still=True)
sc.render.engine='CYCLES'; sc.cycles.samples=48
ld=bpy.data.lights.new("k",'AREA'); ld.energy=120; ld.size=0.6; lo=bpy.data.objects.new("k",ld); sc.collection.objects.link(lo); lo.location=(-1.2,-1.6,1.6); lo.rotation_euler=(Vector((0,0,0.5))-lo.location).to_track_quat('-Z','Y').to_euler()
cd.type='PERSP'; cd.lens=50; cam.location=(0,-1.6,0.5); sc.render.resolution_x=900; sc.render.resolution_y=1300; sc.render.filepath=C+"/front_lit.jpg"; bpy.ops.render.render(write_still=True)
print("DONE")
