"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    UV coordinate calculation for DEM layers based on MAP layers.

"""

# Gets U/V/map layer from MAP layers
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
