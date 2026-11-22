import { CAMPUSES } from "@/data/campuses";
import {
  CampusId,
  ColorSchemePref,
  GraphicsSettings,
  MapUserPrefs,
  QualityTier,
} from "@/data/types";

export const PREFS_STORAGE_KEY = "ibb-school-map:prefs:v1";

export const QUALITY_TIERS: {
  id: QualityTier;
  label: string;
  shortLabel: string;
  classicDesc: string;
  enhancedDesc: string;
}[] = [
  {
    id: "low",
    label: "低",
    shortLabel: "低",
    classicDesc: "1x 分辨率 · 关闭阴影与反射 · 零外部纹理与后处理，最省电",
    enhancedDesc: "仅加载基础漫反射与树叶透贴 · 关闭法线/ORM 与后处理管线",
  },
  {
    id: "medium",
    label: "中",
    shortLabel: "中",
    classicDesc: "最高 1.5x 分辨率 · 1024 阴影 · 抗锯齿与轻环境反射 · 零外部纹理",
    enhancedDesc: "加载漫反射与法线贴图 · 2048 阴影 · 跳过 ORM 与后处理 AO",
  },
  {
    id: "high",
    label: "高",
    shortLabel: "高",
    classicDesc: "最高 2x 高清渲染 · 2048 柔影 · 8x 各向异性过滤 · 零外部纹理",
    enhancedDesc: "全量 PBR（漫反射/法线/ORM）· 动态加载 N8AO + SSGI + ACES Filmic + 4x MSAA",
  },
  {
    id: "ultra",
    label: "极致",
    shortLabel: "极致",
    classicDesc: "超采样高清渲染 · 4096 级全域阴影 · 满格各向异性 · 全设备解禁",
    enhancedDesc: "全量 PBR · 4096 阴影 · 超采样 · N8AO Ultra + 全量 SSGI + CAS 锐化 + 全规格光追",
  },
];

const VALID_QUALITIES = new Set<QualityTier>(["low", "medium", "high", "ultra"]);
const VALID_SCHEMES = new Set<ColorSchemePref>(["light", "dark", "system"]);

/**
 * Only used for first-time initial default quality when localStorage has no saved prefs.
 * Never caps or restricts any quality level (including Ultra) on any device!
 */
export function getRecommendedInitialQuality(): QualityTier {
  if (typeof window === "undefined") return "high";
  const isCoarseOrNarrow =
    window.matchMedia("(max-width: 860px), (pointer: coarse)").matches;
  return isCoarseOrNarrow ? "medium" : "high";
}

export function getDefaultUserPrefs(): MapUserPrefs {
  return {
    version: 1,
    enhancedMap: false,
    quality: getRecommendedInitialQuality(),
    showTouchControls: false,
    showPins: true,
    colorScheme: "light",
  };
}

export function loadUserPrefs(): MapUserPrefs {
  const fallback = getDefaultUserPrefs();
  if (typeof window === "undefined") return fallback;

  try {
    const raw = window.localStorage.getItem(PREFS_STORAGE_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw) as Partial<MapUserPrefs> | null;
    if (!parsed || typeof parsed !== "object") return fallback;

    const quality =
      parsed.quality && VALID_QUALITIES.has(parsed.quality)
        ? parsed.quality
        : fallback.quality;
    const colorScheme =
      parsed.colorScheme && VALID_SCHEMES.has(parsed.colorScheme)
        ? parsed.colorScheme
        : fallback.colorScheme;

    return {
      version: 1,
      enhancedMap: Boolean(parsed.enhancedMap),
      quality,
      showTouchControls: Boolean(parsed.showTouchControls),
      showPins: typeof parsed.showPins === "boolean" ? parsed.showPins : true,
      colorScheme,
    };
  } catch {
    return fallback;
  }
}

export function saveUserPrefs(prefs: MapUserPrefs): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(PREFS_STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Ignore storage quota or private browsing errors
  }
}

export function graphicsSettingsEqual(a: GraphicsSettings, b: GraphicsSettings): boolean {
  return a.enhancedMap === b.enhancedMap && a.quality === b.quality;
}

export interface ResourceEstimate {
  totalMB: number;
  modelMB: number;
  texturesMB: number;
  pipelineNote: string;
  loadedModules: string[];
}

export function estimateResourceFootprint(
  campusId: CampusId,
  settings: GraphicsSettings
): ResourceEstimate {
  const campus = CAMPUSES[campusId];

  if (!settings.enhancedMap) {
    const noteMap: Record<QualityTier, string> = {
      low: "仅经典模型 · 零外部贴图 · 关闭阴影",
      medium: "仅经典模型 · 零外部贴图 · 1024 阴影",
      high: "仅经典模型 · 零外部贴图 · 2048 柔影",
      ultra: "仅经典模型 · 零外部贴图 · 4096 阴影 + 超采样",
    };
    return {
      totalMB: campus.classicModelMB,
      modelMB: campus.classicModelMB,
      texturesMB: 0,
      pipelineNote: noteMap[settings.quality],
      loadedModules: ["经典 3D 模型（内嵌图集）", "轻量原生 WebGL 渲染器"],
    };
  }

  const texByTier: Record<QualityTier, number> = {
    low: 2.8,
    medium: 7.2,
    high: 8.5,
    ultra: 8.5,
  };
  const texturesMB = texByTier[settings.quality];
  const totalMB = Number((campus.enhancedModelMB + texturesMB).toFixed(1));

  const pipelineByTier: Record<QualityTier, string> = {
    low: "增强模型 + 漫反射/树叶贴图 · 零法线/ORM/后处理",
    medium: "增强模型 + 漫反射与法线贴图 · 2048 阴影 · 无后处理 AO",
    high: "增强模型 + 全量 PBR + 动态加载 N8AO / SSGI / ACES / 4x MSAA",
    ultra: "增强模型 + 全量 PBR + 4096 阴影 + Ultra N8AO + 全量 SSGI + CAS",
  };

  const modulesByTier: Record<QualityTier, string[]> = {
    low: ["增强 3D 模型", "基础漫反射 & 树叶透贴", "24h 天光与天气系统"],
    medium: ["增强 3D 模型", "漫反射 + 法线贴图 + 室内视差", "24h 天光与天气系统"],
    high: ["增强 3D 模型", "全量 PBR (Albedo/Normal/ORM)", "24h 天光天气 + N8AO & SSGI 后处理"],
    ultra: [
      "增强 3D 模型",
      "全量 PBR + 满格各向异性",
      "4096 阴影 + Ultra N8AO + SSGI + CAS",
      "按需懒加载 GPU 真光追（点击时加载）",
    ],
  };

  return {
    totalMB,
    modelMB: campus.enhancedModelMB,
    texturesMB,
    pipelineNote: pipelineByTier[settings.quality],
    loadedModules: modulesByTier[settings.quality],
  };
}
