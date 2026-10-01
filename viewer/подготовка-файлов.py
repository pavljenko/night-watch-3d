#!/usr/bin/env python3
"""Файлы сцены «Ночной дозор» для сайта из исходного GLB артефакта (63 МБ).

В артефакте картинки лежали внутри GLB, а геометрия ехала base64-текстом (так требовал
хостинг артефактов). Для сайта раскладка другая:

* геометрия — GLB без картинок (картинки в нём ссылаются на внешние имена tex_NN.webp),
  нарезан на 4 куска: грузятся параллельно и с честным прогрессом;
* текстуры — отдельными WebP в двух наборах: 2560 px (исходные байты, как в артефакте)
  для компьютера и 1280 px для телефонов и планшетов (4096 → 2048).

Результат — в файлы/сайт/ (в git не кладётся) + файлы/сайт/опись.json (размеры, sha1).

Запуск: python3 подготовка-файлов.py
"""
import hashlib
import io
import json
import pathlib
import struct

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / 'файлы' / 'исходник' / 'сцена-исходная.glb'
OUT = HERE / 'файлы' / 'сайт'
VER = 'v1'                  # InSales не принимает повторное имя файла — новая версия = новый суффикс
PARTS = 4                   # кусков геометрии
MOBILE_Q = 82               # качество WebP облегчённого набора


def pad4(b, fill=b'\0'):
    return b + fill * (-len(b) % 4)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    glb = SRC.read_bytes()
    magic, ver, total = struct.unpack('<4sII', glb[:12])
    assert magic == b'glTF' and ver == 2 and total == len(glb)
    jlen, jtype = struct.unpack('<I4s', glb[12:20])
    assert jtype == b'JSON'
    J = json.loads(glb[20:20 + jlen])
    blen, btype = struct.unpack('<I4s', glb[20 + jlen:28 + jlen])
    assert btype == b'BIN\0'
    BIN = glb[28 + jlen:28 + jlen + blen]

    # 1. картинки — наружу
    img_views = set()
    textures = []
    for i, im in enumerate(J['images']):
        bv = J['bufferViews'][im['bufferView']]
        data = BIN[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]
        img_views.add(im['bufferView'])
        uri = 'tex_%02d.webp' % i
        J['images'][i] = {'uri': uri, 'mimeType': im.get('mimeType', 'image/webp'), 'name': im.get('name', uri)}
        textures.append((i, uri, data))

    # 2. bufferView картинок убираются, остальные пересобираются подряд с выравниванием по 4
    keep = [k for k in range(len(J['bufferViews'])) if k not in img_views]
    remap = {old: new for new, old in enumerate(keep)}
    newbin = bytearray()
    views = []
    for old in keep:
        bv = dict(J['bufferViews'][old])
        chunk = BIN[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]
        newbin += b'\0' * (-len(newbin) % 4)
        bv['byteOffset'] = len(newbin)
        newbin += chunk
        views.append(bv)
    J['bufferViews'] = views
    J['buffers'][0]['byteLength'] = len(newbin)

    def fix(o):                                   # все ссылки на bufferView — на новые номера
        if isinstance(o, dict):
            for k, v in o.items():
                if k == 'bufferView' and isinstance(v, int):
                    assert v in remap, 'ссылка на вырезанный bufferView %d' % v
                    o[k] = remap[v]
                else:
                    fix(v)
        elif isinstance(o, list):
            for x in o:
                fix(x)
    fix({k: v for k, v in J.items() if k != 'images'})

    js = pad4(json.dumps(J, ensure_ascii=False, separators=(',', ':')).encode('utf-8'), b' ')
    bn = pad4(bytes(newbin))
    out = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(bn)) + struct.pack('<I4s', len(js), b'JSON') + js + struct.pack('<I4s', len(bn), b'BIN\0') + bn

    # 3. нарезка геометрии
    opis = {'версия': VER, 'glb': len(out), 'куски': [], 'текстуры': []}
    step = -(-len(out) // PARTS)
    for p in range(PARTS):
        part = out[p * step:(p + 1) * step]
        name = 'nightwatch-geo-%s-%d.bin' % (VER, p)
        (OUT / name).write_bytes(part)
        opis['куски'].append({'имя': name, 'байт': len(part), 'sha1': hashlib.sha1(part).hexdigest()})
    (OUT / ('nightwatch-geo-%s.glb' % VER)).write_bytes(out)   # целиком — для проверки, на сайт не идёт

    # 4. текстуры: 2560 — исходные байты; 1280 — уменьшенные
    for i, uri, data in textures:
        big = 'nightwatch-tex-%s-%02d-d.webp' % (VER, i)
        (OUT / big).write_bytes(data)
        im = Image.open(io.BytesIO(data))
        w, h = im.size
        small = im.convert('RGBA' if im.mode in ('RGBA', 'LA') else 'RGB').resize((w // 2, h // 2), Image.LANCZOS)
        buf = io.BytesIO()
        small.save(buf, 'WEBP', quality=MOBILE_Q, method=6)
        mob = 'nightwatch-tex-%s-%02d-m.webp' % (VER, i)
        (OUT / mob).write_bytes(buf.getvalue())
        opis['текстуры'].append({'uri': uri, 'имя': J['images'][i]['name'], 'размер': [w, h],
                                 'd': {'имя': big, 'байт': len(data)}, 'm': {'имя': mob, 'байт': buf.tell(), 'размер': [w // 2, h // 2]}})

    d = sum(t['d']['байт'] for t in opis['текстуры'])
    m = sum(t['m']['байт'] for t in opis['текстуры'])
    opis['итого'] = {'компьютер': len(out) + d, 'телефон': len(out) + m}
    json.dump(opis, open(OUT / 'опись.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('геометрия: %.1f МБ (%d кусков), текстуры 2560: %.1f МБ, 1280: %.1f МБ' % (len(out) / 2**20, PARTS, d / 2**20, m / 2**20))
    print('итого компьютер %.1f МБ, телефон %.1f МБ' % (opis['итого']['компьютер'] / 2**20, opis['итого']['телефон'] / 2**20))


if __name__ == '__main__':
    main()
