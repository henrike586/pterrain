"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    PTerrain settings.

"""
import os
from .presets import *

PT_VERSION = '1.0.0'

PT_WORK_DIR = os.path.join(os.path.expanduser('~'), '.pterrain')
if not os.path.exists(PT_WORK_DIR):
    os.mkdir(PT_WORK_DIR)

PT_SETTINGS = {
    'grid_center_x' : 0x80000000,
    'grid_center_y' : 0x80000000,
    'proj_center_x' : 0x80000000,
    'proj_center_y' : 0x80000000,
    'dem_preset' : PT_DEM_PRESETS[0],
    'map_preset' : PT_MAP_PRESETS[0],
    'clamp_to_sea_level' : False
}

