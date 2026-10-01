# Pipeline scripts

These are the Blender and Python scripts exactly as they were used to turn the Blender scene into the web scene. They are working scripts, not a tool. Paths are hard-coded to my machine and to a temporary working folder, and most settings come from environment variables. Read them as a record of what was done. If you want to reuse the approach, [gltf-transform](https://gltf-transform.dev/) or [gltfpack](https://github.com/zeux/meshoptimizer) will do most of it with one command.

Blender scripts were run headless: `blender -b <file.blend> --python <script.py>` (Blender 4.3.2). The others are plain Python 3 with numpy and Pillow.

## Stages

| Folder | Script | What it does |
|---|---|---|
| `1_light_rig` | `main_update.py` | In the source `.blend`: adds a face spotlight for each figure (SPOT 18°, parented to the figure) and links it only to that figure with Cycles light linking; adds three wall spotlights and an invisible blocker quad in the arch so the corridor stays dark. Saves only with `SAVE=1`. |
| | `cart_light.py` | Re-aims the shield's light at the centre of the oval and sets cone and energy. |
| `2_lettering` | `export_arrays.py` → `paper.py` → `grow.py` → `inner_sel.py` → `inner_grow.py` → `ink_inner.py` | Writes the Gogol quote onto the inner side of the scroll held by my figure (as if I were reading it): exports the mesh to arrays, finds the paper faces, unrolls a height field, and inks the text into the texture, mirrored for the inner side. |
| | `engrave.py` | Bakes the quote into the shield's base colour and normal maps (4096 px). |
| `3_decimate` | `dec_worker.py` | Queue worker: takes a job file (`todo → doing → done`), appends one object from the 6 GB source file (appending one at a time keeps memory low), applies Decimate (Collapse) with `ratio = target / triangles`, saves a small `.blend`. One worker processed all 46 jobs in 1,039 s. |
| | `dec_prot.py` | Re-decimates the two objects with lettering (the scroll figure and the shield). The text area is a vertex group; with `invert_vertex_group=True` and `vertex_group_factor=1000` the decimator leaves it alone. In the modifier, weight 1 means "simplify" and 0 means "keep". |
| `4_textures` | `resize_tex.py` | Resizes to 2560 px (Lanczos), removes duplicate images by SHA-1 (54 image slots → 38 files), writes the texture map. |
| | `webp_tex.py` | The same textures as WebP: quality 87 for colour, 95 for non-colour data, method 6. |
| `5_assemble` | `build_glb_webp.py` | Links the decimated meshes and WebP images and exports one GLB with Draco: compression level 7, quantization position 14 / normal 10 / texcoord 14 bits. |
| | `assemble.py` | Builds the compressed `.blend` and exports lights, camera and the blocker (converted to Y-up) to JSON for the viewer. |
| `6_first_viewer` | `build_web.py`, `viewer_template.html` | The first viewer, built for a sandbox that could not serve binary files: geometry as base64 chunks, images as separate files. The site viewer in [`../viewer`](../viewer) replaced it, but the per-figure light code started here. |
| `benchmarks` | `geo.py`, `tex.py`, `geo.json`, `tex.json` | Budget and codec tests on one figure (Barent Harmansen Bolhamer); the numbers quoted in the main README come from these JSON files. |

## Numbers

**Decimation targets:**
- 200,000 triangles for 33 objects;
- 150,000 for each of the 9 pikes (1,131,092 each in the source);
- three parts of one group proportionally.

The whole scene went from **76,959,568 to 8,536,698 triangles**, including the protected lettering.

**Text-protected decimation:**

| Object | Triangles | Kept untouched |
|---|---|---|
| Scroll figure | 1,862,866 → 305,512 | 105,512 faces (all 53,382 protected vertices) |
| Shield | 943,048 → 281,194 | 81,195 faces (all 41,050 protected vertices) |

**Codec test**, one 2560 px colour texture (`benchmarks/tex.json`):

| Format | Bytes | PSNR | SSIM |
|---|---|---|---|
| JPEG q85 | 1,057,107 | 38.01 | 0.9789 |
| WebP q85 | 737,970 | 38.14 | 0.9752 |
| WebP q90 | 1,035,716 | 39.62 | 0.9827 |
| KTX2 ETC1S | 1,259,064 | 33.81 | 0.9598 |

UASTC was not tested. One texture is not a benchmark.

**Geometry budget**, one figure with Draco (`benchmarks/geo.json`): 200k triangles → 657,528 bytes; 150k → 517,804 bytes. The figure's 8K texture alone was 12.4 MB, so textures, not polygons, set the download size.

## Steps that were done by hand

- The job files for `dec_worker.py`, which hold the per-object targets.
- The vertex group of the scroll's text area.
- The 4096 px scroll texture.
- Re-pointing two jobs to the protected meshes.
- Extracting the viewer's scene settings.
