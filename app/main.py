# -*- coding: utf-8 -*-
"""PME Conductor E2 — app de estudio para la oposición de Conductor/a del Parque Móvil del Estado.

Pedagogía antes que gamificación: estudiar → practicar → fallar → entender → repasar → consolidar.
"""
import os
import time
import datetime

from kivy.config import Config
Config.set('kivy', 'exit_on_escape', '0')

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.utils import platform

import engine
import ui
from ui import T, Txt, Btn, Chip, Box, Bar, card, gap, row, grid, callout, render_blocks, md, col

HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = 'PME Conductor E2'
LETTERS = 'ABC'

DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
         'octubre', 'noviembre', 'diciembre']


def fmt_date(d):
    return f'{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}'


def pct(x):
    return '—' if x is None else f'{round(x * 100)}%'


def mmss(s):
    s = max(0, int(s))
    return f'{s // 60:02d}:{s % 60:02d}'


class Session:
    def __init__(self, qids, mode='learn', kind='test', title='Test', limit=None, penal=True, back_to=None):
        self.qids = list(qids)
        self.mode = mode           # 'learn' | 'exam'
        self.kind = kind           # 'test' | 'sim_libre' | 'sim_interna' | 'sim_mini' | 'recup' | 'micro' ...
        self.title = title
        self.limit = limit         # segundos
        self.penal = penal
        self.answers = {}
        self.marked = set()
        self.understood = {}
        self.idx = 0
        self.start = time.time()
        self.finished = False
        self.result = None
        self.no_entiendo = set()
        self.related_added = set()

    def elapsed(self):
        return time.time() - self.start

    def remaining(self):
        return None if not self.limit else self.limit - self.elapsed()


# ======================================================================
# Páginas
# ======================================================================
class Page(Screen):
    title = ''
    nav = None          # nombre del botón de la barra inferior activo
    back = True

    def on_pre_enter(self, *a):
        self.build()

    def build(self):
        self.clear_widgets()
        app = App.get_running_app()
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(*T['bg'])
            self._rect = Rectangle()
        root.bind(pos=lambda w, v: setattr(self._rect, 'pos', v), size=lambda w, v: setattr(self._rect, 'size', v))
        # barra superior
        top = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(6), dp(6), dp(12), dp(6)], spacing=dp(6))
        with top.canvas.before:
            Color(*T['primary'])
            self._tr = Rectangle()
        top.bind(pos=lambda w, v: setattr(self._tr, 'pos', v), size=lambda w, v: setattr(self._tr, 'size', v))
        if self.back and len(app.stack) > 1:
            b = Btn('‹', app.back, kind='primary', size=28, h=44, size_hint_x=None, width=dp(44))
            top.add_widget(b)
        else:
            top.add_widget(Widget(size_hint_x=None, width=dp(8)))
        tl = Txt(self.get_title(), size=18, color=T['primary_t'], bold=True)
        tl.size_hint_y = 1
        tl.shorten = True
        tl.shorten_from = 'right'
        top.add_widget(tl)
        extra = self.top_extra()
        if extra:
            top.add_widget(extra)
        root.add_widget(top)
        # contenido
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        body = Box(padding=[dp(14), dp(14), dp(14), dp(24)], spacing=dp(12))
        self.body = body
        self.scroll.add_widget(body)
        root.add_widget(self.scroll)
        foot = self.footer()
        if foot is not None:
            root.add_widget(foot)
        if self.nav:
            root.add_widget(app.navbar(self.nav))
        self.add_widget(root)
        self.render(body)

    def get_title(self):
        return self.title

    def top_extra(self):
        return None

    def footer(self):
        return None

    def render(self, body):
        pass

    @property
    def app(self):
        return App.get_running_app()

    @property
    def args(self):
        return self.app.args.get(self.name, {})


def section_title(text):
    return Txt(text.upper(), size=12.5, color=T['muted'], bold=True, pad=2)


# ---------------------------------------------------------------- INICIO
class HomePage(Page):
    nav = 'home'
    back = False

    def get_title(self):
        return APP_NAME

    def render(self, b):
        app = self.app
        e, s = app.e, app.s
        h = datetime.datetime.now().hour
        saludo = 'Buenos días' if 6 <= h < 14 else ('Buenas tardes' if h < 21 else 'Buenas noches')
        name = s.d['settings'].get('name')
        b.add_widget(Txt(saludo + (f', {name}' if name else ''), size=24, bold=True))
        sub = fmt_date(datetime.date.today())
        plan = s.d.get('plan') or {}
        if plan.get('exam'):
            try:
                left = (datetime.date.fromisoformat(plan['exam']) - datetime.date.today()).days
                if left >= 0:
                    sub += f'  ·  Faltan [b]{left}[/b] días para el examen'
            except Exception:
                pass
        b.add_widget(Txt(sub, size=14, color=T['muted']))

        idx, parts = e.readiness()
        c = card()
        c.add_widget(Txt('TU PREPARACIÓN', size=12.5, color=T['muted'], bold=True))
        c.add_widget(Txt(f'[b]{idx}%[/b]', size=40, color=T['primary']))
        c.add_widget(Bar(idx / 100, h=10))
        c.add_widget(Txt('Indicador interno orientativo (temario estudiado, aciertos, retención de fallos y simulacros). No garantiza el aprobado.',
                         size=12.5, color=T['muted']))
        acc = e.global_acc()
        stats = grid(3, 6)
        for label, val in (('Rendimiento', pct(acc)), ('Racha', (f'{s.streak_days()} día' if s.streak_days() == 1 else f'{s.streak_days()} días')),
                           ('Nivel', f"{s.d['xp'] // 200 + 1}")):
            bx = Box(bg=T['card2'], padding=[dp(8), dp(8)], radius=10)
            bx.add_widget(Txt(val, size=17, bold=True, halign='center'))
            bx.add_widget(Txt(label, size=12, color=T['muted'], halign='center'))
            stats.add_widget(bx)
        c.add_widget(stats)
        b.add_widget(c)

        # Recomendaciones
        rc = card()
        rc.add_widget(Txt('HOY TE RECOMENDAMOS', size=12.5, color=T['muted'], bold=True))
        recs = 0
        due = e.due()
        if due:
            rc.add_widget(Btn(f'Repasar {len(due)} preguntas que tocan hoy (repetición espaciada)',
                              lambda: app.start(Session(due[:30], title='Repaso del día', kind='repaso')),
                              kind='ghost', halign='left', size=14.5))
            recs += 1
        ws = e.weak_sections()
        if ws:
            n, tid, sid = ws[0]
            sec = app.c.section(tid, sid)
            rc.add_widget(Btn(f"Microrrepaso: has fallado {n} preguntas de «{sec['title']}» ({app.c.label(tid)})",
                              lambda tid=tid, sid=sid: app.go('section', tid=tid, sid=sid, micro=True),
                              kind='ghost', halign='left', size=14.5))
            recs += 1
        nxt = self.next_to_study()
        if nxt:
            tid, sec = nxt
            rc.add_widget(Btn(f"Estudiar {app.c.label(tid)} · {sec['id']} {sec['title']}",
                              lambda tid=tid, sid=sec['id']: app.go('section', tid=tid, sid=sid),
                              kind='ghost', halign='left', size=14.5))
            recs += 1
        pend = e.fallos()['pend']
        if pend and not due:
            rc.add_widget(Btn(f'Recuperar {len(pend)} fallos pendientes',
                              lambda: app.start(Session(e.recovery_test(pend, 20), title='Recuperación de fallos', kind='recup')),
                              kind='ghost', halign='left', size=14.5))
            recs += 1
        if recs == 0:
            rc.add_widget(Txt('Empieza por el temario o haz un test inteligente de 20 preguntas.', size=14.5))
        b.add_widget(rc)

        b.add_widget(Btn('EMPEZAR SESIÓN DE ESTUDIO', lambda: app.start(Session(e.smart_test(20), title='Test inteligente', kind='smart')),
                         kind='primary', size=17, h=60))
        weak = e.weaknesses()
        if weak:
            tid, a, _ = weak[0]
            b.add_widget(Txt(f"Tu principal debilidad ahora: [b]{app.c.label(tid)}[/b] — {app.c.tema[tid]['short']} ({pct(a)} de acierto)",
                             size=14, color=T['muted']))

        b.add_widget(section_title('Accesos'))
        g = grid(2, 8)
        items = [('Temario', lambda: app.go('temario')), ('Test', lambda: app.go('test')),
                 ('Simulacro', lambda: app.go('sim')), ('Mis fallos', lambda: app.go('fallos')),
                 ('Mis dudas', lambda: app.go('dudas')), ('Favoritas', lambda: app.go('favs')),
                 ('Mi progreso', lambda: app.go('progreso')), ('Plan de estudio', lambda: app.go('plan')),
                 ('Bases de la oposición', lambda: app.go('bases')), ('Ajustes', lambda: app.go('ajustes'))]
        for label, cb in items:
            g.add_widget(Btn(label, cb, kind='outline', size=14.5, h=54))
        b.add_widget(g)

    def next_to_study(self):
        app = self.app
        for t in app.c.temas:
            for sec in app.c.study_sections(t['id']):
                if not app.s.is_studied(t['id'], sec['id']) and sec['id'] not in ('1', '2'):
                    return t['id'], sec
        return None


