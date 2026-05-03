"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    Geocentric projection for projecting DEM vertices to 3D coordinates.
    See https://en.wikipedia.org/wiki/Earth-centered,_Earth-fixed_coordinate_system

"""
import math
from .constants import *
from .web_mercator import *

class proj_geocentric:
    """
    Class for projecting DEM vertices to 3D coordinates using a geocentric projection.
    The 3D coordinates are adapted for Blender's coordinate system, where the x-axis points east, 
    the y-axis points north, and the z-axis points up.
    """
    def __init__(self, center_x : int, center_y : int):
        """
        Parameters
        ----------
        center_x : int
            The x-coordinate of the projection center [web mercator].
        center_y : int
            The y-coordinate of the projection center [web mercator].
        """
        self.lonc = wmx2lon(center_x)
        self.latc = wmy2lat(center_y)
        self.c1 = math.cos(self.latc) 
        self.s1 = math.sin(self.latc) 
        self.z_offset = 0.0


    def name(self) -> str:
        """
        Returns the name of the projection.
        
        Returns
        -------
        str
            The name of the projection.
        """
        return "Geocentric"
    

    def set_z_offset(self, z_offset : float):
        """ 
        Sets the z-offset for the projection. This is used to adjust the height of the terrain in Blender.
        Parameters
        ---------- 
        z_offset : float
            The z-offset value to set.
        """
        self.z_offset = z_offset


    def project(self, v) -> tuple:
        """
        Projects a vertex from web mercator coordinates to 3D coordinates.
        
        Parameters
        ----------
        v : tuple
            A tuple containing the x, y, and z coordinates of the vertex [web mercator].

        Returns
        -------
        tuple
            A tuple containing the x, y, and z coordinates of the projected vertex.
        """
        lon = wmx2lon(v[0])
        lat = wmy2lat(v[1])
        r = PT_EARTH_RADIUS + v[2] + self.z_offset
        x = r * math.cos(lat) * math.cos(lon - self.lonc)
        y = r * math.cos(lat) * math.sin(lon - self.lonc)
        z = r * math.sin(lat)
        # Rotation around y-axis
        xr =  x * self.c1 + z * self.s1
        zr = -x * self.s1 + z * self.c1
        return (y, zr, xr - PT_EARTH_RADIUS)
    



        
