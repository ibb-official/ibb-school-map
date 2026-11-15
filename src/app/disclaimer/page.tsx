import Link from "next/link";
import type { Metadata } from "next";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { DATA_SOURCES } from "@/data/sources";

export const metadata: Metadata = {
  title: "免责声明 | 北京市第一六六中学三维校园地图",
  description: "本站的项目性质、内容来源与精度、隐私与版权说明，以及公开资料来源。",
};

const LAST_UPDATED = "2026-11-15";

export default function DisclaimerPage() {
  return (
    <>
      <Header activeRoute="disclaimer" />

      <main style={{ flex: 1 }}>
        <div className="about-container legal-container">
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

          <article className="card-surface legal-body">
            <p className="legal-kicker">DISCLAIMER</p>
            <h2>免责声明</h2>
            <p className="legal-lead">
              本站是非官方校园地图项目，与北京市第一六六中学及教育行政部门没有隶属、授权或合作关系。
            </p>

            <h3>项目性质</h3>
            <p>
              本站由 ibb-official 同学与校友协作维护，属于公开资料整理与三维可视化实践。站内文字、模型与观点不代表学校立场，也不构成学校发布的信息。
            </p>

            <h3>内容来源与精度</h3>
            <p>
              建筑轮廓、比例与位置整理自 OpenStreetMap、公开影像、公开报道与实景照片；三维模型为示意性还原。受资料时效、建模简化与视角限制，模型可能与校园现状存在差异，本站不保证内容的完整、准确或及时更新。请勿将本站用于入校导航、工程测量、安全管理或其他需要官方数据的用途。
            </p>

            <h3>内容范围</h3>
            <p>
              当前版本以校园建筑外观与公共空间为主，室内导览将随资料与建模进度逐步补充。本站不展示师生个人联系方式、现役学生可识别肖像，以及门禁、监控、值班安排等安全管理信息。
            </p>

            <h3>隐私与更正</h3>
            <p>
              本站为静态页面，不主动收集访问者个人信息。若图片或文字涉及您的权益，请通过{" "}
              <a
                href="https://github.com/ibb-official/ibb-school-map/issues"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub Issues
              </a>{" "}
              提出，我们会核实并更正或移除。
            </p>

            <h3 id="sources">版权与来源</h3>
            <p>
              站内三维模型与页面由项目协作者制作；公开资料与照片的版权归原权利人。主要来源如下：
            </p>
            <div style={{ overflowX: "auto", margin: "12px 0 14px" }}>
              <table className="source-table">
                <thead>
                  <tr>
                    <th scope="col">类别</th>
                    <th scope="col">来源名称</th>
                    <th scope="col">对照用途与覆盖范围</th>
                    <th scope="col">许可与说明</th>
                  </tr>
                </thead>
                <tbody>
                  {DATA_SOURCES.map((row) => (
                    <tr key={row.id}>
                      <td
                        data-label="类别"
                        style={{ fontWeight: 600, color: "#0b3f70", whiteSpace: "nowrap" }}
                      >
                        {row.category}
                      </td>
                      <td data-label="来源名称">
                        {row.url ? (
                          <a
                            href={row.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: "#155b96", fontWeight: 600 }}
                          >
                            {row.name}
                          </a>
                        ) : (
                          <strong>{row.name}</strong>
                        )}
                      </td>
                      <td data-label="对照用途与覆盖范围" style={{ color: "#334155", lineHeight: 1.55 }}>
                        {row.coverage}
                      </td>
                      <td data-label="许可与说明" style={{ color: "#516175", lineHeight: 1.55 }}>
                        {row.licenseOrNote}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <ul className="legal-list">
              <li>OpenStreetMap：© OpenStreetMap contributors，ODbL 许可。</li>
              <li>Esri World Imagery：用于建模校核，原始影像版权归 Esri 及数据提供方。</li>
              <li>公开报道与照片：版权归原权利人，站内注明出处。</li>
              <li>本站原创模型与页面：转载或复用请先联系项目协作者。</li>
            </ul>

            <h3>声明更新</h3>
            <p>
              本页内容可能随项目调整更新，以当前版本为准。最后更新：{LAST_UPDATED}。
            </p>
          </article>
        </div>
      </main>

      <Footer />
    </>
  );
}
