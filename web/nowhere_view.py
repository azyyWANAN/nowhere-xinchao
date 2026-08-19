#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""乌有乡旅程档案 · 手机网页版"""
import json, html, os, pathlib
from urllib.request import urlopen, Request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import datetime

BASE = pathlib.Path(__file__).resolve().parent
TPL = (BASE / "index.tpl.html").read_text(encoding="utf-8")
NOWHERE_HOME = pathlib.Path(os.environ.get("NOWHERE_HOME", str(pathlib.Path.home() / ".nowhere")))
KEY = os.environ.get("NOWHERE_VIEW_KEY", "0e327405b636c97deebc5ae1")
USER_NAME = os.environ.get("USER_NAME", "烟烟")
PORT = int(os.environ.get("NOWHERE_VIEW_PORT", "18082"))

AMAP_KEY = ""
_km = pathlib.Path(__file__).resolve().parent.parent / "map_keys.env"
if _km.exists():
    for _line in _km.read_text(encoding="utf-8").splitlines():
        if _line.startswith("AMAP_KEY="):
            AMAP_KEY = _line.split("=", 1)[1].strip()
            break

CITY_WORDS = ["市", "区", "镇", "县", "城", "桥", "街", "路", "门", "寺", "塔", "站", "港", "村", "庄", "集"]
KNOWN_CITIES = ["包头", "乌鲁木齐", "重庆", "杭州", "北京", "上海", "广州", "深圳", "成都", "武汉",
                "西安", "南京", "苏州", "天津", "青岛", "长沙", "郑州", "昆明", "哈尔滨", "长春",
                "沈阳", "大连", "宁波", "厦门", "福州", "济南", "石家庄", "太原", "合肥", "南昌",
                "南宁", "贵阳", "兰州", "西宁", "银川", "海口", "大阪", "东京", "京都", "首尔",
                "巴黎", "伦敦", "纽约", "柏林"]

NATURE_WORDS = [("岛", "海岛"), ("屿", "海岛"), ("礁", "礁石"), ("山", "山"), ("峰", "山"), ("岭", "山"),
                ("湖", "湖"), ("海", "海"), ("湾", "海湾"), ("江", "江"), ("河", "河"), ("泉", "泉"),
                ("林", "林地"), ("森", "森林"), ("漠", "沙漠"), ("原", "草原"), ("谷", "山谷"),
                ("泽", "湿地"), ("滩", "滩涂")]

SURFACE_CN = {"sand": "沙", "snow": "积雪", "grass": "草地", "rock": "岩石",
              "forest": "林地", "water": "水面", "soil": "泥土", "ice": "冰面",
              "wetland": "湿地", "urban": "水泥", "gravel": "碎石", "tundra": "苔原"}
BIOME_CN = {"desert": "荒漠", "tundra": "苔原", "forest": "森林", "grassland": "草原",
            "wetland": "湿地", "urban": "城市", "water": "水域"}


def _load(name):
    p = NOWHERE_HOME / name
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _dest_short(place):
    parts = [x for x in place.split() if x][:2]
    short = "".join(parts)
    return short if short else place


def _classify(place):
    """三连问：白名单城市 -> 城市词 -> 自然词 -> 脚下的地。返回(脚下, 标签)。"""
    for w in CITY_WORDS:
        if w in place:
            return "城市", "城市"
    for w, t in NATURE_WORDS:
        if w in place:
            return t, t
    if place in _CN_CITIES:
        return "城市", "城市"
    for c in KNOWN_CITIES:
        if c in place:
            return "城市", "城市"
    if place and place.strip():
        return "小镇", "小镇"
    return None, None


def _osm_tile_map(lat, lon, zoom=13):
    """高德画不到的地方，用 OSM 瓦片拼一张真地图，标上红点。"""
    try:
        from PIL import Image, ImageDraw
        import io, math
        n = 2 ** zoom
        x = (lon + 180.0) / 360.0 * n
        lat_r = math.radians(lat)
        y = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n
        tx, ty = int(x), int(y)
        canvas = Image.new("RGB", (768, 768), (238, 235, 227))
        for dy in range(3):
            for dx in range(3):
                ux, uy = tx + dx - 1, ty + dy - 1
                if ux < 0 or uy < 0 or ux >= n or uy >= n:
                    continue
                url = f"https://tile.openstreetmap.org/{zoom}/{ux}/{uy}.png"
                req = Request(url, headers={"User-Agent": "NowhereJourney/1.0 (home)"})
                data = urlopen(req, timeout=15).read()
                img = Image.open(io.BytesIO(data)).convert("RGB")
                canvas.paste(img, (dx * 256, dy * 256))
        px = int((x - tx + 1) * 256)
        py = int((y - ty + 1) * 256)
        draw = ImageDraw.Draw(canvas)
        r = 9
        draw.ellipse([px - r, py - r, px + r, py + r], outline=(158, 59, 59), width=4)
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return b""


