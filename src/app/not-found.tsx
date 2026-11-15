import Link from "next/link";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";

export default function NotFoundPage() {
  return (
    <>
      <Header activeRoute="map" />
      <main
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "32px 16px",
        }}
      >
        <div
          className="card-surface"
          style={{ maxWidth: "460px", textAlign: "center", padding: "32px 26px" }}
        >
          <div style={{ fontSize: "38px", fontWeight: 800, color: "#0b3f70" }}>404</div>
          <h2 style={{ margin: "6px 0 8px", fontSize: "19px", color: "#0f1f33" }}>
            未找到该校园地图页面
          </h2>
          <p style={{ margin: "0 0 18px", fontSize: "13.5px", color: "#516175", lineHeight: 1.65 }}>
            您访问的路径不存在或已调整，请返回双校区三维地图主页继续浏览。
          </p>
          <Link
            href="/"
            style={{
              display: "inline-block",
              padding: "9px 18px",
              borderRadius: "10px",
              background: "#0b3f70",
              color: "#ffffff",
              fontSize: "13.5px",
              fontWeight: 600,
            }}
          >
            返回三维地图主页
          </Link>
        </div>
      </main>
      <Footer />
    </>
  );
}
