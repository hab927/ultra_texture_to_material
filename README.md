# Texture To Material Blender Add-On

This is a Blender Add-On meant to make material creation in Blender for Rude custom level developers. It is much simpler and faster compared to the conventional material creation method since it automates a large part of the process. Currently only supports texture/material patterns found in Rude Level Editor projects.

## Usage

1. Download the `ultrakill_tex_to_mat.zip` file
2. Navigate to `Edit > Preferences > Add-Ons > arrow in top-right > Install From Disk...`. Choose the .zip file.
3. When you have an object selected, select a file from the file browser (click on **Shading** tab at the top toolbar) and right click
4. Press "Assign Material using Selected" and the selected object will have the new materials
5. If you are in edit mode and have faces selected, it will also assign the material to those faces

## Known Issues

- Takes a while. Blender may hang for 0.5-1.5 seconds during conversion. This is partly because of the lack of a cache and also the current algorithm for finding matching GUIDs is a recursive search through the entire Materials directory.
- Not universal. It works well in a generalized sense, where it is given a "Textures" and "Materials" folder, however this is currently limited to the structure of a Rude project.

## To-Do

- Generalized texture/material folder support. Will likely have user specify the Textures and Materials folders.
- Optimized caching. If added, the ability to cache every texture/material pair once can be added to create a master `.json` cache, making future imports much faster. However, currently, caching like this is a process that takes multiple minutes. Will probably do this with CPU multithreading.