# ---------------------------------------------------------------- TEMARIO
class TemarioPage(Page):
    title = 'Temario'
    nav = 'temario'
    back = False

    def render(self, b):
        app = self.app
        for parte, temas in (('Parte común (40 preguntas en el examen)', app.c.comun()),
                             ('Parte específica (60 preguntas en el examen)', app.c.especifica())):
            b.add_widget(section_title(parte))
            for t in temas:
                st = app.e.tema_stats(t['id'])
                c = card(spacing=dp(6))
                fav = '  ' + ui.col('accent') + '★[/color]' if t['id'] in app.s.d['favtema'] else ''
                c.add_widget(Txt(f"[b]Tema {t['num']}[/b]{fav}", size=13, color=T['primary'], raw=True))
                c.add_widget(Txt(t['short'], size=16, bold=True))
                prog = st['studied'] / st['nsecs'] if st['nsecs'] else 0
                c.add_widget(Bar(prog, h=6))
                c.add_widget(Txt(f"Estudiado {st['studied']}/{st['nsecs']} apartados  ·  Acierto {pct(st['acc'])}  ·  {st['total']} preguntas",
                                 size=12.5, color=T['muted']))
                c.add_widget(Btn('Abrir tema', lambda tid=t['id']: app.go('tema', tid=tid), kind='ghost', h=42, size=14))
                b.add_widget(c)


class TemaPage(Page):
    def get_title(self):
        t = self.app.c.tema[self.args['tid']]
        return f"Tema {t['num']} · {'Común' if t['parte'] == 'comun' else 'Específica'}"

    def render(self, b):
        app = self.app
        tid = self.args['tid']
        t = app.c.tema[tid]
        b.add_widget(Txt(t['title'], size=19, bold=True))
        st = app.e.tema_stats(tid)
        b.add_widget(Txt(f"Estudiado {st['studied']}/{st['nsecs']}  ·  Acierto {pct(st['acc'])}  ·  Vistas {st['seen']}/{st['total']} preguntas",
                         size=13, color=T['muted']))
        isfav = tid in app.s.d['favtema']

        def fav():
            app.s.toggle('favtema', tid)
            app.s.save()
            self.build()
        b.add_widget(row(
            Btn('Test del tema', lambda: app.go('test', temas=[tid]), kind='primary', h=46, size=14.5),
            Btn('★ Favorito' if isfav else '☆ Favorito', fav, kind='outline', h=46, size=14.5)))
        b.add_widget(section_title('Índice'))
        for sec in t['secs']:
            if sec['id'] == '2' and not sec['blocks']:
                continue
            done = app.s.is_studied(tid, sec['id'])
            nf = len(app.e.sec_fails(tid, sec['id']))
            mark = ui.col('ok') + '✓ [/color]' if done else ''
            extra = f"   {ui.col('ko')}{nf} fallos[/color]" if nf else ''
            ind = '      ' if sec['lvl'] == 3 else ''
            label = f"{ind}{mark}[b]{ui.esc(sec['id']) if sec['id'] != 'F' else ''}[/b] {ui.esc(sec['title'])}{extra}"
            b.add_widget(Btn(label, lambda sid=sec['id']: app.go('section', tid=tid, sid=sid), kind='ghost',
                             halign='left', size=14.5, h=46, bold=False, raw=True))
        b.add_widget(section_title('Mis notas del tema'))
        ti = TextInput(text=app.s.d['notes'].get(tid, ''), size_hint_y=None, height=dp(130),
                       font_size=dp(15), background_normal='', background_active='', background_color=T['card2'], foreground_color=T['text'], padding=[dp(10), dp(12)],
                       cursor_color=T['primary'], hint_text='Escribe aquí tus apuntes, trucos o dudas…')
        b.add_widget(ti)

        def save():
            app.s.d['notes'][tid] = ti.text
            app.s.save()
            app.toast('Notas guardadas')
        b.add_widget(Btn('Guardar notas', save, kind='outline', h=44, size=14))


class SectionPage(Page):
    def get_title(self):
        a = self.args
        if a['tid'] == 'bases':
            return 'Bases de la oposición'
        t = self.app.c.tema[a['tid']]
        return f"Tema {t['num']} · {a['sid'] if a['sid'] != 'F' else 'Fuentes'}"

    def secs(self):
        a = self.args
        if a['tid'] == 'bases':
            return self.app.c.bases['secs']
        return [s for s in self.app.c.tema[a['tid']]['secs'] if s['blocks'] or s['id'] == '2']

    def render(self, b):
        app = self.app
        a = self.args
        tid, sid = a['tid'], a['sid']
        secs = self.secs()
        i = next((k for k, s in enumerate(secs) if s['id'] == sid), 0)
        sec = secs[i]
        if a.get('micro'):
            b.add_widget(callout('rigor', 'Lee con calma este apartado. Después responde 5 preguntas de recuperación para comprobar que has entendido el concepto (no la respuesta de memoria).',
                                 'MICRORREPASO'))
        if tid != 'bases':
            b.add_widget(Txt(app.c.tema[tid]['short'], size=13, color=T['muted']))
        head = (sec['id'] + '. ' if sec['id'] not in ('F',) else '') + sec['title']
        b.add_widget(Txt(head, size=20, bold=True, color=T['primary']))
        # subapartados vacíos ("2. Desarrollo"): mostrar índice
        if not sec['blocks']:
            subs = [s for s in secs if s['id'].startswith(sec['id'] + '.')]
            for s in subs:
                b.add_widget(Btn(f"{s['id']} {s['title']}", lambda sid=s['id']: app.go('section', tid=tid, sid=sid, replace=True),
                                 kind='ghost', halign='left', size=14.5, h=46, bold=False))
        c = card(spacing=dp(10))
        render_blocks(sec['blocks'], c)
        if sec['blocks']:
            b.add_widget(c)
        if tid == 'bases':
            nav = []
            if i > 0:
                nav.append(Btn('‹ Anterior', lambda: app.go('section', tid=tid, sid=secs[i - 1]['id'], replace=True), kind='ghost', h=46, size=14))
            if i < len(secs) - 1:
                nav.append(Btn('Siguiente ›', lambda: app.go('section', tid=tid, sid=secs[i + 1]['id'], replace=True), kind='ghost', h=46, size=14))
            if nav:
                b.add_widget(row(*nav))
            return
        # acciones
        qids = app.c.by_sec.get((tid, sid), [])
        if a.get('micro'):
            b.add_widget(Btn('Responder 5 preguntas de recuperación',
                             lambda: app.start(Session(app.e.micro(tid, sid), title='Microrrepaso', kind='micro')), kind='primary', h=54))
        if sec['id'] not in ('F',):
            done = app.s.is_studied(tid, sid)

            def mark():
                app.s.mark_studied(tid, sid, not done)
                app.s.save()
                self.build()
            b.add_widget(Btn('✓ Estudiado (pulsa para desmarcar)' if done else 'Marcar como estudiado', mark,
                             kind='ok' if done else 'outline', h=48, size=14.5))
        if qids:
            b.add_widget(Btn(f'Practicar este apartado ({len(qids)} preguntas)',
                             lambda: app.start(Session(_shuffled(qids)[:15],
                                                       title=f'Apartado {sid}', kind='test')),
                             kind='primary', h=48, size=14.5))
        nav = []
        if i > 0:
            nav.append(Btn('‹ Anterior', lambda: app.go('section', tid=tid, sid=secs[i - 1]['id'], replace=True), kind='ghost', h=46, size=14))
        if i < len(secs) - 1:
            nav.append(Btn('Siguiente ›', lambda: app.go('section', tid=tid, sid=secs[i + 1]['id'], replace=True), kind='ghost', h=46, size=14))
        if nav:
            b.add_widget(row(*nav))
        b.add_widget(Txt('Contenido: base normativa oficial citada en «Fuentes y elaboración» del tema; explicaciones y resúmenes de elaboración propia.',
                         size=12, color=T['muted']))


def _shuffled(lst):
    import random
    l2 = list(lst)
    random.shuffle(l2)
    return l2


