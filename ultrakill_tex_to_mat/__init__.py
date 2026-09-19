# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
import bmesh
import re
import os
import json

from pathlib import Path

bl_info = {
    "name": "Ultrakill Texture To Material",
    "author": "hab",
    "description": "turn ultrakill textures into materials more easily",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic",
}

class TextureToMaterial(bpy.types.Operator):
    """Texture to Material Script"""
    bl_idname = "object.ultrakill_material_from_image"
    bl_label = "Add Material using Selected"
    bl_options = {'REGISTER', 'UNDO'}

    tex_guid_pattern = re.compile(r"^guid:\s([0-9a-f]{32})$")                               # for GUID
    mat_name_pattern = re.compile(r"^\s*m_Name:\s([0-9a-zA-Z_\-\s]+)$", re.MULTILINE)       # material name
    mat_guid_pattern = re.compile(r"_MainTex:.*\n.*guid:\s([0-9a-f]{32})")                  # check tex GUID match
    assetdir_pattern = re.compile(r".*Rude[\\/]Assets")                                        # cache file directory
    
    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        # ugly ass list comprehension to get the file browser area
        # context -> screen -> area -> area spaces -> space file browser -> params -> filename
        fb_area = [area for area in context.screen.areas if area.type == "FILE_BROWSER"][0]
        # have to temporarily switch context to get all selected files
        files = []
        with bpy.context.temp_override(area = fb_area):
            files_dirty = bpy.context.selected_files
            files = [f for f in files_dirty if not f.name.endswith(".meta")]     # clean up .meta files in selection if there are any
            
        space_file_browser = fb_area.spaces.active
        materials_to_assign = []
        #combine active directory and meta name (https://stackoverflow.com/questions/41918836/how-do-i-get-rid-of-the-b-prefix-in-a-string-in-python)
        tex_directory = space_file_browser.params.directory.decode('utf-8')

        a_match = re.search(self.assetdir_pattern, tex_directory)
        assets_path = a_match.group(0)
        cache_file = os.path.join(assets_path, "TexMatCache.json")
        cache = None
        # does the cache exist? *VSauce Music*
        if not os.path.isfile(cache_file):
            print("\nNo cache, making one now.\n")
            with open(cache_file, "w") as f:
                f.write("{}")
        else:
            with open(cache_file, "r+") as f:
                content = f.read()          # this shouldnt happen unlss you clear all the text in the .json, not advised
                if not content:
                    f.write("{}")
                cache = json.loads(content)
        
        tex_mat_dictionary = {}             # must populate this and update the json with it during import
        #repeat for every file
        for texture_file in files:
            image_name = texture_file.name
            clean_image_name = Path(image_name).stem            # same as above just no file extension
            
            mat_absolute_path = None
            tex_absolute_path = None
            mat_name = clean_image_name         # default
            
            # WITH THE BRAND NEW CACHE!!!!
            # see if it exists in the cache. if it does, then we can skip the search
            cache_entry = cache.get(clean_image_name)
            if cache_entry:
                mat_name = cache_entry.get("matName")
                tex_absolute_path = cache_entry.get("texPath") + ".meta"
            
            else:
                # the search
                meta_name = image_name + ".meta"
                
                tex_absolute_path = tex_directory + meta_name
                tex_guid = None
                with open(tex_absolute_path) as f:
                    for line in f:
                        match = re.search(self.tex_guid_pattern, line)
                        if match:
                            tex_guid = match.group(1)
                            break

                mat_folder = re.sub(r'Textures.*', 'Materials', tex_directory)
                
                # have to open each material in the folder and check if the guid that appears in _MainTex matches
                p = Path(mat_folder)
                mat_file_list = p.rglob('*.mat')
                mat_file_list = [f for f in mat_file_list if not f.name.endswith('NoFog.mat')]      # make sure nofog files can't get picked
                for file in mat_file_list:
                    with open(file) as f:
                        file_content = f.read()
                    guid_match = re.search(self.mat_guid_pattern, file_content)
                    if not guid_match or guid_match.group(1) != tex_guid:
                        mat_absolute_path = "None"
                        continue
                    name_match = re.search(self.mat_name_pattern, file_content)
                    mat_name = name_match.group(1)
                    mat_absolute_path = file
                    
                # add to the dictionary
                tex_mat_dictionary[clean_image_name] = {
                    "guid": tex_guid,
                    "texName": clean_image_name,
                    "matName": mat_name,
                    "texPath": str(tex_directory + image_name),
                    "matPath": str(mat_absolute_path)
                }

            # create new material with the texture IF IT IS UNIQUE
            # if its not then just use the old one
            if mat_name in [m.name for m in list(bpy.data.materials)]:
                materials_to_assign.append(bpy.data.materials[mat_name])
                continue
            
            material = bpy.data.materials.new(name = mat_name)
            material.preview_render_type = 'FLAT'
            nt = material.node_tree
            image_texture_node = nt.nodes.new("ShaderNodeTexImage")
            bsdf_node = nt.nodes.get("Principled BSDF")
            #and change the properties
            bpy.data.images.load(tex_absolute_path.replace(".meta", ""), check_existing=True)
            image_texture_node.location = (350, 640)
            image_texture_node.image = bpy.data.images[image_name]
            image_texture_node.interpolation = "Closest"
            # link the two nodes
            nt.links.new(image_texture_node.outputs['Color'], bsdf_node.inputs['Base Color'])
            materials_to_assign.append(material)
            
        # update cache with dicitonary contents
        with open(cache_file, "r+") as f:
            content = f.read()
            if content:
                print("Content found.\n")
                TMJ_dict = json.loads(content)
                TMJ_dict.update(tex_mat_dictionary)
            else:
                print("No content found.\n")
                TMJ_dict = tex_mat_dictionary
            new_content = json.dumps(TMJ_dict)
            f.seek(0)
            f.write(new_content)
            f.truncate()

        for obj in bpy.context.selected_objects:
            for am in materials_to_assign:
                obj.data.materials.append(bpy.data.materials[am.name])
                # because we just added a material, it will be at the end. so to get the index just take the length of the materials list and subtract 1
                mat_index = len(obj.data.materials) - 1;
                # assign to faces if in edit mode
                if obj.mode == 'EDIT':
                    me = obj.data
                    bm = bmesh.from_edit_mesh(me)
                    selected_faces = [f for f in bm.faces if f.select]
                    if selected_faces:
                        for face in selected_faces:
                            face.material_index = mat_index
                        bmesh.update_edit_mesh(me)

        return {'FINISHED'}

def menu_item(self, context):
    self.layout.operator(TextureToMaterial.bl_idname)

def register():
    bpy.utils.register_class(TextureToMaterial)
    bpy.types.FILEBROWSER_MT_context_menu.append(menu_item)
    bpy.types.VIEW3D_MT_edit_mesh_faces.append(menu_item)

def unregister():
    bpy.types.FILEBROWSER_MT_context_menu.remove(menu_item)
    bpy.types.VIEW3D_MT_edit_mesh_faces.remove(menu_item)
    bpy.utils.unregister_class(TextureToMaterial)
    
# if __name__ == "__main__":
#      register()