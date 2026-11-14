# 校园三维建模管线说明（Blender & glTF 2.0）

本目录保存 `ibb-school-map` 东西两校区 3D 校园模型的代码化真源、坐标数据集与纹理生成脚本。最终 Web 端直接加载 `public/models/west-campus.glb` 与 `public/models/east-campus.glb`。

## 目录结构

```
blender/
├── README.md                          # 本说明文档
├── data/
│   ├── west_metric.json               # 西校区 OSM / 实测米制 ENU 多边形真源
│   └── east_metric.json               # 东校区 OSM / 实测米制 ENU 多边形真源
└── scripts/
    ├── render_textures.swift          # (macOS CoreGraphics) 生成校园招牌/砖纹/跑道图集 PNG
    ├── generate_campus_glb.py         # 纯 Python glTF 2.0 (.glb) 精细生成器（无须安装 Blender）
    └── build_in_blender.py            # Blender 4.x (`bpy`) 原生装配与 glTF 导出脚本
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
  - 东校区：`Campus_Ground_East`, `E-G1`, `E-N1`, `E-N2`, `E-N3`, `E-P1`, `E-B1`, `E-B2`, `E-B3`, `E-B4`, `E-B5`, `Context_East`

## 重建与修改方式

### 方式 A：纯脚本重建（推荐用于无 Blender 环境与精确同步照片细节）

1. （可选，仅更新文字牌/砖瓦纹理时在 macOS 执行）生成纹理图集到临时目录：

```bash
swift blender/scripts/render_textures.swift /tmp/glb_textures
export MAP_TEX_DIR=/tmp/glb_textures
```

2. 重新生成带结构窗框凹进、青砖/红砖材质、膜结构张拉架、LED 门额与顶点环境光遮蔽（AO）的 `.glb` 模型：

```bash
python3 blender/scripts/generate_campus_glb.py
```

### 方式 B：在 Blender 4.x 中交互编辑并导出

```bash
blender --background --python blender/scripts/build_in_blender.py -- --campus all --save-blend
```

打开生成的本地 `.blend`（已被 `.gitignore` 忽略，请勿提交大体积 `.blend` 二进制文件），使用 Blender 的材质、倒角与建筑插件做深化修改后，保留上述 `W-*` / `E-*` 对象名导出至 `public/models/`。

## 隐私与模型边界

- 现阶段聚焦**校园外部围合、门头招牌、户外景观与建筑立面体量**，不做室内教室细节与门禁点位。
- 模型中不出现任何师生个人姓名（历史公开校友“诚·爱”校训雕塑语境与公共纪念石碑除外）、联系方式或监控点位。
