import * as THREE from "three";
import { CampusLightAnchor } from "@/data/campusLights";
import { CampusId, QualityTier, WeatherMode } from "@/data/types";
import { UpgradedMaterialBuckets } from "./pbrMaterialSystem";
import { SolarAtmosphereSample } from "./sunAstronomy";

interface FixedCampusPointLight {
  light: THREE.PointLight;
  baseIntensity: number;
}

/**
 * Spatial greedy clustering that merges densely spaced campus lamp anchors into
 * permanent, world-fixed PointLights covering the entire compact campus uniformly.
 * Because lights are never reassigned based on camera position, moving or zooming
 * the camera causes ZERO light popping or flickering.
 */
function buildFixedCampusPointClusters(
  anchors: CampusLightAnchor[],
  mergeRadius: number,
  maxLights: number
): { pos: [number, number, number]; color: string; intensity: number; distance: number }[] {
  const candidates = anchors.filter((a) => a.kind !== "floodlight");
  const clusters: {
    sumX: number;
    sumY: number;
    sumZ: number;
    count: number;
    maxIntensity: number;
    maxDistance: number;
    color: string;
  }[] = [];

  const rSq = mergeRadius * mergeRadius;
  for (const a of candidates) {
    let merged = false;
    for (const c of clusters) {
      const cx = c.sumX / c.count;
      const cz = c.sumZ / c.count;
      const dx = a.pos[0] - cx;
      const dz = a.pos[2] - cz;
      if (dx * dx + dz * dz <= rSq) {
        c.sumX += a.pos[0];
        c.sumY += a.pos[1];
        c.sumZ += a.pos[2];
        c.count += 1;
        c.maxIntensity = Math.max(c.maxIntensity, a.intensity);
        c.maxDistance = Math.max(c.maxDistance, a.distance);
        merged = true;
        break;
      }
    }
    if (!merged) {
      clusters.push({
        sumX: a.pos[0],
        sumY: a.pos[1],
        sumZ: a.pos[2],
        count: 1,
        maxIntensity: a.intensity,
        maxDistance: a.distance,
        color: a.color,
      });
    }
  }

  // Sort deterministically by cluster weight so important courtyards/gates always get real lights
  clusters.sort((a, b) => b.count * b.maxIntensity - a.count * a.maxIntensity);

  return clusters.slice(0, maxLights).map((c) => ({
    pos: [c.sumX / c.count, Math.max(c.sumY / c.count, 3.2), c.sumZ / c.count],
    color: c.color,
    intensity: c.maxIntensity * (1.0 + Math.min(c.count - 1, 3) * 0.24),
    distance: Math.min(c.maxDistance + mergeRadius * 0.65, 32),
  }));
}

/**
 * Coordinates rock-solid, camera-invariant lighting for compact campus scenes:
 * - World-locked high-resolution DirectionalLight shadow frustum (up to 4096x4096 in Ultra mode)
 *   with ZERO view-distance cascade seams or camera-move shadow swimming
 * - Multi-temperature time-staggered interior room lighting (7 school schedule buckets)
 * - Fixed world-space campus PointLights & stadium floodlights (zero camera-distance popping)
 * - Campus-anchored 3D rain/snow weather particle volumes
 */
export class LightingAndWeatherSystem {
  /** Single world-locked sun/moon directional light (works cleanly in both Raster & PathTracer) */
  public readonly sunLight: THREE.DirectionalLight;
  public readonly hemiLight: THREE.HemisphereLight;

  private readonly scene: THREE.Scene;
  private readonly floodLights: { spot: THREE.SpotLight; cone: THREE.Mesh; baseIntensity: number }[] = [];
  private readonly fixedPointLights: FixedCampusPointLight[] = [];
  private readonly glowDecals: THREE.Mesh[] = [];
  private readonly glowDecalMat: THREE.MeshBasicMaterial;
  private readonly coneMat: THREE.MeshBasicMaterial;
  private readonly lightGroup = new THREE.Group();

  // Campus-centered weather particles (fixed over the whole campus, never chasing camera)
  private readonly rainPoints: THREE.LineSegments;
  private readonly rainPositions: Float32Array;
  private readonly rainMat: THREE.LineBasicMaterial;
  private readonly snowPoints: THREE.Points;
  private readonly snowPositions: Float32Array;
  private readonly snowPhases: Float32Array;
  private readonly snowMat: THREE.PointsMaterial;
  private readonly weatherGroup = new THREE.Group();
  private readonly campusCenter: THREE.Vector3;
  private readonly shadowHalfExtent: number;

  private currentShadowRes = 2048;
  private lastNightFactor = -1;

