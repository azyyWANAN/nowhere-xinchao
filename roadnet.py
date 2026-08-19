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
    url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={"User-Agent": "NowhereJourney/1.0 (home)"})
    with urllib.request.urlopen(req, timeout=80) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def draw(lat, lon, data, out_path):
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
        return False
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


if __name__ == "__main__":
    lat = float(sys.argv[1])
    lon = float(sys.argv[2])
    name = sys.argv[3] if len(sys.argv) > 3 else "roadnet"
    radius = int(sys.argv[4]) if len(sys.argv) > 4 else 5000
    out = sys.argv[5] if len(sys.argv) > 5 else "/tmp/%s.png" % name
    try:
        data = fetch(lat, lon, radius)
        ok = draw(lat, lon, data, out)
        print("OK" if ok else "EMPTY", out)
    except Exception as ex:
        print("ERR", str(ex)[:120])
