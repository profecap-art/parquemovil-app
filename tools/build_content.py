#!/usr/bin/env python3
"""Convierte el contenido en bruto (temas .md, tests .md/.psv, banco difícil .txt)
en un único JSON (app/data/content.json) que usa la app.

Valida: 3 opciones, una sola correcta, sin preguntas duplicadas, secciones existentes.
"""
import json, re, sys, os, hashlib, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'content', 'raw')
HARD = os.path.join(ROOT, 'content', 'hard')
OUT = os.path.join(ROOT, 'app', 'data', 'content.json')

TEMAS = [
    ('c01', 'comun', 1, 'La Constitución Española de 1978'),
    ('c02', 'comun', 2, 'El Gobierno y la Administración General del Estado'),
    ('c03', 'comun', 3, 'Régimen jurídico del personal en las Administraciones Públicas'),
    ('c04', 'comun', 4, 'El contrato de trabajo en la Administración Pública'),
    ('c05', 'comun', 5, 'Igualdad de género, discapacidad, dependencia e igualdad LGTBI'),
    ('e01', 'especifica', 1, 'El conductor: comportamiento, permisos y licencias, infracciones'),
    ('e02', 'especifica', 2, 'El vehículo: normas generales, condiciones técnicas, matriculación, documentación'),
    ('e03', 'especifica', 3, 'Seguridad activa y pasiva del vehículo'),
    ('e04', 'especifica', 4, 'La vía: partes, utilización, peligros concretos'),
    ('e05', 'especifica', 5, 'Velocidad: límites, adecuación, distancias entre vehículos'),
    ('e06', 'especifica', 6, 'Maniobras: incorporación, desplazamientos, adelantamientos, cambios de dirección'),
    ('e07', 'especifica', 7, 'Conducción nocturna y condiciones meteorológicas adversas'),
    ('e08', 'especifica', 8, 'Señales de circulación: tipos y significados'),
    ('e09', 'especifica', 9, 'Accidente de circulación, delitos contra la seguridad vial, alcohol y drogas'),
    ('e10', 'especifica', 10, 'Elementos del vehículo: descripción y funcionamiento'),
]

EMOJI_RE = re.compile('[\U0001F000-\U0001FAFF☀-➿️⭐✅❌⬆-⬇]')

CALLOUTS = [
    ('MUY PREGUNTADO', 'star'), ('IMPORTANTE', 'info'), ('Nota de rigor', 'rigor'),
    ('ERROR FRECUENTE', 'error'), ('Aviso', 'rigor'),
]

errors = []


def clean(s):
    s = EMOJI_RE.sub('', s)
    s = s.replace('‍', '')
    return re.sub(r'[ \t]+', ' ', s).strip()


def md_blocks(lines):
    """Convierte líneas markdown en bloques simples para la app."""
    blocks = []
    para = []
    table = []

    def flush_para():
        if para:
            blocks.append({'t': 'p', 'x': clean(' '.join(para))})
            para.clear()

    def flush_table():
        if table:
            rows = []
            for r in table:
                cells = [clean(c) for c in r.strip().strip('|').split('|')]
                if all(re.fullmatch(r':?-{2,}:?', c) or c == '' for c in cells):
                    continue
                rows.append(cells)
            if rows:
                blocks.append({'t': 'table', 'rows': rows})
            table.clear()

    for ln in lines:
        s = ln.rstrip('\n')
        st = s.strip()
        if st.startswith('|'):
            flush_para(); table.append(st); continue
        else:
            flush_table()
        if not st or st == '---':
            flush_para(); continue
        if st.startswith('>'):
            flush_para()
            txt = clean(st.lstrip('>').strip())
            kind = 'info'
            for key, k in CALLOUTS:
                if key.lower() in txt.lower()[:40]:
                    kind = k; break
            # quita la etiqueta inicial ("**MUY PREGUNTADO:**"): la app pinta su propia cabecera
            txt = re.sub(r'^\*\*\s*[^*]{2,30}?:?\s*\*\*:?\s*', '', txt) if re.match(r'^\*\*\s*(MUY|IMPORTANTE|Nota|ERROR|Aviso)', txt) else txt
            if blocks and blocks[-1]['t'] == 'call' and blocks[-1].get('cont'):
                blocks[-1]['x'] += ' ' + txt
            else:
                blocks.append({'t': 'call', 'k': kind, 'x': txt})
            continue
        m = re.match(r'^(\s*)[-*] (.*)', s)
        if m:
            flush_para()
            lvl = 1 if len(m.group(1)) >= 2 else 0
            blocks.append({'t': 'li', 'l': lvl, 'x': clean(m.group(2))})
            continue
        m = re.match(r'^\s*(\d+)\. (.*)', s)
        if m:
            flush_para()
            blocks.append({'t': 'ol', 'n': m.group(1), 'x': clean(m.group(2))})
            continue
        if st.startswith('#### '):
            flush_para(); blocks.append({'t': 'h4', 'x': clean(st[5:])}); continue
        para.append(st)
    flush_para(); flush_table()
    return blocks


