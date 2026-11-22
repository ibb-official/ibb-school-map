"use client";

import { ActionButton } from "@react-spectrum/s2/ActionButton";
import { Badge } from "@react-spectrum/s2/Badge";
import { Button, Text } from "@react-spectrum/s2/Button";
import { CloseButton } from "@react-spectrum/s2/CloseButton";
import { Divider } from "@react-spectrum/s2/Divider";
import { ProgressBar } from "@react-spectrum/s2/ProgressBar";
import { SegmentedControl, SegmentedControlItem } from "@react-spectrum/s2/SegmentedControl";
import { Slider } from "@react-spectrum/s2/Slider";
import { ToggleButton } from "@react-spectrum/s2/ToggleButton";
import Camera from "@react-spectrum/s2/icons/Camera";
import Clock from "@react-spectrum/s2/icons/Clock";
import Pause from "@react-spectrum/s2/icons/Pause";
import Play from "@react-spectrum/s2/icons/Play";
import Lighten from "@react-spectrum/s2/icons/Lighten";
import { AtmosphereState, WeatherMode } from "@/data/types";
import type { PathTracerStatus } from "@/scene/pathTracerController";
import { formatTimeHours, getPhaseLabel } from "@/scene/sunAstronomy";

interface AtmosphereDockProps {
  state: AtmosphereState;
  pathTracerStatus: PathTracerStatus;
  onChange: (patch: Partial<AtmosphereState>) => void;
  onSyncBeijingNow: () => void;
  onExportPhoto: () => void;
  onClose?: () => void;
}

const TIME_PRESETS: { label: string; hours: number }[] = [
  { label: "朝霞", hours: 5.82 },
  { label: "晨光", hours: 8.5 },
  { label: "正午", hours: 12.5 },
  { label: "晚霞", hours: 17.78 },
  { label: "蓝调", hours: 19.05 },
  { label: "夜校", hours: 20.75 },
];

const WEATHER_OPTIONS: { id: WeatherMode; label: string }[] = [
  { id: "clear", label: "晴朗" },
  { id: "cloudy", label: "多云" },
  { id: "rainy", label: "雨湿" },
  { id: "misty", label: "晨雾" },
  { id: "snowy", label: "初雪" },
];

/**
 * Spectrum 2 redesigned Atmosphere / Solar Time / Weather / Path Tracing panel.
 * Rendered ONLY when Enhanced Map mode is enabled.
 */
