"use client";

import Link from "next/link";
import { Badge } from "@react-spectrum/s2/Badge";
import { LinkButton, Text } from "@react-spectrum/s2/LinkButton";
import ChevronLeft from "@react-spectrum/s2/icons/ChevronLeft";

interface SubpageTopbarProps {
  activeRoute: "about" | "disclaimer" | "not-found";
}

export function SubpageTopbar({ activeRoute }: SubpageTopbarProps) {
  return (
    <header className="subpage-topbar">
      <div className="subpage-topbar-inner">
        <div className="subpage-topbar-left">
          <LinkButton href="/" variant="secondary" fillStyle="outline" size="S">
            <ChevronLeft />
            <Text>返回三维地图</Text>
          </LinkButton>

          <Link href="/" className="subpage-brand">
            <img src="/maps/map-mark.svg" alt="" width={22} height={22} />
            <span>166 校园地图</span>
            <Badge variant="notice" fillStyle="subtle" size="S">
              非官方
            </Badge>
          </Link>
        </div>

        <nav className="subpage-nav" aria-label="文档页导航">
          <Link
            href="/about"
            className={`subpage-nav-link${activeRoute === "about" ? " subpage-nav-link-active" : ""}`}
          >
            关于项目
          </Link>
          <Link
            href="/disclaimer"
            className={`subpage-nav-link${activeRoute === "disclaimer" ? " subpage-nav-link-active" : ""}`}
          >
            免责声明
          </Link>
          <a
            href="https://bj166zx.cn"
            target="_blank"
            rel="noopener noreferrer"
            className="subpage-nav-link"
          >
            校园文化站点 ↗
          </a>
        </nav>
      </div>
    </header>
  );
}
