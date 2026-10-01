/* «Ночной дозор» в 3D — сцена страницы /blogs/tools/night_watch_3d.
   Перенос первой версии просмотрщика (three.js 0.160.1): свет из Blender,
   «привязанные» источники внутри материалов, орбитальная камера — без изменений.
   Отличия от артефакта (решения владельца 01.10.2026):
   * на сцене нет интерфейса — ни плашки со статистикой, ни кнопок, ни подсказок;
   * загрузка — в фирменном стиле сайта (чёрный фон, узор), разметка и узор — в виджете;
   * файлы — из «Файлов» InSales; на телефонах и планшетах текстуры 1280 px и внизу надпись
     «Упрощённая мобильная версия».
   Собирается в один классический скрипт: python3 сборка.py (esbuild, формат iife). */
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import CRYSTAL from './данные/кристалл.json';                   // из Кристалл.obj владельца, собирает сборка.py

const box = document.querySelector('[data-sp-nw]');
if (box && !box.__spNwScene) {
  box.__spNwScene = true;
  run(box);
}

function run(box) {
  const CFG = JSON.parse(box.querySelector('[data-sp-nw-config]').textContent);
  const EN = box.getAttribute('data-lang') === 'en';
  const T = CFG.text[EN ? 'en' : 'ru'];
  const q = s => box.querySelector(s);
  const ui = {
    loader: q('.sp-nw__loader'), fill: q('.sp-nw__fill'), bar: q('.sp-nw__bar'), done: q('[data-nw="done"]'),
    total: q('[data-nw="total"]'), pct: q('[data-nw="pct"]'), step: q('[data-nw="step"]'), speed: q('[data-nw="speed"]'),
    err: q('.sp-nw__err'), note: q('.sp-nw__note'), stage: q('.sp-nw__stage'),
  };
  const DATA = CFG.scene;

  /* ── телефон или планшет — облегчённые текстуры; ?nw-tex=d|m — принудительно (для проверки) ── */
  const force = new URLSearchParams(location.search).get('nw-tex');
  const MOBILE = force ? force === 'm' : isMobile();
  if (MOBILE && ui.note) ui.note.hidden = false;

  const fmt = (n, d = 1) => n.toLocaleString(EN ? 'en-US' : 'ru-RU', { minimumFractionDigits: d, maximumFractionDigits: d });
  const MB = b => fmt(b / 1048576);
  const fail = msg => {
    ui.err.textContent = msg; ui.err.hidden = false;
    box.classList.add('is-error'); ui.loader.classList.remove('is-done'); ui.loader.hidden = false;
  };
  const setStep = (name, a, b) => { ui.step.textContent = b ? `${name} · ${a} ${T.of} ${b}` : name; };

  /* ── рендерер, сцена, камера ── */
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  } catch (e) {
    fail(T.errGl);
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.toneMappingExposure = Math.pow(2, DATA.exposure ?? 0) * (DATA.tune?.exposure ?? 1);
  ui.stage.appendChild(renderer.domElement);
  renderer.domElement.addEventListener('webglcontextlost', e => { e.preventDefault(); fail(T.errLost); });

  const scene = new THREE.Scene(); scene.background = new THREE.Color(0x000000);
  const cam = DATA.camera;
  const camera = new THREE.PerspectiveCamera(40, 1, 0.05, 120);
  const HFOV = 2 * Math.atan(cam.sensor / 2 / cam.lens), FRAME_ASPECT = cam.res[0] / cam.res[1];
  const home = { pos: new THREE.Vector3(...cam.pos), tgt: new THREE.Vector3(...cam.pos).addScaledVector(new THREE.Vector3(...cam.dir), DATA.tune?.targetDist ?? 10.5) };
  camera.position.copy(home.pos); camera.up.set(0, 1, 0);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(home.tgt); controls.enableDamping = true; controls.dampingFactor = 0.08;
  controls.minDistance = 0.8; controls.maxDistance = 30; controls.maxPolarAngle = Math.PI * 0.53;
  let dirty = true;
  const view = camera;                                        // камера кадра (на стенде кристаллов 01.10.2026 переключалась на вид сверху)
  const resizeHooks = [];                                     // холст кристалла подстраивается следом
  function resize() {
    const w = Math.max(1, ui.stage.clientWidth), h = Math.max(1, ui.stage.clientHeight), a = w / h;
    renderer.setSize(w, h, false); camera.aspect = a;
    // кадр картины целиком в окне при любой форме экрана
    const vfovFrame = 2 * Math.atan(Math.tan(HFOV / 2) / FRAME_ASPECT);
    camera.fov = THREE.MathUtils.radToDeg(a >= FRAME_ASPECT ? vfovFrame : 2 * Math.atan(Math.tan(HFOV / 2) / a));
    camera.updateProjectionMatrix(); dirty = true;
    for (const f of resizeHooks) f(w, h);
  }
  resize();
  if (window.ResizeObserver) new ResizeObserver(resize).observe(ui.stage);
  else window.addEventListener('resize', resize);
  controls.addEventListener('change', () => { dirty = true; });
  /* «Оригинальный ракурс»: ракурс владельца (данные/ракурс.json), пока его нет — исходная камера сцены */
  const VIEW = CFG.view && CFG.view.pos ? { pos: new THREE.Vector3(...CFG.view.pos), tgt: new THREE.Vector3(...CFG.view.target) } : home;
  const REDUCE = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  /* Появление (просьба владельца 01.10.2026): сцена открывается видом сверху под 45° на задние
     фигуры и сама плавно перелетает к «Оригинальному ракурсу», общий свет по ходу пролёта
     нарастает до выбранного. С «уменьшить движение» — сразу ракурс и свет. */
  const INTRO_MS = 4500, intro = !REDUCE && VIEW !== home;
  {
    const s = new THREE.Spherical().setFromVector3(VIEW.pos.clone().sub(VIEW.tgt));
    // начало: середина задних фигур (Медичи, фрейлины, Рембрандт), камера в 5,5 м спереди и сверху под 45°
    if (intro) { const t = new THREE.Vector3(-1.5, 2.0, -0.1); s.set(5.5, Math.PI / 4, s.theta); controls.target.copy(t); camera.position.setFromSpherical(s).add(t); }
    else { controls.target.copy(VIEW.tgt); camera.position.copy(VIEW.pos); }
    controls.update();
  }
  let tween = null, tweenDamp = true;
  /* «Оригинальный ракурс» — плавно и по дуге вокруг сцены, а не напрямик: из-за спины прямая
     прошла бы сквозь фигуры. Цель камеры едет по прямой, сама камера — по сфере вокруг неё
     (кратчайший поворот, расстояние — плавно в логарифме); ход — easeInOutCubic, 0,9–2,4 с. */
  const s0 = new THREE.Spherical(), s1 = new THREE.Spherical(), sNow = new THREE.Spherical(), vTmp = new THREE.Vector3();
  function goView(msFixed) {
    if (tween) { tween = null; controls.enableDamping = tweenDamp; }
    const t0 = controls.target.clone(), t1 = VIEW.tgt.clone();
    s0.setFromVector3(vTmp.copy(camera.position).sub(t0));
    s1.setFromVector3(vTmp.copy(VIEW.pos).sub(t1));
    const dTheta = Math.atan2(Math.sin(s1.theta - s0.theta), Math.cos(s1.theta - s0.theta));
    const turn = Math.hypot(dTheta, s1.phi - s0.phi), move = t0.distanceTo(t1) + Math.abs(Math.log(s1.radius / s0.radius));
    if (REDUCE || (turn < 1e-3 && move < 1e-3)) { camera.position.copy(VIEW.pos); controls.target.copy(VIEW.tgt); controls.update(); dirty = true; return; }
    const ms = msFixed || Math.min(2400, 900 + 650 * turn + 350 * Math.min(2, move));
    let start = 0;                                            // отсчёт — с первого показанного кадра (фоновая вкладка не съест пролёт)
    tweenDamp = controls.enableDamping; controls.enableDamping = false;   // остаток инерции от прежнего жеста не мешает
    tween = () => {
      const now = performance.now(); if (!start) start = now;
      const k = Math.min(1, (now - start) / ms), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      controls.target.lerpVectors(t0, t1, e);
      sNow.set(s0.radius * Math.pow(s1.radius / s0.radius, e), s0.phi + (s1.phi - s0.phi) * e, s0.theta + dTheta * e);
      camera.position.setFromSpherical(sNow).add(controls.target);
      dirty = true;
      if (k >= 1) { tween = null; controls.enableDamping = tweenDamp; }
    };
  }
  controls.addEventListener('start', () => { if (tween) { tween = null; controls.enableDamping = tweenDamp; } });

  /* ── свет из сцены Blender (как в артефакте) ──
     Источники без привязок — обычные источники сцены. Привязанные (лицо одной фигуры, настенные для фона)
     вшиваются в материал своих объектов, как light linking в Blender: каждый пиксель считает только свой свет. */
  const K = DATA.tune?.light ?? 1;
  const sanitize = n => THREE.PropertyBinding.sanitizeNodeName(n);
  const FACE_DECL = `
#ifdef NUM_FACE
uniform vec3 uFacePos[ NUM_FACE ]; uniform vec3 uFaceDir[ NUM_FACE ]; uniform vec3 uFaceColor[ NUM_FACE ]; uniform vec2 uFaceCone[ NUM_FACE ];
#ifdef FACE_BLOCKER
uniform mat4 uViewInv; uniform vec3 uFaceWorld[ NUM_FACE ]; uniform vec3 uBlkMin; uniform vec3 uBlkMax;
#endif
#ifdef BG_DIM
uniform float uBgWall; uniform float uBgFloor;
#endif
#endif`;
  const FACE_CODE = `
#ifdef BG_DIM
{ // фон: несвязанные источники и заполняющий свет доходят до него лишь частично (в Cycles его затеняют фигуры и фасад)
  vec3 pwd = ( uViewInv * vec4( geometryPosition, 1.0 ) ).xyz;
  float dim = mix( uBgFloor, uBgWall, smoothstep( 1.1, 1.9, pwd.y ) );
  reflectedLight.directDiffuse *= dim; reflectedLight.directSpecular *= dim; irradiance *= dim;
}
#endif
#ifdef NUM_FACE
for ( int fi = 0; fi < NUM_FACE; fi ++ ) {
  vec3 lv = uFacePos[ fi ] - geometryPosition; float dd = length( lv ); vec3 ldir = lv / max( dd, 1e-4 );
  float sp = smoothstep( uFaceCone[ fi ].x, uFaceCone[ fi ].y, dot( ldir, uFaceDir[ fi ] ) );
  #ifdef FACE_BLOCKER
  vec3 pw = ( uViewInv * vec4( geometryPosition, 1.0 ) ).xyz; vec3 lw = uFaceWorld[ fi ];
  float tt = ( uBlkMin.z - pw.z ) / ( lw.z - pw.z );
  if ( tt > 0.0 && tt < 1.0 ) { vec3 q = pw + tt * ( lw - pw ); if ( q.x > uBlkMin.x && q.x < uBlkMax.x && q.y > uBlkMin.y && q.y < uBlkMax.y ) sp = 0.0; }
  #endif
  if ( sp > 0.0 ) {
    IncidentLight fl; fl.direction = ldir; fl.color = uFaceColor[ fi ] * sp / max( dd * dd, 0.01 ); fl.visible = true;
    RE_Direct( fl, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
  }
}
#endif`;
  const linked = [];
  function spotParams(L) {
    const col = new THREE.Color().setRGB(L.color[0], L.color[1], L.color[2], THREE.LinearSRGBColorSpace);
    const inten = (L.type === 'AREA' ? L.energy / Math.PI : L.energy / (4 * Math.PI)) * K;
    const ang = L.type === 'AREA' ? 1.25 : L.angle, pen = L.type === 'AREA' ? 1 : Math.min(1, L.blend ?? 0.5);
    return { pos: new THREE.Vector3(...L.pos), toLight: new THREE.Vector3(...L.dir).negate(), color: col.multiplyScalar(inten), cone: new THREE.Vector2(Math.cos(ang), Math.cos(ang * (1 - pen))) };
  }
  function linkInto(mesh, lights, blocker) {
    const m = mesh.material, n = lights.length;
    const U = {
      uFacePos: { value: lights.map(() => new THREE.Vector3()) }, uFaceDir: { value: lights.map(() => new THREE.Vector3()) },
      uFaceColor: { value: lights.map(l => l.color) }, uFaceCone: { value: lights.map(l => l.cone) },
      uViewInv: { value: new THREE.Matrix4() }, uFaceWorld: { value: lights.map(l => l.pos) },
      uBlkMin: { value: new THREE.Vector3() }, uBlkMax: { value: new THREE.Vector3() },
      uBgWall: { value: DATA.tune?.bgWall ?? 1 }, uBgFloor: { value: DATA.tune?.bgFloor ?? 1 },
    };
    if (blocker) { U.uBlkMin.value.set(blocker.min[0], blocker.min[1], blocker.min[2]); U.uBlkMax.value.set(blocker.max[0], blocker.max[1], blocker.max[2]); }
    m.defines = Object.assign(m.defines || {}, { NUM_FACE: n }, blocker ? { FACE_BLOCKER: 1, BG_DIM: 1 } : {});
    m.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, U);
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\n' + FACE_DECL).replace('#include <lights_fragment_begin>', '#include <lights_fragment_begin>\n' + FACE_CODE);
    };
    m.customProgramCacheKey = () => 'linked-' + n + (blocker ? '-b' : '');
    m.needsUpdate = true;
    linked.push({ U, lights });
  }
  function updateLinked() {
    view.updateMatrixWorld(); const V = view.matrixWorldInverse;
    for (const { U, lights } of linked) {
      lights.forEach((l, i) => { U.uFacePos.value[i].copy(l.pos).applyMatrix4(V); U.uFaceDir.value[i].copy(l.toLight).transformDirection(V); });
      U.uViewInv.value.copy(view.matrixWorld);
    }
  }
  /* Ползунок «Изменить освещение»: три прожектора задника и общие источники — заливка справа,
     контровой сзади, свет на знамя и рассеянный. Ключевые на центральные фигуры (Key_*), акцент
     на девочку и личные прожекторы лиц не трогаем: как у Рембрандта, свет остаётся на центре
     и на девочке, остальные уходят в тень. k: 0 — общие погашены, 1 — как задумано, 4 — ярче
     (задник ×4, общие — до ×2, иначе рассеянный свет съедает светотень). */
  const wall = [], gen = [];
  let lightK = 1, lightRamp = null;
  function setLight(k) {
    lightK = k; const g = k <= 1 ? k : 1 + (k - 1) / 3;
    for (const w of wall) w.sp.color.copy(w.base).multiplyScalar(k);
    for (const o of gen) o.l.intensity = o.base * g;
    dirty = true;
  }
  function rampLight(to, ms) {                                // плавно к to; отсчёт — с первого показанного кадра
    const from = lightK; let start = 0;
    lightRamp = () => {
      const now = performance.now(); if (!start) start = now;
      const k = Math.min(1, (now - start) / ms);
      setLight(from + (to - from) * k * k * (3 - 2 * k));
      if (k >= 1) lightRamp = null;
    };
  }
  const LIGHT_KEY = 'sp-nw-light';
  const kOf = v => v <= 50 ? (v / 50) * (v / 50) : Math.pow(4, (v - 50) / 50);   // 0…50 — до темноты, 50…100 — ×1…×4
  let lightSaved = 50;
  try { const v = localStorage.getItem(LIGHT_KEY); if (v !== null && +v >= 0 && +v <= 100) lightSaved = +v; } catch (e) { /* без памяти браузера — середина */ }
  function addLights(rootObj) {
    const byName = {}; rootObj.traverse(o => { if (o.name) byName[o.name] = o; });
    const meshesOf = name => { const o = byName[sanitize(name)]; const out = []; o && o.traverse(m => { if (m.isMesh) out.push(m); }); return out; };
    const perMesh = new Map();
    let blocker = null;
    if (DATA.blocker) { const c = DATA.blocker; blocker = { min: [0, 1, 2].map(i => Math.min(...c.map(p => p[i]))), max: [0, 1, 2].map(i => Math.max(...c.map(p => p[i]))) }; }
    for (const L of DATA.lights) {
      const rec = L.receivers || [];
      if (rec.length === 1 && rec[0] === 'Картуш') {           // картуш: мягкий ровный свет, без ореола на стене за ним
        const col = new THREE.Color().setRGB(L.color[0], L.color[1], L.color[2], THREE.LinearSRGBColorSpace);
        const E = L.energy / (4 * Math.PI) / (L.aim_dist * L.aim_dist) * Math.max(0.2, DATA.tune?.cartoucheCos ?? 0.76);
        meshesOf('Картуш').forEach(m => { m.material.emissiveMap = m.material.map; m.material.emissive = col; m.material.emissiveIntensity = E / Math.PI * K; m.material.needsUpdate = true; });
        continue;
      }
      if (rec.length) {                                         // привязанный — в материалы своих получателей
        const sp = spotParams(L);
        if (rec.includes('Фон_сцена')) wall.push({ sp, base: sp.color.clone() });   // три прожектора задника — под ползунок «Изменить освещение»
        for (const r of rec) for (const m of meshesOf(r)) { if (!perMesh.has(m)) perMesh.set(m, []); perMesh.get(m).push(sp); }
        continue;
      }
      const col = new THREE.Color().setRGB(L.color[0], L.color[1], L.color[2], THREE.LinearSRGBColorSpace);
      let light;
      if (L.type === 'SPOT') light = new THREE.SpotLight(col, L.energy / (4 * Math.PI) * K, 0, L.angle, Math.min(1, L.blend ?? 0.5), 2);
      else if (L.type === 'POINT') light = new THREE.PointLight(col, L.energy / (4 * Math.PI) * K, 0, 2);
      else if (L.type === 'AREA') light = new THREE.SpotLight(col, L.energy / Math.PI * K, 0, 1.25, 1, 2);
      else if (L.type === 'SUN') light = new THREE.DirectionalLight(col, L.energy * K);
      else continue;
      light.position.set(...L.pos);
      if (light.target) { light.target.position.set(...L.pos).addScaledVector(new THREE.Vector3(...L.dir), 5); scene.add(light.target); }
      scene.add(light);
      if (!/^(Key|Accent)/.test(L.name)) gen.push({ l: light, base: light.intensity });   // общий — под ползунок
    }
    const bgMeshes = new Set(meshesOf('Фон_сцена'));
    for (const [m, lights] of perMesh) linkInto(m, lights, bgMeshes.has(m) ? blocker : null);
    const amb = DATA.tune?.ambient ?? 0.02;
    if (amb > 0) { const h = new THREE.HemisphereLight(0xffe2c0, 0x2a2018, amb); scene.add(h); gen.push({ l: h, base: h.intensity }); }
  }

  /* ── загрузка файлов с побайтовым прогрессом ──
     Геометрия — GLB без картинок, нарезан кусками; текстуры — отдельные WebP (набор d или m).
     Куски геометрии пишутся сразу на своё место в общем буфере, текстуры становятся blob-адресами,
     и загрузчик glTF получает их вместо имён tex_NN.webp. */
  const TEX = CFG.tex.map(t => ({ uri: t.uri, ...t[MOBILE ? 'm' : 'd'] }));
  const geoTotal = CFG.geo.reduce((s, f) => s + f.size, 0);
  let glb = new Uint8Array(geoTotal);
  let off = 0;
  const jobs = [
    ...CFG.geo.map(f => { const j = { url: f.url, size: f.size, at: off }; off += f.size; return j; }),
    ...TEX.map(t => ({ url: t.url, size: t.size, uri: t.uri })),
  ];
  const total = jobs.reduce((s, j) => s + j.size, 0);
  ui.total.textContent = MB(total);
  const urlMap = { 'draco_wasm_wrapper.js': CFG.draco.wrapper, 'draco_decoder.wasm': CFG.draco.wasm };
  let got = 0, filesDone = 0, lastPaint = 0;
  const t0 = performance.now();
  function showBytes(force) {
    const now = performance.now();
    if (!force && now - lastPaint < 80) return;
    lastPaint = now;
    const pct = total ? Math.min(100, got / total * 100) : 0;
    ui.done.textContent = MB(got); ui.pct.textContent = Math.floor(pct) + '%';
    ui.fill.style.transform = `scaleX(${(pct / 100).toFixed(4)})`; ui.bar.setAttribute('aria-valuenow', Math.floor(pct));
    setStep(T.files, filesDone, jobs.length);
    const s = (now - t0) / 1000;
    if (s > 1 && got > 0 && got < total) {
      const v = got / s, eta = (total - got) / v;
      ui.speed.textContent = `${MB(v)} ${T.mbs} · ` + T.eta.replace('{t}', eta < 60 ? Math.ceil(eta) + ' ' + T.sec : Math.ceil(eta / 60) + ' ' + T.min);
    } else if (got >= total) ui.speed.textContent = '';
  }
  /* Сторож на каждом файле: нет данных FIRST/STALL мс — запрос обрывается, файл докачивается
     с того же места (Range). 01.10.2026 загрузка у владельца замирала на последнем файле: куски
     геометрии шли с корня сайта через защиту QRATOR (0,4–0,6 МБ/с, поток мог встать без ошибки),
     а ожидание было без срока. Теперь все файлы идут с CDN, а зависший запрос не вечен. */
  const FIRST = 15000, STALL = 12000, TRIES = 6;
  async function fetchJob(j) {
    const out = j.at !== undefined ? glb.subarray(j.at, j.at + j.size) : new Uint8Array(j.size);
    let at = 0, noRange = false;                                // at — сколько байт файла уже есть
    for (let attempt = 0; ; attempt++) {
      const ctrl = new AbortController();
      let timer = 0, ranged = false;
      const arm = ms => { clearTimeout(timer); timer = setTimeout(() => ctrl.abort(), ms); };
      try {
        arm(FIRST);
        ranged = at > 0 && !noRange;
        if (at > 0 && !ranged) { got -= at; at = 0; }
        const res = await fetch(j.url, { credentials: 'omit', signal: ctrl.signal, headers: ranged ? { Range: `bytes=${at}-` } : undefined });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (ranged && res.status !== 206) { got -= at; at = 0; }  // докачку не дали — файл целиком
        if (!res.body || !res.body.getReader) {                 // старые браузеры: без потока
          const b = new Uint8Array(await res.arrayBuffer());
          if (at + b.length !== j.size) throw new Error('size');
          out.set(b, at); at += b.length; got += b.length;
        } else {
          const reader = res.body.getReader();
          arm(STALL);
          for (;;) {
            const { done, value } = await reader.read(); if (done) break;
            arm(STALL);
            if (at + value.length > out.length) throw new Error('size');
            out.set(value, at); at += value.length; got += value.length; showBytes();
          }
          if (at !== j.size) throw new Error('size');
        }
        clearTimeout(timer);
        if (j.uri) urlMap[j.uri] = URL.createObjectURL(new Blob([out], { type: 'image/webp' }));
        filesDone++; showBytes(true);
        return;
      } catch (e) {
        clearTimeout(timer);
        const timeout = ctrl.signal.aborted;
        if (e && e.message === 'size') { got -= at; at = 0; }  // размер не сошёлся — заново целиком
        else if (ranged && !timeout && e && e.name === 'TypeError') noRange = true;   // браузер не пустил Range — дальше без него
        showBytes(true);
        if (attempt >= TRIES - 1) throw new Error(`${timeout ? 'timeout' : e.message} (${j.url.split('/').pop().split('?')[0]})`);
        await new Promise(r => setTimeout(r, Math.min(4000, 700 * (attempt + 1))));
      }
    }
  }
  async function download() {
    setStep(T.files, 0, jobs.length); showBytes(true);
    let next = 0;
    const worker = async () => { while (next < jobs.length) await fetchJob(jobs[next++]); };
    await Promise.all(Array.from({ length: 6 }, worker));
  }

  /* ── разбор glTF: Draco в воркерах, текстуры из blob-адресов ── */
  const manager = new THREE.LoadingManager();
  manager.setURLModifier(url => urlMap[url.split('/').pop().split('?')[0]] || url);
  const draco = new DRACOLoader(manager);
  draco.setDecoderPath(''); draco.setDecoderConfig({ type: 'wasm' });
  draco.setWorkerLimit(Math.max(2, Math.min(6, (navigator.hardwareConcurrency || 4) - 1)));
  draco.preload();                                            // расшифровщик едет, пока качаются файлы

  function parse() {
    const gTot = DATA.stats.meshes, tTot = DATA.stats.images;
    let gDone = 0, tDone = 0;
    const upd = () => {
      if (gDone < gTot) setStep(T.geo, gDone, gTot);
      else if (tDone < tTot) setStep(T.tex, tDone, tTot);
      else setStep(T.gpu);
    };
    const orig = draco.decodeDracoFile.bind(draco);
    draco.decodeDracoFile = (buf, cb, ...rest) => orig(buf, g => { gDone++; upd(); cb(g); }, ...rest);
    const loader = new GLTFLoader(manager); loader.setDRACOLoader(draco);
    loader.register(parser => {
      const tl = parser.textureLoader, load = tl.load.bind(tl);
      tl.load = (url, onLoad, onProg, onErr) => load(url, t => { tDone++; upd(); onLoad && onLoad(t); }, onProg, e => { tDone++; upd(); onErr && onErr(e); });
      return { name: 'SP_TEXTURE_PROGRESS' };
    });
    upd();
    return new Promise((res, rej) => loader.parse(glb.buffer, '', res, rej));
  }

  download().then(parse).then(async gltf => {
    glb = null; draco.dispose();                             // буфер GLB и воркеры Draco больше не нужны
    const rootObj = gltf.scene;
    const maxAniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    const textures = new Set();
    rootObj.traverse(o => {
      if (!o.isMesh) return;
      const src = o.material; if (src.map) src.map.anisotropy = maxAniso;
      o.material = new THREE.MeshStandardMaterial({ map: src.map, normalMap: src.normalMap || null, roughness: src.roughness ?? 0.9, metalness: src.metalness ?? 0,
        roughnessMap: src.roughnessMap || null, metalnessMap: src.metalnessMap || null, side: src.side, name: src.name });
      if (src.normalMap && src.normalScale) o.material.normalScale.copy(src.normalScale);
      for (const t of [src.map, src.normalMap, src.roughnessMap, src.metalnessMap]) if (t) textures.add(t);
    });
    scene.add(rootObj);
    setStep(T.gpu);
    addLights(rootObj);
    setLight(intro ? 0 : kOf(lightSaved));                    // при пролёте общий свет нарастает с нуля
    updateLinked();
    /* плашки и кристалл готовятся до первого кадра: головы фигур считаются по вершинам, а после
       передачи в видеокарту копии вершин освобождаются (onUpload) — на телефоне это ≈0,2 ГБ */
    let figures = null;
    try { figures = setupFigures(rootObj); } catch (e) { console.error(e); }   // сцена работает и без плашек
    const keepArrays = /[?&]nw-debug/.test(location.search);   // проверкам нужны вершины
    rootObj.traverse(o => {
      if (!o.isMesh || keepArrays) return;
      const g = o.geometry;
      for (const a of Object.values(g.attributes)) a.onUpload(freeArray);
      if (g.index) g.index.onUpload(freeArray);
    });
    await new Promise(r => requestAnimationFrame(r));
    try { if (renderer.compileAsync) await renderer.compileAsync(scene, camera); } catch (e) { /* соберётся в первом кадре */ }
    /* все текстуры — в видеопамять сразу, затем копии картинок в обычной памяти освобождаются
       (иначе вкладка держит их второй раз: до 1 ГБ на компьютере) */
    for (const t of textures) renderer.initTexture(t);
    renderer.render(scene, view); dirty = false;
    /* копии картинок в обычной памяти больше не нужны: ImageBitmap закрываем, а <img> (так грузит
       любой Safari, включая все браузеры iPhone и iPad, в three 0.160) просто отпускаем */
    for (const t of textures) { const img = t.source && t.source.data; if (!img) continue; if (typeof img.close === 'function') img.close(); t.source.data = null; }
    for (const k in urlMap) if (urlMap[k].startsWith('blob:')) URL.revokeObjectURL(urlMap[k]);
    ui.loader.classList.add('is-done');
    box.classList.add('is-ready');
    setTimeout(() => { ui.loader.hidden = true; }, 700);
    if (figures) figures.warm();                               // шейдер выбора — заранее, не на первом нажатии
    setupTools();
    if (intro) { goView(INTRO_MS); rampLight(kOf(lightSaved), INTRO_MS); }
  }).catch(e => {
    console.error(e);
    const m = String((e && (e.message || (e.error && e.error.message))) || (e && e.type) || e);
    fail(T.errLoad.replace('{m}', m));
  });

  /* ── нажатие на фигуру: кристалл над ней и плашка снизу ──
     Какая фигура под пальцем — выясняется «по цвету»: сцена рисуется в невидимый кадр 1×1 пиксель,
     каждая фигура своим цветом-номером. Это точнее и быстрее луча по 8,5 млн треугольников. */
  let tick = null;                                            // покачивание кристалла, пока он виден
  function setupFigures(rootObj) {
    const DB = JSON.parse(q('[data-sp-nw-persons]').textContent);
    const P = DB['персонажи'] || {}, ALIAS = DB['_модели'] || {};
    const keyOf = o => { const n = o.userData.name || o.name; return P[n] ? n : (ALIAS[n] && P[ALIAS[n]] ? ALIAS[n] : null); };
    const meshes = [], parts = new Map(), keyFor = new Map();
    rootObj.traverse(o => { if (o.isMesh) meshes.push(o); });
    for (const m of meshes) {
      let k = null; for (let o = m; o && !k; o = o.parent) k = keyOf(o);
      if (k) { keyFor.set(m, k); if (!parts.has(k)) parts.set(k, []); parts.get(k).push(m); }
    }
    const keys = [...parts.keys()];
    const black = new THREE.MeshBasicMaterial({ color: 0x000000, toneMapped: false });
    const idMat = new Map(keys.map((k, i) => [k, new THREE.MeshBasicMaterial({ color: new THREE.Color().setRGB((i + 1) / 255, 0, 0, THREE.LinearSRGBColorSpace), toneMapped: false })]));
    const tmpColor = new THREE.Color();

    /* кристалл — модель владельца (Кристалл.obj), высотой с голову, фирменный салатовый.
       Рисуется на своём прозрачном холсте поверх сцены: пока он крутится, большая сцена
       (8,5 млн треугольников) не перерисовывается — иначе видеокарта работала бы без остановки. */
    const over = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    over.setPixelRatio(renderer.getPixelRatio());
    over.outputColorSpace = THREE.SRGBColorSpace; over.toneMapping = renderer.toneMapping; over.toneMappingExposure = renderer.toneMappingExposure;
    over.setClearColor(0x000000, 0);
    over.domElement.className = 'sp-nw__over'; over.domElement.setAttribute('aria-hidden', 'true');
    ui.stage.appendChild(over.domElement);
    const sizeOver = (w, h) => over.setSize(w, h, false);
    resizeHooks.push(sizeOver);
    sizeOver(Math.max(1, ui.stage.clientWidth), Math.max(1, ui.stage.clientHeight));
    const cScene = new THREE.Scene();
    cScene.add(new THREE.HemisphereLight(0xfff3dc, 0x1d2415, 1.1));
    const cLight = new THREE.DirectionalLight(0xffe7c4, 1.8); cLight.position.set(-3, 5, 8); cScene.add(cLight);
    const crystal = new THREE.Group(); crystal.visible = false; cScene.add(crystal);
    let overDirty = false;
    const cg = new THREE.BufferGeometry();
    cg.setAttribute('position', new THREE.Float32BufferAttribute(CRYSTAL.p, 3));
    cg.setAttribute('normal', new THREE.Float32BufferAttribute(CRYSTAL.n, 3));
    const cMesh = new THREE.Mesh(cg, new THREE.MeshStandardMaterial({ color: 0x96E354, emissive: 0x96E354, emissiveIntensity: 0.5, metalness: 0.15, roughness: 0.3, flatShading: true }));
    const cEdges = new THREE.LineSegments(new THREE.EdgesGeometry(cg, 1), new THREE.LineBasicMaterial({ color: 0xe6ffd2, transparent: true, opacity: 0.85, toneMapped: false }));
    crystal.add(cMesh, cEdges);
    const H = 0.34;                                           // высота кристалла, м сцены
    let current = null, base = 0, shownAt = 0;
    /* где голова: рамка фигуры не годится — пики и знамёна уходят выше головы и в сторону.
       Ось берём по корпусу (середина высоты), голову — как верх точек у этой оси. */
    const heads = new Map();
    function headOf(k) {
      if (heads.has(k)) return heads.get(k);
      const v = new THREE.Vector3(), xs = [], ys = [], zs = [];
      for (const m of parts.get(k)) {
        const pos = m.geometry.attributes.position, step = Math.max(1, Math.floor(pos.count / 40000));
        m.updateWorldMatrix(true, false);
        for (let i = 0; i < pos.count; i += step) { v.fromBufferAttribute(pos, i).applyMatrix4(m.matrixWorld); xs.push(v.x); ys.push(v.y); zs.push(v.z); }
      }
      let minY = Infinity, maxY = -Infinity, x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;   // без Math.min(...) — Safari не берёт больше 65 тыс. аргументов
      for (let i = 0; i < ys.length; i++) {
        if (ys[i] < minY) minY = ys[i]; if (ys[i] > maxY) maxY = ys[i];
        if (xs[i] < x0) x0 = xs[i]; if (xs[i] > x1) x1 = xs[i]; if (zs[i] < z0) z0 = zs[i]; if (zs[i] > z1) z1 = zs[i];
      }
      const top = Math.min(maxY, minY + 2.1), hgt = top - minY;
      const med = a => { const s = a.slice().sort((p, q) => p - q); return s[s.length >> 1]; };
      const bx = [], bz = [];
      for (let i = 0; i < ys.length; i++) if (ys[i] > minY + hgt * 0.45 && ys[i] < minY + hgt * 0.7) { bx.push(xs[i]); bz.push(zs[i]); }
      const cx = bx.length ? med(bx) : (x0 + x1) / 2, cz = bx.length ? med(bz) : (z0 + z1) / 2;
      const r2 = 0.22 * 0.22, hy = [];
      for (let i = 0; i < ys.length; i++) if (ys[i] <= top && (xs[i] - cx) ** 2 + (zs[i] - cz) ** 2 < r2) hy.push(ys[i]);
      hy.sort((p, q) => p - q);
      const head = hy.length ? hy[Math.floor(hy.length * 0.995)] : top;   // 99,5-й перцентиль: одиночные торчащие точки не в счёт
      const res = { x: cx, y: head, z: cz };
      heads.set(k, res);
      return res;
    }
    for (const k of keys) headOf(k);                           // сейчас, пока вершины ещё в памяти
    /* точки, которые владелец показал на стенде 01.10.2026 (данные/кристаллы.json): ключ → [x, y, z] центра кристалла;
       у остальных фигур — автоматически над головой */
    const MANUAL = Object.assign({}, CFG.crystals || {});
    const autoPos = k => { const h = headOf(k); return [h.x, h.y + 0.08 + H / 2, h.z]; };   // 8 см над головой
    const crystalAt = k => MANUAL[k] || autoPos(k);
    function placeCrystal(k) {
      const c = crystalAt(k);
      base = c[1];
      crystal.position.set(c[0], c[1], c[2]);
      if (!crystal.visible) shownAt = performance.now();
      crystal.visible = true;
    }
    const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    tick = () => {
      if (!crystal.visible) { if (overDirty) hideCrystal(); return; }
      const t = performance.now() / 1000, grow = Math.min(1, (performance.now() - shownAt) / 350);
      const e = reduce ? 1 : 1 - Math.pow(1 - grow, 3);
      crystal.scale.setScalar(H * e);
      if (!reduce) { crystal.rotation.y = t * 0.9; crystal.position.y = base + Math.sin(t * 2) * 0.04; }
      over.render(cScene, view); overDirty = true;
    };
    const hideCrystal = () => { crystal.visible = false; if (overDirty) { over.render(cScene, view); overDirty = false; } };

    /* rad — допуск в пикселях экрана: палец крупнее фигур на телефоне, поэтому вокруг точки касания
       рисуется квадрат (2·rad+1)² и берётся ближайшая к центру фигура */
    const targets = new Map();
    function pick(clientX, clientY, rad = 0) {
      const r = renderer.domElement.getBoundingClientRect(), x = Math.floor(clientX - r.left), y = Math.floor(clientY - r.top);
      if (x < 0 || y < 0 || x >= r.width || y >= r.height) return null;
      const n = 2 * rad + 1;
      if (!targets.has(n)) targets.set(n, { rt: new THREE.WebGLRenderTarget(n, n), buf: new Uint8Array(n * n * 4) });
      const { rt, buf } = targets.get(n);
      const saved = meshes.map(m => m.material);
      meshes.forEach(m => { const k = keyFor.get(m); m.material = k ? idMat.get(k) : black; });
      const cm = cMesh.material, ev = cEdges.visible;          // кристалл — часть своей фигуры
      if (current) cMesh.material = idMat.get(current);
      cEdges.visible = false;
      if (current) scene.add(crystal);                        // на время замера — в большой сцене, как часть фигуры
      const bg = scene.background; scene.background = null;
      const prevTarget = renderer.getRenderTarget(), prevAlpha = renderer.getClearAlpha(); renderer.getClearColor(tmpColor);
      view.setViewOffset(r.width, r.height, x - rad, y - rad, n, n);
      renderer.setRenderTarget(rt); renderer.setClearColor(0x000000, 1); renderer.clear();
      renderer.render(scene, view);
      renderer.readRenderTargetPixels(rt, 0, 0, n, n, buf);
      renderer.setRenderTarget(prevTarget); renderer.setClearColor(tmpColor, prevAlpha);
      view.clearViewOffset();
      meshes.forEach((m, i) => { m.material = saved[i]; });
      cMesh.material = cm; cEdges.visible = ev; scene.background = bg;
      if (crystal.parent !== cScene) cScene.add(crystal);
      let best = 0, bestD = Infinity;                          // строки буфера идут снизу вверх
      for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
        const id = buf[(j * n + i) * 4];
        if (!id || id > keys.length) continue;
        const d = (i - rad) ** 2 + (n - 1 - j - rad) ** 2;
        if (d < bestD) { bestD = d; best = id; }
      }
      return best ? keys[best - 1] : null;
    }

    /* плашка */
    const info = q('.sp-nw__info'), nameEl = q('.sp-nw__name'), metaEl = q('.sp-nw__orig'), bioEl = q('.sp-nw__bio');
    function fade() { bioEl.classList.toggle('is-more', bioEl.scrollHeight - bioEl.scrollTop - bioEl.clientHeight > 4); }
    bioEl.addEventListener('scroll', fade, { passive: true });
    function open(k) {
      const p = P[k];
      current = k;
      nameEl.textContent = p.name;
      const meta = [p.original && p.original !== '—' ? p.original : '', p.years && p.years !== '—' ? p.years : ''].filter(Boolean).join(' · ');
      metaEl.textContent = meta; metaEl.hidden = !meta;
      bioEl.textContent = '';
      for (const para of [...String(p.text || '').split(/\n+/), p.rembrandt || '']) {
        if (!para.trim()) continue;
        const el = document.createElement('p'); el.textContent = para.trim(); bioEl.appendChild(el);
      }
      if (p.sources && p.sources.length) {
        const s = document.createElement('p'); s.className = 'sp-nw__src'; s.append(T.sources + ' ');
        p.sources.forEach((u, i) => {
          const a = document.createElement('a'); a.href = u; a.target = '_blank'; a.rel = 'noopener';
          try { a.textContent = new URL(u).hostname.replace(/^www\./, ''); } catch (e) { a.textContent = u; }
          if (i) s.append(', '); s.appendChild(a);
        });
        bioEl.appendChild(s);
      }
      info.hidden = false; bioEl.scrollTop = 0;
      requestAnimationFrame(() => { info.classList.add('is-open'); fade(); });
      box.classList.add('is-info');
      placeCrystal(k);
    }
    function close() {
      if (!current) return;
      current = null; hideCrystal();
      info.classList.remove('is-open'); box.classList.remove('is-info');
      setTimeout(() => { if (!current) info.hidden = true; }, 260);
    }
    q('.sp-nw__close').addEventListener('click', close);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

    /* нажатие = короткое касание без сдвига; перетаскивание и щипок крутят сцену, как раньше */
    const el = renderer.domElement;
    let down = null, pointers = 0;
    el.addEventListener('pointerdown', e => { pointers++; down = pointers === 1 && (e.pointerType !== 'mouse' || e.button === 0) ? { x: e.clientX, y: e.clientY, t: performance.now() } : null; });
    el.addEventListener('pointerup', e => {
      pointers = Math.max(0, pointers - 1);
      const d = down; down = null;
      if (!d || Math.hypot(e.clientX - d.x, e.clientY - d.y) > (e.pointerType === 'mouse' ? 5 : 10) || performance.now() - d.t > 700) return;
      const k = pick(e.clientX, e.clientY, e.pointerType === 'mouse' ? 3 : 14);
      if (k) open(k); else close();
    });
    el.addEventListener('pointercancel', () => { pointers = Math.max(0, pointers - 1); down = null; });

    /* мышь: над фигурой — курсор-рука (проверка не чаще 10 раз в секунду) */
    if (window.matchMedia && matchMedia('(hover: hover) and (pointer: fine)').matches) {
      let last = 0, hoverT = 0;
      el.addEventListener('pointermove', e => {
        if (e.buttons) return;
        clearTimeout(hoverT);
        const run = () => { last = performance.now(); el.style.cursor = pick(e.clientX, e.clientY, 3) ? 'pointer' : ''; };
        const wait = 100 - (performance.now() - last);
        if (wait <= 0) run(); else hoverT = setTimeout(run, wait);
      });
      el.addEventListener('pointerleave', () => { clearTimeout(hoverT); el.style.cursor = ''; });
    }
    if (new URLSearchParams(location.search).has('nw-debug')) window.__spNw = { keys, open, close, pick, crystal, camera, controls, renderer, headOf, root: rootObj, scene, setLight, gen, wall };   // только для проверки
    return {
      warm() { const r = el.getBoundingClientRect(); pick(r.left + r.width / 2, r.top + r.height / 2); },
    };
  }

  /* ── кнопки по макету «Frame 9»: стрелка раскрывает «Оригинальный ракурс» и «солнце»;
     солнце раскрывает шкалу яркости трёх прожекторов задника (середина — свет, как задуман,
     с лёгким примагничиванием), на месте солнца — «ОК»: запомнить выбор в этом браузере. ── */
  function setupTools() {
    const tools = q('.sp-nw__tools'); if (!tools) return;
    const toggle = tools.querySelector('.sp-nw__toggle'), more = tools.querySelector('.sp-nw__more');
    const bView = tools.querySelector('[data-nw-tool="view"]'), bSun = tools.querySelector('[data-nw-tool="light"]');
    const range = tools.querySelector('.sp-nw__range input'), sunLabel = bSun.getAttribute('aria-label');
    // настоящее преломление стекла — Chromium с мышью (как у кнопки баннера), остальным — матовое стекло
    if (window.chrome && window.CSS && CSS.supports && CSS.supports('backdrop-filter', 'url(#spNwLGc)') && matchMedia('(hover: hover) and (pointer: fine)').matches) tools.classList.add('is-lg');
    let touched = false;                                       // двигали ли ползунок с открытия шкалы
    const mark = v => { range.value = v; range.style.setProperty('--v', v + '%'); };
    const show = v => { mark(v); lightRamp = null; setLight(kOf(v)); };
    mark(lightSaved);
    range.addEventListener('input', () => { let v = +range.value; if (Math.abs(v - 50) <= 4) v = 50; touched = true; show(v); });
    const isOpen = () => tools.classList.contains('is-open'), isLight = () => tools.classList.contains('is-light');
    function openLight(on, keep) {
      if (!on && isLight() && !keep && touched) show(lightSaved);   // закрыли без «ОК» — свет как был
      if (!on) touched = false;
      tools.classList.toggle('is-light', on);
      bSun.setAttribute('aria-expanded', String(on));
      bSun.setAttribute('aria-label', on ? bSun.getAttribute('data-ok') : sunLabel);
      range.tabIndex = on ? 0 : -1;
    }
    function setOpen(on) {
      if (!on) openLight(false);
      tools.classList.toggle('is-open', on);
      toggle.setAttribute('aria-expanded', String(on));
      more.inert = !on;
      bView.tabIndex = bSun.tabIndex = on ? 0 : -1;
    }
    toggle.addEventListener('click', () => setOpen(!isOpen()));
    bSun.addEventListener('click', () => {
      if (!isLight()) { openLight(true); return; }
      lightSaved = +range.value;                               // «ОК»
      try { localStorage.setItem(LIGHT_KEY, String(lightSaved)); } catch (e) { /* приватный режим — до перезагрузки */ }
      openLight(false, true);
    });
    bView.addEventListener('click', () => goView());
    document.addEventListener('keydown', e => { if (e.key !== 'Escape') return; if (isLight()) openLight(false); else if (isOpen()) setOpen(false); });
    setOpen(false);
    tools.hidden = false;
  }

  /* ── кадр рисуется только когда что-то изменилось ── */
  renderer.setAnimationLoop(() => {
    if (tween) tween();
    if (lightRamp) lightRamp();
    controls.update();
    if (tick) tick();
    if (dirty && box.classList.contains('is-ready')) { updateLinked(); renderer.render(scene, view); dirty = false; }
  });
}

function freeArray() { this.array = null; }                 // BufferAttribute.onUpload: вершины уже в видеокарте

function isMobile() {
  const ua = navigator.userAgent || '';
  if (/Android|iPhone|iPad|iPod|Mobile|Silk|Kindle|Opera Mini/i.test(ua)) return true;
  if (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1) return true;    // iPadOS представляется компьютером
  return window.matchMedia && matchMedia('(hover: none) and (pointer: coarse)').matches;
}
