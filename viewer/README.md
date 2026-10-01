# Viewer

This is the code of the page [pavljenko.ru/blogs/tools/night_watch_3d](https://pavljenko.ru/blogs/tools/night_watch_3d?lang=en). It uses three.js 0.160.1 (WebGLRenderer) and is bundled with esbuild into one classic script. The page itself is a widget in my site's builder (InSales), so the markup is a Liquid template.

| File | What it is |
|---|---|
| `сцена.js` | The scene: loading, lights, picking, cards, camera tools. |
| `запуск.js` | Inline bootstrap: sizes the widget and draws the loading screen. |
| `шаблон.liquid`, `стили.css` | Markup and styles of the widget. |
| `сборка.py` | Build: bundles the script with a content-hashed name, assembles `content.liquid`, writes a local test page `проверка/`. |
| `подготовка-файлов.py` | Splits the scene GLB into an image-free geometry file cut into 4 parts, plus two WebP sets: 2560 px for desktop and 1280 px (quality 82) for phones. |
| `файлы-на-сайте.json` | Addresses of the uploaded files on the site's CDN. |
| `данные/персонажи.json`, `персонажи-en.json` | The cards in Russian and English. The key is the model name; `_модели` maps unnamed Tripo meshes to keys. |
| `данные/кристаллы.json` | Positions of the marker above each figure, placed by hand. |
| `данные/ракурс.json` | The "original view" camera, matched to the painting. |
| `данные/сцена.json` | Lights, exposure and the blocker, exported from Blender (`pipeline/5_assemble/assemble.py`). |
| `данные/Кристалл.obj` | The marker model, made in Rhino. |

## Where things are in `сцена.js`

**Per-figure lights:**
- `FACE_DECL` and `FACE_CODE` (lines 134–166) are the shader chunks.
- `linkInto` (174) attaches them to a figure's material through `onBeforeCompile` and gives it its own `customProgramCacheKey`.
- `updateLinked` (193) moves the lights into view space every frame.
- `addLights` (226) decides which lights are linked and which stay global three.js lights.
- Of 44 lights from Blender (42 spots, 2 area lights), 38 are linked and 6 stay global, plus a hemisphere light.

**Arch blocker** (inside `FACE_CODE`): the segment from the pixel to the wall light is intersected with the plane of an invisible quad in the arch. If it hits the quad, that light is skipped. This works only for one flat occluder; it is not a general shadow.

**Background dimming** (inside `FACE_CODE`): after the global lights are accumulated, the background is multiplied by `mix(0.85, 0.2, smoothstep(1.1, 1.9, worldY))`. The wall spotlights are added after that and stay bright.

**Downloader** (from line 264):
- `FIRST = 15000`, `STALL = 12000`, `TRIES = 6`.
- An `AbortController` timer re-arms on every chunk, and a stalled download resumes with `Range: bytes=N-`.
- Geometry parts are written straight into one buffer at their offsets.
- Six downloads run in parallel.

**Picking:**
- `pick` (530) swaps in flat ID materials, renders a small window around the pointer with `setViewOffset` into a render target, and reads it back.
- The radius is 3 px for a mouse and 14 px for touch.

**Marker over the head:**
- `headOf` (477) takes the 99.5th percentile of vertex heights near the body axis, so pikes and banners do not lift the marker.
- The final positions were then set by hand in `данные/кристаллы.json`.

## Build

```bash
cd сборка && npm install && cd ..   # three 0.160.1 and esbuild
python3 сборка.py --локально        # script + local test page
python3 -m http.server 8765         # then open http://127.0.0.1:8765/проверка/
```

The scene files are not in this repository. `подготовка-файлов.py` expects the GLB at `файлы/исходник/сцена-исходная.glb`, and the full build expects the files to be on the CDN listed in `файлы-на-сайте.json`. I uploaded them to the site with separate admin automation, which is not included. Add `?nw-debug` to the page address to get `window.__spNw` for inspection.