  constructor(
    scene: THREE.Scene,
    campusId: CampusId,
    campusCenter: [number, number, number],
    anchors: CampusLightAnchor[],
    quality: QualityTier
  ) {
    this.scene = scene;
    this.campusCenter = new THREE.Vector3(...campusCenter);
    // Tightly frame the entire compact campus so shadow texel density is maximized & camera-invariant
    this.shadowHalfExtent = campusId === "west" ? 116 : 82;
    this.lightGroup.name = "__campus_night_lights";
    this.weatherGroup.name = "__campus_weather_particles";

    // 1. World-locked sun/moon DirectionalLight (ZERO camera frustum cascades -> ZERO shimmer!)
    this.currentShadowRes = this.shadowSizeForQuality(quality);
    this.sunLight = new THREE.DirectionalLight(0xfff5e4, 2.8);
    this.sunLight.castShadow = true;
    this.sunLight.shadow.mapSize.set(this.currentShadowRes, this.currentShadowRes);
    this.sunLight.shadow.camera.near = 10;
    this.sunLight.shadow.camera.far = 420;
    this.sunLight.shadow.camera.left = -this.shadowHalfExtent;
    this.sunLight.shadow.camera.right = this.shadowHalfExtent;
    this.sunLight.shadow.camera.top = this.shadowHalfExtent;
    this.sunLight.shadow.camera.bottom = -this.shadowHalfExtent;
    this.sunLight.shadow.bias = -0.00028;
    this.sunLight.shadow.normalBias = 0.028;
    this.sunLight.shadow.radius = 1.5;
    this.sunLight.target.position.copy(this.campusCenter);
    scene.add(this.sunLight);
    scene.add(this.sunLight.target);

    // Hemisphere ambient sky/ground fill
    this.hemiLight = new THREE.HemisphereLight(0xaad0ff, 0x706c66, 0.85);
    scene.add(this.hemiLight);

    // 2. Soft radial glow decal texture for every individual courtyard lamp anchor
    const decalTex = this.createRadialGlowTexture();
    this.glowDecalMat = new THREE.MeshBasicMaterial({
      map: decalTex,
      color: 0xffd28e,
      transparent: true,
      opacity: 0.0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    // Subtle volumetric cone material for playground high-mast floodlights
    this.coneMat = new THREE.MeshBasicMaterial({
      color: 0xdcecff,
      transparent: true,
      opacity: 0.0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    });

    const decalGeo = new THREE.PlaneGeometry(1, 1);
    decalGeo.rotateX(-Math.PI / 2);

    for (const anchor of anchors) {
      if (anchor.kind === "floodlight") {
        const spot = new THREE.SpotLight(anchor.color, 0, anchor.distance, Math.PI * 0.34, 0.58, 1.4);
        spot.position.set(...anchor.pos);
        const tgt = new THREE.Object3D();
        if (anchor.target) {
          tgt.position.set(...anchor.target);
        } else {
          tgt.position.set(anchor.pos[0], 0, anchor.pos[2]);
        }
        this.lightGroup.add(tgt);
        spot.target = tgt;
        this.lightGroup.add(spot);

        const beamLen = spot.position.distanceTo(tgt.position) * 0.62;
        const coneGeo = new THREE.ConeGeometry(beamLen * 0.42, beamLen, 16, 1, true);
        coneGeo.translate(0, -beamLen * 0.5, 0);
        coneGeo.rotateX(Math.PI / 2);
        const cone = new THREE.Mesh(coneGeo, this.coneMat);
        cone.position.copy(spot.position);
        cone.lookAt(tgt.position);
        cone.frustumCulled = false;
        this.lightGroup.add(cone);

        this.floodLights.push({ spot, cone, baseIntensity: anchor.intensity });
      } else {
        const radius = anchor.kind === "gate_led" ? 8.5 : anchor.kind === "window_spill" ? 7.5 : 6.8;
        const decal = new THREE.Mesh(decalGeo, this.glowDecalMat);
        decal.scale.set(radius, 1, radius);
        decal.position.set(anchor.pos[0], 0.08, anchor.pos[2]);
        decal.renderOrder = 2;
        this.lightGroup.add(decal);
        this.glowDecals.push(decal);
      }
    }

    // 3. Permanent world-fixed campus PointLights (deterministically clustered once; never swapped on camera move!)
    const maxClusterLights = campusId === "west" ? 12 : 8;
    const clusters = buildFixedCampusPointClusters(anchors, 16, maxClusterLights);
    for (const cl of clusters) {
      const pl = new THREE.PointLight(cl.color, 0, cl.distance, 1.75);
      pl.position.set(...cl.pos);
      pl.visible = false;
      this.lightGroup.add(pl);
      this.fixedPointLights.push({ light: pl, baseIntensity: cl.intensity });
    }
    scene.add(this.lightGroup);

    // 4. Campus-fixed rain streak volume (1,500 crisp diagonal streaks covering entire campus)
    const span = this.shadowHalfExtent * 1.75;
    const rainCount = 1500;
    this.rainPositions = new Float32Array(rainCount * 6);
    for (let i = 0; i < rainCount; i++) {
      const rx = (Math.random() - 0.5) * span;
      const ry = Math.random() * 48;
      const rz = (Math.random() - 0.5) * span;
      const o = i * 6;
      this.rainPositions[o] = rx;
      this.rainPositions[o + 1] = ry;
      this.rainPositions[o + 2] = rz;
      this.rainPositions[o + 3] = rx - 0.14;
      this.rainPositions[o + 4] = ry - 1.15;
      this.rainPositions[o + 5] = rz - 0.08;
    }
    const rainGeo = new THREE.BufferGeometry();
    rainGeo.setAttribute("position", new THREE.BufferAttribute(this.rainPositions, 3));
    this.rainMat = new THREE.LineBasicMaterial({
      color: 0xc8def2,
      transparent: true,
      opacity: 0.36,
      depthWrite: false,
    });
    this.rainPoints = new THREE.LineSegments(rainGeo, this.rainMat);
    this.rainPoints.position.set(this.campusCenter.x, 0, this.campusCenter.z);
    this.rainPoints.visible = false;
    this.rainPoints.frustumCulled = false;
    this.weatherGroup.add(this.rainPoints);

    // 5. Campus-fixed gentle falling winter snowflakes (1,300 flakes)
    const snowCount = 1300;
    this.snowPositions = new Float32Array(snowCount * 3);
    this.snowPhases = new Float32Array(snowCount);
    for (let i = 0; i < snowCount; i++) {
      this.snowPositions[i * 3] = (Math.random() - 0.5) * span;
      this.snowPositions[i * 3 + 1] = Math.random() * 45;
      this.snowPositions[i * 3 + 2] = (Math.random() - 0.5) * span;
      this.snowPhases[i] = Math.random() * Math.PI * 2;
    }
    const snowGeo = new THREE.BufferGeometry();
    snowGeo.setAttribute("position", new THREE.BufferAttribute(this.snowPositions, 3));
    this.snowMat = new THREE.PointsMaterial({
      color: 0xf4f8ff,
      size: 0.42,
      map: decalTex,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
    });
    this.snowPoints = new THREE.Points(snowGeo, this.snowMat);
    this.snowPoints.position.set(this.campusCenter.x, 0, this.campusCenter.z);
    this.snowPoints.visible = false;
    this.snowPoints.frustumCulled = false;
    this.weatherGroup.add(this.snowPoints);
    scene.add(this.weatherGroup);
  }

  private shadowSizeForQuality(quality: QualityTier): number {
    if (quality === "low") return 1024;
    if (quality === "medium" || quality === "high") return 2048;
    return 4096; // Ultra High Quality: razor-sharp 4K world-locked shadow map (unrestricted on all devices)
  }

  private createRadialGlowTexture(): THREE.CanvasTexture {
    const c = document.createElement("canvas");
    c.width = 128;
    c.height = 128;
    const ctx = c.getContext("2d")!;
    const g = ctx.createRadialGradient(64, 64, 2, 64, 64, 62);
    g.addColorStop(0.0, "rgba(255,255,255,1.0)");
    g.addColorStop(0.35, "rgba(255,244,218,0.55)");
    g.addColorStop(0.7, "rgba(255,220,165,0.16)");
    g.addColorStop(1.0, "rgba(255,210,140,0.0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 128, 128);
    const tex = new THREE.CanvasTexture(c);
    tex.needsUpdate = true;
    return tex;
  }

  /** Dynamically switches shadow map resolution (1024 / 2048 / 4096) without context reset. */
  public setQuality(quality: QualityTier, maxTextureSize = 4096): void {
    const targetRes = Math.min(this.shadowSizeForQuality(quality), maxTextureSize);
    if (targetRes !== this.currentShadowRes) {
      this.currentShadowRes = targetRes;
      this.sunLight.shadow.mapSize.set(targetRes, targetRes);
      if (this.sunLight.shadow.map) {
        this.sunLight.shadow.map.dispose();
        this.sunLight.shadow.map = null;
      }
      this.sunLight.shadow.radius = quality === "ultra" ? 1.25 : 1.65;
      this.sunLight.shadow.needsUpdate = true;
    }
  }

  /** Hides additive cones/decals/particles while physical GPU PathTracer renders directly. */
  public setPathTracingMode(active: boolean): void {
    for (const fl of this.floodLights) {
      fl.cone.visible = !active && this.lastNightFactor > 0.12;
    }
    for (const d of this.glowDecals) {
      d.visible = !active;
    }
    this.weatherGroup.visible = !active;
  }

  public update(
    sample: SolarAtmosphereSample,
    timeHours: number,
    weather: WeatherMode,
    buckets: UpgradedMaterialBuckets | null,
    dt: number,
    elapsedSec: number,
    pathTracingActive: boolean
  ): void {
    // 1. World-locked sun/moon light position (100% independent of camera movement!)
    this.sunLight.position
      .copy(sample.keyLightDir)
      .multiplyScalar(195)
      .add(this.campusCenter);
    this.sunLight.target.position.copy(this.campusCenter);
    this.sunLight.target.updateMatrixWorld();
    this.sunLight.color.copy(sample.keyLightColor);
    this.sunLight.intensity = sample.keyLightIntensity * (pathTracingActive ? 1.15 : 1.0);

    this.hemiLight.color.copy(sample.hemiSkyColor);
    this.hemiLight.groundColor.copy(sample.hemiGroundColor);
    this.hemiLight.intensity = sample.hemiIntensity;

    // 2. Realistic Beijing school lighting schedule by timeOfDay & overcast weather
    const h = ((timeHours % 24) + 24) % 24;
    const isGloomyDay = (weather === "rainy" || weather === "cloudy" || weather === "snowy") && !sample.isNight;
    const nightAmt = sample.nightFactor;
    this.lastNightFactor = nightAmt;

    const eveningActive =
      h >= 17.0 && h <= 22.3
        ? 1.0
        : h > 22.3 && h < 23.4
        ? 1.0 - (h - 22.3) / 1.1
        : h >= 5.5 && h < 7.2
        ? 0.55
        : 0.08;

    // 3. Drive 7 interior room & luminaire buckets + outdoor lamps + signage LEDs
    if (buckets) {
      const bucketColors: Record<number, { light: number; glow: number; onWeight: number }> = {
        0: { light: 0xfff6e8, glow: 0xffe4bc, onWeight: Math.max(nightAmt * eveningActive * 1.05, isGloomyDay ? 0.36 : 0.0) },
        1: { light: 0xf7f5ef, glow: 0xf2dec0, onWeight: Math.max(nightAmt * eveningActive * 0.92, isGloomyDay ? 0.24 : 0.0) },
        2: { light: 0xfff1dc, glow: 0xffd7a4, onWeight: Math.max(nightAmt * Math.max(0, eveningActive - 0.15) * 1.0, isGloomyDay ? 0.18 : 0.0) },
        3: { light: 0xf2f4fa, glow: 0xdfe6f2, onWeight: Math.max(nightAmt * (eveningActive > 0.45 ? 0.85 : 0.12), 0.0) },
        4: { light: 0xffd89e, glow: 0xffbe74, onWeight: Math.max(nightAmt * (h >= 23 || h < 5.5 ? 0.65 : 1.08), isGloomyDay ? 0.42 : 0.08) },
        5: { light: 0xffcfa0, glow: 0xffb368, onWeight: Math.max(nightAmt * (h >= 22.5 || h < 6 ? 0.38 : 1.05), isGloomyDay ? 0.38 : 0.10) },
        6: { light: 0xeef5ff, glow: 0xd0e2f8, onWeight: Math.max(nightAmt * 0.88, isGloomyDay ? 0.32 : 0.0) },
      };

      for (let bIdx = 0; bIdx < 7; bIdx++) {
        const cfg = bucketColors[bIdx];
        const w = THREE.MathUtils.clamp(cfg.onWeight, 0, 1.15);
        const lMats = buckets.interiorLights.get(bIdx) ?? [];
        for (const m of lMats) {
          m.emissive.setHex(cfg.light);
          m.emissiveIntensity = w * 3.2;
        }
        const gMats = buckets.interiorGlows.get(bIdx) ?? [];
        for (const m of gMats) {
          m.emissive.setHex(cfg.glow);
          m.emissiveIntensity = w * 0.92;
        }
      }

      const lampOn = THREE.MathUtils.smoothstep(nightAmt, 0.12, 0.65);
      for (const lm of buckets.outdoorLamps) {
        lm.emissive.setHex(0xffd28c);
        lm.emissiveIntensity = 0.08 + lampOn * 3.8;
      }

      const floodOn = lampOn * (h >= 16.5 && h <= 21.8 ? 1.0 : 0.18);
      for (const fm of buckets.floodlightHeads) {
        fm.emissive.setHex(0xf0f6ff);
        fm.emissiveIntensity = 0.12 + floodOn * 4.5;
      }

      const ledIntensity = 0.85 + nightAmt * 2.1 + sample.twilightGlow * 0.6;
      for (const sm of buckets.ledSignage) {
        sm.emissiveIntensity = ledIntensity;
      }
    }

    // 4. Update playground SpotLights & permanent fixed campus PointLights (ZERO camera-based popping)
    const lampOn = THREE.MathUtils.smoothstep(nightAmt, 0.12, 0.65);
    const floodOn = lampOn * (h >= 16.5 && h <= 21.8 ? 1.0 : 0.18);

    this.coneMat.opacity = pathTracingActive ? 0 : floodOn * (weather === "misty" || weather === "rainy" ? 0.10 : 0.05);
    for (const fl of this.floodLights) {
      fl.spot.intensity = fl.baseIntensity * floodOn;
      fl.spot.visible = floodOn > 0.02;
      fl.cone.visible = !pathTracingActive && floodOn > 0.04;
    }

    this.glowDecalMat.opacity = pathTracingActive ? 0 : lampOn * 0.34;

    const lightsVisible = lampOn > 0.02;
    for (const slot of this.fixedPointLights) {
      slot.light.visible = lightsVisible;
      slot.light.intensity = lightsVisible ? slot.baseIntensity * lampOn : 0;
    }

    // 5. Update campus-fixed rain & snow particle volumes
    const isRain = weather === "rainy" && !pathTracingActive;
    const isSnow = weather === "snowy" && !pathTracingActive;
    this.rainPoints.visible = isRain;
    this.snowPoints.visible = isSnow;

    const span = this.shadowHalfExtent * 1.75;
    if (isRain) {
      this.rainMat.color.setHex(sample.isNight ? 0x6f8eb5 : 0xcde0f4);
      this.rainMat.opacity = sample.isNight ? 0.28 : 0.36;
      const fallSpeed = 34.0 * dt;
      const windDrift = 3.2 * dt;
      const arr = this.rainPositions;
      for (let i = 0; i < arr.length; i += 6) {
        arr[i] -= windDrift;
        arr[i + 1] -= fallSpeed;
        arr[i + 3] -= windDrift;
        arr[i + 4] -= fallSpeed;
        if (arr[i + 1] < 0) {
          const rx = (Math.random() - 0.5) * span;
          const ry = 38 + Math.random() * 14;
          const rz = (Math.random() - 0.5) * span;
          arr[i] = rx;
          arr[i + 1] = ry;
          arr[i + 2] = rz;
          arr[i + 3] = rx - 0.14;
          arr[i + 4] = ry - 1.15;
          arr[i + 5] = rz - 0.08;
        }
      }
      this.rainPoints.geometry.attributes.position.needsUpdate = true;
    }

    if (isSnow) {
      this.snowMat.color.setHex(sample.isNight ? 0x9fb8db : 0xf7faff);
      const fallSpeed = 3.8 * dt;
      const arr = this.snowPositions;
      const ph = this.snowPhases;
      for (let i = 0; i < ph.length; i++) {
        const o = i * 3;
        arr[o] += Math.sin(elapsedSec * 0.9 + ph[i]) * 1.1 * dt;
        arr[o + 1] -= fallSpeed;
        arr[o + 2] += Math.cos(elapsedSec * 0.7 + ph[i]) * 0.8 * dt;
        if (arr[i * 3 + 1] < 0) {
          arr[o] = (Math.random() - 0.5) * span;
          arr[o + 1] = 36 + Math.random() * 12;
          arr[o + 2] = (Math.random() - 0.5) * span;
        }
      }
      this.snowPoints.geometry.attributes.position.needsUpdate = true;
    }
  }

  public dispose(): void {
    this.sunLight.shadow.map?.dispose();
    this.scene.remove(this.sunLight);
    this.scene.remove(this.sunLight.target);
    this.scene.remove(this.hemiLight);
    this.scene.remove(this.lightGroup);
    this.scene.remove(this.weatherGroup);

    this.glowDecalMat.map?.dispose();
    this.glowDecalMat.dispose();
    this.coneMat.dispose();
    for (const fl of this.floodLights) {
      fl.cone.geometry.dispose();
    }
    if (this.glowDecals.length > 0) {
      this.glowDecals[0].geometry.dispose();
    }
    this.rainPoints.geometry.dispose();
    this.rainMat.dispose();
    this.snowPoints.geometry.dispose();
    this.snowMat.dispose();
  }
}
