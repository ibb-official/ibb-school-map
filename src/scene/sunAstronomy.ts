import * as THREE from "three";
import { LightingPreset, WeatherMode } from "@/data/types";

/** Beijing No. 166 Middle School (Dongcheng District) geographic coordinates */
const BEIJING_LAT_DEG = 39.92;
const BEIJING_LON_DEG = 116.41;

export interface SolarAtmosphereSample {
  /** Sun unit direction vector in campus glTF coordinates (+X East, +Y Up, -Z North) */
  sunDir: THREE.Vector3;
  /** Active key light direction (sun during day, moon at night) */
  keyLightDir: THREE.Vector3;
  /** Solar elevation angle in degrees (-90 .. +90) */
  sunElevationDeg: number;
  /** Solar azimuth angle in degrees clockwise from North (0=N, 90=E, 180=S, 270=W) */
  sunAzimuthDeg: number;
  /** True when sun is below horizon (moonlight + full campus lamps take over) */
  isNight: boolean;
  /** 0 = bright day, 1 = full dusk/night (drives smooth lamp & window light transition) */
  nightFactor: number;
  /** 0..1 sunrise/sunset golden & crimson glow strength */
  twilightGlow: number;
  /** Main directional light color & intensity */
  keyLightColor: THREE.Color;
  keyLightIntensity: number;
  /** Hemisphere sky/ground ambient bounce */
  hemiSkyColor: THREE.Color;
  hemiGroundColor: THREE.Color;
  hemiIntensity: number;
  /** IBL environment reflection intensity */
  envIntensity: number;
  /** Distance fog color & density */
  fogColor: THREE.Color;
  fogDensity: number;
  /** Sky shader artistic & physical parameters */
  turbidity: number;
  rayleigh: number;
  mieCoefficient: number;
  mieDirectionalG: number;
  cloudCoverage: number;
  cloudTint: THREE.Color;
  /** Renderer exposure compensation (auto-adapts day vs night) */
  exposure: number;
  /** Surface physical weather states */
  wetness: number;
  snowCoverage: number;
  windStrength: number;
  /** Human-readable Chinese time-of-day label */
  phaseLabel: string;
}

/** Returns current Beijing (UTC+8) time as continuous hours in [0, 24). */
export function getCurrentBeijingTimeHours(): number {
  const now = new Date();
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60_000;
  const bj = new Date(utcMs + 8 * 3_600_000);
  return bj.getHours() + bj.getMinutes() / 60 + bj.getSeconds() / 3600;
}

