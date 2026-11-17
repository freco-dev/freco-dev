#!/usr/bin/env python3
"""
Monochrome terminal SVG generator for the freco-dev GitHub profile.

Edit the scenes at the bottom (HEADER / TERMINAL) and run:
    python3 scripts/gen.py
It rewrites assets/header.svg, assets/terminal.svg, assets/pulse.svg.

Pure CSS animations inside SVG -> they play when GitHub embeds them via <img>.
No JS, no external fonts.
"""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"

# ---- palette (monochrome) -------------------------------------------------
BG = "#0a0a0a"
BORDER = "#262626"
BAR = "#141414"
FG = "#e6e6e6"
DIM = "#8a8a8a"
FAINT = "#4a4a4a"
SHADOW = "#2e2e2e"

FONT = ("'JetBrains Mono','Fira Code','SF Mono',SFMono-Regular,ui-monospace,"
        "Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace")
FS = 14          # font size
CW = 8.43        # assumed monospace char width at 14px (0.6em)
LH = 22          # line height
PAD_X = 22
TYPE_SPEED = 0.045   # seconds per typed char

PROMPT = [("freco", FG, True), ("@", DIM, False), ("dev", FG, True),
          (":", DIM, False), ("~", FG, False), ("$ ", DIM, False)]
PROMPT_LEN = sum(len(s) for s, _, _ in PROMPT)


def fmt(t):
    return f"{t:.2f}".rstrip("0").rstrip(".") + "s"