export function AtmosphereDock({
  state,
  pathTracerStatus,
  onChange,
  onSyncBeijingNow,
  onExportPhoto,
  onClose,
}: AtmosphereDockProps) {
  const formattedTime = formatTimeHours(state.timeHours);
  const phaseLabel = getPhaseLabel(state.timeHours);

  return (
    <div className="atmo-s2-panel" aria-label="增强版天光、时间、天气与光追面板">
      <div className="atmo-s2-header">
        <div className="atmo-s2-title-group">
          <span className="atmo-s2-time">{formattedTime}</span>
          <Badge variant="informative" fillStyle="subtle" size="S">
            {phaseLabel}
          </Badge>
        </div>

        <div className="atmo-s2-header-actions">
          <ToggleButton
            size="S"
            isQuiet
            isEmphasized
            isSelected={state.autoPlay}
            onChange={(selected) =>
              onChange({ autoPlay: selected, syncBeijingTime: false })
            }
            aria-label={state.autoPlay ? "暂停昼夜延时" : "播放昼夜延时"}
          >
            {state.autoPlay ? <Pause /> : <Play />}
          </ToggleButton>

          <ToggleButton
            size="S"
            isQuiet
            isEmphasized
            isSelected={state.syncBeijingTime}
            onChange={() => onSyncBeijingNow()}
            aria-label="同步当前北京时间"
          >
            <Clock />
          </ToggleButton>

          {onClose && <CloseButton size="S" onPress={onClose} />}
        </div>
      </div>

      {/* 24h Continuous Solar Time Slider */}
      <div className="atmo-s2-section">
        <Slider
          aria-label="24小时连续北京太阳时刻"
          size="S"
          isEmphasized
          UNSAFE_style={{ width: "100%" }}
          minValue={0}
          maxValue={23.95}
          step={0.05}
          value={state.timeHours}
          onChange={(val) =>
            onChange({
              timeHours: val,
              syncBeijingTime: false,
              autoPlay: false,
            })
          }
        />

        <div className="atmo-s2-presets">
          {TIME_PRESETS.map((p) => {
            const active = Math.abs(state.timeHours - p.hours) < 0.35;
            return (
              <ActionButton
                key={p.label}
                size="XS"
                isQuiet={!active}
                onPress={() =>
                  onChange({
                    timeHours: p.hours,
                    syncBeijingTime: false,
                    autoPlay: false,
                  })
                }
              >
                {p.label}
              </ActionButton>
            );
          })}
        </div>
      </div>

      <Divider size="S" />

      {/* 5 Weather Modes */}
      <div className="atmo-s2-section">
        <div className="atmo-s2-label">校园天气</div>
        <SegmentedControl
          aria-label="选择校园天气"
          isJustified
          UNSAFE_style={{ width: "100%" }}
          selectedKey={state.weather}
          onSelectionChange={(key) => {
            if (
              key === "clear" ||
              key === "cloudy" ||
              key === "rainy" ||
              key === "misty" ||
              key === "snowy"
            ) {
              onChange({ weather: key });
            }
          }}
        >
          {WEATHER_OPTIONS.map((w) => (
            <SegmentedControlItem key={w.id} id={w.id}>
              {w.label}
            </SegmentedControlItem>
          ))}
        </SegmentedControl>
      </div>

      <Divider size="S" />

      {/* GPU Path Tracing (Lazy-loaded on demand) */}
      <div className="atmo-s2-section">
        <div className="atmo-s2-rt-row">
          <div>
            <div className="atmo-s2-label" style={{ marginBottom: "2px" }}>
              GPU 真路径追踪
            </div>
            <div className="atmo-s2-helper">
              静止累积多重反弹全局光照与玻璃真折射
            </div>
          </div>

          <ToggleButton
            size="S"
            isEmphasized
            isSelected={state.pathTracingActive}
            onChange={(selected) =>
              onChange({ pathTracingActive: selected, autoPlay: false })
            }
          >
            <Lighten />
            <Text>{state.pathTracingActive ? "退出" : "开启"}</Text>
          </ToggleButton>
        </div>

        {(state.pathTracingActive || pathTracerStatus.phase === "error") && (
          <div className="atmo-s2-pt-box">
            {pathTracerStatus.phase === "error" ? (
              <div className="atmo-s2-pt-error">
                {pathTracerStatus.message ?? "当前 GPU 暂不支持路径追踪"}
              </div>
            ) : pathTracerStatus.phase === "building" || pathTracerStatus.phase === "idle" ? (
              <ProgressBar
                size="S"
                isIndeterminate
                label={pathTracerStatus.message ?? "正在初始化光线追踪 BVH 加速结构..."}
              />
            ) : (
              <>
                <ProgressBar
                  size="S"
                  label={`光线追踪收敛中 (${pathTracerStatus.samples}/${pathTracerStatus.targetSamples} spp)`}
                  value={Math.min(
                    100,
                    Math.round(
                      (pathTracerStatus.samples /
                        Math.max(1, pathTracerStatus.targetSamples)) *
                        100
                    )
                  )}
                />
                <div style={{ marginTop: "8px", display: "flex", justifyContent: "flex-end" }}>
                  <Button size="S" variant="accent" onPress={onExportPhoto}>
                    <Camera />
                    <Text>保存高清写真</Text>
                  </Button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
