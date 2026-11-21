"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import {
  detectDeviceProfile,
  MOBILE_SHELL_MEDIA_QUERY,
} from "@/scene/deviceProfile";
import type { PathTracerStatus } from "@/scene/pathTracerController";
import {
  formatTimeHours,
  getCurrentBeijingTimeHours,
  presetToTimeHours,
} from "@/scene/sunAstronomy";
import { AtmosphereDock } from "./AtmosphereDock";
import { CameraTourBar } from "./CameraTourBar";
import { CampusMap2D } from "./CampusMap2D";
import { CampusScene3D, TouchNavMode } from "./CampusScene3D";
import { Footer } from "./Footer";
import { Header } from "./Header";
import {
  CloseIcon,
  CompassIcon,
  CubeIcon,
  ExternalIcon,
  GridMapIcon,
  HandIcon,
  InfoIcon,
  ListIcon,
  MapLayersIcon,
  MoonIcon,
  OrbitIcon,
  PinIcon,
  ResetIcon,
  SearchIcon,
  SparklesIcon,
  SunIcon,
} from "./Icons";
import { MobileBottomSheet, SheetSnap } from "./MobileBottomSheet";
import { PlaceDetailDrawer } from "./PlaceDetailDrawer";

type MobileSheetKind = "none" | "directory" | "place" | "atmosphere" | "more";

const INITIAL_ATMOSPHERE: AtmosphereState = {
  // Deterministic SSR initial hour; immediately synced to live Beijing local time on client mount
  timeHours: 9.5,
  syncBeijingTime: true,
  weather: "clear",
  quality: "refined",
  autoPlay: false,
  pathTracingActive: false,
};

const INITIAL_PT_STATUS: PathTracerStatus = {
  phase: "idle",
  samples: 0,
  targetSamples: 128,
};

