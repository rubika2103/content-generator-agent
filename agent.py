#!/usr/bin/env python3
"""Qualesce Blog Poster Agent — generates 1024x1536 PNG posters using Groq"""

import os, json, base64, re, subprocess, tempfile, zipfile, time
import xml.etree.ElementTree as ET
from pathlib import Path
from flask import Flask, request, jsonify, Response
import queue, threading
import httpx

DIR = Path(__file__).parent
ASSETS = DIR / 'assets'
TRACKER = DIR / 'style_tracker.json'

_public = DIR / 'public'
app = Flask(__name__, static_folder=str(_public) if _public.exists() else None, static_url_path='')

# Load logo once at startup
LOGO_B64 = ''
if (ASSETS / 'logo_b64.txt').exists():
    LOGO_B64 = (ASSETS / 'logo_b64.txt').read_text().strip()
    print(f"Logo loaded ({len(LOGO_B64)} chars)")
elif (ASSETS / 'qualesce_logo.jpg').exists():
    LOGO_B64 = base64.b64encode((ASSETS / 'qualesce_logo.jpg').read_bytes()).decode()
    print("Logo loaded from assets/qualesce_logo.jpg")
elif (DIR / 'qualesce_logo.jpg').exists():
    LOGO_B64 = base64.b64encode((DIR / 'qualesce_logo.jpg').read_bytes()).decode()
    print("Logo loaded from qualesce_logo.jpg")
else:
    print("WARNING: No logo file found")

LOGO_URL   = 'LOGO_DATA_URI'   # replaced at render time with base64
ALL_STYLES = list(range(11))
STYLE_NAMES = [
    "Bento Dashboard","Editorial Magazine","Feature Card Matrix","Apple Keynote",
    "Split Showcase","Zig-Zag Storyboard","Executive Report","Floating Tiles",
    "Magazine Cover","Serpentine Timeline","Hexagon Network"
]

