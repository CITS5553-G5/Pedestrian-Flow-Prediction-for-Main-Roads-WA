# ABS ASGS Remoteness 与 UCL 接入指导

**核对日期：2026-08-21**
**当前状态：官方图层和字段已核验；适合作为下一个 49 地点测试**
**建议用途：描述地点的偏远程度、聚居地归属，并分层检查其他数据源的覆盖差异**

## 1. 当前采用决定

Remoteness Areas（RA）和 Urban Centres and Localities（UCL）回答两个不同问题。RA 是基于服务可达性的偏远类别；UCL 表示地点是否落在 ABS 定义的城市中心或地方性聚居地内。RA 不能被解释成道路质量，UCL 也不等于商业中心、地方政府边界或实际建筑密度。

本项目使用 ASGS Edition 3（2021），与 Mesh Block、SA1 和 2021 Census 保持一致。第一阶段只做点落区分类，不计算“到最近 UCL 的距离”，因为距离到边界还是中心点需要另行定义。

## 2. 49 地点共同输入前置条件

Notebook 读取 `data/test_inputs/pedestrian_observation_locations_49.csv`。文件必须包含 49 个唯一 `location_id`、WGS84 经纬度和坐标来源字段。当前 `Ped_iRAP_merged.csv` 只有 48 个地点，缺少 **North West Coastal Hwy Norseman, SLK 52.5**；应先完成这一地点的坐标关联，不能在指导中假定 49 地点文件已经存在。

## 3. 官方图层与已核验字段

官方定义和下载入口为 [ASGS Edition 3 Remoteness Structure](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/remoteness-structure) 和 [ASGS Edition 3 数据服务](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/data-services-and-apis)。

已在 2026-08-21 核验的 Feature Layers 是：

```text
RA 2021:
https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/RA/MapServer/0

UCL 2021:
https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/UCL/MapServer/0
```

RA 图层实际包含 `ra_code_2021`、`ra_name_2021`、`state_code_2021` 和 `area_albers_sqkm`。UCL 图层实际包含 `ucl_code_2021`、`ucl_name_2021`、`sosr_code_2021`、`sosr_name_2021`、`sos_code_2021`、`sos_name_2021` 和州代码。两个图层都是 `Feature Layer`，最大单次返回 2,000 条；49 个点可直接调用 `/query`。

## 4. 首轮输出字段

| 输出字段 | 定义 | 处理规则 |
|---|---|---|
| `abs_ra_code_2021` | 地点所在 RA 代码 | 保存为字符串 |
| `abs_ra_name_2021` | Major Cities、Inner Regional、Outer Regional、Remote 或 Very Remote 等官方类别 | 分类变量；不要擅自当作等距的 1–5 连续分数 |
| `abs_ucl_code_2021` | 地点所在 UCL 代码 | UCL 外地点保持空值 |
| `abs_ucl_name_2021` | 所在 UCL 名称 | 只在 UCL 内有效 |
| `abs_sosr_name_2021` | 图层记录的 Section of State Range 名称 | 保持官方文本，不自行重新分类 |
| `abs_sos_name_2021` | 图层记录的 Section of State 名称 | 同上 |
| `abs_ra_match_status` | RA 查询状态 | `matched`、`no_match`、`multiple_matches`、`request_failed` |
| `abs_ucl_match_status` | UCL 查询状态 | `inside_ucl`、`outside_ucl`、`multiple_matches`、`request_failed` |

`outside_ucl` 是有意义的真实类别，不是缺失。只有成功收到 UCL 查询响应且 feature 列表为空时，才能写为 `outside_ucl`；请求失败不能伪装成覆盖外。

## 5. Notebook 实施合同

当前个人探索 Notebook 保留在本地，不在团队 Git 仓库中共享。以后若团队决定正式接入该来源，应根据本指南创建新的共享实现并经过评审。

Notebook 使用“英文 Markdown → 中文 Markdown → 代码”，官方定义和字段说明只写在 Markdown，不单独输出 metadata。使用项目相对路径和统一 49 地点输入。每个地点分别查询 RA 与 UCL，并保留两套状态；不要因为 RA 成功就推定 UCL 成功。

唯一输出为：

```text
outputs/01_data_preparation/abs-asgs-remoteness-ucl/haoqi-49-location-pilot/
abs_asgs_remoteness_ucl_features_49_locations.csv
```

代码应当检查输入为 49 个唯一地点、所有坐标为 EPSG:4326、RA 正常情况下每个陆地点唯一匹配、UCL 可以合法为空。不得生成 `data/work` 或额外 metadata/quality 文件。

## 6. 科学使用与质量检查

首轮必须报告 RA 类别分布、UCL 内外数量、接口失败数和多重匹配数。建议把 49 地点按 RA 与 UCL 内外分层，用来检查 Microsoft footprints、PTA Stops、Health 和 Education 在不同环境中的缺失与异常，而不是先假定这些类别必然提高模型表现。

如果某一 RA 类别只有极少地点，不应在模型中为其拟合复杂的独立效应。UCL 名称具有高基数，主要用于审计和分层描述，不应直接 one-hot 后投入只有 49 个地点的模型。

## 7. 与模型划分的关系

RA/UCL 可以在模型划分前为全部地点提取，因为它们不使用结果变量。若用 RA/UCL 帮助构造训练折，应在 49 地点层面分组，保证各折尽量覆盖不同地理环境；不能为了平衡类别而把同一地点的多日观测拆开。任何类别合并方案必须在训练数据中确定并应用到验证/测试数据。

## 8. 当前结论

RA/UCL 是下一步优先级很高的测试来源，因为代码简单、全州解释清楚，并能帮助判断其他数据源在城市、区域和偏远地点上的适用性。它们首先是覆盖审计和上下文变量，不是道路现场环境特征。
