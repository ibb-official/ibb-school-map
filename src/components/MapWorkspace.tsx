"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CAMPUSES } from "@/data/campuses";
import {
  CATEGORY_COLORS,
  CATEGORY_LABELS,
  getPlaceById,
  getPlacesByCampus,
} from "@/data/places";
import { getToursByCampus } from "@/data/tours";
import {
  AtmosphereState,
  CameraTourStop,
  CampusId,
  PlaceCategory,
  ViewMode,
} from "@/data/types";
import { getCurrentBeijingTimeHours, presetToTimeHours } from "@/scene/sunAstronomy";
import { CameraTourBar } from "./CameraTourBar";
import { CampusMap2D } from "./CampusMap2D";
import { CampusScene3D } from "./CampusScene3D";
import { Footer } from "./Footer";
import { Header } from "./Header";
import {
  CloseIcon,
  CompassIcon,
  CubeIcon,
  ListIcon,
  MapLayersIcon,
  PinIcon,
  ResetIcon,
  SearchIcon,
} from "./Icons";
import { PlaceDetailDrawer } from "./PlaceDetailDrawer";

const INITIAL_ATMOSPHERE: AtmosphereState = {
  // Deterministic SSR initial hour; immediately synced to live Beijing local time on client mount
  timeHours: 9.5,
  syncBeijingTime: true,
  weather: "clear",
  quality: "refined",
  autoPlay: false,
  pathTracingActive: false,
};

