# 校园地图（ibb-school-map）· 项目规范与架构守则

> 本文件是所有参与本仓库的协作者与 AI 智能体必须遵守的系统架构规范与操作纪律。
> 设备级通用 Git 规范见 `~/.qoder/coder-rules/global-rules.md`。

Collaboration: collaborative
Baseline: main
Default branch: main
Release: Docker / GitHub Packages (GHCR) -> sofia-vps 生产自动化部署
Validation: npm run lint && npm run build & Dockerfile 容器化检查
Worktree: `~/项目/.wt/校园地图/<slug>`

---

## ⚠️ 生产主机职责与边界规范（严禁混淆！）

本项目沿用 `bj166-school-site` 的**单主机部署**模式：应用容器、反向代理与 TLS 终结全部落在同一台公网 VPS 上，不经过内网穿透中转。

### 生产主机 `sofia-vps` (hostname `r-server89187-mls`，公网 IP: 108.165.233.143)
- **唯一角色**：**站点的运行服务器与流量入口**（与 `bj166-school-site` 共享主机，但容器、端口、目录、网络必须完全隔离）。
- **规划组件（首次上线前由 `IGNGserver` 分配并固定）**：
  - `Docker` & `docker compose`：运行 Next.js Standalone 生产容器 `ibb-school-map-web`（仅绑定本机回环地址 `127.0.0.1:<MAP_PORT>`，**禁止复用已被 `bj166-web` 占用的 `3000` 端口**；使用独立网络如 `ibb-school-map_default` 与独立子网，禁止复用 `bj166-site_default` / `172.20.1.0/24`）。
  - `edge-caddy`（Docker Caddy，监听 80/443）：负责校园地图独立域名的反向代理与证书签发，规则为 `reverse_proxy 127.0.0.1:<MAP_PORT>`（待域名确定后接入，不得影响 `bj166zx.cn` 现有规则）。
- **应用部署目录**：`/opt/ibb-school-map/`（存放独立的 `docker-compose.yml`，严禁混入 `/opt/bj166-site/`）。
- **日常运维（由生产机维护者执行）**：
  - 查看站点运行状态：`docker ps` / `docker logs -f ibb-school-map-web`
  - 检查本地健康响应：`curl -I http://127.0.0.1:<MAP_PORT>`
  - 重载反向代理：`docker exec edge-caddy caddy reload --config /etc/caddy/Caddyfile`
- **【严禁操作】**：
  - ❌ **禁止把 `ibb-school-map-web` 的监听端口绑定到公网（`0.0.0.0`）**，对外只能经 `edge-caddy` 的 443；容器端口映射必须保持 `127.0.0.1:<MAP_PORT>:3000`。
  - ❌ **禁止占用或覆盖 `bj166-web` 的 `127.0.0.1:3000` 端口、`/opt/bj166-site/` 目录或 `bj166-site_default` 网络**。
  - ❌ **禁止把本站点的业务代码、构建产物放到其它主机上运行**；`los-vps2`、`debian-web2`（已于 2026-10-30 销毁）与其它 VPS 均不是部署目标。
  - ❌ **禁止改动 `sofia-vps` 上共用的 `new-api` / 账号池或 `bj166-site` 相关配置文件**。

---

## 网络链路与流量拓扑

```
[ 客户端浏览器 ]
       │
       ▼ (HTTPS 443 / 校园地图域名，待分配)
[ Cloudflare DNS ] (灰云 DNS-Only，指向 sofia-vps: 108.165.233.143)
       │
       ▼
[ sofia-vps (应用服务器 + 流量入口) ]
       │ 运行: edge-caddy (监听 80/443 / TLS 证书终结)
       │ Caddyfile 规则: reverse_proxy 127.0.0.1:<MAP_PORT>
       │ 运行: Next.js Standalone 生产容器 ibb-school-map-web (127.0.0.1:<MAP_PORT>)
```

