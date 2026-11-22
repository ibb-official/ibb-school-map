"use client";

import type React from "react";
import { useEffect, useRef, useState } from "react";
import { Badge } from "@react-spectrum/s2/Badge";
import { ProgressBar } from "@react-spectrum/s2/ProgressBar";
import { CATEGORY_COLORS } from "@/data/places";
import {
  AtmosphereState,
  CameraSnapshot,
  CampusMeta,
  CampusPlace,
  FlightInputVector,
  GraphicsSettings,
} from "@/data/types";
import type { CampusSceneEngineHandle } from "@/scene/engineTypes";
import type { PathTracerStatus } from "@/scene/pathTracerController";
import { QUALITY_TIERS } from "@/scene/prefs";

interface CampusScene3DProps {
  campus: CampusMeta;
  places: CampusPlace[];
  graphics: GraphicsSettings;
  reloadNonce: number;
  selectedPlaceId: string | null;
  showPins: boolean;
  isCompactViewport: boolean;
  atmosphere: AtmosphereState;
  compassDialRef: React.RefObject<HTMLDivElement | null>;
  virtualInputRef: React.MutableRefObject<FlightInputVector>;
  alignNorthRef: React.MutableRefObject<(() => void) | null>;
  exportPhotoRef: React.MutableRefObject<(() => void) | null>;
  cameraFlightRequest: {
    id: number;
    cameraPos: [number, number, number];
    cameraTarget: [number, number, number];
  } | null;
  onSelectPlace: (placeId: string | null) => void;
  onAtmosphereChange: (patch: Partial<AtmosphereState>) => void;
  onPathTracerStatusChange: (status: PathTracerStatus) => void;
  onLoadedChange: (loaded: boolean) => void;
  onWebGLError: (message: string) => void;
}

