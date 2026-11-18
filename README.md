# 北京市第一六六中学三维校园地图（`map.bj166zx.cn`）

基于 **Next.js 15 (App Router) + TypeScript + Three.js + glTF 2.0 (`.glb`) / Blender** 构建的北京市第一六六中学双校区三维校园导览地图项目，涵盖**西校区（同福夹道3号校本部）** 与 **东校区（东四六条甲44号毕业年级部）**，当前以校园建筑体量、校门牌匾与户外公共空间为主，室内导览将随资料与建模进度逐步补充。

生产环境沿用 `bj166-school-site` 的单主机架构，部署于公网 VPS `sofia-vps`（hostname `r-server89187-mls`，IP `108.165.233.143`），由 `edge-caddy` 负责反向代理与 TLS 终结，与 `bj166-web` 端口及容器网络完全隔离。

> **免责声明**：本站为非官方项目，不代表北京市第一六六中学或任何教育行政部门。完整免责声明、隐私说明与全部资料来源见 `https://map.bj166zx.cn/disclaimer`。

---

## 核心特性

1. **双校区独立精细 3D 校园模型（`public/models/*.glb`）**：
   - **西校区（15 个可交互点位）**：同福夹道3号古铜悬挑门额与 LED 校名牌匾、“慎独”巨石与校友雕塑庭院、南院弧面教学综合楼、5 层 B 座斜翼与“B 教学楼”红书标识、C 座 3×5 金字塔玻璃天窗矩阵、白色弧形无障碍大坡道与雪松、东北外挂折返钢构楼梯塔、百草园方亭、北区塑胶操场与三跨白色张拉膜主席台、青砖灰瓦二层挑廊 D 座等。
   - **东校区（8 个可交互点位）**：东四六条甲44号深红门楼（LED 屏、折叠门、不锈钢校牌）与青砖门房、白底红圈“5”限速标线、约 6 m × 56 m 北巷红砖通道与两侧院墙平房、南院两片 13.6 × 25 m 球场（链式围网、灯杆、4 副篮架）与 5 栋绿/灰屋顶教学建筑。
2. **数据与三维场景解耦**：所有空间坐标、建筑描述、相机机位、精选巡航路径与图源声明均独立维护于 `src/data/`，`.glb` 模型节点通过精准名称（`W-*` / `E-*`）与数据绑定。
3. **晨光 / 正午 / 夕照三时段实时光照 + 交互式 2D 矢量平面降级 + 1.24 km 双校同城空间总览**。
4. **公开摄影实拍对比抽屉**：每个重点点位在侧边栏联动显示年份实拍照片与明确版权出处。

---

## 仓库结构

```
├── .github/
│   ├── CODEOWNERS                    PR 自动请求全体协作者评审
│   └── workflows/
│       ├── ci.yml                    PR 校验（Node 20: npm ci / lint / build）
│       └── deploy.yml                main 分支构建 GHCR 镜像并部署 sofia-vps
├── blender/
│   ├── README.md                     Blender / glTF 建模坐标系与规范
│   ├── data/                         东西校区 ENU 米制 OSM 真源坐标 JSON
│   └── scripts/
│       ├── render_textures.swift     (macOS) 招牌、砖瓦、跑道图集渲染脚本
│       ├── generate_campus_glb.py    无须 Blender 的高精度 glTF 2.0 (.glb) 生成器
│       └── build_in_blender.py       Blender 4.x (`bpy`) 装配及 glTF 导出脚本
├── public/
│   ├── images/ref/                   经合规排查并转换后的轻量化 WebP 校园照片
│   ├── maps/map-mark.svg             站点图标
│   └── models/                       west-campus.glb / east-campus.glb
├── src/
│   ├── app/                          首页地图工作台 (/)、项目介绍 (/about)、免责声明与资料来源 (/disclaimer)、404
│   ├── components/                   CampusScene3D、CampusMap2D、PlaceDetailDrawer 等
│   └── data/                         campuses.ts / places.ts / tours.ts / sources.ts / map2dGeometry.ts
├── Dockerfile                        Node 20 Alpine 多阶段最小化生产镜像
├── docker-compose.yml                sofia-vps 隔离容器编排 (127.0.0.1:3010 -> 3000)
├── next.config.mjs                   Next.js Standalone + `.glb` MIME 响应头
├── AGENTS.md                         服务器职责边界与内容安全红线
└── CLAUDE.md                         协作者交接说明入口
```

---

## 本地开发（遵循 worktree 与本机构建区规范）

主目录（`_anchor` 空树分支）不直接修改或安装依赖；所有开发通过独立 `wt` 工作区与本机构建区执行：

```bash
# 1. 创建独立开发 worktree
wt new 校园地图 <任务slug>
cd ~/dev/.wt/校园地图/<任务slug>

# 2. 若需重建 3D .glb 模型（支持纯 Python 或 Blender 4.x）
python3 blender/scripts/generate_campus_glb.py

# 3. 同步至本机高速盘构建区执行安装、校验与测试（避免在项目卷写入 node_modules/.next）
mkdir -p "$HOME/.build/校园地图/<任务slug>"
rsync -a --delete --exclude='.git' --exclude='node_modules' --exclude='.next' ./ "$HOME/.build/校园地图/<任务slug>/"
cd "$HOME/.build/校园地图/<任务slug>"
npm ci && npm run lint && npm run build
```
