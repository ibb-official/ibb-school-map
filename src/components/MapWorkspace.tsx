"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ActionButton } from "@react-spectrum/s2/ActionButton";
import { Button } from "@react-spectrum/s2/Button";
import { Content, Heading, IllustratedMessage } from "@react-spectrum/s2/IllustratedMessage";
import { DialogTrigger, Popover } from "@react-spectrum/s2/Popover";
import { ToggleButton } from "@react-spectrum/s2/ToggleButton";
import { Tooltip, TooltipTrigger } from "@react-spectrum/s2/Tooltip";
import AlertTriangle from "@react-spectrum/s2/icons/AlertTriangle";
import Lighten from "@react-spectrum/s2/icons/Lighten";
import PinOff from "@react-spectrum/s2/icons/PinOff";
import PinOn from "@react-spectrum/s2/icons/PinOn";
import Refresh from "@react-spectrum/s2/icons/Refresh";
import Search from "@react-spectrum/s2/icons/Search";
import Settings from "@react-spectrum/s2/icons/Settings";
import TouchOneFingerSwipeLeftRight from "@react-spectrum/s2/icons/TouchOneFingerSwipeLeftRight";
import { CAMPUSES } from "@/data/campuses";
import { getPlaceById, getPlacesByCampus } from "@/data/places";
import { getToursByCampus } from "@/data/tours";
import {
  AtmosphereState,
  CameraTourStop,
  CampusId,
  ColorSchemePref,
  FlightInputVector,
  GraphicsSettings,
  MapUserPrefs,
  PlaceCategory,
} from "@/data/types";
import { MOBILE_SHELL_MEDIA_QUERY } from "@/scene/deviceProfile";
import type { PathTracerStatus } from "@/scene/pathTracerController";
import {
  getDefaultUserPrefs,
  graphicsSettingsEqual,
  loadUserPrefs,
  saveUserPrefs,
} from "@/scene/prefs";
import { CameraTourBar } from "./CameraTourBar";
import { CampusScene3D } from "./CampusScene3D";
import { CampusSwitcher } from "./CampusSwitcher";
import { DirectoryPanel } from "./DirectoryPanel";
import { HelpDialog } from "./HelpDialog";
import { MobileBottomSheet, SheetSnap } from "./MobileBottomSheet";
import { PlaceDetailDrawer } from "./PlaceDetailDrawer";
import { QualitySettingsContent } from "./QualitySettingsPopover";
import { useSpectrumTheme } from "./SpectrumProvider";
import { TopCornerBrandMenu } from "./TopCornerBrandMenu";
import { TouchFlightControls } from "./TouchFlightControls";

// Strictly code-split AtmosphereDock so Standard/Classic mode never loads time/weather UI
const LazyAtmosphereDock = dynamic(
  () => import("./AtmosphereDock").then((m) => m.AtmosphereDock),
  { ssr: false }
);

type MobileSheetKind = "none" | "directory" | "place" | "settings" | "atmosphere";

const INITIAL_ATMOSPHERE: AtmosphereState = {
  timeHours: 10.0,
  syncBeijingTime: true,
  weather: "clear",
  autoPlay: false,
  pathTracingActive: false,
};

const INITIAL_PT_STATUS: PathTracerStatus = {
  phase: "idle",
  samples: 0,
  targetSamples: 128,
};

function getCurrentBeijingHours(): number {
  const now = new Date();
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60_000;
  const bj = new Date(utcMs + 8 * 3_600_000);
  return bj.getHours() + bj.getMinutes() / 60 + bj.getSeconds() / 3600;
}