export function CampusScene3D({
  campus,
  places,
  graphics,
  reloadNonce,
  selectedPlaceId,
  showPins,
  isCompactViewport,
  atmosphere,
  compassDialRef,
  virtualInputRef,
  alignNorthRef,
  exportPhotoRef,
  cameraFlightRequest,
  onSelectPlace,
  onAtmosphereChange,
  onPathTracerStatusChange,
  onLoadedChange,
  onWebGLError,
}: CampusScene3DProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const pinElsRef = useRef<Map<string, HTMLButtonElement>>(new Map());
  const engineRef = useRef<CampusSceneEngineHandle | null>(null);
  const lastCampusIdRef = useRef<string>(campus.id);
  const preservedSnapshotRef = useRef<CameraSnapshot | null>(null);

  const [loadProgress, setLoadProgress] = useState<number>(0);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);

  // Latest callbacks & state refs for imperative engine bridge
  const onSelectRef = useRef(onSelectPlace);
  onSelectRef.current = onSelectPlace;

  const onAtmoRef = useRef(onAtmosphereChange);
  onAtmoRef.current = onAtmosphereChange;

  const onPtStatusRef = useRef(onPathTracerStatusChange);
  onPtStatusRef.current = onPathTracerStatusChange;

  const onLoadedRef = useRef(onLoadedChange);
  onLoadedRef.current = onLoadedChange;

  const onErrorRef = useRef(onWebGLError);
  onErrorRef.current = onWebGLError;

  const placesRef = useRef(places);
  placesRef.current = places;

  const selectedRef = useRef(selectedPlaceId);
  selectedRef.current = selectedPlaceId;

  const showPinsRef = useRef(showPins);
  showPinsRef.current = showPins;

  const compactRef = useRef(isCompactViewport);
  compactRef.current = isCompactViewport;

  const atmosphereRef = useRef(atmosphere);
  atmosphereRef.current = atmosphere;

  // Mount & strictly code-split either Classic Engine or Enhanced Engine
  useEffect(() => {
    const container = hostRef.current;
    if (!container) return;

    let cancelled = false;
    setIsLoaded(false);
    setLoadProgress(5);
    onLoadedRef.current(false);

    // Keep camera position when reloading graphics settings on the SAME campus; reset when switching campus
    const snapshot =
      lastCampusIdRef.current === campus.id ? preservedSnapshotRef.current : null;
    lastCampusIdRef.current = campus.id;
    preservedSnapshotRef.current = null;

    const mountEngine = async () => {
      const commonOptions = {
        container,
        campus,
        places: placesRef.current,
        quality: graphics.quality,
        initialSelectedPlaceId: selectedRef.current,
        initialShowPins: showPinsRef.current,
        initialCompactViewport: compactRef.current,
        initialSnapshot: snapshot,
        initialAtmosphere: atmosphereRef.current,
        pinElsRef,
        compassDialRef,
        virtualInputRef,
        onProgress: (p: number) => {
          if (!cancelled) setLoadProgress(p);
        },
        onLoaded: (loaded: boolean) => {
          if (!cancelled) {
            setIsLoaded(loaded);
            onLoadedRef.current(loaded);
          }
        },
        onSelectPlace: (pid: string | null) => {
          if (!cancelled) onSelectRef.current(pid);
        },
        onWebGLError: (msg: string) => {
          if (!cancelled) onErrorRef.current(msg);
        },
        onAtmosphereChange: (patch: Partial<AtmosphereState>) => {
          if (!cancelled) onAtmoRef.current(patch);
        },
        onPathTracerStatusChange: (status: PathTracerStatus) => {
          if (!cancelled) onPtStatusRef.current(status);
        },
      };

      let handle: CampusSceneEngineHandle | null = null;
      if (graphics.enhancedMap) {
        const mod = await import("@/scene/enhancedEngine");
        if (cancelled) return;
        handle = await mod.mountEnhancedEngine(commonOptions);
      } else {
        const mod = await import("@/scene/classicEngine");
        if (cancelled) return;
        handle = mod.mountClassicEngine(commonOptions);
      }

      if (cancelled) {
        handle?.dispose();
        return;
      }

      engineRef.current = handle;
      alignNorthRef.current = handle ? () => handle.alignNorth() : null;
      exportPhotoRef.current =
        handle && handle.exportPhoto ? () => handle.exportPhoto?.() : null;
    };

    void mountEngine();

    return () => {
      cancelled = true;
      if (engineRef.current) {
        // Save camera snapshot before tearing down so quality/mode reload keeps current view
        preservedSnapshotRef.current = engineRef.current.getCameraSnapshot();
        engineRef.current.dispose();
        engineRef.current = null;
      }
      alignNorthRef.current = null;
      exportPhotoRef.current = null;
    };
  }, [
    campus,
    graphics.enhancedMap,
    graphics.quality,
    reloadNonce,
    compassDialRef,
    virtualInputRef,
    alignNorthRef,
    exportPhotoRef,
  ]);

  useEffect(() => {
    engineRef.current?.setSelectedPlaceId(selectedPlaceId);
  }, [selectedPlaceId]);

  useEffect(() => {
    engineRef.current?.setShowPins(showPins);
  }, [showPins]);

  useEffect(() => {
    engineRef.current?.setIsCompactViewport(isCompactViewport);
  }, [isCompactViewport]);

  useEffect(() => {
    if (graphics.enhancedMap) {
      engineRef.current?.setAtmosphere?.(atmosphere);
    }
  }, [graphics.enhancedMap, atmosphere]);

  useEffect(() => {
    if (!cameraFlightRequest) return;
    engineRef.current?.flyTo(
      cameraFlightRequest.cameraPos,
      cameraFlightRequest.cameraTarget
    );
  }, [cameraFlightRequest]);

  const qualityLabel =
    QUALITY_TIERS.find((t) => t.id === graphics.quality)?.label ?? graphics.quality;

  return (
    <>
      <div
        ref={hostRef}
        className="scene-canvas-host"
        aria-label={`${campus.name} 三维交互画布`}
      />

      {showPins && isLoaded && !(graphics.enhancedMap && atmosphere.pathTracingActive) && (
        <div className="pins-overlay-layer" aria-label="三维空间点位标签层">
          {places.map((place) => {
            const selected = place.id === selectedPlaceId;
            return (
              <button
                key={place.id}
                ref={(el) => {
                  if (el) pinElsRef.current.set(place.id, el);
                  else pinElsRef.current.delete(place.id);
                }}
                type="button"
                className={`pin-3d-btn${selected ? " pin-3d-btn-selected" : ""}`}
                onClick={() => onSelectPlace(place.id)}
                title={place.name}
              >
                <span
                  className="pin-dot"
                  style={{ backgroundColor: CATEGORY_COLORS[place.category] }}
                />
                <span>{place.shortName}</span>
              </button>
            );
          })}
        </div>
      )}

      {!isLoaded && (
        <div className="scene-loading-card" role="status" aria-live="polite">
          <div className="scene-loading-header">
            <span className="scene-loading-title">正在加载 {campus.shortName}</span>
            <Badge
              variant={graphics.enhancedMap ? "accent" : "neutral"}
              fillStyle="subtle"
              size="S"
            >
              {graphics.enhancedMap ? "增强版" : "普通版"} · {qualityLabel}画质
            </Badge>
          </div>
          <ProgressBar
            size="M"
            label={
              graphics.enhancedMap
                ? "按当前画质按需加载模型与 PBR 资源..."
                : "加载经典轻量 3D 模型（零外部纹理）..."
            }
            value={loadProgress}
          />
        </div>
      )}
    </>
  );
}