# ---------------------------------------------------------------- TEST (configurador)
class TestPage(Page):
    title = 'Configurar test'
    nav = 'test'
    back = False

    def build(self):
        a = self.args
        if not hasattr(self, 'cfg') or a.get('temas'):
            self.cfg = {'mode': 'learn', 'temas': set(a.get('temas') or []), 'n': 20, 'origin': 'todas', 'dif': None}
            if 'temas' in a:
                a.pop('temas')
        super().build()

    def render(self, b):
        app = self.app
        cfg = self.cfg
        b.add_widget(Btn('TEST INTELIGENTE (20)', lambda: app.start(Session(app.e.smart_test(20), title='Test inteligente', kind='smart')),
                         kind='primary', h=54))
        b.add_widget(Txt('Elige las preguntas según tu rendimiento: fallos pendientes, repasos del día, temas débiles y preguntas nuevas.',
                         size=13, color=T['muted']))
        b.add_widget(Btn('Simulacros de examen', lambda: app.go('sim'), kind='outline', h=48))

        def chips(title, options, key, multi=False):
            b.add_widget(section_title(title))
            g = grid(2 if len(options) > 3 else len(options), 6)
            widgets = []

            def pick(ch, val):
                if multi:
                    if val in cfg[key]:
                        cfg[key].remove(val)
                    else:
                        cfg[key].add(val)
                    ch.set(val in cfg[key])
                    self.update_count()
                else:
                    cfg[key] = val
                    for w, v in widgets:
                        w.set(v == val)
                    self.update_count()
            for label, val in options:
                active = (val in cfg[key]) if multi else (cfg[key] == val)
                w = Chip(label, active, cb=lambda ch, val=val: pick(ch, val))
                widgets.append((w, val))
                g.add_widget(w)
            b.add_widget(g)
            return widgets

        chips('Modo', [('Aprendizaje (corrige al momento)', 'learn'), ('Examen (corrige al final)', 'exam')], 'mode')
        b.add_widget(section_title('Temas (si no marcas ninguno: todo el temario)'))
        quick = grid(3, 6)

        def set_temas(lst):
            cfg['temas'] = set(lst)
            self.build()
        quick.add_widget(Chip('Todo', not cfg['temas'], cb=lambda ch: set_temas([])))
        quick.add_widget(Chip('Común', cfg['temas'] == {t['id'] for t in app.c.comun()},
                              cb=lambda ch: set_temas([t['id'] for t in app.c.comun()])))
        quick.add_widget(Chip('Específica', cfg['temas'] == {t['id'] for t in app.c.especifica()},
                              cb=lambda ch: set_temas([t['id'] for t in app.c.especifica()])))
        b.add_widget(quick)
        g = grid(1, 6)
        for t in app.c.temas:
            lab = f"{'C' if t['parte'] == 'comun' else 'E'}{t['num']} · {t['short']}"

            def tog(ch, tid=t['id']):
                if tid in cfg['temas']:
                    cfg['temas'].remove(tid)
                else:
                    cfg['temas'].add(tid)
                ch.set(tid in cfg['temas'])
                self.update_count()
            ch = Chip(lab, t['id'] in cfg['temas'], cb=tog, halign='left')
            g.add_widget(ch)
        b.add_widget(g)
        chips('Número de preguntas', [('10', 10), ('20', 20), ('30', 30), ('50', 50), ('100', 100)], 'n')
        chips('Tipo de preguntas', [('Todas', 'todas'), ('Nuevas', 'nuevas'), ('Falladas', 'falladas'),
                                    ('Mis dudas', 'dudas'), ('Favoritas', 'favoritas'), ('Difíciles', 'dificiles')], 'origin')
        chips('Dificultad', [('Cualquiera', None), ('Básica', 1), ('Media', 2), ('Alta', 3)], 'dif')
        self.count_lbl = Txt('', size=13.5, color=T['muted'], halign='center')
        b.add_widget(self.count_lbl)
        self.update_count()

    def footer(self):
        f = BoxLayout(size_hint_y=None, height=dp(70), padding=[dp(14), dp(10)])
        with f.canvas.before:
            Color(*T['card'])
            r = Rectangle()
        f.bind(pos=lambda w, v: setattr(r, 'pos', v), size=lambda w, v: setattr(r, 'size', v))
        f.add_widget(Btn('EMPEZAR TEST', self.start, kind='primary', h=50))
        return f

    def update_count(self):
        app = self.app
        cfg = self.cfg
        n = len(app.e.pool(list(cfg['temas']) or None, cfg['origin'], cfg['dif']))
        if hasattr(self, 'count_lbl'):
            self.count_lbl.text = md(f'Preguntas disponibles con estos filtros: **{n}**')

    def start(self):
        app = self.app
        cfg = self.cfg
        qids = app.e.build_test(list(cfg['temas']) or None, cfg['n'], cfg['origin'], cfg['dif'])
        if not qids:
            app.toast('No hay preguntas con esos filtros')
            return
        limit = len(qids) * 60 if cfg['mode'] == 'exam' else None
        app.start(Session(qids, mode=cfg['mode'], title='Test', kind='test', limit=limit))


# ---------------------------------------------------------------- SIMULACROS
SIMS = {
    'sim_libre': ('Simulacro oficial · Turno libre', '100 preguntas (40 comunes + 60 específicas) · 100 minutos · cada fallo resta 1/3 · mínimo 50 puntos', 'libre', 100 * 60, 50),
    'sim_interna': ('Simulacro · Promoción interna', '60 preguntas de la parte específica · 60 minutos · cada fallo resta 1/3 · mínimo 30 puntos', 'interna', 60 * 60, 30),
    'sim_mini': ('Mini simulacro', '20 preguntas variadas · 20 minutos · mismas reglas de penalización', 'mini', 20 * 60, 10),
}


class SimPage(Page):
    title = 'Simulacros'

    def render(self, b):
        app = self.app
        b.add_widget(Txt('Reproducen las condiciones del examen: cronómetro, sin ver las soluciones hasta entregar, preguntas marcables para revisar y penalización por fallo.',
                         size=14, color=T['muted']))
        for kind, (title, desc, k, lim, minimo) in SIMS.items():
            c = card()
            c.add_widget(Txt(title, size=17, bold=True))
            c.add_widget(Txt(desc, size=13.5, color=T['muted']))
            c.add_widget(Btn('Empezar', lambda kind=kind, k=k, lim=lim, title=title:
                             app.start(Session(app.e.simulacro(k), mode='exam', kind=kind, title=title, limit=lim)),
                             kind='primary', h=48))
            b.add_widget(c)
        b.add_widget(callout('info', 'En el examen real cada pregunta tiene 4 opciones; aquí practicas con 3 (formato del curso). La forma de razonar y la penalización son las mismas.'))
        hist = [h for h in app.s.d['hist'] if h['kind'].startswith('sim')][-8:]
        if hist:
            b.add_widget(section_title('Tus últimos simulacros'))
            for h in reversed(hist):
                d = datetime.datetime.fromtimestamp(h['ts']).strftime('%d/%m %H:%M')
                b.add_widget(Txt(f"{d} · {h['title']}: [b]{h['score']:.2f}[/b] / {h['max']} · {h['ok']} aciertos, {h['ko']} fallos, {h['blank']} en blanco",
                                 size=13.5))


