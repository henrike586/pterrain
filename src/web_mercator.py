"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    Web Mercator projection for transforming geographic coordinates.
    See https://en.wikipedia.org/wiki/Web_Mercator_projection

    Web Mercator coordinates (x, y) in 32-bit fixed point format, where the full range of x and y is [0, 2^32 - 1].
    x wraps around, y is truncated

"""
import math
from .constants import *

def lon2wmx(lon : float) -> int:
    """
    Converts a longitude value to a Web Mercator x-coordinate in 32-bit fixed point format.
    
    Parameters
    ----------
    lon : float
        The longitude value in radians.

    Returns
    -------
    int
        The Web Mercator x-coordinate in 32-bit fixed point format.
    """
    a = (lon + math.pi) / (2.0 * math.pi)
    return int(round(float(0x100000000) * a)) & 0xffffffff


def wmx2lon(x : int) -> float:
    """
    Converts a Web Mercator x-coordinate to a longitude value.

    Parameters
    ----------
    x : int
        The Web Mercator x-coordinate in 32-bit fixed point format.

    Returns
    -------
    float
        The longitude value in radians.
    """
    a = (int(x) & 0xffffffff) / float(0x100000000)
    return (2.0 * math.pi) * a - math.pi


def lat2wmy(lat : float) -> int:
    """
    Converts a latitude value to a Web Mercator y-coordinate in 32-bit fixed point format.

    Parameters
    ----------
    lat : float
        The latitude value in radians.

    Returns
    -------
    int
        The Web Mercator y-coordinate in 32-bit fixed point format.
    """
    if lat > 1.6:
        lat = 1.6
    if lat < -1.6:
        lat = -1.6
    a = (math.pi - math.log(math.tan(math.pi / 4.0 + lat / 2.0))) / (2.0 * math.pi)
    ia = int(round(a * float(0x100000000)))
    if ia < 0:
        ia = 0
    if ia > 0xffffffff:
        ia = 0xffffffff
    return ia


def wmy2lat(y : int) -> float:
    """
    Converts a Web Mercator y-coordinate to a latitude value.

    Parameters
    ----------
    y : int
        The Web Mercator y-coordinate in 32-bit fixed point format.

    Returns
    -------
    float
        The latitude value in radians.
    """
    if y < 0:
        y = 0
    if y > 0xffffffff:
        y = 0xffffffff
    a = float(y) / float(0x100000000)
    return 2.0 * (math.atan(math.exp(math.pi - 2.0 * math.pi * a)) - math.pi / 4.0)


class proj_web_mercator:
    """
    Class for projecting DEM vertices to 3D coordinates using a Web Mercator projection.
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
        self.cx = center_x
        self.cy = center_y
        self.lon_res = 2.0 * math.pi * PT_EARTH_RADIUS / float(1 << 32)
        self.z_offset = 0.0


    def name(self) -> str:
        """
        Returns the name of the projection.
        
        Returns
        -------
        str
            The name of the projection.
        """
        return "Web Mercator"
    

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
        return ((v[0] - self.cx) * self.lon_res, (self.cy - v[1]) * self.lon_res, v[2] + self.z_offset)
   