_STYLE_SPECS_REMOVED = {
0: """STYLE 0 — REMOVED
Radial glow overlay + dot grid (background-image:radial-gradient). ALL content centered.
Header(96px): logo+category badge centered, border-bottom rgba(255,255,255,0.08).
Hero(240px): title 58px white Georgia, subtitle #7fdfda 17px, tags row.
Stats(100px): 4 frosted chips flex row, bg rgba(255,255,255,0.07), border rgba(255,255,255,0.12).
Problem(120px): italic rgba(255,255,255,0.7) centered, borders top+bottom rgba(255,255,255,0.08).
Highlights(flex:1): 3-col CSS grid of 6 glass cards, bg rgba(255,255,255,0.06), border rgba(255,255,255,0.1), border-radius:14px, centered content.
Quote(130px): italic white 14px, attribution #7fdfda bold, border-top rgba(255,255,255,0.08).
Footer(88px): bg:#0d1e2e, border-top rgba(255,255,255,0.08).""",

1: """STYLE 1 — Editorial Left (Newspaper, Hard Left Alignment)
bg:#f7f9fb. Header(80px): bg:#0d2a3d, logo left 72px, category badge right, padding:0 48px.
Blue rule below header: height:4px width:80px bg:#0096b4 margin:0 0 0 48px.
Title(220px): 64px Georgia left padding:20px 48px 0.
Stats(260px): vertical column — each row display:flex align-items:baseline gap:16px border-bottom:1px solid #e2eaf0, num 36px #0096b4, label 14px dark.
Problem(110px): 14px left padding:0 48px.
Highlights(flex:1): 2-col table rows — LEFT emoji+heading bold, RIGHT body — border-bottom:1px solid #e8eef4, padding:11px 48px. No card boxes.
Quote(120px): left-aligned, decorative mark 40px color:#e2eaf0, then 15px italic text, padding:0 48px.
Footer(86px): bg:#0d2a3d, white CTA text centered.""",

2: """STYLE 2 — Split Hero (Two-Tone Panel)
Hero(360px): display:flex — LEFT 56% white (logo 72px top-left + subtitle 16px + 3 tag pills) / RIGHT 44% bg:#005a8c (category badge top + big emoji 80px centered + 2 stat items white text).
Full-width title(180px): 54px Georgia left padding:18px 44px 0.
Remaining 2 stats(88px): bg:#f0f4f8 display:flex, vertical dividers.
Problem(110px): padding:0 44px.
Highlights(flex:1): alternating rows bg:#f0f4f8/#fff, icon emoji left 22px, heading+body right, padding:11px 44px.
Quote(110px): right-aligned, border-right:3px solid #7fdfda, padding:14px 48px 14px 120px.
Footer(88px): bg:#0d2a3d.""",

3: """STYLE 3 — Typographic Giant (Type as Design)
White bg. Absolute top strip: height:5px bg:#20b2aa.
Header(72px): logo top-left 72px, category plain text top-right, padding:0 40px.
Title(240px): 76px Georgia line-height:0.93 padding:14px 40px.
Subtitle(50px): right-aligned 16px color:#4a6a80 padding-right:40px.
Stats(88px): 4-col flex, each border-right:1px solid #e2eaf0 padding:10px text-align:center, num 32px #0096b4 bold, label 12px.
Problem(110px): 14px padding:0 40px.
Highlights(flex:1): numbered 01–06, NO emojis — display:flex gap:16px border-bottom:1px solid #eef2f6 padding:11px 40px — num 10px bold #0096b4, heading 13px bold dark, body 12px gray.
Quote(130px): 21px italic centered padding:18px 60px, attribution border-bottom:3px solid #0096b4 display:inline-block.
Footer(86px): bg:#fff border-top:4px solid #0096b4, dark CTA text.""",

4: """STYLE 4 — Color Bands (7 Horizontal Bands = 1536px)
Band1(82px): bg:#0d2a3d — logo left 72px, category badge right, padding:0 44px.
Band2(200px): bg:#fff padding:22px 44px — title 52px Georgia, subtitle 15px.
Band3(90px): bg:linear-gradient(90deg,#0096b4,#20b2aa) — 4 stats white text flex row, rgba(255,255,255,0.3) pipe dividers.
Band4(110px): bg:#f0f4f8 border-left:4px solid #e8900a padding:16px 44px — problem text.
Band5(flex:1, min 460px): bg:#fff — section label + 3×2 TABLE GRID with border:1px solid #e2eaf0 cell borders, emoji center top each cell, heading+body centered.
Band6(120px): bg:#0d2a3d — quote white italic centered, attribution #7fdfda.
Band7(82px): bg:linear-gradient(90deg,#005a8c,#0096b4) — CTA centered white.""",

5: """STYLE 5 — Diagonal Slash (Z-Pattern Flow)
bg:#f7f9fb. Diagonal slash: position:absolute top:0 right:0 width:100% height:500px clip-path:polygon(58% 0,100% 0,100% 100%,74% 100%) bg:linear-gradient(155deg,#0096b4,#005a8c) z-index:1.
Logo: position:relative z-index:3 padding:28px 0 0 48px height:72px.
Title: position:relative z-index:3 font-size:56px color:#0d2a3d padding:10px 0 8px 48px max-width:600px.
Stats: 2×2 dark box LEFT — bg:#0d2a3d border-radius:14px display:grid grid-template-columns:1fr 1fr max-width:460px margin:0 0 0 48px padding:18px 22px — nums #7fdfda 28px bold.
Problem: right-aligned border-right:4px solid #e8900a text-align:right padding:14px 48px 14px 120px bg:#fff9f5.
Highlights(flex:1): 2-col grid padding:0 44px — circle icon bg alternating, white card bg border-radius:12px box-shadow.
Quote: full-width centered gradient card.""",

6: """STYLE 6 — Magazine Cover (Dark Clip Hero)
Hero(400px): position:relative bg:linear-gradient(160deg,#0d2a3d,#005a8c,#0096b4) clip-path:polygon(0 0,100% 0,100% 88%,0 100%).
Logo: position:absolute top:24px left:44px height:72px z-index:2.
Badge: position:absolute top:24px right:44px.
Big emoji: position:absolute top:50% left:50% transform:translate(-50%,-65%) font-size:96px.
Title: position:absolute bottom:-18px left:44px font-size:52px color:#fff text-shadow:0 4px 24px rgba(0,0,0,0.5) max-width:860px line-height:1.05 z-index:3.
Stat chips(96px): 4 chips flex row, each border-top:3px solid cycling #0096b4/#20b2aa/#e8900a/#005a8c, padding:14px text-align:center.
Problem(110px): padding:0 44px.
Highlights(flex:1): 2-col grid, each card border-top:3px solid accent border-radius:12px box-shadow padding:16px.
Quote(116px): italic centered.
Footer(88px): bg gradient.""",

7: """STYLE 7 — Right Rail (Dashboard Layout)
Root: display:flex flex-direction:column height:1536px.
Inner flex row (flex:1): LEFT 68% bg:#f7f9fb padding:28px 28px 0 — title 48px + subtitle + border-bottom #0096b4 + problem orange left-border + section label + 6 highlights vertical list with border-bottom + quote italic.
RIGHT 32% bg:linear-gradient(180deg,#0d2a3d,#005a8c) padding:28px 20px — logo 72px white + category badge + big emoji 72px + 4 vertical stats white text #7fdfda nums + tag pills + quote-by italic bottom.
Footer: flex-shrink:0 height:88px bg:linear-gradient(90deg,#005a8c,#0096b4) full-width CTA centered.""",

8: """STYLE 8 — Brutalist Grid (Bold Borders)
White bg. Outer frame: position:absolute inset:14px border:3px solid #0d2a3d pointer-events:none z-index:10.
Header(88px): bg:#0d2a3d, logo white/light 72px padding:0 44px.
Title(220px): 68px Georgia line-height:0.92 padding:20px 44px.
Accent stripe(10px): height:8px bg:linear-gradient(90deg,#0096b4,#20b2aa,#e8900a) margin:12px 44px.
Stats(110px): display:grid grid-template-columns:repeat(4,1fr) margin:0 44px — each cell border:2px solid #0d2a3d margin:-1px shared borders, num #0096b4 28px bold.
Problem(110px): bg:#0d2a3d color:#f0f4f8 padding:16px 44px inverted.
Highlights(flex:1): 2-col grid margin:0 44px — sharp border-radius:0 border:2px solid #e2eaf0, left accent border-left:4px alternating #0096b4/#20b2aa.
Quote(120px): padding:16px 44px, attribution border-bottom:3px solid #e8900a display:inline-block.
Footer(88px): bg:#0d2a3d.""",

9: """STYLE 9 — Soft Gradient Cards (Friendly SaaS)
bg:linear-gradient(160deg,#f0f8ff,#e8f4f0,#f0f4f8). Root: padding:14px 14px 0 display:flex flex-direction:column gap:10px.
ALL sections are white rounded cards border-radius:18-22px box-shadow:0 4px 20px rgba(0,90,140,0.08) padding inside.
Header card(96px): logo centered + category badge.
Hero card(230px): bg:linear-gradient(135deg,#005a8c,#0096b4) border-radius:22px — title white 52px, subtitle rgba white.
4 individual stat cards flex row gap:10px(96px total): each border-radius:16px box-shadow.
Problem card(110px).
Highlights(flex:1): 2-col grid of white rounded cards.
Quote card(120px).
Footer card: bg:linear-gradient(135deg,#005a8c,#0096b4) border-radius:20px 20px 0 0.""",

10: """STYLE 10 — Timeline Flow (Step-by-Step)
White bg. Top strip: height:5px bg:solid #0096b4 flex-shrink:0.
Header(80px): logo left, category right, clean minimal padding:0 44px.
Title(200px): 52px Georgia padding:20px 44px.
Subtitle(50px): 16px padding:0 44px.
Stats banner(88px): bg:#0d2a3d padding:16px 44px flex row — white text, rgba(255,255,255,0.3) pipe dividers.
Problem(110px): padding:14px 44px.
Timeline(flex:1): 6 items, each display:flex gap:16px padding:8px 44px align-items:flex-start — LEFT: circle 40px border:2px solid #0096b4 border-radius:50% centered number + connector line 2px bg:#e2eaf0 height:22px margin:0 auto — RIGHT: heading bold 13px + body 12px gray.
Quote(120px): centered 15px italic between decorative "— — —" lines.
Footer(88px): bg:#fff border-top:3px solid #0096b4 dark CTA text.""",

11: """STYLE 11 — Dark Sidebar (Enterprise Dashboard)
Root: display:flex flex-direction:column height:1536px.
Inner flex row (flex:1):
LEFT sidebar 230px bg:#0d2a3d padding:24px 16px — logo 72px, thin divider rgba(255,255,255,0.1), teal category badge, big emoji 64px, 4 stats #7fdfda nums white labels thin dividers, tag pills, quote-by italic absolute bottom.
RIGHT main flex:1 bg:#f7f9fb padding:26px 28px — title 46px + subtitle + border-bottom:2px solid #0096b4 + problem border-left:3px solid #e8900a + section label + 2-col compact card grid (border-radius:10px box-shadow) + raw italic quote.
Footer: flex-shrink:0 height:88px bg:linear-gradient(90deg,#005a8c,#0096b4) full-width CTA.""",

12: """STYLE 12 — Glassmorphism (Frosted Glass)
bg:#1a0033 with radial glow rgba(107,33,168,0.3). ALL sections: backdrop-filter:blur(10px) bg:rgba(107,33,168,0.08) border:1px solid rgba(255,255,255,0.3) border-radius:20px box-shadow:0 8px 32px rgba(0,0,0,0.1) padding inside.
Cyan #06b6d4 accents. Dark violet #1a0033 text on light areas, white on dark.
Header glass card(96px): logo + category badge centered.
Hero glass(230px): title 52px, subtitle.
Stats glass row(96px): 4 glass chips.
Problem glass(110px).
Highlights(flex:1): 2-col glass grid, icons in small glass circles.
Quote glass(110px): cyan italic text centered.
Footer glass(88px): cyan CTA.""",

13: """STYLE 13 — Bento Grid (Modular Playful)
bg:#fff7ed. Root: display:flex flex-direction:column height:1536px.
Header(80px): bg:#fff7ed logo left, badge right padding:0 20px.
Middle(flex:1): display:grid grid-template-columns:repeat(4,1fr) gap:12px padding:0 16px — burnt orange #ea580c palette.
  Title cell: grid-column:span 2 grid-row:span 2 bg:#7c2d12 color:#fff padding:20px border-radius:12px — title 40px.
  Subtitle cell: grid-column:span 2 bg:#fef3c7 padding:16px border-radius:12px.
  4 stat cells: each bg:#fff7ed border:1px solid #fed7aa border-radius:10px padding:12px text-align:center.
  Problem cell: grid-column:span 2 bg:#ea580c color:#fff padding:16px border-radius:12px.
  6 highlight cells: vary in span, bg alternating #fff7ed/white, border #fed7aa border-radius:10px padding:12px.
  Quote cell: grid-column:span 2 bg:#fef3c7 border:2px solid #ea580c border-radius:12px padding:16px italic.
Footer(88px): bg:#ea580c color:#fff CTA centered.""",

14: """STYLE 14 — Dashboard Style (Dark Analytics)
bg:#0f172a very dark navy. ALL cards: bg:#1e293b border:1px solid #334155 border-radius:8px color:#f1f5f9.
Dark nav header(80px): bg:#1e293b logo + category badge pills padding:0 24px flex align-items:center gap:16px.
Main area(flex:1): display:flex gap:16px padding:16px.
LEFT 65%: hero metrics row (4 large num boxes alternating #0ea5e9/#10b981/#e8900a/#20b2aa bg) + title 40px + subtitle + problem card + 2-col highlight card grid.
RIGHT 35%: stats sidebar cards + quote insight card left-border:3px solid #20b2aa.
Footer(88px): bg:#1e293b border-top:1px solid #334155 CTA #f1f5f9.""",

15: """STYLE 15 — Infographic Split Screen (Dual Narrative)
Root: display:flex flex-direction:column height:1536px.
Split(flex:1): display:flex.
LEFT 50%: bg:linear-gradient(135deg,#fef2f2,#fca5a5) padding:24px — logo top + category red badge + first half of title + 2 stats red accents + problem red left-border + 3 highlights red theme.
RIGHT 50%: bg:linear-gradient(135deg,#f5f3ff,#e9d5ff) padding:24px — second half of title + 2 stats purple + 3 highlights purple theme.
Quote(90px): full-width bg:linear-gradient(90deg,#be123c,#7c3aed) color:#fff italic centered padding:16px 60px.
Footer(88px): bg:linear-gradient(90deg,#9f1239,#6d28d9) color:#fff CTA.""",

16: """STYLE 16 — Storytelling Flow (Narrative Journey)
bg:linear-gradient(180deg,#fef2f2,#fff5ee,#fef2f2). Left edge stripe: position:absolute left:0 top:0 bottom:0 width:4px bg:linear-gradient(180deg,#ea580c,#dc2626).
Header(90px): logo left padding:24px 44px.
Title: 54px color:#ea580c padding:0 44px.
Subtitle: narrative intro 16px padding:0 44px.
Stats(88px): 4 connecting flow items flex row with lines between.
Problem(110px): "The Challenge" label + warm card bg:#fff5ee border:1px solid #fed7aa padding:16px 44px.
Highlights(flex:1): 6 story beats — each display:flex gap:16px padding:10px 44px — left: num 01-06 color:#ea580c bold 12px + connector — right: emoji + heading bold + body.
Quote(110px): cream bg:#fef2f2 border:2px solid #ea580c border-radius:12px margin:0 44px padding:16px italic text centered.
Footer(88px): bg:#ea580c color:#fff "Continue Your Story" CTA.""",

17: """STYLE 17 — LinkedIn Carousel (Professional Social)
bg:#f3f2ef. Top white bar(90px): bg:#fff border-bottom:1px solid #e0e0e0 padding:0 24px — logo left + "1 / 1" slide counter right color:#666.
Main(flex:1): display:flex align-items:flex-start justify-content:center padding:20px 40px.
Centered white card max-width:700px width:100% bg:#fff border-radius:8px box-shadow:0 4px 12px rgba(0,0,0,0.08) padding:28px:
  Logo + category pill row. Title 40px color:#2d2d2d. Subtitle. Stats: 3 chips #0a66c2 style.
  Problem: quote-box bg:#f3f2ef border-left:4px solid #0a66c2 padding:12px 16px.
  3 highlights: checkmark bullet style dark text. Testimonial quote italic attribution.
Footer(88px): bg:#0a66c2 color:#fff CTA "View This Insight →" centered.
Carousel dots: 5 dots centered below footer inside footer area, first dot filled white others outlined.""",

18: """STYLE 18 — Corporate Executive (Premium Elegant)
bg:#f9fafb. Header(96px): bg:#064e3b padding:0 60px flex align-items:center — logo white-tinted + category text color:#d97706 font-size:13px.
Content max-width:820px margin:0 auto padding:0 40px:
  Title(140px): 58px Georgia color:#064e3b text-align:center padding:28px 0 0.
  Subtitle: color:#d97706 font-size:14px letter-spacing:1.5px text-transform:uppercase text-align:center.
  Gold divider: height:1px bg:#d97706 margin:16px 0.
  Stats(100px): 4-col flex row, each text-align:center — num color:#d97706 28px bold Georgia, label 12px #064e3b.
  Gold divider.
  Problem(120px): blockquote indent, border-left:3px solid #d97706 padding:0 0 0 20px italic color:#064e3b.
  Gold divider.
  Highlights(flex:1): 2-col text table no boxes — LEFT emoji+heading 13px bold #064e3b, RIGHT body 12px #4a6a80 — border-bottom:1px solid #d1fae5 padding:10px 0.
  Quote(130px): large 22px Georgia italic centered color:#064e3b, gold decorative mark top, attribution 11px small-caps color:#d97706.
Footer(88px): removed."""
}

GROQ_MODEL        = 'llama-3.3-70b-versatile'
GROQ_MODEL_FAST   = 'llama-3.1-8b-instant'
EDGE_EXE          = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

# ── helpers ──────────────────────────────────────────────────────────────────

def _e(s):
    return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def _stats_row(stats, num_color, label_color, divider='rgba(0,0,0,0.08)', bg='transparent'):
    parts = []
    for i, s in enumerate(stats[:4]):
        br = f'border-right:1px solid {divider};' if i < 3 else ''
        parts.append(
            f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;{br}background:{bg}">'
            f'<div style="font-size:28px;font-weight:800;color:{num_color};font-family:Georgia,serif;line-height:1">{_e(s["num"])}</div>'
            f'<div style="font-size:11px;color:{label_color};text-align:center;margin-top:5px;line-height:1.3;padding:0 6px">{_e(s["label"])}</div>'
            f'</div>'
        )
    return ''.join(parts)

def _tags_row(tags, bg, color, border='transparent'):
    return ''.join(
        f'<span style="background:{bg};border:1px solid {border};color:{color};font-size:11px;'
        f'font-weight:600;letter-spacing:0.5px;padding:5px 14px;border-radius:20px">{_e(t)}</span>'
        for t in tags[:3]
    )

def _footer(bg, text_color, sub_color):
    return (
        f'<div style="height:66px;background:{bg};display:flex;flex-direction:column;'
        f'align-items:center;justify-content:center;flex-shrink:0">'
        f'<div style="font-size:13px;font-weight:700;color:{text_color}">Ready to Transform Your Business?</div>'
        f'<div style="font-size:11px;color:{sub_color};margin-top:3px">www.qualesce.com</div>'
        f'</div>'
    )

