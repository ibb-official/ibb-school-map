import type React from "react";
import {
  AtmosphereState,
  CameraSnapshot,
  CampusMeta,
  CampusPlace,
  FlightInputVector,
  QualityTier,
} from "@/data/types";
import type { PathTracerStatus } from "./pathTracerController";

export interface EngineMountOptions {
  container: HTMLDivElement;
  campus: CampusMeta;
  places: CampusPlace[];
  quality: QualityTier;
  initialSelectedPlaceId: string | null;
  initialShowPins: boolean;
  initialCompactViewport: boolean;
  initialSnapshot?: CameraSnapshot | null;
  initialAtmosphere?: AtmosphereState;
  pinElsRef: React.MutableRefObject<Map<string, HTMLButtonElement>>;
  compassDialRef: React.RefObject<HTMLDivElement | null>;
  virtualInputRef: React.MutableRefObject<FlightInputVector>;
  onProgress: (percent: number) => void;
  onLoaded: (loaded: boolean) => void;
  onSelectPlace: (placeId: string | null) => void;
  onWebGLError: (reason: string) => void;
  onAtmosphereChange?: (patch: Partial<AtmosphereState>) => void;
  onPathTracerStatusChange?: (status: PathTracerStatus) => void;
}

export interface CampusSceneEngineHandle {
  flyTo: (pos: [number, number, number], target: [number, number, number]) => void;
  alignNorth: () => void;
  getCameraSnapshot: () => CameraSnapshot;
  setSelectedPlaceId: (id: string | null) => void;
  setShowPins: (show: boolean) => void;
  setIsCompactViewport: (compact: boolean) => void;
  setAtmosphere?: (atmo: AtmosphereState) => void;
  exportPhoto?: () => void;
  dispose: () => void;
}
