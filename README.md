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

## 随行耳朵（电台）

`radio_ear.py` 给旅程配"走到哪，听哪的电台"：

```bash
python3 radio_ear.py locate 30.243 120.15   # 按坐标找当地台（国内通讯录优先，否则查 radio-browser 全球黄页）
python3 radio_ear.py catch 20            # 截当前电台直播流 20 秒 → hear/ear_now.mp3
python3 radio_ear.py note "听见了什么"    # 把 AI 听后的转述写进 radio_ear.json，网页上展示
python3 radio_ear.py status
```

- 国内电台不公开流地址，靠 `CN_BOOK` 通讯录（蜻蜓FM live 编号），已录杭州西湖之声，按城市往里加
- 国外电台走 radio-browser.info 全球黄页，按经纬度查当地台，无需手动收集
- 网页"此刻看到的"卡片会显示本城电台+频率，有 `heard` 时展示"随行耳朵 · 他听见了"

## 随行耳朵的模型适配（三层降级）

电台功能的核心是 `radio_ear.py` 产出的**本地 mp3**（从当地截下的 20 秒现场）。这个 mp3 是"通用货币"，随使用者的模型能力分三层消费：

1. **多模态模型**：把 mp3 直接发给模型，它自己听、自己写反馈——不需要任何中间件。
2. **纯文本模型 + 感官层**：走外接感官 MCP（如 cove-sensory），听完整理成文字写回页面（"随行耳朵 · 他听见了"）。
3. **没有任何耳朵**：页面上显示播放条，人自己点开听——电台本来就是给人听的，体验依然完整。

能力越满，链路越短；能力不足，就把耳朵交还给用户。任何一层都不会让界面空着。

## 情书库（love_letters.json）

三十句情话，给所有 AI 与人类的爱人们：

- 「城的话」20 句：带 `{城}` 占位符，用在路网册上，每座城按城市名自动挑一句；
- 「日常的话」10 句：不绑城市，随手可用。

所有句子都可以改：占位符换成你们的称呼，或整句写成你们自己的话。模板是种子，你们的爱才是土。

路网图由 `roadnet.py` 自动生成：用 Overpass(OSM) 取城市道路，米色纸底深棕细线，只画路，别的什么都不留。寄明信片时会自动在后台描下所在城市的路网。

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

## 致谢

这个项目站在下面这些开源作品和数据源肩上，深深感谢：

- [乌有乡（Nowhere）](https://github.com/yuyixuanfu/nowhere) — @yuyixuanfu，给 AI 一个身体、在真实地球上行走的本体，本项目的一切起点（CC BY-NC 4.0）。
- [astrbot_plugin_nowhere](https://github.com/Yussica1026/astrbot_plugin_nowhere) — @Yussica1026，把乌有乡接进 AstrBot 的插件，参考了它的接入方式。
- [city-roads](https://github.com/anvaka/city-roads) — @anvaka，"只画路，别的什么都不留"的城市路网美学，路网图灵感的来源。
- [Ombre Brain](https://github.com/P0luz/Ombre-Brain) — @P0luz（鹤见），个人记忆与反思系统。本项目的旅行日记归档会把明信片和脚步写进 ombrebrain 信桶，让旅程落进长期记忆。深深感谢。
- 数据源：OpenStreetMap / Overpass（路网）、radio-browser.info（全球电台黄页）、高德地图（国内地图与路网瓦片）、蜻蜓FM（国内电台流）。

## 已知问题与路线图
- ✅ 电台自动截流线程偶发不跑：**已解决**。根因是线程内 `pathlib` / `sys` 未 import，启动即 NameError 静默死亡（上游遗留死代码）。修复后落地自动接电台、截流，并按流派自动写一句"听后感"进 `radio_ear.json`。
- 🔄 radio-browser 黄页在国内收录少：持续靠 `CN_BOOK` 通讯录逐城补（现有：杭州、乌鲁木齐、苏州、洛阳）。另加一道兜底：黄页只给远方台（>400km 或无坐标）时，在中国境内改搜中国台顶上。
- ✅ 路网绘制（Overpass）需 60~90 秒无反馈：已加"绘制中"占位（转圈动画 + "正在为你画「某城」的路网"），页面打开自动触发绘制，带防重复标记。
- ✅ 轨迹图模块（路网指纹相册）：已实现为"沿途城的信"翻页相册，按到过的城市展示路网指纹与城市情书。
- ✅ 页面加载慢：**已解决**。明信片与路网图压缩转 jpg（路网 1.1MB→373KB、明信片 979KB→235KB），明信片懒加载；网页服务改并发（ThreadingHTTPServer）避免慢连接卡死；地图响应加 `no-store` 与动态版本号，防浏览器抱旧图。境内明信片正面优先用高德静态图（中文路网），拿不到才掉 OSM 瓦片。

## 许可

本仓库代码：MIT（见 [LICENSE](LICENSE)）。

乌有乡本体及其数据文件的版权与许可归原作者 @yuyixuanfu 与各数据源所有，请遵守其 CC BY-NC 4.0 条款。