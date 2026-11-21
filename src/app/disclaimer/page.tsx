import type { Metadata } from "next";
import { SubpageTopbar } from "@/components/SubpageTopbar";
import { DATA_SOURCES } from "@/data/sources";

export const metadata: Metadata = {
  title: "免责声明 | 北京市第一六六中学三维校园地图",
  description: "本站的项目性质、内容来源与精度、隐私与版权说明，以及公开资料来源。",
};

const LAST_UPDATED = "2026-11-22";

export default function DisclaimerPage() {
  return (
    <div className="subpage-shell">
      <SubpageTopbar activeRoute="disclaimer" />

      <main className="subpage-main">
        <div className="subpage-container">
          <article className="s2-card legal-article">
            <p className="s2-kicker">DISCLAIMER</p>
            <h1 className="s2-h1">免责声明</h1>
            <p className="s2-lead">
              本站是非官方校园地图项目，与北京市第一六六中学及教育行政部门没有隶属、授权或合作关系。
            </p>

            <h2>项目性质</h2>
            <p>
              本站由 ibb-official 同学与校友协作维护，属于公开资料整理与三维可视化实践。站内文字、模型与观点不代表学校立场，也不构成学校发布的信息。
            </p>

            <h2>内容来源与精度</h2>
            <p>
              建筑轮廓、比例与位置整理自 OpenStreetMap、公开影像、公开报道与实景照片；三维模型为示意性还原。受资料时效、建模简化与视角限制，模型可能与校园现状存在差异，本站不保证内容的完整、准确或及时更新。请勿将本站用于入校导航、工程测量、安全管理或其他需要官方数据的用途。
            </p>

            <h2>内容范围</h2>
            <p>
              当前版本以校园建筑外观与公共空间为主，增强版浅层室内仅呈现通用示意性轮廓。本站不展示师生个人联系方式、现役学生可识别肖像，以及门禁、监控、值班安排等安全管理信息。
            </p>

            <h2>隐私与本地存储</h2>
            <p>
              本站为静态页面，不主动收集访问者个人信息；画质档位、增强版开关、触屏虚拟按键与主题偏好仅保存在您的浏览器本地存储（<code>localStorage</code>）中。若图片或文字涉及您的权益，请通过{" "}
              <a
                href="https://github.com/ibb-official/ibb-school-map/issues"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub Issues
              </a>{" "}
              提出，我们会核实并更正或移除。
            </p>

            <h2 id="sources">版权与公开资料来源</h2>
            <p>
              站内三维模型与页面由项目协作者制作；公开资料与照片的版权归原权利人。主要来源如下：
            </p>

            <div className="s2-table-scroll">
              <table className="s2-source-table">
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
                      <td className="s2-td-cat">{row.category}</td>
                      <td>
                        {row.url ? (
                          <a
                            href={row.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {row.name}
                          </a>
                        ) : (
                          <strong>{row.name}</strong>
                        )}
                      </td>
                      <td>{row.coverage}</td>
                      <td className="s2-td-muted">{row.licenseOrNote}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <ul className="s2-meta-list">
              <li>OpenStreetMap：© OpenStreetMap contributors，ODbL 许可。</li>
              <li>Esri World Imagery：用于建模校核，原始影像版权归 Esri 及数据提供方。</li>
              <li>公开报道与照片：版权归原权利人，站内注明出处。</li>
              <li>本站原创模型与页面：转载或复用请先联系项目协作者。</li>
            </ul>

            <h2>声明更新</h2>
            <p>
              本页内容可能随项目调整更新，以当前版本为准。最后更新：{LAST_UPDATED}。
            </p>
          </article>
        </div>
      </main>
    </div>
  );
}