def _html_wrap(body: str) -> str:
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<style>*{margin:0;padding:0;box-sizing:border-box}'
        'body{width:1024px;height:1536px;overflow:hidden;font-family:"Liberation Sans","DejaVu Sans",Arial,"Segoe UI",sans-serif}'
        '</style></head><body>' + body + '</body></html>'
    )

# ── Highlight layout helpers ───────────────────────────────────────────────────

def _hl_card_grid(highlights, cols, bg_card, border, accents, head_color, body_color, section_bg='transparent', label_color='#0096b4'):
    """3×2 or 2×3 card grid — full block content in cards."""
    rows = 6 // cols
    cards = ''
    for i, hl in enumerate(highlights[:6]):
        ac = accents[i % len(accents)]
        cards += (
            f'<div style="background:{bg_card};border:1px solid {border};border-radius:12px;'
            f'border-top:3px solid {ac};padding:16px 18px;display:flex;flex-direction:column;overflow:hidden;position:relative">'
            f'<div style="position:absolute;top:8px;right:12px;font-size:32px;font-weight:900;'
            f'color:{ac};opacity:0.12;font-family:Georgia,serif;line-height:1">0{i+1}</div>'
            f'<div style="font-size:14px;font-weight:700;color:{head_color};line-height:1.35;margin-bottom:8px">{_e(hl["heading"])}</div>'
            f'<div style="font-size:12px;color:{body_color};line-height:1.6;overflow-wrap:break-word;flex:1">{_e(hl["body"])}</div>'
            f'</div>'
        )
    return (
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;padding:10px 36px 14px;background:{section_bg}">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:2.5px;color:{label_color};text-transform:uppercase;margin-bottom:10px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:grid;grid-template-columns:repeat({cols},1fr);grid-template-rows:repeat({rows},1fr);gap:10px">'
        f'{cards}</div></div>'
    )

def _hl_full_blocks(highlights, bg_odd, bg_even, accent, head_color, body_color, label_color='#0096b4'):
    """Full-width alternating content blocks — each highlight is a prominent section."""
    items = ''
    for i, hl in enumerate(highlights[:6]):
        bg = bg_odd if i % 2 == 0 else bg_even
        items += (
            f'<div style="flex:1;display:flex;align-items:center;gap:18px;padding:0 48px;background:{bg};'
            f'border-bottom:1px solid rgba(0,0,0,0.05);min-height:0">'
            f'<div style="font-size:38px;font-weight:900;color:{accent};font-family:Georgia,serif;'
            f'opacity:0.18;min-width:48px;text-align:right;flex-shrink:0;line-height:1">0{i+1}</div>'
            f'<div style="width:3px;align-self:stretch;background:{accent};opacity:0.4;flex-shrink:0;margin:14px 0"></div>'
            f'<div style="min-width:0;flex:1">'
            f'<div style="font-size:15px;font-weight:700;color:{head_color};line-height:1.3;margin-bottom:6px">{_e(hl["heading"])}</div>'
            f'<div style="font-size:13px;color:{body_color};line-height:1.65;overflow-wrap:break-word">{_e(hl["body"])}</div>'
            f'</div></div>'
        )
    return (
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:2.5px;color:{label_color};'
        f'text-transform:uppercase;padding:10px 48px 5px;flex-shrink:0;background:{bg_odd}">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{items}</div></div>'
    )

def _hl_two_col(highlights, border, head_color, body_color, accent, bg='transparent', label_color='#0096b4'):
    """2-column layout — 3 highlights left, 3 right side by side."""
    def item(hl, num):
        return (
            f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;'
            f'padding:0 18px;border-bottom:1px solid {border};min-height:0">'
            f'<div style="display:flex;gap:10px;align-items:flex-start">'
            f'<div style="width:26px;height:26px;min-width:26px;border-radius:6px;background:{accent};'
            f'display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;'
            f'color:#fff;margin-top:2px;flex-shrink:0">{num}</div>'
            f'<div style="min-width:0">'
            f'<div style="font-size:13px;font-weight:700;color:{head_color};line-height:1.3;margin-bottom:4px">{_e(hl["heading"])}</div>'
            f'<div style="font-size:11.5px;color:{body_color};line-height:1.55;overflow-wrap:break-word">{_e(hl["body"])}</div>'
            f'</div></div></div>'
        )
    left  = ''.join(item(hl, i+1) for i, hl in enumerate(highlights[:3]))
    right = ''.join(item(hl, i+4) for i, hl in enumerate(highlights[3:6]))
    return (
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;background:{bg}">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:2.5px;color:{label_color};'
        f'text-transform:uppercase;padding:10px 18px 5px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;min-height:0;border-top:1px solid {border}">'
        f'<div style="flex:1;display:flex;flex-direction:column;border-right:1px solid {border}">{left}</div>'
        f'<div style="flex:1;display:flex;flex-direction:column">{right}</div>'
        f'</div></div>'
    )

# ── Corporate flat-design helpers ─────────────────────────────────────────────

def _logo(h=88):
    return f'<img src="{LOGO_URL}" style="height:{h}px;object-fit:contain;display:block">'

def _cat_badge(txt, bg, color, border):
    return (f'<span style="background:{bg};border:1px solid {border};color:{color};'
            f'font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;'
            f'padding:6px 16px;border-radius:4px">{_e(txt)}</span>')

def _stat_block(stats, num_color, label_color, sep='rgba(255,255,255,0.15)', bg='transparent'):
    parts = []
    for i, s in enumerate(stats[:4]):
        br = f'border-right:1px solid {sep};' if i < 3 else ''
        parts.append(
            f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;{br}background:{bg}">'
            f'<div style="font-size:30px;font-weight:900;color:{num_color};font-family:Georgia,serif;line-height:1">{_e(s["num"])}</div>'
            f'<div style="font-size:11px;color:{label_color};text-align:center;margin-top:5px;padding:0 8px;line-height:1.35">{_e(s["label"])}</div>'
            f'</div>'
        )
    return ''.join(parts)

def _quote_block(quote, quote_by, bg, text_color, attr_color, border_color=None):
    border = f'border-left:4px solid {border_color};padding-left:20px;' if border_color else 'text-align:center;'
    return (
        f'<div style="height:112px;display:flex;align-items:center;padding:0 52px;background:{bg};flex-shrink:0">'
        f'<div style="{border}min-width:0">'
        f'<div style="font-size:14px;font-style:italic;color:{text_color};line-height:1.6;margin-bottom:6px;word-break:break-word">"{_e(quote)}"</div>'
        f'<div style="font-size:12px;font-weight:700;color:{attr_color}">— {_e(quote_by)}</div>'
        f'</div></div>'
    )

# ── Unique highlight layouts (one per style) ──────────────────────────────────

def _hl_mag_list(highlights, bg='#f8fafc', num_color='#0096b4', head_color='#0d2a3d', body_color='#4a6080', border='#dde8f0'):
    """Style 1 — Magazine list: big left number, heading+body on right."""
    rows = ''
    for i, hl in enumerate(highlights[:6]):
        rows += (
            f'<div style="flex:1;display:flex;align-items:stretch;border-bottom:1px solid {border};min-height:0">'
            f'<div style="width:68px;min-width:68px;display:flex;align-items:center;justify-content:center;'
            f'font-size:36px;font-weight:900;color:{num_color};font-family:Georgia,serif;opacity:0.25;line-height:1;flex-shrink:0">{i+1:02d}</div>'
            f'<div style="flex:1;padding:10px 18px 10px 0;border-left:1px solid {border};display:flex;flex-direction:column;justify-content:center;min-width:0">'
            f'<div style="font-size:13px;font-weight:700;color:{head_color};line-height:1.3;margin-bottom:4px">{_e(hl["heading"])}</div>'
            f'<div style="font-size:11.5px;color:{body_color};line-height:1.55;overflow-wrap:break-word">{_e(hl["body"])}</div>'
            f'</div></div>'
        )
    return (
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;background:{bg}">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:{num_color};text-transform:uppercase;padding:8px 18px 4px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{rows}</div></div>'
    )

def _hl_h_bands(highlights, section_bg, bg_row1, bg_row2, border, head_color, body_color, accents):
    """Style 2 — Horizontal bands: 2 rows × 3 items side by side."""
    def row(items_slice, bg, row_border_b):
        cells = ''
        for j, hl in enumerate(items_slice):
            br = f'border-right:1px solid {border};' if j < 2 else ''
            ac = accents[j % len(accents)]
            cells += (
                f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;'
                f'padding:12px 16px;{br}min-height:0;border-top:3px solid {ac}">'
                f'<div style="font-size:12.5px;font-weight:700;color:{head_color};line-height:1.3;margin-bottom:5px">{_e(hl["heading"])}</div>'
                f'<div style="font-size:11px;color:{body_color};line-height:1.5;overflow-wrap:break-word">{_e(hl["body"])}</div>'
                f'</div>'
            )
        return f'<div style="flex:1;display:flex;background:{bg};{row_border_b}">{cells}</div>'
    r1 = row(highlights[:3], bg_row1, f'border-bottom:1px solid {border};')
    r2 = row(highlights[3:6], bg_row2, '')
    return (
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;background:{section_bg}">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:#0096b4;text-transform:uppercase;padding:8px 18px 5px;flex-shrink:0;background:{section_bg}">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{r1}{r2}</div></div>'
    )

def _hl_bignum_blocks(highlights, bg_odd, bg_even, accent, head_color, body_color):
    """Style 3 — Full-width blocks with giant faded background number."""
    items = ''
    for i, hl in enumerate(highlights[:6]):
        bg = bg_odd if i % 2 == 0 else bg_even
        items += (
            f'<div style="flex:1;display:flex;align-items:center;padding:0 52px;background:{bg};'
            f'border-bottom:1px solid rgba(0,0,0,0.04);min-height:0;position:relative;overflow:hidden">'
            f'<div style="position:absolute;right:16px;font-size:96px;font-weight:900;color:{accent};'
            f'font-family:Georgia,serif;opacity:0.07;line-height:1;user-select:none">{i+1:02d}</div>'
            f'<div style="width:4px;align-self:stretch;background:{accent};opacity:0.45;flex-shrink:0;margin:12px 0"></div>'
            f'<div style="flex:1;padding:0 18px;min-width:0;position:relative">'
            f'<div style="font-size:15px;font-weight:700;color:{head_color};line-height:1.3;margin-bottom:5px">{_e(hl["heading"])}</div>'
            f'<div style="font-size:12.5px;color:{body_color};line-height:1.6;overflow-wrap:break-word">{_e(hl["body"])}</div>'
            f'</div></div>'
        )
    return (
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:#0096b4;text-transform:uppercase;padding:8px 52px 5px;flex-shrink:0;background:{bg_odd}">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{items}</div></div>'
    )

