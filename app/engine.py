# -*- coding: utf-8 -*-
"""Motor pedagógico de la app (sin dependencias de Kivy, se puede probar en PC).

- Carga del contenido (temario + banco de preguntas).
- Progreso del alumno en JSON local.
- Repetición espaciada tipo Leitner.
- Selección de preguntas: por tema, fallos, dudas, test inteligente, recuperación, simulacros.
- Corrección con penalización (−1/3) e índice de preparación.
"""
import json
import os
import random
import re
import time
import datetime

INTERVALS = {1: 1, 2: 3, 3: 7, 4: 16, 5: 35}   # días hasta el siguiente repaso por caja
DOMINADA_STREAK = 3                            # aciertos seguidos para considerarla dominada

STOP = set('''a al algo ante con contra cual cuando de del desde donde el ella en entre era es esta este
esto ha hay la las le lo los mas más no o para pero por que qué se según ser si sí sin sobre son su sus
también tiene un una uno y ya debe puede caso general carácter forma cuál cuáles siguiente siguientes
respecto'''.split())


def today():
    return datetime.date.today().toordinal()


def norm_words(s):
    s = re.sub(r'\*\*|\[/?b\]', '', s.lower())
    return [w for w in re.findall(r'[a-záéíóúñü0-9,]+', s) if w not in STOP and len(w) > 2]


class Content:
    def __init__(self, path):
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        self.version = d['version']
        self.temas = d['temas']
        self.tema = {t['id']: t for t in self.temas}
        self.preguntas = d['preguntas']
        self.q = {q['id']: q for q in self.preguntas}
        self.bases = d['bases']
        self.by_tema = {}
        for q in self.preguntas:
            self.by_tema.setdefault(q['t'], []).append(q['id'])
        self.by_sec = {}
        for q in self.preguntas:
            self.by_sec.setdefault((q['t'], q['s']), []).append(q['id'])

    def comun(self):
        return [t for t in self.temas if t['parte'] == 'comun']

    def especifica(self):
        return [t for t in self.temas if t['parte'] == 'especifica']

    def label(self, tid):
        t = self.tema[tid]
        return ('Común' if t['parte'] == 'comun' else 'Específica') + f" · Tema {t['num']}"

    def section(self, tid, sid):
        for s in self.tema[tid]['secs']:
            if s['id'] == sid:
                return s
        return None

    def study_sections(self, tid):
        """Apartados "estudiables" (los que tienen contenido)."""
        return [s for s in self.tema[tid]['secs'] if s['blocks'] and s['id'] != 'F']

    def best_block(self, q):
        """Fragmento del temario más relacionado con la pregunta (para 'Explicación del concepto')."""
        sec = self.section(q['t'], q['s']) if q['s'] != '-' else None
        cands = []
        secs = [sec] if sec else self.study_sections(q['t'])
        for s in secs:
            for b in s['blocks']:
                if b['t'] in ('p', 'li', 'call', 'ol'):
                    cands.append((s, b))
        if not cands:
            return None, None
        qw = set(norm_words(q['q'] + ' ' + q['e'] + ' ' + q['o'][q['k']]))
        best, score = None, -1
        for s, b in cands:
            bw = set(norm_words(b['x']))
            sc = len(qw & bw) + (0.5 if b['t'] == 'call' else 0)
            if sc > score:
                best, score = (s, b), sc
        if score < 2 and sec is None:
            return None, None
        return best


