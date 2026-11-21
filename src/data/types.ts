export type CampusId = "west" | "east";

export type QualityTier = "low" | "medium" | "high" | "ultra";

export type ColorSchemePref = "light" | "dark" | "system";

export type WeatherMode = "clear" | "cloudy" | "rainy" | "misty" | "snowy";

export type LightingPreset = "morning" | "noon" | "sunset";

export interface GraphicsSettings {
  /** false = 经典普通地图（默认，零外部纹理/后处理）; true = 增强版地图（PBR + 天光天气 + 光追） */
  enhancedMap: boolean;
  /** 四档画质：全设备均开放最高极致画质，决定实际加载的资源与管线 */
  quality: QualityTier;
}

export interface MapUserPrefs extends GraphicsSettings {
  version: 1;
  /** 虚拟摇杆 + 上下移动键（桌面端与移动端均可开启） */
  showTouchControls: boolean;
  /** 是否显示 3D 悬浮点位标签 */
  showPins: boolean;
  /** Spectrum 外观主题 */
  colorScheme: ColorSchemePref;
}

export interface AtmosphereState {
  /** Continuous Beijing local time in hours [0, 24) */
  timeHours: number;
  /** Whether time automatically tracks live Beijing wall-clock time */
  syncBeijingTime: boolean;
  /** Whether time-lapse playback is active */
  autoPlay: boolean;
  weather: WeatherMode;
  /** True GPU Monte Carlo path-tracing photo mode (Enhanced mode only) */
  pathTracingActive: boolean;
}

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
  /** Exact object node name inside public/models/<campus>-campus*.glb */
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
  /** Quantized classic map GLB (zero external texture dependencies) */
  classicModelUrl: string;
  classicModelMB: number;
  /** Quantized enhanced ArchViz GLB (paired with on-demand PBR textures) */
  enhancedModelUrl: string;
  enhancedModelMB: number;
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

export interface CameraSnapshot {
  position: [number, number, number];
  target: [number, number, number];
}

export interface FlightInputVector {
  /** Left (-1) to Right (+1) strafe */
  moveX: number;
  /** Backward (-1) to Forward (+1) horizontal movement */
  moveZ: number;
  /** Down (-1) to Up (+1) vertical altitude movement */
  moveY: number;
}
