#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手机自动收货：把新明信片和旅行日记拉到手机本地。
用法：先填下面的 BASE 和 KEY，然后在手机 Termux 里运行：python3 fetch_cards.py
"""
import json
import pathlib
import urllib.request

# ===== 改成你自己的服务器地址（二选一）=====
BASE = "http://你的服务器IP:18082"
# BASE = "https://你的域名或隧道地址"
KEY = "你的访问钥匙"
# ==========================================

PIC_DIR = pathlib.Path("/sdcard/Pictures/乌有乡明信片")
DIARY_DIR = pathlib.Path("/sdcard/Download/Operit/乌有乡存档")


def get(url):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch():
    PIC_DIR.mkdir(parents=True, exist_ok=True)
    DIARY_DIR.mkdir(parents=True, exist_ok=True)

    cards = json.loads(get("%s/nwdl/?f=list&k=%s" % (BASE, KEY)).decode("utf-8"))
    for name in cards.get("cards", []):
        dst = PIC_DIR / name
        if dst.exists():
            continue
        data = get("%s/nwimg/%s?k=%s" % (BASE, name, KEY))
        dst.write_bytes(data)
        print("已收明信片:", name)

    diary = get("%s/nwdl/?f=diary&k=%s" % (BASE, KEY))
    (DIARY_DIR / "旅行日记.md").write_bytes(diary)
    print("旅行日记已更新")


if __name__ == "__main__":
    fetch()