export function MapWorkspace() {
  const [campusId, setCampusId] = useState<CampusId>("west");
  const [viewMode, setViewMode] = useState<ViewMode>("3d");
  const [atmosphere, setAtmosphere] = useState<AtmosphereState>(INITIAL_ATMOSPHERE);
  const [showPins, setShowPins] = useState<boolean>(true);
  const [directoryOpen, setDirectoryOpen] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeCategory, setActiveCategory] = useState<PlaceCategory | "all">("all");
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const [activeTourId, setActiveTourId] = useState<string | null>("tour-w-overview");
  const [webglFallbackMsg, setWebglFallbackMsg] = useState<string | null>(null);

  // Client hydration: sync default time to real Beijing local time & adapt layout/tier for mobile screens
  useEffect(() => {
    if (typeof window === "undefined") return;
    const isNarrow = window.innerWidth < 860;
    if (isNarrow) {
      setDirectoryOpen(false);
    }
    setAtmosphere((prev) => ({
      ...prev,
      timeHours: getCurrentBeijingTimeHours(),
      quality: window.innerWidth < 768 ? "smooth" : prev.quality,
    }));
  }, []);

  // Keep Beijing clock synchronized every 30s while syncBeijingTime mode is active
  useEffect(() => {
    if (!atmosphere.syncBeijingTime) return;
    const timer = window.setInterval(() => {
      setAtmosphere((prev) =>
        prev.syncBeijingTime
          ? { ...prev, timeHours: getCurrentBeijingTimeHours() }
          : prev
      );
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [atmosphere.syncBeijingTime]);

  const [cameraFlight, setCameraFlight] = useState<{
    id: number;
    cameraPos: [number, number, number];
    cameraTarget: [number, number, number];
  } | null>(null);

  const campus = CAMPUSES[campusId];
  const allCampusPlaces = useMemo(() => getPlacesByCampus(campusId), [campusId]);
  const campusTours = useMemo(() => getToursByCampus(campusId), [campusId]);

  const filteredPlaces = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return allCampusPlaces.filter((place) => {
      if (activeCategory !== "all" && place.category !== activeCategory) {
        return false;
      }
      if (!q) return true;
      return (
        place.name.toLowerCase().includes(q) ||
        place.shortName.toLowerCase().includes(q) ||
        place.code.toLowerCase().includes(q) ||
        place.summary.toLowerCase().includes(q)
      );
    });
  }, [allCampusPlaces, activeCategory, searchQuery]);

  const selectedPlace = useMemo(
    () => (selectedPlaceId ? getPlaceById(selectedPlaceId) ?? null : null),
    [selectedPlaceId]
  );

  const handleAtmosphereChange = useCallback((patch: Partial<AtmosphereState>) => {
    setAtmosphere((prev) => ({ ...prev, ...patch }));
  }, []);

  const handleSyncBeijingNow = useCallback(() => {
    setAtmosphere((prev) => ({
      ...prev,
      timeHours: getCurrentBeijingTimeHours(),
      syncBeijingTime: true,
      autoPlay: false,
    }));
  }, []);

  const triggerFlight = (
    cameraPos: [number, number, number],
    cameraTarget: [number, number, number]
  ) => {
    setCameraFlight({
      id: Date.now() + Math.random(),
      cameraPos,
      cameraTarget,
    });
  };

  const handleSwitchCampus = (nextCampus: CampusId) => {
    setCampusId(nextCampus);
    setViewMode(webglFallbackMsg ? "2d" : "3d");
    setActiveCategory("all");
    setSearchQuery("");
    setSelectedPlaceId(null);
    setActiveTourId(nextCampus === "west" ? "tour-w-overview" : "tour-e-overview");
    setCameraFlight(null);
    setAtmosphere((prev) =>
      prev.pathTracingActive ? { ...prev, pathTracingActive: false } : prev
    );
  };

  const handleSelectPlace = (placeId: string | null) => {
    setSelectedPlaceId(placeId);
    if (!placeId) return;
    const place = getPlaceById(placeId);
    if (place) {
      setActiveTourId(null);
      if (place.campusId !== campusId) {
        setCampusId(place.campusId);
        setAtmosphere((prev) =>
          prev.pathTracingActive ? { ...prev, pathTracingActive: false } : prev
        );
      }
      if (viewMode === "3d") {
        triggerFlight(place.cameraPos, place.cameraTarget);
      }
    }
  };

  const handleSelectTour = (tour: CameraTourStop) => {
    setActiveTourId(tour.id);
    if (tour.lightingSuggestion) {
      setAtmosphere((prev) => ({
        ...prev,
        timeHours: presetToTimeHours(tour.lightingSuggestion!),
        syncBeijingTime: false,
        autoPlay: false,
      }));
    }
    if (tour.highlightPlaceId) {
      setSelectedPlaceId(tour.highlightPlaceId);
    }
    if (viewMode !== "3d" && !webglFallbackMsg) {
      setViewMode("3d");
    }
    triggerFlight(tour.cameraPos, tour.cameraTarget);
  };

  const handleResetView = () => {
    setActiveTourId(campusId === "west" ? "tour-w-overview" : "tour-e-overview");
    triggerFlight(campus.defaultCameraPos, campus.defaultCameraTarget);
  };

  const handleWebGLError = (reason: string) => {
    setWebglFallbackMsg(reason);
    setAtmosphere((prev) => ({ ...prev, pathTracingActive: false }));
    setViewMode("2d");
  };

  return (
    <>
      <Header activeRoute="map" />

      <main className="workspace-main">
        {/* Top Interactive Control Strip */}
        <div className="top-control-strip">
          <div className="top-control-inner">
            <div className="segmented-group" role="tablist" aria-label="校区及总览切换">
              <button
                type="button"
                role="tab"
                aria-selected={viewMode !== "overview" && campusId === "west"}
                className={`seg-btn ${
                  viewMode !== "overview" && campusId === "west" ? "seg-btn-active" : ""
                }`}
                onClick={() => handleSwitchCampus("west")}
              >
                西校区（同福夹道3号）
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={viewMode !== "overview" && campusId === "east"}
                className={`seg-btn ${
                  viewMode !== "overview" && campusId === "east" ? "seg-btn-active" : ""
                }`}
                onClick={() => handleSwitchCampus("east")}
              >
                东校区（东四六条甲44号）
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={viewMode === "overview"}
                className={`seg-btn ${viewMode === "overview" ? "seg-btn-active" : ""}`}
                onClick={() => {
                  setViewMode("overview");
                  setSelectedPlaceId(null);
                  setAtmosphere((prev) =>
                    prev.pathTracingActive ? { ...prev, pathTracingActive: false } : prev
                  );
                }}
              >
                <MapLayersIcon size={14} />
                <span>双校同城总览 (1.24km)</span>
              </button>
            </div>

            <div className="toolbar-actions">
              <div className="segmented-group" role="group" aria-label="维度切换">
                <button
                  type="button"
                  className={`seg-btn ${viewMode === "3d" ? "seg-btn-active" : ""}`}
                  onClick={() => {
                    if (!webglFallbackMsg) setViewMode("3d");
                  }}
                  disabled={Boolean(webglFallbackMsg)}
                  title={webglFallbackMsg ?? "切换实时三维视角"}
                >
                  <CubeIcon size={14} />
                  <span>3D 模型</span>
                </button>
                <button
                  type="button"
                  className={`seg-btn ${viewMode === "2d" ? "seg-btn-active" : ""}`}
                  onClick={() => {
                    setAtmosphere((prev) =>
                      prev.pathTracingActive ? { ...prev, pathTracingActive: false } : prev
                    );
                    setViewMode("2d");
                  }}
                >
                  <span>2D 平面图</span>
                </button>
              </div>

              {viewMode === "3d" && (
                <>
                  <button
                    type="button"
                    className={`tool-btn ${showPins ? "tool-btn-active" : ""}`}
                    onClick={() => setShowPins((v) => !v)}
                  >
                    <PinIcon size={14} />
                    <span>{showPins ? "隐藏标签" : "显示标签"}</span>
                  </button>

                  <button type="button" className="tool-btn" onClick={handleResetView}>
                    <ResetIcon size={14} />
                    <span>复位视角</span>
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Interactive Stage */}
        <div className="viewport-stage">
          {viewMode === "3d" ? (
            <CampusScene3D
              campus={campus}
              places={allCampusPlaces}
              selectedPlaceId={selectedPlaceId}
              atmosphere={atmosphere}
              showPins={showPins}
              cameraFlightRequest={cameraFlight}
              onSelectPlace={handleSelectPlace}
              onAtmosphereChange={handleAtmosphereChange}
              onSyncBeijingNow={handleSyncBeijingNow}
              onWebGLError={handleWebGLError}
            />
          ) : (
            <CampusMap2D
              mode={viewMode}
              campusId={campusId}
              places={allCampusPlaces}
              selectedPlaceId={selectedPlaceId}
              fallbackNotice={webglFallbackMsg}
              onSelectPlace={(pid) => handleSelectPlace(pid)}
              onEnterCampus3D={handleSwitchCampus}
            />
          )}

          {/* Left Collapsible Building Directory */}
          {viewMode !== "overview" && (
            <>
              {!directoryOpen && (
                <button
                  type="button"
                  className="reopen-dir-btn"
                  onClick={() => setDirectoryOpen(true)}
                >
                  <ListIcon size={15} />
                  <span>点位索引 ({allCampusPlaces.length})</span>
                </button>
              )}

              <aside
                className={`directory-panel ${
                  directoryOpen ? "" : "directory-panel-collapsed"
                }`}
                aria-label="校园建筑与景观目录"
              >
                <div className="directory-header">
                  <div className="directory-title-row">
                    <div>
                      <h2 className="directory-title">{campus.name}</h2>
                      <p className="directory-address">{campus.address}</p>
                    </div>
                    <button
                      type="button"
                      className="icon-close-btn"
                      onClick={() => setDirectoryOpen(false)}
                      aria-label="收起目录"
                    >
                      <CloseIcon size={14} />
                    </button>
                  </div>

                  <div className="search-box">
                    <span className="search-icon">
                      <SearchIcon size={14} />
                    </span>
                    <input
                      type="search"
                      className="search-input"
                      placeholder="搜索建筑编号或名称（如 B座、坡道、篮球场）"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>

                  <div className="category-chips">
                    <button
                      type="button"
                      className={`chip-btn ${
                        activeCategory === "all" ? "chip-btn-active" : ""
                      }`}
                      onClick={() => setActiveCategory("all")}
                    >
                      全部 ({allCampusPlaces.length})
                    </button>
                    {(Object.keys(CATEGORY_LABELS) as PlaceCategory[]).map((cat) => (
                      <button
                        key={cat}
                        type="button"
                        className={`chip-btn ${
                          activeCategory === cat ? "chip-btn-active" : ""
                        }`}
                        onClick={() => setActiveCategory(cat)}
                      >
                        {CATEGORY_LABELS[cat]}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="directory-list">
                  {filteredPlaces.length === 0 ? (
                    <div
                      style={{
                        padding: "20px 10px",
                        textAlign: "center",
                        fontSize: "12.5px",
                        color: "#64748b",
                      }}
                    >
                      未找到匹配的建筑或景点
                    </div>
                  ) : (
                    filteredPlaces.map((place) => {
                      const active = place.id === selectedPlaceId;
                      return (
                        <button
                          key={place.id}
                          type="button"
                          className={`place-item-btn ${
                            active ? "place-item-btn-active" : ""
                          }`}
                          onClick={() => handleSelectPlace(place.id)}
                        >
                          <span
                            className="place-code-pill"
                            style={{ backgroundColor: CATEGORY_COLORS[place.category] }}
                          >
                            {place.code}
                          </span>
                          <div style={{ minWidth: 0, flex: 1 }}>
                            <div className="place-item-name">{place.name}</div>
                            <div className="place-item-meta">
                              {place.storiesLabel}
                              {place.photoRefs.length > 0
                                ? ` · 附实拍照片 (${place.photoRefs.length})`
                                : ""}
                            </div>
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </aside>
            </>
          )}

          {/* Bottom Camera Tour Presets in 3D Mode */}
          {viewMode === "3d" && (
            <CameraTourBar
              tours={campusTours}
              activeTourId={activeTourId}
              onSelectTour={handleSelectTour}
            />
          )}

          {/* Right/Mobile Place Detail Drawer */}
          {selectedPlace && viewMode !== "overview" && (
            <PlaceDetailDrawer
              place={selectedPlace}
              viewMode={viewMode}
              onClose={() => setSelectedPlaceId(null)}
              onFocus3D={(p) => triggerFlight(p.cameraPos, p.cameraTarget)}
            />
          )}

          {/* Subtle Mode Hint when in 2D */}
          {viewMode === "2d" && !selectedPlace && (
            <div
              className="tour-dock"
              style={{ fontSize: "12px", padding: "7px 16px" }}
            >
              <CompassIcon size={14} />
              <span>点击平面图中高亮建筑物即可查阅详情与实景照</span>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </>
  );
}
