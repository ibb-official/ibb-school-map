import Link from "next/link";
import { CompassIcon, ExternalIcon, InfoIcon } from "./Icons";

interface HeaderProps {
  activeRoute: "map" | "about";
}

export function Header({ activeRoute }: HeaderProps) {
  return (
    <>
      <div className="disclaimer-ribbon">
        <div className="disclaimer-ribbon-inner">
          <div className="disclaimer-tag">
            <span className="disclaimer-badge">非官方项目</span>
            <span>
              本项目系学生/校友技术整理与公开建筑外围三维测绘示范（map.bj166zx.cn），不代表北京市第一六六中学或教育行政部门官方发布。
            </span>
          </div>
          <span style={{ opacity: 0.88 }}>
            现阶段仅含校园外部风貌与公共场地，不涉及室内结构、个人隐私及安防点位
          </span>
        </div>
      </div>

      <header className="site-header">
        <div className="site-header-inner">
          <Link href="/" className="brand-link">
            <img
              src="/maps/map-mark.svg"
              alt="校园三维地图徽标"
              className="brand-mark"
              width={34}
              height={34}
            />
            <div>
              <h1 className="brand-title">北京 166 中学 · 三维校园地图</h1>
              <p className="brand-sub">
                西校区（同福夹道3号）× 东校区（东四六条甲44号）外围建筑导览
              </p>
            </div>
          </Link>

          <nav className="site-nav" aria-label="主导航">
            <Link
              href="/"
              className={`nav-link ${activeRoute === "map" ? "nav-link-active" : ""}`}
            >
              <CompassIcon size={15} />
              <span>三维导览</span>
            </Link>
            <Link
              href="/about"
              className={`nav-link ${activeRoute === "about" ? "nav-link-active" : ""}`}
            >
              <InfoIcon size={15} />
              <span>项目说明与图源</span>
            </Link>
            <a
              href="https://bj166zx.cn"
              target="_blank"
              rel="noopener noreferrer"
              className="nav-link"
            >
              <span>校园文化站点</span>
              <ExternalIcon size={13} />
            </a>
          </nav>
        </div>
      </header>
    </>
  );
}
