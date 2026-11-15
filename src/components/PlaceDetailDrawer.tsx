"use client";

import { CATEGORY_COLORS, CATEGORY_LABELS } from "@/data/places";
import { CampusPlace, ViewMode } from "@/data/types";
import { CloseIcon, CompassIcon } from "./Icons";

interface PlaceDetailDrawerProps {
  place: CampusPlace;
  viewMode: ViewMode;
  onClose: () => void;
  onFocus3D: (place: CampusPlace) => void;
}

export function PlaceDetailDrawer({
  place,
  viewMode,
  onClose,
  onFocus3D,
}: PlaceDetailDrawerProps) {
  return (
    <aside className="detail-drawer" aria-label={`${place.name} 详情面板`}>
      <div className="detail-header">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <span
              className="place-code-pill"
              style={{ backgroundColor: CATEGORY_COLORS[place.category] }}
            >
              {place.code}
            </span>
            <span
              style={{
                fontSize: "11.5px",
                fontWeight: 600,
                color: CATEGORY_COLORS[place.category],
              }}
            >
              {CATEGORY_LABELS[place.category]}
            </span>
          </div>
          <h2
            style={{
              margin: "6px 0 2px",
              fontSize: "16.5px",
              lineHeight: 1.35,
              color: "#0b3f70",
            }}
          >
            {place.name}
          </h2>
          <p style={{ margin: 0, fontSize: "12px", color: "#516175" }}>
            {place.storiesLabel} · ENU 相对坐标 ({place.enu[0].toFixed(1)}m,{" "}
            {place.enu[1].toFixed(1)}m)
          </p>
        </div>

        <button
          type="button"
          className="icon-close-btn"
          onClick={onClose}
          aria-label="关闭建筑详情"
        >
          <CloseIcon size={15} />
        </button>
      </div>

      <div className="detail-body">
        {viewMode === "3d" && (
          <button
            type="button"
            onClick={() => onFocus3D(place)}
            style={{
              width: "100%",
              padding: "9px 12px",
              borderRadius: "10px",
              border: "none",
              background: "linear-gradient(135deg, #0b3f70 0%, #155b96 100%)",
              color: "#ffffff",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "7px",
              marginBottom: "14px",
            }}
          >
            <CompassIcon size={15} />
            <span>飞至最佳 3D 观赏机位</span>
          </button>
        )}

        <section style={{ marginBottom: "14px" }}>
          <h3 style={{ margin: "0 0 6px", fontSize: "13px", color: "#0b3f70" }}>
            建筑概览
          </h3>
          <p style={{ margin: 0, fontSize: "13px", lineHeight: 1.65, color: "#1f2d3d" }}>
            {place.summary}
          </p>
        </section>

        <section style={{ marginBottom: "14px" }}>
          <h3 style={{ margin: "0 0 6px", fontSize: "13px", color: "#0b3f70" }}>
            实景建模细节特征
          </h3>
          <ul
            style={{
              margin: 0,
              paddingLeft: "18px",
              fontSize: "12.5px",
              lineHeight: 1.65,
              color: "#334155",
            }}
          >
            {place.architecturalFeatures.map((feat, idx) => (
              <li key={idx} style={{ marginBottom: "4px" }}>
                {feat}
              </li>
            ))}
          </ul>
        </section>

        {place.historicalNote && (
          <section
            style={{
              marginBottom: "14px",
              padding: "10px 12px",
              borderRadius: "10px",
              background: "#faf6ee",
              border: "1px solid #e7dcc4",
            }}
          >
            <div style={{ fontSize: "12px", fontWeight: 700, color: "#8a6d3b", marginBottom: "3px" }}>
              校园人文脉络（公开文献）
            </div>
            <p style={{ margin: 0, fontSize: "12px", lineHeight: 1.55, color: "#5c4a28" }}>
              {place.historicalNote}
            </p>
          </section>
        )}

        <section>
          <h3 style={{ margin: "0 0 8px", fontSize: "13px", color: "#0b3f70" }}>
            真实摄影对照存档
          </h3>
          {place.photoRefs.length === 0 ? (
            <p
              style={{
                margin: 0,
                padding: "10px 12px",
                borderRadius: "10px",
                background: "#f4f7fa",
                fontSize: "12px",
                color: "#64748b",
              }}
            >
              该点位三维形态与色彩已依据 OSM 实测矢量轮廓与 Zoom-19 航拍正射影像校准；公开地面摄影资料持续补充中。
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {place.photoRefs.map((photo) => (
                <figure
                  key={photo.src}
                  style={{
                    margin: 0,
                    borderRadius: "10px",
                    border: "1px solid rgba(15, 39, 68, 0.12)",
                    overflow: "hidden",
                    background: "#f8fafc",
                  }}
                >
                  <img
                    src={photo.src}
                    alt={photo.caption}
                    loading="lazy"
                    style={{
                      display: "block",
                      width: "100%",
                      height: "auto",
                      maxHeight: "200px",
                      objectFit: "cover",
                    }}
                  />
                  <figcaption
                    style={{
                      padding: "8px 10px",
                      fontSize: "11.5px",
                      lineHeight: 1.45,
                      color: "#475569",
                    }}
                  >
                    <div style={{ fontWeight: 600, color: "#1e293b" }}>{photo.caption}</div>
                    <div style={{ marginTop: "2px", color: "#64748b" }}>
                      拍摄年份：{photo.year} · 来源：{photo.sourceLabel}
                    </div>
                  </figcaption>
                </figure>
              ))}
            </div>
          )}
        </section>
      </div>
    </aside>
  );
}
