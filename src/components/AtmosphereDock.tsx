"use client";

import { useEffect, useState } from "react";
import { AtmosphereState, QualityTier, WeatherMode } from "@/data/types";
import { formatTimeHours, getPhaseLabel } from "@/scene/sunAstronomy";
import type { PathTracerStatus } from "@/scene/pathTracerController";
import {
  CameraIcon,
  ClockIcon,
  CloudIcon,
  MistIcon,
  MoonIcon,
  PauseIcon,
  PlayIcon,
  RainIcon,
  SnowIcon,
  SparklesIcon,
  SunIcon,
} from "./Icons";

interface AtmosphereDockProps {
  state: AtmosphereState;
  pathTracerStatus: PathTracerStatus;
  shifted?: boolean;
  onChange: (patch: Partial<AtmosphereState>) => void;
  onSyncBeijingNow: () => void;
  onExportPhoto: () => void;
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

const QUALITY_OPTIONS: { id: QualityTier; label: string }[] = [
  { id: "smooth", label: "流畅" },
  { id: "refined", label: "标准" },
  { id: "cinematic", label: "极致画质" },
];

function WeatherIcon({ mode, size = 13 }: { mode: WeatherMode; size?: number }) {
  switch (mode) {
    case "clear":
      return <SunIcon size={size} />;
    case "cloudy":
      return <CloudIcon size={size} />;
    case "rainy":
      return <RainIcon size={size} />;
    case "misty":
      return <MistIcon size={size} />;
    case "snowy":
      return <SnowIcon size={size} />;
  }
}

export function AtmosphereDock({
  state,
  pathTracerStatus,
  shifted = false,
  onChange,
  onSyncBeijingNow,
  onExportPhoto,
}: AtmosphereDockProps) {
  const [expanded, setExpanded] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth >= 860) {
      setExpanded(true);
    }
  }, []);

  useEffect(() => {
    if (state.pathTracingActive) {
      setExpanded(true);
    }
  }, [state.pathTracingActive]);
  const isNight = state.timeHours < 5.5 || state.timeHours >= 18.8;
  const formattedTime = formatTimeHours(state.timeHours);
  const phaseLabel = getPhaseLabel(state.timeHours);

  return (
    <div
      className={`atmo-dock ${expanded ? "atmo-dock-expanded" : "atmo-dock-collapsed"}${
        shifted ? " atmo-dock-shifted" : ""
      }`}
      aria-label="三维天光、时间、天气与光线追踪控制台"
    >
      {/* Compact Header Summary Row */}
      <div className="atmo-header">
        <button
          type="button"
          className="atmo-toggle-btn"
          onClick={() => setExpanded((v) => !v)}
          title={expanded ? "收起光影天气面板" : "展开光影天气面板"}
        >
          <span className={`atmo-orb ${isNight ? "atmo-orb-night" : "atmo-orb-day"}`}>
            {isNight ? <MoonIcon size={13} /> : <SunIcon size={13} />}
          </span>
          <span className="atmo-time-readout">{formattedTime}</span>
          <span className="atmo-phase-tag">{phaseLabel}</span>
          <span className="atmo-chevron">{expanded ? "▾" : "▸"}</span>
        </button>

        <div className="atmo-header-quick">
          <button
            type="button"
            className={`atmo-mini-btn ${state.autoPlay ? "atmo-mini-btn-active" : ""}`}
            onClick={() =>
              onChange({ autoPlay: !state.autoPlay, syncBeijingTime: false })
            }
            title={state.autoPlay ? "暂停昼夜延时" : "播放昼夜光影流转"}
            aria-label={state.autoPlay ? "暂停昼夜延时" : "播放昼夜光影流转"}
          >
            {state.autoPlay ? <PauseIcon size={12} /> : <PlayIcon size={12} />}
          </button>
          <button
            type="button"
            className={`atmo-mini-btn ${state.syncBeijingTime ? "atmo-mini-btn-active" : ""}`}
            onClick={onSyncBeijingNow}
            title="同步当前北京时间（东城区真实太阳高度）"
          >
            <ClockIcon size={12} />
            <span>北京</span>
          </button>
        </div>
      </div>

      {expanded && (
        <div className="atmo-body">
          {/* 24h Continuous Solar Time Slider */}
          <div className="atmo-slider-wrap">
            <input
              type="range"
              min={0}
              max={23.98}
              step={0.05}
              value={state.timeHours}
              aria-label="24小时连续太阳时间拉条"
              className="atmo-time-slider"
              onChange={(e) =>
                onChange({
                  timeHours: parseFloat(e.target.value),
                  syncBeijingTime: false,
                  autoPlay: false,
                })
              }
            />
            <div className="atmo-scale-labels">
              <span>00:00</span>
              <span>06:00</span>
              <span>12:00</span>
              <span>18:00</span>
              <span>24:00</span>
            </div>
          </div>

          {/* 6 Curated Golden Moments */}
          <div className="atmo-row-chips">
            {TIME_PRESETS.map((p) => {
              const active = Math.abs(state.timeHours - p.hours) < 0.35;
              return (
                <button
                  key={p.label}
                  type="button"
                  className={`atmo-chip ${active ? "atmo-chip-active" : ""}`}
                  onClick={() =>
                    onChange({
                      timeHours: p.hours,
                      syncBeijingTime: false,
                      autoPlay: false,
                    })
                  }
                >
                  {p.label}
                </button>
              );
            })}
          </div>

          {/* 5 Weather Modes */}
          <div className="atmo-section-row">
            <span className="atmo-section-label">天气</span>
            <div className="atmo-pill-group">
              {WEATHER_OPTIONS.map((w) => (
                <button
                  key={w.id}
                  type="button"
                  className={`atmo-pill ${state.weather === w.id ? "atmo-pill-active" : ""}`}
                  onClick={() => onChange({ weather: w.id })}
                >
                  <WeatherIcon mode={w.id} size={12} />
                  <span>{w.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Quality Tier + True GPU Path Tracing Switch */}
          <div className="atmo-section-row atmo-bottom-row">
            <div className="atmo-quality-group" title="实时渲染画质档位">
              <span className="atmo-section-label">画质</span>
              <div className="atmo-pill-group">
                {QUALITY_OPTIONS.map((q) => (
                  <button
                    key={q.id}
                    type="button"
                    disabled={state.pathTracingActive}
                    className={`atmo-pill ${
                      !state.pathTracingActive && state.quality === q.id
                        ? "atmo-pill-active"
                        : ""
                    }`}
                    onClick={() => onChange({ quality: q.id })}
                  >
                    {q.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              className={`atmo-rt-btn ${state.pathTracingActive ? "atmo-rt-btn-active" : ""}`}
              onClick={() =>
                onChange({
                  pathTracingActive: !state.pathTracingActive,
                  autoPlay: false,
                })
              }
              title="开启 GPU 真实蒙特卡洛路径追踪（静止累积多重反弹全局光照与玻璃真折射）"
            >
              <SparklesIcon size={13} />
              <span>{state.pathTracingActive ? "退出真光追" : "真光追"}</span>
            </button>
          </div>

          {/* True Path Tracing Progress & High-Res Photo Capture Bar */}
          {state.pathTracingActive && (
            <div className="atmo-pt-status">
              <div className="atmo-pt-row">
                <span>
                  {pathTracerStatus.phase === "building"
                    ? pathTracerStatus.message ?? "构建 BVH..."
                    : pathTracerStatus.phase === "error"
                    ? pathTracerStatus.message ?? "真光追不可用"
                    : `真路径追踪收敛中 · ${pathTracerStatus.samples}/${pathTracerStatus.targetSamples} spp`}
                </span>
                {pathTracerStatus.phase === "rendering" && (
                  <button
                    type="button"
                    className="atmo-snap-btn"
                    onClick={onExportPhoto}
                    title="导出当前光追渲染画面为高清 PNG 写真"
                  >
                    <CameraIcon size={12} />
                    <span>保存写真</span>
                  </button>
                )}
              </div>
              {pathTracerStatus.phase === "rendering" && (
                <div className="atmo-pt-bar">
                  <div
                    className="atmo-pt-fill"
                    style={{
                      width: `${Math.min(
                        100,
                        (pathTracerStatus.samples / Math.max(1, pathTracerStatus.targetSamples)) *
                          100
                      )}%`,
                    }}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
