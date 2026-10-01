#!/usr/bin/env python3
"""Сборка страницы «Ночной дозор» в 3D.

1. сцена.js + three.js 0.160.1 → один классический скрипт файлы/сайт/nightwatch-3d-<хэш>.js (esbuild).
   Имя с хэшем содержимого: InSales не принимает повторное имя файла, а так новая версия кода
   сама получает новое имя.
2. шаблон.liquid + стили.css + запуск.js + настройки сцены → content.liquid для виджета
   (заливка — node .playwright-insales/nightwatch-widget-put.mjs).
3. проверка/index.html — та же разметка с локальными адресами файлов: проверить сцену до заливки
   (python3 -m http.server в папке ночной-дозор, открыть /проверка/).

Адреса файлов на сайте — из файлы-на-сайте.json (итог заливки upload-account-files-bulk.mjs),
всё — через CDN InSales: не-картинки InSales называет адресом на корне сайта, а корень идёт через
защиту QRATOR (0,4–0,6 МБ/с, поток может встать); тот же файл на CDN — 3–5 МБ/с (замер 01.10.2026).
Файлов, которых там нет, сборка не пропустит — сначала залить.
Ещё сборка готовит данные/кристалл.json из Кристалл.obj владельца и вставляет базу персонажей
(данные/персонажи.json, английская — персонажи-en.json).

Запуск: python3 сборка.py            — всё
        python3 сборка.py --локально — только скрипт и страница проверки (без адресов сайта)
"""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE / 'файлы' / 'сайт'
DRACO_SRC = HERE / 'сборка' / 'node_modules' / 'three' / 'examples' / 'jsm' / 'libs' / 'draco' / 'gltf'
DRACO = {'wrapper': 'nightwatch-draco-wasm-wrapper-r160.js', 'wasm': 'nightwatch-draco-decoder-r160.wasm'}   # из three 0.160.1

TEXT = {
    'ru': {'of': 'из', 'files': 'Файлы сцены', 'geo': 'Распаковка геометрии', 'tex': 'Текстуры', 'gpu': 'Свет и первый кадр',
           'mbs': 'МБ/с', 'eta': 'ещё ≈ {t}', 'sec': 'с', 'min': 'мин',
           'errGl': 'Браузер не смог запустить трёхмерную графику (WebGL). Попробуйте другой браузер или устройство.',
           'errLost': 'Видеокарте не хватило памяти, и сцена остановилась. Обновите страницу; если повторится — откройте её на компьютере.',
           'errLoad': 'Сцену не удалось загрузить: {m}. Обновите страницу.', 'sources': 'Источники:'},
    'en': {'of': 'of', 'files': 'Scene files', 'geo': 'Unpacking geometry', 'tex': 'Textures', 'gpu': 'Lights and first frame',
           'mbs': 'MB/s', 'eta': '≈ {t} left', 'sec': 's', 'min': 'min',
           'errGl': 'Your browser could not start 3D graphics (WebGL). Please try another browser or device.',
           'errLost': 'The graphics card ran out of memory and the scene stopped. Reload the page; if it happens again, open it on a computer.',
           'errLoad': 'The scene failed to load: {m}. Please reload the page.', 'sources': 'Sources:'},
}