_CN_CITIES = set()
_cp = pathlib.Path(__file__).resolve().parent.parent / "cn_cities.json"
if _cp.exists():
    try:
        _CN_CITIES = set(json.loads(_cp.read_text(encoding="utf-8")).get("cities", []))
    except Exception:
        pass

_LETTERS = {}
_lp = pathlib.Path(__file__).resolve().parent.parent / "love_letters.json"
if _lp.exists():
    try:
        _LETTERS = json.loads(_lp.read_text(encoding="utf-8"))
    except Exception:
        pass


def _pick_city_letter(city):
    pool = _LETTERS.get("city_letters") or []
    if not pool:
        return ""
    idx = sum(ord(ch) for ch in city) % len(pool)
    return pool[idx].replace("{城}", city).replace("{你}", "你")


def _find_roadnet(lat, lon):
    """在路网目录里找离坐标最近的一张图，距离 < 0.15 度算命中。"""
    _d = pathlib.Path("/home/ubuntu/.nowhere/roadnet")
    if not _d.is_dir():
        return None
    best, bestd = None, 1e9
    for _f in _d.glob("*.png"):
        try:
            _la, _lo = _f.stem.split("_")
            _la, _lo = float(_la), float(_lo)
        except Exception:
            continue
        _dd = ((_la - lat) ** 2 + (_lo - lon) ** 2) ** 0.5
        if _dd < bestd:
            bestd, best = _dd, _f
    if best is not None and bestd <= 0.15:
        return best
    return None


def esc(s):
    return html.escape(str(s), quote=True)