def parse_tema(tid, path=None):
    path = path or os.path.join(RAW, f'tema-{tid}.md')
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    title = clean(lines[0].lstrip('# '))
    sections = []
    cur = None
    for ln in lines[1:]:
        m2 = re.match(r'^## (.*)', ln)
        m3 = re.match(r'^### (\d+(?:\.\d+)*)\.? (.*)', ln)
        if m3:
            cur = {'id': m3.group(1), 'title': clean(m3.group(2)), 'lines': [], 'lvl': 3}
            sections.append(cur); continue
        if m2 and not ln.startswith('###'):
            h = clean(m2.group(1))
            mm = re.match(r'^(\d+)\.\s*(.*)', h)
            if mm:
                sid, stitle = mm.group(1), mm.group(2)
            else:
                sid, stitle = 'F', h  # Fuentes y elaboración
            cur = {'id': sid, 'title': stitle, 'lines': [], 'lvl': 2}
            sections.append(cur); continue
        if cur is None:
            continue
        cur['lines'].append(ln)
    out = []
    for s in sections:
        b = md_blocks(s['lines'])
        out.append({'id': s['id'], 'title': s['title'], 'lvl': s['lvl'], 'blocks': b})
    return title, out


def parse_test_md(tid):
    path = os.path.join(RAW, f'test-{tid}.md')
    txt = open(path, encoding='utf-8').read()
    body, sheet = txt.split('## HOJA')
    qs = {}
    cur = None
    for ln in body.split('\n'):
        m = re.match(r'^(\d+)\. (.*)', ln)
        if m:
            cur = int(m.group(1)); qs[cur] = {'q': clean(m.group(2)), 'o': []}; continue
        m = re.match(r'^\s*([ABC])\) (.*)', ln)
        if m and cur:
            qs[cur]['o'].append(clean(m.group(2))); continue
        if ln.strip() and cur and not qs[cur]['o']:
            qs[cur]['q'] += ' ' + clean(ln)
    res = []
    for ln in sheet.split('\n'):
        m = re.match(r'^\|\s*(\d+)\s*\|\s*([ABC])\s*\|(.*)\|(.*)\|\s*$', ln)
        if not m:
            continue
        n = int(m.group(1)); letter = m.group(2)
        expl = clean(m.group(3)); sec = clean(m.group(4))
        if n not in qs:
            errors.append(f'{tid}: hoja {n} sin pregunta'); continue
        res.append(mk_q(tid, n, qs[n]['q'], qs[n]['o'], 'ABC'.index(letter), expl, sec, 'banco'))
    return res


def parse_test_psv(tid):
    path = os.path.join(RAW, f'test-{tid}.psv')
    res = []
    for ln in open(path, encoding='utf-8'):
        ln = ln.strip()
        if not ln:
            continue
        p = ln.split('|')
        if len(p) != 8:
            errors.append(f'{tid}: línea psv con {len(p)} campos: {ln[:60]}'); continue
        n, sec, ok, q, a, b, c, expl = p
        res.append(mk_q(tid, int(n), clean(q), [clean(a), clean(b), clean(c)], 'ABC'.index(ok), clean(expl), sec, 'banco'))
    return res


def parse_hard(tid):
    path = os.path.join(HARD, f'hard-{tid}.txt')
    if not os.path.exists(path):
        return []
    res = []
    chunks = open(path, encoding='utf-8').read().split('\n---')
    i = 0
    for ch in chunks:
        d = {}
        key = None
        for ln in ch.strip().split('\n'):
            m = re.match(r'^(Q|A|B|C|OK|WHY|TRAP|MEMO|SEC|REF):\s?(.*)', ln)
            if m:
                key = m.group(1); d[key] = m.group(2).strip()
            elif key and ln.strip():
                d[key] += ' ' + ln.strip()
        if not d:
            continue
        missing = [k for k in ('Q', 'A', 'B', 'C', 'OK', 'WHY') if k not in d]
        if missing:
            errors.append(f'hard-{tid}: faltan {missing} en {d.get("Q","?")[:50]}'); continue
        i += 1
        q = mk_q(tid, 900 + i, clean(d['Q']), [clean(d['A']), clean(d['B']), clean(d['C'])],
                 'ABC'.index(d['OK'].strip()), clean(d['WHY']), d.get('SEC', '-'), 'dificil')
        q['trap'] = clean(d.get('TRAP', ''))
        q['memo'] = clean(d.get('MEMO', ''))
        q['ref'] = clean(d.get('REF', ''))
        res.append(q)
    return res


