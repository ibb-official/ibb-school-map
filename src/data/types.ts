export type CampusId = "west" | "east";

export type ViewMode = "3d" | "2d" | "overview";

export type LightingPreset = "morning" | "noon" | "sunset";

export type PlaceCategory =
  | "gate"
  | "academic"
  | "sports"
  | "heritage"
  | "corridor";

export interface PhotoReference {
  src: string;
  caption: string;
  year: string;
  sourceLabel: string;
}

export interface CampusPlace {
  id: string;
  campusId: CampusId;
  /** Exact object node name inside public/models/<campus>-campus.glb */
  meshNodeName: string;
  code: string;
  name: string;
  shortName: string;
  category: PlaceCategory;
  storiesLabel: string;
  heightMeters: number;
  /** Pin anchor position in glTF Y-up coordinates [x=E, y=Up, z=-N] */
  position: [number, number, number];
  /** Metric ENU coordinates relative to campus origin [East, North] */
  enu: [number, number];
  /** Fly-to camera position in glTF coordinates */
  cameraPos: [number, number, number];
  /** Fly-to look-at target in glTF coordinates */
  cameraTarget: [number, number, number];
  summary: string;
  architecturalFeatures: string[];
  historicalNote?: string;
  photoRefs: PhotoReference[];
}

export interface CampusMeta {
  id: CampusId;
  name: string;
  shortName: string;
  roleLabel: string;
  address: string;
  district: string;
  modelUrl: string;
  approxAreaSqm: string;
  defaultCameraPos: [number, number, number];
  defaultCameraTarget: [number, number, number];
  panBounds: {
    minX: number;
    maxX: number;
    minZ: number;
    maxZ: number;
  };
  nearestTransit: string[];
  surroundingStreets: string[];
  summary: string;
}

export interface CameraTourStop {
  id: string;
  campusId: CampusId;
  title: string;
  subtitle: string;
  lightingSuggestion?: LightingPreset;
  cameraPos: [number, number, number];
  cameraTarget: [number, number, number];
  highlightPlaceId?: string;
}

export interface DataSourceEntry {
  id: string;
  category: string;
  name: string;
  coverage: string;
  licenseOrNote: string;
  url?: string;
}
