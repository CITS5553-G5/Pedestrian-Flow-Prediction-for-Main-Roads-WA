# WA Department of Health 接入指导

**核对日期：2026-08-21**
**当前状态：官方目录、Feature Layer、字段和值域已实际核验**
**建议用途：到最近开放 Acute Hospital 或 Nursing Post 的接近性背景**

## 1. 当前采用决定

这个来源只记录公立和私立 Acute Hospital 以及 Nursing Post。它不包含全部 GP、诊所、药房、急诊能力、营业时间或服务质量，因此字段必须明确命名为 `health_establishment`，不能笼统解释为“医疗资源可达性”。

49 地点首轮只提取最近开放设施的直线距离、设施类别和 Public/Private 类型。暂不使用床位数，也不计算任意半径内设施数；设施只有约百余个，半径计数很容易大面积为零，而且床位字段需要另外核对统计口径和缺失。

## 2. 49 地点共同输入前置条件

统一输入为 `data/test_inputs/pedestrian_observation_locations_49.csv`，需要 49 个唯一 `location_id` 和 EPSG:4326 坐标。当前合并表只有 48 行，缺少 **North West Coastal Hwy Norseman, SLK 52.5**；开始本来源前应先解决该地点坐标。

## 3. 官方来源与当前真实状态

官方目录为 [Data WA — Health Hospitals (HEALTH-001)](https://catalogue.data.wa.gov.au/dataset/health-establishments)。目录说明数据包括 WA 的公立和私立 acute hospitals 与 nursing posts，并按年度更新。

已在 2026-08-21 确认能够返回真实要素的 Feature Layer 是：

```text
https://public-services.slip.wa.gov.au/public/rest/services/
SLIP_Public_Services/Health_WFS/MapServer/1
```

Data WA 目录列出的 `Health/MapServer/1` 可能是展示服务中的组图层；Notebook 首先读取 `?f=pjson`，必须确认 `type == Feature Layer` 后才能查询。也可以保存官方 GeoJSON 快照：

```text
https://data-downloads.slip.wa.gov.au/HEALTH-001/GeoJSON
```

当前 `returnCountOnly` 返回 153 条。真实字段包括 `estab_id`、`establishm`、`is_open`、`category`、`est`、`no_of_beds`、`longitude`、`latitude` 和 geometry。当前 distinct 查询显示所有可见组合的 `is_open` 都是 `Y`，`category` 只有 `Acute Hospital` 与 `Nursing Post`，`est` 为 `Public` 或 `Private`。这些值域必须在新快照再次检查。

Data WA package 当前没有标准 `license_title`，但 metadata 写有 Government of Western Australia 版权说明。Notebook 可以下载和测试公开数据，但对外再分发源数据时必须保留来源和版权说明，并在交付前重新核对使用条款；不能擅自把它标成 CC BY。

## 4. 首轮输出字段

| 输出字段 | 定义 | 使用限制 |
|---|---|---|
| `health_nearest_establishment_distance_m` | 到最近 `is_open == Y` 设施的直线平面距离 | 不是驾车时间或实际就医时间 |
| `health_nearest_establishment_category` | 最近设施的 `Acute Hospital` 或 `Nursing Post` | 保留官方类别 |
| `health_nearest_establishment_type` | 最近设施的 `Public` 或 `Private` | 不表示个人一定可以获得服务 |
| `health_nearest_establishment_id` | 最近设施 `estab_id` | 用于审计，不作为连续变量 |
| `health_nearest_establishment_name` | 最近设施名称 | 仅用于解释和抽查，通常不进入模型 |
| `health_data_status` | `matched`、`no_open_record`、`invalid_coordinate` 或 `source_failed` | 接口失败和真实缺失必须分开 |

`no_of_beds` 暂不输出。即使字段存在，空值、年度、私立/公立口径和设施类别之间的可比性尚未完成验证。

## 5. Notebook 实施合同

下一次调用本指南时创建：

```text
02_imagery_features/02_04_haoqi_wa_health_establishments.ipynb
```

源快照保存到：

```text
data/external_raw/wa_health_establishments/<YYYY-MM-DD>/
```

唯一特征输出为：

```text
outputs/01_data_preparation/wa-health-establishments/haoqi-49-location-pilot/
wa_health_establishment_features_49_locations.csv
```

Notebook 使用“英文 Markdown → 中文 Markdown → 代码”。metadata、版权、字段和值域只写在说明中，不生成单独 metadata 文件。代码一次下载全州图层，不为 49 个地点重复请求；验证 `is_open`、类别和值域；筛选开放记录；使用每个地点的本地 UTM CRS计算最近距离；输出每个地点一行。

## 6. 质量检查与科学限制

运行必须报告源记录数、开放状态分布、类别与 Public/Private 分布、重复 `estab_id`、空 geometry、WA 坐标范围以及 49 个最近距离的最小值、中位数和最大值。至少人工抽查 metropolitan、regional、remote 各若干地点。

最近医院距离不能解释为医疗需求、服务容量、急诊可用性或实际交通时间。这个变量与偏远程度高度相关是可能的；在只有 49 个地点的模型中，应检查它与 RA/UCL、人口密度等变量的冗余，而不是把多个相似地理代理同时塞入模型。

## 7. 与模型划分的关系

距离可以为全部地点预先计算，因为不使用结果变量。任何对数变换、异常值截断、缺失填补或是否保留该变量的决定，都必须在训练折中确定。同一地点的重复日期不得跨折。

## 8. 当前结论

该来源技术上容易、全州范围明确，但语义较窄，适合作为候选目的地背景。先完成 49 地点测试并查看距离分布，再决定是否进入模型；不能仅因为数据可下载就把它视为核心行人特征。