def crystal():
    """Кристалл.obj (Rhino, 42 треугольника) → данные/кристалл.json: плоские треугольники, центр в нуле, высота 1."""
    V, N, P, Nn = [], [], [], []
    for line in (HERE / 'данные' / 'Кристалл.obj').read_text(encoding='utf-8', errors='replace').splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == 'v':
            V.append(tuple(map(float, t[1:4])))                  # у Rhino после xyz ещё цвет — не нужен
        elif t[0] == 'vn':
            N.append(tuple(map(float, t[1:4])))
        elif t[0] == 'f':
            idx = [c.split('/') for c in t[1:]]
            for a in range(1, len(idx) - 1):                    # многоугольник → веер треугольников
                for c in (idx[0], idx[a], idx[a + 1]):
                    P.append(V[int(c[0]) - 1])
                    Nn.append(N[int(c[2]) - 1] if len(c) > 2 and c[2] else (0.0, 1.0, 0.0))
    lo = [min(v[i] for v in P) for i in range(3)]
    hi = [max(v[i] for v in P) for i in range(3)]
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    h = hi[1] - lo[1]
    out = {'p': [round((v[i] - c[i]) / h, 5) for v in P for i in range(3)], 'n': [round(x, 4) for v in Nn for x in v]}
    (HERE / 'данные' / 'кристалл.json').write_text(json.dumps(out, separators=(',', ':')), encoding='utf-8')
    print('кристалл: %d треугольников, пропорции %.2f × 1 × %.2f' % (len(P) // 3, (hi[0] - lo[0]) / h, (hi[2] - lo[2]) / h))


def cdn(rec):
    """Адрес файла на CDN InSales: files/1/<id mod 8192>/<id>/original/<имя> (проверено на всех файлах сцены)."""
    u = rec['url']
    if u.startswith('https://pavljenko.ru/'):
        return 'https://cdn.insales-shop.ru/files/1/%d/%d/original/%s' % (rec['id'] % 8192, rec['id'], u.rsplit('/', 1)[1])
    return u


def persons(lang):
    f = HERE / 'данные' / ('персонажи-en.json' if lang == 'en' else 'персонажи.json')
    if not f.exists():
        print('внимание: нет %s — на английской странице будет русская база' % f.name)
        f = HERE / 'данные' / 'персонажи.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    d.pop('_о_файле', None)
    return json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def bundle():
    esb = HERE / 'сборка' / 'node_modules' / '.bin' / 'esbuild'
    tmp = HERE / 'сборка' / 'scene.bundle.js'
    subprocess.run([str(esb), str(HERE / 'сцена.js'), '--bundle', '--format=iife', '--minify', '--target=es2020',
                    '--legal-comments=none', '--log-level=warning', '--outfile=' + str(tmp)],
                   check=True, cwd=str(HERE / 'сборка'),
                   env={**os.environ, 'NODE_PATH': str(HERE / 'сборка' / 'node_modules')})   # three лежит в сборка/node_modules
    data = tmp.read_bytes()
    name = 'nightwatch-3d-%s.js' % hashlib.sha1(data).hexdigest()[:8]
    for old in SITE.glob('nightwatch-3d-*.js'):
        if old.name != name:
            old.unlink()
    (SITE / name).write_bytes(data)
    tmp.unlink()
    for key, fname in DRACO.items():
        src = DRACO_SRC / ('draco_wasm_wrapper.js' if key == 'wrapper' else 'draco_decoder.wasm')
        shutil.copyfile(src, SITE / fname)
    print('скрипт сцены: %s, %.0f КБ' % (name, len(data) / 1024))
    return name


def config(url):
    opis = json.loads((SITE / 'опись.json').read_text(encoding='utf-8'))
    scene = json.loads((HERE / 'данные' / 'сцена.json').read_text(encoding='utf-8'))
    return {
        'scene': scene,
        'geo': [{'url': url(k['имя']), 'size': k['байт']} for k in opis['куски']],
        'tex': [{'uri': t['uri'], 'd': {'url': url(t['d']['имя']), 'size': t['d']['байт']},
                 'm': {'url': url(t['m']['имя']), 'size': t['m']['байт']}} for t in opis['текстуры']],
        'draco': {'wrapper': url(DRACO['wrapper']), 'wasm': url(DRACO['wasm'])},
        'text': TEXT,
        # точки кристаллов со стенда владельца (?nw-stand → «Скопировать результат»): ключ → [x, y, z]
        'crystals': json.loads((HERE / 'данные' / 'кристаллы.json').read_text(encoding='utf-8')) if (HERE / 'данные' / 'кристаллы.json').exists() else {},
        # «Оригинальный ракурс» со стенда ракурса (?nw-debug → «Скопировать ракурс»): {"pos": […], "target": […]}
        'view': json.loads((HERE / 'данные' / 'ракурс.json').read_text(encoding='utf-8')) if (HERE / 'данные' / 'ракурс.json').exists() else None,
    }


def lg(w, h, scales=(-18, -22, -26)):
    """Преломление «жидкого стекла» для кнопок (как у кнопки баннера, spLG; работает в Chromium):
    карта смещений w×h — по x чёрный→красный, по y чёрный→зелёный, середина нейтральная (#808000)
    и к кромке растворяется; три прохода со сдвигом разной силы по каналам R/G/B дают радужную кромку."""
    r = min(w, h) / 2
    if w == h:      # круг: нейтраль до 70 % радиуса, к кромке — на нет
        shape = ("<radialGradient id='n' cx='0.5' cy='0.5' r='0.5'><stop offset='0' stop-color='#808000'/>"
                 "<stop offset='0.7' stop-color='#808000'/><stop offset='1' stop-color='#808000' stop-opacity='0'/></radialGradient>")
        body = f"<rect width='{w}' height='{h}' fill='url(#n)'/>"
    else:           # капсула: та же нейтраль — скруглённый прямоугольник с размытой кромкой
        shape = "<filter id='b' x='-20%' y='-50%' width='140%' height='200%'><feGaussianBlur stdDeviation='2.6'/></filter>"
        i = 3.4
        body = f"<rect x='{i}' y='{i}' width='{w - 2 * i:g}' height='{h - 2 * i:g}' rx='{r - i:g}' fill='#808000' filter='url(#b)'/>"
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}'><defs>"
           "<linearGradient id='x' x1='0' x2='1' y1='0' y2='0'><stop offset='0' stop-color='#000'/><stop offset='1' stop-color='#f00'/></linearGradient>"
           "<linearGradient id='y' x1='0' x2='0' y1='0' y2='1'><stop offset='0' stop-color='#000'/><stop offset='1' stop-color='#0f0'/></linearGradient>"
           f"{shape}</defs><rect width='{w}' height='{h}' fill='url(#x)'/>"
           f"<rect width='{w}' height='{h}' fill='url(#y)' style='mix-blend-mode:screen'/>{body}</svg>")
    from urllib.parse import quote
    href = 'data:image/svg+xml;utf8,' + quote(svg, safe="'/=:;,.-()")
    ch = ('1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0', '0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0', '0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0')
    out = [f'<feImage x="0" y="0" width="{w}" height="{h}" preserveAspectRatio="none" result="m" href="{href}"/>']
    for n, (k, m) in enumerate(zip(scales, ch)):
        out.append(f'<feDisplacementMap in="SourceGraphic" in2="m" scale="{k}" xChannelSelector="R" yChannelSelector="G" result="d{n}"/>'
                   f'<feColorMatrix in="d{n}" type="matrix" values="{m}" result="c{n}"/>')
    out.append('<feBlend in="c0" in2="c1" mode="screen" result="c01"/><feBlend in="c01" in2="c2" mode="screen"/>')
    return ''.join(out)