# ---------------------------------------------------------------- QUIZ
class QuizPage(Page):
    back = True

    def get_title(self):
        s = self.app.session
        return f"{s.title} · {s.idx + 1}/{len(s.qids)}"

    def top_extra(self):
        s = self.app.session
        if s.mode == 'exam' and s.limit:
            self.timer = Txt('', size=16, color=T['primary_t'], bold=True, halign='right')
            self.timer.size_hint = (None, 1)
            self.timer.width = dp(70)
            self.tick()
            return self.timer
        return None

    def on_enter(self, *a):
        Clock.unschedule(self.tick)
        if self.app.session.mode == 'exam' and self.app.session.limit:
            Clock.schedule_interval(self.tick, 1)

    def on_leave(self, *a):
        Clock.unschedule(self.tick)

    def tick(self, *a):
        s = self.app.session
        if s.finished:
            return
        r = s.remaining()
        if r is None:
            return
        if hasattr(self, 'timer'):
            self.timer.text = mmss(r)
            self.timer.color = T['accent'] if r < 300 else T['primary_t']
        if r <= 0:
            Clock.unschedule(self.tick)
            self.app.toast('Tiempo agotado')
            self.app.finish_session()

    def footer(self):
        s = self.app.session
        f = BoxLayout(size_hint_y=None, height=dp(66), padding=[dp(10), dp(8)], spacing=dp(8))
        with f.canvas.before:
            Color(*T['card'])
            r = Rectangle()
        f.bind(pos=lambda w, v: setattr(r, 'pos', v), size=lambda w, v: setattr(r, 'size', v))
        if s.mode == 'exam':
            f.add_widget(Btn('‹', self.prev, kind='ghost', h=48, size=20, size_hint_x=0.18))
            f.add_widget(Btn('Índice', self.show_grid, kind='ghost', h=48, size=14, size_hint_x=0.27))
            f.add_widget(Btn('Entregar', self.ask_finish, kind='accent', h=48, size=14, size_hint_x=0.3))
            f.add_widget(Btn('›', self.next, kind='primary', h=48, size=20, size_hint_x=0.25))
        else:
            answered = s.idx in s.answers
            f.add_widget(Btn('Terminar', self.ask_finish, kind='ghost', h=48, size=14, size_hint_x=0.35))
            f.add_widget(Btn('Siguiente ›' if s.idx < len(s.qids) - 1 else 'Ver resultado',
                             self.next if s.idx < len(s.qids) - 1 else self.app.finish_session,
                             kind='primary' if answered else 'ghost', h=48, size=15, size_hint_x=0.65))
        return f

    def render(self, b):
        app = self.app
        s = app.session
        q = app.c.q[s.qids[s.idx]]
        # cabecera de la pregunta
        dif = {1: 'Básica', 2: 'Media', 3: 'Alta'}[q['d']]
        b.add_widget(Bar((s.idx + 1) / len(s.qids), h=5))
        meta = f"{app.c.label(q['t'])}  ·  Dificultad {dif}"
        b.add_widget(Txt(meta, size=12.5, color=T['muted']))
        b.add_widget(Txt(q['q'], size=18, bold=True, pad=8))
        chosen = s.answers.get(s.idx)
        show = s.mode == 'learn' and chosen is not None
        for i, o in enumerate(q['o']):
            text = f"[b]{LETTERS[i]})[/b]  {md(o)}"
            btn = Btn(text, lambda i=i: self.choose(i), kind='outline', halign='left', size=16, h=56, bold=False, raw=True)
            if show:
                if i == q['k']:
                    btn.restyle(T['ok_bg'], T['text'], T['ok'])
                    btn.text = ui.sym(text + f"   {col('ok')}[b]✓ Correcta[/b][/color]")
                elif i == chosen:
                    btn.restyle(T['ko_bg'], T['text'], T['ko'])
                    btn.text = ui.sym(text + f"   {col('ko')}[b]✗ Tu respuesta[/b][/color]")
                else:
                    btn.restyle(T['card'], T['muted'], T['line'])
            elif chosen == i:
                btn.restyle(T['sel'], T['text'], T['primary'])
            else:
                btn.restyle(T['opt'], T['text'], T['opt_line'])
            b.add_widget(btn)
        # acciones de pregunta
        qid = q['id']
        isd = qid in app.s.d['dudas']
        isf = qid in app.s.d['favq']
        acts = [Btn('★ Favorita' if isf else '☆ Favorita', lambda: self.tog('favq', qid), kind='ghost', h=40, size=13),
                Btn('Duda guardada' if isd else '? Marcar duda', lambda: self.tog('dudas', qid), kind='ghost', h=40, size=13)]
        if s.mode == 'exam':
            ism = s.idx in s.marked
            acts.append(Btn('⚑ Marcada' if ism else '⚑ Revisar luego', self.mark, kind='accent' if ism else 'ghost', h=40, size=13))
        b.add_widget(row(*acts))
        if show:
            for w in feedback(app, q, chosen, s):
                b.add_widget(w)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', self._scroll_to), 0)

    _scroll_to = 1

    def tog(self, key, qid):
        self.app.s.toggle(key, qid)
        self.app.s.save()
        self._keep_scroll()

    def _keep_scroll(self):
        self._scroll_to = self.scroll.scroll_y
        self.build()
        self._scroll_to = 1

    def mark(self):
        s = self.app.session
        if s.idx in s.marked:
            s.marked.remove(s.idx)
        else:
            s.marked.add(s.idx)
        self._keep_scroll()

    def choose(self, i):
        app = self.app
        s = app.session
        if s.mode == 'learn':
            if s.idx in s.answers:
                return
            s.answers[s.idx] = i
            q = app.c.q[s.qids[s.idx]]
            ok = i == q['k']
            rec = app.s.record(q['id'], ok)
            app.s.save()
            if rec:
                app.toast('¡Pregunta recuperada! Pasa a «Dominada»')
            self._scroll_to = self.scroll.scroll_y
            self.build()
            self._scroll_to = 1
        else:
            if s.answers.get(s.idx) == i:
                s.answers.pop(s.idx)    # tocar de nuevo deja en blanco
            else:
                s.answers[s.idx] = i
            self._keep_scroll()

    def next(self):
        s = self.app.session
        if s.idx < len(s.qids) - 1:
            s.idx += 1
            self.build()
        elif s.mode == 'exam':
            self.show_grid()

    def prev(self):
        s = self.app.session
        if s.idx > 0:
            s.idx -= 1
            self.build()

    def goto(self, i, popup=None):
        if popup:
            popup.dismiss()
        self.app.session.idx = i
        self.build()

    def show_grid(self):
        s = self.app.session
        content = Box(bg=T['card'], padding=[dp(12), dp(12)], spacing=dp(8), auto=False)
        content.add_widget(Txt(f"Respondidas {len(s.answers)}/{len(s.qids)}  ·  Marcadas {len(s.marked)}  ·  En blanco {len(s.qids) - len(s.answers)}", size=13.5))
        sv = ScrollView()
        g = grid(6, 6)
        pop = Popup(title='Índice de preguntas', content=content, size_hint=(0.95, 0.85),
                    separator_color=T['primary'], title_color=T['text'], background_color=T['card'])
        for i in range(len(s.qids)):
            if i in s.marked:
                kind = 'accent'
            elif i in s.answers:
                kind = 'primary'
            else:
                kind = 'ghost'
            lab = str(i + 1) + ('⚑' if i in s.marked else '')
            g.add_widget(Btn(lab, lambda i=i: self.goto(i, pop), kind=kind, h=44, size=14))
        sv.add_widget(g)
        content.add_widget(sv)
        content.add_widget(Txt('Azul: respondida · Naranja: marcada para revisar · Gris: en blanco', size=12, color=T['muted']))
        content.add_widget(row(Btn('Cerrar', pop.dismiss, kind='ghost', h=46),
                               Btn('Entregar', lambda: (pop.dismiss(), self.ask_finish()), kind='accent', h=46)))
        pop.open()

    def ask_finish(self):
        s = self.app.session
        if s.mode == 'learn':
            self.app.finish_session()
            return
        blank = len(s.qids) - len(s.answers)
        msg = f'Te quedan {blank} preguntas en blanco y {len(s.marked)} marcadas para revisar. ¿Entregar ya?' if (blank or s.marked) else '¿Entregar el examen?'
        self.app.confirm(msg, self.app.finish_session, ok='Entregar')


