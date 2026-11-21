"use client";

import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { CAMPUSES, DUAL_CAMPUS_LINK } from "@/data/campuses";
import {
  EAST_2D_POLYGONS,
  EnuPoint,
  Map2DPolygon,
  WEST_2D_POLYGONS,
} from "@/data/map2dGeometry";
import { CATEGORY_COLORS } from "@/data/places";
import { CampusId, CampusPlace, ViewMode } from "@/data/types";

interface CampusMap2DProps {
  mode: Extract<ViewMode, "2d" | "overview">;
  campusId: CampusId;
  places: CampusPlace[];
  selectedPlaceId: string | null;
  fallbackNotice?: string | null;
  resetViewRef?: React.MutableRefObject<(() => void) | null>;
  onSelectPlace: (placeId: string) => void;
  onEnterCampus3D: (campusId: CampusId) => void;
}

const POLY_FILL: Record<Map2DPolygon["kind"], string> = {
  road: "#cbd5e1",
  boundary: "#f8fafc",
  context: "#e2e8f0",
  academic: "#dce8f5",
  heritage: "#efe6d5",
  sports: "#fed7aa",
  "sports-track": "#e28879",
  "sports-infield": "#f6cfc4",
  "sports-court": "#a7f3d0",
  gate: "#fecaca",
  corridor: "#ccfbf1",
  plaza: "#f1f5f9",
};

const POLY_STROKE: Record<Map2DPolygon["kind"], string> = {
  road: "#94a3b8",
  boundary: "#0b3f70",
  context: "#cbd5e1",
  academic: "#155b96",
  heritage: "#8a6d3b",
  sports: "#c2410c",
  "sports-track": "#b93822",
  "sports-infield": "#c25943",
  "sports-court": "#0f766e",
  gate: "#b91c1c",
  corridor: "#0f766e",
  plaza: "#cbd5e1",
};

const MIN_SCALE = 0.85;
const MAX_SCALE = 4.0;

function pointsToSvg(pts: EnuPoint[]): string {
  return pts.map(([e, n]) => `${e.toFixed(1)},${(-n).toFixed(1)}`).join(" ");
}

function clamp(v: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, v));
}

