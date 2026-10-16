# -*- coding: utf-8 -*-
"""Widgets y tema visual (claro/oscuro) de la app."""
import re
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex as hx

THEMES = {
    'light': {
        'bg': '#F3F5F9', 'card': '#FFFFFF', 'card2': '#EEF2F8', 'text': '#1A1F27', 'muted': '#5D6878',
        'primary': '#1F4E8C', 'primary_t': '#FFFFFF', 'accent': '#D9971A', 'line': '#DDE3EC',
        'ok': '#2E7D32', 'ok_bg': '#E5F3E6', 'ko': '#C62828', 'ko_bg': '#FBE7E7', 'warn': '#B85C00',
        'warn_bg': '#FFF1DF', 'info_bg': '#E7EFFB', 'star_bg': '#FFF6DA', 'nav': '#FFFFFF',
        'opt': '#FFFFFF', 'opt_line': '#C9D2DF', 'sel': '#DCE7F7',
    },
    'dark': {
        'bg': '#111418', 'card': '#1B2027', 'card2': '#242B34', 'text': '#E8EBEF', 'muted': '#A3ADBA',
        'primary': '#5B9BEF', 'primary_t': '#0B1220', 'accent': '#F2B84B', 'line': '#2E3640',
        'ok': '#6CCB73', 'ok_bg': '#1D3322', 'ko': '#FF7B7B', 'ko_bg': '#3A1E21', 'warn': '#FFB45E',
        'warn_bg': '#3A2C18', 'info_bg': '#1D2A3D', 'star_bg': '#3A3218', 'nav': '#171B21',
        'opt': '#1F252D', 'opt_line': '#3A4450', 'sel': '#22344D',
    },
}

T = {}
FS = [1.0]


def register_fonts(here):
    from kivy.core.text import LabelBase
    import os
    LabelBase.register(name='Sym', fn_regular=os.path.join(here, 'fonts', 'Sym.ttf'),
                       fn_bold=os.path.join(here, 'fonts', 'Sym-Bold.ttf'))


def set_theme(name, font=1.0):
    T.clear()
    for k, v in THEMES.get(name, THEMES['light']).items():
        T[k] = hx(v)
        T[k + '#'] = v.lstrip('#')
    FS[0] = font


def esc(s):
    return s.replace('&', '&amp;').replace('[', '&bl;').replace(']', '&br;')


SYMS = set('✓✗★☆⚑●≈≤≥≠→')


def sym(s):
    """Los símbolos que no tiene Roboto se pintan con la fuente Sym (subconjunto de DejaVu)."""
    return ''.join('[font=Sym]' + ch + '[/font]' if ch in SYMS else ch for ch in s)


def md(s):
    """**negrita** y *cursiva* a markup de Kivy (respeta etiquetas [b] [i] [color] ya presentes)."""
    s = esc(s)
    s = re.sub(r'&bl;(/?(?:b|i|color(?:=#?[0-9A-Fa-f]{6,8})?))&br;', r'[\1]', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'[b]\1[/b]', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'[i]\1[/i]', s)
    return sym(s.replace('**', ''))


def col(name):
    return '[color=' + T[name + '#'] + ']'


class Bg:
    """Mixin: fondo redondeado."""

    def _init_bg(self, bg, radius, line=None):
        self._bgc = None
        with self.canvas.before:
            if line is not None:
                self._lc = Color(*line)
                self._lr = RoundedRectangle(radius=[dp(radius)])
            if bg is not None:
                self._bgc = Color(*bg)
                self._bgr = RoundedRectangle(radius=[dp(radius)])
        self._line = line is not None
        self.bind(pos=self._upd_bg, size=self._upd_bg)

    def _upd_bg(self, *a):
        if self._line:
            self._lr.pos = self.pos
            self._lr.size = self.size
        if self._bgc is not None:
            if self._line:
                self._bgr.pos = (self.x + dp(1.2), self.y + dp(1.2))
                self._bgr.size = (self.width - dp(2.4), self.height - dp(2.4))
            else:
                self._bgr.pos = self.pos
                self._bgr.size = self.size

    def set_bg(self, bg, line=None):
        if self._bgc is not None and bg is not None:
            self._bgc.rgba = bg
        if line is not None and self._line:
            self._lc.rgba = line


