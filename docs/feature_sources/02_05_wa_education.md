# WA Department of Education 接入指导

**核对日期：2026-08-21**
**当前状态：2026 Semester 1 XLSX 已实际下载并核验；优先使用最新文件而非 2025 API**
**建议用途：到最近在册学校的距离、学校 sector 和年级范围背景**

## 1. 当前采用决定

首轮使用 Data WA 的 **Current Active Schools Semester 1 2026 (DET-024)** XLSX 或同版本 shapefile，不因为 2025 数据有 ArcGIS API 就使用过时年度。2025 REST 图层只可作为接口试验，不能与 2026 结果静默混合。

更重要的是，官方 package 标题含有 “Public”，但实际 2026 XLSX 的 `Sector` 并不只包含公立学校。2026-08-21 实测 1,152 行中有 817 个 `GOVERNMENT`、317 个 `NON-GOVERNMENT` 和 18 个 `COMMUNITY KINDER`。因此首轮输出应称为“active schools”，并保留真实 `Sector`，不能根据标题把它错误描述成 public-only。

## 2. 49 地点共同输入前置条件

统一输入为 `data/test_inputs/pedestrian_observation_locations_49.csv`，必须有 49 个唯一地点和 EPSG:4326 坐标。当前 `Ped_iRAP_merged.csv` 只有 48 行，缺少 **North West Coastal Hwy Norseman, SLK 52.5**；开始学校距离计算前应补齐其坐标。

## 3. 官方来源、许可和实际表结构

官方 Data WA package 为 [Current Active Schools Semester 1 2026 — DET-024](https://catalogue.data.wa.gov.au/dataset/current-active-schools-semester-1-2026-public-det-024)，metadata 更新时间为 2026-05-13，许可为 [Creative Commons Attribution-NonCommercial 4.0](https://creativecommons.org/licenses/by-nc/4.0/)。正式对外使用必须保留 attribution，并确认项目交付方式符合 NonCommercial 条件。

当前 XLSX 下载地址：

```text
https://catalogue.data.wa.gov.au/dataset/90b5a308-edd6-4814-89f7-1af4df14687b/
resource/d1bec5f9-e284-4484-af4d-cc7a69a55c5a/download/
currentactiveschools20261.xlsx
```

同版本也提供 zipped shapefile。XLSX 实际只有 `ActiveSchools` 工作表，共 1,152 行、19 列；包括 `Code`、`SchoolName`、`Latitude`、`Longitude`、`EducationRegionName`、`Sector`、`RemCode`、`RemoteArea`、`LowYear`、`HighYear`、`TotalPrimaryK_6`、`TotalSecondary7_12` 和 `TotalSchool` 等字段，检查时这些 19 列没有空值。

数据还包含 Christmas Island District High School 和 Cocos Islands District High School。这两所学校由 WA 教育系统管理，但不位于本项目的 Western Australia 道路空间范围。Notebook 应使用正式 WA 州界或明确的项目空间范围筛选，而不是只凭学校名称手工删除。

可查询的旧图层是：

```text
https://public-services.slip.wa.gov.au/public/rest/services/
SLIP_Public_Services/Education/MapServer/12
```

2026-08-21 元数据仍明确命名为 `Current Active Schools Semester 1 2025 - Public (DET-023)`，有 1,151 条，因此不作为首轮正式来源。

## 4. 首轮输出字段

| 输出字段 | 定义 | 使用限制 |
|---|---|---|
| `education_nearest_active_school_distance_m` | 到最近在册、项目范围内学校的直线平面距离 | 不是步行网络距离，也不表示学生必经该道路 |
| `education_nearest_school_sector` | 最近学校的 `GOVERNMENT`、`NON-GOVERNMENT` 或 `COMMUNITY KINDER` | 保留真实源值 |
| `education_nearest_school_low_year` | 最近学校最低年级编码 | 保留 `KIN`、`PKG`、`Y07` 等原编码 |
| `education_nearest_school_high_year` | 最近学校最高年级编码 | 不自行转换成连续教育质量分数 |
| `education_nearest_school_code` | 最近学校 `Code` | 标识符，用于审计 |
| `education_nearest_school_name` | 最近学校名称 | 仅用于解释和地图抽查 |
| `education_data_status` | `matched`、`invalid_coordinate`、`source_empty` 或 `source_failed` | 请求/读取失败不能填零距离 |

`TotalSchool`、`TotalPrimaryK_6` 和 `TotalSecondary7_12` 首轮不作为特征。表中 `TotalSchool` 最小值为 0，而且不同 sector、学校类型和年级结构不完全可比；应另做数据字典和敏感性分析后再决定。

## 5. Notebook 实施合同

下一次调用本指南时创建：

```text
02_imagery_features/02_05_haoqi_wa_education_schools.ipynb
```

固定源文件位置：

```text
data/external_raw/wa_education/2026_S1/currentactiveschools20261.xlsx
```

唯一特征输出：

```text
outputs/01_data_preparation/wa-education-schools/haoqi-49-location-pilot/
wa_education_school_features_49_locations.csv
```

Notebook 使用“英文 Markdown → 中文 Markdown → 代码”。官方 metadata、许可、工作表和字段定义放在说明中，不生成单独 metadata 文件。代码下载或读取固定快照，验证工作表和必需字段，保留 `Code` 为字符串，使用项目 WA 空间范围筛选两处外部领地记录，为每个地点估计本地 UTM CRS并计算最近距离，最后输出每个 `location_id` 一行。

## 6. 质量检查与科学限制

运行必须报告总行数、唯一学校代码数、sector 分布、WA 范围外记录数、坐标异常、最低/最高年级值域和 49 个最近距离分布。至少手工地图抽查不同 sector 和 metropolitan/regional/remote 地点。

最近学校距离只是目的地背景。它不能直接代表上学方式、学生数量、道路穿越需求或学校出入口位置。学校 polygon、校门和道路网络都不在这个点数据中。若后续要研究 school-related pedestrian exposure，需要额外的时间、入口和路网数据。

## 7. 与模型划分的关系

学校距离可在模型划分前为 49 地点统一提取。若以后根据结果比较“最近任意学校”“最近小学”“1 km 内学校数”等定义，定义选择必须放入训练流程，不能看过全部 49 个结果后再选择表现最好的版本。同一地点的多日观测必须成组划分。

## 8. 当前结论

这个来源的最新 2026 文件结构清楚、覆盖广，适合在 Health 之前或之后作为 49 地点候选目的地测试。最重要的修正是：不要把当前文件误称为 public-only，也不要为了使用 API 而退回 2025 年度。
