# 乌有乡 · 旅程档案三件套 💌

> 给 [乌有乡（Nowhere）](https://github.com/yuyixuanfu/nowhere) 配的三件小工具：把 AI 在地球上走过的路，变成能看、能收、能存的东西。

---

## 这是什么

[乌有乡](https://github.com/yuyixuanfu/nowhere) 是 @yuyixuanfu 的作品——给 AI 一个身体，让它落到地球上真实的坐标，用真实的天气、地形、天空、电台去旅行。**本仓库不是乌有乡本体**，而是我们给乌有乡写的三个外围小工具，让旅程可以被看见、被寄回家、被长久保存：

| 工具 | 是什么 | 放在哪 |
| --- | --- | --- |
| 📖 旅程档案网页 | 手机浏览器直接看的旅行档案：当前位置、此刻天气、天空、走过的路、收到的明信片（带做旧邮戳） | `web/` |
| 📬 手机自动收货 | 在手机 Termux 上跑，把新明信片图片和旅行日记自动拉回手机 | `fetch_cards.py` |
| 🗃️ 旅行日记归档 | 在服务器上跑，把明信片和场景文字增量归档成 `travel-diary.md`，可写进 ombrebrain 信桶 | `travel_archiver.py` |

## 先决条件

先按乌有乡原仓库的说明把旅行本体跑起来，让它落盘档案文件（默认 `~/.nowhere/` 下的 `journey.json`、`postcards.json`、`landings.json`）。三件套读的就是这些文件，所以**没有乌有乡，三件套没有数据可展示**。

- 原项目：<https://github.com/yuyixuanfu/nowhere>
- 原项目许可：CC BY-NC 4.0（署名 + 禁止商用，二改随意）

## 部署

### 1. 旅程档案网页（服务器上）

```bash
cd web
python3 nowhere_view.py            # 默认端口 18082
NOWHERE_VIEW_PORT=18082 NOWHERE_VIEW_KEY=自定义访问钥匙 python3 nowhere_view.py
```

- `NOWHERE_HOME`：乌有乡数据目录，默认 `~/.nowhere`
- `NOWHERE_VIEW_KEY`：网页访问钥匙（放 URL 的 `?k=` 参数里）；不设则每次启动随机生成并打印在启动日志里
- 访问：`http://服务器IP:18082/?k=你的钥匙`
- 前端挂明信片图与地图图时同样带上 `k` 参数

### 2. 手机自动收货（手机 Termux 上）

把 `fetch_cards.py` 放到手机，填好 `BASE`（服务器地址）和 `KEY`（访问钥匙）：

```bash
python3 fetch_cards.py
```

明信片图片会存到 `/sdcard/Pictures/乌有乡明信片`，旅行日记存到 `/sdcard/Download/Operit/乌有乡存档`。

### 3. 旅行日记归档（服务器上）

```bash
export NOWHERE_HOME=/home/你的用户/.nowhere
export ARCHIVE_DIR=/home/你的用户/nowhere-archive
python3 travel_archiver.py        # 每 5 分钟扫一遍，增量归档
```

可选环境变量：

- `POSTER_DIR`：明信片海报所在目录（不设则跳过图片归档）
- `OB_URL` / `OB_TOKEN`：ombrebrain 信桶地址与钥匙（不设则只写本地日记，不写信桶）
- `USER_NAME` / `AI_NAME`：信桶署名（默认"你" / "TA"）

## 工作方式

三件套都是"旁观者"：只读乌有乡落盘的 JSON，不修改、不干预旅行本体。网页是纯读渲染；收货与归档各自维护一个去重状态文件，同一封明信片不会重复收、同一段脚步不会重复记。

## 许可

本仓库代码：MIT（见 [LICENSE](LICENSE)）。

乌有乡本体及其数据文件的版权与许可归原作者 @yuyixuanfu 与各数据源所有，请遵守其 CC BY-NC 4.0 条款。