def _hl_compact_dot(highlights, border, head_color, body_color, accent, bg='transparent', label_color='#0096b4'):
    """Style 4 — Compact dot list: small dot + heading + body, tight rows."""
    items = ''
    for hl in highlights[:6]:
        items += (
            f'<div style="flex:1;display:flex;align-items:center;padding:0 20px;border-bottom:1px solid {border};min-height:0;gap:12px">'
            f'<div style="width:8px;height:8px;min-width:8px;border-radius:50%;background:{accent};flex-shrink:0"></div>'
            f'<div style="min-width:0;flex:1">'
            f'<div style="font-size:12.5px;font-weight:700;color:{head_color};line-height:1.25;margin-bottom:3px">{_e(hl["heading"])}</div>'
            f'<div style="font-size:11px;color:{body_color};line-height:1.5;overflow-wrap:break-word">{_e(hl["body"])}</div>'
            f'</div></div>'
        )
    return (
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;background:{bg}">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2px;color:{label_color};text-transform:uppercase;padding:8px 20px 3px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{items}</div></div>'
    )

def _hl_table_rows(highlights, num_color, head_color, body_color, border, bg_odd, bg_even):
    """Style 5 — Table layout: left number column + right content column."""
    rows = ''
    for i, hl in enumerate(highlights[:6]):
        bg = bg_odd if i % 2 == 0 else bg_even
        rows += (
            f'<div style="flex:1;display:flex;align-items:stretch;background:{bg};border-bottom:1px solid {border};min-height:0">'
            f'<div style="width:54px;min-width:54px;display:flex;align-items:center;justify-content:center;'
            f'font-size:20px;font-weight:900;color:{num_color};font-family:Georgia,serif;border-right:2px solid {border};flex-shrink:0">{i+1:02d}</div>'
            f'<div style="flex:1;padding:10px 18px;display:flex;flex-direction:column;justify-content:center;min-width:0">'
            f'<div style="font-size:13.5px;font-weight:700;color:{head_color};line-height:1.3;margin-bottom:4px">{_e(hl["heading"])}</div>'
            f'<div style="font-size:12px;color:{body_color};line-height:1.55;overflow-wrap:break-word">{_e(hl["body"])}</div>'
            f'</div></div>'
        )
    return (
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:{num_color};text-transform:uppercase;padding:8px 18px 4px;flex-shrink:0;background:{bg_odd}">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{rows}</div></div>'
    )

def _hl_step_boxes(highlights, bg_card, border, head_color, body_color, section_bg='#f4f9fc'):
    """Style 7 — 2×3 step boxes with top-right number badge."""
    accents = ['#0096b4','#20b2aa','#e8900a','#0096b4','#20b2aa','#e8900a']
    cards = ''
    for i, hl in enumerate(highlights[:6]):
        ac = accents[i]
        cards += (
            f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:14px 16px;'
            f'background:{bg_card};border:1px solid {border};border-top:3px solid {ac};'
            f'position:relative;overflow:hidden;min-height:0">'
            f'<div style="position:absolute;top:6px;right:10px;font-size:24px;font-weight:900;'
            f'color:{ac};font-family:Georgia,serif;opacity:0.18;line-height:1">{i+1:02d}</div>'
            f'<div style="font-size:13px;font-weight:700;color:{head_color};line-height:1.3;margin-bottom:5px">{_e(hl["heading"])}</div>'
            f'<div style="font-size:11.5px;color:{body_color};line-height:1.55;overflow-wrap:break-word">{_e(hl["body"])}</div>'
            f'</div>'
        )
    return (
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;padding:10px 36px 12px;background:{section_bg}">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:#0096b4;text-transform:uppercase;margin-bottom:8px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:repeat(3,1fr);gap:8px">{cards}</div></div>'
    )

def _hl_diag_2col(highlights, bg, border, head_color, body_color, accents):
    """Style 10 — 2-col with accent-colored heading strip above each item."""
    left  = highlights[:3]
    right = highlights[3:6]
    def item(hl, num, ac):
        return (
            f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;border-bottom:1px solid {border};overflow:hidden">'
            f'<div style="height:3px;background:{ac}"></div>'
            f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:8px 16px">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
            f'<span style="font-size:10px;font-weight:900;color:{ac};font-family:Georgia,serif;opacity:0.6">{num:02d}</span>'
            f'<span style="font-size:13px;font-weight:700;color:{head_color};line-height:1.3">{_e(hl["heading"])}</span></div>'
            f'<div style="font-size:11.5px;color:{body_color};line-height:1.5;overflow-wrap:break-word">{_e(hl["body"])}</div>'
            f'</div></div>'
        )
    l = ''.join(item(hl, i+1, accents[i]) for i, hl in enumerate(left))
    r = ''.join(item(hl, i+4, accents[i+3]) for i, hl in enumerate(right))
    return (
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;background:{bg}">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:#0096b4;text-transform:uppercase;padding:8px 18px 4px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;min-height:0;border-top:1px solid {border}">'
        f'<div style="flex:1;display:flex;flex-direction:column;border-right:1px solid {border}">{l}</div>'
        f'<div style="flex:1;display:flex;flex-direction:column">{r}</div>'
        f'</div></div>'
    )

# ── 31 templates ───────────────────────────────────────────────────────────────
# Shared mini-helpers
_N='#0d2a3d';_B='#005a8c';_T='#0096b4';_L='#20b2aa';_A='#7fdfda';_O='#e8900a'
_AC=[_T,_L,_O,_A,_T,_L]
def _hdr(c,logo_h=88,bg='#0d2a3d',badge_bg='rgba(0,150,180,0.2)',badge_col='#7fdfda',badge_brd='rgba(0,150,180,0.5)'):
    return (f'<div style="height:92px;display:flex;align-items:center;justify-content:space-between;padding:0 48px;background:{bg};flex-shrink:0">'
            f'{_logo(logo_h)}{_cat_badge(_e(c["category"]),badge_bg,badge_col,badge_brd)}</div>')
def _hero(c,fs=46,color='#fff',bg='transparent',pad='0 48px',align='flex-start',ta='left'):
    return (f'<div style="height:170px;display:flex;flex-direction:column;justify-content:center;padding:{pad};background:{bg};flex-shrink:0">'
            f'<div style="font-size:{fs}px;font-weight:900;color:{color};font-family:Georgia,serif;line-height:1.0;margin-bottom:10px;word-break:break-word;text-align:{ta}">{_e(c["title"])}</div>'
            f'<div style="font-size:13px;color:{"rgba(255,255,255,0.65)" if color=="#fff" else "#4a6080"};line-height:1.5;word-break:break-word;text-align:{ta}">{_e(c["subtitle"])}</div></div>')
def _sband(c,nc='#7fdfda',lc='rgba(255,255,255,0.6)',bg='#005a8c'):
    return f'<div style="height:80px;display:flex;background:{bg};flex-shrink:0">{_stat_block(c["stats"],nc,lc,"rgba(255,255,255,0.2)",bg)}</div>'
def _prob(c,bdr_col=_O,text_col='rgba(255,255,255,0.65)',bg='transparent',h=82):
    return (f'<div style="height:{h}px;display:flex;align-items:center;padding:0 48px;background:{bg};border-bottom:1px solid rgba(255,255,255,0.08);flex-shrink:0">'
            f'<div style="border-left:4px solid {bdr_col};padding-left:16px;font-size:13px;color:{text_col};line-height:1.65;word-break:break-word">{_e(c["problem"])}</div></div>')
def _qt(c,bg='#0d2a3d',tc='rgba(255,255,255,0.85)',ac='#7fdfda',h=90):
    return (f'<div style="height:{h}px;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:0 60px;background:{bg};border-top:1px solid rgba(255,255,255,0.1);flex-shrink:0">'
            f'<div style="font-size:13px;font-style:italic;color:{tc};text-align:center;line-height:1.6;margin-bottom:5px;word-break:break-word">"{_e(c["quote"])}"</div>'
            f'<div style="font-size:11px;font-weight:700;color:{ac}">— {_e(c["quote_by"])}</div></div>')

def _t00(c):
    """Style 0 — Bento Dashboard · mixed-size CSS grid cells."""
    h=c['highlights'][:6]
    cells=''.join(
        f'<div style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.12);border-radius:10px;border-top:3px solid {_AC[i]};padding:14px;overflow:hidden;position:relative;display:flex;flex-direction:column;justify-content:center">'
        f'<div style="position:absolute;top:6px;right:10px;font-size:26px;font-weight:900;color:{_AC[i]};opacity:0.14;font-family:Georgia,serif">{i+1:02d}</div>'
        f'<div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:5px;line-height:1.3">{_e(h[i]["heading"])}</div>'
        f'<div style="font-size:11px;color:rgba(255,255,255,0.58);line-height:1.5;overflow-wrap:break-word">{_e(h[i]["body"])}</div>'
        f'</div>' for i in range(6)
    )
    stat_chips=''.join(
        f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(255,255,255,0.08);border-radius:8px;margin:10px 6px">'
        f'<div style="font-size:24px;font-weight:900;color:{[_A,_L,_O,_T][i]};font-family:Georgia,serif">{_e(c["stats"][i]["num"])}</div>'
        f'<div style="font-size:10px;color:rgba(255,255,255,0.5);text-align:center;margin-top:3px;padding:0 4px">{_e(c["stats"][i]["label"])}</div></div>'
        for i in range(4)
    )
    body=(
        f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;background:#071524;overflow:hidden">'
        f'<div style="height:12px;background:linear-gradient(90deg,{_T},{_L},{_A});flex-shrink:0"></div>'
        +_hdr(c)
        +_hero(c,fs=42,color='#fff',bg=_N,pad='0 48px')
        +f'<div style="height:80px;display:flex;padding:0 38px;background:#0a1a2e;flex-shrink:0">{stat_chips}</div>'
        +_prob(c,bdr_col=_O,text_col='rgba(255,255,255,0.65)',bg='#0a1a2e',h=80)
        +f'<div style="height:34px;display:flex;align-items:center;gap:8px;padding:0 48px;background:#071524;flex-shrink:0">{_tags_row(c["tags"],"rgba(0,150,180,0.2)","#7fdfda","rgba(0,150,180,0.4)")}</div>'
        +f'<div style="flex:1;display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,1fr);gap:8px;padding:8px 40px;min-height:0">{cells}</div>'
        +_qt(c)
        +_footer('linear-gradient(90deg,#005a8c,#0096b4)','#fff','rgba(255,255,255,0.8)')
        +f'</div>'
    )
    return _html_wrap(body)

