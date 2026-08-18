#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""随行耳朵 · radio_ear

给乌有乡的旅程配上"走到哪，听哪的电台"：
  locate LAT LON            按坐标找当地电台（国内通讯录优先，否则查 radio-browser 全球黄页）
  catch [STREAM] [SEC] [OUT] 截取电台直播流 SEC 秒，转成 mp3 放进 hear/ 目录
  note TEXT                  把"听见了什么"写进 radio_ear.json（供旅程网页展示）
  status                     打印当前 radio_ear.json

环境变量：
  NOWHERE_HOME  乌有乡数据目录，默认 ~/.nowhere
"""
import json, os, sys, subprocess, urllib.request, math, datetime, pathlib, re

NOWHERE_HOME = pathlib.Path(os.environ.get("NOWHERE_HOME", str(pathlib.Path.home() / ".nowhere")))
HEAR_DIR = NOWHERE_HOME / "hear"
STATE = NOWHERE_HOME / "radio_ear.json"

# 国内通讯录：蜻蜓FM live 编号 → 直播流。往后按城市往里加。
CN_BOOK = [
    {"name": "西湖之声", "city": "杭州", "freq": "FM105.4",
     "lat": 30.25, "lon": 120.15,
     "stream": "http://lhttp.qingting.fm/live/1163/64k.mp3",
     "genre": "城市综合 · 娱乐", "homepage": "https://www.qtfm.cn/radios/1163"},
]


def hav(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _load():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(d):
    HEAR_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def locate(lat, lon):
    """先翻国内通讯录（距离 <= 80km），翻不到再问 radio-browser。"""
    best, bestd = None, 1e9
    for e in CN_BOOK:
        d = hav(lat, lon, e["lat"], e["lon"])
        if d < bestd:
            bestd, best = d, e
    if best is not None and bestd <= 80:
        return {"source": "cn_book", "distance_km": round(bestd, 1),
                "station": best, "lat": lat, "lon": lon, "at": _now()}

    url = ("https://de1.api.radio-browser.info/json/stations/search"
           f"?geo_lat={lat}&geo_lon={lon}&geo_radius=300&hidebroken=true"
           "&limit=10&order=distance")
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            stations = json.loads(r.read().decode("utf-8"))
        if not stations:
            return {"source": "none", "station": None, "lat": lat, "lon": lon, "at": _now()}
        s = stations[0]
        st = {"name": (s.get("name") or "未知电台").strip(),
              "city": s.get("countrycode", "?"),
              "freq": "", "stream": s.get("url_resolved") or s.get("url") or "",
              "genre": (s.get("tags") or "").replace(",", " · "),
              "homepage": s.get("homepage") or ""}
        return {"source": "radio_browser", "distance_km": None,
                "station": st, "lat": lat, "lon": lon, "at": _now()}
    except Exception as e:
        return {"source": "error", "station": None, "lat": lat, "lon": lon,
                "at": _now(), "error": str(e)}


def catch(stream, sec=20, out="ear_now"):
    """ffmpeg 截流 SEC 秒 → hear/out.mp3"""
    HEAR_DIR.mkdir(parents=True, exist_ok=True)
    dst = HEAR_DIR / f"{out}.mp3"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error",
           "-i", stream, "-t", str(sec),
           "-acodec", "libmp3lame", "-ar", "24000", "-b:a", "48k",
           "-y", str(dst)]
    subprocess.run(cmd, timeout=int(sec) + 30, check=False)
    if dst.exists() and dst.stat().st_size > 1000:
        print(f"OK {dst} ({dst.stat().st_size} bytes)")
        return str(dst)
    print(f"FAIL {dst}")
    return ""


def note(text, mp3=""):
    d = _load()
    d["heard"] = {"text": text, "mp3": mp3, "at": _now()}
    _save(d)
    print("已写入 radio_ear.json")


def status():
    d = _load()
    print(json.dumps(d, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] == "status":
        status()
    elif argv[0] == "locate" and len(argv) >= 3:
        d = _load()
        d["located"] = locate(float(argv[1]), float(argv[2]))
        _save(d)
        print(json.dumps(d["located"], ensure_ascii=False, indent=2))
    elif argv[0] == "catch":
        d = _load()
        st = (d.get("located") or {}).get("station") or {}
        a = argv[1:]
        stream, sec, out = st.get("stream", ""), 20, "ear_now"
        if a and not re.fullmatch(r"\d+", a[0]):
            stream = a[0]
            a = a[1:]
        if a:
            sec = int(a[0])
        if len(a) > 1:
            out = a[1]
        if not stream:
            print("没有流地址，先跑 locate")
        else:
            mp3 = catch(stream, sec, out)
            if mp3:
                d["heard"] = {"text": d.get("heard", {}).get("text", ""),
                              "mp3": f"hear/{out}.mp3", "sec": sec, "at": _now()}
                _save(d)
    elif argv[0] == "note" and len(argv) >= 2:
        note(" ".join(argv[1:]), "hear/ear_now.mp3")
    else:
        print(__doc__)
