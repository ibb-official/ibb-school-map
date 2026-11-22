"use client";

import { useEffect, useState } from "react";
import { Badge } from "@react-spectrum/s2/Badge";
import { Button } from "@react-spectrum/s2/Button";
import { CloseButton } from "@react-spectrum/s2/CloseButton";
import { Divider } from "@react-spectrum/s2/Divider";
import { SegmentedControl, SegmentedControlItem } from "@react-spectrum/s2/SegmentedControl";
import { Switch } from "@react-spectrum/s2/Switch";
import {
  CampusId,
  ColorSchemePref,
  GraphicsSettings,
  MapUserPrefs,
  QualityTier,
} from "@/data/types";
import {
  estimateResourceFootprint,
  graphicsSettingsEqual,
  QUALITY_TIERS,
} from "@/scene/prefs";

interface QualitySettingsContentProps {
  campusId: CampusId;
  activeGraphics: GraphicsSettings;
  prefs: MapUserPrefs;
  onApplyGraphics: (next: GraphicsSettings) => void;
  onToggleTouchControls: (enabled: boolean) => void;
  onTogglePins: (enabled: boolean) => void;
  onChangeColorScheme: (scheme: ColorSchemePref) => void;
  onClose?: () => void;
}

export function QualitySettingsContent({
  campusId,
  activeGraphics,
  prefs,
  onApplyGraphics,
  onToggleTouchControls,
  onTogglePins,
  onChangeColorScheme,
  onClose,
}: QualitySettingsContentProps) {
  const [draft, setDraft] = useState<GraphicsSettings>(activeGraphics);

  useEffect(() => {
    setDraft(activeGraphics);
  }, [activeGraphics]);

  const isDirty = !graphicsSettingsEqual(draft, activeGraphics);
  const currentTierInfo =
    QUALITY_TIERS.find((t) => t.id === draft.quality) ?? QUALITY_TIERS[2];
  const estimate = estimateResourceFootprint(campusId, draft);

  const handleApply = () => {
    onApplyGraphics(draft);
    onClose?.();
  };

  return (
    <div className="settings-panel-body">
      <div className="settings-panel-header">
        <div>
          <h2 className="settings-panel-title">画质与操控设置</h2>
          <p className="settings-panel-sub">设置将保存至本地，按画质按需加载对应资源</p>
        </div>
        {onClose && <CloseButton size="S" onPress={onClose} />}
      </div>

      {/* 1. Enhanced Map Switch */}
      <div className="settings-section">
        <div className="settings-row-between">
          <div className="settings-row-copy">
            <div className="settings-label-line">
              <span className="settings-label">增强版地图</span>
              <Badge
                variant={draft.enhancedMap ? "accent" : "neutral"}
                fillStyle="subtle"
                size="S"
              >
                {draft.enhancedMap ? "已启用" : "普通版"}
              </Badge>
            </div>
            <p className="settings-helper">
              {draft.enhancedMap
                ? "加载写实 PBR 材质、物理玻璃浅层室内、24h 天光天气与 GPU 光追。"
                : "默认经典清爽地图：零外部 PBR 贴图与后处理，加载更快、占用更低。"}
            </p>
          </div>
          <Switch
            isEmphasized
            aria-label="开启或关闭增强版地图"
            isSelected={draft.enhancedMap}
            onChange={(val) => setDraft((prev) => ({ ...prev, enhancedMap: val }))}
          />
        </div>
      </div>

      {/* 2. Quality Tier (Unrestricted on all devices) */}
      <div className="settings-section">
        <div className="settings-label-line" style={{ marginBottom: "8px" }}>
          <span className="settings-label">渲染画质</span>
          {draft.quality === "ultra" && (
            <Badge variant="informative" fillStyle="subtle" size="S">
              全设备开放极致画质
            </Badge>
          )}
        </div>

        <SegmentedControl
          aria-label="选择三维渲染画质档位"
          isJustified
          UNSAFE_style={{ width: "100%" }}
          selectedKey={draft.quality}
          onSelectionChange={(key) => {
            if (key === "low" || key === "medium" || key === "high" || key === "ultra") {
              setDraft((prev) => ({ ...prev, quality: key as QualityTier }));
            }
          }}
        >
          {QUALITY_TIERS.map((tier) => (
            <SegmentedControlItem key={tier.id} id={tier.id}>
              {tier.label}
            </SegmentedControlItem>
          ))}
        </SegmentedControl>

        <p className="settings-helper" style={{ marginTop: "8px" }}>
          {draft.enhancedMap ? currentTierInfo.enhancedDesc : currentTierInfo.classicDesc}
        </p>

        {/* Live Resource Footprint Preview */}
        <div className="settings-footprint-card">
          <div className="settings-footprint-top">
            <span className="settings-footprint-label">本次加载资源预估</span>
            <span className="settings-footprint-size">约 {estimate.totalMB} MB</span>
          </div>
          <div className="settings-footprint-detail">
            模型 {estimate.modelMB} MB · 外部纹理{" "}
            {estimate.texturesMB === 0 ? "0 MB（不加载）" : `${estimate.texturesMB} MB`}
          </div>
          <ul className="settings-module-list">
            {estimate.loadedModules.map((mod) => (
              <li key={mod}>{mod}</li>
            ))}
          </ul>
        </div>

        {/* Apply & Reload Bar */}
        <div className="settings-apply-bar">
          {isDirty ? (
            <>
              <Button variant="accent" size="M" onPress={handleApply}>
                应用并重新加载地图
              </Button>
              <Button
                variant="secondary"
                fillStyle="outline"
                size="M"
                onPress={() => setDraft(activeGraphics)}
              >
                还原
              </Button>
            </>
          ) : (
            <div className="settings-saved-note">
              <span className="settings-saved-badge">
                <Badge variant="positive" fillStyle="subtle" size="S">
                  已生效
                </Badge>
              </span>
              <span>修改地图模式或画质后，点击应用将释放旧显存并重新加载</span>
            </div>
          )}
        </div>
      </div>

      <Divider size="S" />

      {/* 3. Controls & Interface Preferences (Instant apply, no reload needed) */}
      <div className="settings-section">
        <div className="settings-row-between">
          <div className="settings-row-copy">
            <span className="settings-label">虚拟触屏按键</span>
            <p className="settings-helper">
              电脑端与移动端均可开启：左下角摇杆平移漫游，右下角按钮上升/下降。
            </p>
          </div>
          <Switch
            isEmphasized
            aria-label="开启或关闭虚拟触屏按键"
            isSelected={prefs.showTouchControls}
            onChange={onToggleTouchControls}
          />
        </div>

        <div className="settings-row-between" style={{ marginTop: "12px" }}>
          <div className="settings-row-copy">
            <span className="settings-label">3D 建筑浮动标签</span>
            <p className="settings-helper">在三维场景建筑上方显示名称标注。</p>
          </div>
          <Switch
            isEmphasized
            aria-label="显示或隐藏建筑标签"
            isSelected={prefs.showPins}
            onChange={onTogglePins}
          />
        </div>

        <div style={{ marginTop: "14px" }}>
          <div className="settings-label" style={{ marginBottom: "8px" }}>
            界面外观
          </div>
          <SegmentedControl
            aria-label="选择界面色彩外观"
            isJustified
            UNSAFE_style={{ width: "100%" }}
            selectedKey={prefs.colorScheme}
            onSelectionChange={(key) => {
              if (key === "light" || key === "dark" || key === "system") {
                onChangeColorScheme(key);
              }
            }}
          >
            <SegmentedControlItem id="light">浅色</SegmentedControlItem>
            <SegmentedControlItem id="dark">深色</SegmentedControlItem>
            <SegmentedControlItem id="system">自动</SegmentedControlItem>
          </SegmentedControl>
        </div>
      </div>
    </div>
  );
}