def _t01(c):
    """Style 1 — Editorial Magazine · large headline + 2-col article with sidebar."""
    h=c['highlights'][:6]
    # Left col: 3 items, Right col: 3 items
    def row(hl,num):
        return(f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:10px 0;border-bottom:1px solid #e2eaf2;min-height:0">'
               f'<div style="display:flex;gap:10px;align-items:flex-start">'
               f'<div style="font-size:30px;font-weight:900;color:{_T};font-family:Georgia,serif;opacity:0.22;min-width:36px;line-height:1">{num:02d}</div>'
               f'<div style="min-width:0"><div style="font-size:13px;font-weight:700;color:{_N};margin-bottom:4px">{_e(hl["heading"])}</div>'
               f'<div style="font-size:11.5px;color:#4a6080;line-height:1.5;overflow-wrap:break-word">{_e(hl["body"])}</div></div></div></div>')
    left=''.join(row(h[i],i+1) for i in range(3))
    right=''.join(row(h[i],i+1) for i in range(3,6))
    body=(
        f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;background:#f8fafc;overflow:hidden">'
        f'<div style="height:10px;background:{_N};flex-shrink:0"></div>'
        +_hdr(c,bg=_N)
        +f'<div style="height:5px;width:100%;background:{_T};flex-shrink:0"></div>'
        +f'<div style="height:185px;display:flex;flex-direction:column;justify-content:center;padding:0 52px;background:#fff;flex-shrink:0">'
        f'<div style="font-size:52px;font-weight:900;color:{_N};font-family:Georgia,serif;line-height:1.0;word-break:break-word">{_e(c["title"])}</div>'
        f'<div style="font-size:14px;color:#4a6080;margin-top:10px;line-height:1.5">{_e(c["subtitle"])}</div></div>'
        +f'<div style="height:80px;display:flex;background:#fff;border-top:1px solid #e2eaf2;border-bottom:1px solid #e2eaf2;flex-shrink:0">'
        f'{_stat_block(c["stats"],_T,"#4a6080","#e2eaf2","#fff")}</div>'
        +_prob(c,bdr_col=_O,text_col='#2d3f50',bg='#fff',h=82)
        +f'<div style="flex:1;display:flex;min-height:0;border-top:1px solid #e2eaf2">'
        f'<div style="flex:1;display:flex;flex-direction:column;padding:10px 52px 0 52px;border-right:1px solid #e2eaf2">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2px;color:{_T};text-transform:uppercase;margin-bottom:6px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'{left}</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;padding:10px 52px 0 28px">'
        f'<div style="height:18px;flex-shrink:0"></div>{right}</div></div>'
        +f'<div style="height:90px;display:flex;align-items:center;padding:0 52px;background:#fff;border-top:1px solid #e2eaf2;flex-shrink:0">'
        f'<div style="font-size:40px;color:#e2eaf2;font-family:Georgia,serif;margin-right:16px;line-height:1;flex-shrink:0">"</div>'
        f'<div style="min-width:0"><div style="font-size:13px;font-style:italic;color:#2d3f50;line-height:1.6;margin-bottom:5px;word-break:break-word">{_e(c["quote"])}</div>'
        f'<div style="font-size:11px;font-weight:700;color:{_T}">— {_e(c["quote_by"])}</div></div></div>'
        +_footer(_N,'#fff','#7fdfda')
        +f'</div>'
    )
    return _html_wrap(body)

def _t02(c):
    """Style 2 — Feature Card Matrix · 3×2 cards with icon circles."""
    h=c['highlights'][:6]
    icon_colors=[_T,_L,_O,_A,_T,_O]
    cards=''.join(
        f'<div style="display:flex;flex-direction:column;background:#fff;border-radius:12px;border:1px solid #dde8f0;padding:18px 16px;overflow:hidden">'
        f'<div style="width:40px;height:40px;border-radius:50%;background:{icon_colors[i]};display:flex;align-items:center;justify-content:center;'
        f'font-size:15px;font-weight:900;color:#fff;margin-bottom:12px;flex-shrink:0">{i+1}</div>'
        f'<div style="font-size:13.5px;font-weight:700;color:{_N};margin-bottom:6px;line-height:1.3">{_e(h[i]["heading"])}</div>'
        f'<div style="font-size:11.5px;color:#4a6080;line-height:1.55;flex:1;overflow-wrap:break-word">{_e(h[i]["body"])}</div>'
        f'</div>' for i in range(6)
    )
    body=(
        f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;background:#eef3f8;overflow:hidden">'
        f'<div style="height:10px;background:{_T};flex-shrink:0"></div>'
        +_hdr(c,bg='#fff',badge_bg='#e6f4fb',badge_col=_B,badge_brd=_T)
        +_hero(c,fs=46,color=_N,bg='#fff',pad='0 48px',ta='left')
        +f'<div style="height:80px;display:flex;background:#fff;border-top:1px solid #dde8f0;border-bottom:1px solid #dde8f0;flex-shrink:0">'
        f'{_stat_block(c["stats"],_T,"#4a6080","#dde8f0","#fff")}</div>'
        +_prob(c,bdr_col=_O,text_col='#2d3f50',bg='#fff',h=80)
        +f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;padding:10px 36px 12px">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:{_T};text-transform:uppercase;margin-bottom:10px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,1fr);gap:10px">{cards}</div></div>'
        +_qt(c,bg='#fff',tc='#2d3f50',ac=_T,h=88)
        +_footer(f'linear-gradient(90deg,{_B},{_T})','#fff','rgba(255,255,255,0.8)')
        +f'</div>'
    )
    return _html_wrap(body)

def _t03(c):
    """Style 3 — Apple Keynote · minimal white, stacked full-width feature rows."""
    h=c['highlights'][:6]
    rows=''
    for i,hl in enumerate(h):
        bg='#fff' if i%2==0 else '#f7fafc'
        num_col=_AC[i]
        rows+=(f'<div style="flex:1;display:flex;align-items:center;padding:0 52px;background:{bg};border-bottom:1px solid #e8eef4;min-height:0;gap:24px">'
               f'<div style="font-size:48px;font-weight:900;color:{num_col};font-family:Georgia,serif;opacity:0.2;min-width:56px;text-align:right;flex-shrink:0;line-height:1">{i+1:02d}</div>'
               f'<div style="width:3px;align-self:stretch;background:{num_col};opacity:0.35;flex-shrink:0;margin:14px 0"></div>'
               f'<div style="min-width:0;flex:1">'
               f'<div style="font-size:16px;font-weight:700;color:{_N};line-height:1.3;margin-bottom:5px">{_e(hl["heading"])}</div>'
               f'<div style="font-size:13px;color:#4a6080;line-height:1.6;overflow-wrap:break-word">{_e(hl["body"])}</div>'
               f'</div></div>')
    body=(
        f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;background:#fff;overflow:hidden">'
        f'<div style="height:10px;background:{_T};flex-shrink:0"></div>'
        +_hdr(c,bg='#fff',badge_bg='#e6f4fb',badge_col=_B,badge_brd=_T)
        +f'<div style="height:200px;display:flex;flex-direction:column;justify-content:center;padding:0 52px;background:#fff;border-bottom:3px solid {_T};flex-shrink:0">'
        f'<div style="font-size:58px;font-weight:900;color:{_N};font-family:Georgia,serif;line-height:0.95;word-break:break-word">{_e(c["title"])}</div>'
        f'<div style="font-size:15px;color:#4a6080;margin-top:14px;line-height:1.5">{_e(c["subtitle"])}</div>'
        f'<div style="display:flex;gap:8px;margin-top:12px">{_tags_row(c["tags"],"#e6f4fb",_B,_T)}</div></div>'
        +f'<div style="height:80px;display:flex;background:#f7fafc;border-bottom:1px solid #e8eef4;flex-shrink:0">'
        f'{_stat_block(c["stats"],_T,"#4a6080","#e8eef4","#f7fafc")}</div>'
        +_prob(c,bdr_col=_O,text_col='#2d3f50',bg='#fff',h=82)
        +f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:{_T};text-transform:uppercase;padding:8px 52px 4px;flex-shrink:0;background:#fff">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{rows}</div></div>'
        +_qt(c,bg='#fff',tc='#2d3f50',ac=_T,h=88)
        +_footer(f'linear-gradient(90deg,{_N},{_B})','#fff','rgba(255,255,255,0.75)')
        +f'</div>'
    )
    return _html_wrap(body)