export function CampusMap2D({
  mode,
  campusId,
  places,
  selectedPlaceId,
  fallbackNotice,
  resetViewRef,
  onSelectPlace,
  onEnterCampus3D,
}: CampusMap2DProps) {
  const [zoomPercent, setZoomPercent] = useState<number>(100);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const viewportRef = useRef<HTMLDivElement | null>(null);
  const canvasWrapRef = useRef<HTMLDivElement | null>(null);
  const transformRef = useRef<{ scale: number; tx: number; ty: number }>({
    scale: 1,
    tx: 0,
    ty: 0,
  });
  const pointersRef = useRef<Map<number, { x: number; y: number }>>(new Map());
  const gestureRef = useRef<{
    startX: number;
    startY: number;
    moved: boolean;
    hadMultiTouch: boolean;
    pinchDist: number;
    pinchMidX: number;
    pinchMidY: number;
    lastTapTime: number;
    lastTapX: number;
    lastTapY: number;
  }>({
    startX: 0,
    startY: 0,
    moved: false,
    hadMultiTouch: false,
    pinchDist: 0,
    pinchMidX: 0,
    pinchMidY: 0,
    lastTapTime: 0,
    lastTapX: 0,
    lastTapY: 0,
  });
  const suppressClickRef = useRef<boolean>(false);

  const applyTransform = useCallback((scale: number, tx: number, ty: number, animate = false) => {
    const vp = viewportRef.current;
    const wrap = canvasWrapRef.current;
    const clampedScale = clamp(scale, MIN_SCALE, MAX_SCALE);

    let clampedTx = tx;
    let clampedTy = ty;
    if (vp) {
      const rect = vp.getBoundingClientRect();
      const maxPanX = Math.max(rect.width * 0.28, (rect.width * (clampedScale - 1)) / 2 + rect.width * 0.22);
      const maxPanY = Math.max(rect.height * 0.28, (rect.height * (clampedScale - 1)) / 2 + rect.height * 0.22);
      clampedTx = clamp(tx, -maxPanX, maxPanX);
      clampedTy = clamp(ty, -maxPanY, maxPanY);
    }

    transformRef.current = { scale: clampedScale, tx: clampedTx, ty: clampedTy };
    if (wrap) {
      wrap.style.transition = animate ? "transform 0.22s cubic-bezier(0.22, 1, 0.36, 1)" : "none";
      wrap.style.transform = `translate3d(${clampedTx.toFixed(1)}px, ${clampedTy.toFixed(1)}px, 0) scale(${clampedScale.toFixed(4)})`;
    }
    const pct = Math.round(clampedScale * 100);
    setZoomPercent((prev) => (prev === pct ? prev : pct));
  }, []);

  const zoomAtClientPoint = useCallback(
    (nextScale: number, clientX: number, clientY: number, animate = false) => {
      const vp = viewportRef.current;
      const cur = transformRef.current;
      const clampedNext = clamp(nextScale, MIN_SCALE, MAX_SCALE);
      if (!vp) {
        applyTransform(clampedNext, cur.tx, cur.ty, animate);
        return;
      }
      const rect = vp.getBoundingClientRect();
      const dx = clientX - (rect.left + rect.width * 0.5);
      const dy = clientY - (rect.top + rect.height * 0.5);
      const lx = (dx - cur.tx) / cur.scale;
      const ly = (dy - cur.ty) / cur.scale;
      const nextTx = dx - lx * clampedNext;
      const nextTy = dy - ly * clampedNext;
      applyTransform(clampedNext, nextTx, nextTy, animate);
    },
    [applyTransform]
  );

  const resetTransform = useCallback(() => {
    applyTransform(1, 0, 0, true);
  }, [applyTransform]);

  useEffect(() => {
    if (resetViewRef) {
      resetViewRef.current = mode === "2d" ? resetTransform : null;
    }
    return () => {
      if (resetViewRef) resetViewRef.current = null;
    };
  }, [mode, resetTransform, resetViewRef]);

  // Reset pan & zoom cleanly whenever switching campus or re-entering 2D CAD mode
  useEffect(() => {
    if (mode === "2d") {
      applyTransform(1, 0, 0, false);
    }
  }, [campusId, mode, applyTransform]);

  // Smooth desktop wheel zoom anchored to cursor position
  useEffect(() => {
    if (mode !== "2d") return;
    const vp = viewportRef.current;
    if (!vp) return;
    const handleWheel = (ev: WheelEvent) => {
      ev.preventDefault();
      const factor = ev.deltaY < 0 ? 1.14 : 0.88;
      zoomAtClientPoint(transformRef.current.scale * factor, ev.clientX, ev.clientY, false);
    };
    vp.addEventListener("wheel", handleWheel, { passive: false });
    return () => vp.removeEventListener("wheel", handleWheel);
  }, [mode, zoomAtClientPoint]);

  const handlePointerDown = (ev: React.PointerEvent<HTMLDivElement>) => {
    if (ev.button !== 0 && ev.pointerType === "mouse") return;
    const target = ev.target as HTMLElement | null;
    if (target?.closest(".map2d-top-hud")) return;

    pointersRef.current.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
    const g = gestureRef.current;

    if (pointersRef.current.size === 1) {
      g.startX = ev.clientX;
      g.startY = ev.clientY;
      g.moved = false;
      g.hadMultiTouch = false;
      suppressClickRef.current = false;
    } else if (pointersRef.current.size === 2) {
      g.hadMultiTouch = true;
      g.moved = true;
      suppressClickRef.current = true;
      const pts = Array.from(pointersRef.current.values());
      g.pinchDist = Math.max(Math.hypot(pts[1].x - pts[0].x, pts[1].y - pts[0].y), 1);
      g.pinchMidX = (pts[0].x + pts[1].x) * 0.5;
      g.pinchMidY = (pts[0].y + pts[1].y) * 0.5;
    }
  };

  const handlePointerMove = (ev: React.PointerEvent<HTMLDivElement>) => {
    const prev = pointersRef.current.get(ev.pointerId);
    if (!prev) return;

    const g = gestureRef.current;
    const prevX = prev.x;
    const prevY = prev.y;
    pointersRef.current.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });

    if (pointersRef.current.size === 1 && !g.hadMultiTouch) {
      const dx = ev.clientX - prevX;
      const dy = ev.clientY - prevY;
      const totalDist = Math.hypot(ev.clientX - g.startX, ev.clientY - g.startY);
      if (totalDist >= 8) {
        g.moved = true;
        suppressClickRef.current = true;
      }
      if (g.moved) {
        const cur = transformRef.current;
        applyTransform(cur.scale, cur.tx + dx, cur.ty + dy, false);
      }
      return;
    }

    if (pointersRef.current.size >= 2) {
      const pts = Array.from(pointersRef.current.values());
      const dist = Math.max(Math.hypot(pts[1].x - pts[0].x, pts[1].y - pts[0].y), 1);
      const midX = (pts[0].x + pts[1].x) * 0.5;
      const midY = (pts[0].y + pts[1].y) * 0.5;

      const cur = transformRef.current;
      const vp = viewportRef.current;
      if (vp && g.pinchDist > 0) {
        const rect = vp.getBoundingClientRect();
        const scaleRatio = dist / g.pinchDist;
        const nextScale = clamp(cur.scale * scaleRatio, MIN_SCALE, MAX_SCALE);

        const prevDx = g.pinchMidX - (rect.left + rect.width * 0.5);
        const prevDy = g.pinchMidY - (rect.top + rect.height * 0.5);
        const nextDx = midX - (rect.left + rect.width * 0.5);
        const nextDy = midY - (rect.top + rect.height * 0.5);

        const lx = (prevDx - cur.tx) / cur.scale;
        const ly = (prevDy - cur.ty) / cur.scale;
        const nextTx = nextDx - lx * nextScale;
        const nextTy = nextDy - ly * nextScale;
        applyTransform(nextScale, nextTx, nextTy, false);
      }

      g.pinchDist = dist;
      g.pinchMidX = midX;
      g.pinchMidY = midY;
    }
  };

  const handlePointerEnd = (ev: React.PointerEvent<HTMLDivElement>) => {
    const g = gestureRef.current;
    const wasSingleTap =
      pointersRef.current.size === 1 && !g.moved && !g.hadMultiTouch;
    pointersRef.current.delete(ev.pointerId);

    if (pointersRef.current.size === 1) {
      // One finger remains after pinch; re-anchor so it doesn't jump
      const [rem] = Array.from(pointersRef.current.values());
      g.startX = rem.x;
      g.startY = rem.y;
    } else if (pointersRef.current.size === 0) {
      if (wasSingleTap) {
        const now = performance.now();
        const tapDist = Math.hypot(ev.clientX - g.lastTapX, ev.clientY - g.lastTapY);
        const target = ev.target as HTMLElement | null;
        const clickedPlace = Boolean(target?.closest("[data-place-hit='1']"));
        if (!clickedPlace && now - g.lastTapTime < 300 && tapDist < 30) {
          // Double-tap empty map area: zoom in or reset to 100%
          if (transformRef.current.scale < 1.65) {
            zoomAtClientPoint(2.2, ev.clientX, ev.clientY, true);
          } else {
            resetTransform();
          }
          g.lastTapTime = 0;
        } else {
          g.lastTapTime = now;
          g.lastTapX = ev.clientX;
          g.lastTapY = ev.clientY;
        }
      }
      // Clear click suppression right after the synthetic click tick
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 40);
    }
  };

  const handlePlaceClick = (placeId: string) => {
    if (suppressClickRef.current) return;
    onSelectPlace(placeId);
  };

  if (mode === "overview") {
    return (
      <div className="overview-scroll-stage">
        <div className="overview-inner">
          <div className="card-surface overview-hero-card">
            <div className="overview-hero-header">
              <div>
                <h2 className="overview-hero-title">
                  北京市第一六六中学 · 双校区同城空间关系总览（东城区）
                </h2>
                <p className="overview-hero-meta">
                  两校区直线间距 <strong>{DUAL_CAMPUS_LINK.straightLineKm} km</strong>（东偏 {DUAL_CAMPUS_LINK.deltaEastMeters} m / 北偏 {DUAL_CAMPUS_LINK.deltaNorthMeters} m）· 骑行 {DUAL_CAMPUS_LINK.cyclingMinutes} · 步行 {DUAL_CAMPUS_LINK.walkingMinutes}
                </p>
              </div>

              <div className="overview-hero-actions">
                <button
                  type="button"
                  onClick={() => onEnterCampus3D("west")}
                  className="overview-cta-primary"
                >
                  进入西校区 3D 模型
                </button>
                <button
                  type="button"
                  onClick={() => onEnterCampus3D("east")}
                  className="overview-cta-secondary"
                >
                  进入东校区 3D 模型
                </button>
              </div>
            </div>

            <svg
              viewBox="-350 -1420 1280 1740"
              className="overview-schematic-svg"
              role="img"
              aria-label="北京166中学东西校区东城区空间相对关系示意总图"
            >
              {/* Street Grid */}
              <g stroke="#dce4ee" strokeWidth="1.5">
                {[-200, 0, 200, 400, 600, 800].map((x) => (
                  <line key={`vx-${x}`} x1={x} y1={-1420} x2={x} y2={320} />
                ))}
                {[-1200, -1000, -800, -600, -400, -200, 0].map((y) => (
                  <line key={`hy-${y}`} x1={-350} y1={y} x2={930} y2={y} />
                ))}
              </g>

              {/* Main Arteries (approximate schematic ENU offsets relative to West origin) */}
              <g stroke="#cbd5e1" strokeWidth="22" strokeLinecap="round">
                <line x1="215" y1="260" x2="215" y2="-1360" />
                <line x1="780" y1="260" x2="780" y2="-1360" />
                <line x1="-290" y1="150" x2="870" y2="150" />
                <line x1="-290" y1="-440" x2="870" y2="-440" />
                <line x1="-290" y1="-1125" x2="870" y2="-1125" />
                <line x1="-290" y1="-1300" x2="870" y2="-1300" />
              </g>

              {/* Street Labels */}
              <g fill="#475569" fontSize="22" fontWeight="600">
                <text x="235" y="-560">东四南/北大街</text>
                <text x="580" y="-560">朝阳门北小街</text>
                <text x="-80" y="128">灯市口大街</text>
                <text x="-80" y="-458">朝内大街</text>
                <text x="360" y="-1145">东四六条</text>
                <text x="360" y="-1318">平安大街（张自忠路）</text>
              </g>

              {/* Direct Distance Link */}
              <line
                x1="-35"
                y1="-65"
                x2="565"
                y2="-1115"
                stroke="#8a6d3b"
                strokeWidth="5"
                strokeDasharray="16 12"
              />
              <g transform="translate(275, -595)">
                <rect x="-112" y="-26" width="224" height="44" rx="22" fill="#0b3f70" />
                <text
                  x="0"
                  y="3"
                  textAnchor="middle"
                  fill="#fde68a"
                  fontSize="22"
                  fontWeight="700"
                >
                  直线距离 1.24 km
                </text>
              </g>

              {/* Transit Pins */}
              {[
                { x: 215, y: 150, label: "M 5号线 灯市口站" },
                { x: -245, y: 150, label: "M 8号线 金鱼胡同站" },
                { x: 215, y: -440, label: "M 5/6号线 东四站" },
                { x: 215, y: -1300, label: "M 5号线 张自忠路站" },
              ].map((st) => (
                <g key={st.label} transform={`translate(${st.x}, ${st.y})`}>
                  <circle r="13" fill="#0f766e" stroke="#fff" strokeWidth="3.5" />
                  <text x="18" y="6" fontSize="20" fill="#0f766e" fontWeight="700">
                    {st.label}
                  </text>
                </g>
              ))}

              {/* West Campus Clickable Card */}
              <g
                transform="translate(-40, -68)"
                style={{ cursor: "pointer" }}
                onClick={() => onEnterCampus3D("west")}
              >
                <rect
                  x="-76"
                  y="-76"
                  width="152"
                  height="152"
                  rx="16"
                  fill="rgba(21, 91, 150, 0.20)"
                  stroke="#0b3f70"
                  strokeWidth="5"
                />
                <circle cx="0" cy="0" r="14" fill="#c2410c" stroke="#fff" strokeWidth="4" />
                <rect x="-135" y="92" width="270" height="62" rx="12" fill="#0b3f70" />
                <text x="0" y="120" textAnchor="middle" fill="#fff" fontSize="22" fontWeight="700">
                  西校区 · 校本部
                </text>
                <text x="0" y="144" textAnchor="middle" fill="#cbd5e1" fontSize="17">
                  同福夹道3号（16个建模节点）
                </text>
              </g>

              {/* East Campus Clickable Card */}
              <g
                transform="translate(565, -1115)"
                style={{ cursor: "pointer" }}
                onClick={() => onEnterCampus3D("east")}
              >
                <rect
                  x="-65"
                  y="-88"
                  width="130"
                  height="176"
                  rx="16"
                  fill="rgba(21, 128, 61, 0.18)"
                  stroke="#15803d"
                  strokeWidth="5"
                />
                <circle cx="0" cy="0" r="14" fill="#15803d" stroke="#fff" strokeWidth="4" />
                <rect x="-140" y="-164" width="280" height="62" rx="12" fill="#155b96" />
                <text x="0" y="-136" textAnchor="middle" fill="#fff" fontSize="22" fontWeight="700">
                  东校区 · 毕业年级部
                </text>
                <text x="0" y="-112" textAnchor="middle" fill="#cbd5e1" fontSize="17">
                  东四六条甲44号（10个建模节点）
                </text>
              </g>

              {/* Compass Rose (上北下南 · 左西右东) */}
              <g transform="translate(830, -1330)">
                <circle r="44" fill="#ffffff" stroke="#0b3f70" strokeWidth="2.8" />
                <circle r="33" fill="none" stroke="rgba(11,63,112,0.16)" strokeWidth="1.2" />
                <polygon points="0,-18 -6,0 0,-2 6,0" fill="#c9332b" />
                <polygon points="0,18 -6,0 0,2 6,0" fill="#94a3b8" />
                <text x="0" y="-25" textAnchor="middle" fontSize="13" fontWeight="700" fill="#c9332b">
                  北
                </text>
                <text x="0" y="36" textAnchor="middle" fontSize="11.5" fontWeight="600" fill="#475569">
                  南
                </text>
                <text x="-30" y="4.5" textAnchor="middle" fontSize="11.5" fontWeight="600" fill="#475569">
                  西
                </text>
                <text x="30" y="4.5" textAnchor="middle" fontSize="11.5" fontWeight="600" fill="#475569">
                  东
                </text>
              </g>
            </svg>
          </div>

          <div className="overview-cards-grid">
            {(["west", "east"] as CampusId[]).map((cid) => {
              const meta = CAMPUSES[cid];
              return (
                <div key={cid} className="card-surface overview-campus-card">
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "#8a6d3b" }}>
                    {meta.roleLabel}
                  </div>
                  <h3 style={{ margin: "4px 0 6px", fontSize: "16px", color: "#0b3f70" }}>
                    {meta.name}
                  </h3>
                  <p style={{ margin: "0 0 8px", fontSize: "13px", color: "#475569", lineHeight: 1.55 }}>
                    {meta.summary}
                  </p>
                  <div style={{ fontSize: "12px", color: "#516175", marginBottom: "12px", lineHeight: 1.65 }}>
                    <div>地址：{meta.address}</div>
                    <div>规模：{meta.approxAreaSqm}</div>
                    <div>轨道交通：{meta.nearestTransit[0]}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => onEnterCampus3D(cid)}
                    className="tool-btn tool-btn-active overview-enter-btn"
                  >
                    进入该校区 3D 浏览
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // Interactive 2D Metric CAD Plan Mode with Pointer Pan + Pinch-to-Zoom + Double-Tap
  const polys = campusId === "west" ? WEST_2D_POLYGONS : EAST_2D_POLYGONS;
  const viewBox =
    campusId === "west"
      ? "-178 -154 220 192"
      : "-55 -105 130 165";

  return (
    <div
      ref={viewportRef}
      className="map2d-viewport"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
    >
      {fallbackNotice && (
        <div role="status" className="map2d-fallback-banner">
          {fallbackNotice}
        </div>
      )}

      <div
        className={`map2d-top-hud${selectedPlaceId ? " map2d-top-hud-shifted" : ""}`}
      >
        <div
          className="map2d-compass-pill"
          title="2D 平面图固定为上北下南、左西右东"
          aria-label="方向指北针：上北下南，左西右东"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <circle cx="12" cy="12" r="10.5" fill="#ffffff" stroke="#0b3f70" strokeWidth="1.2" />
            <polygon points="12,3 9.2,12 12,10.8 14.8,12" fill="#c9332b" />
            <polygon points="12,21 9.2,12 12,13.2 14.8,12" fill="#94a3b8" />
          </svg>
          <span>上北下南</span>
        </div>
        <button
          type="button"
          className="tool-btn map2d-zoom-btn"
          onClick={() =>
            applyTransform(
              transformRef.current.scale / 1.25,
              transformRef.current.tx,
              transformRef.current.ty,
              true
            )
          }
          aria-label="缩小 2D 平面图"
        >
          －
        </button>
        <button
          type="button"
          className="tool-btn map2d-zoom-readout"
          onClick={resetTransform}
          title="点击复位 2D 缩放与位置"
          aria-label={`当前缩放 ${zoomPercent}%，点击复位`}
        >
          {zoomPercent}%
        </button>
        <button
          type="button"
          className="tool-btn map2d-zoom-btn"
          onClick={() =>
            applyTransform(
              transformRef.current.scale * 1.25,
              transformRef.current.tx,
              transformRef.current.ty,
              true
            )
          }
          aria-label="放大 2D 平面图"
        >
          ＋
        </button>
      </div>

      <div ref={canvasWrapRef} className="map2d-svg-wrap">
        <svg
          viewBox={viewBox}
          className="map2d-svg"
          role="img"
          aria-label={`${CAMPUSES[campusId].name} 实测二维矢量平面总图`}
        >
          {/* 20m Coordinate Grid */}
          <g stroke="#f1f5f9" strokeWidth="0.45">
            {Array.from({ length: 16 }, (_, idx) => -180 + idx * 20).map((gx) => (
              <line key={`gx-${gx}`} x1={gx} y1={-170} x2={gx} y2={65} />
            ))}
            {Array.from({ length: 14 }, (_, idx) => -160 + idx * 20).map((gy) => (
              <line key={`gy-${gy}`} x1={-190} y1={gy} x2={85} y2={gy} />
            ))}
          </g>

          {/* Polygons */}
          {polys.map((poly) => {
            const isInteractive = Boolean(poly.placeId);
            const isSelected = poly.placeId === selectedPlaceId;
            const isHovered = poly.placeId !== undefined && poly.placeId === hoveredId;

            return (
              <polygon
                key={poly.id}
                data-place-hit={isInteractive ? "1" : undefined}
                points={pointsToSvg(poly.pts)}
                fill={
                  isSelected
                    ? "#fde68a"
                    : isHovered
                      ? "#bfdbfe"
                      : POLY_FILL[poly.kind]
                }
                stroke={isSelected ? "#b45309" : POLY_STROKE[poly.kind]}
                strokeWidth={
                  poly.kind === "boundary"
                    ? 1.1
                    : isSelected
                      ? 1.1
                      : isHovered
                        ? 0.85
                        : 0.55
                }
                strokeDasharray={poly.kind === "boundary" ? "2.4 1.4" : undefined}
                style={{ cursor: isInteractive ? "pointer" : "default" }}
                onMouseEnter={() => {
                  if (poly.placeId) setHoveredId(poly.placeId);
                }}
                onMouseLeave={() => setHoveredId(null)}
                onClick={() => {
                  if (poly.placeId) handlePlaceClick(poly.placeId);
                }}
              />
            );
          })}

          {/* West Campus Oval Track Lanes, Hard-Surface Courts, Water Rockery & 5 Ping-Pong Tables */}
          {campusId === "west" && (
            <g pointerEvents="none" fill="none" stroke="rgba(255,255,255,0.90)">
              {[12.9, 13.925, 14.95, 15.975, 17.0].map((r) => {
                const inset = 17.0 - r;
                const x = -92.3 + inset;
                const y = -(124.6 - inset);
                const w = -14.3 - inset - (-92.3 + inset);
                const h = 34.0 - 2 * inset;
                return (
                  <rect
                    key={`lane-${r}`}
                    x={x}
                    y={y}
                    width={w}
                    height={h}
                    rx={r}
                    ry={r}
                    strokeWidth="0.3"
                  />
                );
              })}
              {[-120.5, -121.525, -122.55, -123.575, -124.6].map((ly) => (
                <line
                  key={`ne-lane-${ly}`}
                  x1={-31.3}
                  y1={ly}
                  x2={-9.5}
                  y2={ly}
                  strokeWidth="0.3"
                />
              ))}
              <line x1={-9.8} y1={-124.62} x2={-9.8} y2={-120.48} strokeWidth="0.38" />
              <line x1={-59.8} y1={-124.62} x2={-59.8} y2={-120.48} strokeWidth="0.38" />
              {[
                [-74.8, -61.8],
                [-59.8, -46.8],
                [-44.8, -31.8],
              ].map(([cx0, cx1]) => {
                const cmid = (cx0 + cx1) * 0.5;
                return (
                  <g key={`court-${cx0}`} strokeWidth="0.32">
                    <rect
                      x={cx0 - 0.5}
                      y={-119.55}
                      width={cx1 - cx0 + 1.0}
                      height={23.9}
                      fill="#7dd9b2"
                      stroke="none"
                    />
                    <rect x={cmid - 2.4} y={-119.1} width={4.8} height={5.5} fill="#d9775e" />
                    <rect x={cmid - 2.4} y={-101.6} width={4.8} height={5.5} fill="#d9775e" />
                    <circle cx={cmid} cy={-107.6} r={1.8} fill="#d9775e" />
                    <path d={`M ${(cmid - 5.8).toFixed(2)},-117.6 A 6.0,6.0 0 0 0 ${(cmid + 5.8).toFixed(2)},-117.6`} />
                    <path d={`M ${(cmid - 5.8).toFixed(2)},-97.6 A 6.0,6.0 0 0 1 ${(cmid + 5.8).toFixed(2)},-97.6`} />
                    <rect x={cx0} y={-119.1} width={cx1 - cx0} height={23.0} />
                    <line x1={cx0} y1={-107.6} x2={cx1} y2={-107.6} />
                  </g>
                );
              })}
              <line
                x1={-75.2}
                y1={-107.6}
                x2={-61.4}
                y2={-107.6}
                stroke="#ea580c"
                strokeWidth="0.5"
                strokeDasharray="0.9 0.5"
              />
              <circle cx={-75.05} cy={-134.55} r={1.15} fill="rgba(21,128,61,0.45)" stroke="#15803d" strokeWidth="0.35" />
              <circle cx={-22.0} cy={-120.25} r={1.15} fill="rgba(21,128,61,0.45)" stroke="#15803d" strokeWidth="0.35" />
              <circle cx={-20.6} cy={-131.5} r={2.25} fill="#38bdf8" fillOpacity={0.62} stroke="#334155" strokeWidth="0.55" />
              <circle cx={-20.6} cy={-131.5} r={1.18} fill="#57534e" stroke="#e0f2fe" strokeWidth="0.28" />
              <line x1={-5.8} y1={-130.6} x2={-5.8} y2={-132.1} stroke="#ffffff" strokeWidth="0.7" />
              <path
                d="M 1.45,-73.8 L 1.45,-85.4 L -13.2,-85.4"
                stroke="#0f766e"
                strokeWidth="0.55"
                strokeDasharray="1.3 0.9"
              />
              <polygon points="-14.4,-85.4 -12.7,-86.2 -12.7,-84.6" fill="#0f766e" stroke="none" />
              {[-29.2, -24.8, -16.2, -12.4, -8.6].map((tx) => (
                <rect
                  key={`pp-${tx}`}
                  x={tx - 1.35}
                  y={-133.0 - 0.75}
                  width={2.7}
                  height={1.5}
                  fill="#2563eb"
                  stroke="#ffffff"
                  strokeWidth="0.22"
                />
              ))}
            </g>
          )}

          {/* Sub-zone & Neighbor Captions */}
          <g pointerEvents="none">
            {polys
              .filter((poly) => poly.subLabel && poly.labelEnu)
              .map((poly) => (
                <text
                  key={`sublabel-${poly.id}`}
                  x={poly.labelEnu![0]}
                  y={-poly.labelEnu![1]}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={poly.kind === "context" ? 5.2 : 3.4}
                  fontWeight={poly.kind === "context" ? "700" : "600"}
                  fill={poly.kind === "context" ? "#475569" : "#334155"}
                  stroke="#ffffff"
                  strokeWidth="0.7"
                  paintOrder="stroke"
                >
                  {poly.subLabel}
                </text>
              ))}
          </g>

          {/* Clickable Point Markers + Codes (with enlarged invisible touch target) */}
          {places.map((p) => {
            const sx = p.enu[0];
            const sy = -p.enu[1];
            const selected = p.id === selectedPlaceId;
            const color = CATEGORY_COLORS[p.category];
            return (
              <g
                key={p.id}
                data-place-hit="1"
                transform={`translate(${sx.toFixed(1)}, ${sy.toFixed(1)})`}
                style={{ cursor: "pointer" }}
                onClick={() => handlePlaceClick(p.id)}
              >
                {/* Invisible touch-friendly hit circle (~38-44px equivalent on mobile) */}
                <circle r={campusId === "west" ? 7.2 : 5.6} fill="transparent" />
                <circle
                  r={selected ? 3.4 : 2.5}
                  fill={selected ? "#b45309" : color}
                  stroke="#ffffff"
                  strokeWidth="0.7"
                />
                <text
                  x="3.3"
                  y="1.2"
                  fontSize={campusId === "west" ? 4.2 : 3.3}
                  fontWeight="700"
                  fill="#0f1f33"
                  stroke="#ffffff"
                  strokeWidth="0.9"
                  paintOrder="stroke"
                >
                  {p.code} {p.shortName}
                </text>
              </g>
            );
          })}

          {/* Compass Rose (上北下南 · 左西右东) */}
          <g
            transform={
              campusId === "west"
                ? "translate(13, -141)"
                : "translate(61, -92)"
            }
          >
            <circle r="9.5" fill="#ffffff" stroke="#0b3f70" strokeWidth="0.6" />
            <circle r="7.2" fill="none" stroke="rgba(11,63,112,0.18)" strokeWidth="0.25" />
            <polygon points="0,-4.4 -1.8,0.2 0,-0.4 1.8,0.2" fill="#c9332b" />
            <polygon points="0,4.4 -1.8,0.2 0,0.8 1.8,0.2" fill="#94a3b8" />
            <text x="0" y="-5.3" textAnchor="middle" fontSize="2.7" fontWeight="700" fill="#c9332b">
              北
            </text>
            <text x="0" y="7.7" textAnchor="middle" fontSize="2.3" fontWeight="600" fill="#475569">
              南
            </text>
            <text x="-6.4" y="0.9" textAnchor="middle" fontSize="2.3" fontWeight="600" fill="#475569">
              西
            </text>
            <text x="6.4" y="0.9" textAnchor="middle" fontSize="2.3" fontWeight="600" fill="#475569">
              东
            </text>
          </g>

          <g
            transform={
              campusId === "west"
                ? "translate(-165, 22)"
                : "translate(-46, 51)"
            }
          >
            <line x1="0" y1="0" x2="20" y2="0" stroke="#0b3f70" strokeWidth="1.0" />
            <line x1="0" y1="-1.5" x2="0" y2="1.5" stroke="#0b3f70" strokeWidth="0.8" />
            <line x1="20" y1="-1.5" x2="20" y2="1.5" stroke="#0b3f70" strokeWidth="0.8" />
            <text x="10" y="-2.5" textAnchor="middle" fontSize="3.6" fontWeight="700" fill="#0b3f70">
              20 m（真实米制比例）
            </text>
          </g>
        </svg>
      </div>
    </div>
  );
}
