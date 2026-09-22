"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    DEM layer generation from DEM tiles.

"""
from .constants import *
from .settings import *
from .dem_cache import dem_cache
from .tile_db import tile_db
from . import layer_arithmetics as ptl
import numpy as np
import math

class init_dem_layer:
    """
    Empty DEM layer used during build initialization
    """
    def __init__(self):
        return
    def is_inside(self, x : int, y : int) -> bool:
        return False
    def is_border(self, x : int, y : int) -> int:
        return 0

class dem_layer:
    """
    Class used to generate a 3D grid from DEM elevation data.
    It generates the grid vertices and faces in web mercator coordinates.
    """
    def __init__(self, center_x : int, center_y : int, z : int, grid_size : int, dcache : dem_cache):
        """
        Parameters
        ----------
        center_x : int
            The x-coordinate of the grid center [web mercator].
        center_y : int
            The y-coordinate of the grid center [web mercator].
        z : int
            The zoom level.
        grid_size : int
            The size of the grid (NxN)
        dcache : dem_cache
            The DEM cache to use for loading elevation data.
        """

        self.z = z
        self.dcache = dcache

        # Set grid center point aligned to elevation z
        # Use one step above actual zoom level to ensure grid alignment during build
        # Note that the center for map layers are related to this formula
        center_mask = ptl.mask(self.z + PT_DEM_TILE_RES_LOG2 - 1)
        self.xc = center_x & center_mask
        self.yc = center_y & center_mask

        # LSB (step)
        self.step = ptl.lsb(self.z + PT_DEM_TILE_RES_LOG2)

        # Grid bounds
        # Do not wrap coords, the database lookup will handle this.
        grid_size_half = grid_size >> 1
        self.x_min = self.xc - grid_size_half * self.step
        self.x_max = self.xc + grid_size_half * self.step
        self.y_min = self.yc - grid_size_half * self.step
        self.y_max = self.yc + grid_size_half * self.step


    def is_inside(self, x : int, y : int) -> bool:
        """
        Tests if a point is inside the grid.

        Parameters
        ----------
        x : int
            The x-coordinate of the point [web mercator].
        y : int
            The y-coordinate of the point [web mercator].

        Returns
        -------
        bool
            True if the point is inside the grid, False otherwise.
        """
        return (x >= self.x_min and x <= self.x_max and y >= self.y_min and y <= self.y_max)


    def is_border(self, x : int, y : int) -> int:
        """
        Tests if a point is on the border of the grid.

        Parameters
        ----------
        x : int
            The x-coordinate of the point [web mercator].
        y : int
            The y-coordinate of the point [web mercator].

        Returns
        -------
        int
            1 if the point is on the border, 0 otherwise.
            Do not use bool, since the return value is used in arithmetic operations during grid generation.
        """
        if (x == self.x_min or x == self.x_max):
            if (y >= self.y_min and y <= self.y_max):
                return 1
        if (y == self.y_min or y == self.y_max):
            if (x >= self.x_min and x <= self.x_max):
                return 1
        return 0


    def get_tiles(self) -> set:
        """
        Gets the set of tiles covered by the grid.

        Returns
        -------
        set
            A set of tile descriptors.
        """
        tiles = set()
        for y in range(self.y_min, self.y_max + 1, self.step * PT_DEM_TILE_RES):
            if not (ptl.valid_y(y) and ptl.valid_y(y + 1)):
                continue
            for x in range(self.x_min, self.x_max + 1, self.step * PT_DEM_TILE_RES):
                tx, ty = ptl.tile(x, y, self.z)
                tiles.add((tx, ty, self.z))
        return tiles


    def preload_tiles(self) -> None:
        """
        Preloads the tiles covered by the grid into the DEM cache.
        """
        self.dcache.preload_tiles(self.get_tiles())


    def filter_tiles(self, threshold : float = 1.0, median_size : int = 5) -> None:
        """
        Filters the tiles to remove erraneous 'spikes' in the DEM data.
        If a value differs from the median of its neighborhood by more than the threshold,
        it is replaced with the median value.

        Parameters
        ----------
        threshold : float, optional
            Threshold for detecting spikes, in relative grid units. Default is 1.0.
        median_size : int, optional
            Side length of the median filter neighborhood. Must be odd and >= 3.
        """
        if median_size < 3 or median_size % 2 == 0:
            raise ValueError('median_size must be an odd integer >= 3')

        # Convert the threshold from relative grid units to meters
        threshold *= ptl.lon_res(self.z + PT_DEM_TILE_RES_LOG2) # To meters

        # Merge all tiles in the current layer into one rectangular array,
        # filter the interior once, and then write the result back into each tile.
        tiles = list(self.get_tiles())
        if not tiles:
            return

        # Setup the merged array dimensions based on the tile extents
        txs = [tx for tx, ty, z in tiles]
        tys = [ty for tx, ty, z in tiles]
        min_tx = min(txs)
        max_tx = max(txs)
        min_ty = min(tys)
        max_ty = max(tys)
        tile_cols = max_tx - min_tx + 1
        tile_rows = max_ty - min_ty + 1
        merged = np.zeros((tile_rows * PT_DEM_TILE_RES, tile_cols * PT_DEM_TILE_RES), dtype=np.float32)

        # Merge all tiles into a single array for filtering
        tile_map = {}
        for tx, ty, z in tiles:
            dem = self.dcache.get_tile(tx, ty, z)
            r0 = (ty - min_ty) * PT_DEM_TILE_RES
            r1 = r0 + PT_DEM_TILE_RES
            c0 = (tx - min_tx) * PT_DEM_TILE_RES
            c1 = c0 + PT_DEM_TILE_RES
            merged[r0:r1, c0:c1] = dem
            tile_map[(tx, ty, z)] = (r0, r1, c0, c1)

        # Filter the merged array using a median filter
        pad = median_size // 2
        interior = merged[pad:-pad, pad:-pad]
        windows = np.lib.stride_tricks.sliding_window_view(merged, (median_size, median_size))
        median_interior = np.median(windows, axis=(-2, -1)).astype(merged.dtype)

        # Smooth the interior using a same-size averaging kernel
        kernel = np.ones((median_size, median_size), dtype=np.float32) / (median_size * median_size)
        smoothed_interior = np.sum(windows * kernel, axis=(-2, -1)).astype(merged.dtype)

        # Replace the interior with the smoothed values where the difference exceeds the threshold
        diff = np.abs(median_interior - interior)
        merged[pad:-pad, pad:-pad] = np.where(diff >= threshold, smoothed_interior, interior)

        # Restore the filtered data back into the individual tiles
        for tx, ty, z in tiles:
            if (tx, ty, z) not in tile_map:
                continue
            r0, r1, c0, c1 = tile_map[(tx, ty, z)]
            self.dcache.set_tile(tx, ty, z, merged[r0:r1, c0:c1].copy())


    def add_vertex(self, x : int, y : int, z : int) -> int:
        """
        Adds a new vertex to the grid and returns its index. If the vertex already exists, returns the existing index.
        
        Parameters
        ----------
        x : int
            The x-coordinate of the vertex [web mercator].
        y : int
            The y-coordinate of the vertex [web mercator].
        z : int
            The zoom level.

        Returns
        -------
        int
            The index of the vertex in the grid.
        """

        # Check if already in cache
        key = (x, y)
        vidx = self.verts_cache.get(key)
        if vidx is not None:
            return vidx

        # Not in cache, construct vertex and add to cache
        e = self.dcache.get_elevation(x, y, z)
        if PT_SETTINGS['clamp_to_sea_level'] and e < 0:
            e = 0
        self.verts.append((x, y, e))
        vidx = len(self.verts) - 1
        self.verts_cache[key] = vidx
        return vidx


    def generate(self, prev_layer : any) -> None:
        """
        Generates the grid vertices and faces for the DEM layer.

        Parameters
        ----------
        prev_layer : any
            The previous DEM layer, should be contained within the current layer.
        """

        # Preload tiles
        self.preload_tiles()

        # Filter tiles
        if PT_SETTINGS['dem_filter_spikes']:
            self.filter_tiles()

        # Generate grid faces
        self.verts = []
        self.faces = []
        self.verts_cache = {}
        z = self.z
        for y in range(self.y_min, self.y_max, self.step):
            y0 = y
            y1 = y + self.step
            yc = (y0 + y1) >> 1
            if not (ptl.valid_y(y0) and ptl.valid_y(y1)):
                continue
            for x in range(self.x_min, self.x_max, self.step):
                x0 = x
                x1 = x + self.step
                xc = (x0 + x1) >> 1

                # Test if face center is inside previous layer
                if (prev_layer.is_inside(xc, yc)):
                    continue

                # Add vertices and face
                # If an edge is at the border of the previous grid, add an extra vertex at the middle of the edge
                # Note that some vertices are duplicated, must be merged afterwards to get a smooth surface

                # Border status and mask                
                b0 = prev_layer.is_border(x0, y0)
                b1 = prev_layer.is_border(x1, y0)
                b2 = prev_layer.is_border(x1, y1)
                b3 = prev_layer.is_border(x0, y1)
                bmask = int(0)
                bmask += b0 << 0
                bmask += b1 << 1
                bmask += b2 << 2
                bmask += b3 << 3

                # Base points, clockwise
                i0 = self.add_vertex(x0, y0, z + b0)
                i1 = self.add_vertex(x1, y0, z + b1)
                i2 = self.add_vertex(x1, y1, z + b2)
                i3 = self.add_vertex(x0, y1, z + b3)

                # Add faces, special cases for border edges
                match bmask:
                    case 3:  # Border edge 0 <-> 1
                        i4 = self.add_vertex(xc, y0, z + 1)
                        self.faces.append([i0, i4, i3])
                        self.faces.append([i4, i1, i2])
                        self.faces.append([i2, i3, i4])
                    case 6:  # Border edge 1 <-> 2
                        i4 = self.add_vertex(x1, yc, z + 1)
                        self.faces.append([i0, i1, i4])
                        self.faces.append([i4, i2, i3])
                        self.faces.append([i3, i0, i4])
                    case 12: # Border edge 2 <-> 3
                        i4 = self.add_vertex(xc, y1, z + 1)
                        self.faces.append([i0, i1, i4])
                        self.faces.append([i1, i2, i4])
                        self.faces.append([i4, i3, i0])
                    case 9:  # Border edge 3 <-> 1
                        i4 = self.add_vertex(x0, yc, z + 1)
                        self.faces.append([i0, i1, i4])
                        self.faces.append([i1, i2, i4])
                        self.faces.append([i2, i3, i4])
                    case _:  # All other cases
                        self.faces.append([i0, i1, i2])
                        self.faces.append([i2, i3, i0])

        # Save centre height
        self.center_height = self.dcache.get_elevation(self.xc, self.yc, z)


def build_dems(dem_tile_url : str, status_callback : callable) -> list:
    """
    Builds the DEM layers for the current project settings.

    Parameters
    ----------
    dem_tile_url : str
        The URL for the DEM tile data.
    status_callback : callable
        Callback for status updates during terrain generation.

    Returns
    -------
    list
        A list of tuples containing the layer index and the corresponding DEM layer object.
    """

    # Connect to tile database and cache
    ddb = tile_db(PT_DEM_DB_NAME, dem_tile_url)
    dcache = dem_cache(ddb)

    # Try connection
    test_tile = ddb.get_tile(0, 0, 0, True)
    if test_tile is None:
        raise Exception('Cannot download from DEM tile source')

    # Build DEM layers from bottom to top
    layers = []
    z_layers = PT_SETTINGS['dem_preset']['z_layers']
    prev_layer = init_dem_layer()
    for i in range(len(z_layers)):
        z = z_layers[i]
        status_callback(f'DEM layer {i + 1}/{len(z_layers)}')
        layer = dem_layer(PT_SETTINGS['grid_center_x'], PT_SETTINGS['grid_center_y'], z, PT_SETTINGS['dem_preset']['grid_size'], dcache)
        layer.generate(prev_layer)
        layers.append((z, layer))
        prev_layer = layer

    ddb.close()
    return layers


