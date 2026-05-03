"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    Loading/caching of DEM files and extraction of elevation data.

"""
from .constants import *
from .tile_db import tile_db
from . import layer_arithmetics as ptl
import numpy as np
from .pillow_support import import_pillow
Image = import_pillow()

class dem_cache:
    """
    Class for loading DEM tiles and extracting elevation data.
    Caches decoded tiles for quick access
    """
    def __init__(self, db: tile_db):
        """
        Parameters
        ----------
        db : tile_db
            The tile database to use for loading DEM tiles.
        """
        self.db = db
        self.dems = {}  # Cache


    def preload_tiles(self, tiles : set) -> None:
        """
        Preloads a set of tiles into the cache.

        Parameters 
        ---------
        tiles : set
            A set of tile descriptors to preload.
        """
        self.db.preload_tiles(tiles)
    

    def unpack_dem(self, tile : Image.Image) -> np.array:
        """
        Unpack a time image to a DEM

        Parameters 
        ---------
        tile : Image.Image
            The tile image to unpack.
        Returns
        -------
        np.array
            A 2D array of elevation values extracted from the tile image.
        """
        pixels = tile.getdata()
        dem = np.zeros((PT_DEM_TILE_RES, PT_DEM_TILE_RES), dtype=np.float32)
        for y in range(PT_DEM_TILE_RES):
            for x in range(PT_DEM_TILE_RES):
                pixel = pixels[y * PT_DEM_TILE_RES + x]
                red = float(pixel[0])
                grn = float(pixel[1])
                blu = float(pixel[2])
                e = (256.0 * red + grn + blu / 256.0) - 32768.0
                dem[y][x] = e
        return dem


    def get_elevation(self, x : int, y : int, z : int) -> float:
        """
        Gets elevation for a given point (x, y) at layer z.

        Parameters
        ----------
        x : int
            The x-coordinate of the point [web mercator].
        y : int
            The y-coordinate of the point [web mercator].
        z : int
            The zoom level.

        Returns
        -------
        float
            The elevation at the given point [meters].
        """
        
        # Generate tile key
        tx, ty = ptl.tile(x, y, z)
        key = f'{tx}:{ty}:{z}'

        # Get tile image from cache or load from database
        dem = self.dems.get(key)
        if dem is None:
            tile = self.db.get_tile(tx, ty, z)   
            if tile is None:
                return 0.0  # Failed download
            dem = self.unpack_dem(tile)
            self.dems[key] = dem

        # Get position within tile and extract elevation
        sx, sy = ptl.tile_sub(x, y, z, PT_DEM_TILE_RES_LOG2)
        return dem[sy][sx]
