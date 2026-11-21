import Link from "next/link";

interface FooterProps {
  className?: string;
}

export function Footer({ className = "" }: FooterProps) {
  return (
    <footer className={`site-footer ${className}`.trim()}>
      <div className="site-footer-inner">
        <span>
          © 2026 ibb-official · 同学共建 · 地图数据 © OpenStreetMap contributors（ODbL）
        </span>
        <div className="site-footer-links">
          <Link href="/about">关于项目</Link>
          <Link href="/disclaimer">免责声明</Link>
          <a
            href="https://github.com/ibb-official/ibb-school-map"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
