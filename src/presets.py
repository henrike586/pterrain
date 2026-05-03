"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    DEM and MAP layer presets for different quality levels.

"""

"""
DEM presets
- name : Name of the preset.
- grid_size : The size of the grid for the DEM layer (NxN).
- z_layers : The zoom levels to use for the DEM layer. Ranges High->Low.
"""
PT_DEM_PRESETS = [
    {
        'name' : 'Low',
        'grid_size' : 128,
        'z_layers' : range(15, 2-1, -1)
    },
    {
        'name' : 'Medium',
        'grid_size' : 256,
        'z_layers' : range(15, 3-1, -1)
    },
    {
        'name' : 'High',
        'grid_size' : 512,
        'z_layers' : range(15, 4-1, -1)
    }
]


"""
MAP presets
- name : Name of the preset.
- texture_size : The size of the texture for the MAP layer (NxN).
- z_layers : The zoom levels to use for the MAP layer. Ranges Low->High.
"""
PT_MAP_PRESETS = [
    {
        'name' : 'Low',
        'texture_size' : 2048,
        'z_layers' : [6, 7, 10, 13, 16, 17, 18, 19, 20]
    },
    {
        'name' : 'Medium',
        'texture_size' : 2048,
        'z_layers' : [6, 8, 10, 12, 14, 15, 16, 17, 18, 19, 20]
    },
    {
        'name' : 'High',
        'texture_size' : 2048,
        'z_layers' : [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    },
]