def feedback(app, q, chosen, s):
    """Explicación pedagógica tras responder (modo aprendizaje y revisión)."""
    out = []
    ok = chosen == q['k']
    hard = q['src'] == 'dificil'
    tema = app.c.tema[q['t']]
    sec = app.c.section(q['t'], q['s']) if q['s'] != '-' else None
    c = card(spacing=dp(8))
    if ok:
        c.set_bg(T['ok_bg'])
        c.add_widget(Txt('✓  ¡CORRECTO!', size=18, bold=True, color=T['ok']))
        c.add_widget(Txt(f"[b]¿Por qué?[/b] {md(q['e'])}", size=15.5, raw=True))
    else:
        c.set_bg(T['ko_bg'])
        c.add_widget(Txt('✗  HAS FALLADO', size=18, bold=True, color=T['ko']))
        if chosen is not None:
            c.add_widget(Txt(f"[b]Tu respuesta:[/b] {LETTERS[chosen]}) {md(q['o'][chosen])}", size=15, raw=True))
        else:
            c.add_widget(Txt('[b]Tu respuesta:[/b] en blanco', size=15, raw=True))
        c.add_widget(Txt(f"[b]Respuesta correcta:[/b] {col('ok')}[b]{LETTERS[q['k']]})[/b][/color] {md(q['o'][q['k']])}", size=15, raw=True))
    out.append(c)
    if not ok:
        e = card(spacing=dp(6))
        e.add_widget(Txt(f"¿POR QUÉ ES CORRECTA LA {LETTERS[q['k']]}?", size=12.5, bold=True, color=T['primary']))
        e.add_widget(Txt(q['e'], size=15.5))
        if chosen is not None:
            e.add_widget(Txt('¿POR QUÉ HAS FALLADO?', size=12.5, bold=True, color=T['primary']))
            e.add_widget(Txt(f"Elegiste «{md(q['o'][chosen])}», pero eso no es lo que establece el temario para esta pregunta. Fíjate en la diferencia entre tu opción y la correcta: suele estar en una palabra clave, una cifra o una excepción.",
                             size=15, raw=True))
        out.append(e)
    if hard and q.get('trap'):
        out.append(callout('trap', q['trap']))
    if hard and q.get('memo'):
        out.append(callout('memo', q['memo']))
    # concepto desde el temario
    s_, blk = app.c.best_block(q)
    if blk is not None:
        cc = card(spacing=dp(6))
        cc.add_widget(Txt('EXPLICACIÓN DEL CONCEPTO (DEL TEMARIO)', size=12.5, bold=True, color=T['primary']))
        render_blocks([blk], cc)
        out.append(cc)
    # relación con el temario
    rel = card(spacing=dp(6))
    rel.add_widget(Txt('RELACIÓN CON EL TEMARIO', size=12.5, bold=True, color=T['primary']))
    where = f"{app.c.label(q['t'])}: {tema['short']}"
    target = sec or s_
    if target:
        where += f"\nApartado {target['id']} — {target['title']}"
    rel.add_widget(Txt(where, size=14.5))
    if q.get('ref'):
        rel.add_widget(Txt(f"[b]Referencia:[/b] {md(q['ref'])}", size=14, raw=True))
    rel.add_widget(Txt('Pregunta de elaboración propia para practicar (no es una pregunta oficial de examen).', size=12, color=T['muted']))
    if target:
        rel.add_widget(Btn('VER EN EL TEMARIO', lambda: app.go('section', tid=q['t'], sid=target['id']), kind='outline', h=44, size=14))
    out.append(rel)
    # ¿lo has entendido?
    if s is not None and not ok:
        idx = s.idx
        u = card(spacing=dp(8))
        u.add_widget(Txt('¿LO HAS ENTENDIDO?', size=12.5, bold=True, color=T['primary']))
        state = s.understood.get(idx)
        if state == 'yes':
            u.add_widget(Txt('Perfecto. Esta pregunta volverá a salir en tus repasos para comprobar que lo has consolidado.', size=14.5))
        elif state == 'no':
            u.add_widget(Txt('Vamos paso a paso:', size=14.5, bold=True))
            u.add_widget(Txt(f"1. La pregunta trata de: [b]{md(target['title']) if target else md(tema['short'])}[/b].", size=14.5, raw=True))
            u.add_widget(Txt(f"2. La idea que tienes que quedarte: {md(q['e'])}", size=14.5, raw=True))
            u.add_widget(Txt(f"3. Por eso la correcta es la {LETTERS[q['k']]}: «{md(q['o'][q['k']])}».", size=14.5, raw=True))
            if target and target['blocks']:
                u.add_widget(Txt('4. Lee el apartado completo (es corto) y después responde una pregunta relacionada para comprobarlo.', size=14.5))
            rid = s.related_added
            if idx not in rid:
                def add_rel():
                    r = app.e.related(q['id'], exclude=set(s.qids))
                    if r:
                        s.qids.insert(idx + 1, r)
                        s.related_added.add(idx)
                        app.toast('Pregunta relacionada añadida: es la siguiente')
                        app.screen('quiz').build()
                    else:
                        app.toast('No hay más preguntas de este apartado')
                u.add_widget(Btn('Hacer una pregunta relacionada', add_rel, kind='primary', h=46, size=14))
            else:
                u.add_widget(Txt('La siguiente pregunta es del mismo concepto.', size=14, color=T['ok']))
        else:
            def yes():
                s.understood[idx] = 'yes'
                app.screen('quiz')._keep_scroll()

            def no():
                s.understood[idx] = 'no'
                app.screen('quiz')._keep_scroll()

            def duda():
                if q['id'] not in app.s.d['dudas']:
                    app.s.d['dudas'].append(q['id'])
                    app.s.save()
                app.toast('Guardada en «Mis dudas»')
                s.understood[idx] = 'yes'
                app.screen('quiz')._keep_scroll()
            u.add_widget(row(Btn('YA LO ENTIENDO', yes, kind='ok', h=46, size=13.5),
                             Btn('NO LO ENTIENDO', no, kind='ko', h=46, size=13.5)))
            u.add_widget(Btn('GUARDAR COMO DUDA', duda, kind='ghost', h=44, size=13.5))
        out.append(u)
    return out


# ---------------------------------------------------------------- RESULTADO
class ResultPage(Page):
    title = 'Resultado'
    back = False

    def top_extra(self):
        return Btn('Inicio', lambda: self.app.home(), kind='primary', h=44, size=14, size_hint_x=None, width=dp(80))

    def render(self, b):
        app = self.app
        s = app.session
        r = s.result
        sim = SIMS.get(s.kind)
        c = card()
        if sim:
            minimo = sim[4]
            apto = r['raw'] >= minimo
            c.add_widget(Txt(s.title, size=14, color=T['muted']))
            c.add_widget(Txt(f"[b]{r['raw']:.2f}[/b] / {r['n']} puntos", size=30, color=T['ok'] if apto else T['ko'], raw=True))
            c.add_widget(Txt(('SUPERADO' if apto else 'NO SUPERADO') + f' (mínimo {minimo})', size=15, bold=True,
                             color=T['ok'] if apto else T['ko']))
        else:
            nota = max(0, r['raw']) / r['n'] * 10 if r['n'] else 0
            c.add_widget(Txt(s.title, size=14, color=T['muted']))
            c.add_widget(Txt(f"[b]{r['ok']}[/b] de {r['n']} aciertos  ({pct(r['ok'] / r['n'] if r['n'] else 0)})", size=24, raw=True))
            c.add_widget(Txt(f"Nota con penalización (−1/3 por fallo): [b]{nota:.2f}[/b] / 10", size=15, raw=True))
        g = grid(3, 6)
        for lab, val, colr in (('Aciertos', r['ok'], 'ok'), ('Fallos', r['ko'], 'ko'), ('En blanco', r['blank'], 'muted')):
            bx = Box(bg=T['card2'], padding=[dp(6), dp(8)], radius=10)
            bx.add_widget(Txt(str(val), size=20, bold=True, color=T[colr], halign='center'))
            bx.add_widget(Txt(lab, size=12, color=T['muted'], halign='center'))
            g.add_widget(bx)
        c.add_widget(g)
        dur = s.result_dur
        c.add_widget(Txt(f"Tiempo: {mmss(dur)}  ·  Media por pregunta: {dur / max(1, r['n']):.0f} s", size=13.5, color=T['muted']))
        b.add_widget(c)

        # análisis pedagógico por tema
        b.add_widget(section_title('Análisis por tema'))
        rows = []
        for tid, (ok, ko, bl) in r['per'].items():
            n = ok + ko + bl
            rows.append((ok / n if n else 0, tid, ok, n))
        rows.sort()
        a = card(spacing=dp(6))
        for frac, tid, ok, n in rows:
            a.add_widget(Txt(f"{app.c.label(tid)} · {app.c.tema[tid]['short']}", size=13.5))
            colr = T['ok'] if frac >= 0.7 else (T['accent'] if frac >= 0.5 else T['ko'])
            a.add_widget(Bar(frac, color=colr, h=8))
            a.add_widget(Txt(f"{ok}/{n} ({pct(frac)})", size=12.5, color=T['muted']))
        b.add_widget(a)
        if rows and rows[0][0] < 0.7:
            frac, tid, ok, n = rows[0]
            b.add_widget(callout('rigor', f"Tu principal debilidad en este test: **{app.c.label(tid)}** ({pct(frac)}). Te recomendamos repasar ese tema y hacer el test de recuperación.",
                                 'TU PRINCIPAL DEBILIDAD'))
            b.add_widget(Btn(f"Ir al {app.c.label(tid)}", lambda tid=tid: app.go('tema', tid=tid), kind='outline', h=46))
        # plan de recuperación
        if r['ko'] > 25 or (r['n'] and r['ko'] / r['n'] > 0.4 and r['ko'] >= 4):
            p = card(spacing=dp(6))
            p.set_bg(T['warn_bg'])
            p.add_widget(Txt('PLAN DE RECUPERACIÓN', size=13, bold=True, color=T['warn']))
            p.add_widget(Txt(f"Has fallado {r['ko']} preguntas ({pct(r['ko'] / r['n'])}). Fallar no es fracasar: es información sobre lo que necesitas aprender.", size=14.5))
            secs = {}
            for qid in r['wrong']:
                q = app.c.q[qid]
                secs[(q['t'], q['s'])] = secs.get((q['t'], q['s']), 0) + 1
            top = sorted(secs.items(), key=lambda x: -x[1])[:4]
            for (tid, sid), n in top:
                sec = app.c.section(tid, sid)
                name = sec['title'] if sec else app.c.tema[tid]['short']
                p.add_widget(Txt(f"• {n} fallos en {app.c.label(tid)} — {md(name)}", size=14, raw=True))
            p.add_widget(Txt('El test de recuperación mezcla tus fallos con preguntas nuevas del mismo concepto y sube la dificultad poco a poco.', size=13.5, color=T['muted']))
            p.add_widget(Btn('HACER TEST DE RECUPERACIÓN', lambda: app.start(Session(app.e.recovery_test(r['wrong'], 25), title='Recuperación', kind='recup')),
                             kind='primary', h=50))
            b.add_widget(p)
        elif r['wrong']:
            b.add_widget(Btn(f"Repasar mis {len(r['wrong'])} fallos de este test", lambda: app.start(Session(app.e.recovery_test(r['wrong'], max(10, len(r['wrong']) * 2)), title='Recuperación', kind='recup')),
                             kind='primary', h=48))
        b.add_widget(Btn('Revisar todas las respuestas', lambda: app.go('review'), kind='outline', h=48))
        b.add_widget(Btn('Volver al inicio', app.home, kind='ghost', h=46))


