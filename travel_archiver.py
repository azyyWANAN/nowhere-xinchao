#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旅行归档差：乌有乡的明信片与场景文字，一条不丢。

跑在乌有乡同一台服务器上，每 5 分钟扫一遍数据目录：
- 新明信片 -> travel-diary.md（可选写入 ombrebrain 信桶）
- 新场景文字 -> travel-diary.md
- 明信片图 -> archive 目录（可选）

配置（环境变量）：
  NOWHERE_HOME  乌有乡数据目录，默认 ~/.nowhere
  ARCHIVE_DIR   归档目录，默认 ./archive
  POSTER_DIR    明信片海报目录，不设则跳过图片归档
  OB_URL         ombrebrain 信桶地址，不设则跳过信桶写入
  OB_TOKEN       ombrebrain 信桶钥匙
  USER_NAME      信桶署名（收信人），默认 "你"
  AI_NAME        信桶署名（写信人），默认 "TA"
"""
import hashlib
import json
import os
import pathlib
import time
import datetime
import urllib.request
import shutil

NOWHERE_HOME = pathlib.Path(os.environ.get("NOWHERE_HOME", str(pathlib.Path.home() / ".nowhere")))
ARCHIVE_DIR = pathlib.Path(os.environ.get("ARCHIVE_DIR", "archive"))
DIARY = ARCHIVE_DIR / "travel-diary.md"
STATE = ARCHIVE_DIR / ".archive-state.json"
_POSTER_DIR = os.environ.get("POSTER_DIR", "")
POSTER_DIR = pathlib.Path(_POSTER_DIR) if _POSTER_DIR else None
OB_URL = os.environ.get("OB_URL", "")
OB_TOKEN = os.environ.get("OB_TOKEN", "")
USER_NAME = os.environ.get("USER_NAME", "你")
AI_NAME = os.environ.get("AI_NAME", "TA")


def post_json(url, payload, token=None, timeout=60):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def load_json(name):
    try:
        return json.loads((NOWHERE_HOME / name).read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"postcards": [], "scene_hash": ""}


def save_state(st):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def diary_append(text):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    with open(DIARY, "a", encoding="utf-8") as f:
        f.write("\n## " + now + "\n\n" + text.strip() + "\n")


def ob_letter(title, content):
    if not OB_URL:
        return
    today = datetime.date.today().isoformat()
    payload = {
        "jsonrpc": "2.0", "id": 11, "method": "tools/call",
        "params": {
            "name": "letter_write",
            "arguments": {
                "author": "ai",
                "content": content,
                "title": title,
                "user_name": USER_NAME,
                "ai_name": AI_NAME,
                "date": today,
            },
        },
    }
    try:
        post_json(OB_URL, payload, token=OB_TOKEN)
    except Exception as e:
        print(datetime.datetime.now().isoformat(), "OB ERR", str(e)[:120], flush=True)


def main():
    while True:
        try:
            st = load_state()
            # 1. 明信片
            pcs = load_json("postcards.json").get("items", [])
            for pc in pcs:
                pid = str(pc.get("id"))
                if pid in st["postcards"]:
                    continue
                stamp = pc.get("stamp") or {}
                place = stamp.get("place", "某处")
                text = pc.get("text", "")
                meta = "（%s · %s · %s°N %s°E · %s°C %s）" % (
                    stamp.get("local_time", "")[:16], place,
                    stamp.get("lat", "?"), stamp.get("lon", "?"),
                    stamp.get("temp_c", "?"), stamp.get("weather", ""),
                )
                diary_append("【明信片 · %s】%s\n\n%s" % (place, meta, text))
                ob_letter("乌有乡明信片·%s" % place, text + "\n\n" + meta)
                # 图归档
                if POSTER_DIR is not None:
                    src = POSTER_DIR / ("card_%s.png" % pid)
                    if src.exists():
                        dst = ARCHIVE_DIR / "postcards" / ("card_%s.png" % pid)
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                st["postcards"].append(pid)
                print(datetime.datetime.now().isoformat(), "postcard archived", pid, flush=True)
            # 2. 场景文字（增量，防滚动覆盖丢字）
            j = load_json("journey.json")
            scenes = j.get("recent_scenes") or []
            last_text = j.get("last_text") or ""
            h = json.dumps([scenes[-4:], last_text[:400], j.get("place_name", "")], ensure_ascii=False, sort_keys=True)
            hh = hashlib.md5(h.encode("utf-8")).hexdigest()
            if st.get("scene_hash") != hh and (scenes or last_text):
                block = list(scenes[-4:])
                if last_text and (not block or block[-1] != last_text):
                    block.append(last_text)
                if block:
                    diary_append("【脚步 · %s】%s" % (j.get("place_name", ""), "；".join(block[-3:])))
                st["scene_hash"] = hh
            save_state(st)
        except Exception as e:
            print(datetime.datetime.now().isoformat(), "ERR", str(e)[:120], flush=True)
        time.sleep(300)


if __name__ == "__main__":
    main()