def _t04(c):
    """Style 4 — Split Showcase · 70/30 split with dark benefit panel."""
    h=c['highlights'][:6]
    left_rows=''
    for i,hl in enumerate(h):
        left_rows+=(f'<div style="flex:1;display:flex;align-items:center;gap:14px;padding:0 32px;border-bottom:1px solid #e2eaf2;min-height:0">'
                    f'<div style="width:28px;height:28px;min-width:28px;border-radius:6px;background:{_AC[i]};display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;color:#fff">{i+1}</div>'
                    f'<div style="min-width:0"><div style="font-size:13px;font-weight:700;color:{_N};margin-bottom:3px">{_e(hl["heading"])}</div>'
                    f'<div style="font-size:11.5px;color:#4a6080;line-height:1.5;overflow-wrap:break-word">{_e(hl["body"])}</div></div></div>')
    right_stats=''.join(
        f'<div style="padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.1)">'
        f'<div style="font-size:26px;font-weight:900;color:{[_A,_L,_O,_T][i]};font-family:Georgia,serif;line-height:1">{_e(c["stats"][i]["num"])}</div>'
        f'<div style="font-size:10px;color:rgba(255,255,255,0.55);margin-top:3px;line-height:1.35">{_e(c["stats"][i]["label"])}</div></div>'
        for i in range(4)
    )
    sidebar=(f'<div style="width:300px;min-width:300px;background:{_N};display:flex;flex-direction:column;padding:24px 20px">'
             f'{_logo(80)}<div style="margin:14px 0 20px"><span style="background:rgba(0,150,180,0.2);border:1px solid rgba(0,150,180,0.5);color:{_A};font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:4px 10px;border-radius:4px">{_e(c["category"])}</span></div>'
             f'<div style="font-size:9px;font-weight:700;letter-spacing:2px;color:rgba(255,255,255,0.3);text-transform:uppercase;margin-bottom:10px">METRICS</div>'
             f'{right_stats}<div style="flex:1"></div>'
             f'<div style="font-size:13px;font-style:italic;color:rgba(255,255,255,0.75);line-height:1.6;border-left:3px solid {_T};padding-left:14px;word-break:break-word">"{_e(c["quote"])}"<div style="font-size:11px;font-weight:700;color:{_A};margin-top:6px">— {_e(c["quote_by"])}</div></div></div>')
    main=(f'<div style="flex:1;display:flex;flex-direction:column;background:#f8fafc;min-width:0">'
          f'<div style="height:160px;display:flex;flex-direction:column;justify-content:center;padding:0 36px;border-bottom:3px solid {_T};flex-shrink:0;background:#fff">'
          f'<div style="font-size:40px;font-weight:900;color:{_N};font-family:Georgia,serif;line-height:1.05;word-break:break-word">{_e(c["title"])}</div>'
          f'<div style="font-size:13px;color:#4a6080;margin-top:8px;line-height:1.5">{_e(c["subtitle"])}</div></div>'
          f'<div style="height:80px;display:flex;background:#fff;border-bottom:1px solid #e2eaf2;flex-shrink:0">'
          f'{_stat_block(c["stats"],_T,"#4a6080","#e2eaf2","#fff")}</div>'
          +_prob(c,bdr_col=_O,text_col='#2d3f50',bg='#fff',h=82)
          +f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">'
          f'<div style="font-size:9px;font-weight:700;letter-spacing:2px;color:{_T};text-transform:uppercase;padding:8px 32px 4px;flex-shrink:0">KEY HIGHLIGHTS</div>'
          f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{left_rows}</div></div></div>')
    body=(
        f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;overflow:hidden">'
        f'<div style="height:26px;background:{_B};flex-shrink:0"></div>'
        f'<div style="flex:1;display:flex;min-height:0">{sidebar}{main}</div>'
        +_footer(f'linear-gradient(90deg,{_B},{_T})','#fff','rgba(255,255,255,0.8)')
        +f'</div>'
    )
    return _html_wrap(body)

def _t05(c):
    """Style 5 — Zig-Zag Storyboard · alternating L/R connected blocks."""
    h=c['highlights'][:6]
    items=''
    for i,hl in enumerate(h):
        is_left=i%2==0
        ac=_AC[i]
        arrow=(f'<div style="position:absolute;{"right" if is_left else "left"}:-14px;top:50%;transform:translateY(-50%);'
               f'width:0;height:0;border-top:14px solid transparent;border-bottom:14px solid transparent;'
               f'border-{"left" if is_left else "right"}:14px solid {ac}"></div>')
        items+=(f'<div style="flex:1;display:flex;align-items:center;{"justify-content:flex-start" if is_left else "justify-content:flex-end"};padding:0 48px;min-height:0">'
                f'<div style="width:82%;position:relative;background:{"rgba(255,255,255,0.08)" if True else "#fff"};border:1px solid {ac};border-radius:8px;padding:12px 16px">'
                f'{arrow}'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">'
                f'<div style="width:24px;height:24px;border-radius:50%;background:{ac};display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:900;color:#fff;flex-shrink:0">{i+1}</div>'
                f'<div style="font-size:13px;font-weight:700;color:#fff;line-height:1.3">{_e(hl["heading"])}</div></div>'
                f'<div style="font-size:11.5px;color:rgba(255,255,255,0.6);line-height:1.5;padding-left:34px;overflow-wrap:break-word">{_e(hl["body"])}</div>'
                f'</div></div>')
    body=(
        f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;background:#0a1a2e;overflow:hidden">'
        f'<div style="height:12px;background:linear-gradient(90deg,{_T},{_O});flex-shrink:0"></div>'
        +_hdr(c)
        +_hero(c,fs=44,color='#fff',bg=_N,pad='0 48px')
        +_sband(c)
        +_prob(c,bdr_col=_O,text_col='rgba(255,255,255,0.65)',bg='#071524',h=80)
        +f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:{_T};text-transform:uppercase;padding:8px 48px 4px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{items}</div></div>'
        +_qt(c)
        +_footer(f'linear-gradient(90deg,{_T},{_O})','#fff','rgba(255,255,255,0.8)')
        +f'</div>'
    )
    return _html_wrap(body)

def _t06(c):
    """Style 6 — Executive Report · KPI row + divider sections."""
    h=c['highlights'][:6]
    kpi=''.join(
        f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;background:{"#064e3b" if i<2 else ("#005a8c" if i<3 else "#0d2a3d")};padding:10px 6px">'
        f'<div style="font-size:28px;font-weight:900;color:{["#d97706","#d97706",_A,_L][i]};font-family:Georgia,serif">{_e(c["stats"][i]["num"])}</div>'
        f'<div style="font-size:10px;color:rgba(255,255,255,0.6);text-align:center;margin-top:4px;padding:0 4px">{_e(c["stats"][i]["label"])}</div></div>'
        for i in range(4)
    )
    rows=''
    for i,hl in enumerate(h):
        bg='#fff' if i%2==0 else '#f7faf8'
        rows+=(f'<div style="flex:1;display:flex;align-items:center;padding:0 52px;background:{bg};border-bottom:1px solid #d8ece0;min-height:0;gap:16px">'
               f'<div style="width:32px;height:32px;min-width:32px;background:#064e3b;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:900;color:#d97706">{i+1:02d}</div>'
               f'<div style="min-width:0;flex:1"><div style="font-size:14px;font-weight:700;color:#064e3b;font-family:Georgia,serif;margin-bottom:4px">{_e(hl["heading"])}</div>'
               f'<div style="font-size:12px;color:#3d6b55;line-height:1.6;overflow-wrap:break-word">{_e(hl["body"])}</div></div></div>')
    body=(
        f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;background:#f7faf8;overflow:hidden">'
        f'<div style="height:96px;display:flex;align-items:center;justify-content:space-between;padding:0 52px;background:#064e3b;flex-shrink:0">'
        f'{_logo(88)}<span style="color:#d97706;font-size:12px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase">{_e(c["category"])}</span></div>'
        f'<div style="height:4px;background:linear-gradient(90deg,#d97706,#f59e0b);flex-shrink:0"></div>'
        f'<div style="height:170px;display:flex;flex-direction:column;justify-content:center;padding:0 52px;background:#fff;flex-shrink:0">'
        f'<div style="font-size:44px;font-weight:900;color:#064e3b;font-family:Georgia,serif;line-height:1.0;word-break:break-word">{_e(c["title"])}</div>'
        f'<div style="font-size:13px;color:#d97706;font-weight:600;margin-top:10px;line-height:1.5">{_e(c["subtitle"])}</div></div>'
        f'<div style="height:78px;display:flex;flex-shrink:0">{kpi}</div>'
        f'<div style="height:80px;display:flex;align-items:center;padding:0 52px;background:#fff;border-bottom:1px solid #d8ece0;flex-shrink:0">'
        f'<div style="border-left:5px solid #d97706;padding-left:18px;font-size:13px;font-style:italic;color:#2d4a3e;line-height:1.65;word-break:break-word">{_e(c["problem"])}</div></div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">'
        f'<div style="padding:8px 52px 4px;font-size:9px;font-weight:700;letter-spacing:2.5px;color:#064e3b;text-transform:uppercase;flex-shrink:0;background:#f7faf8">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{rows}</div></div>'
        f'<div style="height:90px;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:0 60px;background:#fff;border-top:1px solid #d8ece0;flex-shrink:0">'
        f'<div style="font-size:13px;font-style:italic;color:#2d4a3e;text-align:center;line-height:1.6;margin-bottom:5px;word-break:break-word">"{_e(c["quote"])}"</div>'
        f'<div style="font-size:11px;font-weight:700;color:#d97706;text-transform:uppercase;letter-spacing:1px">— {_e(c["quote_by"])}</div></div>'
        +_footer('#064e3b','#d97706','rgba(217,119,6,0.7)')
        +f'</div>'
    )
    return _html_wrap(body)

def _t07(c):
    """Style 7 — Floating Tiles · asymmetric grid of varied-size glowing tiles."""
    h=c['highlights'][:6]
    # Row 1: 1 large (col span 2) + 1 medium
    # Row 2: 1 medium + 1 large (col span 2)
    # Row 3: 3 small equal
    tile_sizes=[
        ('1/3','1/2','large'),  # h[0]: spans 2 cols, 2 rows
        ('3/4','1/2','medium'), # h[1]: 1 col, 2 rows
        ('1/2','2/3','medium'), # h[2]: 1 col, 2 rows
        ('2/4','2/3','large'),  # h[3]: spans 2 cols, 2 rows
        ('1/2','3/4','small'),  # h[4]: 1 col, 1 row
        ('2/3','3/4','small'),  # h[5]: 1 col, 1 row
    ]
    tiles=''
    sizes_css=[
        ('grid-column:1/3;grid-row:1/3','large'),
        ('grid-column:3/4;grid-row:1/3','medium'),
        ('grid-column:1/2;grid-row:3/5','medium'),
        ('grid-column:2/4;grid-row:3/5','large'),
        ('grid-column:1/2;grid-row:5/7','small'),
        ('grid-column:2/4;grid-row:5/7','small'),
    ]
    glows=['0 0 24px rgba(0,150,180,0.4)','0 0 20px rgba(32,178,170,0.35)',
           '0 0 24px rgba(232,144,10,0.35)','0 0 24px rgba(127,223,218,0.3)',
           '0 0 20px rgba(0,90,140,0.4)','0 0 20px rgba(0,150,180,0.3)']
    for i,((gcol,sz)) in enumerate(sizes_css):
        ac=_AC[i]
        is_large='large' in sz
        fs_h='15px' if is_large else '13px'
        fs_b='13px' if is_large else '11px'
        tiles+=(f'<div style="{gcol};background:linear-gradient(135deg,rgba(13,42,61,0.95),rgba(10,26,46,0.9));'
                f'border:1px solid {ac};border-radius:14px;border-left:4px solid {ac};'
                f'padding:{"20px" if is_large else "14px"};display:flex;flex-direction:column;justify-content:center;'
                f'box-shadow:{glows[i]};overflow:hidden;position:relative">'
                f'<div style="position:absolute;top:10px;right:14px;font-size:{"36px" if is_large else "26px"};'
                f'font-weight:900;color:{ac};opacity:0.1;font-family:Georgia,serif;line-height:1">{i+1:02d}</div>'
                f'<div style="font-size:{fs_h};font-weight:700;color:#fff;margin-bottom:8px;line-height:1.3;position:relative">{_e(h[i]["heading"])}</div>'
                f'<div style="font-size:{fs_b};color:rgba(255,255,255,0.62);line-height:1.6;overflow-wrap:break-word;position:relative">{_e(h[i]["body"])}</div>'
                f'</div>')
    body=(
        f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;background:linear-gradient(160deg,#050e18,#0a1a2e);overflow:hidden">'
        f'<div style="height:12px;background:linear-gradient(90deg,{_T},{_L},{_O});flex-shrink:0"></div>'
        +_hdr(c)
        +f'<div style="height:170px;display:flex;flex-direction:column;justify-content:center;padding:0 48px;flex-shrink:0">'
        f'<div style="font-size:46px;font-weight:900;color:#fff;font-family:Georgia,serif;line-height:1.0;word-break:break-word">{_e(c["title"])}</div>'
        f'<div style="font-size:13px;color:rgba(255,255,255,0.6);margin-top:10px;line-height:1.5;word-break:break-word">{_e(c["subtitle"])}</div>'
        f'<div style="display:flex;gap:8px;margin-top:10px">{_tags_row(c["tags"],"rgba(0,150,180,0.15)","#7fdfda","rgba(0,150,180,0.4)")}</div></div>'
        +_sband(c)
        +_prob(c,bdr_col=_O,text_col='rgba(255,255,255,0.65)',bg='rgba(0,0,0,0.25)',h=76)
        +f'<div style="flex:1;display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(6,1fr);gap:10px;padding:12px 36px;min-height:0">'
        f'{tiles}</div>'
        +_qt(c)
        +_footer(f'linear-gradient(90deg,{_B},{_T})','#fff','rgba(255,255,255,0.8)')
        +f'</div>'
    )
    return _html_wrap(body)

def _t08(c):
    """Style 8 — Magazine Cover · full-bleed diagonal hero, numbered grid."""
    h=c['highlights'][:6]
    items=''
    for i,hl in enumerate(h):
        col=i%3; border_r=f'border-right:1px solid rgba(255,255,255,0.12);' if col<2 else ''
        border_b=f'border-bottom:1px solid rgba(255,255,255,0.12);' if i<3 else ''
        items+=(f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:14px 16px;{border_r}{border_b}overflow:hidden">'
                f'<div style="font-size:26px;font-weight:900;color:{_AC[i]};font-family:Georgia,serif;opacity:0.6;line-height:1;margin-bottom:6px">{i+1:02d}</div>'
                f'<div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:5px;line-height:1.3">{_e(hl["heading"])}</div>'
                f'<div style="font-size:11px;color:rgba(255,255,255,0.58);line-height:1.5;overflow-wrap:break-word">{_e(hl["body"])}</div>'
                f'</div>')
    body=(
        f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;background:#071524;overflow:hidden">'
        # Diagonal clip hero
        f'<div style="height:550px;position:relative;flex-shrink:0;overflow:hidden">'
        f'<div style="position:absolute;inset:0;background:linear-gradient(135deg,{_N} 0%,{_B} 55%,{_T} 100%)"></div>'
        f'<div style="position:absolute;bottom:0;left:0;right:0;height:90px;background:#071524;clip-path:polygon(0 100%,100% 0,100% 100%)"></div>'
        f'<div style="position:absolute;right:-80px;top:-80px;width:400px;height:400px;border-radius:50%;border:60px solid rgba(255,255,255,0.05)"></div>'
        f'<div style="position:absolute;right:120px;bottom:80px;width:160px;height:160px;border-radius:50%;background:rgba(0,150,180,0.1)"></div>'
        f'<div style="position:relative;height:92px;display:flex;align-items:center;justify-content:space-between;padding:0 52px">'
        f'{_logo(88)}{_cat_badge(_e(c["category"]),"rgba(255,255,255,0.12)","#fff","rgba(255,255,255,0.3)")}</div>'
        f'<div style="position:relative;padding:10px 52px 0">'
        f'<div style="font-size:62px;font-weight:900;color:#fff;font-family:Georgia,serif;line-height:0.95;word-break:break-word">{_e(c["title"])}</div>'
        f'<div style="font-size:14px;color:rgba(255,255,255,0.75);margin-top:14px;line-height:1.5;max-width:780px">{_e(c["subtitle"])}</div>'
        f'<div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">{_tags_row(c["tags"],"rgba(255,255,255,0.12)","#fff","rgba(255,255,255,0.25)")}</div>'
        f'</div></div>'
        +_sband(c,bg=_B)
        +_prob(c,bdr_col=_A,text_col='rgba(255,255,255,0.65)',bg='#0a1a2e',h=80)
        +f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;background:#071524">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:{_T};text-transform:uppercase;padding:8px 20px 4px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,1fr)">{items}</div></div>'
        +_qt(c)
        +_footer(f'linear-gradient(90deg,{_B},{_T})','#fff','rgba(255,255,255,0.75)')
        +f'</div>'
    )
    return _html_wrap(body)

def _t09(c):
    """Style 9 — Serpentine Timeline · S-shaped numbered milestone flow."""
    h=c['highlights'][:6]
    items=''
    for i,hl in enumerate(h):
        is_left=i%2==0
        ac=_AC[i]
        margin_l='0' if is_left else '300px'
        margin_r='300px' if is_left else '0'
        connector=(f'<div style="position:absolute;{"left" if is_left else "right"}:100%;top:50%;'
                   f'width:{"200px" if i<5 else "0"};height:2px;background:rgba(255,255,255,0.15);'
                   f'transform:translateY(-50%);z-index:0"></div>' if i<5 else '')
        items+=(f'<div style="flex:1;position:relative;display:flex;align-items:center;padding:0 40px;min-height:0">'
                f'<div style="margin-left:{margin_l};margin-right:{margin_r};'
                f'background:rgba(255,255,255,0.07);border:1px solid {ac};border-radius:8px;'
                f'padding:12px 16px;position:relative;z-index:1;flex:1">'
                f'{connector}'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:5px">'
                f'<div style="width:28px;height:28px;border-radius:50%;background:{ac};display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;color:#fff;flex-shrink:0">{i+1}</div>'
                f'<div style="font-size:13px;font-weight:700;color:#fff;line-height:1.3">{_e(hl["heading"])}</div></div>'
                f'<div style="font-size:11.5px;color:rgba(255,255,255,0.6);line-height:1.5;padding-left:38px;overflow-wrap:break-word">{_e(hl["body"])}</div>'
                f'</div></div>')
    body=(
        f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;background:#0a1a2e;overflow:hidden">'
        f'<div style="height:12px;background:linear-gradient(90deg,{_T},{_L},{_A});flex-shrink:0"></div>'
        +_hdr(c)
        +_hero(c,fs=44,color='#fff',bg=_N,pad='0 48px')
        +_sband(c)
        +_prob(c,bdr_col=_O,text_col='rgba(255,255,255,0.65)',bg='#071524',h=80)
        +f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:{_T};text-transform:uppercase;padding:8px 40px 4px;flex-shrink:0">KEY HIGHLIGHTS</div>'
        f'<div style="flex:1;display:flex;flex-direction:column;min-height:0">{items}</div></div>'
        +_qt(c)
        +_footer(f'linear-gradient(90deg,{_T},{_L})','#fff','rgba(255,255,255,0.8)')
        +f'</div>'
    )
    return _html_wrap(body)


def _t10(c):
    h=c['highlights'][:6]
    HEX='clip-path:polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)'
    cells=''.join(
        f'<div style="display:flex;flex-direction:column;align-items:center;justify-content:center">'
        f'<div style="{HEX};width:190px;height:190px;background:rgba(255,255,255,0.07);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:30px 18px">'
        f'<div style="font-size:22px;font-weight:900;color:{_AC[i]};font-family:Georgia,serif;line-height:1;margin-bottom:6px">{i+1:02d}</div>'
        f'<div style="font-size:12px;font-weight:700;color:#fff;text-align:center;line-height:1.25;margin-bottom:4px">{_e(h[i]["heading"])}</div>'
        f'<div style="font-size:10px;color:rgba(255,255,255,0.55);text-align:center;line-height:1.4">{_e(h[i]["body"][:55]+"...")}</div>'
        f'</div></div>' for i in range(6))
    body=(f'<div style="display:flex;flex-direction:column;width:1024px;height:1536px;background:#071524;overflow:hidden">'
          f'<div style="height:10px;background:linear-gradient(90deg,{_T},{_L},{_A});flex-shrink:0"></div>'
          +_hdr(c)+_hero(c,fs=42,color="#fff",bg=_N,pad="0 48px")+_sband(c)
          +_prob(c,bdr_col=_O,text_col="rgba(255,255,255,0.65)",bg="#0a1a2e",h=76)
          +f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;padding:10px 36px 14px">'
          f'<div style="font-size:9px;font-weight:700;letter-spacing:2.5px;color:{_T};text-transform:uppercase;margin-bottom:12px;flex-shrink:0">KEY HIGHLIGHTS</div>'
          f'<div style="flex:1;display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,1fr);gap:4px;align-items:center;justify-items:center">{cells}</div></div>'
          +_qt(c)+_footer(f"linear-gradient(90deg,{_B},{_T})","#fff","rgba(255,255,255,0.8)")+f'</div>')
    return _html_wrap(body)

TEMPLATES = [_t00,_t01,_t02,_t03,_t04,_t05,_t06,_t07,_t08,_t09,_t10]

# ── content extraction ────────────────────────────────────────────────────────

def extract_content(raw: str) -> dict:
    """Extract rich structured content as JSON using fast model."""
    system = (
        'You are a marketing content writer. Extract and EXPAND content for a professional poster. '
        'Return ONLY valid JSON — no markdown, no explanation.\n\n'
        'Required JSON structure (follow character limits EXACTLY):\n'
        '{\n'
        '  "title": "compelling title, max 8 words",\n'
        '  "subtitle": "one strong sentence explaining the core value, 15-20 words",\n'
        '  "category": "one of: Customer Story / Product Insight / Use Case / Industry Trend / How-To / Case Study",\n'
        '  "stats": [\n'
        '    {"num": "85%", "label": "Reduction in manual processing time"},\n'
        '    {"num": "3x", "label": "Faster customer onboarding cycle"},\n'
        '    {"num": "60%", "label": "Decrease in operational costs"},\n'
        '    {"num": "99%", "label": "Customer satisfaction rate achieved"}\n'
        '  ],\n'
        '  "problem": "Write 3 full sentences describing the core challenge. Be specific about pain points, business impact, and why existing solutions fail.",\n'
        '  "highlights": [\n'
        '    {"heading": "Short Feature Name", "body": "Write 2 full sentences explaining the benefit and how it works in practice for enterprise teams."},\n'
        '    ... (6 total, each body must be 2 sentences minimum)\n'
        '  ],\n'
        '  "quote": "A specific, impactful testimonial quote with measurable outcome mentioned, 20-30 words",\n'
        '  "quote_by": "First Last, Job Title at Company Name",\n'
        '  "tags": ["Keyword One", "Keyword Two", "Keyword Three"]\n'
        '}\n\n'
        'RULES: Use real details from the input. If data is missing, invent realistic enterprise-grade specifics. '
        'Every highlight body MUST be 2 sentences. The problem field MUST be 3 sentences.'
    )
    raw_json = groq_call(
        model=GROQ_MODEL_FAST,
        max_tokens=1000,
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user',   'content': f'Create poster content for:\n\n{raw[:4500]}'}
        ]
    )
    clean = raw_json.strip()
    if clean.startswith('```'):
        clean = clean.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    try:
        d = json.loads(clean)
    except Exception:
        d = {}

    d.setdefault('title',    'Transforming Business with Intelligent Automation')
    d.setdefault('subtitle', 'Transforming enterprise operations with intelligent AI automation solutions.')
    d.setdefault('category', 'Product Insight')
    d.setdefault('problem',
        'Enterprise teams struggle with disconnected manual processes that slow growth and drain resources. '
        'Without automation, employees spend hours on repetitive tasks instead of strategic work. '
        'This leads to costly errors, delayed delivery, and frustrated customers who expect faster results.')
    d.setdefault('quote',    'Implementing this solution cut our onboarding time in half and increased customer retention by 40%.')
    d.setdefault('quote_by', 'Sarah Mitchell, VP of Operations at TechCorp')
    if not isinstance(d.get('stats'), list) or len(d['stats']) < 4:
        d['stats'] = [
            {'num':'85%', 'label':'Reduction in manual processing time'},
            {'num':'3x',  'label':'Faster customer onboarding cycle'},
            {'num':'60%', 'label':'Decrease in operational costs'},
            {'num':'99%', 'label':'Customer satisfaction rate achieved'},
        ]
    if not isinstance(d.get('highlights'), list) or len(d['highlights']) < 6:
        d['highlights'] = [
            {'heading':'Seamless Integration',  'body':'Connects with your existing tools in under 2 hours. No complex migrations or IT overhead required.'},
            {'heading':'AI-Powered Automation', 'body':'Intelligently handles repetitive workflows without human intervention. Your team focuses on high-value strategic tasks.'},
            {'heading':'Real-time Analytics',   'body':'Live dashboards surface actionable insights the moment data changes. Decision-makers always have a clear picture.'},
            {'heading':'Enterprise Scalability','body':'Handles millions of transactions without performance degradation. Scales from 10 to 10,000 users effortlessly.'},
            {'heading':'Bank-grade Security',   'body':'End-to-end encryption and SOC 2 compliance protect every data point. Full audit trails for regulatory confidence.'},
            {'heading':'24/7 Expert Support',   'body':'Dedicated customer success managers respond within minutes. Proactive monitoring prevents issues before they impact you.'},
        ]
    # Pad to exactly 6 highlights if Groq returned fewer
    fallback_hl = [
        {'heading':'Seamless Integration',    'body':'Connects with existing tools in under 2 hours. No complex migrations or IT overhead required.'},
        {'heading':'AI-Powered Automation',   'body':'Intelligently handles repetitive workflows without human intervention. Teams focus on high-value tasks.'},
        {'heading':'Real-time Analytics',     'body':'Live dashboards surface actionable insights the moment data changes. Decision-makers always have a clear picture.'},
        {'heading':'Enterprise Scalability',  'body':'Handles millions of transactions without performance degradation. Scales from 10 to 10,000 users effortlessly.'},
        {'heading':'Bank-grade Security',     'body':'End-to-end encryption and SOC 2 compliance protect every data point. Full audit trails for regulatory confidence.'},
        {'heading':'24/7 Expert Support',     'body':'Dedicated customer success managers respond within minutes. Proactive monitoring prevents issues before they impact you.'},
    ]
    while len(d['highlights']) < 6:
        d['highlights'].append(fallback_hl[len(d['highlights'])])
    # Ensure each highlight body is rich enough
    for hl in d['highlights']:
        if len(hl.get('body', '').split()) < 8:
            hl['body'] = hl.get('body', '') + ' This drives measurable results across your entire organization.'
    if not isinstance(d.get('tags'), list):
        d['tags'] = ['AI Automation', 'Enterprise', 'ROI']
    d['stats']      = d['stats'][:4]
    d['highlights'] = d['highlights'][:6]
    d['tags']       = d['tags'][:3]
    return d

def render_poster(raw_content: str, style_num: int) -> str:
    """Extract JSON content then render via Python template. Returns HTML string."""
    content = extract_content(raw_content)
    return TEMPLATES[style_num % len(TEMPLATES)](content)

def render_to_png(html: str) -> bytes:
    """Render at 2x for crisp fonts. Uses Edge on Windows, Playwright on Linux/cloud."""
    from PIL import Image
    import io as _io
    html = html.replace('LOGO_DATA_URI', f'data:image/jpeg;base64,{LOGO_B64}')
    with tempfile.TemporaryDirectory() as tmp:
        html_path = os.path.join(tmp, 'poster.html')
        png_path  = os.path.join(tmp, 'poster.png')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)

        if os.path.exists(EDGE_EXE):
            # Windows local — use Edge
            file_url = 'file:///' + html_path.replace('\\', '/')
            subprocess.run([
                EDGE_EXE,
                '--headless', '--disable-gpu', '--no-sandbox', '--disable-web-security',
                '--force-device-scale-factor=2',
                '--window-size=1024,1536',
                f'--screenshot={png_path}',
                file_url
            ], check=True, capture_output=True, timeout=60)
        else:
            # Cloud (Linux) — use Playwright
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch(args=['--no-sandbox','--disable-setuid-sandbox'])
                page = browser.new_page(viewport={'width':1024,'height':1536}, device_scale_factor=2)
                page.goto('file://' + html_path)
                page.wait_for_timeout(1500)
                page.screenshot(path=png_path, clip={'x':0,'y':0,'width':1024,'height':1536})
                browser.close()

        img = Image.open(png_path)
        img = img.resize((1024, 1536), Image.LANCZOS)
        buf = _io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        return buf.getvalue()

