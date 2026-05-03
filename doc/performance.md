# PTerrain - Performance

Here follows some preformance figures for the generation of terrain meshes with PTerrain. They are provided here as a rough indication, it ultimately depends the current hardware and Internet connection. They are measured on a computer with an Intel i7 2.90GHz CPU and 64GB RAM. The map projection was set to Geocentric.

## Generation times, no data in download cache

| DEM/MAP-preset | Time (seconds) |
| --- | --- |
| Low/Low | 38 |
| Medium/Medium | 51 |
| High/High | 122 |

## Generation times, all data in download cache

| DEM/MAP-preset | Time (seconds) |
| --- | --- |
| Low/Low | 12 |
| Medium/Medium | 29 |
| High/High | 90 |

## Blender file size contribution from texture data

| MAP-preset | File size (MB) |
| --- | --- |
| Low | 63 |
| Medium | 78 |
| High | 110 |

## Blender file size contribution from mesh data

| DEM-preset | File size (MB) |
| --- | --- |
| Low | 26 |
| Medium | 96 |
| High | 352 |

## Vertices/triangles in mesh

| DEM-preset | Verts/tris |
| --- | --- |
| Low | 178k / 356k |
| Medium | 657k / 1317k |
| High | 2431k / 4861k |

---

### [Main page](../README.md)
- [Add-on installation](./installation.md)
- [Parameters](./parameters.md)
- [Data sources](./data-sources.md)
- [Performance](./performance.md)