def fill(tpl, cfg, bundle_url):
    css = (HERE / 'стили.css').read_text(encoding='utf-8').strip()
    boot = (HERE / 'запуск.js').read_text(encoding='utf-8').strip()
    cfg_json = json.dumps(cfg, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    pru, pen = persons('ru'), persons('en')
    for name, part in (('стили', css), ('запуск', boot), ('настройки', cfg_json), ('персонажи', pru), ('персонажи-en', pen)):
        if '{{' in part or '{%' in part:
            sys.exit(f'СТОП: в части «{name}» есть {{{{ или {{% — Liquid примет это за свой код')
    out = (tpl.replace('@@CSS@@', css).replace('@@BOOT@@', boot).replace('@@CONFIG@@', cfg_json).replace('@@BUNDLE@@', bundle_url)
           .replace('@@PERSONS_RU@@', pru).replace('@@PERSONS_EN@@', pen)
           .replace('@@LG_CIRCLE@@', lg(45, 45)).replace('@@LG_PILL@@', lg(158, 45)))
    if '@@' in out:
        sys.exit('СТОП: остались незаменённые метки @@')
    return out


def render_liquid(src, en=False):
    """Хватает для этого шаблона: комментарий, assign и {% if nw_en %}…{% else %}…{% endif %}."""
    src = re.sub(r'\{%-? comment -?%\}.*?\{%-? endcomment -?%\}\s*', '', src, flags=re.S)
    src = re.sub(r"\{%-? if language\.locale == 'en' -?%\}.*?\{%-? endif -?%\}", '', src, flags=re.S)
    src = re.sub(r'\{%-? assign [^%]*-?%\}', '', src)
    src = re.sub(r'\{%-? if nw_en -?%\}(.*?)(?:\{%-? else -?%\}(.*?))?\{%-? endif -?%\}',
                 lambda m: m.group(1) if en else (m.group(2) or ''), src, flags=re.S)
    assert '{%' not in src and '{{' not in src, 'в шаблоне остался Liquid'
    return src


def main():
    local_only = '--локально' in sys.argv
    tpl = (HERE / 'шаблон.liquid').read_text(encoding='utf-8')
    crystal()
    name = bundle()

    # страница проверки: файлы с локального сервера, шапка-заглушка 86 px
    (HERE / 'проверка').mkdir(exist_ok=True)
    loc = fill(tpl, config(lambda n: '../файлы/сайт/' + n), '../файлы/сайт/' + name)
    for en in (False, True):
        body = render_liquid(loc, en)
        page = ('<!doctype html><html lang="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
                '<title>Проверка: Ночной дозор</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;700&display=swap">'
                '<style>@font-face{font-family:OnestLocal;src:local("Onest")} html,body{margin:0;background:#fff}'
                ' .layout[class*="widget_v4_header"]{height:86px;background:#000;color:#fff;display:flex;align-items:center;padding:0 5vw;font:500 15px Onest,Arial}'
                ' .sp-nw{--font:"Onest",Arial,sans-serif}</style></head><body>'
                '<div class="layout widget_v4_header">шапка сайта (заглушка)</div><div class="layout"><div class="layout__content">%s</div></div></body></html>') % ('en' if en else 'ru', body)
        (HERE / 'проверка' / ('index-en.html' if en else 'index.html')).write_text(page, encoding='utf-8')
    print('страница проверки: проверка/index.html и index-en.html')
    if local_only:
        return

    upl = HERE / 'файлы-на-сайте.json'
    files = json.loads(upl.read_text(encoding='utf-8')) if upl.exists() else {}
    need = [name, DRACO['wrapper'], DRACO['wasm']] + [k['имя'] for k in json.loads((SITE / 'опись.json').read_text(encoding='utf-8'))['куски']]
    for t in json.loads((SITE / 'опись.json').read_text(encoding='utf-8'))['текстуры']:
        need += [t['d']['имя'], t['m']['имя']]
    missing = [n for n in need if not (files.get(n) or {}).get('url')]
    if missing:
        sys.exit('СТОП: не залиты в «Файлы» (%d): %s' % (len(missing), ', '.join(missing[:6]) + (' …' if len(missing) > 6 else '')))
    out = fill(tpl, config(lambda n: cdn(files[n])), cdn(files[name]))
    (HERE / 'content.liquid').write_text(out, encoding='utf-8')
    print('content.liquid: %d знаков' % len(out))


if __name__ == '__main__':
    main()