class Store:
    """Progreso del alumno."""

    def __init__(self, path):
        self.path = path
        self.d = {}
        if os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as f:
                    self.d = json.load(f)
            except Exception:
                self.d = {}
        for k, v in (('q', {}), ('dudas', []), ('favq', []), ('favtema', []), ('studied', {}),
                     ('notes', {}), ('hist', []), ('days', {}), ('xp', 0), ('recent', []),
                     ('settings', {'theme': 'light', 'font': 1.0, 'name': ''}),
                     ('plan', {})):
            self.d.setdefault(k, v)

    def save(self):
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.d, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    # ---------- respuestas ----------
    def qs(self, qid):
        return self.d['q'].get(qid)

    def record(self, qid, ok, tid=None, sec=None):
        st = self.d['q'].setdefault(qid, {'a': 0, 'c': 0, 'w': 0, 'st': 0, 'box': 0, 'due': 0})
        st['a'] += 1
        st['last'] = time.time()
        recovered = False
        if ok:
            st['c'] += 1
            st['st'] += 1
            if st['w'] > 0 and st['st'] == DOMINADA_STREAK:
                recovered = True
            st['box'] = min(st.get('box', 0) + 1, 5)
            st['due'] = today() + INTERVALS[st['box']]
            self.d['xp'] += 2 if st['w'] > 0 else 1
        else:
            st['w'] += 1
            st['st'] = 0
            st['box'] = 1
            st['due'] = today()      # vuelve a salir hoy en el repaso
            st['lw'] = time.time()
        day = datetime.date.today().isoformat()
        self.d['days'][day] = self.d['days'].get(day, 0) + 1
        self.d['recent'].append([qid, 1 if ok else 0])
        self.d['recent'] = self.d['recent'][-400:]
        return recovered

    def status(self, qid):
        """None (nunca fallada) | 'pend' | 'recu' | 'dom'"""
        st = self.d['q'].get(qid)
        if not st or st['w'] == 0:
            return None
        if st['st'] >= DOMINADA_STREAK:
            return 'dom'
        if st['st'] >= 1:
            return 'recu'
        return 'pend'

    def toggle(self, key, val):
        lst = self.d[key]
        if val in lst:
            lst.remove(val)
            return False
        lst.append(val)
        return True

    def streak_days(self):
        days = set(self.d['days'].keys())
        n = 0
        d = datetime.date.today()
        if d.isoformat() not in days:
            d -= datetime.timedelta(days=1)
        while d.isoformat() in days:
            n += 1
            d -= datetime.timedelta(days=1)
        return n

    def mark_studied(self, tid, sid, val=True):
        lst = self.d['studied'].setdefault(tid, [])
        if val and sid not in lst:
            lst.append(sid)
        if not val and sid in lst:
            lst.remove(sid)

    def is_studied(self, tid, sid):
        return sid in self.d['studied'].get(tid, [])


