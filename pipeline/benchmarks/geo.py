import bpy, os, json
C="/private/tmp/claude-501/-Users-pavljenko-Desktop-------------/2002a65a-ba2c-46ff-afdf-d5a6bea37e21/scratchpad/cmp"; B=C+"/bol"
P="/Users/pavljenko/Desktop/ночной дозор/сцена/сборка/Ночной_дозор_сборка.blend"
res={}
for tgt in (200000,150000):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(P, link=False) as (s,d): d.objects=["Болхамер"]
    ob=d.objects[0]; sc=bpy.context.scene; sc.collection.objects.link(ob)
    bpy.context.view_layer.objects.active=ob; ob.select_set(True)
    me=ob.data; me.calc_loop_triangles(); n0=len(me.loop_triangles)
    md=ob.modifiers.new("dec",'DECIMATE'); md.decimate_type='COLLAPSE'; md.ratio=tgt/n0; md.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier="dec")
    fp=f"{B}/bol_{tgt//1000}k_geo.glb"
    bpy.ops.export_scene.gltf(filepath=fp, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7, export_draco_position_quantization=14, export_draco_normal_quantization=10, export_draco_texcoord_quantization=14,
        export_image_format='NONE', export_materials='EXPORT', export_normals=True, export_texcoords=True, export_tangents=False, export_lights=False, export_cameras=False, export_animations=False)
    res[tgt]={"tris":len(ob.data.polygons),"verts":len(ob.data.vertices),"glb":os.path.getsize(fp)}
    bpy.ops.wm.save_as_mainfile(filepath=f"{B}/bol_{tgt//1000}k.blend")
    print("RES",tgt,res[tgt],flush=True)
json.dump(res,open(B+"/geo.json","w"))