def mk_q(tid, n, q, opts, ok, expl, sec, origin):
    sec = (sec or '-').strip()
    sec = re.sub(r'\s*\(.*\)\s*$', '', sec)  # "2.1 (ampliación)" -> "2.1"
    sec = sec.split('/')[0].strip()
    if not re.fullmatch(r'\d+(\.\d+)*', sec):
        sec = '-'
    if len(opts) != 3:
        errors.append(f'{tid}-{n}: {len(opts)} opciones')
    if origin == 'dificil':
        dif = 3
    else:
        dif = 1 if n <= 50 else 2
    return {'id': f'{tid}-{n:03d}', 't': tid, 'n': n, 's': sec, 'q': q, 'o': opts,
            'k': ok, 'e': expl, 'd': dif, 'src': origin}


C01_RANGES = [(1, 9, '2.2'), (10, 55, '2.3'), (56, 65, '2.4'), (66, 96, '2.5'), (97, 107, '2.6'),
              (108, 116, '2.7'), (117, 127, '2.8'), (128, 136, '2.9'), (137, 158, '2.10'),
              (159, 165, '2.11'), (166, 169, '2.12')]
C01_TIT = [('preliminar', '2.2'), ('título i:', '2.3'), ('derechos', '2.3'), ('corona', '2.4'), ('rey', '2.4'),
           ('cortes', '2.5'), ('congreso', '2.5'), ('senado', '2.5'), ('gobierno', '2.6'),
           ('judicial', '2.8'), ('justicia', '2.8'), ('cgpj', '2.8'), ('hacienda', '2.9'), ('territorial', '2.10'),
           ('ccaa', '2.10'), ('autonom', '2.10'), ('tribunal constitucional', '2.11'), ('tc:', '2.11'),
           ('reforma', '2.12'), ('disposici', '2.13')]


def map_c01(q):
    e = q['e'].lower()
    m = re.search(r'arts?\.\s*(\d+)', e)
    if m:
        a = int(m.group(1))
        for lo, hi, sid in C01_RANGES:
            if lo <= a <= hi:
                return sid
    for k, sid in C01_TIT:
        if k in e:
            return sid
    return '2.1'


def main():
    temas = []
    preguntas = []
    for tid, parte, num, short in TEMAS:
        title, secs = parse_tema(tid)
        sec_ids = {s['id'] for s in secs}
        temas.append({'id': tid, 'parte': parte, 'num': num, 'short': short, 'title': title, 'secs': secs})
        if os.path.exists(os.path.join(RAW, f'test-{tid}.psv')):
            qs = parse_test_psv(tid)
        else:
            qs = parse_test_md(tid)
        qs += parse_hard(tid)
        if tid == 'c01':
            for q in qs:
                if q['s'] == '-':
                    q['s'] = map_c01(q)
        for q in qs:
            if q['s'] != '-' and q['s'] not in sec_ids:
                top = q['s'].split('.')[0]
                if top in sec_ids:
                    q['s'] = top
                else:
                    errors.append(f"{q['id']}: sección {q['s']} no existe")
                    q['s'] = '-'
        preguntas += qs
    # duplicados
    seen = {}
    for q in preguntas:
        key = re.sub(r'\W+', '', q['q'].lower())
        if key in seen:
            errors.append(f"duplicada: {q['id']} ~ {seen[key]}")
        seen[key] = q['id']
        if len(set(o.lower() for o in q['o'])) != 3:
            errors.append(f"{q['id']}: opciones repetidas")
    btitle, bsecs = parse_tema(None, os.path.join(RAW, 'bases.md'))
    bases = {'title': btitle, 'secs': bsecs}
    data = {
        'version': datetime.date.today().isoformat(),
        'temas': temas,
        'preguntas': preguntas,
        'bases': bases,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    by = {}
    for q in preguntas:
        by.setdefault(q['t'], [0, 0])
        by[q['t']][0 if q['src'] == 'banco' else 1] += 1
    for k, v in by.items():
        print(k, 'banco', v[0], 'dificil', v[1])
    print('TOTAL', len(preguntas), 'preguntas;', os.path.getsize(OUT) // 1024, 'KB')
    if errors:
        print('\nAVISOS:', len(errors))
        for e in errors:
            print(' -', e)


if __name__ == '__main__':
    main()
