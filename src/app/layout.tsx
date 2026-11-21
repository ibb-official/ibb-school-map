import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "北京市第一六六中学三维校园地图 | map.bj166zx.cn",
  description:
    "三维校园导览地图：呈现北京市第一六六中学西校区（同福夹道3号）与东校区（东四六条甲44号）的校园建筑与公共空间。",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0b3f70",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="app-shell">{children}</div>
      </body>
    </html>
  );
}
