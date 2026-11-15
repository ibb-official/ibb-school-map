"use client";

import { useState } from "react";
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
  "sports-track": "#f2b8b5",
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
  "sports-track": "#c2410c",
  "sports-court": "#0f766e",
  gate: "#b91c1c",
  corridor: "#0f766e",
  plaza: "#cbd5e1",
};

function pointsToSvg(pts: EnuPoint[]): string {
  return pts.map(([e, n]) => `${e.toFixed(1)},${(-n).toFixed(1)}`).join(" ");
}

export function CampusMap2D({
  mode,
  campusId,
  places,
  selectedPlaceId,
  fallbackNotice,
  onSelectPlace,
  onEnterCampus3D,
}: CampusMap2DProps) {
  const [zoom, setZoom] = useState<number>(1);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  if (mode === "overview") {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          overflowY: "auto",
          background: "linear-gradient(180deg, #e7eef6 0%, #f4f7fb 100%)",
          padding: "18px",
        }}
      >
        <div style={{ maxWidth: "1120px", margin: "0 auto", display: "grid", gap: "16px" }}>
          <div className="card-surface" style={{ padding: "18px 20px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "12px",
                flexWrap: "wrap",
                marginBottom: "12px",
              }}
            >
              <div>
                <h2 style={{ margin: 0, fontSize: "17px", color: "#0b3f70" }}>
                  北京市第一六六中学 · 双校区同城空间关系总览（东城区）
                </h2>
                <p style={{ margin: "4px 0 0", fontSize: "13px", color: "#516175" }}>
                  两校区直线间距 <strong>{DUAL_CAMPUS_LINK.straightLineKm} km</strong>（东偏 {DUAL_CAMPUS_LINK.deltaEastMeters} m / 北偏 {DUAL_CAMPUS_LINK.deltaNorthMeters} m）· 骑行 {DUAL_CAMPUS_LINK.cyclingMinutes} · 步行 {DUAL_CAMPUS_LINK.walkingMinutes}
                </p>
              </div>

              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={() => onEnterCampus3D("west")}
                  style={{
                    border: "none",
                    borderRadius: "9px",
                    background: "#0b3f70",
                    color: "#fff",
                    padding: "8px 14px",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  进入西校区 3D 模型
                </button>
                <button
                  type="button"
                  onClick={() => onEnterCampus3D("east")}
                  style={{
                    border: "1px solid #155b96",
                    borderRadius: "9px",
                    background: "#ffffff",
                    color: "#155b96",
                    padding: "8px 14px",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  进入东校区 3D 模型
                </button>
              </div>
            </div>

            <svg
              viewBox="-350 -1420 1280 1740"
              style={{
                width: "100%",
                maxHeight: "460px",
                borderRadius: "12px",
                border: "1px solid rgba(15, 39, 68, 0.14)",
                background: "#f8fafc",
              }}
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

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "14px",
            }}
          >
            {(["west", "east"] as CampusId[]).map((cid) => {
              const meta = CAMPUSES[cid];
              return (
                <div key={cid} className="card-surface" style={{ padding: "16px 18px" }}>
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "#8a6d3b" }}>
                    {meta.roleLabel}
                  </div>
                  <h3 style={{ margin: "4px 0 6px", fontSize: "16px", color: "#0b3f70" }}>
                    {meta.name}
                  </h3>
                  <p style={{ margin: "0 0 8px", fontSize: "13px", color: "#475569", lineHeight: 1.55 }}>
                    {meta.summary}
                  </p>
                  <div style={{ fontSize: "12px", color: "#516175", marginBottom: "10px" }}>
                    <div>地址：{meta.address}</div>
                    <div>规模：{meta.approxAreaSqm}</div>
                    <div>轨道交通：{meta.nearestTransit[0]}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => onEnterCampus3D(cid)}
                    className="tool-btn tool-btn-active"
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

  // Interactive 2D Metric CAD Plan Mode
  const polys = campusId === "west" ? WEST_2D_POLYGONS : EAST_2D_POLYGONS;
  const viewBox =
    campusId === "west"
      ? "-178 -154 202 192"
      : "-55 -105 130 165";

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        overflow: "auto",
        background: "#edf2f7",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
    >
      {fallbackNotice && (
        <div
          role="status"
          style={{
            position: "absolute",
            top: "14px",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 20,
            background: "#fff7ed",
            border: "1px solid #fdba74",
            color: "#9a3412",
            padding: "8px 14px",
            borderRadius: "10px",
            fontSize: "12.5px",
            fontWeight: 600,
          }}
        >
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
          className="tool-btn"
          onClick={() => setZoom((z) => Math.max(0.7, +(z - 0.2).toFixed(2)))}
          aria-label="缩小 2D 平面图"
        >
          －
        </button>
        <span
          className="tool-btn"
          style={{ cursor: "default", minWidth: "56px", justifyContent: "center" }}
        >
          {Math.round(zoom * 100)}%
        </span>
        <button
          type="button"
          className="tool-btn"
          onClick={() => setZoom((z) => Math.min(2.0, +(z + 0.2).toFixed(2)))}
          aria-label="放大 2D 平面图"
        >
          ＋
        </button>
      </div>

      <svg
        viewBox={viewBox}
        style={{
          width: `${zoom * 100}%`,
          height: `${zoom * 100}%`,
          maxWidth: zoom === 1 ? "980px" : "none",
          maxHeight: zoom === 1 ? "100%" : "none",
          background: "#ffffff",
          borderRadius: "14px",
          border: "1px solid rgba(15, 39, 68, 0.14)",
          boxShadow: "0 8px 28px rgba(15, 39, 68, 0.08)",
        }}
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
                if (poly.placeId) onSelectPlace(poly.placeId);
              }}
            />
          );
        })}

        {/* West Campus Oval Track Lanes & NE 50m Start + 3 Basketball Courts Markings */}
        {campusId === "west" && (
          <g pointerEvents="none" fill="none" stroke="rgba(255,255,255,0.88)">
            {[14.35, 15.35, 16.4, 17.45, 18.45].map((r) => {
              const inset = 18.5 - r;
              const x = -89.5 + inset;
              const y = -(124.5 - inset);
              const w = -8.0 - inset - (-89.5 + inset);
              const h = 37.0 - 2 * inset;
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
            {[-120.35, -121.35, -122.4, -123.45, -124.45].map((ly) => (
              <line
                key={`ne-lane-${ly}`}
                x1={-26.6}
                y1={ly}
                x2={-6.5}
                y2={ly}
                strokeWidth="0.3"
              />
            ))}
            <line x1={-7.0} y1={-124.48} x2={-7.0} y2={-120.32} strokeWidth="0.38" />
            <line x1={-57.0} y1={-124.48} x2={-57.0} y2={-120.32} strokeWidth="0.38" />
            {[
              [-69.5, -56.3],
              [-54.7, -41.5],
              [-39.9, -26.7],
            ].map(([cx0, cx1]) => (
              <g key={`court-${cx0}`} strokeWidth="0.35">
                <rect x={cx0} y={-118.2} width={cx1 - cx0} height={24.4} />
                <line x1={cx0} y1={-106.0} x2={cx1} y2={-106.0} />
                <circle cx={(cx0 + cx1) * 0.5} cy={-106.0} r={1.8} />
              </g>
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

        {/* Clickable Point Markers + Codes */}
        {places.map((p) => {
          const sx = p.enu[0];
          const sy = -p.enu[1];
          const selected = p.id === selectedPlaceId;
          const color = CATEGORY_COLORS[p.category];
          return (
            <g
              key={p.id}
              transform={`translate(${sx.toFixed(1)}, ${sy.toFixed(1)})`}
              style={{ cursor: "pointer" }}
              onClick={() => onSelectPlace(p.id)}
            >
              <circle
                r={selected ? 3.2 : 2.3}
                fill={selected ? "#b45309" : color}
                stroke="#ffffff"
                strokeWidth="0.7"
              />
              <text
                x="3.2"
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
  );
}