class Engine:
    def __init__(self, content, store):
        self.c = content
        self.s = store

    # ---------- estadísticas ----------
    def tema_stats(self, tid):
        a = c = seen = 0
        for qid in self.c.by_tema[tid]:
            st = self.s.qs(qid)
            if st:
                seen += 1
                a += st['a']
                c += st['c']
        total = len(self.c.by_tema[tid])
        acc = (c / a) if a else None
        secs = self.c.study_sections(tid)
        studied = len([x for x in secs if self.s.is_studied(tid, x['id'])])
        return {'acc': acc, 'answers': a, 'seen': seen, 'total': total,
                'studied': studied, 'nsecs': len(secs)}

    def sec_fails(self, tid, sid):
        return [q for q in self.c.by_sec.get((tid, sid), []) if self.s.status(q) == 'pend']

    def fallos(self):
        res = {'pend': [], 'recu': [], 'dom': []}
        for qid in self.s.d['q']:
            st = self.s.status(qid)
            if st and qid in self.c.q:
                res[st].append(qid)
        return res

    def due(self):
        t = today()
        return [qid for qid, st in self.s.d['q'].items()
                if qid in self.c.q and st.get('due', 0) <= t and (st['w'] > 0 or st['box'] < 5)
                and self.s.status(qid) != 'dom']

    def global_acc(self, last=300):
        r = self.s.d['recent'][-last:]
        if not r:
            return None
        return sum(x[1] for x in r) / len(r)

    def weaknesses(self):
        """Lista de (tid, acc, answers) ordenada de peor a mejor (solo temas con datos)."""
        out = []
        for t in self.c.temas:
            st = self.tema_stats(t['id'])
            if st['answers'] >= 5:
                out.append((t['id'], st['acc'], st['answers']))
        out.sort(key=lambda x: x[1])
        return out

    def weak_sections(self, minfails=4):
        res = []
        for (tid, sid), qids in self.c.by_sec.items():
            if sid == '-':
                continue
            n = len([q for q in qids if self.s.status(q) == 'pend'])
            if n >= minfails:
                res.append((n, tid, sid))
        res.sort(reverse=True)
        return res

    def readiness(self):
        """Índice interno de preparación 0-100 (orientativo, no garantiza el aprobado)."""
        nsecs = sum(len(self.c.study_sections(t['id'])) for t in self.c.temas)
        studied = sum(len(self.s.d['studied'].get(t['id'], [])) for t in self.c.temas)
        cov_temario = min(1.0, studied / nsecs) if nsecs else 0
        seen = len([q for q in self.s.d['q'] if q in self.c.q])
        cov_banco = min(1.0, seen / max(1, len(self.c.preguntas) * 0.7))
        acc = self.global_acc() or 0
        f = self.fallos()
        tot_f = sum(len(v) for v in f.values())
        retention = (len(f['dom']) + 0.5 * len(f['recu'])) / tot_f if tot_f else (1.0 if seen else 0)
        sims = [h for h in self.s.d['hist'] if h.get('kind') == 'sim_libre']
        sim = 0
        if sims:
            last = sims[-3:]
            sim = max(0, min(1, sum(h['score'] / h['max'] for h in last) / len(last)))
        val = 0.15 * cov_temario + 0.15 * cov_banco + 0.30 * acc + 0.15 * retention + 0.25 * sim
        if not sims:
            val = val / 0.75 * 0.85   # sin simulacros el índice se queda limitado
            val = min(val, 0.75)
        return int(round(val * 100)), {'temario': cov_temario, 'banco': cov_banco, 'acierto': acc,
                                       'retencion': retention, 'simulacro': sim}

    # ---------- selección de preguntas ----------
    def pool(self, temas=None, origin='todas', dif=None):
        temas = temas or [t['id'] for t in self.c.temas]
        res = []
        for tid in temas:
            for qid in self.c.by_tema[tid]:
                q = self.c.q[qid]
                if dif and q['d'] != dif:
                    continue
                st = self.s.qs(qid)
                if origin == 'nuevas' and st:
                    continue
                if origin == 'falladas' and self.s.status(qid) not in ('pend', 'recu'):
                    continue
                if origin == 'dudas' and qid not in self.s.d['dudas']:
                    continue
                if origin == 'favoritas' and qid not in self.s.d['favq']:
                    continue
                if origin == 'dificiles' and q['d'] != 3:
                    continue
                res.append(qid)
        return res

    def build_test(self, temas=None, n=20, origin='todas', dif=None):
        p = self.pool(temas, origin, dif)
        random.shuffle(p)
        # prioriza las no vistas para que el alumno avance por el banco
        if origin == 'todas':
            p.sort(key=lambda q: 1 if self.s.qs(q) else 0)
            head = p[:n]
            random.shuffle(head)
            return head
        return p[:n]

    def smart_test(self, n=20, temas=None):
        """Test inteligente: prioriza aprender, no hacer más preguntas."""
        temas = temas or [t['id'] for t in self.c.temas]
        tset = set(temas)
        chosen = []

        def add(lst, k):
            random.shuffle(lst)
            for q in lst:
                if len(chosen) >= n or k <= 0:
                    break
                if q not in chosen and self.c.q[q]['t'] in tset:
                    chosen.append(q)
                    k -= 1

        due = self.due()
        pend = self.fallos()['pend']
        add([q for q in due if q in pend], int(n * 0.30))
        add(due, int(n * 0.15))
        weak = [w[0] for w in self.weaknesses() if w[0] in tset][:3]
        if weak:
            add([q for t in weak for q in self.c.by_tema[t] if not self.s.qs(q) or self.s.status(q)], int(n * 0.30))
        unseen = [q for t in temas for q in self.c.by_tema[t] if not self.s.qs(q)]
        add(unseen, n - len(chosen) - max(1, n // 10))
        dom = self.fallos()['dom']
        add(dom, n - len(chosen))
        add([q for t in temas for q in self.c.by_tema[t]], n - len(chosen))
        random.shuffle(chosen)
        return chosen[:n]

    def related(self, qid, exclude=()):
        """Pregunta del mismo apartado (o tema) para comprobar que se entiende el concepto."""
        q = self.c.q[qid]
        cand = [x for x in self.c.by_sec.get((q['t'], q['s']), []) if x != qid and x not in exclude]
        if not cand:
            cand = [x for x in self.c.by_tema[q['t']] if x != qid and x not in exclude]
        if not cand:
            return None
        cand.sort(key=lambda x: (self.c.q[x]['d'], 1 if self.s.qs(x) else 0))
        return random.choice(cand[:5])

    def recovery_test(self, failed, n=25):
        """Fallos + preguntas del mismo concepto (apartado) + nuevas, con dificultad progresiva."""
        failed = [q for q in failed if q in self.c.q]
        chosen = list(dict.fromkeys(failed))[: n // 2]
        secs = list(dict.fromkeys((self.c.q[q]['t'], self.c.q[q]['s']) for q in failed))
        sims = []
        for key in secs:
            for x in self.c.by_sec.get(key, []):
                if x not in chosen:
                    sims.append(x)
        random.shuffle(sims)
        for x in sims:
            if len(chosen) >= n:
                break
            chosen.append(x)
        if len(chosen) < n:
            temas = list(dict.fromkeys(self.c.q[q]['t'] for q in failed))
            rest = [x for t in temas for x in self.c.by_tema[t] if x not in chosen]
            random.shuffle(rest)
            chosen += rest[: n - len(chosen)]
        chosen.sort(key=lambda x: (self.c.q[x]['d'], random.random()))
        return chosen

    def micro(self, tid, sid, n=5):
        qids = self.c.by_sec.get((tid, sid), [])
        pend = [q for q in qids if self.s.status(q) == 'pend']
        other = [q for q in qids if q not in pend]
        random.shuffle(pend)
        random.shuffle(other)
        return (pend + other)[:n]

    def simulacro(self, kind='libre'):
        """libre: 40 común (8 por tema) + 60 específica (6 por tema). interna: 60 específica."""
        def pick(tid, k):
            qs = list(self.c.by_tema[tid])
            random.shuffle(qs)
            qs.sort(key=lambda q: (1 if self.s.qs(q) else 0))
            hard = [q for q in qs if self.c.q[q]['d'] == 3][: max(1, k // 4)]
            rest = [q for q in qs if q not in hard][: k - len(hard)]
            out = hard + rest
            random.shuffle(out)
            return out
        res = []
        if kind == 'libre':
            for t in self.c.comun():
                res += pick(t['id'], 8)
            for t in self.c.especifica():
                res += pick(t['id'], 6)
        elif kind == 'interna':
            for t in self.c.especifica():
                res += pick(t['id'], 6)
        else:  # mini: 20 preguntas en 20 minutos
            for t in self.c.comun():
                res += pick(t['id'], 1)
            for t in random.sample(self.c.especifica(), 5):
                res += pick(t['id'], 3)
        return res

    # ---------- corrección ----------
    def grade(self, qids, answers, penal=True):
        ok = ko = blank = 0
        per = {}
        wrong = []
        for i, qid in enumerate(qids):
            q = self.c.q[qid]
            a = answers.get(i)
            p = per.setdefault(q['t'], [0, 0, 0])   # ok, ko, blank
            if a is None:
                blank += 1
                p[2] += 1
            elif a == q['k']:
                ok += 1
                p[0] += 1
            else:
                ko += 1
                p[1] += 1
                wrong.append(qid)
        score = ok - (ko / 3.0 if penal else 0)
        return {'ok': ok, 'ko': ko, 'blank': blank, 'n': len(qids), 'score': round(max(score, 0), 2),
                'raw': round(score, 2), 'per': per, 'wrong': wrong}

    def save_result(self, kind, title, res, dur, mode):
        h = {'ts': time.time(), 'kind': kind, 'title': title, 'mode': mode, 'n': res['n'], 'ok': res['ok'],
             'ko': res['ko'], 'blank': res['blank'], 'score': res['score'], 'max': res['n'], 'dur': int(dur),
             'per': res['per']}
        self.s.d['hist'].append(h)
        self.s.d['hist'] = self.s.d['hist'][-200:]
        self.s.save()
        return h

    # ---------- plan de estudio ----------
    def plan_week(self):
        p = self.s.d.get('plan') or {}
        if not p.get('exam'):
            return None
        try:
            exam = datetime.date.fromisoformat(p['exam'])
        except Exception:
            return None
        mins = int(p.get('mins', 60))
        days = p.get('days', [0, 1, 2, 3, 4])
        start = datetime.date.today()
        left = (exam - start).days
        weak = [w[0] for w in self.weaknesses()]
        order = []
        # primero temas no estudiados, después los débiles
        for t in self.c.temas:
            st = self.tema_stats(t['id'])
            if st['studied'] < st['nsecs']:
                order.append(t['id'])
        for w in weak:
            if w not in order:
                order.append(w)
        for t in self.c.temas:
            if t['id'] not in order:
                order.append(t['id'])
        out = []
        i = 0
        d = start
        while len(out) < 7:
            if d.weekday() in days:
                remaining = (exam - d).days
                tasks = []
                tid = order[i % len(order)]
                i += 1
                if remaining < 0:
                    break
                if remaining <= 14 and d.weekday() in (days[-1],):
                    tasks.append(('sim', min(mins, 100), 'Simulacro oficial (100 preguntas)'))
                else:
                    t = self.c.tema[tid]
                    tasks.append(('read', int(mins * 0.45), f"Estudiar: {self.c.label(tid)} — {t['short']}", tid))
                    tasks.append(('test', int(mins * 0.35), f"Test de 20 preguntas del Tema {t['num']} ({'Común' if t['parte']=='comun' else 'Específica'})", tid))
                    tasks.append(('fallos', max(5, mins - int(mins * 0.45) - int(mins * 0.35)), 'Repaso de fallos y repasos del día'))
                out.append((d, tasks))
            d += datetime.timedelta(days=1)
            if (d - start).days > 30:
                break
        return {'left': left, 'days': out}