class ReviewPage(Page):
    title = 'Revisión'

    def render(self, b):
        app = self.app
        s = app.session
        only = self.args.get('only')
        b.add_widget(row(Chip('Todas', not only, cb=lambda ch: app.go('review', replace=True)),
                         Chip('Solo fallos', only == 'ko', cb=lambda ch: app.go('review', only='ko', replace=True))))
        for i, qid in enumerate(s.qids):
            q = app.c.q[qid]
            a = s.answers.get(i)
            if only == 'ko' and a == q['k']:
                continue
            ok = a == q['k']
            mark = col('ok') + '✓' if ok else (col('muted') + '—' if a is None else col('ko') + '✗')
            b.add_widget(Btn(f"{mark}[/color]  [b]{i + 1}.[/b] {md(q['q'])}", lambda qid=qid, a=a: app.go('qdetail', qid=qid, chosen=a),
                             kind='ghost', halign='left', h=50, size=14, bold=False, raw=True))


class QDetailPage(Page):
    title = 'Pregunta'

    def render(self, b):
        app = self.app
        q = app.c.q[self.args['qid']]
        chosen = self.args.get('chosen', -1)
        b.add_widget(Txt(app.c.label(q['t']), size=12.5, color=T['muted']))
        b.add_widget(Txt(q['q'], size=17, bold=True))
        for i, o in enumerate(q['o']):
            t = f"[b]{LETTERS[i]})[/b] {md(o)}"
            btn = Btn(t, None, kind='outline', halign='left', size=15, h=50, bold=False, raw=True)
            if i == q['k']:
                btn.restyle(T['ok_bg'], T['text'], T['ok'])
            elif i == chosen:
                btn.restyle(T['ko_bg'], T['text'], T['ko'])
            b.add_widget(btn)
        st = app.s.qs(q['id'])
        if st:
            b.add_widget(Txt(f"Respondida {st['a']} veces · {st['c']} aciertos · {st['w']} fallos · racha {st['st']}", size=13, color=T['muted']))
        for w in feedback(app, q, chosen if chosen != -1 else q['k'], None):
            b.add_widget(w)
        isd = q['id'] in app.s.d['dudas']

        def tog():
            app.s.toggle('dudas', q['id'])
            app.s.save()
            self.build()
        b.add_widget(Btn('Quitar de mis dudas' if isd else 'Guardar como duda', tog, kind='outline', h=44))


# ---------------------------------------------------------------- FALLOS / DUDAS / FAVORITAS
class FallosPage(Page):
    title = 'Mis fallos'
    nav = 'fallos'
    back = False

    def render(self, b):
        app = self.app
        f = app.e.fallos()
        b.add_widget(Txt('Cada pregunta fallada se guarda y vuelve a salir con repetición espaciada (al día siguiente, a los 3, 7, 16 y 35 días) hasta que la aciertes 3 veces seguidas.',
                         size=13.5, color=T['muted']))
        g = grid(3, 6)
        for key, lab, colr, bg in (('pend', 'Pendientes', 'ko', 'ko_bg'), ('recu', 'En recuperación', 'warn', 'warn_bg'),
                                   ('dom', 'Dominadas', 'ok', 'ok_bg')):
            bx = Box(bg=T[bg], padding=[dp(6), dp(10)], radius=12)
            bx.add_widget(Txt(str(len(f[key])), size=24, bold=True, color=T[colr], halign='center'))
            bx.add_widget(Txt(lab, size=12.5, color=T[colr], halign='center', bold=True))
            g.add_widget(bx)
        b.add_widget(g)
        due = app.e.due()
        b.add_widget(Btn(f'Repaso del día ({len(due)})', lambda: app.start(Session(due[:30], title='Repaso del día', kind='repaso')) if due else app.toast('Hoy no tienes repasos pendientes'),
                         kind='primary', h=50))
        pend = f['pend'] + f['recu']
        b.add_widget(Btn(f'Test de recuperación ({len(pend)} fallos + preguntas del mismo concepto)',
                         lambda: app.start(Session(app.e.recovery_test(pend, 25), title='Recuperación', kind='recup')) if pend else app.toast('No tienes fallos pendientes'),
                         kind='outline', h=50))
        ws = app.e.weak_sections(3)
        if ws:
            b.add_widget(section_title('Mapa de conceptos débiles (microrrepasos)'))
            for n, tid, sid in ws[:6]:
                sec = app.c.section(tid, sid)
                b.add_widget(Btn(f"{n} fallos · {app.c.label(tid)} · {sec['title']}", lambda tid=tid, sid=sid: app.go('section', tid=tid, sid=sid, micro=True),
                                 kind='ghost', halign='left', size=14, h=46, bold=False))
        b.add_widget(section_title('Fallos por tema'))
        per = {}
        for k in ('pend', 'recu'):
            for qid in f[k]:
                per.setdefault(app.c.q[qid]['t'], []).append(qid)
        if not per:
            b.add_widget(Txt('No tienes fallos pendientes. ¡Sigue practicando!', size=14.5))
        for tid, lst in sorted(per.items(), key=lambda x: -len(x[1])):
            b.add_widget(Btn(f"{len(lst)} · {app.c.label(tid)} — {app.c.tema[tid]['short']}",
                             lambda lst=lst: app.start(Session(app.e.recovery_test(lst, min(25, len(lst) * 2)), title='Recuperación', kind='recup')),
                             kind='ghost', halign='left', size=14, h=46, bold=False))
        last = sorted([q for q in f['pend']], key=lambda q: -app.s.qs(q).get('lw', 0))[:25]
        if last:
            b.add_widget(section_title('Últimos fallos'))
            for qid in last:
                q = app.c.q[qid]
                st = app.s.qs(qid)
                b.add_widget(Btn(f"{col('ko')}●[/color] {md(q['q'])}  {col('muted')}({st['w']} fallos)[/color]",
                                 lambda qid=qid: app.go('qdetail', qid=qid), kind='ghost', halign='left', size=13.5, h=46, bold=False, raw=True))


class ListPage(Page):
    key = 'dudas'
    title = 'Mis dudas'
    empty = 'Cuando una pregunta no te quede clara, pulsa «Marcar duda» o «Guardar como duda» y aparecerá aquí.'

    def render(self, b):
        app = self.app
        lst = [q for q in app.s.d[self.key] if q in app.c.q]
        if lst:
            b.add_widget(Btn(f'Hacer test ({len(lst)} preguntas)', lambda: app.start(Session(_shuffled(lst)[:50], title=self.title)), kind='primary', h=50))
        else:
            b.add_widget(Txt(self.empty, size=14.5))
        for qid in reversed(lst):
            q = app.c.q[qid]
            b.add_widget(Btn(f"{md(q['q'])}  {col('muted')}· {app.c.label(q['t'])}[/color]", lambda qid=qid: app.go('qdetail', qid=qid),
                             kind='ghost', halign='left', size=14, h=50, bold=False, raw=True))


class DudasPage(ListPage):
    key = 'dudas'
    title = 'Mis dudas'


class FavsPage(ListPage):
    key = 'favq'
    title = 'Preguntas favoritas'
    empty = 'Pulsa «☆ Favorita» en cualquier pregunta para guardarla aquí.'


