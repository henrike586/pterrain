"""
    PTerrain - a progressive terrain add-on for Blender
    Copyright (C) 2026 Henrik Engström
    Licensed under GPL-3.0 License (https://www.gnu.org/licenses/gpl-3.0.html)   

    Downloading of tiles from public servers. They are stored in a local sqlite database for caching and quick access.

"""
import os
import io
import sqlite3
import requests
import threading
import concurrent.futures
from .constants import *
from .settings import *
from .pillow_support import import_pillow
Image = import_pillow()

# Global variables (used in threads)
g_url_header = { 'User-Agent' : f'PTerrain ({PT_VERSION})' }
g_lock = threading.Lock()


def tile_download_thread(url) -> bytes:
    """
    Thread function that downloads a tile from a URL.

    Parameters
    ----------
    url : str
        The URL of the tile to download.

    Returns
    -------    
    bytes        
        The content of the downloaded tile as bytes. If the download fails, returns a single null byte.
    """

    # Execute download
    res = requests.get(url, headers = g_url_header)            
    with g_lock:
        if res.status_code == 200:
            print('Fetch: ' + url)
            return res.content
        else:
            print('Fail: ' + url)
            return b'\x00'


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
        with concurrent.futures.ThreadPoolExecutor(PT_TILE_DOWNLOAD_BATCH_SIZE) as executor:
            res = [executor.submit(tile_download_thread, url) for url in urls]
            concurrent.futures.wait(res)

        # Process result
        res_iter = iter(res)
        for tile in uncached:
            key = self.get_key(*tile)
            self.insert_tile(key, next(res_iter)._result)
