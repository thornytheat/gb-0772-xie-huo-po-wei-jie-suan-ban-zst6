# 卸货泊位结算板

供城市配送管理岗核对杆侧停靠、卸货预约与实收回执。阶段导航按采信、匿名关联、占位重建、核价、对账及签发展开。竖向时间轨显示同一次停靠的午夜切分和收费档。

## 启动

```sh
docker compose up --build
```

访问 `http://localhost:18471/`。本地用 Python 3.12 运行。

```sh
python -m pip install -r requirements-test.txt
python -m uvicorn app.main:create_app --factory --port 18471
python -m pytest -q
```

默认数据库为 `var/curb.sqlite3`，容器使用 `curb-dockets` 卷。重置自建环境可在停服后删除该数据库文件或命名卷。生成新的数据库会生成新的车辆代号密钥。

## 核对样例

1. 首页选择「跨夜争议样例」。两个泊位合计应管 240 分钟，133 空闲、7 争议、10 首免、68 基础价及 22 升级价。
2. 「占用区间重建」查去重的 17 分钟；「首免与升级价」选择 11/30 23:40 的 B-01，时间轨显示首免一次、午夜切日、升级档和 5 分钟同泊争议。
3. 「逐单与泊位对账」查看应收 ¥22.40、关联实收 ¥23.10、净差 ¥0.70，以及单列的游离回执 ¥1.40；「泊位待核与应管」并列各泊位停测、已核实、他杆补足、待核分钟。
4. 点击「运行清算」生成留档，重复运行复用同一编号。进入「理赔证据签发」下载去车牌化的逐单证据。

## 停测与更正

`survey.json` 可加 `outages` 申报杆侧停测：

```json
{"berth":"B-02","sensor":"side-2","start":"2026-12-01T01:10+08:00","end":"2026-12-01T01:30+08:00"}
```

申报内没有任何检测的分钟转「待核」，既不算空闲也不出账；同一泊位另一根杆实际覆盖到的申报分钟按停靠正常结账，其余仍待核，所以单个泊位的缺口不会拖住整批。对账页可逐泊位核对停测、已核实、他杆补足与待核分钟及应管分钟。

晚到杆侧记录补齐后，用原留档编号提交更正，留档不新增：

```sh
curl -s localhost:18471/api/dockets -H 'Content-Type: application/json' \
  -d '{"bundle": {...四份原件...}, "parent": "<原留档编号>"}'
```

更正沿用原留档编号，`manifest.changes` 逐泊位列出待核、空闲、争议与出账分钟的前后值，原摘要进入 `manifest.history`。同一份补齐输入重跑复用原记录，不重复出账也不新增留档。详见[理赔复核步骤](docs/APPEAL.md)。

独立预览为 `GET /api/cases/{dirty|clean}/{stage}`，阶段名见深度登记，另可用 `outages` 看停测待核；带 `parent=<原留档编号>` 可按更正口径预览。自有样例可以 `POST /api/dockets`，`bundle` 对象需包含 `survey`、`sensors`、`bookings`、`payments` 四份 UTF-8 字符串，内置数据可用 `{"sample":"dirty"}`，更正另加 `parent`。历史 `GET /api/dockets`，归档 `GET /api/dockets/{key}`，理赔附件 `GET /api/export/{key}`。

- [字段、计费与边界](docs/DATA-DICTIONARY.md)
- [模块和陷阱](docs/DEPTH.md)
- [理赔复核步骤](docs/APPEAL.md)
