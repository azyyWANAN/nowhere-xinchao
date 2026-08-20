# -*- coding: utf-8 -*-
"""乌有乡明信片正面图生成器（写实风景照）。
配置：web/nwimg_config.json
  {"enabled": true, "api_key": "...", "model": "image-01",
   "prompt_template": "..."}
enabled=false 或 api_key 为空时关闭（通用版默认关闭）。"""
import json, pathlib, time, urllib.request

BASE = pathlib.Path(__file__).resolve().parent
CFG = BASE / "nwimg_config.json"
OUT = pathlib.Path("/home/ubuntu/apps/nowhere/nowhere/static/postcards")

def _cfg():
    try:
        return json.loads(CFG.read_text(encoding="utf-8"))
    except Exception:
        return {}

def make_postcard_image(place, lat, lon, weather, biome, time_hint=""):
    """生成一张正面图，返回文件名；失败/关闭返回 None。"""
    c = _cfg()
    if not c.get("enabled") or not c.get("api_key"):
        return None
    key = c["api_key"]
    model = c.get("model", "image-01")
    # 地点专属提示词优先（img_prompts.json）
    try:
        prompts = json.loads((BASE / "img_prompts.json").read_text(encoding="utf-8"))
    except Exception:
        prompts = {}
    scene = (prompts or {}).get(place, "")
    if scene == "KEEP":
        return None
    tpl = c.get("prompt_template",
        "A photorealistic travel landscape photograph, 35mm film, natural light, "
        "no text, no watermark, no people, serene and beautiful scenery of {place}, "
        "{weather} weather, {biome} terrain, golden hour atmosphere.")
    light = ""
    if time_hint:
        try:
            _h = int(time_hint.split(":")[0])
        except Exception:
            _h = 12
        if 0 <= _h < 5:
            light = "深夜：深蓝近黑的夜空，一轮明月，星星稀疏，暖黄灯火零星点缀，冷蓝主色调，景物呈剪影"
        elif 5 <= _h < 8:
            light = "清晨：淡蓝晨光，薄雾贴着地面流动，天边泛鱼肚白，草叶带露水，清冷宁静"
        elif 8 <= _h < 17:
            light = "白天：明亮自然光，蓝天白云，景物清晰通透"
        elif 17 <= _h < 20:
            light = "黄昏：金色暖光，天边橙红渐变，地面拉出长影子，温暖"
        else:
            light = "夜晚：蓝紫色夜空，华灯初上，暖色灯光与冷色天空对比"
    if scene:
        prompt = scene + "，" + (light or "自然光") + "，写实摄影，35mm胶片，横构图4:3，无文字，无水印，无人"
    else:
        prompt = tpl.format(place=place, lat=lat, lon=lon, weather=weather,
                            biome=biome, light=(light or "自然光"))
    body = {"model": model, "prompt": prompt, "n": 1,
            "response_format": "url", "aspect_ratio": "4:3"}
    req = urllib.request.Request("https://api.minimaxi.com/v1/image_generation",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read().decode())
        url = None
        d = resp.get("data") or {}
        if isinstance(d, dict):
            items = d.get("image_urls") or []
            if items:
                url = items[0]
            elif d.get("url"):
                url = d["url"]
        elif isinstance(d, list) and d:
            first = d[0] or {}
            url = first.get("url") or first.get("image_url")
        if not url:
            print("imggen: no url in resp", str(resp)[:300])
            return None
        with urllib.request.urlopen(url, timeout=120) as r2:
            data = r2.read()
        OUT.mkdir(parents=True, exist_ok=True)
        fname = "pc_%s_%d.png" % (abs(hash(place + str(lat) + str(lon))) % 100000, int(time.time()))
        (OUT / fname).write_bytes(data)
        return fname
    except Exception as e:
        print("imggen FAIL:", e)
        return None

if __name__ == "__main__":
    import sys
    r = make_postcard_image(sys.argv[1] if len(sys.argv) > 1 else "测试地点",
                            sys.argv[2] if len(sys.argv) > 2 else "0",
                            sys.argv[3] if len(sys.argv) > 3 else "0",
                            sys.argv[4] if len(sys.argv) > 4 else "晴",
                            sys.argv[5] if len(sys.argv) > 5 else "城市")
    print("RESULT:", r)
