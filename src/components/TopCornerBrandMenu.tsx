"use client";

import Link from "next/link";
import { ActionButton } from "@react-spectrum/s2/ActionButton";
import { Badge } from "@react-spectrum/s2/Badge";
import { Menu, MenuItem, MenuSection, MenuTrigger, Header, Text } from "@react-spectrum/s2/Menu";
import More from "@react-spectrum/s2/icons/More";
import InfoCircle from "@react-spectrum/s2/icons/InfoCircle";
import FileText from "@react-spectrum/s2/icons/FileText";
import KeyboardIcon from "@react-spectrum/s2/icons/Keyboard";
import OpenIn from "@react-spectrum/s2/icons/OpenIn";
import Code from "@react-spectrum/s2/icons/Code";

interface TopCornerBrandMenuProps {
  onOpenHelp: () => void;
  compact?: boolean;
}

export function TopCornerBrandMenu({ onOpenHelp, compact = false }: TopCornerBrandMenuProps) {
  return (
    <div className={`hud-island hud-brand-island${compact ? " hud-brand-compact" : ""}`}>
      <Link
        href="/"
        className="hud-brand-link"
        aria-label="北京市第一六六中学三维校园地图（非官方）"
      >
        <img
          src="/maps/map-mark.svg"
          alt=""
          className="hud-brand-mark"
          width={24}
          height={24}
        />
        <span className="hud-brand-title">{compact ? "166地图" : "166 校园地图"}</span>
        <Badge variant="notice" fillStyle="subtle" size="S">
          非官方
        </Badge>
      </Link>

      <span className="hud-hairline-v" aria-hidden="true" />

      <MenuTrigger align="start" direction="bottom">
        <ActionButton
          isQuiet
          size="S"
          aria-label="展开关于项目、免责声明与帮助菜单"
        >
          <More />
        </ActionButton>
        <Menu
          size="M"
          onAction={(key) => {
            if (key === "help") {
              onOpenHelp();
            }
          }}
        >
          <MenuSection>
            <Header>站点信息</Header>
            <MenuItem id="about" href="/about">
              <InfoCircle />
              <Text>关于项目与建模说明</Text>
            </MenuItem>
            <MenuItem id="disclaimer" href="/disclaimer">
              <FileText />
              <Text>免责声明与数据来源</Text>
            </MenuItem>
            <MenuItem id="help">
              <KeyboardIcon />
              <Text>键盘与触屏操控说明</Text>
            </MenuItem>
          </MenuSection>
          <MenuSection>
            <Header>相关链接</Header>
            <MenuItem
              id="school-site"
              href="https://bj166zx.cn"
              target="_blank"
              rel="noopener noreferrer"
            >
              <OpenIn />
              <Text>校园文化站点 (bj166zx.cn)</Text>
            </MenuItem>
            <MenuItem
              id="github"
              href="https://github.com/ibb-official/ibb-school-map"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Code />
              <Text>GitHub 开源仓库</Text>
            </MenuItem>
          </MenuSection>
        </Menu>
      </MenuTrigger>
    </div>
  );
}