class Box(Bg, BoxLayout):
    def __init__(self, bg=None, radius=14, line=None, auto=True, **kw):
        kw.setdefault('orientation', 'vertical')
        if auto:
            kw.setdefault('size_hint_y', None)
        super().__init__(**kw)
        self._init_bg(bg, radius, line)
        if auto and self.orientation == 'vertical':
            self.bind(minimum_height=self.setter('height'))


def card(**kw):
    kw.setdefault('padding', [dp(16), dp(14)])
    kw.setdefault('spacing', dp(8))
    return Box(bg=T['card'], **kw)


class Txt(Label):
    def __init__(self, text='', size=15, color=None, bold=False, halign='left', pad=4, raw=False, **kw):
        super().__init__(text=sym(text) if raw else md(text), markup=True, font_size=sp(size * FS[0]),
                         color=color or T['text'], bold=bold, halign=halign, valign='middle',
                         size_hint_y=None, **kw)
        self._pad = pad
        self.bind(width=self._w, texture_size=self._h)

    def _w(self, *a):
        self.text_size = (self.width, None)

    def _h(self, *a):
        self.height = self.texture_size[1] + dp(self._pad)


BTN = {
    'primary': ('primary', 'primary_t', None),
    'ghost': ('card2', 'text', None),
    'outline': ('card', 'primary', 'primary'),
    'ok': ('ok', 'primary_t', None),
    'ko': ('ko', 'primary_t', None),
    'accent': ('accent', 'primary_t', None),
    'flat': ('bg', 'primary', None),
}


class Btn(ButtonBehavior, Bg, Label):
    def __init__(self, text, cb=None, kind='primary', size=15, h=50, halign='center', bold=True, raw=False, **kw):
        bg, fg, line = BTN[kind]
        self._kind = kind
        super().__init__(text=sym(text) if raw else md(text), markup=True, font_size=sp(size * FS[0]), color=T[fg],
                         halign=halign, valign='middle', bold=bold, size_hint_y=None, height=dp(h), **kw)
        self._minh = dp(h)
        self._init_bg(T[bg], 12, T[line] if line else None)
        self._base = T[bg]
        self.bind(width=self._w, texture_size=self._h)
        if cb:
            self.bind(on_release=lambda *a: cb())

    def _w(self, *a):
        self.text_size = (self.width - dp(24), None)

    def _h(self, *a):
        self.height = max(self._minh, self.texture_size[1] + dp(22))

    def on_state(self, inst, val):
        if self._bgc is None:
            return
        if val == 'down':
            c = self._base
            self._bgc.rgba = (c[0] * 0.85, c[1] * 0.85, c[2] * 0.85, 1)
        else:
            self._bgc.rgba = self._base

    def restyle(self, bg, fg, line=None):
        self._base = bg
        self.set_bg(bg, line)
        self.color = fg


class Chip(Btn):
    """Botón conmutable para filtros."""

    def __init__(self, text, active=False, cb=None, **kw):
        kw.setdefault('h', 40)
        kw.setdefault('size', 14)
        super().__init__(text, None, kind='ghost', **kw)
        self.active = active
        self._cb = cb
        self.bind(on_release=self._toggle)
        self._paint()

    def _toggle(self, *a):
        if self._cb:
            self._cb(self)

    def set(self, v):
        self.active = v
        self._paint()

    def _paint(self):
        if self.active:
            self.restyle(T['primary'], T['primary_t'])
        else:
            self.restyle(T['card2'], T['text'])