# ---------------------------------------------------------------- PROGRESO
class ProgresoPage(Page):
    title = 'Mi progreso'
    nav = 'progreso'
    back = False

    def render(self, b):
        app = self.app
        e, s = app.e, app.s
        idx, parts = e.readiness()
        c = card()
        c.add_widget(Txt('ÍNDICE DE PREPARACIÓN', size=12.5, color=T['muted'], bold=True))
        c.add_widget(Txt(f'[b]{idx}%[/b]', size=38, color=T['primary'], raw=True))
        c.add_widget(Bar(idx / 100, h=10))
        for lab, k in (('Temario estudiado', 'temario'), ('Banco de preguntas trabajado', 'banco'), ('Acierto reciente', 'acierto'),
                       ('Fallos recuperados', 'retencion'), ('Simulacros oficiales', 'simulacro')):
            c.add_widget(Txt(f"{lab}: [b]{pct(parts[k])}[/b]", size=13.5, raw=True))
            c.add_widget(Bar(parts[k], h=5))
        c.add_widget(Txt('Es un indicador interno para orientarte. No es una garantía de aprobar.', size=12, color=T['muted']))
        b.add_widget(c)
        tot = sum(x['a'] for x in s.d['q'].values())
        cor = sum(x['c'] for x in s.d['q'].values())
        f = e.fallos()
        g = grid(2, 8)
        for lab, val in (('Respuestas', str(tot)), ('Acierto global', pct(cor / tot if tot else None)),
                         ('Preguntas vistas', f"{len(s.d['q'])}/{len(app.c.preguntas)}"), ('Fallos recuperados', str(len(f['dom']))),
                         ('Racha de estudio', (f'{s.streak_days()} día' if s.streak_days() == 1 else f'{s.streak_days()} días')), ('Puntos', str(s.d['xp']))):
            bx = Box(bg=T['card'], padding=[dp(10), dp(10)], radius=12)
            bx.add_widget(Txt(val, size=19, bold=True))
            bx.add_widget(Txt(lab, size=12.5, color=T['muted']))
            g.add_widget(bx)
        b.add_widget(g)
        weak = e.weaknesses()
        if weak:
            b.add_widget(section_title('Mapa de debilidades · Top 5 a reforzar'))
            for tid, acc, n in weak[:5]:
                b.add_widget(self.tema_row(tid, acc, n))
            b.add_widget(section_title('Top 5 fortalezas'))
            for tid, acc, n in list(reversed(weak))[:5]:
                b.add_widget(self.tema_row(tid, acc, n))
        else:
            b.add_widget(Txt('Responde al menos 5 preguntas de un tema para ver tu mapa de debilidades y fortalezas.', size=14))
        hist = s.d['hist'][-10:]
        if hist:
            b.add_widget(section_title('Evolución (últimos tests)'))
            ch = BoxLayout(size_hint_y=None, height=dp(120), spacing=dp(6), padding=[dp(4), 0])
            for h in hist:
                frac = h['ok'] / h['n'] if h['n'] else 0
                colb = BoxLayout(orientation='vertical')
                colb.add_widget(Widget(size_hint_y=max(0.01, 1 - frac)))
                bar = Box(bg=T['ok'] if frac >= 0.7 else (T['accent'] if frac >= 0.5 else T['ko']), radius=4, auto=False, size_hint_y=max(0.02, frac))
                colb.add_widget(bar)
                ch.add_widget(colb)
            b.add_widget(ch)
            b.add_widget(Txt('Porcentaje de aciertos de tus últimos 10 tests (de izquierda a derecha, del más antiguo al más reciente).', size=12, color=T['muted']))
            b.add_widget(section_title('Historial'))
            for h in reversed(hist):
                d = datetime.datetime.fromtimestamp(h['ts']).strftime('%d/%m %H:%M')
                b.add_widget(Txt(f"{d} · {h['title']} · {h['ok']}/{h['n']} aciertos · {h['ko']} fallos", size=13.5))

    def tema_row(self, tid, acc, n):
        app = self.app
        c = card(spacing=dp(4))
        c.add_widget(Txt(f"{app.c.label(tid)} · {app.c.tema[tid]['short']}", size=14))
        colr = T['ok'] if acc >= 0.7 else (T['accent'] if acc >= 0.5 else T['ko'])
        c.add_widget(Bar(acc, color=colr, h=8))
        c.add_widget(row(Txt(f"{pct(acc)} de acierto en {n} respuestas", size=12.5, color=T['muted']),
                         Btn('Practicar', lambda: app.start(Session(app.e.smart_test(20, [tid]), title=f"Refuerzo {app.c.label(tid)}")),
                             kind='ghost', h=38, size=13, size_hint_x=0.45)))
        return c


# ---------------------------------------------------------------- PLAN DE ESTUDIO
class PlanPage(Page):
    title = 'Mi plan de estudio'

    def render(self, b):
        app = self.app
        p = app.s.d.setdefault('plan', {})
        b.add_widget(Txt('Indica la fecha del examen, cuánto tiempo puedes estudiar y qué días. El plan se adapta a tus resultados: primero lo no estudiado y después tus temas débiles; en las dos últimas semanas incluye simulacros.',
                         size=13.5, color=T['muted']))
        b.add_widget(section_title('Fecha del examen (dd/mm/aaaa)'))
        val = ''
        if p.get('exam'):
            d = datetime.date.fromisoformat(p['exam'])
            val = d.strftime('%d/%m/%Y')
        ti = TextInput(text=val, multiline=False, size_hint_y=None, height=dp(48), font_size=dp(17),
                       background_normal='', background_active='', background_color=T['card2'], foreground_color=T['text'], padding=[dp(10), dp(12)], cursor_color=T['primary'], hint_text='p. ej. 14/02/2027',
                       input_filter=lambda t, u: t if (t.isdigit() or t == '/') else '')
        b.add_widget(ti)
        b.add_widget(section_title('Minutos al día'))
        mins = grid(4, 6)
        mw = []

        def setm(ch, m):
            p['mins'] = m
            for w, v in mw:
                w.set(v == m)
        for m in (30, 60, 90, 120):
            w = Chip(f'{m} min', p.get('mins', 60) == m, cb=lambda ch, m=m: setm(ch, m))
            mw.append((w, m))
            mins.add_widget(w)
        b.add_widget(mins)
        b.add_widget(section_title('Días de estudio'))
        dg = grid(4, 6)
        days = set(p.get('days', [0, 1, 2, 3, 4]))

        def tog(ch, d):
            if d in days:
                days.discard(d)
            else:
                days.add(d)
            ch.set(d in days)
        for i, dn in enumerate(DIAS):
            dg.add_widget(Chip(dn[:3], i in days, cb=lambda ch, i=i: tog(ch, i)))
        b.add_widget(dg)

        def save():
            try:
                d = datetime.datetime.strptime(ti.text.strip(), '%d/%m/%Y').date()
            except Exception:
                app.toast('Fecha no válida (usa dd/mm/aaaa)')
                return
            if not days:
                app.toast('Elige al menos un día')
                return
            p['exam'] = d.isoformat()
            p['days'] = sorted(days)
            p.setdefault('mins', 60)
            app.s.save()
            self.build()
        b.add_widget(Btn('GENERAR / ACTUALIZAR PLAN', save, kind='primary', h=50))
        plan = app.e.plan_week()
        if plan:
            b.add_widget(Txt(f"Faltan [b]{plan['left']}[/b] días para el examen.", size=15, raw=True))
            for d, tasks in plan['days']:
                c = card(spacing=dp(6))
                c.add_widget(Txt(fmt_date(d).upper(), size=13, bold=True, color=T['primary']))
                for t in tasks:
                    kind, m, text = t[0], t[1], t[2]
                    tid = t[3] if len(t) > 3 else None
                    if kind == 'read':
                        cb = (lambda tid=tid: app.go('tema', tid=tid))
                    elif kind == 'test':
                        cb = (lambda tid=tid: app.start(Session(app.e.smart_test(20, [tid]), title='Test del plan')))
                    elif kind == 'sim':
                        cb = (lambda: app.go('sim'))
                    else:
                        cb = (lambda: app.go('fallos'))
                    c.add_widget(Btn(f"[b]{m} min[/b] → {md(text)}", cb, kind='ghost', halign='left', size=14, h=44, bold=False, raw=True))
                b.add_widget(c)


# ---------------------------------------------------------------- BASES
class BasesPage(Page):
    title = 'Bases de la oposición'

    def render(self, b):
        app = self.app
        b.add_widget(Txt('Conductor/a E2 · Parque Móvil del Estado', size=18, bold=True))
        hi = card()
        hi.add_widget(Txt('¿CÓMO ES EL EXAMEN?', size=12.5, bold=True, color=T['muted']))
        for line in ('**100 preguntas** · 40 comunes + 60 específicas', '**100 minutos**', 'Cada fallo **resta 1/3** · en blanco no resta',
                     'Aprobado con **50 puntos** sobre 100', 'Después: prueba práctica en **simulador** (mín. 25/50)'):
            hi.add_widget(Txt('•  ' + line, size=15))
        b.add_widget(hi)
        b.add_widget(Btn('Hacer un simulacro oficial', lambda: app.go('sim'), kind='primary', h=48))
        b.add_widget(section_title('Apartados'))
        for sec in app.c.bases['secs']:
            ind = '      ' if '.' in sec['id'] else ''
            label = f"{ind}{sec['id'] + '. ' if sec['id'] != 'F' else ''}{sec['title']}"
            b.add_widget(Btn(label, lambda sid=sec['id']: app.go('section', tid='bases', sid=sid), kind='ghost', halign='left', size=14.5, h=46, bold=False))


# ---------------------------------------------------------------- AJUSTES
class AjustesPage(Page):
    title = 'Ajustes'

    def render(self, b):
        app = self.app
        st = app.s.d['settings']
        b.add_widget(section_title('Tu nombre (para el saludo)'))
        ti = TextInput(text=st.get('name', ''), multiline=False, size_hint_y=None, height=dp(48), font_size=dp(16),
                       background_normal='', background_active='', background_color=T['card2'], foreground_color=T['text'], padding=[dp(10), dp(12)], cursor_color=T['primary'])
        b.add_widget(ti)

        def savename():
            st['name'] = ti.text.strip()[:30]
            app.s.save()
            app.toast('Guardado')
        b.add_widget(Btn('Guardar nombre', savename, kind='outline', h=44))
        b.add_widget(section_title('Apariencia'))
        b.add_widget(row(Chip('Modo claro', st.get('theme') == 'light', cb=lambda ch: app.set_theme('light')),
                         Chip('Modo oscuro', st.get('theme') == 'dark', cb=lambda ch: app.set_theme('dark'))))
        b.add_widget(section_title('Tamaño del texto'))
        b.add_widget(row(*[Chip(lab, abs(st.get('font', 1.0) - v) < 0.01, cb=lambda ch, v=v: app.set_font(v))
                           for lab, v in (('Normal', 1.0), ('Grande', 1.15), ('Muy grande', 1.3))]))
        b.add_widget(section_title('Contenido'))
        c = card()
        c.add_widget(Txt(f"Versión del contenido: {app.c.version} · {len(app.c.preguntas)} preguntas · {len(app.c.temas)} temas", size=14))
        c.add_widget(Txt('Diferenciamos siempre: **contenido oficial** (normas y bases citadas en las fuentes de cada tema), **explicaciones de elaboración propia** para estudiar y **preguntas propias** para practicar (no son preguntas oficiales de examen). Las normas pueden cambiar: verifica en el BOE las notas de rigor marcadas.', size=13.5))
        b.add_widget(c)
        b.add_widget(section_title('Datos'))
        b.add_widget(Btn('Borrar todo mi progreso', lambda: app.confirm('¿Seguro? Se borrarán respuestas, fallos, dudas, notas y plan.', app.reset, ok='Borrar'),
                         kind='ko', h=46))


