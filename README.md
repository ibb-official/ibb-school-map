# 北京市第一六六中学（非官方校园地图）

基于 **Next.js (App Router) + TypeScript** 规划构建的北京市第一六六中学非官方校园地图与空间导览整理项目。

生产环境沿用 `bj166-school-site` 的单主机架构，规划运行在公网 VPS `sofia-vps`（hostname `r-server89187-mls`，IP `108.165.233.143`），由同机的 `edge-caddy` 承担反向代理与 TLS 终结，配合 Cloudflare DNS 与 GitHub Actions 全自动 CI/CD 发布（镜像独立托管于 GHCR，容器端口与网络与 `bj166-web` 完全隔离）。

> **免责声明**：本站为学生协作维护的非官方项目，不代表北京市第一六六中学或任何教育行政部门。地图与建筑信息仅整理自公开资料，不得将本站当作校方正式导览、通知或安防管理依据。

---

## 架构与基础设施拓扑（规划）

```
       [ 公网访客浏览器 ]
               │
               ▼ (HTTPS 443 / 校园地图域名，待分配)
     [ Cloudflare DNS ] (灰云 DNS-Only，指向 sofia-vps: 108.165.233.143)
               │
               ▼
  [ 核心服务节点: sofia-vps ] ─── 网站运行主机 + 流量入口 (hostname r-server89187-mls)
               │ 运行: Docker edge-caddy (监听 80/443，管理证书，reverse_proxy 127.0.0.1:<MAP_PORT>)
               │ 运行: Next.js Standalone 生产容器 ibb-school-map-web (127.0.0.1:<MAP_PORT>)
               │ 目录: /opt/ibb-school-map/ (docker-compose.yml 托管，与 /opt/bj166-site/ 隔离)
```

---

## 仓库结构

当前仓库已完成协作配置与规范骨架，应用代码将通过后续 PR 逐步初始化：

```
├── .github/
│   ├── CODEOWNERS              PR 自动请求全体协作者评审
│   └── workflows/
│       ├── ci.yml              GitHub Actions PR 校验（ESLint + Next.js Build）
│       └── deploy.yml          GitHub Actions 构建镜像、推送 GHCR 与远程部署流水线
├── .dockerignore               Docker 构建排除规则
├── .gitignore                  Git 忽略规则（Node/Next.js/环境变量/临时文件）
├── AGENTS.md                   服务器职责边界、安全红线与团队协作规范（AI/协作者必读）
├── CLAUDE.md                   项目交接说明与当前状态唯一入口
└── README.md                   项目说明与本地开发指引
```

---

## 本地开发（遵循 worktree 协作纪律）

请勿在仓库主目录（`_anchor` 空树分支）直接开发，所有修改均通过独立 worktree 与 Pull Request 完成：

```bash
# 1. 创建任务工作区
wt new 校园地图 <任务slug>
cd ~/dev/.wt/校园地图/<任务slug>

# 2. 安装依赖与本地开发（应用脚手架初始化后）
npm ci
npm run dev

# 3. 提交前校验
npm run lint && npm run build
```

---

## 团队自动化部署与协作（CI/CD）

本项目配置了完整的 GitHub Actions 流水线与评审机制：

- **PR 评审机制（CODEOWNERS）**：任何 PR 创建后会自动向 `@huihiya`、`@guaiqi1964-dev`、`@IGNGserver`、`@hxsx1016`、`@ljy111222` 发送评审请求，需经过校验与评审后合入 `main`。
- **PR 阶段（`.github/workflows/ci.yml`）**：当应用或配置代码变更时，自动运行 `npm ci`、`npm run lint` 与 `npm run build`。
- **main 分支（`.github/workflows/deploy.yml`）**：应用代码合入 `main` 后，自动执行：
  1. 通过 Docker Buildx 进行多阶段构建；
  2. 推送容器镜像到 GitHub Packages：`ghcr.io/ibb-official/ibb-school-map:latest`；
  3. 通过受控 SSH Secret 直连部署目标 `sofia-vps`，触发受控部署与健康检查确认上线。
