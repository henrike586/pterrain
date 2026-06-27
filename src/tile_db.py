"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    Downloading of tiles from public servers. They are stored in a local sqlite database for caching and quick access.

"""
import os
import io
import asyncio
import sqlite3
import requests
from .constants import *
from .settings import *
from .pillow_support import import_pillow
Image = import_pillow()

# Global variables (used in downloads)
g_url_header = { 'User-Agent' : f'PTerrain ({PT_VERSION})' }


async def _async_fetch_url(url, timeout=10.0):
    """
    Asynchronously fetch a single URL using the existing requests client.

    Parameters
    ----------
    url : str
        URL to download.
    timeout : float
        Request timeout in seconds.

    Returns
    -------
    content : bytes
    """
    print(url)
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, headers=g_url_header, timeout=timeout),
        )
        return (response.content)
    except Exception:
        return b''


async def fetch_urls_async(urls, timeout=10.0):
    """
    Download the content of all URLs concurrently.

    Parameters
    ----------
    urls : list[str]
        URLs to download.
    timeout : float
        Request timeout in seconds.

    Returns
    -------
    list[bytes]
        A list of downloaded tile contents as bytes.
    """
    tasks = [_async_fetch_url(url, timeout) for url in urls]
    return list(await asyncio.gather(*tasks))


class tile_db:
    """
    Class for managing a local tile database using sqlite. Tiles are stored as blobs in the database for caching and quick access.
    """
    def __init__(self, db_filename : str, url_format : str):
        """
        Parameters
        ----------
        db_filename : str
            The name of the SQLite database file. Saved in working directory.
        url_format : str
            The format string for generating tile URLs.
        """

        self.url_format = url_format

        # Create database and table
        self.db = sqlite3.connect(os.path.join(PT_WORK_DIR, db_filename))
        cur = self.db.cursor()
        cmd = 'CREATE TABLE IF NOT EXISTS tiles (key TEXT UNIQUE PRIMARY KEY, tile BLOB)'
        cur.execute(cmd)
        self.db.commit()


    def close(self) -> None:
        """
        Closes the database connection.
        """
        self.db.close()


    def unpack(self, blob : bytes) -> Image.Image:
        """
        Unpacks a tile blob and returns it as a PIL Image.

        Parameters
        ----------
        blob : bytes
            The tile blob to unpack.

        Returns
        -------
        Image.Image
            A PIL Image object.
        """
        image = Image.open(io.BytesIO(blob))
        return image


    def get_key(self, x : int, y : int, z : int) -> str:
        """
        Generates a unique key for a tile based on its coordinates and layer.

        Parameters
        ----------
        x : int
            The x-coordinate of the tile.
        y : int
            The y-coordinate of the tile.
        z : int
            The zoom level of the tile.

        Returns
        -------
        str
            The unique key for the tile.
        """
        return f'{x}:{y}:{z}'


    def insert_tile(self, key : str, blob) -> None:
        """
        Inserts a tile blob into the database.

        Parameters
        ----------
        key : str
            The unique key for the tile.
        blob : bytes
            The tile data as bytes.
        """
        cmd = 'INSERT OR REPLACE INTO tiles VALUES (?,?)'
        self.db.cursor().execute(cmd, (key, blob))
        self.db.commit()


    def fetch_tile(self, key : str) -> list:
        """
        Fetches a tile blob from the database based on its unique key.

        Parameters
        ----------
        key : str
            The unique key for the tile.

        Returns
        -------
        list
            A list of tile blobs matching the key.
        """
        cmd = 'SELECT tile FROM tiles WHERE key = ?'
        return self.db.cursor().execute(cmd, (key,)).fetchall()


    def get_tile(self, x : int, y : int, z : int, refetch : bool = False) -> Image.Image:
        """
        Gets a tile from the database or fetches it from the URL if not present.

        Parameters
        ----------
        x : int
            The x-coordinate of the tile.
        y : int
            The y-coordinate of the tile.
        z : int
            The zoom level of the tile.
        refetch : bool, optional
            Whether to refetch the tile even if it exists in the database.

        Returns
        -------
        Image.Image or None
            The requested tile as a PIL Image object, or None if the tile could not be retrieved.
        """

        url = self.url_format.format(x = x, y = y, z = z)

        # Query if tile exists in the database
        key = self.get_key(x, y, z)
        res = self.fetch_tile(key)
        if len(res) == 1 and not refetch:
            # Tile exists in database 
            if len(res[0][0]) > 1:
                return self.unpack(res[0][0])
            else:
                # Failed download from earlier
                return None
        else:
            # Fetch image
            res = requests.get(url, headers = g_url_header)            
            if res.status_code == 200:
                # Got image, save in database
                print('Fetch: ' + url)
                self.insert_tile(key, res.content)
                return self.unpack(res.content)
            else:
                # Store fail token
                print('Fail : ' + url)
                self.insert_tile(key, b'\x00')
                return None


    def preload_tiles(self, tiles : set) -> None:
        """
        Preloads a set of tiles into the database. Tiles that are not already in the database will be fetched from the URL and stored.

        Parameters
        ----------
        tiles : set of tuples
            A set of tile coordinates (x, y, z).
        """

        # Get uncached tiles (i.e. not in database)
        uncached = []
        for tile in tiles:
            res = self.fetch_tile(self.get_key(*tile))
            if len(res) == 1:
                continue
            uncached.append(tile)

        # Load uncached tiles in parallel
        ntiles = len(uncached)
        if ntiles == 0:
            return

        # Prepare download urls
        urls = []
        for tile in uncached:
            (x, y, z) = tile
            urls.append(self.url_format.format(x = x, y = y, z = z))

        # Download in batches
        res = asyncio.run(fetch_urls_async(urls, timeout=PT_TILE_DOWNLOAD_TIMEOUT))

        # Process result
        res_iter = iter(res)
        for tile in uncached:
            key = self.get_key(*tile)
            self.insert_tile(key, next(res_iter))
