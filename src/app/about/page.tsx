import Link from "next/link";
import type { Metadata } from "next";
import { SubpageTopbar } from "@/components/SubpageTopbar";
import { CAMPUSES, DUAL_CAMPUS_LINK } from "@/data/campuses";

export const metadata: Metadata = {
  title: "关于项目 | 北京市第一六六中学三维校园地图",
  description: "ibb-school-map 三维校园地图的项目介绍、双校区空间尺度与建模说明。",
};

export default function AboutPage() {
  return (
    <div className="subpage-shell">
      <SubpageTopbar activeRoute="about" />

      <main className="subpage-main">
        <div className="subpage-container">
          <section className="s2-card">
            <p className="s2-kicker">ABOUT · MAP.BJ166ZX.CN</p>
            <h1 className="s2-h1">关于本三维校园地图项目</h1>
            <p className="s2-lead">
              本项目由 ibb-official 同学与校友协作维护，利用开源 WebGL / glTF 2.0
              与代码化三维建筑生成管线，面向关心母校与东城胡同风貌的访客，细致呈现北京市第一六六中学
              <strong>西校区（同福夹道3号）</strong>与
              <strong>东校区（东四六条甲44号）</strong>的校园建筑体量、校园广场、林荫院落与空间动线。
            </p>
          </section>

          <section className="s2-grid-2">
            {(["west", "east"] as const).map((cid) => {
              const meta = CAMPUSES[cid];
              return (
                <div key={cid} className="s2-card">
                  <div className="s2-kicker">{meta.roleLabel}</div>
                  <h2 className="s2-h2">{meta.name}</h2>
                  <p className="s2-body">{meta.summary}</p>
                  <ul className="s2-meta-list">
                    <li>位置：{meta.address}</li>
                    <li>规模：{meta.approxAreaSqm}</li>
                    <li>周边街道：{meta.surroundingStreets.join(" · ")}</li>
                    <li>公共交通：{meta.nearestTransit.join("；")}</li>
                  </ul>
                </div>
              );
            })}
          </section>

          <section className="s2-card">
            <h2 className="s2-h2">双校区同城尺度与双引擎渲染架构</h2>
            <p className="s2-body">
              两校区直线相距约 <strong>{DUAL_CAMPUS_LINK.straightLineKm} 公里</strong>（东偏{" "}
              {DUAL_CAMPUS_LINK.deltaEastMeters} 米，北偏 {DUAL_CAMPUS_LINK.deltaNorthMeters}{" "}
              米）。三维场景采用 <strong>1:1 米制 ENU 工程坐标</strong>（1 Three.js 单位 = 1.0
              米），依据 OpenStreetMap 与正射航拍复核多边形底座起模，对照多角度实景照片精细还原层间饰带、深凹铝框窗格、C
              座屋顶梁格构架、弧形大坡道与张拉膜主席台。
            </p>
            <p className="s2-body" style={{ marginBottom: 0 }}>
              前端默认加载轻量自包含的<strong>经典普通版模型</strong>（零外部贴图与后处理负担，首屏极速流畅）；需要写实质感时，可在右上角设置中随时开启
              <strong>增强版地图</strong>（按画质档位严格按需加载 Poly Haven CC0 PBR
              贴图、24 小时天光天气、N8AO 环境遮蔽与 GPU 路径追踪）。
            </p>
          </section>

          <footer className="subpage-footer">
            <span>
              © 2026 ibb-official · 非官方同学共建 · 地图数据 © OpenStreetMap contributors（ODbL）
            </span>
            <div className="subpage-footer-links">
              <Link href="/disclaimer">免责声明与数据来源</Link>
              <a
                href="https://github.com/ibb-official/ibb-school-map"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
            </div>
          </footer>
        </div>
      </main>
    </div>
  );
}
