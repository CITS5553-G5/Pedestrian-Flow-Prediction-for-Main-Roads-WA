# ABS Mesh Block 与 SA1 接入指导

**核对日期：2026-08-21**
**当前状态：10 地点 Notebook 已验证；下一步扩展到完整 49 地点**
**建议用途：地点所属统计区域、Mesh Block 土地用途类别、住宅和通常居住人口背景**

## 1. 当前采用决定

本项目继续使用 ASGS Edition 3（2021）与 2021 Census Mesh Block Counts。原因是当前人口和住宅表属于 2021 Census，地理边界、代码和统计表必须使用同一版本。即使已有更新的 ASGS 版本，也不能把新边界代码直接连接到 2021 表。

首轮只提取 Mesh Block 和 SA1 标识、Mesh Block 类别与面积、住宅数和通常居住人口，并计算单位面积住宅数和人口数。暂不接入 SEIFA 或数百个 SA1 Census 字段；这些属于后续有明确研究假设时的独立步骤。

## 2. 49 地点共同输入前置条件

下一版 Notebook 统一读取：

```text
data/test_inputs/pedestrian_observation_locations_49.csv
```

它必须恰好包含 49 个唯一 `location_id`，并至少具有 `location_id`、`road_no`、`slk_km`、`road_name`、`latitude`、`longitude`、`coordinate_crs`、`coordinate_method` 和 `ausrap_segment_match_count`。所有坐标必须是 WGS84（`EPSG:4326`）。

当前原始观测文件夹对应 49 个地点，但 `data/raw/Ped_iRAP_merged.csv` 只有 48 行。缺少的是 **North West Coastal Hwy Norseman, SLK 52.5**。在该地点获得可追溯坐标并生成完整的 49 地点输入前，不应把 48 行文件改名伪装成 49 行。

## 3. 官方来源、接口和真实字段

官方解释来源包括 [2021 Census Mesh Block Counts](https://www.abs.gov.au/census/guide-census-data/mesh-block-counts/2021)、[ASGS Edition 3 Mesh Blocks](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/main-structure-and-greater-capital-city-statistical-areas/mesh-blocks) 和 [ASGS Edition 3 数据服务](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/data-services-and-apis)。

本地原始统计表固定放在：

```text
data/external_raw/Mesh Block Counts, 2021.xlsx
```

小规模地点匹配使用已核验的 ABS Feature Layer：

```text
https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/MB/MapServer/0
```

2026-08-21 实际元数据确认该图层是 `Feature Layer`，单次最大返回 2,000 条，并包含 `mb_code_2021`、`mb_category_2021`、`sa1_code_2021`、`area_albers_sqkm` 等字段。49 个点可以使用 `/query` 逐点测试；无需同时再查询 SA1 图层，因为 MB 图层已经返回 `sa1_code_2021`。

工作簿 `Contents` 表说明 Western Australia 是 `Table 5`；`Explanatory Notes` 给出字段属性。实际统计字段包括 `MB_CODE_2021`、`MB_CATEGORY_NAME_2021`、`AREA_ALBERS_SQKM`、`Dwelling`、`Person` 和 `State`。所有代码字段必须按字符串读取。

## 4. 首轮输出字段

| 输出字段 | 定义 | 使用限制 |
|---|---|---|
| `mb_code_2021` | 地点所在的 2021 Mesh Block 代码 | 标识符，不是连续预测变量 |
| `sa1_code_2021` | 地点所在的 2021 SA1 代码 | 为以后连接 SA1 数据保留 |
| `mb_category_2021` | ABS 设计时确定的主导 MB 类别 | 不是地块级土地用途，也不表示混合度 |
| `mb_area_sqkm_2021` | 所在 MB 的 Albers 面积 | 这是行政统计区域面积，不是道路缓冲区 |
| `mb_dwellings_2021` | 所在 MB 的住宅计数 | 保留原始值以便审查 |
| `mb_persons_usual_resident_2021` | 所在 MB 的通常居住人口 | 不代表道路现场实际行人 |
| `mb_dwellings_per_sqkm_2021` | 住宅数除以 MB 面积 | 小型 Transport 等 MB 可能产生极端密度，必须结合类别解释 |
| `mb_persons_per_sqkm_2021` | 通常居住人口除以 MB 面积 | 同上 |
| `match_status` | `matched`、`no_match`、`multiple_matches` 或 `request_failed` | 缺失和接口失败不能填零 |

原始数量与单位面积指标同时保留是为了可审计性；建模时不能默认将同一信息的原始值、面积和密度全部同时加入小样本模型。

## 5. Notebook 实施合同

下一次调用本指南时，应修改或复用：

```text
02_imagery_features/02_01_haoqi_abs_mesh_block_sa1.ipynb
```

Notebook 保持“英文 Markdown → 中文 Markdown → 代码”的顺序。metadata 和字段官方定义写在 Markdown 中，不生成单独 metadata 输出。代码使用项目根目录自动发现和项目相对路径，不出现个人绝对路径，也不创建 `data/work`。

唯一特征输出为：

```text
outputs/01_data_preparation/abs-mesh-block-sa1/haoqi-49-location-pilot/
abs_mb_sa1_features_49_locations.csv
```

执行顺序是：读取工作簿 metadata；读取并验证 49 地点输入；调用 MB `/query` 获得 MB/SA1 代码；通过 `mb_code_2021` 连接 WA Table 5；计算两个单位面积指标；保存每个地点一行的 CSV。原始工作簿不得改写。

## 6. 必须完成的质量检查

运行必须报告输入行数、唯一地点数、匹配状态分布、重复 MB 代码情况、统计表连接缺失数以及密度极端值。边界点返回多条记录时标记 `multiple_matches`，不能静默取第一条。道路点落入 Transport、Parkland 或其他零人口 MB 是可能的有效结果，不能用周边住宅直觉覆盖官方匹配。

## 7. 与模型划分的关系

对所有 49 个地点提取这些特征本身不会造成目标泄漏，因为过程只使用地点坐标和外部官方数据，不读取行人结果。真正建模时，缺失值处理、缩放、特征选择和任何基于结果变量的筛选必须只在训练折内拟合。同一地点的多日记录必须留在同一折；不能把同一路点的观测随机拆到训练集和测试集。

## 8. 当前结论

这是七个来源中的基础地理连接层，适合优先扩展到 49 个地点。它提供的是“地点所在统计区”的背景，不是 500 米或 800 米邻域人口；如果后续研究确实需要缓冲区人口，应另行设计面积加权或人口栅格方法。
