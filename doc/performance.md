# PTerrain - Performance

Here follows some preformance figures for the generation of terrain meshes with PTerrain. They are provided here as a rough indication, it ultimately depends the current hardware and Internet connection. They are measured on a computer with an Intel i7 2.90GHz CPU and 64GB RAM. The map projection was set to Geocentric, DEM spike suppression is on.

## Generation times, no data in download cache

| DEM/MAP-preset | Time (seconds) |
| --- | --- |
| Low/Low | 34 |
| Medium/Medium | 55 |
| High/High | 161 |
| Ultra/High | 393 |

## Generation times, all data in download cache

| DEM/MAP-preset | Time (seconds) |
| --- | --- |
| Low/Low | 11 |
| Medium/Medium | 34 |
| High/High | 111 |
| Ultra/High | 329 |

## Blender file size contribution from texture data (MAP)

| MAP-preset | File size (MB) |
| --- | --- |
| Low | 31 |
| Medium | 110 |
| High | 400 |

## Blender file size contribution from mesh data (DEM)

| DEM-preset | File size (MB) |
| --- | --- |
| Low | 26 |
| Medium | 96 |
| High | 352 |
| Ultra | 1290 |

## Vertices/triangles in mesh

| DEM-preset | Verts/tris |
| --- | --- |
| Low | 178k / 356k |
| Medium | 659k / 1317k |
| High | 2431k / 4861k |
| Ultra | 8925k / 17846k |

---

### [Main page](../README.md)
- [Add-on installation](./installation.md)
- [Parameters](./parameters.md)
- [Data sources](./data-sources.md)
- [Performance](./performance.md)

