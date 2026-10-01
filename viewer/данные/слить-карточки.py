#!/usr/bin/env python3
"""Слить карточки из файла вида {"_модели": {...}, "ru": {ключ: карточка}, "en": {...}} в персонажи.json и персонажи-en.json.
Существующие ключи заменяются (так «Лунден» становится Ромбаутом Кемпом), новые дописываются в конец.
Запуск: python3 слить-карточки.py <файл.json>"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
src = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
for lang, fname in (('ru', 'персонажи.json'), ('en', 'персонажи-en.json')):
    f = HERE / fname
    d = json.loads(f.read_text(encoding='utf-8'))
    d['_модели'].update(src.get('_модели', {}))
    for k, v in src.get(lang, {}).items():
        d['персонажи'][k] = v
    s = json.dumps(d, ensure_ascii=False, indent=1)
    if '{{' in s or '{%' in s or '@@' in s:
        sys.exit('СТОП: в тексте есть {{, {% или @@')
    f.write_text(s + '\n', encoding='utf-8')
    print(fname, 'персонажей', len(d['персонажи']), 'псевдонимов моделей', len(d['_модели']))