/** Formats continuous hours (e.g. 17.75) as "17:45". */
export function formatTimeHours(hours: number): string {
  const wrapped = ((hours % 24) + 24) % 24;
  const h = Math.floor(wrapped);
  const m = Math.floor((wrapped - h) * 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function presetToTimeHours(preset: LightingPreset): number {
  switch (preset) {
    case "morning":
      return 8.5;
    case "noon":
      return 12.5;
    case "sunset":
      return 17.7;
  }
}

export function getPhaseLabel(hours: number): string {
  const h = ((hours % 24) + 24) % 24;
  if (h < 4.75) return "深夜静谧";
  if (h < 5.65) return "黎明微曦";
  if (h < 6.75) return "破晓朝霞";
  if (h < 9.5) return "清朗晨光";
  if (h < 11.5) return "上午晴日";
  if (h < 14.5) return "正午朗照";
  if (h < 16.9) return "午后暖阳";
  if (h < 18.45) return "金红晚霞";
  if (h < 19.65) return "蓝调黄昏";
  if (h < 22.0) return "晚自习灯火";
  return "夜深校园";
}

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = THREE.MathUtils.clamp((x - edge0) / (edge1 - edge0), 0, 1);
  return t * t * (3 - 2 * t);
}

/**
 * Computes physical solar position for Beijing (39.92°N, 116.41°E) mapped onto the
 * campus glTF coordinate frame (+X East, +Y Up, -Z North), plus physically coupled
 * atmospheric, twilight, moonlight, and multi-weather parameters.
 */
export function computeSolarAtmosphere(
  timeHours: number,
  weather: WeatherMode,
  dayOfYear = 145 // Pleasant late-spring/early-autumn solar arc (~14h daylight, ~68° noon peak)
): SolarAtmosphereSample {
  const h = ((timeHours % 24) + 24) % 24;

  // 1. Astronomical solar declination & hour angle for Beijing (UTC+8, 116.41°E)
  const latRad = THREE.MathUtils.degToRad(BEIJING_LAT_DEG);
  const declRad = THREE.MathUtils.degToRad(
    23.44 * Math.sin(((2 * Math.PI) / 365) * (dayOfYear - 81))
  );
  // Solar noon in Beijing (~12:14 CST due to 116.41°E vs 120°E standard meridian)
  const solarTime = h - (120.0 - BEIJING_LON_DEG) / 15.0;
  const hourAngleRad = THREE.MathUtils.degToRad((solarTime - 12.0) * 15.0);

  const sinAlt =
    Math.sin(latRad) * Math.sin(declRad) +
    Math.cos(latRad) * Math.cos(declRad) * Math.cos(hourAngleRad);
  const altRad = Math.asin(THREE.MathUtils.clamp(sinAlt, -1, 1));
  const cosAlt = Math.max(0.0001, Math.cos(altRad));

  // Azimuth measured clockwise from North (0=N, 90=E, 180=S, 270=W)
  const cosAz = THREE.MathUtils.clamp(
    (Math.sin(declRad) - Math.sin(altRad) * Math.sin(latRad)) / (cosAlt * Math.cos(latRad)),
    -1,
    1
  );
  let azRad = Math.acos(cosAz);
  if (hourAngleRad > 0) {
    azRad = 2 * Math.PI - azRad;
  }

  // Convert (Altitude, Azimuth-from-North) -> glTF ENU (+X=East, +Y=Up, -Z=North)
  const sunDir = new THREE.Vector3(
    Math.cos(altRad) * Math.sin(azRad),
    Math.sin(altRad),
    -Math.cos(altRad) * Math.cos(azRad)
  ).normalize();

  const sunElevationDeg = THREE.MathUtils.radToDeg(altRad);
  const sunAzimuthDeg = THREE.MathUtils.radToDeg(azRad);

  // Night transition & sunrise/sunset twilight crimson glow
  const isNight = sunElevationDeg < -1.5;
  const nightFactor = smoothstep(4.5, -5.5, sunElevationDeg);
  // Peak golden/crimson twilight glow around -3° .. +12° solar elevation
  const twilightRise = smoothstep(-6.5, 2.0, sunElevationDeg);
  const twilightFall = 1.0 - smoothstep(4.0, 20.0, sunElevationDeg);
  const twilightGlow = THREE.MathUtils.clamp(twilightRise * twilightFall * 1.35, 0, 1);

  // Moonlight vector (graceful silver-blue arc opposite sun, always above horizon at night)
  const moonAngle = ((h + 12) % 24) / 24 * Math.PI * 2;
  const moonDir = new THREE.Vector3(
    Math.sin(moonAngle) * 0.65,
    0.62,
    Math.cos(moonAngle) * 0.44
  ).normalize();

  const keyLightDir = isNight
    ? moonDir
    : new THREE.Vector3(sunDir.x, Math.max(sunDir.y, 0.08), sunDir.z).normalize();

  // Base clear-sky sunlight color & intensity curve
  const dayColor = new THREE.Color(0xfffaf0);
  const goldenColor = new THREE.Color(0xff9248);
  const crimsonHorizon = new THREE.Color(0xff6b38);
  const moonColor = new THREE.Color(0x88aee6);

  const sunColor = dayColor.clone();
  sunColor.lerp(goldenColor, twilightGlow * 0.85);
  sunColor.lerp(crimsonHorizon, smoothstep(5.0, -2.5, sunElevationDeg) * (1 - nightFactor) * 0.65);

  const sunBaseIntensity =
    smoothstep(-2.0, 14.0, sunElevationDeg) * 3.1 +
    twilightGlow * 0.95;

  const keyLightColor = isNight ? moonColor.clone() : sunColor.clone();
  let keyLightIntensity = isNight
    ? 0.42 * (0.45 + 0.55 * nightFactor)
    : Math.max(0.2, sunBaseIntensity);

  // Hemisphere ambient colors across day -> sunset/sunrise -> blue hour -> deep night
  const hemiDaySky = new THREE.Color(0x9ecaff);
  const hemiSunsetSky = new THREE.Color(0xf7a47e);
  const hemiNightSky = new THREE.Color(0x162646);

  const hemiDayGnd = new THREE.Color(0x7c756c);
  const hemiSunsetGnd = new THREE.Color(0x523f42);
  const hemiNightGnd = new THREE.Color(0x0c111c);

  const hemiSkyColor = hemiDaySky
    .clone()
    .lerp(hemiSunsetSky, twilightGlow * 0.78)
    .lerp(hemiNightSky, nightFactor);
  const hemiGroundColor = hemiDayGnd
    .clone()
    .lerp(hemiSunsetGnd, twilightGlow * 0.65)
    .lerp(hemiNightGnd, nightFactor);

  let hemiIntensity = THREE.MathUtils.lerp(0.88, 0.24, nightFactor) + twilightGlow * 0.14;
  let envIntensity = THREE.MathUtils.lerp(1.05, 0.22, nightFactor);

  // Atmospheric fog color & density
  const fogDay = new THREE.Color(0xcde0f5);
  const fogTwilight = new THREE.Color(0xe69f78);
  const fogBlueHour = new THREE.Color(0x233354);
  const fogDeepNight = new THREE.Color(0x0a1120);

  const fogColor = fogDay
    .clone()
    .lerp(fogTwilight, twilightGlow * 0.88)
    .lerp(fogBlueHour, smoothstep(2.0, -5.0, sunElevationDeg) * 0.75)
    .lerp(fogDeepNight, smoothstep(-4.0, -11.0, sunElevationDeg));
  let fogDensity = 0.00105 + twilightGlow * 0.00045 + nightFactor * 0.00055;

  // Sky physical scattering + cloud styling
  let turbidity = 3.2 + twilightGlow * 7.8;
  const rayleigh = 1.45 + twilightGlow * 2.1;
  let mieCoefficient = 0.0045 + twilightGlow * 0.018;
  const mieDirectionalG = 0.82 + twilightGlow * 0.11;
  let cloudCoverage = 0.26;
  const cloudTint = new THREE.Color(0xffffff)
    .lerp(new THREE.Color(0xff9e66), twilightGlow * 0.92)
    .lerp(new THREE.Color(0x1f2d48), nightFactor * 0.92);

  let wetness = 0.0;
  let snowCoverage = 0.0;
  let windStrength = 0.35;
  let exposure = THREE.MathUtils.lerp(1.06, 1.24, nightFactor) + twilightGlow * 0.06;

  // Apply physical multi-weather coupling
  if (weather === "cloudy") {
    cloudCoverage = 0.78;
    keyLightIntensity *= isNight ? 0.65 : 0.42;
    hemiIntensity *= 1.18;
    envIntensity *= 0.88;
    turbidity += 4.0;
    fogDensity *= 1.45;
    fogColor.lerp(new THREE.Color(isNight ? 0x141b29 : 0xbbc6d4), 0.52);
    cloudTint.lerp(new THREE.Color(isNight ? 0x1a2232 : 0xd0d8e2), 0.48);
    windStrength = 0.62;
  } else if (weather === "rainy") {
    cloudCoverage = 0.92;
    wetness = 1.0;
    keyLightIntensity *= isNight ? 0.55 : 0.28;
    hemiIntensity *= 1.05;
    envIntensity *= 0.95; // keep reflections crisp on wet asphalt & puddles
    turbidity += 6.0;
    fogDensity = 0.0028 + nightFactor * 0.0008;
    fogColor.lerp(new THREE.Color(isNight ? 0x0d1524 : 0x7e8f9f), 0.72);
    cloudTint.lerp(new THREE.Color(isNight ? 0x141c2a : 0x8d9aa8), 0.68);
    windStrength = 1.15;
    exposure += 0.04;
  } else if (weather === "misty") {
    cloudCoverage = 0.55;
    wetness = 0.24;
    keyLightIntensity *= isNight ? 0.6 : 0.68;
    hemiIntensity *= 1.16;
    turbidity += 5.5;
    mieCoefficient += 0.025;
    fogDensity = 0.0046;
    fogColor.lerp(
      new THREE.Color(isNight ? 0x182236 : twilightGlow > 0.25 ? 0xe8b594 : 0xd5dfe8),
      0.66
    );
    windStrength = 0.22;
  } else if (weather === "snowy") {
    cloudCoverage = 0.86;
    snowCoverage = 1.0;
    wetness = 0.14;
    keyLightIntensity *= isNight ? 0.82 : 0.52;
    hemiIntensity *= 1.32; // snow ground bounce makes winter scenes softly luminous
    hemiGroundColor.lerp(new THREE.Color(isNight ? 0x26344a : 0xdce6f2), 0.62);
    envIntensity *= 1.05;
    fogDensity = 0.0030;
    fogColor.lerp(new THREE.Color(isNight ? 0x162134 : 0xd8e2ee), 0.68);
    cloudTint.lerp(new THREE.Color(isNight ? 0x222f46 : 0xe4ecf4), 0.65);
    windStrength = 0.78;
  }

  return {
    sunDir,
    keyLightDir,
    sunElevationDeg,
    sunAzimuthDeg,
    isNight,
    nightFactor,
    twilightGlow,
    keyLightColor,
    keyLightIntensity,
    hemiSkyColor,
    hemiGroundColor,
    hemiIntensity,
    envIntensity,
    fogColor,
    fogDensity,
    turbidity,
    rayleigh,
    mieCoefficient,
    mieDirectionalG,
    cloudCoverage,
    cloudTint,
    exposure,
    wetness,
    snowCoverage,
    windStrength,
    phaseLabel: getPhaseLabel(h),
  };
}
