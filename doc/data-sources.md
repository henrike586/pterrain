# PTerrain - Data Sources

## DEM data
The DEM (Digital Elevation Model) data is downloaded as 256x256 PNG tiles from the Terrarium database at Amazon AWS. The elevation (in meters) are calculated from the RGB values using the following formula:

e = (256.0 * red + green + blue / 256.0) - 32768.0

This representation allows for sub-centimeter precision, but the actual data does not always meet this accuracy. The elevation data is also sometimes slightly corrupt, but can often be manually adjusted by editing the mesh data.

## MAP data
The map data is downloaded as 256x256 JPEG tiles from Google. The RGB values are used directly in Blender textures.

## Data URLs
The URLs used to download the data are available as settings under the preferences for the add-on. They can be changed to use other sources, as long as the tile format exactly match the current format.

## Data caching
The downloaded data tiles are stored in a local database cache under the directory '.pterrain' in the users home directory. This significanly speed-up the generation if the same data needs to be accessed again. The tiles are saved in compressed format, so they do not occupy a significant amount of disk space. It is safe to delete the cache at any point if needed.

---

### [Main page](../README.md)
- [Add-on installation](./installation.md)
- [Parameters](./parameters.md)
- [Data sources](./data-sources.md)
- [Performance](./performance.md)
