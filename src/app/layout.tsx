import type { Metadata, Viewport } from "next";
import "@react-spectrum/s2/page.css";
import "./globals.css";
import { SpectrumProvider } from "@/components/SpectrumProvider";

export const metadata: Metadata = {
  title: "北京市第一六六中学三维校园地图 | map.bj166zx.cn",
  description:
    "全屏交互式三维校园地图：呈现北京市第一六六中学西校区（同福夹道3号）与东校区（东四六条甲44号）的校园建筑与公共空间。",
  icons: {
    icon: "/maps/map-mark.svg",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#111111" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" data-color-scheme="light" suppressHydrationWarning>
      <body>
        <SpectrumProvider>{children}</SpectrumProvider>
      </body>
    </html>
  );
}
