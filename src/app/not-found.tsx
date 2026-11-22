import Link from "next/link";
import { SubpageTopbar } from "@/components/SubpageTopbar";

export default function NotFoundPage() {
  return (
    <div className="subpage-shell">
      <SubpageTopbar activeRoute="not-found" />

      <main className="subpage-main subpage-center">
        <div className="s2-card not-found-card">
          <div className="not-found-code">404</div>
          <h1 className="s2-h2">未找到该校园地图页面</h1>
          <p className="s2-body">
            您访问的路径不存在或已调整，请返回双校区三维地图主页继续浏览。
          </p>
          <Link href="/" className="not-found-cta">
            返回三维地图主页
          </Link>
        </div>
      </main>
    </div>
  );
}
