"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    Layer arithmetics.

    Operates on Web Mercator coordinates (x, y) in 32-bit fixed point format, where the full range of x and y is [0, 2^32 - 1].

    Zoom levels are represented as integers, where zoom level 0 corresponds to the entire world in a single tile, 
    and each increase in zoom level doubles the resolution (number of tiles) in both x and y directions.

    Tiles are typically 256x256 pixels, and the tile coordinates (tx, ty) for a given zoom level z can be 
    calculated from the Web Mercator coordinates (x, y) using bit shifts.

"""

def valid_y(y : int) -> bool:
    """
    Checks if a given y-coordinate is valid.

    Parameters
    ----------
    y : int
        The y-coordinate.

    Returns
    -------
    bool
        True if the y-coordinate is valid, False otherwise.
    """
    return (y >= 0 and y <= 0xffffffff)


def wrap_x(x : int) -> int:
    """
    Wraps a given x-coordinate to the valid range.

    Parameters    
    ----------
    x : int
        The x-coordinate.

    Returns
    -------
    int
        The wrapped x-coordinate.
    """
    return x & 0xffffffff


def lsb(z : int) -> int:
    """
    Gets the least significant bit (LSB) for a given zoom level.
    
    Parameters
    ----------
    z : int
        The zoom level.

    Returns
    -------
    int
        The least significant bit.
    """
    return (1 << (32 - z))


def mask(z : int) -> int:
    """
    Gets the mask for a given zoom level. 

    Parameters
    ----------
    z : int
        The zoom level.

    Returns
    -------
    int
        A mask containing 1s in the top bit down to the zoom level LSB, and 0s elsewhere.
    """
    return (-1 << (32 - z)) & 0xffffffff


def shift(z : int, v : int) -> int:
    """
    Shifts a value by the zoom level.

    Parameters    
    ----------
    z : int       
        The zoom level.
    v : int       
        The (0.32) value to shift.

    Returns
    -------
    int
        The shifted value.
    """
    return v >> (32 - z)


def tile(x : int, y : int, z : int) -> tuple[int, int]:
    """
    Calculates the tile coordinates for a given position and zoom level.

    Parameters
    ----------
    x : int
        The x-coordinate.
    y : int
        The y-coordinate.
    z : int
        The zoom level.

    Returns
    -------
    tuple[int, int]
        The tile coordinates (tx, ty).
    """
    tx = shift(z, wrap_x(x))
    ty = shift(z, y)
    return tx, ty


def tile_no_wrap_x(x : int, y : int, z : int) -> tuple[int, int]:
    """
    Calculates the tile coordinates for a given position and zoom level.
    Does not wrap the x-coordinate, so it can return values outside the normal tile range.

    Parameters
    ----------
    x : int
        The x-coordinate.
    y : int
        The y-coordinate.
    z : int
        The zoom level.

    Returns
    -------
    tuple[int, int]
        The tile coordinates (tx, ty).
    """
    tx = shift(z, x)
    ty = shift(z, y)
    return tx, ty


def tile_sub(x : int, y : int, z : int, tile_res_log2 : int) -> tuple[int, int]:
    """
    Calculates the sub-tile pixel coordinates for a given position and zoom level.

    Parameters
    ----------
    x : int
        The x-coordinate.
    y : int
        The y-coordinate.
    z : int
        The zoom level.
    tile_res_log2 : int
        The log2 of the tile resolution (number of pixels per tile).

    Returns
    -------
    tuple[int, int]
        The sub-tile pixel coordinates (sx, sy).
    """
    sx = shift(z + tile_res_log2, wrap_x(x))
    sy = shift(z + tile_res_log2, y)
    return sx & 0xff, sy & 0xff

