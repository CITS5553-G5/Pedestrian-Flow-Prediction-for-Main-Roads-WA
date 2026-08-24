# DPLH Activity Centres 接入指导

**核对日期：2026-08-21**
**当前状态：Activity Centres 与正式 Region Scheme Boundary 图层均已核验**
**建议用途：仅对 Metropolitan/Peel Region Scheme 范围内地点描述规划活动中心接近性**

## 1. 当前采用决定

DPLH-064 是 State Planning Policy 4.2 下的规划活动中心点，不是商店 POI、商业建筑边界或实时经济活动。它只适合回答地点与规划中心体系的关系。

该变量不能用于全州 49 地点的统一比较。首轮必须先用 DPLH-020 Region Scheme Boundary 判断地点是否位于 `MRS` 或 `PRS`，只对范围内地点计算最近中心距离；其余地点写为 `outside_scope` 并保持距离为空。不能用 Activity Centres 点的外接矩形判断覆盖，也不能计算区域地点到 Perth 最近中心的巨大距离。

## 2. 49 地点共同输入前置条件

统一输入为 `data/test_inputs/pedestrian_observation_locations_49.csv`，必须有 49 个唯一地点和 EPSG:4326 坐标。当前合并表只有 48 行，缺少 **North West Coastal Hwy Norseman, SLK 52.5**，应先完成共享地点表。

## 3. 官方来源、真实字段和覆盖边界

官方 Data WA package 是 [State Planning Policy 4.2 Activity centres for Perth and Peel (DPLH-064)](https://catalogue.data.wa.gov.au/dataset/state-planning-policy-4-2-activity-centres-for-perth-and-peel-dplh-064)。2026-08-21 核验时 metadata 更新时间为 2026-08-20。

Activity Centres Feature Layer：

```text
https://public-services.slip.wa.gov.au/public/rest/services/
SLIP_Public_Services/Property_and_Planning/MapServer/69
```

当前 `returnCountOnly` 为 107 个点。实际字段为 `feature_type`、`feature_name`、`policy_number` 和 `layer`；类别分布是 72 个 District、19 个 Secondary、10 个 Strategic、5 个 Specialised 和 1 个 Capital City。

适用范围使用 [Region Scheme — Scheme Boundary (DPLH-020)](https://catalogue.data.wa.gov.au/dataset/region-scheme-scheme-boundary-dop-074)：

```text
https://public-services.slip.wa.gov.au/public/rest/services/
SLIP_Public_Services/Property_and_Planning/MapServer/46
```

该图层实际只有 3 个 polygon，字段为 `descriptio` 和 `reg_scheme`，值分别是 `GBRS`、`MRS` 和 `PRS`。本来源只把 `MRS` 和 `PRS` 作为适用范围；`GBRS` 不属于 SPP 4.2 Perth and Peel 的本次定义。

许可信息存在需要保留的冲突：ArcGIS 图层 description 写有 `License: Creative Commons Attribution`，但 Data WA package 当前显示 `Custom (Active Acceptance)`。Notebook 可以使用公开查询进行测试，但正式再分发前必须保存当次目录 metadata 并确认 active acceptance 条款，不能自行断言某一标准 CC 版本。

## 4. 首轮输出字段

| 输出字段 | 定义 | 处理规则 |
|---|---|---|
| `activity_centre_scope` | `MRS`、`PRS` 或 `outside_scope` | 由 DPLH-020 polygon 精确空间相交决定 |
| `activity_nearest_centre_distance_m` | 范围内地点到最近活动中心点的直线距离 | 范围外保持空值 |
| `activity_nearest_centre_type` | 最近中心的规划等级 | 分类变量，不转成等距 1–5 分数 |
| `activity_nearest_centre_name` | 最近中心名称 | 用于审计和解释 |
| `activity_nearest_centre_policy` | `policy_number` | 用于确认来源政策版本 |
| `activity_data_status` | `matched`、`outside_scope`、`boundary_ambiguous` 或 `source_failed` | 覆盖外不是零距离或缺失错误 |

首轮不计算中心数量、中心面积、商店数量或就业强度。点图层不提供这些信息，而且 107 个规划中心的半径计数需要另外选择有意义尺度。

## 5. Notebook 实施合同

当前个人探索 Notebook 保留在本地，不在团队 Git 仓库中共享。以后若团队决定正式接入该来源，应根据本指南创建新的共享实现并经过评审。

源快照保存到：

```text
data/external_raw/dplh_activity_centres/<YYYY-MM-DD>/
data/external_raw/dplh_region_scheme_boundaries/<YYYY-MM-DD>/
```

唯一特征输出：

```text
outputs/01_data_preparation/dplh-activity-centres/haoqi-49-location-pilot/
dplh_activity_centre_features_49_locations.csv
```

Notebook 使用“英文 Markdown → 中文 Markdown → 代码”。先下载并核对两个图层，再用 MRS/PRS polygon 给地点分配 scope，只为范围内地点使用本地 UTM CRS计算最近距离。每个 `location_id` 必须保留一行，包括 `outside_scope` 地点；不得在计算前直接删除大多数区域样本，也不得创建 `data/work` 或单独 metadata 输出。

## 6. 质量检查与科学限制

运行必须报告 MRS、PRS、outside_scope 地点数，107 个源点的类别分布，多重边界匹配数，范围内最近距离分布和地图抽查。若 49 地点中只有极少数位于 MRS/PRS，指南应如实得出“当前全州模型不适用”，而不是为了保留该数据源给范围外地点填补数值。

活动中心距离表示规划结构背景，不能解释为实际商业活动、人流、停车、建筑密度或公共交通服务。中心名称主要用于审计，不能作为高基数模型特征。

## 7. 与模型划分的关系

范围和距离可以预先对全部 49 地点提取，但该特征很可能存在结构性适用范围。不能把 `outside_scope` 当作普通随机缺失进行均值填补。若仅在 MRS/PRS 子样本中建模，必须把它明确界定为不同研究总体；只有少数地点时不应训练独立模型。

## 8. 当前结论

该来源技术上可行，但对全州样本的优先级低于 RA/UCL、Microsoft footprints、PTA Stops、Education 和 Health。它首先用于检查 Perth/Peel 子样本，而不是强行成为 49 地点统一特征。
