# CLAUDE.md — 交接说明（供协作者与 AI 接手用）

> 本文件是本项目**当前状态与工作约定的唯一入口**。任何接手的人或 AI，先读完这一份再动手。
> 最后更新：2026-11-14（Asia/Shanghai）

---

## 一、这是什么

北京市第一六六中学**非官方**校园地图整理项目。技术栈沿用 `bj166-school-site` 方案：Next.js (App Router) + TypeScript + Docker (Standalone) + Caddy。

| 项 | 值 |
| --- | --- |
| 仓库 | https://github.com/ibb-official/ibb-school-map |
| 参考项目 | https://github.com/ibb-official/bj166-school-site |
| 本地工作区 | `~/dev/ibb/校园地图`（`_anchor` 空树主目录）；开发一律走 `wt new 校园地图 <slug>` |
| 生产机（规划） | `sofia-vps`（108.165.233.143，hostname `r-server89187-mls`），Docker + `edge-caddy` |
| 部署隔离边界 | 独立目录 `/opt/ibb-school-map/`、独立本机端口 `127.0.0.1:<MAP_PORT>`（禁止复用 `bj166-web` 的 `3000`） |

**定位红线**：本站是非官方校园资料与导览整理项目，不代表学校授权发布。页面必须保留“非正式 / 非官方”标识与免责声明。

---

## 二、当前状态（2026-11-14）

| 维度 | 状态 |
| --- | --- |
| GitHub 仓库 | 已创建 `ibb-official/ibb-school-map`（Public） |
| 协作者与评审 | 已配置 `.github/CODEOWNERS`（`@huihiya @guaiqi1964-dev @IGNGserver @hxsx1016 @ljy111222`） |
| CI/CD 流水线 | 已配置 `.github/workflows/ci.yml` 与 `.github/workflows/deploy.yml`（带 `paths` 过滤，应用代码落地后自动激活） |
| 规范文档 | 已完成 `AGENTS.md`、`CLAUDE.md`、`README.md` |
| 应用脚手架 | **待初始化**（尚未写入 `package.json`、`src/`、`Dockerfile`、`docker-compose.yml`） |
| 生产环境配置 | **待分配**：`<MAP_PORT>`、域名、`/opt/ibb-school-map/` 及仓库 SSH Deploy Secrets |

---

## 三、规划代码结构

后续初始化 Next.js 应用时，参考 `bj166-school-site` 保持结构清晰：

```
├── .github/
│   ├── CODEOWNERS               PR 自动请求全体协作者评审
│   └── workflows/
│       ├── ci.yml               PR 阶段自动运行 lint 与 build
│       └── deploy.yml           main 分支构建 GHCR 镜像并部署至 sofia-vps
├── src/
│   ├── app/
│   │   ├── layout.tsx           全局布局、元数据与免责页眉/页脚
│   │   ├── page.tsx             校园地图主视图（交互导览 / 建筑索引 / 搜索）
│   │   ├── globals.css          全局样式（兼顾移动端触控与响应式布局）
│   │   └── ...                  关于本站 / 来源说明 / 404 等页面
│   ├── components/              地图画布、图层控制、点位详情抽屉、检索栏等组件
│   └── data/                    建筑、楼层、设施、路线、来源说明等结构化数据
├── public/                      校徽、矢量底图、建筑实拍图（轻量 WebP/SVG）
├── Dockerfile                   Next.js Standalone 多阶段镜像构建定义
├── docker-compose.yml           sofia-vps 生产容器编排（独立端口与网络）
├── next.config.mjs              Next.js 运行时配置（output: 'standalone'）
├── tsconfig.json
└── AGENTS.md                    服务器边界与项目规范
```

---

## 四、内容与数据规则（硬性，不可违反）

1. **只写公开、可核验的校园空间事实**。不臆测未公开的建筑用途或内部布局。
2. **不发布个人与师生隐私**：教师名录、学生姓名、个人联系方式（电话、邮箱、微信号）、班主任/办公室个人对应信息一律不收。
3. **不标注内部安防与敏感管理设施**：监控探头位置、门禁控制、围墙薄弱点、值班室/财务等内部管理敏感细节不得绘制或标注。
4. **含学生正面肖像且画面出现姓名的照片不用**。所有实拍图与参考资料须注明出处与许可协议。
5. **非官方免责声明常驻**：页面顶部或底部必须明确提示“非学校官方网站 / 仅作公开资料整理导览”。

---

## 五、部署与提交流程

1. **创建任务 worktree**：
   ```bash
   wt new 校园地图 <任务slug>
   cd ~/dev/.wt/校园地图/<任务slug>
   ```
2. **本地校验**（应用初始化后）：
   ```bash
   npm run lint && npm run build
   ```
3. **提交与 PR**：
   - 推送任务分支：`git push -u origin agent/<任务slug>`
   - 创建 PR：`gh pr create`（必须写明改动范围、验证命令与真实结果）
   - 等待 `CI (PR Validation)` 通过且经 `CODEOWNERS` 中协作者评审后合并（不直推 `main`）。
4. **生产发布链路**：
   - 代码合入 `main` → GitHub Actions 构建镜像推送至 `ghcr.io/ibb-official/ibb-school-map:latest` → SSH 至 `sofia-vps`（校验 hostname 为 `r-server89187-mls`）→ 更新容器并健康检查。
   - **安全边界**：不向协作者分发服务器公钥，不开放 root，不把临时排查命令长期塞进 `deploy.yml`。

---

## 六、待办（按优先级）

1. **确定基础设施参数**（由 `IGNGserver` 完成）：
   - 在 `sofia-vps` 分配未占用的本地端口 `<MAP_PORT>`（避开 `3000`）、独立 Docker 子网与 `/opt/ibb-school-map/`；
   - 确定域名并在 Cloudflare DNS 与 `edge-caddy` 中接入；
   - 在 GitHub 仓库配置 Deploy Secrets（`VM_SSH_HOST`、`VM_SSH_PORT`、`VM_SSH_USER`、`VM_SSH_KEY`）与 GHCR 拉取凭据。
2. **初始化 Next.js 应用骨架**（单独走 PR）：
   - 初始化 `package.json`、`tsconfig.json`、`eslint.config.mjs`、`next.config.mjs`、`Dockerfile`、`docker-compose.yml`；
   - 建立基础页面、非官方免责声明与地图数据 schema。
3. **采集与核验校园公开地理/建筑资料**：
   - 整理公开校区分布、主要教学楼/功能区/文化地标与合规实拍图。
