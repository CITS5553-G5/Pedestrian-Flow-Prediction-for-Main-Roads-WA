# Microsoft Global Building Footprints 接入指导

**核对日期：2026-08-21**
**当前状态：官方 2026-07-24 索引、澳大利亚分区和 10 地点 Notebook 已端到端验证**
**建议用途：统一地点缓冲区内识别出的建筑数量与建筑覆盖程度**

## 1. 当前采用决定

Microsoft Global ML Building Footprints 是机器学习从影像生成的建筑多边形，不是地籍、现场清查或法定建筑名录。它适合在固定空间单位内统计“识别出的建筑 footprint 数量和覆盖面积”，但不能回答建筑用途、住户数量、停车场、入口、是否空置或步行可达性。

49 地点测试沿用已经验证的 500 米点缓冲方法。500 米是当前透明的 smoke-test 参数，不是客户确认要求、步行路网范围或沿道路 corridor。以后可以比较尺度或换成道路几何，但不能根据全部结果变量挑选表现最好的半径。

## 2. 49 地点共同输入前置条件

统一输入为 `data/test_inputs/pedestrian_observation_locations_49.csv`，需要 49 个唯一 `location_id`、EPSG:4326 坐标和坐标来源字段。当前合并表只有 48 行，缺少 **North West Coastal Hwy Norseman, SLK 52.5**；应先补齐该地点。

现有 10 地点实现位于：

```text
02_imagery_features/02_07_haoqi_microsoft_building_footprints.ipynb
```

它已经成功选择和下载 10 个 Australia quadkey 分区，解析 226,009 条 footprint，并为 10 个地点生成完整特征。扩展到 49 地点应复用该实现，不重新设计一套不兼容流程。

## 3. 官方来源、版本和真实格式

官方仓库是 [Microsoft GlobalMLBuildingFootprints](https://github.com/microsoft/GlobalMLBuildingFootprints)，许可为 [CDLA Permissive 2.0](https://cdla.dev/permissive-2-0/)。官方说明全球数据来自 2014–2024 年间影像，不同地点的影像时间与检测质量可能不同。

本项目固定使用 **2026-07-24** release index：

```text
https://bfppub.blob.core.windows.net/%24web/2026-07-24/dataset-links.csv
```

2026-08-20 实际下载确认索引字段为 `Location`、`QuadKey`、`Url`、`Size` 和 `UploadDate`。数据按国家与 Bing zoom level 9 quadkey 分区；`QuadKey` 必须按字符串保存。

分区文件名以 `.csv.gz` 结尾，但实际内容是每行一个 GeoJSON Feature。抽查 Australia 记录确认顶层包含 `type`、`properties` 和 `geometry`；`properties` 中可见 `height` 和 `confidence`，而真实样本存在 `height = 0` 与 `confidence = -1`。因此首轮只使用 polygon geometry，暂不把高度或置信度强行解释成可靠特征。

这个来源没有逐地点查询 API。正确接入方法是读取官方索引、计算所需 quadkey、只下载相关分区并在本地精确裁剪。旧的 `minedbuildings.../global-buildings/dataset-links.csv` 地址和 `buildings-coverage.geojson` 不再作为当前实施依据。

## 4. 首轮输出字段

| 输出字段 | 定义 | 科学解释 |
|---|---|---|
| `ms_building_count_500m` | 与精确 500 米缓冲区有正面积交集的源 footprint 记录数 | 会受模型把建筑合并或拆分的影响 |
| `ms_building_count_per_sqkm_500m` | 记录数除以实际缓冲区面积（km²） | 单位面积建筑出现频率 |
| `ms_building_footprint_area_m2_500m` | 裁剪到缓冲区内的 footprint 并集面积 | 使用并集避免重叠检测重复计地面面积 |
| `ms_building_coverage_ratio_500m` | footprint 并集面积除以缓冲区面积 | 标准化的识别建筑覆盖程度 |
| `ms_building_data_status` | `complete_with_buildings`、`complete_no_detected_buildings` 或 `source_tile_not_listed` | 无检测不等于现实中无建筑 |

在所有地点缓冲面积相同时，count 与 count per km² 是固定倍数，area 与 coverage ratio 也是固定倍数。原始值保留用于审计，建模时每一对只选一个，避免完全共线。

首轮不再输出最近建筑距离。要得到缓冲区以外的真实最近建筑，需要确保相邻分区选择范围足够；对当前“周边建筑程度”问题，数量与覆盖率含义更直接。

## 5. Notebook 实施合同

将现有 Notebook 输入从 10 地点改为完整 49 地点，并把唯一输出改为：

```text
outputs/01_data_preparation/microsoft-building-footprints/haoqi-49-location-pilot/
microsoft_building_footprints_features_49_locations.csv
```

固定源缓存为：

```text
data/external_raw/microsoft_building_footprints/2026-07-24/dataset-links.csv
data/external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/
```

Notebook 保持“英文 Markdown → 中文 Markdown → 代码”，metadata、许可和字段定义写在 Markdown，不另存 metadata/manifest 输出。代码用每个地点本地 UTM CRS建立 500 米 buffer，将其 bounding box 转成 zoom 9 quadkeys，从索引筛选 `Location == Australia`，只下载所需瓦片，解析 geometry，并用精确 buffer intersection 统计。

不需要新增 `mercantile` 依赖；已验证 Notebook 内部的 Bing tile/quadkey 函数足以完成选择。下载必须先写 `.part` 临时文件，成功后再替换正式缓存，避免中断文件被误认为完整源数据。

## 6. 质量检查与科学限制

运行必须报告 49 个输入地点、所需唯一 quadkey 数、索引未列出数量、下载分区数、读取 footprint 总数、状态分布和四个数值特征范围。至少按 RA/UCL 环境类型抽查若干 footprint 与地点关系。若源 tile 未列出，应返回空特征和状态，不能自动赋零。

每一个零 footprint 结果都只能解释为“该 release 在该测试 buffer 内无检测记录”。城市样本表现好不能证明偏远样本完整。模型使用前应重点审查 remote/very remote 地点的漏检、位置偏移和影像年代差异。

## 7. 与模型划分的关系

footprint 特征可以先为全部 49 地点提取，因为不读取目标变量。若根据目标结果挑选 250、500、800 米半径，或者在 count 和 coverage 中选择表现最好的字段，这些选择必须在训练折内完成。多日观测必须按 `location_id` 成组划分。

## 8. 当前结论

这是回答“地点周围识别到多少建筑”的首选来源。当前技术路径已经真实运行，不需要回到旧指导中的过度设计。下一步只需补齐 49 地点共享输入并扩展现有 Notebook，同时保留对机器学习检测质量和零值解释的限制。