def get_api_key():
    cfg = DIR / 'brand_config.json'
    if cfg.exists():
        return json.loads(cfg.read_text()).get('groq_api_key', '')
    try:
        import streamlit as st
        return st.secrets.get('GROQ_API_KEY', '') or os.environ.get('GROQ_API_KEY', '')
    except Exception:
        return os.environ.get('GROQ_API_KEY', '')

def get_next_style():
    try:
        t = json.loads(TRACKER.read_text())
    except:
        t = {'used': [], 'cycle_offset': 0}
    remaining = [s for s in ALL_STYLES if s not in t['used']]
    if not remaining:
        offset = (t.get('cycle_offset', 0) + 5) % 19
        t = {'used': [], 'cycle_offset': offset}
        remaining = ALL_STYLES[offset:] + ALL_STYLES[:offset]
    style = remaining[0]
    t['used'].append(style)
    TRACKER.write_text(json.dumps(t))
    return style

def groq_call(messages: list, max_tokens: int, model: str = None, retries: int = 3) -> str:
    """Call Groq with automatic retry on 429."""
    model = model or GROQ_MODEL
    wait = 15
    for attempt in range(retries):
        resp = httpx.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {get_api_key()}', 'Content-Type': 'application/json'},
            json={'model': model, 'max_tokens': max_tokens, 'messages': messages},
            timeout=120
        )
        if resp.status_code == 429:
            if attempt < retries - 1:
                # honour Retry-After header if present, else back off
                retry_after = int(resp.headers.get('retry-after', wait))
                time.sleep(retry_after)
                wait *= 2
                continue
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content'].strip()
    resp.raise_for_status()