---

## 团队自动化部署（GitHub Actions）与协作流程

本项目采用 **PR 自动化校验 + CODEOWNERS 评审 + main 分支自动上线** 的协作模式，协作者无需关心服务器 SSH 凭据或手动运维：

1. **开发与 PR 提交流程（强制分支 + worktree）**：
   - 禁止在主目录（`~/项目/ibb/校园地图`）或 `main` 分支直接修改、提交代码。
   - 使用 `wt new 校园地图 <slug>` 在 `~/项目/.wt/校园地图/<slug>` 创建独立分支与工作区开发。
   - 提交 Pull Request 后，`.github/CODEOWNERS` 会自动向全体协作者发出评审请求；`.github/workflows/ci.yml` 自动触发 `npm run lint` 与 `npm run build` 校验（应用代码就绪后生效）。
   - 验证通过并经协作者评审批准后，由维护者合并至 `main`。

2. **生产自动交付（main 分支触发）**：
   - 应用代码合入 `main` 后，自动触发 `.github/workflows/deploy.yml` 执行生产发布：
     1. **GitHub Runner** 构建 Next.js Docker 镜像（多阶段构建，Standalone 运行时）。
     2. 将最新镜像推送到 **GitHub Packages (`ghcr.io/ibb-official/ibb-school-map:latest`)**。
     3. 通过本仓库预配置的 SSH Secret 直连 `sofia-vps`，在 `/opt/ibb-school-map/` 拉取最新镜像、重启容器并执行本地健康检查（200 OK 确认上线）。
   - **首次上线前置条件**：需先由 `IGNGserver` 在 `sofia-vps` 分配未占用的 `<MAP_PORT>`、`/opt/ibb-school-map/` 部署目录与 `Caddyfile` 站点块，并在 GitHub 仓库 Secrets 中配置 `VM_SSH_HOST`、`VM_SSH_PORT`、`VM_SSH_USER`、`VM_SSH_KEY`。

3. **权限与边界**：
   - 生产机 `sofia-vps` 仅允许 GitHub Actions 受控通道直连部署，不向协作者分发个人 SSH 凭据，不开放 root，不解除部署密钥的最小权限命令限制。
   - 协作者完成功能或数据编辑的标准出口是 **PR 校验通过并经评审合并**。

---

## 本地开发与代码规范

- **框架**：Next.js (App Router) + TypeScript + 原生 CSS / Tailwind（`output: 'standalone'`）。
- **地图与数据分离**：建筑坐标、点位标注、楼层导览、路线及公开说明等结构化数据集中放在 `src/data/`，与地图渲染和 UI 组件解耦，便于多人协作增删。
- **静态资源规范**：平面底图、SVG 矢量图层与校园实拍图统一放入 `public/`（如 `public/maps/`、`public/images/`）；图片优先转为轻量 WebP/SVG，严禁提交超大未压缩原始文件或无关二进制大文件。
- **空间与构建约束**：本机遵循设备级规范第 5c 节，禁止将构建产物和依赖留在项目卷的无效位置；大型全仓构建与容器构建以 GitHub Actions CI 为准。
- **内容安全与合规红线**：
  - 本项目为**非官方校园地图整理项目**，不代表北京市第一六六中学或任何教育行政部门授权发布。页面仅在站名旁保留极小的 `unofficial` 标记；完整免责声明、隐私说明与资料来源集中放在 `/disclaimer`，首页与页头不重复铺陈边界说明。
  - 仅整理公开且可核验的校园建筑与公共区域信息，**严禁收录**：师生个人姓名（公众历史校友除外）、个人电话/邮箱/宿舍等联系方式、校内安防监控点位、门禁/值班密码、内部管理限制区域细节。
  - **含学生正面肖像且画面出现姓名的照片一律不用**；所有实拍图片与外部来源须明确注明出处与版权许可（如 CC BY-SA 等）。