# ======================================================================
class PMEApp(App):
    title = APP_NAME

    def build(self):
        self.c = engine.Content(os.path.join(HERE, 'data', 'content.json'))
        self.s = engine.Store(os.path.join(self.user_data_dir, 'progreso.json'))
        self.e = engine.Engine(self.c, self.s)
        st = self.s.d['settings']
        ui.register_fonts(HERE)
        ui.set_theme(st.get('theme', 'light'), st.get('font', 1.0))
        Window.clearcolor = T['bg']
        Window.softinput_mode = 'below_target'
        self.args = {}
        self.stack = []
        self.session = None
        self.sm = ScreenManager(transition=NoTransition())
        for name, cls in (('home', HomePage), ('temario', TemarioPage), ('tema', TemaPage), ('section', SectionPage),
                          ('test', TestPage), ('sim', SimPage), ('quiz', QuizPage), ('result', ResultPage),
                          ('review', ReviewPage), ('qdetail', QDetailPage), ('fallos', FallosPage), ('dudas', DudasPage),
                          ('favs', FavsPage), ('progreso', ProgresoPage), ('plan', PlanPage), ('bases', BasesPage),
                          ('ajustes', AjustesPage)):
            self.sm.add_widget(cls(name=name))
        Window.bind(on_keyboard=self.on_key)
        self.go('home')
        return self.sm

    def screen(self, name):
        return self.sm.get_screen(name)

    # navegación -------------------------------------------------------
    def go(self, name, replace=False, root=False, **kw):
        if root:
            self.stack = []
        if replace and self.stack:
            self.stack.pop()
        self.args[name] = kw
        self.stack.append((name, kw))
        if self.sm.current == name:
            self.screen(name).build()
        else:
            self.sm.current = name

    def back(self):
        cur = self.stack[-1][0] if self.stack else None
        if cur == 'quiz' and self.session and not self.session.finished:
            self.confirm('¿Salir del test? Las respuestas ya corregidas quedan guardadas en tu progreso.', self._pop, ok='Salir')
            return
        self._pop()

    def _pop(self):
        if len(self.stack) > 1:
            self.stack.pop()
            name, kw = self.stack[-1]
            self.args[name] = kw
            if self.sm.current == name:
                self.screen(name).build()
            else:
                self.sm.current = name
        return True

    def home(self):
        self.stack = []
        self.go('home')

    def on_key(self, window, key, *a):
        if key == 27:   # botón atrás de Android
            if len(self.stack) > 1:
                self.back()
                return True
            return False
        return False

    def navbar(self, active):
        bar = BoxLayout(size_hint_y=None, height=dp(62), padding=[dp(4), dp(6)], spacing=dp(4))
        with bar.canvas.before:
            Color(*T['line'])
            r1 = Rectangle()
            Color(*T['nav'])
            r2 = Rectangle()

        def upd(*a):
            r1.pos = (bar.x, bar.top - dp(1))
            r1.size = (bar.width, dp(1))
            r2.pos = bar.pos
            r2.size = (bar.width, bar.height - dp(1))
        bar.bind(pos=upd, size=upd)
        for key, label in (('home', 'Inicio'), ('temario', 'Temario'), ('test', 'Test'), ('fallos', 'Fallos'), ('progreso', 'Progreso')):
            k = 'primary' if key == active else 'flat'
            btn = Btn(label, lambda key=key: self.go(key, root=True), kind=k, h=48, size=13.5)
            if key != active:
                btn.restyle(T['nav'], T['muted'])
            bar.add_widget(btn)
        return bar

    # sesiones -----------------------------------------------------------
    def start(self, session):
        if not session.qids:
            self.toast('No hay preguntas disponibles para esto todavía')
            return
        self.session = session
        if self.stack and self.stack[-1][0] in ('quiz', 'result', 'review'):
            while self.stack and self.stack[-1][0] in ('quiz', 'result', 'review', 'qdetail'):
                self.stack.pop()
        self.go('quiz')

    def finish_session(self):
        s = self.session
        if s.finished:
            return
        s.finished = True
        if s.mode == 'exam':
            for i, qid in enumerate(s.qids):
                if i in s.answers:
                    self.s.record(qid, s.answers[i] == self.c.q[qid]['k'])
        r = self.e.grade(s.qids, s.answers, s.penal)
        s.result = r
        s.result_dur = min(s.elapsed(), s.limit) if s.limit else s.elapsed()
        self.e.save_result(s.kind, s.title, r, s.result_dur, s.mode)
        while self.stack and self.stack[-1][0] in ('quiz', 'section', 'qdetail'):
            self.stack.pop()
        self.go('result')

    # ajustes ------------------------------------------------------------
    def set_theme(self, name):
        self.s.d['settings']['theme'] = name
        self.s.save()
        ui.set_theme(name, self.s.d['settings'].get('font', 1.0))
        Window.clearcolor = T['bg']
        self.screen(self.sm.current).build()

    def set_font(self, v):
        self.s.d['settings']['font'] = v
        self.s.save()
        ui.set_theme(self.s.d['settings'].get('theme', 'light'), v)
        self.screen(self.sm.current).build()

    def reset(self):
        path = self.s.path
        if os.path.exists(path):
            os.remove(path)
        self.s = engine.Store(path)
        self.e = engine.Engine(self.c, self.s)
        ui.set_theme('light', 1.0)
        self.home()
        self.toast('Progreso borrado')

    # utilidades ---------------------------------------------------------
    def toast(self, msg):
        lab = Txt(msg, size=14, color=T['primary_t'], halign='center')
        box = Box(bg=T['text'], padding=[dp(14), dp(10)], radius=12, auto=False, size_hint=(None, None))
        box.add_widget(lab)
        box.width = min(Window.width - dp(40), dp(420))
        lab.width = box.width - dp(28)
        lab.texture_update()
        box.height = lab.texture_size[1] + dp(24)
        box.pos = ((Window.width - box.width) / 2, dp(90))
        Window.add_widget(box)
        Clock.schedule_once(lambda dt: Window.remove_widget(box), 2.2)

    def confirm(self, msg, cb, ok='Aceptar'):
        content = Box(bg=T['card'], padding=[dp(14), dp(14)], spacing=dp(12), auto=False)
        content.add_widget(Txt(msg, size=15))
        content.add_widget(Widget())
        pop = Popup(title='Confirmar', content=content, size_hint=(0.9, None), height=dp(260),
                    separator_color=T['primary'], title_color=T['text'], background_color=T['card'])
        content.add_widget(row(Btn('Cancelar', pop.dismiss, kind='ghost', h=46),
                               Btn(ok, lambda: (pop.dismiss(), cb()), kind='primary', h=46)))
        pop.open()

    def on_pause(self):
        try:
            self.s.save()
        except Exception:
            pass
        return True

    def on_stop(self):
        try:
            self.s.save()
        except Exception:
            pass


def _show_crash(text):
    """Si algo falla al arrancar, se muestra el error en pantalla (para poder corregirlo)."""
    from kivy.uix.label import Label as _L

    class CrashApp(App):
        def build(self):
            sv = ScrollView()
            lab = _L(text='La app ha encontrado un error al arrancar.\nHaz una captura de pantalla y envíasela a Claude.\n\n' + text,
                     size_hint_y=None, halign='left', valign='top', font_size='13sp', color=(1, 1, 1, 1))
            lab.bind(width=lambda w, v: setattr(w, 'text_size', (v, None)),
                     texture_size=lambda w, v: setattr(w, 'height', v[1]))
            sv.add_widget(lab)
            return sv
    CrashApp().run()


if __name__ == '__main__':
    import traceback
    try:
        PMEApp().run()
    except Exception:
        err = traceback.format_exc()
        try:
            with open(os.path.join(HERE, 'crash.txt'), 'w') as f:
                f.write(err)
        except Exception:
            pass
        _show_crash(err[-3000:])
