#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""乌有乡旅程档案 · 手机网页版（通用版）

读乌有乡落盘的 journey.json / postcards.json / landings.json，
渲染成一页旅程档案。所有访问需要带 ?k= 钥匙。

环境变量：
  NOWHERE_HOME      乌有乡数据目录，默认 ~/.nowhere
  NOWHERE_VIEW_KEY  网页访问钥匙；不设则每次启动随机生成并打印
  NOWHERE_VIEW_PORT 监听端口，默认 18082
"""
import json, html, os, pathlib, secrets
from urllib.request import urlopen, Request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import datetime

BASE = pathlib.Path(__file__).resolve().parent
TPL = (BASE / "index.tpl.html").read_text(encoding="utf-8")
NOWHERE_HOME = pathlib.Path(os.environ.get("NOWHERE_HOME", str(pathlib.Path.home() / ".nowhere")))
KEY = os.environ.get("NOWHERE_VIEW_KEY", "") or secrets.token_hex(16)
USER_NAME = os.environ.get("USER_NAME", "烟烟")
PORT = int(os.environ.get("NOWHERE_VIEW_PORT", "18082"))

AMAP_KEY = os.environ.get("AMAP_KEY", "")

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
    hear_html = ""
    if heard.get("text"):
        hear_html = (f'<div class="ear"><div class="ear-h">&#128266; 随行耳朵 · 他听见了</div>'
                     f'<p>{esc(heard["text"])}</p><div class="ear-m">{esc(heard.get("at", ""))} · 现场截听 {heard.get("sec", 20)} 秒</div><div class="ear-hint">他在这座城，拧开了本地的台</div></div>')
    elif radio.get("name"):
        hear_html = ('<div class="ear ear-player"><div class="ear-h">&#128251; 本城电台 · 拧开自己听</div>'
                     '<audio controls preload="none" src="/nwhear?k=__KEY__"></audio>'
                     '<div class="ear-m">从当地截下的一段现场，点开就是这座城的声音</div></div>')

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
        surface_cn = "城市"
        biome_cn = "城市"

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
        items.append((tstr, f"打开一扇门 → {name}（{SURFACE_CN.get(info.get('surface', ''), info.get('surface', ''))}，海拔 {info.get('elevation', '?')} m）"))
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
    tl = "".join(
        f'<div class="titem"><span class="dot"></span>'
        f'<div class="tinfo"><div class="trow"><span>第{n + 1}步</span><span>{esc(t)}</span></div>'
        f'<div class="tbody">{b}</div></div></div>'
        for n, (t, b) in enumerate(items)
    ) or '<div class="titem"><span class="dot"></span><div class="tinfo"><div class="tbody">还没迈步。</div></div></div>'

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


    pc_html = ""
    for idx, pc in enumerate(pcs.get("items", [])):
        st = pc.get("stamp") or {}
        lt = st.get("local_time") or ""
        _fi = pc.get("front_img") or ""
        _img_html = f'<img class="pc-img" src="/nwimg/{_fi.split("/")[-1]}?k=__KEY__" alt="明信片正面"/>' if _fi else ""
        pc_html += f'''
        <div class="postcard">
          <div class="mail">
            <div class="pc-body">{esc(pc.get("text", ""))}</div>
            <div class="pc-side">
              <div class="stamp"><span class="air">AIR MAIL</span><span class="dest">{esc(_dest_short(st.get("place", "")))}</span></div>
              {pm_svg(idx, esc(st.get("place", "")), lt, st.get("lat", 0) or 0, st.get("lon", 0) or 0)}
            </div>
          </div>
          {_img_html}
          <div class="pc-meta">
            <span>{st.get("lat", "?")}°N, {st.get("lon", "?")}°E</span>
            <span>{esc(st.get("weather", ""))} · {st.get("temp_c", "?")}°C</span>
          </div>
        </div>'''
    if not pc_html:
        pc_html = '<div class="postcard"><div class="pc-body" style="color:#8A8378">还没有明信片寄回来。等他走到下一个地方。</div></div>'

    html = (TPL
            .replace("__UPD__", esc(upd))
            .replace("__PLACE__", esc(place))
            .replace("__LAT__", f"{lat:.4f}")
            .replace("__LON__", f"{lon:.4f}")
            .replace("__OSM__", f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=9/{lat}/{lon}")
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
        if path.startswith("/nwimg"):
            try:
                name = pathlib.Path(urlparse(self.path).path).name
                if not name.endswith(".png"):
                    raise ValueError(name)
                data = (pathlib.Path(os.environ.get("NOWHERE_POSTER_DIR", "")) / name).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
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
                hd = pathlib.Path(NOWHERE_HOME) / "hear"
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
                req = Request(mu, headers={"User-Agent": "Mozilla/5.0"})
                data = urlopen(req, timeout=15).read()
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
        else:
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
    print(f"访问钥匙 k={KEY}", flush=True)
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()