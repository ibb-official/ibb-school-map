export interface DeviceProfile {
  isCoarsePointer: boolean;
  isNarrowViewport: boolean;
  isMobileTier: boolean;
  isLowEndDevice: boolean;
  recommendedDprCap: number;
  maxShadowMapSize: number;
  maxAnisotropyCap: number;
}

/**
 * Shared responsive breakpoint matching both phone/tablet portrait (<= 860px)
 * and phone landscape (height <= 500px with coarse touch pointer).
 */
export const MOBILE_SHELL_MEDIA_QUERY =
  "(max-width: 860px), (max-height: 500px) and (pointer: coarse)";

const DESKTOP_DEFAULT_PROFILE: DeviceProfile = {
  isCoarsePointer: false,
  isNarrowViewport: false,
  isMobileTier: false,
  isLowEndDevice: false,
  recommendedDprCap: 2,
  maxShadowMapSize: 4096,
  maxAnisotropyCap: 16,
};

/**
 * Synchronously probes viewport, pointer capability, and hardware hints on the client
 * BEFORE WebGLRenderer / EffectComposer / shadows are constructed, eliminating the
 * initial frame race condition where mobile devices previously booted into heavy desktop tiers.
 */
export function detectDeviceProfile(): DeviceProfile {
  if (typeof window === "undefined") {
    return DESKTOP_DEFAULT_PROFILE;
  }

  const isCoarsePointer =
    window.matchMedia("(pointer: coarse)").matches ||
    (typeof navigator !== "undefined" && navigator.maxTouchPoints > 0 && window.innerWidth <= 1024);

  const isNarrowViewport = window.matchMedia(MOBILE_SHELL_MEDIA_QUERY).matches;
  const isMobileTier = isCoarsePointer || isNarrowViewport;

  const nav = typeof navigator !== "undefined" ? (navigator as Navigator & { deviceMemory?: number }) : undefined;
  const cores = nav?.hardwareConcurrency ?? 8;
  const memoryGb = nav?.deviceMemory ?? 8;
  const isLowEndDevice = isMobileTier && (cores <= 4 || memoryGb <= 4);

  if (!isMobileTier) {
    return DESKTOP_DEFAULT_PROFILE;
  }

  return {
    isCoarsePointer,
    isNarrowViewport,
    isMobileTier: true,
    isLowEndDevice,
    recommendedDprCap: isLowEndDevice ? 1.25 : 1.5,
    maxShadowMapSize: 2048,
    maxAnisotropyCap: 4,
  };
}
