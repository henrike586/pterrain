"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    Blender object building from DEM and MAP layers.

"""
import bpy
import bmesh
import numpy as np
from .settings import *
from .dem_layer import *
from .map_layer import *
from .map_uv import map_uv_lookup, uv_calc

def build_blender_object(dem_layers : list, map_layers : list, proj : any, status_callback : callable) -> None:
    """
    Builds a Blender object from DEM and MAP layers.

    Parameters
    ----------
    dem_layers : list
        A list of dem_layer objects.
    map_layers : list
        A list of map_layer objects.
    proj : any
        A projection object used to project DEM vertices to 3D coordinates.
        Must support project() method.
    status_callback : callable
        Callback for status updates during terrain generation.
    """
    # Create textures and materials
    status_callback('Generating materials')
    w = PT_SETTINGS['map_preset']['texture_size']
    materials = []
    for (z, mlayer) in map_layers:

        # Convert Pillow image to Blender image
        pixels = np.asarray(mlayer.image, dtype=np.float32) / 255.0
        pixels = np.concatenate((pixels, np.ones((w, w, 1), dtype=np.float32)), axis=2)
        image = bpy.data.images.new(f'pt_image_z{z:02d}', width=w, height=w)
        image.pixels.foreach_set(pixels.flatten())

        # Create and link material shader
        material = bpy.data.materials.new(f'pt_material_z{z:02d}')
        material.use_nodes = True
        mshader = material.node_tree.nodes['Principled BSDF']
        mshader.inputs['Roughness'].default_value = 1.0
        texture = material.node_tree.nodes.new('ShaderNodeTexImage')
        texture.image = image
        texture.location.x -= 600
        texture.location.y += 100
        material.node_tree.links.new(mshader.inputs['Base Color'], texture.outputs['Color'])
        materials.append(material)

    # Save all images in file
    status_callback('Saving images in Blender file')
    bpy.ops.image.save_all_modified()

    # Precalcluate UVs (multithreaded)
    uv_data = []
    for i in range(len(dem_layers)):
        z, dlayer = dem_layers[i]
        status_callback(f'UV layer {i + 1}/{len(dem_layers)}')
        uv_data.append(uv_calc(dlayer, map_layers))
    
    # Create mesh object per layer
    layer_objects = []
    for i in range(len(dem_layers)):
        z, dlayer = dem_layers[i]
        status_callback(f'MESH layer {i + 1}/{len(dem_layers)}')

        # Create new layer object and mesh
        mesh = bpy.data.meshes.new(f'pt_mesh_z{z:02d}')
        object = bpy.data.objects.new(f'pt_object_z{z:02d}', mesh) 
        bpy.context.scene.collection.objects.link(object)
        layer_objects.append(object)

        # Create new BMesh and UV layer
        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new('UVMap')

        # Project and create mesh vertices
        index = 0
        for v in dlayer.verts:
            pv = bm.verts.new(proj.project(v))
            pv.index = index
            index += 1
        bm.verts.ensure_lookup_table()

        # Create mesh faces
        (mat_indexes, uv_loops) = uv_data[i]
        mat_iter = iter(mat_indexes)
        uv_iter = iter(uv_loops)
        for f in dlayer.faces:
            # Create face
            face = bm.faces.new([bm.verts[index] for index in f])

            # Set precalculated UVs
            for loop in face.loops:
                loop[uv_layer].uv = next(uv_iter)

            # Set material
            face.material_index = next(mat_iter)

        bm.to_mesh(mesh)
        mesh.update()
        bm.free()

    # Create target object
    status_callback('Creating target object')
    target_object = bpy.data.objects.new(f'pt_object', bpy.data.meshes.new('pt_mesh')) 
    bpy.context.view_layer.active_layer_collection.collection.objects.link(target_object)
    for material in materials:
        target_object.data.materials.append(material)
    target_object['pterrain_version'] = PT_VERSION
    target_object['pterrain_lon'] = '{:.10f}'.format(PT_SETTINGS['lonc'])
    target_object['pterrain_lat'] = '{:.10f}'.format(PT_SETTINGS['latc'])
    target_object['pterrain_projection'] = proj.name()
    target_object['pterrain_dem_preset'] = PT_SETTINGS['dem_preset']['name']
    target_object['pterrain_map_preset'] = PT_SETTINGS['map_preset']['name']
    
    # Join layers to target object
    status_callback('Joining layers')
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new('UVMap')
    for object in layer_objects:
        bm.from_mesh(object.data)

    # Clean duplicated vertices
    status_callback('Cleaning duplicated vertices')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.5)

    # Set smooth shading and flip normals
    status_callback('Setting smooth shading')
    for face in bm.faces:
        face.smooth = True
        face.normal_flip()

    # Recreate mesh for target object
    bm.to_mesh(target_object.data)

    # Delete layer objects
    for object in layer_objects:
        bpy.data.objects.remove(object, do_unlink=True)

    