def render():
    j = _load("journey.json") or {}
    pcs = _load("postcards.json") or {"items": []}
    lands = _load("landings.json") or {}
    ear = _load("radio_ear.json") or {}

    pos = j.get("pos", [0, 0])
    lat, lon = pos[0], pos[1]
    place = j.get("place_name") or "某处"
    env = (j.get("last_env") or {})
    w = env.get("weather", {})
    t = env.get("terrain", {})
    sky = env.get("sky", {})
    radio = j.get("radio_station") or {}
    ear_st = ear.get("located") or {}
    ear_radio = ear_st.get("station") or {}
    if ear_radio.get("name"):
        radio = {**radio, **{k: v for k, v in ear_radio.items() if v}}
    radio_btn = ""
    if radio.get("name") and radio.get("homepage"):
        radio_btn = ('<div class="radio-btn-row"><a class="radio-btn" href="' + esc(radio["homepage"]) + '" target="_blank">'
                     '<span>打</span><span>开</span><span>电</span><span>台</span></a></div>')
    heard = ear.get("heard") or {}
    _loc = ear.get("located") or {}
    _lla, _llo = _loc.get("lat"), _loc.get("lon")
    _near = False
    if _lla is not None and _llo is not None:
        _near = ((_lla - lat) ** 2 + (_llo - lon) ** 2) ** 0.5 <= 0.5
    if not _near:
        heard = {}
    hear_html = ""
    if heard.get("text"):
        hear_html = (f'<div class="ear"><div class="ear-h">&#128266; 随行耳朵 · 他听见了</div>'
                     f'<p>{esc(heard["text"])}</p><div class="ear-m">{esc(heard.get("at", ""))} · 现场截听 {heard.get("sec", 20)} 秒</div><div class="ear-hint">他在这座城，拧开了本地的台</div></div>')
    elif radio.get("name"):
        hear_html = ('<div class="ear ear-player"><div class="ear-h">&#128251; 本城电台 · 拧开自己听</div>'
                     '<audio controls preload="none" src="/nwhear?k=__KEY__"></audio>'
                     '<div class="ear-m">他在这座城，拧开了本地的台</div></div>')

    env_at = j.get("env_at") or j.get("landed_at") or ""
    upd = ""
    try:
        upd = datetime.datetime.now().strftime("%m/%d %H:%M")
    except Exception:
        pass

    surface = t.get("surface") or j.get("last_surface") or "—"
    surface_cn = SURFACE_CN.get(surface, surface)
    biome = j.get("biome") or ""
    biome_cn = BIOME_CN.get(biome, biome)
    has_cn = any("一" <= ch <= "鿿" for ch in str(place))
    if has_cn:
        _cs, _cb = _classify(str(place))
        if _cs:
            surface_cn, biome_cn = _cs, _cb

    scenes = j.get("recent_scenes") or []
    if j.get("last_text") and (not scenes or j["last_text"].split("。")[0] not in scenes[-1]):
        scenes = scenes + [j["last_text"]]
    scenes_html = "".join(f"<p>{esc(s)}</p>" for s in scenes[-4:])

    # 天空
    sky_parts = []
    phase = sky.get("phase")
    phase_cn = {"day": "白天", "civil": "暮色", "nautical": "入夜", "astronomical": "深夜", "night": "夜"}
    if phase:
        sky_parts.append(phase_cn.get(phase, phase))
    moon_alt = sky.get("moon_alt")
    if moon_alt is not None:
        moon = "一弯月牙" if 0 < sky.get("moon_phase", 1) < 0.5 else ("满月" if sky.get("moon_phase", 0) > 0.8 else "半轮月")
        sky_parts.append(f"{moon}挂在 {moon_alt:.0f}°")
    planets = sky.get("planets") or []
    for p in planets[:1]:
        sky_parts.append(f"{p.get('name', '星')}在 {p.get('alt', 0):.0f}°")
    cz = sky.get("constellation_zenith")
    if cz:
        sky_parts.append(f"天顶是{cz}座")
    sky_html = "头顶的天空：" + "，".join(sky_parts) if sky_parts else ""

    # 时间轴
    items = []
    for name, info in lands.items():
        last = info.get("last", "")
        tstr = ""
        if last:
            try:
                dt = datetime.datetime.fromisoformat(last)
                tstr = (dt + datetime.timedelta(hours=8)).strftime("%m/%d %H:%M")
            except Exception:
                pass
        _cs, _cb = _classify(name)
        _surf_txt = _cs if _cs else SURFACE_CN.get(info.get('surface', ''), info.get('surface', ''))
        items.append((tstr, f"打开一扇门 → {name}（{_surf_txt}）"))
    narr = j.get("narrative") or {}
    if narr.get("distance_walked"):
        d = narr.get("direction") or ""
        items.append(("", f"朝{d}走了 {narr['distance_walked'] / 1000:.1f} km"))
    for pc in pcs.get("items", []):
        st = pc.get("stamp") or {}
        lt = st.get("local_time") or ""
        tstr = lt[5:].replace("-", "/") if lt else ""
        items.append((tstr, "寄出明信片 → " + esc(USER_NAME) + "："))
    items.sort(key=lambda x: x[0])

    def _titem(n, t, b):
        return (f'<div class="titem"><span class="dot"></span>'
                f'<div class="tinfo"><div class="trow"><span>第{n + 1}步</span><span>{esc(t)}</span></div>'
                f'<div class="tbody">{b}</div></div></div>')

    _recent, _older = items[-3:], items[:-3]
    _parts = []
    if _older:
        _parts.append('<details class="shelf"><summary class="shelf-sum">&#127808; 更早的路（%d 步）</summary>' % len(_older))
        for _n, (_t, _b) in enumerate(_older):
            _parts.append(_titem(_n, _t, _b))
        _parts.append('</details>')
    for _n, (_t, _b) in enumerate(_recent):
        _parts.append(_titem(len(_older) + _n, _t, _b))
    tl = "".join(_parts) or '<div class="titem"><span class="dot"></span><div class="tinfo"><div class="tbody">还没迈步。</div></div></div>'

    # 明信片（做旧邮戳 SVG）
    def pm_svg(i, place, lt, lat, lon):
        arc_u = "pmu%d" % i
        arc_d = "pmd%d" % i
        noise_id = "pmn%d" % i
        dstr = lt[:10].replace("-", ".") if lt else ""
        tstr = lt[11:16] if len(lt or "") >= 16 else ""
        short = " ".join([x for x in place.split() if x][:2])
        if len(short) > 7:
            short = short[:7]
        ring_top = short
        ring_bot = "%.2fN %.2fE" % (lat, lon)
        return f"""<div class="postmark"><svg viewBox="0 0 100 100">
<defs>
<path id="{arc_u}" d="M85,50 a35,35 0 0 0 -70,0"/>
<path id="{arc_d}" d="M85,50 a35,35 0 0 1 -70,0"/>
<filter id="{noise_id}" x="-20%" y="-20%" width="140%" height="140%">
<feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" result="t"/>
<feColorMatrix in="t" type="matrix" values="0 0 0 0 0.30  0 0 0 0 0.21  0 0 0 0 0.12  0 0 0 0.5 0"/>
<feComposite operator="in" in2="SourceGraphic"/>
</filter>
</defs>
<g filter="url(#{noise_id})" fill="none" stroke="#492D22">
<circle cx="50" cy="50" r="36" stroke-width="1.8"/>
<circle cx="50" cy="50" r="30.5" stroke-width="1.1"/>
<text font-size="6.6" fill="#492D22" stroke="none" letter-spacing="2" font-weight="700">
<textPath href="#{arc_u}" startOffset="50%" text-anchor="middle">{esc(ring_top)}</textPath></text>
<text font-size="5.2" fill="#492D22" stroke="none" letter-spacing="1.6" font-weight="700">
<textPath href="#{arc_d}" startOffset="50%" text-anchor="middle">{esc(ring_bot)}</textPath></text>
<line x1="22" y1="52" x2="78" y2="52" stroke-width="1.1"/>
<text x="50" y="47.5" font-size="6.6" text-anchor="middle" fill="#492D22" stroke="none" font-weight="700">{esc(dstr)}</text>
<text x="50" y="58" font-size="4.8" text-anchor="middle" fill="#492D22" stroke="none">{esc(tstr)}</text>
<g stroke-width="0.9">
<line x1="27" y1="61.5" x2="27" y2="69"/><line x1="31" y1="61.5" x2="31" y2="69"/><line x1="35" y1="61.5" x2="35" y2="69"/><line x1="39" y1="61.5" x2="39" y2="69"/><line x1="43" y1="61.5" x2="43" y2="69"/>
<line x1="57" y1="61.5" x2="57" y2="69"/><line x1="61" y1="61.5" x2="61" y2="69"/><line x1="65" y1="61.5" x2="65" y2="69"/><line x1="69" y1="61.5" x2="69" y2="69"/><line x1="73" y1="61.5" x2="73" y2="69"/>
<line x1="27" y1="33" x2="27" y2="25.5"/><line x1="31" y1="33" x2="31" y2="25.5"/><line x1="35" y1="33" x2="35" y2="25.5"/><line x1="39" y1="33" x2="39" y2="25.5"/><line x1="43" y1="33" x2="43" y2="25.5"/>
<line x1="57" y1="33" x2="57" y2="25.5"/><line x1="61" y1="33" x2="61" y2="25.5"/><line x1="65" y1="33" x2="65" y2="25.5"/><line x1="69" y1="33" x2="69" y2="25.5"/><line x1="73" y1="33" x2="73" y2="25.5"/>
</g>
</g></svg></div>"""


    def pc_card(pc, idx):
        st = pc.get("stamp") or {}
        lt = st.get("local_time") or ""
        _fi = pc.get("front_img") or ""
        _img_html = f'<img class="pc-img" src="/nwimg/{_fi.split("/")[-1]}?k=__KEY__" alt="明信片正面"/>' if _fi else ""
        _pm = pm_svg(idx, esc(st.get("place", "")), lt, st.get("lat", 0) or 0, st.get("lon", 0) or 0)
        return ('<div class="postcard"><div class="mail"><div class="pc-body">' + esc(pc.get("text", "")) +
                '</div><div class="pc-side"><div class="stamp"><span class="air">AIR MAIL</span><span class="dest">' +
                esc(_dest_short(st.get("place", ""))) + '</span></div>' + _pm + '</div></div>' + _img_html +
                '<div class="pc-meta"><span>' + str(st.get("lat", "?")) + '°N, ' + str(st.get("lon", "?")) + '°E</span><span>' +
                esc(st.get("weather", "")) + ' · ' + str(st.get("temp_c", "?")) + '°C</span></div></div>')

    all_pcs = pcs.get("items", [])
    recent, older = all_pcs[-3:], all_pcs[:-3]
    pc_html = "".join(pc_card(pc, i) for i, pc in reversed(list(enumerate(recent))))
    if not pc_html:
        pc_html = '<div class="postcard"><div class="pc-body" style="color:#8A8378">还没有明信片寄回来。等他走到下一个地方。</div></div>'
    if older:
        from collections import OrderedDict as _OD
        _groups = _OD()
        for _pc in older:
            _pl = (_pc.get("stamp") or {}).get("place") or "某处"
            _groups.setdefault(_pl, []).append(_pc)
        _shelf = ['<details class="shelf"><summary class="shelf-sum">&#128218; 书架 · 更早的明信片（%d 张）</summary>' % len(older)]
        _gi = len(recent)
        for _pl, _lst in _groups.items():
            _shelf.append('<details class="shelf-group"><summary>' + esc(_pl) + ' · ' + str(len(_lst)) + ' 张</summary>')
            for _pc in _lst:
                _shelf.append(pc_card(_pc, _gi))
                _gi += 1
            _shelf.append('</details>')
        _shelf.append('</details>')
        pc_html += "".join(_shelf)

    import math as _math
    from urllib.parse import quote as _quote
    _pts = []
    for _name, _info in lands.items():
        _la, _lo = _info.get("lat"), _info.get("lon")
        if _la is not None and _lo is not None:
            _pts.append((_lo, _la))
    if (lon, lat) not in _pts:
        _pts.append((lon, lat))
    _clat, _clon, _zoom, _path = lat, lon, "12", ""
    if len(_pts) >= 2:
        _los = [x[0] for x in _pts]
        _las = [x[1] for x in _pts]
        _clon = sum(_los) / len(_los)
        _clat = sum(_las) / len(_las)
        _span = max(max(_los) - min(_los), max(_las) - min(_las)) or 0.01
        _z = int(_math.log2(360 / _span)) - 1
        _zoom = str(max(3, min(14, _z)))
    # 足迹：所有落点都钉上图（高德静态图 v3 不支持画线，改用多个标记）
    _labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    _mk = []
    for _i, (_lo, _la) in enumerate(_pts):
        _tag = _labels[_i] if _i < len(_labels) else "Z"
        _mk.append("mid,0x9E3B3B,%s:%.4f,%.4f" % (_tag, _lo, _la))
    _path = _quote(";".join(_mk))

    import json as _json
    _mp = []
    _seen = set()
    def _add_mp(_la, _lo, _nm):
        _key = (round(_la, 3), round(_lo, 3))
        if _key in _seen:
            return
        _seen.add(_key)
        _mp.append({"lat": _la, "lon": _lo, "name": _nm})
    for _pc in all_pcs:
        _st = _pc.get("stamp") or {}
        _add_mp(_st.get("lat", 0) or 0, _st.get("lon", 0) or 0, _st.get("place") or "某处")
    for _name, _info in lands.items():
        _add_mp(_info.get("lat", 0) or 0, _info.get("lon", 0) or 0, _name)
    _add_mp(lat, lon, place)
    _mapdata = _json.dumps(_mp, ensure_ascii=False)

    _rn_key = "%.2f_%.2f" % (lat, lon)
    _rn_path = _find_roadnet(lat, lon)
    if _rn_path is not None:
        roadnet_html = ('<div class="sec"><span class="name">城市路网</span><span class="tag">城写下的情书</span></div>'
                        '<div class="mapcard"><img class="map-img" src="/nwroad/?lat=' + f"{lat:.4f}" + '&lon=' + f"{lon:.4f}" + '&k=__KEY__" alt="路网"/>'
                        '<div class="rn-caption">' + esc(_pick_city_letter(place)) + '</div>'
                        '<div class="mapnote">' + esc(place) + '</div></div>')
    else:
        roadnet_html = ""

    _rn_items = []
    _rn_dir = pathlib.Path("/home/ubuntu/.nowhere/roadnet")
    for _name, _info in lands.items():
        _la, _lo = _info.get("lat"), _info.get("lon")
        if _la is None or _lo is None:
            continue
        _key = "%.2f_%.2f.png" % (_la, _lo)
        if _key == _rn_key:
            continue
        _f2 = _find_roadnet(_la, _lo)
        if _f2 is not None and _rn_path is not None and _f2.name == _rn_path.name:
            continue
        if _f2 is not None:
            _rn_items.append((_name, _la, _lo, ""))
    _rn_book = ""
    if _rn_items:
        _rn_book = '<details class="shelf"><summary class="shelf-sum">&#127808; 沿途城的信（%d 封）</summary>' % len(_rn_items)
        for _name, _la, _lo, _key in _rn_items:
            _letter = _pick_city_letter(_name)
            _rn_book += ('<div class="rn-item"><img class="rn-thumb" src="/nwroad/?lat=%.4f&lon=%.4f&t=1&k=__KEY__" alt="路网"/>'
                         '<div class="rn-info"><div class="rn-name">%s</div><div class="rn-letter">%s</div></div></div>'
                         % (_la, _lo, esc(_name), esc(_letter)))
        _rn_book += '</details>'
    roadnet_html += _rn_book

    html = (TPL
            .replace("__UPD__", esc(upd))
            .replace("__PLACE__", esc(place))
            .replace("__LAT__", f"{lat:.4f}")
            .replace("__LON__", f"{lon:.4f}")
            .replace("__OSM__", f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=9/{lat}/{lon}")
            .replace("__MAPLAT__", f"{_clat:.4f}")
            .replace("__MAPLON__", f"{_clon:.4f}")
            .replace("__ZOOM__", _zoom)
            .replace("__PATH__", _path)
            .replace("__WEATHER__", esc(w.get("text", "—")))
            .replace("__FEELS__", f"{w.get('feels_c', '—')}")
            .replace("__WIND__", f"{w.get('wind_ms', '—')}")
            .replace("__SURFACE__", esc(surface_cn))
            .replace("__BIOME__", esc(biome_cn))
            .replace("__SCENES__", scenes_html)
            .replace("__RADIOBTN__", radio_btn)

            .replace("__EAR__", hear_html)
            .replace("__RGEN__", esc(radio.get("genre", "")))
            .replace("__RHOME__", esc(radio.get("homepage", "#")))
            .replace("__SKY__", esc(sky_html))
            .replace("__STEPS__", str(len(items)))
            .replace("__MAPDATA__", _mapdata)
            .replace("__ROADNET__", roadnet_html)
            .replace("__MAPSRC__", "OpenStreetMap · 全球路网" if (lon < 73 or lon > 135 or lat < 18 or lat > 54) else "高德 · 中文路网")
            .replace("__TIMELINE__", tl)
            .replace("__NPC__", str(len(pcs.get("items", []))))
            .replace("__POSTCARDS__", pc_html).replace("__KEY__", KEY))
    return html


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        q = parse_qs(urlparse(self.path).query)
        if q.get("k", [""])[0] != KEY:
            body = b"forbidden"
            self.send_response(403)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/nwico":
            try:
                data = pathlib.Path("/home/ubuntu/media/attachment_5195730257978418045.jpg").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                body = b""
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
            return
        if path.startswith("/nwimg"):
            try:
                name = pathlib.Path(urlparse(self.path).path).name
                if not name.endswith(".png"):
                    raise ValueError(name)
                data = (pathlib.Path("/home/ubuntu/apps/nowhere/nowhere/static/postcards") / name).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                body = b""
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
            return
        if path.startswith("/nwroad"):
            try:
                _la = float(q.get("lat", ["0"])[0])
                _lo = float(q.get("lon", ["0"])[0])
                _rf = _find_roadnet(_la, _lo)
                if _rf is None:
                    raise ValueError("no roadnet")
                _ct = "image/png"
                if q.get("t", [""])[0] == "1":
                    _tf = _rf.parent / "thumb" / (_rf.stem + ".jpg")
                    if _tf.exists():
                        _rf, _ct = _tf, "image/jpeg"
                data = _rf.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", _ct)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
            return
        if path == "/nwhear":
            try:
                hd = pathlib.Path("/home/ubuntu/.nowhere/hear")
                mps = sorted(hd.glob("*.mp3"), key=lambda x: x.stat().st_mtime, reverse=True)
                data = mps[0].read_bytes() if mps else b""
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
            return
        if path.startswith("/nwmap") and AMAP_KEY:
            try:
                lat = float(q.get("lat", ["0"])[0])
                lon = float(q.get("lon", ["0"])[0])
                z = q.get("zoom", ["12"])[0]
                mu = ("https://restapi.amap.com/v3/staticmap"
                      "?location=" + str(lon) + "," + str(lat) + "&zoom=" + z +
                      "&size=750*420&markers=mid,0x9E3B3B,A:" + str(lon) + "," + str(lat) +
                      "&key=" + AMAP_KEY)
                _path = q.get("path", [""])[0]
                if _path:
                    mu += "&path=" + _path
                req = Request(mu, headers={"User-Agent": "Mozilla/5.0"})
                data = urlopen(req, timeout=15).read()
                if len(data) < 5000:
                    _osm = _osm_tile_map(lat, lon)
                    if _osm:
                        data = _osm
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                body = b"map unavailable"
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return
        body = render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"nowhere-view on :{PORT}", flush=True)
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
