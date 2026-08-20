#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路网指纹：用 Overpass(OSM) 画出城市的路，别的什么都不留。
用法: roadnet.py LAT LON NAME [半径米] [输出png]
"""
import sys, json, io, math, pathlib, urllib.request, urllib.parse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

WIDTHS = {"motorway": 2.2, "trunk": 1.9, "primary": 1.5, "secondary": 1.2,
           "tertiary": 1.0, "residential": 0.7, "unclassified": 0.7, "service": 0.5}


def fetch(lat, lon, radius):
    q = ('[out:json];way(around:%d,%.5f,%.5f)["highway"];out geom;' % (radius, lat, lon))
    mirrors = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]
    last = None
    for base in mirrors:
        try:
            url = base + "?data=" + urllib.parse.quote(q)
            req = urllib.request.Request(url, headers={"User-Agent": "NowhereJourney/1.0 (home)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception as e:
            last = e
            continue
    raise last


def draw(lat, lon, data, out_path, surface="", radius=5000, night_flag=False):
    segs, widths = [], []
    coslat = math.cos(math.radians(lat))
    for e in data.get("elements", []):
        g = e.get("geometry")
        hw = (e.get("tags") or {}).get("highway", "")
        w = WIDTHS.get(hw, 0.45)
        if not g or len(g) < 2:
            continue
        pts = [((p["lon"] - lon) * coslat * 111320.0, (p["lat"] - lat) * 110540.0) for p in g]
        segs.append(pts)
        widths.append(w)
    if not segs:
        # 没有路的地方：先看烟烟画的纹理图，没有再按代码画
        import numpy as _np
        _tex_dir = pathlib.Path(__file__).resolve().parent / "textures"
        _pick = surface
        if surface == "water" and abs(lat) <= 25:
            _pick = "reef"
        if night_flag and abs(lat) >= 58:
            _pick = "aurora"
        _tex = _tex_dir / (_pick + ".jpg")
        if _tex.exists():
            try:
                import shutil as _sh
                _sh.copy(str(_tex), out_path)
                return True
            except Exception:
                pass
        _np.random.seed(abs(hash((round(lat, 2), round(lon, 2)))) % (2**31))
        if surface == "ice":
            _draw_ice_crack(radius, out_path)
            return True
        if surface == "rock":
            _draw_rock_column(radius, out_path)
            return True
        if surface == "salt":
            _draw_salt_hex(radius, out_path)
            return True
        _styles = {
            "water": ("#DDEBF0", "#9FBCC8"),
            "sand": ("#F2E9D5", "#CBB892"),
            "grass": ("#EDF2E2", "#A8BC8C"),
            "snow": ("#F4F7F9", "#C3D2DC"),
        }
        _bg, _line = _styles.get(surface, ("#F2E9D5", "#CBB892"))
        _fig, _ax = plt.subplots(figsize=(6, 6), dpi=160)
        _fig.patch.set_facecolor(_bg)
        _ax.set_facecolor(_bg)
        _x = _np.linspace(-radius, radius, 900)
        for _i in range(26):
            _off = _np.sin(_i * 1.7) * 900
            _y = _x * 0.05 + _off + _np.sin(_x / 700 + _i) * 120
            _ax.plot(_x, _y, color=_line, lw=1.1, alpha=0.55)
        _ax.set_xlim(-radius, radius)
        _ax.set_ylim(-radius, radius)
        _ax.set_aspect("equal")
        _ax.axis("off")
        _fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        _fig.savefig(out_path, facecolor=_fig.get_facecolor())
        plt.close(_fig)
        return True
    fig, ax = plt.subplots(figsize=(6, 6), dpi=200)
    fig.patch.set_facecolor("#F5F0E6")
    ax.set_facecolor("#F5F0E6")
    lc = LineCollection(segs, linewidths=widths, colors="#4A3B2C", alpha=0.85,
                         capstyle="round", joinstyle="round")
    ax.add_collection(lc)
    ax.set_xlim(-radius, radius)
    ax.set_ylim(-radius, radius)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return True

def _draw_ice_crack(radius, out_path):
    import numpy as _np
    _fig, _ax = plt.subplots(figsize=(6, 6), dpi=160)
    _fig.patch.set_facecolor("#E9F3F7")
    _ax.set_facecolor("#E9F3F7")
    for _i in range(60):
        _x0 = _np.random.uniform(-radius, radius)
        _y0 = _np.random.uniform(-radius, radius)
        _ang = _np.random.uniform(0, 2 * _np.pi)
        _seg = _np.random.uniform(300, 1400)
        _x1 = _x0 + _seg * _np.cos(_ang)
        _y1 = _y0 + _seg * _np.sin(_ang)
        _midx = (_x0 + _x1) / 2 + _np.random.uniform(-260, 260)
        _midy = (_y0 + _y1) / 2 + _np.random.uniform(-260, 260)
        _t = _np.linspace(0, 1, 40)
        _cx = (1 - _t)**2 * _x0 + 2 * (1 - _t) * _t * _midx + _t**2 * _x1
        _cy = (1 - _t)**2 * _y0 + 2 * (1 - _t) * _t * _midy + _t**2 * _y1
        _ax.plot(_cx, _cy, color="#7E9BB0", lw=_np.random.uniform(0.8, 1.8), alpha=0.5)
    _ax.set_xlim(-radius, radius)
    _ax.set_ylim(-radius, radius)
    _ax.set_aspect("equal")
    _ax.axis("off")
    _fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    _fig.savefig(out_path, facecolor=_fig.get_facecolor())
    plt.close(_fig)

def _draw_rock_column(radius, out_path):
    import numpy as _np
    _fig, _ax = plt.subplots(figsize=(6, 6), dpi=160)
    _fig.patch.set_facecolor("#4A4A48")
    _ax.set_facecolor("#4A4A48")
    _x = -radius
    while _x < radius:
        _w = _np.random.uniform(120, 420)
        _ax.axvspan(_x, _x + _w, color="#5C5B57", alpha=0.85)
        _ax.plot([_x, _x], [-radius, radius], color="#2F2F2E", lw=1.6)
        _ax.plot([_x + _w, _x + _w], [-radius, radius], color="#8A877E", lw=1.0, alpha=0.8)
        _x += _w
    _ax.set_xlim(-radius, radius)
    _ax.set_ylim(-radius, radius)
    _ax.set_aspect("equal")
    _ax.axis("off")
    _fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    _fig.savefig(out_path, facecolor=_fig.get_facecolor())
    plt.close(_fig)

def _draw_salt_hex(radius, out_path):
    import numpy as _np, math as _m
    _fig, _ax = plt.subplots(figsize=(6, 6), dpi=160)
    _fig.patch.set_facecolor("#F8F5EE")
    _ax.set_facecolor("#F8F5EE")
    _s = 620.0
    _h = _s * _m.sqrt(3) / 2
    _y = -radius
    _row = 0
    while _y < radius + _h:
        _off = (_s / 2) if _row % 2 else 0
        _x = -radius - _s + _off
        while _x < radius + _s:
            _pts = [(_x + _s * _m.cos(_m.radians(60 * i)), _y + _s * _m.sin(_m.radians(60 * i))) for i in range(6)]
            _pts.append(_pts[0])
            _xs, _ys = zip(*_pts)
            _ax.plot(_xs, _ys, color="#D9D2C2", lw=1.1, alpha=0.8)
            _x += _s
        _y += _h
        _row += 1
    _ax.set_xlim(-radius, radius)
    _ax.set_ylim(-radius, radius)
    _ax.set_aspect("equal")
    _ax.axis("off")
    _fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    _fig.savefig(out_path, facecolor=_fig.get_facecolor())
    plt.close(_fig)


if __name__ == "__main__":
    lat = float(sys.argv[1])
    lon = float(sys.argv[2])
    name = sys.argv[3] if len(sys.argv) > 3 else "roadnet"
    radius = int(sys.argv[4]) if len(sys.argv) > 4 else 5000
    out = sys.argv[5] if len(sys.argv) > 5 else "/tmp/%s.png" % name
    surface = sys.argv[6] if len(sys.argv) > 6 else ""
    force_texture = len(sys.argv) > 7 and sys.argv[7] == "force_texture"
    night_flag = len(sys.argv) > 8 and sys.argv[8] == "night"
    try:
        if force_texture:
            ok = draw(lat, lon, {"elements": []}, out, surface, radius, night_flag)
        else:
            data = fetch(lat, lon, radius)
            ok = draw(lat, lon, data, out, surface, radius, night_flag)
        print("OK" if ok else "EMPTY", out)
    except Exception as ex:
        print("ERR", str(ex)[:120])