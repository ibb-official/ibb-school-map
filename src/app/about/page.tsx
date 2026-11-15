import Link from "next/link";
import type { Metadata } from "next";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { CAMPUSES, DUAL_CAMPUS_LINK } from "@/data/campuses";

export const metadata: Metadata = {
  title: "关于项目 | 北京市第一六六中学三维校园地图",
  description: "ibb-school-map 三维校园地图的项目介绍、双校区空间尺度与建模说明。",
};

export default function AboutPage() {
  return (
    <>
      <Header activeRoute="about" />

      <main style={{ flex: 1 }}>
        <div className="about-container">
          <div style={{ marginBottom: "18px" }}>
            <Link
              href="/"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "13px",
                fontWeight: 600,
                color: "#155b96",
              }}
            >
              ← 返回三维校园交互地图
            </Link>
          </div>

          <section className="card-surface" style={{ marginBottom: "18px" }}>
            <div style={{ fontSize: "12.5px", color: "#516175", marginBottom: "8px" }}>
              map.bj166zx.cn（ibb-school-map）
            </div>

            <h2 style={{ margin: "0 0 10px", fontSize: "21px", color: "#0b3f70" }}>
              关于本三维校园地图项目
            </h2>

            <p style={{ margin: 0, fontSize: "14px", lineHeight: 1.75, color: "#1f2d3d" }}>
              本项目由 ibb-official 同学与校友协作维护，利用开源 WebGL/glTF 2.0
              与代码化三维建筑生成管线，面向关心母校与东城胡同风貌的访客，细致还原北京市第一六六中学
              <strong>西校区（同福夹道3号）</strong> 与 <strong>东校区（东四六条甲44号）</strong> 的校园建筑体量、校园广场、林荫院落与空间动线。
            </p>
          </section>

          <section
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))",
              gap: "16px",
              marginBottom: "18px",
            }}
          >
            {(["west", "east"] as const).map((cid) => {
              const meta = CAMPUSES[cid];
              return (
                <div key={cid} className="card-surface">
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "#8a6d3b" }}>
                    {meta.roleLabel}
                  </div>
                  <h3 style={{ margin: "4px 0 8px", fontSize: "17px", color: "#0b3f70" }}>
                    {meta.name}
                  </h3>
                  <p style={{ margin: "0 0 10px", fontSize: "13px", lineHeight: 1.65, color: "#334155" }}>
                    {meta.summary}
                  </p>
                  <ul
                    style={{
                      margin: 0,
                      paddingLeft: "18px",
                      fontSize: "12.5px",
                      lineHeight: 1.7,
                      color: "#475569",
                    }}
                  >
                    <li>位置：{meta.address}</li>
                    <li>规模：{meta.approxAreaSqm}</li>
                    <li>周边街道：{meta.surroundingStreets.join(" · ")}</li>
                    <li>公共交通：{meta.nearestTransit.join("；")}</li>
                  </ul>
                </div>
              );
            })}
          </section>

          <section className="card-surface" style={{ marginBottom: "18px" }}>
            <h3 style={{ margin: "0 0 8px", fontSize: "17px", color: "#0b3f70" }}>
              双校区同城尺度与三维建模精度
            </h3>
            <p style={{ margin: "0 0 10px", fontSize: "13.5px", lineHeight: 1.7, color: "#334155" }}>
              两校区直线相距约 <strong>{DUAL_CAMPUS_LINK.straightLineKm} 公里</strong>（东偏 {DUAL_CAMPUS_LINK.deltaEastMeters} 米，北偏 {DUAL_CAMPUS_LINK.deltaNorthMeters} 米）。三维场景采用 <strong>1:1 米制 ENU 工程坐标</strong>（1 Three.js 单位 = 1.0 米），依据 OpenStreetMap 与手绘/正射复核多边形底座起模，并对照多角度实景照片独立建模建筑层间饰带、-0.20m 深凹铝框窗格、C 座屋顶开敞矩形梁格构架、三次贝塞尔弧形大坡道与坐北朝南张拉膜主席台，最终烘焙导出轻量级 glTF 2.0 二进制模型（.glb）嵌入门牌招牌与材质图集，首屏即可在主流桌面与移动端浏览器中流畅旋转与漫游。
            </p>
            <p style={{ margin: 0, fontSize: "13px", color: "#516175" }}>
              协作者亦可在仓库的 blender/ 目录下运行 build_in_blender.py（Blender 4.x bpy 脚本）或 generate_campus_glb.py 对单个建筑对象继续精修，并同步更新 src/data/places.ts。
            </p>
          </section>

          <p style={{ margin: 0, fontSize: "12px", color: "#718196" }}>
            完整说明与资料来源见{" "}
            <Link href="/disclaimer" style={{ color: "#155b96", fontWeight: 600 }}>
              免责声明
            </Link>
            。
          </p>
        </div>
      </main>

      <Footer />
    </>
  );
}