_progress_queues: dict = {}

def push_progress(job_id: str, msg: str):
    q = _progress_queues.get(job_id)
    if q:
        q.put(msg)

@app.route('/progress/<job_id>')
def progress_stream(job_id):
    q = queue.Queue()
    _progress_queues[job_id] = q
    def stream():
        try:
            while True:
                msg = q.get(timeout=120)
                if msg == '__done__':
                    break
                yield f'data: {msg}\n\n'
        except:
            pass
        finally:
            _progress_queues.pop(job_id, None)
    return Response(stream(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@app.route('/logo')
def serve_logo():
    from flask import send_file
    return send_file(str(ASSETS / 'qualesce_logo.jpg'), mimetype='image/jpeg')

@app.route('/')
def index():
    from flask import send_from_directory
    return send_from_directory(str(DIR / 'public'), 'index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json or {}
    source = data.get('source', 'topic')
    raw = data.get('content', '').strip()

    if not raw:
        return jsonify({'error': 'Content is required'}), 400

    # For URL source, fetch the page text
    content = raw
    if source == 'url':
        try:
            import requests as req
            resp = req.get(raw, timeout=12, headers={'User-Agent': 'Mozilla/5.0'})
            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text).strip()
            content = f"URL: {raw}\n\nPage content:\n{text[:6000]}"
        except Exception as e:
            return jsonify({'error': f'Could not fetch URL: {e}'}), 400

    style_num = get_next_style()
    job_id = data.get('job_id', '')
    push_progress(job_id, 'Generating poster design...')

    try:
        html = render_poster(content, style_num)
    except Exception as e:
        return jsonify({'error': f'Groq API error: {e}'}), 500

    push_progress(job_id, 'Rendering image...')
    try:
        png = render_to_png(html)
    except Exception as e:
        return jsonify({'error': f'Render error: {e}'}), 500

    push_progress(job_id, '__done__')
    return jsonify({
        'png': base64.b64encode(png).decode(),
        'style': style_num,
        'style_name': STYLE_NAMES[style_num]
    })

def extract_file_text(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()

    if ext == '.txt':
        return file_bytes.decode('utf-8', errors='ignore')[:5000]

    if ext == '.docx':
        with zipfile.ZipFile(io_bytes(file_bytes)) as z:
            with z.open('word/document.xml') as f:
                tree = ET.parse(f)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        texts = [t.text for t in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text]
        return ' '.join(texts)[:5000]

    if ext == '.pptx':
        texts = []
        with zipfile.ZipFile(io_bytes(file_bytes)) as z:
            slides = sorted([n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml', n)])
            for slide in slides:
                with z.open(slide) as f:
                    tree = ET.parse(f)
                slide_texts = [t.text for t in tree.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t') if t.text]
                texts.extend(slide_texts)
        return ' '.join(texts)[:5000]

    if ext == '.pdf':
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        texts = [page.extract_text() or '' for page in reader.pages]
        text = ' '.join(texts)
        if not text.strip():
            raise ValueError('No extractable text found in this PDF. Try a text-based PDF (not a scanned image).')
        return text[:5000]

    raise ValueError(f'Unsupported file type: {ext}')

def io_bytes(b):
    import io
    return io.BytesIO(b)

@app.route('/generate-file', methods=['POST'])
def generate_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Empty filename'}), 400
    try:
        text = extract_file_text(f.read(), f.filename)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Could not read file: {e}'}), 400

    if not text.strip():
        return jsonify({'error': 'No text could be extracted from the file'}), 400

    job_id = request.form.get('job_id', '')
    style_num = get_next_style()
    push_progress(job_id, 'Extracting content...')
    try:
        html = render_poster(text, style_num)
    except Exception as e:
        return jsonify({'error': f'Groq API error: {e}'}), 500
    push_progress(job_id, 'Rendering image...')
    try:
        png = render_to_png(html)
    except Exception as e:
        return jsonify({'error': f'Render error: {e}'}), 500
    push_progress(job_id, '__done__')

    return jsonify({
        'png': base64.b64encode(png).decode(),
        'style': style_num,
        'style_name': STYLE_NAMES[style_num]
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'model': GROQ_MODEL,
        'logo_loaded': bool(LOGO_B64),
        'styles': len(TEMPLATES)
    })

if __name__ == '__main__':
    print('Qualesce Poster Agent - http://127.0.0.1:8090')
    app.run(host='127.0.0.1', port=8090, debug=False)
