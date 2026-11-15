import Link from "next/link";
import { CompassIcon, ExternalIcon } from "./Icons";

interface HeaderProps {
  activeRoute: "map" | "about" | "disclaimer";
}

export function Header({ activeRoute }: HeaderProps) {
  return (
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
            <h1 className="brand-title">
              北京 166 中学 · 三维校园地图
              <span className="unofficial" lang="en" title="unofficial project">
                unofficial
              </span>
            </h1>
            <p className="brand-sub">
              西校区（同福夹道3号）× 东校区（东四六条甲44号）校园建筑与空间导览
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
  );
}
