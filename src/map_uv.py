"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    UV coordinate calculation for DEM layers based on MAP layers.

"""
from . import dem_layer

class map_uv_lookup:
    """
    Class for looking up UV coordinates for DEM vertices based on MAP layers.
    """
    def __init__(self, layers):
        """
        Parameters        
        ----------
        layers : list
             A list of tuples [z, map_layer].
        """
        self.layers = layers
        self.cur_z = 0


    def is_inside(self, u : float, v : float) -> bool:
        """
        Checks if given U/V coordinates are inside the current map layer.

        Parameters
        ----------
        u : float
            The U coordinate.
        v : float
            The V coordinate.

        Returns
        -------
        bool
            True if the coordinates are inside the layer, False otherwise.
        """
        return u >= 0.0 and u <= 1.0 and v >= 0.0 and v <= 1.0


    def get_layer_zoom(self, x : int, y : int) -> int:
        """
        Gets the zoom level of the outmost map layer that contains the given point (x, y).

        Parameters
        ----------
        x : int
            The x-coordinate of the point [web mercator].
        y : int
            The y-coordinate of the point [web mercator].

        Returns
        -------
        int
            The zoom level of the outmost map layer containing the point.
        """

        # Increase zoom level until not inside
        while True:
            # Try current layer
            (z, layer) = self.layers[self.cur_z]
            uv = layer.get_uv(x, y)
            if not self.is_inside(*uv):
                break 

            # Inside, try next
            next_layer = self.cur_z + 1
            if next_layer == len(self.layers):
                break # Cannot go futher inwards
            self.cur_z = next_layer

        # Decrease zoom level until inside
        while True:
            # Try current layer
            (z, layer) = self.layers[self.cur_z]
            uv = layer.get_uv(x, y)
            if self.is_inside(*uv):
                break 

            # Outside, try next
            next_layer = self.cur_z - 1
            if next_layer < 0:
                break # This should never happen... assert ?
            self.cur_z = next_layer

        return self.cur_z


    def get_uv(self, x : int, y : int, z : int) -> tuple:
        """
        Gets the U/V coordinates for a given point (x, y) at a specific zoom level.

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
        tuple[float, float]
            The U/V coordinates for the point in the specified layer.
        """
        (_, layer) = self.layers[z]
        return layer.get_uv(x, y)


def uv_calc(dlayer : dem_layer, map_layers : list) -> tuple:
    """
    Function that calculates UV coordinates for a DEM layer based on MAP layers.

    Parameters
    ----------
    dlayer : dem_layer
        The DEM layer for which to calculate UV coordinates.
    map_layers : list
        A list of map_layer objects used for UV calculation. 

    Returns
    -------    
    tuple[mat_indexes, uv_loops]

    mat_indexes : list
        A list of material indexes for each face in the DEM layer.
    uv_loops : list       
        A list of UV coordinates for each loop in the DEM layer faces.
    """

    # Setup UV lookup and allocate UV and material index arrays
    uv_lookup = map_uv_lookup(map_layers)
    uv_loops = [0] * len(dlayer.faces) * 3  # Triangles, 3 UVs per face
    mat_indexes = [0] * len(dlayer.faces)

    # Loop over faces in DEM layer
    i = 0; mat_idx = 0; uv_idx = 0
    for face in dlayer.faces:
        # First find common zoom level - the lowest zoom level that covers all vertices of the face
        common_zoom = 1000
        for vert_index in face:
            (x, y, e) = dlayer.verts[vert_index]
            layer_zoom = uv_lookup.get_layer_zoom(x, y)
            if layer_zoom < common_zoom:
                common_zoom = layer_zoom
        mat_indexes[mat_idx] = common_zoom
        mat_idx += 1

        # Then calculate UVs for the common zoom level 
        for vert_index in face:
            (x, y, e) = dlayer.verts[vert_index]
            uv = uv_lookup.get_uv(x, y, common_zoom)
            uv_loops[uv_idx] = uv
            uv_idx += 1

    return(mat_indexes, uv_loops)   
