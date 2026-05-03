"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    MAP layer generation from MAP tiles.

"""
from .constants import *
from .settings import *
from .tile_db import tile_db
from . import layer_arithmetics as ptl
from .pillow_support import import_pillow
Image = import_pillow()

class init_map_layer:
    """
    Empty MAP layer used during build initialization
    """
    def __init__(self, z : int, texture_size : int):
        self.z = z
        self.image = Image.new('RGB', (texture_size, texture_size), color='grey')


class map_layer:
    """
    Class used to generate a texture image from MAP tiles.
    """
    def __init__(self, center_x : int, center_y : int, z : int, texture_size : int, db : tile_db):
        """
        Parameters
        ----------
        center_x : int
            The x-coordinate of the grid center [web mercator].
        center_y : int
            The y-coordinate of the grid center [web mercator].
        z : int
            The zoom level.
        texture_size : int
            The size of the texture image (NxN).
        db : tile_db
            The tile database.
        """

        self.z = z
        self.db = db

        # Set center (match formula in dem_layer)
        # Need to adjust zoom level with an offset dependent on DEM grid size vs. MAP texture size
        z_offset = PT_SETTINGS['dem_preset']['grid_size'].bit_length() - PT_SETTINGS['map_preset']['texture_size'].bit_length()
        center_mask = ptl.mask(self.z + z_offset + PT_DEM_TILE_RES_LOG2 - 1)
        self.xc = center_x & center_mask
        self.yc = center_y & center_mask

        # LSB (step)
        self.step = ptl.lsb(self.z + PT_MAP_TILE_RES_LOG2)
        self.tstep = ptl.lsb(self.z)

        # Texture size
        self.texture_size = texture_size
        self.texture_size_half = texture_size >> 1

        # Top-left in map coord
        self.x0 = self.xc - self.texture_size_half * self.step
        self.y0 = self.yc - self.texture_size_half * self.step

        # Texture size in map coords
        self.xw = self.texture_size * self.step
        self.yw = self.texture_size * self.step


    def get_uv(self, x : int, y : int) -> tuple:
        """
        Gets U/V coordinates for a given point (x, y) based on the layer's position and size.

        Parameters
        ----------
        x : int
            The x-coordinate of the point [web mercator].
        y : int
            The y-coordinate of the point [web mercator].

        Returns
        -------
        tuple
            The U/V coordinates.
        """
        u = float(x - self.x0) / self.xw
        v = 1.0 - float(y - self.y0) / self.yw
        return (u, v)


    def get_tiles(self) -> set:
        """
        Gets the set of tiles covered by the texture.

        Returns
        -------
        set
            A set of tile descriptors.
        """
        tiles = set()
        for iy in range(-self.texture_size_half, self.texture_size_half + 1, PT_MAP_TILE_RES):
            y = self.yc + iy * self.step
            for ix in range(-self.texture_size_half, self.texture_size_half + 1, PT_MAP_TILE_RES):
                x = self.xc + ix * self.step
                tx, ty = ptl.tile(x, y, self.z)
                tiles.add((tx, ty, self.z))
        return tiles


    def preload_tiles(self) -> None:
        """
        Preloads the tiles covered by the texture.
        """
        self.db.preload_tiles(self.get_tiles())


    def generate(self, prev_layer : any) -> None:
        """
        Generates the texture image for the layer by merging the covered tiles.

        Parameters
        ----------
        prev_layer : any
            The previous layer in the hierarchy.
        """

        # Preload tiles
        self.preload_tiles()

        # Init texture image - take center rect from previous layer
        crop_size_half = self.texture_size >> ((self.z - prev_layer.z) + 1)
        crop_center = self.texture_size >> 1
        crop = prev_layer.image.copy().crop((
            crop_center - crop_size_half, crop_center - crop_size_half, 
            crop_center + crop_size_half, crop_center + crop_size_half
        ))
        merged = crop.resize((self.texture_size, self.texture_size))

        # Merge tiles to texture
        for iy in range(-self.texture_size_half, self.texture_size_half + 1, PT_MAP_TILE_RES):
            y = self.yc + iy * self.step
            for ix in range(-self.texture_size_half, self.texture_size_half + 1, PT_MAP_TILE_RES):
                x = self.xc + ix * self.step

                # Get tile
                tx, ty = ptl.tile(x, y, self.z)
                tile = self.db.get_tile(tx, ty, self.z)
                if tile is None:
                    continue

                # Calculate tile top-left in texture coordinates
                tx, ty = ptl.tile_no_wrap_x(x, y, self.z)
                tx = ptl.shift(self.z + PT_MAP_TILE_RES_LOG2, tx * self.tstep - self.x0)
                ty = ptl.shift(self.z + PT_MAP_TILE_RES_LOG2, ty * self.tstep - self.y0)

                # Merge tile into texture image
                merged.paste(tile, (tx, ty, tx + PT_MAP_TILE_RES, ty + PT_MAP_TILE_RES))

        # Flip Y to match Blender UV coordinates
        self.image = merged.transpose(Image.FLIP_TOP_BOTTOM)


def build_maps(map_tile_url : str, status_callback : callable) -> list:
    """
    Builds MAP layers from MAP tiles.

    Parameters
    ----------
    map_tile_url : str
        The URL for the MAP tile data.
    status_callback : callable
        Callback for status updates during terrain generation.
    
    Returns
    -------
    list
        A list of generated MAP layers.
    """

    # Connect to tile database and cache
    mdb = tile_db(PT_MAP_DB_NAME, map_tile_url)

    # Try connection
    test_tile = mdb.get_tile(0, 0, 0, True)
    if test_tile is None:
        raise Exception('Cannot download from MAP tile source')

    # Build MAP layers from top to bottom
    layers = []
    z_layers = PT_SETTINGS['map_preset']['z_layers']
    prev_layer = init_map_layer(z_layers[0], PT_SETTINGS['map_preset']['texture_size'])
    for i in range(len(z_layers)):
        z = z_layers[i]
        status_callback(f'MAP layer {i + 1}/{len(z_layers)}')
        layer = map_layer(PT_SETTINGS['grid_center_x'], PT_SETTINGS['grid_center_y'], z, PT_SETTINGS['map_preset']['texture_size'], mdb)
        layer.generate(prev_layer)
        layers.append((z, layer))
        prev_layer = layer

    mdb.close()
    return layers