export function MapWorkspace() {
  const [campusId, setCampusId] = useState<CampusId>("west");
  const [viewMode, setViewMode] = useState<ViewMode>("3d");
  const [atmosphere, setAtmosphere] = useState<AtmosphereState>(INITIAL_ATMOSPHERE);
  const [userSelectedQuality, setUserSelectedQuality] = useState<boolean>(false);
  const [showPins, setShowPins] = useState<boolean>(true);
  const [directoryOpen, setDirectoryOpen] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeCategory, setActiveCategory] = useState<PlaceCategory | "all">("all");
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const [activeTourId, setActiveTourId] = useState<string | null>("tour-w-overview");
  const [webglFallbackMsg, setWebglFallbackMsg] = useState<string | null>(null);

  // Mobile-specific shell & mutually exclusive sheet state
  const [isMobileShell, setIsMobileShell] = useState<boolean>(false);
  const [isMobileTier, setIsMobileTier] = useState<boolean>(false);
  const [mobileSheet, setMobileSheet] = useState<MobileSheetKind>("none");
  const [placeSheetSnap, setPlaceSheetSnap] = useState<SheetSnap>("peek");
  const [touchNavMode, setTouchNavMode] = useState<TouchNavMode>("rotate");
  const [pathTracerStatus, setPathTracerStatus] = useState<PathTracerStatus>(INITIAL_PT_STATUS);
  const [isSceneLoaded, setIsSceneLoaded] = useState<boolean>(false);

  const mobileCompassDialRef = useRef<HTMLDivElement | null>(null);
  const alignNorthRef = useRef<(() => void) | null>(null);
  const exportPhotoRef = useRef<(() => void) | null>(null);
  const map2dResetRef = useRef<(() => void) | null>(null);

  // Client hydration: sync live Beijing time, detect mobile capability & listen to viewport/orientation changes
  useEffect(() => {
    if (typeof window === "undefined") return;
    const profile = detectDeviceProfile();
    const mql = window.matchMedia(MOBILE_SHELL_MEDIA_QUERY);

    const syncShell = (matches: boolean) => {
      setIsMobileShell(matches);
      if (matches) {
        setDirectoryOpen(false);
      } else {
        setMobileSheet("none");
      }
    };

    syncShell(mql.matches);
    setIsMobileTier(profile.isMobileTier);

    setAtmosphere((prev) => ({
      ...prev,
      timeHours: getCurrentBeijingTimeHours(),
      quality: profile.isMobileTier ? "smooth" : prev.quality,
    }));

    const handleMediaChange = (ev: MediaQueryListEvent) => syncShell(ev.matches);
    mql.addEventListener("change", handleMediaChange);
    return () => mql.removeEventListener("change", handleMediaChange);
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
    if (patch.quality !== undefined) {
      setUserSelectedQuality(true);
    }
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
    setMobileSheet("none");
    setAtmosphere((prev) =>
      prev.pathTracingActive ? { ...prev, pathTracingActive: false } : prev
    );
  };

  const handleEnterOverview = () => {
    setViewMode("overview");
    setSelectedPlaceId(null);
    setMobileSheet("none");
    setAtmosphere((prev) =>
      prev.pathTracingActive ? { ...prev, pathTracingActive: false } : prev
    );
  };

  const handleToggleDimension = (nextMode: "3d" | "2d") => {
    if (nextMode === "3d") {
      if (webglFallbackMsg) return;
      setViewMode("3d");
    } else {
      setAtmosphere((prev) =>
        prev.pathTracingActive ? { ...prev, pathTracingActive: false } : prev
      );
      setViewMode("2d");
      if (mobileSheet === "atmosphere") {
        setMobileSheet("none");
      }
    }
  };

  const handleSelectPlace = (placeId: string | null) => {
    setSelectedPlaceId(placeId);
    if (!placeId) {
      if (mobileSheet === "place") setMobileSheet("none");
      return;
    }
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
      if (isMobileShell) {
        setDirectoryOpen(false);
        setPlaceSheetSnap("peek");
        setMobileSheet("place");
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
    } else if (isMobileShell) {
      setSelectedPlaceId(null);
    }
    if (viewMode !== "3d" && !webglFallbackMsg) {
      setViewMode("3d");
    }
    // On mobile, keep bottom tour strip unobstructed so user can step smoothly across stops
    if (isMobileShell && mobileSheet !== "none") {
      setMobileSheet("none");
    }
    triggerFlight(tour.cameraPos, tour.cameraTarget);
  };

  const handleResetView = () => {
    if (viewMode === "2d") {
      map2dResetRef.current?.();
      return;
    }
    setActiveTourId(campusId === "west" ? "tour-w-overview" : "tour-e-overview");
    triggerFlight(campus.defaultCameraPos, campus.defaultCameraTarget);
  };

  const handleWebGLError = useCallback((reason: string) => {
    setWebglFallbackMsg(reason);
    setAtmosphere((prev) => ({ ...prev, pathTracingActive: false }));
    setViewMode("2d");
    setMobileSheet((prev) => (prev === "atmosphere" ? "none" : prev));
  }, []);

  const handleClosePlaceDetail = () => {
    setSelectedPlaceId(null);
    if (mobileSheet === "place") {
      setMobileSheet("none");
    }
  };

  const isNight = atmosphere.timeHours < 5.5 || atmosphere.timeHours >= 18.8;
  const compactTimeStr = formatTimeHours(atmosphere.timeHours);

  // Reusable directory search + category filter + list (shared between desktop sidebar & mobile bottom sheet)
  const directorySearchAndFilters = (
    <>
      <div className="search-box">
        <span className="search-icon">
          <SearchIcon size={15} />
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
          className={`chip-btn ${activeCategory === "all" ? "chip-btn-active" : ""}`}
          onClick={() => setActiveCategory("all")}
        >
          全部 ({allCampusPlaces.length})
        </button>
        {(Object.keys(CATEGORY_LABELS) as PlaceCategory[]).map((cat) => (
          <button
            key={cat}
            type="button"
            className={`chip-btn ${activeCategory === cat ? "chip-btn-active" : ""}`}
            onClick={() => setActiveCategory(cat)}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>
    </>
  );

  const directoryListItems =
    filteredPlaces.length === 0 ? (
      <div
        style={{
          padding: "24px 10px",
          textAlign: "center",
          fontSize: "13px",
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
            className={`place-item-btn ${active ? "place-item-btn-active" : ""}`}
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
    );

  // Compact single-row mobile top bar rendered inside Header (shown only on mobile via CSS)
  const mobileMapTopbar = (
    <>
      <Link href="/" className="mobile-brand-compact" aria-label="北京 166 中学三维校园地图（非官方）">
        <img
          src="/maps/map-mark.svg"
          alt=""
          className="mobile-brand-mark"
          width={26}
          height={26}
        />
        <span className="mobile-brand-text">
          <span className="mobile-brand-name">166地图</span>
          <span className="unofficial" lang="en">
            unofficial
          </span>
        </span>
      </Link>

      <div className="mobile-campus-seg" role="tablist" aria-label="校区及总览切换">
        <button
          type="button"
          role="tab"
          aria-selected={viewMode !== "overview" && campusId === "west"}
          className={`mobile-seg-btn ${
            viewMode !== "overview" && campusId === "west" ? "mobile-seg-btn-active" : ""
          }`}
          onClick={() => handleSwitchCampus("west")}
        >
          西校
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={viewMode !== "overview" && campusId === "east"}
          className={`mobile-seg-btn ${
            viewMode !== "overview" && campusId === "east" ? "mobile-seg-btn-active" : ""
          }`}
          onClick={() => handleSwitchCampus("east")}
        >
          东校
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === "overview"}
          className={`mobile-seg-btn ${
            viewMode === "overview" ? "mobile-seg-btn-active" : ""
          }`}
          onClick={handleEnterOverview}
        >
          总览
        </button>
      </div>

      <button
        type="button"
        className={`mobile-topbar-info-btn ${mobileSheet === "more" ? "mobile-topbar-info-btn-active" : ""}`}
        onClick={() => setMobileSheet((prev) => (prev === "more" ? "none" : "more"))}
        aria-label="关于项目与免责声明"
        title="关于项目、免责声明与更多链接"
      >
        <InfoIcon size={18} />
      </button>
    </>
  );

  return (
    <>
      <Header activeRoute="map" mobileMapTopbar={mobileMapTopbar} />

      <main className="workspace-main">
        {/* Desktop Top Interactive Control Strip (hidden on mobile; consolidated into topbar + right rail) */}
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
                onClick={handleEnterOverview}
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
                  onClick={() => handleToggleDimension("3d")}
                  disabled={Boolean(webglFallbackMsg)}
                  title={webglFallbackMsg ?? "切换实时三维视角"}
                >
                  <CubeIcon size={14} />
                  <span>3D 模型</span>
                </button>
                <button
                  type="button"
                  className={`seg-btn ${viewMode === "2d" ? "seg-btn-active" : ""}`}
                  onClick={() => handleToggleDimension("2d")}
                >
                  <span>2D 平面图</span>
                </button>
              </div>

              {viewMode === "3d" && (
                <>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={atmosphere.quality === "cinematic"}
                    className={`tool-btn tool-btn-ultra ${
                      atmosphere.quality === "cinematic" ? "tool-btn-ultra-active" : ""
                    }`}
                    onClick={() =>
                      handleAtmosphereChange({
                        quality: atmosphere.quality === "cinematic" ? "refined" : "cinematic",
                      })
                    }
                    title="开启极致画质：4096 级校园全域阴影、超采样高分渲染、全分辨率精细环境光遮蔽与锐化增强"
                  >
                    <SparklesIcon size={14} />
                    <span>{atmosphere.quality === "cinematic" ? "极致画质：开" : "极致画质"}</span>
                  </button>

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
              userSelectedQuality={userSelectedQuality}
              showPins={showPins}
              touchNavMode={touchNavMode}
              isMobileShell={isMobileShell}
              mobileCompassDialRef={mobileCompassDialRef}
              alignNorthRef={alignNorthRef}
              exportPhotoRef={exportPhotoRef}
              cameraFlightRequest={cameraFlight}
              onSelectPlace={handleSelectPlace}
              onAtmosphereChange={handleAtmosphereChange}
              onSyncBeijingNow={handleSyncBeijingNow}
              onPathTracerStatusChange={setPathTracerStatus}
              onLoadedChange={setIsSceneLoaded}
              onWebGLError={handleWebGLError}
            />
          ) : (
            <CampusMap2D
              mode={viewMode}
              campusId={campusId}
              places={allCampusPlaces}
              selectedPlaceId={selectedPlaceId}
              fallbackNotice={webglFallbackMsg}
              resetViewRef={map2dResetRef}
              onSelectPlace={(pid) => handleSelectPlace(pid)}
              onEnterCampus3D={handleSwitchCampus}
            />
          )}

          {/* Desktop Left Collapsible Building Directory (hidden via CSS on mobile) */}
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

                  {directorySearchAndFilters}
                </div>

                <div className="directory-list">{directoryListItems}</div>
              </aside>
            </>
          )}

          {/* Desktop Bottom Camera Tour Presets in 3D Mode */}
          {viewMode === "3d" && !isMobileShell && (
            <CameraTourBar
              tours={campusTours}
              activeTourId={activeTourId}
              onSelectTour={handleSelectTour}
              variant="floating"
            />
          )}

          {/* Desktop Right Place Detail Drawer */}
          {selectedPlace && viewMode !== "overview" && !isMobileShell && (
            <PlaceDetailDrawer
              place={selectedPlace}
              viewMode={viewMode}
              isMobileShell={false}
              onClose={handleClosePlaceDetail}
              onFocus3D={(p) => triggerFlight(p.cameraPos, p.cameraTarget)}
            />
          )}

          {/* Desktop Subtle Mode Hint when in 2D */}
          {viewMode === "2d" && !selectedPlace && !isMobileShell && (
            <div
              className="tour-dock"
              style={{ fontSize: "12px", padding: "7px 16px" }}
            >
              <CompassIcon size={14} />
              <span>滚轮/双指缩放 · 拖拽平移 · 点击建筑物查看详情与实景照</span>
            </div>
          )}

          {/* ================= MOBILE COMPACT FLOATING SHELL ================= */}
          {viewMode !== "overview" && (
            <div
              className={`mobile-action-rail${
                mobileSheet === "directory" || mobileSheet === "more"
                  ? " mobile-action-rail-dimmed"
                  : ""
              }`}
              aria-label="地图快捷操作栏"
            >
              {viewMode === "3d" && (
                <button
                  type="button"
                  className="mobile-rail-btn mobile-rail-compass"
                  onClick={() => alignNorthRef.current?.()}
                  aria-label="方向指北针：点击回正为上北下南"
                  title="点击回正北向"
                >
                  <div ref={mobileCompassDialRef} className="mobile-compass-dial">
                    <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
                      <circle cx="16" cy="16" r="13.5" fill="none" stroke="rgba(11,63,112,0.16)" strokeWidth="1.2" />
                      <polygon points="16,4.5 13,16 16,14.5 19,16" fill="#c9332b" />
                      <polygon points="16,27.5 13,16 16,17.5 19,16" fill="#94a3b8" />
                      <circle cx="16" cy="16" r="1.8" fill="#0b3f70" />
                    </svg>
                    <span className="mobile-compass-n">北</span>
                  </div>
                </button>
              )}

              <button
                type="button"
                className="mobile-rail-btn"
                onClick={() => handleToggleDimension(viewMode === "3d" ? "2d" : "3d")}
                disabled={viewMode === "2d" && Boolean(webglFallbackMsg)}
                aria-label={viewMode === "3d" ? "切换到 2D 平面图" : "切换到 3D 模型"}
              >
                {viewMode === "3d" ? <GridMapIcon size={17} /> : <CubeIcon size={17} />}
                <span className="mobile-rail-label">{viewMode === "3d" ? "2D" : "3D"}</span>
              </button>

              {viewMode === "3d" && (
                <>
                  <button
                    type="button"
                    className={`mobile-rail-btn ${
                      touchNavMode === "pan" ? "mobile-rail-btn-active" : ""
                    }`}
                    onClick={() =>
                      setTouchNavMode((m) => (m === "rotate" ? "pan" : "rotate"))
                    }
                    aria-label={
                      touchNavMode === "rotate"
                        ? "当前单指旋转，点击切换为单指平移"
                        : "当前单指平移，点击切换为单指旋转"
                    }
                  >
                    {touchNavMode === "rotate" ? (
                      <OrbitIcon size={17} />
                    ) : (
                      <HandIcon size={17} />
                    )}
                    <span className="mobile-rail-label">
                      {touchNavMode === "rotate" ? "旋转" : "平移"}
                    </span>
                  </button>

                  <button
                    type="button"
                    className={`mobile-rail-btn ${showPins ? "mobile-rail-btn-active" : ""}`}
                    onClick={() => setShowPins((v) => !v)}
                    aria-label={showPins ? "隐藏建筑标签" : "显示建筑标签"}
                  >
                    <PinIcon size={17} />
                    <span className="mobile-rail-label">标签</span>
                  </button>

                  <button
                    type="button"
                    className={`mobile-rail-btn mobile-rail-atmo ${
                      mobileSheet === "atmosphere" || atmosphere.pathTracingActive
                        ? "mobile-rail-atmo-active"
                        : ""
                    }`}
                    onClick={() =>
                      setMobileSheet((prev) =>
                        prev === "atmosphere" ? "none" : "atmosphere"
                      )
                    }
                    aria-label="调节时间、天气与画质"
                  >
                    <span
                      className={`mobile-atmo-dot ${
                        isNight ? "atmo-orb-night" : "atmo-orb-day"
                      }`}
                    >
                      {isNight ? <MoonIcon size={12} /> : <SunIcon size={12} />}
                    </span>
                    <span className="mobile-rail-time">{compactTimeStr}</span>
                  </button>
                </>
              )}

              <button
                type="button"
                className="mobile-rail-btn"
                onClick={handleResetView}
                aria-label="复位视角"
              >
                <ResetIcon size={17} />
                <span className="mobile-rail-label">复位</span>
              </button>
            </div>
          )}

          {/* Mobile Idle Bottom Dock: Directory trigger + Horizontal Tour Strip (hidden when a sheet is open) */}
          {viewMode !== "overview" && mobileSheet === "none" && (
            <div className="mobile-bottom-dock">
              <button
                type="button"
                className="mobile-dir-trigger-btn"
                onClick={() => setMobileSheet("directory")}
                aria-label={`打开校园点位索引（共 ${allCampusPlaces.length} 个）`}
              >
                <SearchIcon size={15} />
                <span>点位 ({allCampusPlaces.length})</span>
              </button>

              {viewMode === "3d" ? (
                <div className="mobile-tour-scroll-wrap">
                  <CameraTourBar
                    tours={campusTours}
                    activeTourId={activeTourId}
                    onSelectTour={handleSelectTour}
                    variant="inline"
                  />
                </div>
              ) : (
                <div className="mobile-2d-hint-inline">
                  单指拖动 · 双指缩放 · 点选建筑
                </div>
              )}
            </div>
          )}

          {/* Mobile Mutually Exclusive Sheets */}
          {isMobileShell && viewMode !== "overview" && (
            <>
              {/* 1. Directory Bottom Sheet */}
              <MobileBottomSheet
                open={mobileSheet === "directory"}
                onClose={() => setMobileSheet("none")}
                ariaLabel="校园建筑与景观目录"
                variant="single"
                theme="light"
                modalBackdrop
                header={
                  <div className="mobile-dir-sheet-header">
                    <div className="directory-title-row">
                      <div>
                        <h2 className="directory-title">{campus.name}</h2>
                        <p className="directory-address">{campus.address}</p>
                      </div>
                      <button
                        type="button"
                        className="icon-close-btn mobile-touch-btn"
                        onClick={() => setMobileSheet("none")}
                        aria-label="关闭目录"
                      >
                        <CloseIcon size={16} />
                      </button>
                    </div>
                    {directorySearchAndFilters}
                  </div>
                }
              >
                <div className="directory-list mobile-dir-sheet-list">
                  {directoryListItems}
                </div>
              </MobileBottomSheet>

              {/* 2. Two-Stage Place Detail Sheet (Peek summary <-> Expanded full details) */}
              {mobileSheet === "place" && selectedPlace && (
                <PlaceDetailDrawer
                  place={selectedPlace}
                  viewMode={viewMode}
                  isMobileShell
                  mobileSnap={placeSheetSnap}
                  onMobileSnapChange={setPlaceSheetSnap}
                  onClose={handleClosePlaceDetail}
                  onFocus3D={(p) => triggerFlight(p.cameraPos, p.cameraTarget)}
                />
              )}

              {/* 3. Live Atmosphere / Time / Weather / Quality Bottom Sheet (no dim backdrop so 3D updates live above!) */}
              {viewMode === "3d" && (
                <MobileBottomSheet
                  open={mobileSheet === "atmosphere"}
                  onClose={() => setMobileSheet("none")}
                  ariaLabel="三维天光、时间、天气与光线追踪控制台"
                  variant="single"
                  theme="dark"
                  modalBackdrop={false}
                  className="mobile-atmo-sheet"
                >
                  <AtmosphereDock
                    state={atmosphere}
                    pathTracerStatus={pathTracerStatus}
                    variant="sheet"
                    isMobileTier={isMobileTier}
                    onChange={handleAtmosphereChange}
                    onSyncBeijingNow={handleSyncBeijingNow}
                    onExportPhoto={() => exportPhotoRef.current?.()}
                    onCloseSheet={() => setMobileSheet("none")}
                  />
                  {!isSceneLoaded && (
                    <p className="atmo-mobile-rt-hint" style={{ padding: "0 14px 10px" }}>
                      模型加载完成后将自动应用当前选择的时间与天气。
                    </p>
                  )}
                </MobileBottomSheet>
              )}
            </>
          )}

          {/* 4. Mobile More / About / Disclaimer Sheet (available in all modes including overview) */}
          {isMobileShell && (
            <MobileBottomSheet
              open={mobileSheet === "more"}
              onClose={() => setMobileSheet("none")}
              ariaLabel="项目信息与免责声明"
              variant="single"
              theme="light"
              modalBackdrop
              header={
                <div className="mobile-more-header">
                  <div>
                    <div className="mobile-more-title">
                      北京 166 中学 · 三维校园地图
                      <span className="unofficial" lang="en">
                        unofficial
                      </span>
                    </div>
                    <p className="mobile-more-sub">
                      非官方校友与同学共建项目 · 仅供校园建筑与空间参考
                    </p>
                  </div>
                  <button
                    type="button"
                    className="icon-close-btn mobile-touch-btn"
                    onClick={() => setMobileSheet("none")}
                    aria-label="关闭菜单"
                  >
                    <CloseIcon size={16} />
                  </button>
                </div>
              }
            >
              <div className="mobile-more-body">
                <div className="mobile-more-links">
                  <Link
                    href="/about"
                    className="mobile-more-link-row"
                    onClick={() => setMobileSheet("none")}
                  >
                    <span>关于本项目与建模说明</span>
                    <span className="mobile-more-arrow">›</span>
                  </Link>
                  <Link
                    href="/disclaimer"
                    className="mobile-more-link-row"
                    onClick={() => setMobileSheet("none")}
                  >
                    <span>免责声明与数据来源</span>
                    <span className="mobile-more-arrow">›</span>
                  </Link>
                  <a
                    href="https://bj166zx.cn"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mobile-more-link-row"
                  >
                    <span>校园文化站点（bj166zx.cn）</span>
                    <ExternalIcon size={14} />
                  </a>
                  <a
                    href="https://github.com/ibb-official/ibb-school-map"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mobile-more-link-row"
                  >
                    <span>GitHub 开源仓库</span>
                    <ExternalIcon size={14} />
                  </a>
                </div>

                <div className="mobile-more-guide">
                  <div className="mobile-more-guide-title">触屏操作指南</div>
                  <p>
                    3D 模式：单指{touchNavMode === "rotate" ? "旋转视角" : "平移地图"}、双指
                    {touchNavMode === "rotate" ? "缩放与平移" : "缩放与旋转"}（右侧按钮可随时切换单指模式）；点击建筑或标签查看详情与实拍图。
                  </p>
                  <p>
                    2D 模式：单指拖动平移、双指捏合缩放、双击空白处快速放大或复位。
                  </p>
                </div>

                <p className="mobile-more-copyright">
                  © 2026 ibb-official · 同学共建 · 地图数据 © OpenStreetMap contributors（ODbL）
                </p>
              </div>
            </MobileBottomSheet>
          )}
        </div>
      </main>

      <Footer className="site-footer-map" />
    </>
  );
}
