import * as THREE from "three";
import { CSM } from "three/examples/jsm/csm/CSM.js";
import { CampusLightAnchor } from "@/data/campusLights";
import { QualityTier, WeatherMode } from "@/data/types";
import { UpgradedMaterialBuckets } from "./pbrMaterialSystem";
import { SolarAtmosphereSample } from "./sunAstronomy";

interface ActivePoolLight {
  light: THREE.PointLight;
  assignedIdx: number;
}

/**
 * Coordinates physically accurate Cascaded Shadow Maps (CSM), multi-temperature
 * time-staggered interior room lighting, stadium floodlights with subtle volumetric
 * cones, dynamic proximity-ranked PointLight pool for outdoor lamps, ground glow decals,
 * and 3D rain/snow weather particle systems.
 */
export class LightingAndWeatherSystem {
  public readonly csm: CSM;
  public readonly hemiLight: THREE.HemisphereLight;
  /** Non-CSM sun directional light synced when path tracing mode activates */
  public readonly pathTraceSunLight: THREE.DirectionalLight;

  private readonly scene: THREE.Scene;
  private readonly anchors: CampusLightAnchor[];
  private readonly floodLights: { spot: THREE.SpotLight; cone: THREE.Mesh; baseIntensity: number }[] = [];
  private readonly pointPool: ActivePoolLight[] = [];
  private readonly glowDecals: THREE.Mesh[] = [];
  private readonly glowDecalMat: THREE.MeshBasicMaterial;
  private readonly coneMat: THREE.MeshBasicMaterial;
  private readonly lightGroup = new THREE.Group();

  // Weather particles (Rain streaks & Snowflakes)
  private readonly rainPoints: THREE.LineSegments;
  private readonly rainPositions: Float32Array;
  private readonly rainMat: THREE.LineBasicMaterial;
  private readonly snowPoints: THREE.Points;
  private readonly snowPositions: Float32Array;
  private readonly snowPhases: Float32Array;
  private readonly snowMat: THREE.PointsMaterial;
  private readonly weatherGroup = new THREE.Group();
  private readonly campusCenter: THREE.Vector3;

  private readonly _tmpPos = new THREE.Vector3();
  private lastNightFactor = -1;
  private activePoolLimit = 10;

