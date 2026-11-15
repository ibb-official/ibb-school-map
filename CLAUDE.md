# CLAUDE.md — 交接说明（供协作者与 AI 接手用）

> 本文件是本项目**当前状态与工作约定的唯一入口**。任何接手的人或 AI，先读完这一份再动手。
> 最后更新：2026-11-15（Asia/Shanghai）

---

## 一、这是什么

北京市第一六六中学**非官方**三维校园地图项目（规划域名 `https://map.bj166zx.cn`）。技术栈：Next.js 15 (`output: 'standalone'`) + React 19 + TypeScript + Three.js (`three` + `GLTFLoader` + `MapControls` + `RoomEnvironment`) + 代码化 Blender/glTF 2.0 (`.glb`) 建模流水线。

| 项 | 值 |
| --- | --- |
| 仓库 | https://github.com/ibb-official/ibb-school-map |
| 参考项目 | https://github.com/ibb-official/bj166-school-site |
| 本地工作区 | `~/dev/ibb/校园地图`（`_anchor` 空树主目录）；开发一律走 `wt new 校园地图 <slug>` |
| 生产机（规划） | `sofia-vps`（108.165.233.143，hostname `r-server89187-mls`），Docker + `edge-caddy` |
| 部署隔离边界 | 独立目录 `/opt/ibb-school-map/`、独立本机回环端口 `127.0.0.1:${MAP_PORT:-3010}:3000`、独立网段 `172.20.2.0/24`（禁止复用 `bj166-web` 的 `3000` 与 `172.20.1.0/24`） |

**定位红线**：本站是非官方校园地图项目，不代表学校授权发布。站名旁保留极小 `unofficial` 标记，完整免责声明、隐私说明与资料来源见 `/disclaimer`；不在页头或页脚常驻免责声明。

---

## 二、当前状态（2026-11-14）

| 维度 | 状态 |
| --- | --- |
| GitHub 仓库与协作者 | `ibb-official/ibb-school-map` 已配置 `.github/CODEOWNERS` 与 `ci.yml` / `deploy.yml` |
| 3D `.glb` 模型与建模流水线 | **已完成**：`blender/` 脚本可重建 `public/models/west-campus.glb`（17 节点，约 3.2 MB）与 `east-campus.glb`（12 节点，约 2.0 MB），精细刻画门额牌匾、深凹窗格、3×5 金字塔天窗、弧形大坡道、张拉膜主席台与东四传统合院肌理 |
| Web 应用与容器工程 | **已完成**（PR 验证中）：Next.js 15 + Three.js 实时 3D 浏览（含晨光/正午/夕照、射线拾取高亮、导览飞镜、投影点位标签）、2D 矢量 CAD 降级图、1.24 km 双校总览图、`/about` 项目介绍、`/disclaimer` 免责声明与资料来源页、`Dockerfile`（Node 20 Alpine）与 `docker-compose.yml` |
| 生产环境接入 | **待部署配置**：`sofia-vps` `/opt/ibb-school-map/` 部署目录、`MAP_PORT`（默认 `3010`）、`edge-caddy` `map.bj166zx.cn` 站点块及仓库 Deploy Secrets |

---

## 三、核心目录与节点强约定

```
├── .github/workflows/           ci.yml (Node 20 lint+build) / deploy.yml (GHCR+SSH)
├── blender/
│   ├── data/                    west_metric.json & east_metric.json（ENU 米制真源）
│   └── scripts/                 render_textures.swift / generate_campus_glb.py / build_in_blender.py
├── public/
│   ├── images/ref/              7 张经过安全审查与轻量化转换的校园建筑 WebP 照片
│   ├── maps/map-mark.svg        导航徽标
│   └── models/                  west-campus.glb & east-campus.glb（不可随手改名节点）
├── src/
│   ├── data/                    types.ts / campuses.ts / places.ts / tours.ts / sources.ts / map2dGeometry.ts
│   ├── components/              CampusScene3D.tsx / CampusMap2D.tsx / PlaceDetailDrawer.tsx / MapWorkspace.tsx 等
│   └── app/                     page.tsx / about/page.tsx / disclaimer/page.tsx / not-found.tsx / layout.tsx / globals.css
├── Dockerfile                   Node 20 Alpine Standalone 多阶段加固镜像
└── docker-compose.yml           127.0.0.1:${MAP_PORT:-3010}:3000 + ibb-school-map_default (172.20.2.0/24)
```

> **模型节点绑定约定**：`src/data/places.ts` 中每条记录的 `meshNodeName`（`W-G1`..`W-B6`、`E-G1`..`E-B5`）必须与对应 `.glb` 内的对象节点名称严格一致，Three.js 会基于节点挂载独立克隆材质高亮与射线交互。

---

## 四、内容与安全规则（硬性，不可违反）

1. **只呈现公开、可核验的校园建筑与公共空间事实**；当前以建筑外观与户外公共场地为主，室内内容按资料与建模进度逐步补充。
2. **零个人与师生隐私**：教师名录、现役学生姓名、个人联系方式、班级个人映射一律不收（公开历史校友如冰心、谢希德等历史脉络提及除外）。
3. **零安防敏感细节**：监控点位、门禁/值班密码、内部限制区细节禁止建模或标注。
4. **照片安全审查**：含学生正面肖像且画面出现姓名的照片一律不用；每张实拍图均在 `src/data/places.ts` 与 `/disclaimer` 注明拍摄年份及出处。
5. **不直接在 `~/dev` 或 `.wt` 下保留 `node_modules` / `.next`**，所有构建安装在本机 `$HOME/.build/` 内执行。

---

## 五、常用校验与提交流程

```bash
# 同步至本机高速盘构建区运行校验
mkdir -p "$HOME/.build/校园地图/<slug>"
rsync -a --delete --exclude='.git' --exclude='node_modules' --exclude='.next' \
  "$HOME/dev/.wt/校园地图/<slug>/" "$HOME/.build/校园地图/<slug>/"
cd "$HOME/.build/校园地图/<slug>"
npm ci && npm run lint && npm run build
```

- 分支合并策略：本仓库为 `Collaboration: collaborative`，任何功能改动均走 `branch → push → PR → CI 通过 → 人工评审合并`。
