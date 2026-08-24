# PTA Stops 与 Transperth GTFS 接入指导

**核对日期：2026-08-21**
**当前状态：PTA Stops 图层和 GTFS 下载已实际核验；首轮只测试 PTA Stops**
**建议用途：公共交通站点接近性；Transperth 覆盖内的计划服务作为后续增强**

## 1. 当前采用决定

PTA Stops 与 Transperth GTFS 必须分开处理。PTA Stops 是 WA 公交、铁路和渡轮站点图层；GTFS 是会随时刻表更新的 Transperth 计划服务 feed。站点附近不等于一定有高频服务，GTFS 范围外也不等于零公共交通。

49 地点首轮 Notebook 只接入 PTA Stops，提取最近有效站点距离、最近站点类型和固定测试半径内的有效站点数。GTFS 暂不混入同一个首轮输出；只有先确认 49 地点中有多少能够与 GTFS stop 匹配，才另做时刻表 Notebook。

## 2. 49 地点共同输入前置条件

统一输入为 `data/test_inputs/pedestrian_observation_locations_49.csv`，必须有 49 个唯一 `location_id` 和可追溯的 EPSG:4326 坐标。当前合并表只有 48 个地点，缺少 **North West Coastal Hwy Norseman, SLK 52.5**，因此应先补齐共享输入。

## 3. 官方来源与当前真实状态

官方目录是 [Data WA — Public Transport Authority Stops (PTA-001)](https://catalogue.data.wa.gov.au/dataset/public-transport-authority-stops-bus-stops)，许可标为 [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)。2026-08-21 核验时，目录 metadata 更新时间为 2026-08-20，并提供 GeoJSON、GeoPackage、Shapefile、WFS 和 ArcGIS REST。

已核验的 Feature Layer：

```text
https://public-services.slip.wa.gov.au/public/rest/services/
SLIP_Public_Services/Transport/MapServer/14
```

当前 `returnCountOnly` 返回 16,813 条，图层最大单次返回 10,000 条，因此 REST 全量下载必须分页并核对最终记录数；也可以优先保存官方 GeoJSON 快照：

```text
https://data-downloads.slip.wa.gov.au/PTA-001/GeoJSON
```

真实字段包括 `stopid`、`stopnumber`、`status`、`stopname`、`location`、`stoptype`、`suburb`、`accessible`、`shelter` 以及分时段服务字段。当前可见类别中，`status` 有 `Active` 和 `Planned`，`stoptype` 包含 `Standard`、`School`、`Rail`、`Ferry`、`CAT`、`Standard\CAT` 和 `Transwa`。

当前 distinct 查询中 `accessible` 和 `shelter` 都只出现 `Y`。因此它们在此快照中没有区分能力，首轮不作为输出特征。每次新快照仍应重新检查，不能把这一次的值域永久写死。

Transperth 官方入口是 [Spatial Data Access](https://www.transperth.wa.gov.au/About/Spatial-Data-Access)，GTFS 下载地址为：

```text
https://www.transperth.wa.gov.au/TimetablePDFs/GoogleTransit/Production/google_transit.zip
```

2026-08-21 实际 HEAD 请求成功，文件约 30 MB，`Last-Modified` 为 2026-08-20。该链接是变化中的 feed，正式使用必须保存下载日期和原始 ZIP 快照。

## 4. 首轮 PTA 输出字段

| 输出字段 | 定义 | 限制 |
|---|---|---|
| `pta_nearest_active_stop_distance_m` | 道路地点到最近 `status == Active` 站点的直线平面距离 | 不是步行网络距离，也不是服务频率 |
| `pta_nearest_active_stop_type` | 最近有效站点的源 `stoptype` | 保留原始类别，不自行合并 |
| `pta_active_stops_within_500m` | 500 米点缓冲内有效站点数量 | 500 米是本次测试参数，不是客户已确认标准 |
| `pta_nearest_stop_id` | 最近站点 `stopid` | 用于审计和未来连接 GTFS，不作为连续预测变量 |
| `pta_data_status` | `matched`、`valid_no_stop_within_500m`、`invalid_coordinate` 或 `source_failed` | 最近站点距离存在时，即使 500 米内数量为零也不是请求失败 |

首轮不输出 `accessible`、`shelter`、分时段 service 字段或 GTFS departures。前两者当前无变异；后两类需要先核对数据字典、日期和覆盖，不能仅凭字段名解释。

## 5. Notebook 实施合同

下一次调用本指南时创建：

```text
02_imagery_features/02_03_haoqi_pta_stops.ipynb
```

源快照保存到：

```text
data/external_raw/pta_stops/<YYYY-MM-DD>/
```

唯一特征输出为：

```text
outputs/01_data_preparation/pta-stops/haoqi-49-location-pilot/
pta_stop_features_49_locations.csv
```

Notebook 使用“英文 Markdown → 中文 Markdown → 代码”，说明 source metadata、许可、字段值域和 500 米测试参数，但不另存 metadata 输出。代码先读取图层元数据和记录总数，再下载全量快照，确认分页后的行数等于 count，筛选 `Active`，使用每个地点的本地 UTM CRS计算距离和缓冲区数量，最后保持每个 `location_id` 一行。

## 6. GTFS 后续测试条件

只有 PTA 输出完成后才测试 GTFS。届时必须指定实际参考日期，读取 `stops.txt`、`routes.txt`、`trips.txt`、`stop_times.txt`、`calendar.txt` 和 `calendar_dates.txt`，并正确应用例外服务。GTFS 时间可以超过 `24:00:00`。PTA `stopid` 与 GTFS `stop_id` 必须实测匹配率，不能假定格式完全相同。

如果一个地点不在 Transperth feed 的适用范围内，GTFS 特征应为空并标记 `outside_gtfs_scope`，不能写成零班次。计划班次也不是实时到站、客流或准点率。

## 7. 质量检查与模型划分

运行必须报告源记录总数、Active/Planned 数量、站点类型分布、49 地点的最近距离分布、500 米内零站点比例和人工地图抽查。远距离可能是区域地点的真实结果，但应结合 RA/UCL 分层检查；不能把所有远距离简单视为异常。

特征可以为全部地点预先提取，但若后续比较 400、500、800 米等半径并根据结果表现挑选，半径选择必须在训练折内部完成。多日观测按 `location_id` 成组划分；不能让同一地点的站点环境同时出现在训练与测试。

## 8. 当前结论

PTA Stops 适合做全州 49 地点的首轮公共交通背景测试。GTFS 只作为覆盖内增强，不应为了“有 API”而给多数区域地点制造结构性缺失，也不应把当前无变异的设施字段强行加入模型。