  constructor(
    scene: THREE.Scene,
    camera: THREE.PerspectiveCamera,
    campusCenter: [number, number, number],
    anchors: CampusLightAnchor[],
    quality: QualityTier
  ) {
    this.scene = scene;
    this.anchors = anchors;
    this.campusCenter = new THREE.Vector3(...campusCenter);
    this.lightGroup.name = "__campus_night_lights";
    this.weatherGroup.name = "__campus_weather_particles";

    // 1. Cascaded Shadow Maps (3 cascades @ 2048px keeps near-field crisp and avoids shader recompile on quality switch)
    this.csm = new CSM({
      maxFar: quality === "smooth" ? 150 : quality === "refined" ? 200 : 240,
      cascades: 3,
      mode: "practical",
      parent: scene,
      shadowMapSize: 2048,
      lightDirection: new THREE.Vector3(-0.5, -0.8, -0.4).normalize(),
      lightIntensity: 2.6,
      lightNear: 1,
      lightFar: 320,
      shadowBias: -0.00035,
      camera,
    });
    this.csm.fade = true;
    for (const dl of this.csm.lights) {
      dl.shadow.normalBias = 0.035;
    }

    // Hemisphere ambient sky/ground fill
    this.hemiLight = new THREE.HemisphereLight(0xaad0ff, 0x706c66, 0.85);
    scene.add(this.hemiLight);

    // Mirror directional light (disabled during raster CSM, enabled cleanly for GPU PathTracer)
    this.pathTraceSunLight = new THREE.DirectionalLight(0xfff5e4, 2.8);
    this.pathTraceSunLight.visible = false;
    scene.add(this.pathTraceSunLight);

    // 2. Soft radial glow decal texture for distant/pooled campus lamps
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

    // Build floodlights + ground glow decals for every lamp anchor
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

        // Soft volumetric beam cone oriented from mast head toward court target
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
        // Soft ground light pool decal under courtyard lamps / wall sconces
        const radius = anchor.kind === "gate_led" ? 8.5 : anchor.kind === "window_spill" ? 7.5 : 6.8;
        const decal = new THREE.Mesh(decalGeo, this.glowDecalMat);
        decal.scale.set(radius, 1, radius);
        decal.position.set(anchor.pos[0], 0.08, anchor.pos[2]);
        decal.renderOrder = 2;
        this.lightGroup.add(decal);
        this.glowDecals.push(decal);
      }
    }

    // 3. Dynamic PointLight pool (pre-allocate 14 lights; cap active slots by quality tier)
    this.activePoolLimit = quality === "smooth" ? 6 : quality === "refined" ? 10 : 14;
    for (let i = 0; i < 14; i++) {
      const pl = new THREE.PointLight(0xffcf8c, 0, 18, 1.8);
      pl.visible = false;
      this.lightGroup.add(pl);
      this.pointPool.push({ light: pl, assignedIdx: -1 });
    }
    scene.add(this.lightGroup);

    // 4. Rain streak particles (1,400 crisp diagonal streaks surrounding camera/campus)
    const rainCount = 1400;
    this.rainPositions = new Float32Array(rainCount * 6);
    for (let i = 0; i < rainCount; i++) {
      const rx = (Math.random() - 0.5) * 160;
      const ry = Math.random() * 48;
      const rz = (Math.random() - 0.5) * 160;
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
    this.rainPoints.visible = false;
    this.rainPoints.frustumCulled = false;
    this.weatherGroup.add(this.rainPoints);

    // 5. Gentle falling winter snowflakes (1,200 soft round flakes)
    const snowCount = 1200;
    this.snowPositions = new Float32Array(snowCount * 3);
    this.snowPhases = new Float32Array(snowCount);
    for (let i = 0; i < snowCount; i++) {
      this.snowPositions[i * 3] = (Math.random() - 0.5) * 160;
      this.snowPositions[i * 3 + 1] = Math.random() * 45;
      this.snowPositions[i * 3 + 2] = (Math.random() - 0.5) * 160;
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
    this.snowPoints.visible = false;
    this.snowPoints.frustumCulled = false;
    this.weatherGroup.add(this.snowPoints);
    scene.add(this.weatherGroup);
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

  /**
   * Registers a single material with CSM while safely chaining any existing
   * custom `onBeforeCompile` hook (rain wetness, puddles, snow, foliage wind, parallax).
   */
  public setupMaterialForCSM(mat: THREE.Material): void {
    if (!(mat instanceof THREE.MeshStandardMaterial)) return;
    if (mat.userData.__csmChained) return;
    mat.userData.__csmChained = true;

    const prevCompile = mat.onBeforeCompile;
    const prevKeyFn = mat.customProgramCacheKey?.bind(mat);

    this.csm.setupMaterial(mat);
    const csmCompile = mat.onBeforeCompile;

    mat.onBeforeCompile = (shader, renderer) => {
      csmCompile.call(mat, shader, renderer);
      if (prevCompile && prevCompile !== THREE.Material.prototype.onBeforeCompile) {
        prevCompile.call(mat, shader, renderer);
      }
    };
    mat.customProgramCacheKey = () =>
      `${prevKeyFn ? prevKeyFn() : mat.type}_csm${this.csm.cascades}`;
    mat.needsUpdate = true;
  }

  /** Registers all loaded scene materials with CSM shadow injection (chaining custom shaders). */
  public setupMaterialsForCSM(root: THREE.Object3D): void {
    const seen = new Set<THREE.Material>();
    root.traverse((obj) => {
      if (!(obj as THREE.Mesh).isMesh) return;
      const mats = Array.isArray((obj as THREE.Mesh).material)
        ? ((obj as THREE.Mesh).material as THREE.Material[])
        : [(obj as THREE.Mesh).material as THREE.Material];
      for (const m of mats) {
        if (!m || seen.has(m)) continue;
        seen.add(m);
        this.setupMaterialForCSM(m);
      }
    });
  }

  /** Dynamically adjusts CSM range and active PointLight pool budget without shader recompile. */
  public setQuality(quality: QualityTier): void {
    this.activePoolLimit = quality === "smooth" ? 6 : quality === "refined" ? 10 : 14;
    const nextMaxFar = quality === "smooth" ? 150 : quality === "refined" ? 200 : 240;
    if (this.csm.maxFar !== nextMaxFar) {
      this.csm.maxFar = nextMaxFar;
      this.csm.updateFrustums();
    }
  }

  /** Toggles between rasterized CSM lights and clean single sun light for Path Tracer mode. */
  public setPathTracingMode(active: boolean): void {
    for (const dl of this.csm.lights) {
      dl.visible = !active;
    }
    this.pathTraceSunLight.visible = active;
    // Hide additive glow cones/decals during physical path tracing (path tracer computes true GI bounce!)
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
    camera: THREE.PerspectiveCamera,
    buckets: UpgradedMaterialBuckets | null,
    dt: number,
    elapsedSec: number,
    pathTracingActive: boolean
  ): void {
    // 1. Update CSM shadow cascades & hemisphere bounce
    // CSM expects lightDirection pointing FROM light TOWARD scene (negated keyLightDir)
    this.csm.lightDirection.copy(sample.keyLightDir).negate().normalize();
    for (const dl of this.csm.lights) {
      dl.color.copy(sample.keyLightColor);
      dl.intensity = sample.keyLightIntensity;
    }
    this.csm.update();

    this.pathTraceSunLight.position.copy(sample.keyLightDir).multiplyScalar(180).add(this.campusCenter);
    this.pathTraceSunLight.color.copy(sample.keyLightColor);
    this.pathTraceSunLight.intensity = sample.keyLightIntensity * 1.15;

    this.hemiLight.color.copy(sample.hemiSkyColor);
    this.hemiLight.groundColor.copy(sample.hemiGroundColor);
    this.hemiLight.intensity = sample.hemiIntensity;

    // 2. Compute realistic Beijing school lighting schedule by timeOfDay & overcast weather
    const h = ((timeHours % 24) + 24) % 24;
    const isGloomyDay = (weather === "rainy" || weather === "cloudy" || weather === "snowy") && !sample.isNight;
    const nightAmt = sample.nightFactor;
    this.lastNightFactor = nightAmt;

    // School evening activity factor: peaks 17:30-21:45 (evening self-study), winds down after 22:15
    const eveningActive =
      h >= 17.0 && h <= 22.3
        ? 1.0
        : h > 22.3 && h < 23.4
        ? 1.0 - (h - 22.3) / 1.1
        : h >= 5.5 && h < 7.2
        ? 0.55
        : 0.08; // late night: almost all classrooms off, guardhouse/hallways remain lit

    // 3. Drive 7 interior room & luminaire buckets + outdoor lamps + signage LEDs
    if (buckets) {
      // Color temperatures for each lighting bucket (K)
      const bucketColors: Record<number, { light: number; glow: number; onWeight: number }> = {
        // 4 classroom groups stagger on/off organically
        0: { light: 0xfff6e8, glow: 0xffe4bc, onWeight: Math.max(nightAmt * eveningActive * 1.05, isGloomyDay ? 0.36 : 0.0) },
        1: { light: 0xf7f5ef, glow: 0xf2dec0, onWeight: Math.max(nightAmt * eveningActive * 0.92, isGloomyDay ? 0.24 : 0.0) },
        2: { light: 0xfff1dc, glow: 0xffd7a4, onWeight: Math.max(nightAmt * Math.max(0, eveningActive - 0.15) * 1.0, isGloomyDay ? 0.18 : 0.0) },
        3: { light: 0xf2f4fa, glow: 0xdfe6f2, onWeight: Math.max(nightAmt * (eveningActive > 0.45 ? 0.85 : 0.12), 0.0) },
        // Warm hero group 0 (Guardhouse, Cafeteria, W-B5 veranda rooms — always cozy from dusk to dawn)
        4: { light: 0xffd89e, glow: 0xffbe74, onWeight: Math.max(nightAmt * (h >= 23 || h < 5.5 ? 0.65 : 1.08), isGloomyDay ? 0.42 : 0.08) },
        // Warm hero group 1 (School History Museum & Library warm gallery/reading lamps)
        5: { light: 0xffcfa0, glow: 0xffb368, onWeight: Math.max(nightAmt * (h >= 22.5 || h < 6 ? 0.38 : 1.05), isGloomyDay ? 0.38 : 0.10) },
        // Hallway & Stairwell safety lighting (stays softly lit all night)
        6: { light: 0xeef5ff, glow: 0xd0e2f8, onWeight: Math.max(nightAmt * 0.88, isGloomyDay ? 0.32 : 0.0) },
      };

      for (let bIdx = 0; bIdx < 7; bIdx++) {
        const cfg = bucketColors[bIdx];
        const w = THREE.MathUtils.clamp(cfg.onWeight, 0, 1.15);
        const lMats = buckets.interiorLights.get(bIdx) ?? [];
        for (const m of lMats) {
          m.emissive.setHex(cfg.light);
          // Strong HDR emissive (>1.5) triggers realistic Bloom halos through physical glass
          m.emissiveIntensity = w * 3.2;
        }
        const gMats = buckets.interiorGlows.get(bIdx) ?? [];
        for (const m of gMats) {
          m.emissive.setHex(cfg.glow);
          // Illuminated interior walls & ceilings make rooms genuinely bright when seen from outside
          m.emissiveIntensity = w * 0.92;
        }
      }

      // Outdoor campus courtyard lamp heads
      const lampOn = THREE.MathUtils.smoothstep(nightAmt, 0.12, 0.65);
      for (const lm of buckets.outdoorLamps) {
        lm.emissive.setHex(0xffd28c);
        lm.emissiveIntensity = 0.08 + lampOn * 3.8;
      }

      // Sports floodlight heads (active dusk -> 21:30)
      const floodOn = lampOn * (h >= 16.5 && h <= 21.8 ? 1.0 : 0.18);
      for (const fm of buckets.floodlightHeads) {
        fm.emissive.setHex(0xf0f6ff);
        fm.emissiveIntensity = 0.12 + floodOn * 4.5;
      }

      // Gate & stage LED signage boost at dusk/night
      const ledIntensity = 0.85 + nightAmt * 2.1 + sample.twilightGlow * 0.6;
      for (const sm of buckets.ledSignage) {
        sm.emissiveIntensity = ledIntensity;
      }
    }

    // 4. Update playground SpotLights, volumetric light cones & proximity PointLight pool
    const lampOn = THREE.MathUtils.smoothstep(nightAmt, 0.12, 0.65);
    const floodOn = lampOn * (h >= 16.5 && h <= 21.8 ? 1.0 : 0.18);

    this.coneMat.opacity = pathTracingActive ? 0 : floodOn * (weather === "misty" || weather === "rainy" ? 0.11 : 0.055);
    for (const fl of this.floodLights) {
      fl.spot.intensity = fl.baseIntensity * floodOn;
      fl.spot.visible = floodOn > 0.02;
      fl.cone.visible = !pathTracingActive && floodOn > 0.04;
    }

    this.glowDecalMat.opacity = pathTracingActive ? 0 : lampOn * 0.34;

    if (lampOn > 0.03) {
      // Rank non-floodlight anchors by proximity to camera & assign top N real PointLights
      const ranked: { idx: number; distSq: number }[] = [];
      for (let i = 0; i < this.anchors.length; i++) {
        const a = this.anchors[i];
        if (a.kind === "floodlight") continue;
        this._tmpPos.set(a.pos[0], a.pos[1], a.pos[2]);
        ranked.push({ idx: i, distSq: this._tmpPos.distanceToSquared(camera.position) });
      }
      ranked.sort((a, b) => a.distSq - b.distSq);

      for (let p = 0; p < this.pointPool.length; p++) {
        const slot = this.pointPool[p];
        const target = p < this.activePoolLimit ? ranked[p] : undefined;
        if (!target) {
          slot.light.visible = false;
          continue;
        }
        const a = this.anchors[target.idx];
        slot.light.visible = true;
        slot.light.position.set(a.pos[0], a.pos[1], a.pos[2]);
        slot.light.color.set(a.color);
        slot.light.distance = a.distance;
        slot.light.intensity = a.intensity * lampOn;
      }
    } else {
      for (const slot of this.pointPool) {
        slot.light.visible = false;
      }
    }

    // 5. Update weather particles centered around camera/campus
    const isRain = weather === "rainy" && !pathTracingActive;
    const isSnow = weather === "snowy" && !pathTracingActive;
    this.rainPoints.visible = isRain;
    this.snowPoints.visible = isSnow;

    if (isRain) {
      const cx = THREE.MathUtils.clamp(camera.position.x, this.campusCenter.x - 80, this.campusCenter.x + 80);
      const cz = THREE.MathUtils.clamp(camera.position.z, this.campusCenter.z - 80, this.campusCenter.z + 80);
      this.rainPoints.position.set(cx, 0, cz);
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
          const rx = (Math.random() - 0.5) * 160;
          const ry = 38 + Math.random() * 14;
          const rz = (Math.random() - 0.5) * 160;
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
      const cx = THREE.MathUtils.clamp(camera.position.x, this.campusCenter.x - 80, this.campusCenter.x + 80);
      const cz = THREE.MathUtils.clamp(camera.position.z, this.campusCenter.z - 80, this.campusCenter.z + 80);
      this.snowPoints.position.set(cx, 0, cz);
      this.snowMat.color.setHex(sample.isNight ? 0x9fb8db : 0xf7faff);
      const fallSpeed = 3.8 * dt;
      const arr = this.snowPositions;
      const ph = this.snowPhases;
      for (let i = 0; i < ph.length; i++) {
        const o = i * 3;
        arr[o] += Math.sin(elapsedSec * 0.9 + ph[i]) * 1.1 * dt;
        arr[o + 1] -= fallSpeed;
        arr[o + 2] += Math.cos(elapsedSec * 0.7 + ph[i]) * 0.8 * dt;
        if (arr[o + 1] < 0) {
          arr[o] = (Math.random() - 0.5) * 160;
          arr[o + 1] = 36 + Math.random() * 12;
          arr[o + 2] = (Math.random() - 0.5) * 160;
        }
      }
      this.snowPoints.geometry.attributes.position.needsUpdate = true;
    }
  }

  public dispose(): void {
    this.csm.dispose();
    for (const dl of this.csm.lights) {
      this.scene.remove(dl);
      this.scene.remove(dl.target);
    }
    this.scene.remove(this.hemiLight);
    this.scene.remove(this.pathTraceSunLight);
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