class Bar(Widget):
    """Barra de progreso."""

    def __init__(self, value=0.0, color=None, h=8, **kw):
        super().__init__(size_hint_y=None, height=dp(h), **kw)
        self.value = max(0.0, min(1.0, value or 0))
        with self.canvas:
            Color(*T['line'])
            self._b = RoundedRectangle(radius=[dp(h / 2)])
            Color(*(color or T['primary']))
            self._f = RoundedRectangle(radius=[dp(h / 2)])
        self.bind(pos=self._u, size=self._u)

    def _u(self, *a):
        self._b.pos = self.pos
        self._b.size = self.size
        self._f.pos = self.pos
        self._f.size = (max(self.height, self.width * self.value) if self.value > 0 else 0, self.height)


def gap(h=8):
    return Widget(size_hint_y=None, height=dp(h))


def row(*widgets, spacing=8, h=None):
    b = BoxLayout(orientation='horizontal', spacing=dp(spacing), size_hint_y=None)
    for w in widgets:
        b.add_widget(w)
    if h:
        b.height = dp(h)
    else:
        def fit(*a):
            b.height = max([w.height for w in b.children] + [dp(10)])
        for w in widgets:
            w.bind(height=fit)
        fit()
    return b


def grid(cols=2, spacing=8):
    g = GridLayout(cols=cols, spacing=dp(spacing), size_hint_y=None)
    g.bind(minimum_height=g.setter('height'))
    return g


CALL_STYLE = {
    'star': ('star_bg', 'accent', 'MUY PREGUNTADO'),
    'info': ('info_bg', 'primary', 'IMPORTANTE'),
    'rigor': ('warn_bg', 'warn', 'NOTA DE RIGOR'),
    'error': ('ko_bg', 'ko', 'ERROR FRECUENTE'),
    'memo': ('ok_bg', 'ok', 'PARA RECORDAR'),
    'trap': ('warn_bg', 'warn', 'ATENCIÓN'),
}


def callout(kind, text, title=None):
    bg, fg, label = CALL_STYLE.get(kind, CALL_STYLE['info'])
    b = Box(bg=T[bg], padding=[dp(14), dp(10)], spacing=dp(4), radius=12)
    b.add_widget(Txt(title or label, size=12.5, color=T[fg], bold=True))
    b.add_widget(Txt(text, size=15))
    return b


class Cell(Bg, Label):
    def __init__(self, text, bg, bold=False):
        super().__init__(text=md(text), markup=True, font_size=sp(13.5 * FS[0]), color=T['text'], bold=bold,
                         halign='left', valign='top', size_hint_y=None, padding=(dp(8), dp(6)))
        self._init_bg(bg, 2)
        self.bind(width=lambda *a: setattr(self, 'text_size', (self.width, None)),
                  texture_size=lambda *a: setattr(self, 'height', self.texture_size[1]))


def table(rows):
    ncol = max(len(r) for r in rows)
    b = Box(bg=T['card'], line=T['line'], padding=[dp(2), dp(2)], spacing=0, radius=8)
    g = GridLayout(cols=ncol, spacing=0, size_hint_y=None)
    g.bind(minimum_height=g.setter('height'))
    for i, r in enumerate(rows):
        for j in range(ncol):
            g.add_widget(Cell(r[j] if j < len(r) else '', T['card2'] if i == 0 else None, bold=(i == 0)))
    b.add_widget(g)
    return b


def render_blocks(blocks, parent):
    for bl in blocks:
        t = bl['t']
        if t == 'p':
            parent.add_widget(Txt(bl['x'], size=15.5, pad=6))
        elif t == 'li':
            ind = '      ' if bl.get('l') else ''
            dot = '–' if bl.get('l') else '•'
            parent.add_widget(Txt(ind + col('primary') + dot + '[/color]  ' + md(bl['x']), size=15.5, raw=True, pad=4))
        elif t == 'ol':
            parent.add_widget(Txt(col('primary') + '[b]' + bl['n'] + '.[/b][/color]  ' + md(bl['x']), size=15.5, raw=True))
        elif t == 'call':
            parent.add_widget(callout(bl['k'], bl['x']))
        elif t == 'table':
            parent.add_widget(table(bl['rows']))
        elif t == 'h4':
            parent.add_widget(Txt(bl['x'], size=16, bold=True))
