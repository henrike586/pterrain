"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    Constants for PTerrain.

"""

PT_EARTH_RADIUS = 6378137.0
"""Earth radius in meters."""

PT_DEM_TILE_RES = 256
"""Resolution of DEM tiles in pixels (on public server)."""
PT_DEM_TILE_RES_LOG2 = 8

PT_MAP_TILE_RES = 256
"""Resolution of MAP tiles in pixels (on public server)."""
PT_MAP_TILE_RES_LOG2 = 8

PT_DEM_DB_NAME = 'dem_tiles.db'
"""Name of the DEM tile database file."""

PT_MAP_DB_NAME = 'map_tiles.db'
"""Name of the MAP tile database file."""

PT_TILE_DOWNLOAD_BATCH_SIZE = 8
"""Number of tiles to download simultaneously."""
