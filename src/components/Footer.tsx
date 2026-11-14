import Link from "next/link";

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <span>
          map.bj166zx.cn（非官方整理项目）· 空间比例源自 OpenStreetMap（ODbL）及公开校园建筑资料，仅供外围导览参考。
        </span>
        <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
          <Link href="/about" style={{ color: "#155b96", fontWeight: 600 }}>
            版权出处与建模说明
          </Link>
          <a
            href="https://github.com/ibb-official/ibb-school-map"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "#155b96", fontWeight: 600 }}
          >
            ibb-school-map GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