class Scene:
    def __init__(self, width, title, top=46):
        self.w = width
        self.title = title
        self.body = []
        self.css = []
        self.kid = 0
        self.t = 0.5
        self.y = top + 18          # baseline of first line
        self.top = top
        self.extra_top = []        # things drawn above lines (banners)

    # -- helpers -----------------------------------------------------------
    def _k(self):
        self.kid += 1
        return f"k{self.kid}"

    @staticmethod
    def show(t):
        return f"on .01s {fmt(t)} forwards"

    @staticmethod
    def hide(t):
        return f"off .01s {fmt(t)} forwards"

    def tspans(self, parts):
        out = []
        for s, col, bold in parts:
            w = ' font-weight="700"' if bold else ""
            out.append(f'<tspan fill="{col}"{w}>{escape(s)}</tspan>')
        return "".join(out)

    def text(self, x, y, parts, cls="", style=""):
        c = f' class="{cls}"' if cls else ""
        st = f' style="{style}"' if style else ""
        return (f'<text x="{x:.1f}" y="{y}" xml:space="preserve"{c}{st}>'
                f'{self.tspans(parts)}</text>')

    # -- primitives --------------------------------------------------------
    def cmd(self, command, pause_before=0.35, pause_after=0.25):
        """Prompt appears, cursor waits, command is typed, Enter."""
        t0 = self.t
        y = self.y
        x_cmd = PAD_X + PROMPT_LEN * CW
        n = len(command)
        t_type = t0 + pause_before
        dur = max(n * TYPE_SPEED, 0.05)
        t_end = t_type + dur
        k = self._k()
        dist = n * CW
        self.css.append(f"@keyframes {k}{{to{{transform:translateX({dist:.1f}px)}}}}")
        g = [f'<g class="h" style="animation:{self.show(t0)}">',
             self.text(PAD_X, y, PROMPT),
             self.text(x_cmd, y, [(command, FG, False)]),
             # cover + cursor slide right in char steps
             f'<g style="animation:{k} {fmt(dur)} steps({n}) {fmt(t_type)} forwards,'
             f'{self.hide(t_end + pause_after)}">',
             f'<rect x="{x_cmd:.1f}" y="{y - 15}" width="{dist + 60:.1f}" height="20" fill="{BG}"/>',
             f'<rect x="{x_cmd:.1f}" y="{y - 14}" width="{CW:.1f}" height="18" fill="{FG}"/>',
             "</g></g>"]
        self.body.append("".join(g))
        self.t = t_end + pause_after
        self.y += LH
        return self

    def out(self, parts, delay=0.06, x=None):
        """Instant output line."""
        if isinstance(parts, str):
            parts = [(parts, DIM, False)]
        self.t += delay
        self.body.append(self.text(x if x is not None else PAD_X, self.y, parts,
                                   cls="h", style=f"animation:{self.show(self.t)}"))
        self.y += LH
        return self

    def swap(self, before, after, wait):
        """Line shows `before`, then switches to `after` after `wait` seconds."""
        self.t += 0.08
        t1 = self.t
        t2 = t1 + wait
        self.body.append(self.text(PAD_X, self.y, before, cls="h",
                                   style=f"animation:{self.show(t1)},{self.hide(t2)}"))
        self.body.append(self.text(PAD_X, self.y, after, cls="h",
                                   style=f"animation:{self.show(t2)}"))
        self.y += LH
        return t2

    def gap(self, h=8, t=0.0):
        self.y += h
        self.t += t
        return self

    def final_prompt(self):
        y = self.y
        x = PAD_X + PROMPT_LEN * CW
        self.body.append(f'<g class="h" style="animation:{self.show(self.t)}">'
                         + self.text(PAD_X, y, PROMPT)
                         + f'<rect class="blink" x="{x:.1f}" y="{y - 14}" width="{CW:.1f}" height="18" fill="{FG}"/></g>')
        self.y += LH
        return self

    def pixels(self, word, px=8, pitch=9, start=None):
        """Big 5x7 pixel banner that sweeps in column by column."""
        t0 = self.t if start is None else start
        x0 = PAD_X + 2
        y0 = self.y - 12
        col = 0
        shadow, front = [], []
        for ch in word:
            g = GLYPHS[ch]
            for c in range(5):
                tc = t0 + col * 0.022
                for r in range(7):
                    if g[r][c] == "1":
                        x = x0 + col * pitch
                        y = y0 + r * pitch
                        st = f"animation:{self.show(tc)}"
                        shadow.append(f'<rect class="h" x="{x + 3}" y="{y + 3}" width="{px}" height="{px}" fill="{SHADOW}" style="{st}"/>')
                        front.append(f'<rect class="h" x="{x}" y="{y}" width="{px}" height="{px}" fill="{FG}" style="{st}"/>')
                col += 1
            col += 1  # letter spacing
        self.body.append("".join(shadow) + "".join(front))
        self.y += 7 * pitch + 14
        self.t = t0 + col * 0.022 + 0.3
        return self

    # -- render -----------------------------------------------------------
    def render(self, path):
        h = int(self.y + 4)
        w = self.w
        title_x = w / 2
        css = "\n".join([
            f"text{{font-family:{FONT};font-size:{FS}px}}",
            ".h{opacity:0}",
            "@keyframes on{to{opacity:1}}",
            "@keyframes off{to{opacity:0}}",
            "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}",
            ".blink{animation:blink 1.05s step-end infinite}",
            "@keyframes scan{from{transform:translateY(-40px)}to{transform:translateY(%dpx)}}" % (h + 40),
            ".scan{animation:scan 7s linear infinite}",
            "@media (prefers-reduced-motion:reduce){*{animation-duration:.01s!important;animation-delay:0s!important}"
            ".blink,.scan{animation:none!important}}",
            *self.css,
        ])
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(self.title)}">
<style>
{css}
</style>
<defs>
<clipPath id="win"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="10"/></clipPath>
<linearGradient id="sl" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".045"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
</linearGradient>
</defs>
<g clip-path="url(#win)">
<rect width="{w}" height="{h}" fill="{BG}"/>
<rect width="{w}" height="34" fill="{BAR}"/>
<line x1="0" y1="34.5" x2="{w}" y2="34.5" stroke="{BORDER}"/>
<circle cx="20" cy="17" r="5.5" fill="none" stroke="{DIM}"/>
<circle cx="38" cy="17" r="5.5" fill="none" stroke="{DIM}"/>
<circle cx="56" cy="17" r="5.5" fill="{DIM}"/>
<text x="{title_x}" y="21.5" text-anchor="middle" fill="{DIM}" style="font-size:12px">{escape(self.title)}</text>
{"".join(self.body)}
<rect class="scan" x="0" y="0" width="{w}" height="40" fill="url(#sl)"/>
</g>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" fill="none" stroke="{BORDER}"/>
</svg>
'''
        path.write_text(svg)
        print(f"wrote {path.name}: {w}x{h}, ends at {self.t:.1f}s")


GLYPHS = {
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
}

W = 840

# ============================================================================
# HEADER
# ============================================================================
s = Scene(W, "freco@dev: ~")
s.cmd("figlet freco-dev")
s.gap(4).pixels("FRECO-DEV")
s.cmd("whoami")
s.out([("Nurullo Muxiddinov", FG, True), ("  //  ", FAINT, False),
       ("Site Reliability Engineer · Full-Stack Developer", DIM, False)])
s.gap(6)
s.cmd("cat /etc/motd")
s.out([("> ", FAINT, False), ("building infra that stays up when everything else goes down", DIM, False)])
s.out([("> ", FAINT, False), ("Go · Python · TypeScript · eBPF · 1C integrations · AI/ML", DIM, False)])
s.out([("> ", FAINT, False), ("Tashkent, UZ  ·  UTC+5", DIM, False)])
s.gap(6)
s.final_prompt()
s.render(OUT / "header.svg")

# ============================================================================
# TERMINAL — projects + healthcheck
# ============================================================================
PROJECTS = [
    ("cc01",            "overlay network · eBPF firewall · IPv6/client", "go"),
    ("rivora",          "course marketplace + LMS, live classes",         "go/nuxt"),
    ("wms",             "enterprise warehouse management system",         "go"),
    ("face-attendance", "face-recognition attendance, hybrid cloud",      "py/go"),
    ("hud-bridge",      "navigator -> factory car HUD bridge",            "android"),
    ("live-vst-host",   "ultra-low-latency live VST host",                "c++20"),
]

t = Scene(W, "freco@dev: ~/projects")
t.cmd("ls ~/projects")
t.out([("  ".join(p[0] + "/" for p in PROJECTS), FG, False)])
t.gap(6)
t.cmd("./healthcheck --all --verbose")
t.out([("running %d checks..." % len(PROJECTS), FAINT, False)], delay=0.15)
t.gap(2)
last = 0
for i, (name, desc, lang) in enumerate(PROJECTS):
    base = [(f"  {name:<17}", FG, True), (f"{desc:<46}", DIM, False), (f"{lang:<9}", FAINT, False)]
    last = t.swap(base + [("[ .... ]", FAINT, False)],
                  base + [("[  ", DIM, False), ("OK", FG, True), ("  ]", DIM, False)],
                  wait=0.55 + 0.12 * i)
t.t = last + 0.25
t.gap(4)
t.out([("  %d/%d checks passed" % (len(PROJECTS), len(PROJECTS)), FG, True),
       ("  ·  0 warnings  ·  exit 0", FAINT, False)])
t.gap(6)
t.final_prompt()
t.render(OUT / "terminal.svg")


# ============================================================================
# PULSE — looping heartbeat divider
# ============================================================================
def pulse(path, w=W, h=96):
    period = 140  # px per beat
    beats = w // period + 3
    B = 60
    seg = []
    for b in range(beats):
        x = b * period
        seg.append(f"L{x + 40},{B} L{x + 52},{B} L{x + 58},{B - 9} L{x + 64},{B + 9} L{x + 70},{B - 26} "
                   f"L{x + 77},{B + 24} L{x + 83},{B - 4} L{x + 90},{B} L{x + period},{B}")
    d = f"M0,{B} " + " ".join(seg)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="heartbeat">
<style>
text{{font-family:{FONT};font-size:12px}}
@keyframes mv{{to{{transform:translateX(-{period}px)}}}}
.ln{{animation:mv 1.6s linear infinite}}
@keyframes bl{{0%,100%{{opacity:1}}50%{{opacity:.25}}}}
.dot{{animation:bl 1.6s ease-in-out infinite}}
@media (prefers-reduced-motion:reduce){{.ln,.dot{{animation:none}}}}
</style>
<defs>
<linearGradient id="fade" x1="0" x2="1">
<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".12" stop-color="#fff" stop-opacity="1"/>
<stop offset=".88" stop-color="#fff" stop-opacity="1"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
</linearGradient>
<mask id="m"><rect width="{w}" height="{h}" fill="url(#fade)"/></mask>
<pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
<path d="M20 0H0V20" fill="none" stroke="#1a1a1a" stroke-width="1"/>
</pattern>
</defs>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
<g mask="url(#m)">
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" fill="url(#grid)"/>
<g class="ln"><path d="{d}" fill="none" stroke="{FG}" stroke-width="1.6" stroke-linejoin="round"/></g>
</g>
<circle class="dot" cx="{w - 130}" cy="17" r="3.5" fill="{FG}"/>
<text x="{w - 18}" y="21" text-anchor="end" fill="{DIM}">all systems up</text>
<text x="18" y="21" fill="{FAINT}">$ watch -n1 heartbeat</text>
</svg>
'''
    path.write_text(svg)
    print(f"wrote {path.name}: {w}x{h}")


pulse(OUT / "pulse.svg")
