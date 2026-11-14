import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "北京市第一六六中学三维校园外围地图（非官方）| map.bj166zx.cn",
  description:
    "非官方校园开源三维导览地图：基于实测矢量轮廓与实景照片精细建模，呈现北京市第一六六中学西校区（同福夹道3号）与东校区（东四六条甲44号）校园外围空间。",
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
