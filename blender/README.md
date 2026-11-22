# 校园三维建模与写实 PBR 管线说明（glTF 2.0 & ArchViz）

本目录保存 `ibb-school-map` 东西两校区 3D 校园模型的代码化真源、坐标数据集、CC0 PBR 贴图拉取与校色管线、法线烘焙脚本与 glTF 网格量化优化工具。最终 Web 端加载 `public/models/west-campus.glb`、`public/models/east-campus.glb` 以及 `public/textures/` 下的 WebP PBR 纹理集。

## 目录结构

```
blender/
├── README.md                              # 本说明文档
├── data/
│   ├── west_metric.json                   # 西校区 OSM / 实测米制 ENU 多边形真源
│   └── east_metric.json                   # 东校区 OSM / 实测米制 ENU 多边形真源
└── scripts/
    ├── fetch_pbr_textures.mjs             # 拉取 Poly Haven CC0 1K PBR (Albedo/Normal/ORM) 并按实景校色输出 WebP
    ├── render_textures.swift              # (macOS CoreGraphics) 生成校园门额/碑刻/校徽招牌基础图集
    ├── render_foliage_and_atlases.swift   # (macOS CoreGraphics) 绘制 6 类植物枝叶卡图集与邻楼视差室内图集
    ├── bake_campus_atlases.mjs            # 为招牌/浮雕/枝叶卡批量烘焙 Sobel 切线空间法线贴图（WebP）
    ├── archviz_geometry.py                # 写实建模模块：米制平铺 UV、浅层 3D 室内教室、植物群落、雕塑/太湖石、夜景灯具
    ├── detailed_props.py                  # 高精度建筑细部与设施库：圆轮自行车、石质坡道护栏、镂空花槽、石砖路缘挡墙、飞檐中式亭、篮架/乒乓球台/拒马/建筑门厅
    ├── generate_campus_glb.py             # 纯 Python glTF 2.0 (.glb) 东西两校区双版本（Enhanced + Classic）统一真源生成器 + 自动产出 src/data/campusLights.ts
    ├── generate_classic_glb.py            # 普通/经典模式快捷入口（委托给 `generate_campus_glb.py --variant classic`，保留 FLOAT32 顶点 + 零双面重复面）
    ├── optimize_glb.mjs                   # @gltf-transform 网格焊点、去重与 KHR_mesh_quantization 压缩（`--preserve-positions` 保留 FLOAT32 顶点防 Z-fighting）
    └── build_in_blender.py                # Blender 4.x (`bpy`) 原生装配与 glTF 导出脚本
```

## 坐标系与节点命名规范（强约定）

Web 端 [src/data/places.ts](../src/data/places.ts) 与 [src/components/CampusScene3D.tsx](../src/components/CampusScene3D.tsx) 依赖 `.glb` 内严格的节点名称与米制尺度：

- **尺度**：`1.0 unit = 1.0 meter`（真实地理米制尺寸）
- **轴向**：`+X` 为东、`+Y` 为高程（glTF Y-up）、`-Z` 为北（等同 ENU `(e, h, -n)`）
- **原点**：
  - 西校区 `(0, 0, 0)` = 同福夹道 3 号门（校门中轴门柱基准）
  - 东校区 `(0, 0, 0)` = 东校区南院双联篮球场中心区域
- **节点命名表**：
  - 西校区：`Campus_Ground_West`, `W-G1`, `W-L1`, `W-L2`, `W-L3`, `W-B1`, `W-B2`, `W-B3`, `W-B4`, `W-B5`, `W-B6`, `W-H1`, `W-R1`, `W-ST1`, `W-MC`, `W-P1`, `W-P2`, `Context_West`
  - 东校区：`Campus_Ground_East`, `E-G1`, `E-N1`, `E-P1`, `E-B1`, `E-B2`, `E-B3`, `E-B4`, `E-B5`, `Context_East`
- **语义材质与灯光通道**：
  - 外立面/地面/屋顶使用 `Mat_PBR_*` 语义材质配米制重复 UV，Web 端由 `src/scene/pbrMaterialSystem.ts` 绑定 15 套 Poly Haven CC0 Albedo + Normal + ORM 贴图与雨湿/积雪动态着色器。
  - 窗玻璃使用物理透明材质 `Mat_Glass_Physical` / `Mat_WarmGlass_Physical`，透过窗户可见真实浅层 3D 室内空间与 7 组独立分时色温灯光（`Mat_IntLight_*` + `Mat_IntGlow_*`）。
  - 户外庭院灯、壁灯与操场高杆投光灯坐标由 `generate_campus_glb.py` 自动同步写入 [src/data/campusLights.ts](../src/data/campusLights.ts)。

## 重建与修改方式

### 方式 A：纯脚本重建（推荐用于无 Blender 环境）

1. （仅当更新 PBR 贴图或校园图集法线时执行，工具依赖安装在 `$HOME/.build/校园地图/tools`）：

```bash
NODE_PATH="$HOME/.build/校园地图/tools/node_modules" node blender/scripts/fetch_pbr_textures.mjs
swift blender/scripts/render_textures.swift /tmp/glb_textures
swift blender/scripts/render_foliage_and_atlases.swift /tmp/foliage_raw
NODE_PATH="$HOME/.build/校园地图/tools/node_modules" node blender/scripts/bake_campus_atlases.mjs /tmp/glb_textures /tmp/foliage_raw
```

2. 同步生成东西两校区增强版与经典版 `.glb` 模型（`--variant all|enhanced|classic`）、更新 [src/data/campusLights.ts](../src/data/campusLights.ts) 与 [src/data/campuses.ts](../src/data/campuses.ts) 版本哈希与体积，并执行 `KHR_mesh_quantization` 网格量化压缩（经典版自动附加 `--preserve-positions`）：

```bash
export MAP_TEX_DIR="$HOME/.build/校园地图/glb_textures"
export NODE_PATH="$HOME/.build/校园地图/tools/node_modules"
python3 blender/scripts/generate_campus_glb.py --campus all --variant all
```

### 方式 B：在 Blender 4.x 中交互编辑并导出

```bash
blender --background --python blender/scripts/build_in_blender.py -- --campus all --save-blend
```

打开生成的本地 `.blend`（已被 `.gitignore` 忽略，请勿提交大体积 `.blend` 二进制文件），保留上述 `W-*` / `E-*` 节点名与 `Mat_PBR_*` / `Mat_IntLight_*` 材质名导出至 `public/models/`。

## 隐私与模型边界

- 浅层室内建模仅呈现通用公共建筑与教学空间轮廓（窗帘、黑板、讲台、课桌阵列、书架、餐桌与走廊吊灯），用于支撑透明玻璃与夜景室内透光效果，**暂不做室内漫游**。
- 模型与贴图中严格禁止出现师生个人姓名（公众历史校友“诚·爱”校训雕塑语境与公共纪念碑除外）、班号、联系方式、门禁密码或校内安防监控点位细节。
- 所有 CC0 PBR 贴图均已在 [src/data/sources.ts](../src/data/sources.ts) 注明 Poly Haven CC0 1.0 来源。