function formatCompactHour(hours: number): string {
  const w = ((hours % 24) + 24) % 24;
  const h = Math.floor(w);
  const m = Math.floor((w - h) * 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function MapWorkspace() {
  const { setColorScheme } = useSpectrumTheme();

  // Preferences loaded synchronously before first WebGL engine mount (zero wasted double-load!)
  const [prefsReady, setPrefsReady] = useState<boolean>(false);
  const [prefs, setPrefs] = useState<MapUserPrefs>(getDefaultUserPrefs);
  const [graphicsDraft, setGraphicsDraft] = useState<GraphicsSettings>(() => {
    const defaults = getDefaultUserPrefs();
    return {
      enhancedMap: defaults.enhancedMap,
      quality: defaults.quality,
    };
  });

  const [campusId, setCampusId] = useState<CampusId>("west");
  const [reloadNonce, setReloadNonce] = useState<number>(0);
  const [isMobileShell, setIsMobileShell] = useState<boolean>(false);

  // Panels & overlays (directory collapsed by default so landing immediately showcases full 3D campus)
  const [directoryOpen, setDirectoryOpen] = useState<boolean>(false);
  const [desktopAtmoOpen, setDesktopAtmoOpen] = useState<boolean>(false);
  const [desktopSettingsOpen, setDesktopSettingsOpen] = useState<boolean>(false);
  const [mobileSheet, setMobileSheet] = useState<MobileSheetKind>("none");
  const [placeSheetSnap, setPlaceSheetSnap] = useState<SheetSnap>("peek");
  const [helpOpen, setHelpOpen] = useState<boolean>(false);
  const [hintDismissed, setHintDismissed] = useState<boolean>(false);

  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeCategory, setActiveCategory] = useState<PlaceCategory | "all">("all");
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const [activeTourId, setActiveTourId] = useState<string | null>("tour-w-overview");
  const [webglError, setWebglError] = useState<string | null>(null);
  const [isSceneLoaded, setIsSceneLoaded] = useState<boolean>(false);

  // Enhanced-mode atmosphere & path tracer state
  const [atmosphere, setAtmosphere] = useState<AtmosphereState>(INITIAL_ATMOSPHERE);
  const [pathTracerStatus, setPathTracerStatus] = useState<PathTracerStatus>(INITIAL_PT_STATUS);

  const [cameraFlight, setCameraFlight] = useState<{
    id: number;
    cameraPos: [number, number, number];
    cameraTarget: [number, number, number];
  } | null>(null);

  const compassDialRef = useRef<HTMLDivElement | null>(null);
  const alignNorthRef = useRef<(() => void) | null>(null);
  const exportPhotoRef = useRef<(() => void) | null>(null);
  const virtualInputRef = useRef<FlightInputVector>({ moveX: 0, moveZ: 0, moveY: 0 });

  // Hydrate user prefs from localStorage BEFORE mounting 3D scene + track viewport breakpoint
  useEffect(() => {
    if (typeof window === "undefined") return;
    const loaded = loadUserPrefs();
    setPrefs(loaded);
    setGraphicsDraft({
      enhancedMap: loaded.enhancedMap,
      quality: loaded.quality,
    });
    setColorScheme(loaded.colorScheme);
    setPrefsReady(true);

    if (loaded.enhancedMap) {
      setAtmosphere((prev) => ({ ...prev, timeHours: getCurrentBeijingHours() }));
    }

    const mql = window.matchMedia(MOBILE_SHELL_MEDIA_QUERY);
    const syncShell = (matches: boolean) => {
      setIsMobileShell(matches);
      if (matches) {
        setDirectoryOpen(false);
        setDesktopAtmoOpen(false);
        setDesktopSettingsOpen(false);
      } else {
        setMobileSheet("none");
      }
    };
    syncShell(mql.matches);
    const handleMqlChange = (ev: MediaQueryListEvent) => syncShell(ev.matches);
    mql.addEventListener("change", handleMqlChange);
    return () => {
      mql.removeEventListener("change", handleMqlChange);
    };
  }, [setColorScheme]);

  // Keep Beijing clock synchronized ONLY when Enhanced Map is active & syncBeijingTime is on
  useEffect(() => {
    if (!prefs.enhancedMap || !atmosphere.syncBeijingTime) return;
    setAtmosphere((prev) =>
      prev.syncBeijingTime ? { ...prev, timeHours: getCurrentBeijingHours() } : prev
    );
    const timer = window.setInterval(() => {
      setAtmosphere((prev) =>
        prev.syncBeijingTime ? { ...prev, timeHours: getCurrentBeijingHours() } : prev
      );
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [prefs.enhancedMap, atmosphere.syncBeijingTime]);

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

  const activeGraphics: GraphicsSettings = useMemo(
    () => ({
      enhancedMap: prefs.enhancedMap,
      quality: prefs.quality,
    }),
    [prefs.enhancedMap, prefs.quality]
  );

  const hasPendingGraphicsChanges = useMemo(
    () => !graphicsSettingsEqual(graphicsDraft, activeGraphics),
    [graphicsDraft, activeGraphics]
  );

  const updatePrefs = useCallback((patch: Partial<MapUserPrefs>) => {
    setPrefs((prev) => {
      const next: MapUserPrefs = { ...prev, ...patch };
      saveUserPrefs(next);
      return next;
    });
  }, []);

  const handleApplyGraphics = useCallback(
    (nextGraphics: GraphicsSettings) => {
      setWebglError(null);
      updatePrefs({
        enhancedMap: nextGraphics.enhancedMap,
        quality: nextGraphics.quality,
      });
      setGraphicsDraft({
        enhancedMap: nextGraphics.enhancedMap,
        quality: nextGraphics.quality,
      });
      if (nextGraphics.enhancedMap) {
        setAtmosphere((prev) => ({
          ...prev,
          pathTracingActive: false,
          timeHours: prev.syncBeijingTime ? getCurrentBeijingHours() : prev.timeHours,
        }));
      } else {
        setDesktopAtmoOpen(false);
        setMobileSheet((prev) => (prev === "atmosphere" ? "none" : prev));
        setAtmosphere((prev) => ({ ...prev, pathTracingActive: false, autoPlay: false }));
      }
      setReloadNonce((n) => n + 1);
    },
    [updatePrefs]
  );

  const handleResetDraftGraphics = useCallback(() => {
    setGraphicsDraft(activeGraphics);
  }, [activeGraphics]);

  const handleToggleTouchControls = useCallback(
    (enabled: boolean) => {
      updatePrefs({ showTouchControls: enabled });
    },
    [updatePrefs]
  );

  const handleTogglePins = useCallback(
    (enabled: boolean) => {
      updatePrefs({ showPins: enabled });
    },
    [updatePrefs]
  );

  const handleChangeColorScheme = useCallback(
    (scheme: ColorSchemePref) => {
      setColorScheme(scheme);
      updatePrefs({ colorScheme: scheme });
    },
    [setColorScheme, updatePrefs]
  );

  const triggerFlight = useCallback(
    (cameraPos: [number, number, number], cameraTarget: [number, number, number]) => {
      setCameraFlight({
        id: Date.now() + Math.random(),
        cameraPos,
        cameraTarget,
      });
    },
    []
  );

  const handleSwitchCampus = useCallback((nextCampus: CampusId) => {
    setCampusId(nextCampus);
    setActiveCategory("all");
    setSearchQuery("");
    setSelectedPlaceId(null);
    setActiveTourId(nextCampus === "west" ? "tour-w-overview" : "tour-e-overview");
    setCameraFlight(null);
    setMobileSheet("none");
    setAtmosphere((prev) =>
      prev.pathTracingActive ? { ...prev, pathTracingActive: false } : prev
    );
  }, []);

  const handleSelectPlace = useCallback(
    (placeId: string | null) => {
      setSelectedPlaceId(placeId);
      if (!placeId) {
        setMobileSheet((prev) => (prev === "place" ? "none" : prev));
        return;
      }
      const place = getPlaceById(placeId);
      if (!place) return;
      setActiveTourId(null);
      if (place.campusId !== campusId) {
        setCampusId(place.campusId);
        setAtmosphere((prev) =>
          prev.pathTracingActive ? { ...prev, pathTracingActive: false } : prev
        );
      }
      triggerFlight(place.cameraPos, place.cameraTarget);
      if (isMobileShell) {
        setPlaceSheetSnap("peek");
        setMobileSheet("place");
      }
    },
    [campusId, isMobileShell, triggerFlight]
  );

  const handleSelectTour = useCallback(
    (tour: CameraTourStop) => {
      setActiveTourId(tour.id);
      if (tour.highlightPlaceId) {
        setSelectedPlaceId(tour.highlightPlaceId);
      } else if (isMobileShell) {
        setSelectedPlaceId(null);
      }
      if (isMobileShell && mobileSheet !== "none") {
        setMobileSheet("none");
      }
      triggerFlight(tour.cameraPos, tour.cameraTarget);
    },
    [isMobileShell, mobileSheet, triggerFlight]
  );

  const handleResetView = useCallback(() => {
    setActiveTourId(campusId === "west" ? "tour-w-overview" : "tour-e-overview");
    triggerFlight(campus.defaultCameraPos, campus.defaultCameraTarget);
  }, [campus, campusId, triggerFlight]);

  const handleAtmosphereChange = useCallback((patch: Partial<AtmosphereState>) => {
    setAtmosphere((prev) => ({ ...prev, ...patch }));
  }, []);

  const handleSyncBeijingNow = useCallback(() => {
    setAtmosphere((prev) => ({
      ...prev,
      timeHours: getCurrentBeijingHours(),
      syncBeijingTime: true,
      autoPlay: false,
    }));
  }, []);

  const handleClosePlaceDetail = useCallback(() => {
    setSelectedPlaceId(null);
    setMobileSheet((prev) => (prev === "place" ? "none" : prev));
  }, []);

  const handleWebGLError = useCallback((reason: string) => {
    setWebglError(reason);
    setAtmosphere((prev) => ({ ...prev, pathTracingActive: false }));
  }, []);

  const handleToggleDirectory = () => {
    if (isMobileShell) {
      setMobileSheet((prev) => (prev === "directory" ? "none" : "directory"));
    } else {
      setDirectoryOpen((v) => !v);
    }
  };

  const handleToggleAtmosphere = () => {
    if (isMobileShell) {
      setMobileSheet((prev) => (prev === "atmosphere" ? "none" : "atmosphere"));
    } else {
      setDesktopAtmoOpen((v) => !v);
    }
  };

  const settingsContent = (onClose?: () => void) => (
    <QualitySettingsContent
      campusId={campusId}
      activeGraphics={activeGraphics}
      draftGraphics={graphicsDraft}
      prefs={prefs}
      onChangeDraftGraphics={setGraphicsDraft}
      onResetDraftGraphics={handleResetDraftGraphics}
      onApplyGraphics={handleApplyGraphics}
      onToggleTouchControls={handleToggleTouchControls}
      onTogglePins={handleTogglePins}
      onChangeColorScheme={handleChangeColorScheme}
      onClose={onClose}
    />
  );

  return (
    <main className="map-stage-root">
      {/* 1. Full-bleed 3D Campus Viewport */}
      {prefsReady && !webglError && (
        <CampusScene3D
          campus={campus}
          places={allCampusPlaces}
          graphics={activeGraphics}
          reloadNonce={reloadNonce}
          selectedPlaceId={selectedPlaceId}
          showPins={prefs.showPins}
          isCompactViewport={isMobileShell}
          atmosphere={atmosphere}
          compassDialRef={compassDialRef}
          virtualInputRef={virtualInputRef}
          alignNorthRef={alignNorthRef}
          exportPhotoRef={exportPhotoRef}
          cameraFlightRequest={cameraFlight}
          onSelectPlace={handleSelectPlace}
          onAtmosphereChange={handleAtmosphereChange}
          onPathTracerStatusChange={setPathTracerStatus}
          onLoadedChange={setIsSceneLoaded}
          onWebGLError={handleWebGLError}
        />
      )}

      {/* WebGL Graceful Error Fallback */}
      {webglError && (
        <div className="webgl-error-stage">
          <div className="webgl-error-card">
            <IllustratedMessage size="M">
              <AlertTriangle />
              <Heading>无法初始化三维渲染视口</Heading>
              <Content>{webglError}</Content>
            </IllustratedMessage>
            <div className="webgl-error-actions">
              <Button
                variant="accent"
                onPress={() => {
                  setWebglError(null);
                  setReloadNonce((n) => n + 1);
                }}
              >
                重新加载地图
              </Button>
              <Button
                variant="secondary"
                fillStyle="outline"
                onPress={handleToggleDirectory}
              >
                浏览校园建筑文字与实拍档案
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Top Floating HUD Row (Left Brand/Pages Corner | Center Campus Switcher | Right Toolbar) */}
      <div className="hud-top-bar">
        <div className="hud-top-left">
          <TopCornerBrandMenu
            compact={isMobileShell}
            onOpenHelp={() => setHelpOpen(true)}
          />
        </div>

        <div className="hud-top-center">
          <CampusSwitcher
            campusId={campusId}
            compact={isMobileShell}
            onChange={handleSwitchCampus}
          />
        </div>

        <div className="hud-top-right">
          {!isMobileShell ? (
            <div className="hud-island hud-toolbar-island" role="toolbar" aria-label="三维地图工具栏">
              <TooltipTrigger>
                <ToggleButton
                  size="S"
                  isQuiet
                  isEmphasized
                  isSelected={directoryOpen}
                  onChange={setDirectoryOpen}
                  aria-label="点位搜索与目录"
                >
                  <Search />
                </ToggleButton>
                <Tooltip>点位目录与搜索 ({allCampusPlaces.length})</Tooltip>
              </TooltipTrigger>

              <TooltipTrigger>
                <ToggleButton
                  size="S"
                  isQuiet
                  isEmphasized
                  isSelected={prefs.showPins}
                  onChange={handleTogglePins}
                  aria-label={prefs.showPins ? "隐藏建筑标签" : "显示建筑标签"}
                >
                  {prefs.showPins ? <PinOn /> : <PinOff />}
                </ToggleButton>
                <Tooltip>{prefs.showPins ? "隐藏 3D 建筑标签" : "显示 3D 建筑标签"}</Tooltip>
              </TooltipTrigger>

              <TooltipTrigger>
                <ToggleButton
                  size="S"
                  isQuiet
                  isEmphasized
                  isSelected={prefs.showTouchControls}
                  onChange={handleToggleTouchControls}
                  aria-label="开关虚拟摇杆与上下移动按键"
                >
                  <TouchOneFingerSwipeLeftRight />
                </ToggleButton>
                <Tooltip>
                  {prefs.showTouchControls ? "关闭虚拟摇杆与升降键" : "开启虚拟摇杆与升降键"}
                </Tooltip>
              </TooltipTrigger>

              {prefs.enhancedMap && (
                <TooltipTrigger>
                  <ToggleButton
                    size="S"
                    isQuiet
                    isEmphasized
                    isSelected={desktopAtmoOpen || atmosphere.pathTracingActive}
                    onChange={setDesktopAtmoOpen}
                    aria-label="调节时间、天气与真光追"
                  >
                    <Lighten />
                  </ToggleButton>
                  <Tooltip>
                    天光天气与光追 ({formatCompactHour(atmosphere.timeHours)})
                  </Tooltip>
                </TooltipTrigger>
              )}

              <span className="hud-settings-btn-wrap">
                <DialogTrigger
                  isOpen={desktopSettingsOpen}
                  onOpenChange={setDesktopSettingsOpen}
                >
                  <TooltipTrigger>
                    <ActionButton
                      size="S"
                      isQuiet
                      aria-label={
                        hasPendingGraphicsChanges
                          ? "画质与操控设置（有未应用的画质修改）"
                          : "画质与操控设置"
                      }
                    >
                      <Settings />
                    </ActionButton>
                    <Tooltip>
                      {hasPendingGraphicsChanges
                        ? "画质设置存在未应用修改，点击查看或应用"
                        : "画质、增强版地图与操控设置"}
                    </Tooltip>
                  </TooltipTrigger>
                  <Popover
                    placement="bottom end"
                    hideArrow
                    padding="none"
                    UNSAFE_className="s2-settings-popover"
                  >
                    {settingsContent(() => setDesktopSettingsOpen(false))}
                  </Popover>
                </DialogTrigger>
                {hasPendingGraphicsChanges && (
                  <span className="hud-settings-dirty-dot" aria-hidden="true" />
                )}
              </span>

              <TooltipTrigger>
                <ActionButton
                  size="S"
                  isQuiet
                  onPress={handleResetView}
                  aria-label="复位鸟瞰视角"
                >
                  <Refresh />
                </ActionButton>
                <Tooltip>复位鸟瞰视角</Tooltip>
              </TooltipTrigger>
            </div>
          ) : (
            <div className="hud-island hud-toolbar-island">
              <span className="hud-settings-btn-wrap">
                <ActionButton
                  size="S"
                  isQuiet
                  onPress={() =>
                    setMobileSheet((prev) => (prev === "settings" ? "none" : "settings"))
                  }
                  aria-label={
                    hasPendingGraphicsChanges
                      ? "打开画质与操控设置（有未应用的画质修改）"
                      : "打开画质与操控设置"
                  }
                >
                  <Settings />
                </ActionButton>
                {hasPendingGraphicsChanges && (
                  <span className="hud-settings-dirty-dot" aria-hidden="true" />
                )}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 3. Right Floating Utility Stack: Live 3D Compass (+ Mobile Quick Action Rail) */}
      <div
        className={`hud-right-stack${
          !isMobileShell && selectedPlace ? " hud-right-stack-shifted" : ""
        }`}
      >
        <button
          type="button"
          className="hud-compass-btn"
          onClick={() => alignNorthRef.current?.()}
          title="实时方向指北针（红针指北，点击回正上北下南）"
          aria-label="方向指北针：点击回正北向"
        >
          <div ref={compassDialRef} className="hud-compass-dial">
            <span className="hud-compass-n">北</span>
            <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
              <circle
                cx="16"
                cy="16"
                r="13"
                fill="none"
                stroke="currentColor"
                strokeOpacity="0.16"
                strokeWidth="1.2"
              />
              <polygon points="16,5 13.2,16 16,14.5 18.8,16" fill="#d7373f" />
              <polygon points="16,27 13.2,16 16,17.5 18.8,16" fill="currentColor" fillOpacity="0.38" />
              <circle cx="16" cy="16" r="1.8" fill="currentColor" />
            </svg>
          </div>
        </button>

        {isMobileShell && (
          <div className="hud-island hud-mobile-rail" aria-label="快捷工具">
            <ToggleButton
              size="S"
              isQuiet
              isEmphasized
              isSelected={mobileSheet === "directory"}
              onChange={() => handleToggleDirectory()}
              aria-label="点位目录"
            >
              <Search />
            </ToggleButton>

            <ToggleButton
              size="S"
              isQuiet
              isEmphasized
              isSelected={prefs.showPins}
              onChange={handleTogglePins}
              aria-label="建筑标签开关"
            >
              {prefs.showPins ? <PinOn /> : <PinOff />}
            </ToggleButton>

            <ToggleButton
              size="S"
              isQuiet
              isEmphasized
              isSelected={prefs.showTouchControls}
              onChange={handleToggleTouchControls}
              aria-label="虚拟按键开关"
            >
              <TouchOneFingerSwipeLeftRight />
            </ToggleButton>

            {prefs.enhancedMap && (
              <ToggleButton
                size="S"
                isQuiet
                isEmphasized
                isSelected={mobileSheet === "atmosphere" || atmosphere.pathTracingActive}
                onChange={() => handleToggleAtmosphere()}
                aria-label="时间天气与光追"
              >
                <Lighten />
              </ToggleButton>
            )}

            <ActionButton
              size="S"
              isQuiet
              onPress={handleResetView}
              aria-label="复位视角"
            >
              <Refresh />
            </ActionButton>
          </div>
        )}
      </div>

      {/* 4. Desktop Enhanced-Mode Floating Atmosphere Panel (only when Enhanced Map is ON & toggled) */}
      {!isMobileShell && prefs.enhancedMap && desktopAtmoOpen && isSceneLoaded && (
        <div
          className={`hud-atmo-float${selectedPlace ? " hud-atmo-float-shifted" : ""}`}
        >
          <LazyAtmosphereDock
            state={atmosphere}
            pathTracerStatus={pathTracerStatus}
            onChange={handleAtmosphereChange}
            onSyncBeijingNow={handleSyncBeijingNow}
            onExportPhoto={() => exportPhotoRef.current?.()}
            onClose={() => setDesktopAtmoOpen(false)}
          />
        </div>
      )}

      {/* 5. Desktop Left Collapsible Directory Drawer */}
      {!isMobileShell && directoryOpen && (
        <DirectoryPanel
          campus={campus}
          allPlacesCount={allCampusPlaces.length}
          places={filteredPlaces}
          searchQuery={searchQuery}
          activeCategory={activeCategory}
          selectedPlaceId={selectedPlaceId}
          onSearchChange={setSearchQuery}
          onCategoryChange={setActiveCategory}
          onSelectPlace={(pid) => handleSelectPlace(pid)}
          onClose={() => setDirectoryOpen(false)}
        />
      )}

      {/* 6. Desktop Right Place Detail Drawer */}
      {!isMobileShell && selectedPlace && (
        <PlaceDetailDrawer
          place={selectedPlace}
          isMobileShell={false}
          onClose={handleClosePlaceDetail}
          onFocus3D={(p) => triggerFlight(p.cameraPos, p.cameraTarget)}
        />
      )}

      {/* 7. Bottom Camera Tour Presets (hide when a full mobile sheet is open) */}
      {(!isMobileShell || mobileSheet === "none") && (
        <CameraTourBar
          tours={campusTours}
          activeTourId={activeTourId}
          onSelectTour={handleSelectTour}
          elevatedForVpad={isMobileShell && prefs.showTouchControls}
        />
      )}

      {/* 8. Optional Virtual Joystick & Altitude Controls (Desktop + Mobile both supported) */}
      {prefs.showTouchControls && (!isMobileShell || mobileSheet === "none") && (
        <TouchFlightControls inputRef={virtualInputRef} />
      )}

      {/* 9. Subtle Desktop Keyboard Hint (only when virtual controls are off and not dismissed) */}
      {!isMobileShell && !prefs.showTouchControls && !hintDismissed && !directoryOpen && (
        <button
          type="button"
          className="hud-kbd-hint"
          onClick={() => setHintDismissed(true)}
          title="点击隐藏操作提示"
        >
          WASD 移动 · Space/Shift 升降 · 拖拽平移 · 右键旋转
        </button>
      )}

      {/* 10. Mobile Mutually Exclusive Bottom Sheets */}
      {isMobileShell && (
        <>
          <MobileBottomSheet
            open={mobileSheet === "directory"}
            onClose={() => setMobileSheet("none")}
            ariaLabel="校园建筑与景观目录"
            modalBackdrop
          >
            <DirectoryPanel
              campus={campus}
              allPlacesCount={allCampusPlaces.length}
              places={filteredPlaces}
              searchQuery={searchQuery}
              activeCategory={activeCategory}
              selectedPlaceId={selectedPlaceId}
              onSearchChange={setSearchQuery}
              onCategoryChange={setActiveCategory}
              onSelectPlace={(pid) => handleSelectPlace(pid)}
              onClose={() => setMobileSheet("none")}
              embedded
            />
          </MobileBottomSheet>

          {mobileSheet === "place" && selectedPlace && (
            <PlaceDetailDrawer
              place={selectedPlace}
              isMobileShell
              mobileSnap={placeSheetSnap}
              onMobileSnapChange={setPlaceSheetSnap}
              onClose={handleClosePlaceDetail}
              onFocus3D={(p) => triggerFlight(p.cameraPos, p.cameraTarget)}
            />
          )}

          <MobileBottomSheet
            open={mobileSheet === "settings"}
            onClose={() => setMobileSheet("none")}
            ariaLabel="画质与操控设置"
            modalBackdrop
          >
            {settingsContent(() => setMobileSheet("none"))}
          </MobileBottomSheet>

          {prefs.enhancedMap && (
            <MobileBottomSheet
              open={mobileSheet === "atmosphere"}
              onClose={() => setMobileSheet("none")}
              ariaLabel="时间、天气与光追控制台"
              modalBackdrop={false}
            >
              <LazyAtmosphereDock
                state={atmosphere}
                pathTracerStatus={pathTracerStatus}
                onChange={handleAtmosphereChange}
                onSyncBeijingNow={handleSyncBeijingNow}
                onExportPhoto={() => exportPhotoRef.current?.()}
                onClose={() => setMobileSheet("none")}
              />
            </MobileBottomSheet>
          )}
        </>
      )}

      {/* 11. Keyboard & Touch Controls Help Dialog */}
      <HelpDialog open={helpOpen} onClose={() => setHelpOpen(false)} />
    </main>
  );
}
