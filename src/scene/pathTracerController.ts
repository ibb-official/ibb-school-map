import * as THREE from "three";
import type { BVHWorker, WebGLPathTracer } from "three-gpu-pathtracer";
import { SolarAtmosphereSample } from "./sunAstronomy";

export interface PathTracerStatus {
  phase: "idle" | "building" | "rendering" | "error";
  samples: number;
  targetSamples: number;
  message?: string;
}

interface GlassMaterialBackup {
  material: THREE.MeshPhysicalMaterial;
  transparent: boolean;
  opacity: number;
  transmission: number;
  roughness: number;
  ior: number;
  thickness: number;
}

interface InternalTracerFields {
  _quad?: { dispose?: () => void; material?: { dispose?: () => void } };
  _pathTracer?: {
    dispose?: () => void;
    material?: {
      stratifiedTexture?: {
        strata: number;
        init: (count?: number, depth?: number, strata?: number) => void;
      };
    };
  };
  _lowResPathTracer?: { dispose?: () => void };
  _generator?: { bvh?: unknown; _bvhWorker?: unknown };
}

/**
 * Ensures quantized glTF BufferAttributes (Int16/Int8 from KHR_mesh_quantization)
 * and Uint16 indices are cleanly expanded to Float32 / Uint32 before BVH merging.
 */
function normalizeGeometryForPathTracer(root: THREE.Object3D): void {
  root.traverseVisible((obj) => {
    if (!(obj as THREE.Mesh).isMesh) return;
    const mesh = obj as THREE.Mesh;
    const geo = mesh.geometry;
    if (!geo) return;

    for (const attrName of ["position", "normal", "uv", "color"] as const) {
      const attr = geo.getAttribute(attrName);
      if (!attr) continue;
      const isFloat32 =
        attr.array instanceof Float32Array &&
        !attr.normalized &&
        !(attr as THREE.InterleavedBufferAttribute).isInterleavedBufferAttribute;
      if (!isFloat32) {
        const itemSize = attr.itemSize;
        const count = attr.count;
        const arr = new Float32Array(count * itemSize);
        for (let i = 0; i < count; i++) {
          arr[i * itemSize] = attr.getX(i);
          if (itemSize > 1) arr[i * itemSize + 1] = attr.getY(i);
          if (itemSize > 2) arr[i * itemSize + 2] = attr.getZ(i);
          if (itemSize > 3) arr[i * itemSize + 3] = attr.getW(i);
        }
        geo.setAttribute(attrName, new THREE.BufferAttribute(arr, itemSize));
      }
    }
    if (geo.index && !(geo.index.array instanceof Uint32Array)) {
      const idx = geo.index;
      const u32 = new Uint32Array(idx.count);
      for (let i = 0; i < idx.count; i++) {
        u32[i] = idx.getX(i);
      }
      geo.setIndex(new THREE.BufferAttribute(u32, 1));
    }
  });
}

function nextPaintFrame(): Promise<void> {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => resolve()));
  });
}

/**
 * Generates an HDR Equirectangular sky texture matching Three.js & `three-gpu-pathtracer`'s
 * exact `equirectDirectionToUv` convention (`u = atan2(z, x)/(2π) + 0.5`, `v = 1 - acos(y)/π`),
 * aligned with Beijing solar direction and coupled to weather overcast/twilight states.
 */
function buildEquirectSkyDataTexture(
  sample: SolarAtmosphereSample,
  weatherDarken = 0,
  width = 512,
  height = 256
): THREE.DataTexture {
  const data = new Float32Array(width * height * 4);
  const sunDir = sample.sunDir.clone().normalize();
  const night = sample.nightFactor;
  const tw = sample.twilightGlow;
  const overcast = THREE.MathUtils.clamp(weatherDarken, 0, 1);

  // Linear-space atmospheric colors matching AtmosphereSkySystem
  const dayZen = new THREE.Color().setRGB(0.055, 0.21, 0.62);
  const dayHor = new THREE.Color().setRGB(0.56, 0.74, 0.92);
  const twZen = new THREE.Color().setRGB(0.07, 0.11, 0.30);
  const twHor = new THREE.Color().setRGB(1.05, 0.38, 0.14);
  const nightZen = new THREE.Color().setRGB(0.01, 0.02, 0.055);
  const nightHor = new THREE.Color().setRGB(0.045, 0.068, 0.125);

  const zen = dayZen.clone().lerp(twZen, tw * 0.88).lerp(nightZen, night);
  const hor = dayHor.clone().lerp(twHor, tw * 0.94).lerp(nightHor, night);
  const fogCol = sample.fogColor.clone();
  zen.lerp(fogCol, overcast * 0.65);
  hor.lerp(fogCol, overcast * 0.72);

  const gnd = sample.hemiGroundColor
    .clone()
    .lerp(fogCol, 0.45)
    .multiplyScalar(sample.isNight ? 0.16 : 0.48);
  const sunCol = sample.keyLightColor.clone();
  const dir = new THREE.Vector3();
  const col = new THREE.Color();

  for (let y = 0; y < height; y++) {
    // v=0 bottom (-Y), v=1 top (+Y) -> matches `uv.y = 1.0 - acos(dir.y) / PI`
    const v = y / (height - 1);
    const phi = (1.0 - v) * Math.PI;
    const sinPhi = Math.sin(phi);
    const cosPhi = Math.cos(phi);

    for (let x = 0; x < width; x++) {
      // u=0..1 -> theta = (u - 0.5) * 2*PI -> matches `atan(dir.z, dir.x) / (2*PI) + 0.5`
      const u = x / (width - 1);
      const theta = (u - 0.5) * Math.PI * 2.0;
      dir.set(sinPhi * Math.cos(theta), cosPhi, sinPhi * Math.sin(theta)).normalize();

      if (dir.y >= 0) {
        const hCurve = Math.pow(1.0 - dir.y, 2.4);
        col.copy(zen).lerp(hor, hCurve);

        const sDot = Math.max(dir.dot(sunDir), 0);
        if (!sample.isNight) {
          const sunVis = 1.0 - overcast * 0.82;
          // Gentle atmospheric sun aureole: direct sun energy & crisp shadows come from DirectionalLight
          // so envMap MIS distributes samples evenly across the sky dome without fireflies or double-lighting.
          const halo = Math.pow(sDot, 10.0) * (0.42 + 0.95 * tw) * sunVis;
          const corona = Math.pow(sDot, 90.0) * 0.85 * sunVis;
          const disc = THREE.MathUtils.smoothstep(sDot, 0.9975, 0.9993) * 2.2 * sunVis;
          col.r += sunCol.r * (halo + corona + disc);
          col.g += sunCol.g * (halo + corona + disc);
          col.b += sunCol.b * (halo + corona + disc);
        }
      } else {
        col.copy(gnd).lerp(hor, Math.exp(dir.y * 5.0) * 0.55);
      }

      const idx = (y * width + x) * 4;
      const gain = sample.isNight ? 0.5 : 0.92;
      data[idx] = col.r * gain;
      data[idx + 1] = col.g * gain;
      data[idx + 2] = col.b * gain;
      data[idx + 3] = 1.0;
    }
  }

  const tex = new THREE.DataTexture(data, width, height, THREE.RGBAFormat, THREE.FloatType);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.needsUpdate = true;
  return tex;
}

/**
 * Lazy-loaded True GPU Monte Carlo Path Tracing Controller (Track B).
 * Uses `three-gpu-pathtracer` + `three-mesh-bvh` for multi-bounce global illumination,
 * physically refractive campus windows showing 3D interiors, and crisp PNG photo export.
 */
export class PathTracerController {
  private tracer: WebGLPathTracer | null = null;
  private bvhWorker: (BVHWorker & { dispose?: () => void }) | null = null;
  private equirectEnv: THREE.DataTexture | null = null;
  private prevBackground: THREE.Color | THREE.Texture | THREE.CubeTexture | null = null;
  private prevEnv: THREE.Texture | null = null;
  private prevEnvIntensity = 0.64;
  private skyDomeRef: THREE.Object3D | null = null;
  private glassBackups: GlassMaterialBackup[] = [];
  private active = false;
  private paused = false;
  private mobileSafeMode = false;
  public targetSamples = 128;

  public isActive(): boolean {
    return this.active;
  }

  public isPaused(): boolean {
    return this.paused;
  }

  public setPaused(p: boolean): void {
    this.paused = p;
    if (this.tracer) {
      this.tracer.pausePathTracing = p;
    }
  }

  public getSamples(): number {
    return this.tracer ? Math.floor(this.tracer.samples) : 0;
  }

  /**
   * Switches campus architectural glass & pool water to thin-film physical `transmission`
   * during GPU path tracing so light refracts and reflects with true Fresnel optics.
   */
  private enablePhysicalGlassForPathTracer(root: THREE.Object3D): void {
    this.restorePhysicalGlass();
    const seen = new Set<THREE.Material>();
    root.traverse((obj) => {
      if (!(obj as THREE.Mesh).isMesh) return;
      const mesh = obj as THREE.Mesh;
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const mat of mats) {
        if (!mat || seen.has(mat)) continue;
        seen.add(mat);
        const phys = mat as THREE.MeshPhysicalMaterial;
        if (!phys.isMeshPhysicalMaterial) continue;
        if (
          phys.name === "Mat_Glass_Physical" ||
          phys.name === "Mat_WarmGlass_Physical" ||
          phys.name === "Mat_RockeryWater"
        ) {
          this.glassBackups.push({
            material: phys,
            transparent: phys.transparent,
            opacity: phys.opacity,
            transmission: phys.transmission,
            roughness: phys.roughness,
            ior: phys.ior,
            thickness: phys.thickness,
          });
          const isWater = phys.name === "Mat_RockeryWater";
          const isWarm = phys.name === "Mat_WarmGlass_Physical";
          phys.transparent = false;
          phys.opacity = 1.0;
          phys.transmission = isWater ? 0.62 : isWarm ? 0.72 : 0.84;
          phys.ior = isWater ? 1.333 : 1.5;
          phys.roughness = isWater ? 0.06 : 0.04;
          // Thin-film single-pane glazing avoids solid-block total internal reflection darkening
          phys.thickness = 0.0;
        }
      }
    });
  }

  private restorePhysicalGlass(): void {
    for (const rec of this.glassBackups) {
      rec.material.transparent = rec.transparent;
      rec.material.opacity = rec.opacity;
      rec.material.transmission = rec.transmission;
      rec.material.roughness = rec.roughness;
      rec.material.ior = rec.ior;
      rec.material.thickness = rec.thickness;
    }
    this.glassBackups.length = 0;
  }

  public async activate(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    camera: THREE.PerspectiveCamera,
    loadedRoot: THREE.Object3D,
    skyDome: THREE.Object3D,
    sample: SolarAtmosphereSample,
    weatherDarken: number,
    onStatus: (status: PathTracerStatus) => void,
    quality: "low" | "medium" | "high" | "ultra" = "high"
  ): Promise<boolean> {
    if (this.active) return true;
    const isLight = quality === "low" || quality === "medium";
    this.mobileSafeMode = isLight;
    this.targetSamples = quality === "ultra" ? 256 : quality === "high" ? 128 : 64;
    onStatus({
      phase: "building",
      samples: 0,
      targetSamples: this.targetSamples,
      message: "正在构建光线追踪 BVH 加速结构...",
    });

    // Yield a paint cycle so the building progress bar renders immediately before BVH work
    await nextPaintFrame();

    try {
      const mod = await import("three-gpu-pathtracer");
      const { WebGLPathTracer: PTClass } = mod;

      this.skyDomeRef = skyDome;
      skyDome.visible = false;
      this.enablePhysicalGlassForPathTracer(loadedRoot);
      normalizeGeometryForPathTracer(scene);
      scene.updateMatrixWorld(true);

      this.prevBackground = scene.background;
      this.prevEnv = scene.environment;
      this.prevEnvIntensity = scene.environmentIntensity;

      if (this.equirectEnv) this.equirectEnv.dispose();
      this.equirectEnv = buildEquirectSkyDataTexture(
        sample,
        weatherDarken,
        isLight ? 256 : 512,
        isLight ? 128 : 256
      );
      scene.environment = this.equirectEnv;
      scene.background = this.equirectEnv;
      scene.environmentIntensity = sample.isNight ? 0.35 : 0.85;

      if (!this.tracer) {
        this.tracer = new PTClass(renderer);
        // Guard against three-gpu-pathtracer@0.0.23 bug: StratifiedSamplesTexture.init(count, depth)
        // assigns image.width = depth & image.height = count, swapped relative to GLSL
        // `texelFetch(stratifiedTexture, ivec2(v, sobolBounceIndex), 0)` where `v` spans 0..16.
        // When bounces + transmissiveBounces < 12, v >= 9 reads out-of-bounds zeros and leaves
        // permanent 64x64 blue-noise black stippling across all surfaces.
        const st = (this.tracer as unknown as InternalTracerFields)._pathTracer?.material
          ?.stratifiedTexture;
        if (st && typeof st.init === "function") {
          const origInit = st.init.bind(st);
          st.init = (count = 20, depth = 20, strata = st.strata) => {
            origInit(Math.max(depth, 20), Math.max(count, 20), strata);
          };
          st.init(20, 20, st.strata);
        }
      }
      const texDim = isLight ? 512 : quality === "ultra" ? 1024 : 768;
      this.tracer.textureSize.set(texDim, texDim);
      this.tracer.bounces = quality === "ultra" ? 4 : quality === "high" ? 3 : 2;
      this.tracer.transmissiveBounces = quality === "ultra" ? 4 : quality === "high" ? 3 : 2;
      this.tracer.multipleImportanceSampling = true;
      this.tracer.filterGlossyFactor = 0.5;
      this.tracer.dynamicLowRes = true;
      this.tracer.lowResScale = isLight ? 0.42 : 0.5;
      this.tracer.renderScale = isLight ? 0.78 : 1.0;
      this.tracer.minSamples = 1;
      this.tracer.fadeDuration = 180;
      this.tracer.tiles.set(isLight ? 2 : 3, isLight ? 2 : 3);

      // Prefer off-thread BVH worker if bundler/CSP permits; fall back seamlessly to sync `setScene`
      let builtAsync = false;
      try {
        if (!this.bvhWorker) {
          const workerMod = await import("three-mesh-bvh/src/workers/GenerateMeshBVHWorker.js");
          const WorkerCtor = workerMod.GenerateMeshBVHWorker;
          if (typeof WorkerCtor === "function") {
            const worker = new WorkerCtor();
            this.bvhWorker = worker;
            this.tracer.setBVHWorker(worker);
          }
        }
        if (this.bvhWorker) {
          await this.tracer.setSceneAsync(scene, camera, {
            onProgress: (p: number) => {
              onStatus({
                phase: "building",
                samples: 0,
                targetSamples: this.targetSamples,
                message: `正在构建 BVH 光追加速结构 (${Math.round(p * 100)}%)...`,
              });
            },
          });
          builtAsync = true;
        }
      } catch {
        // Worker unavailable or blocked by bundler/CSP -> release worker, clear rejected BVH promise & build directly
        try {
          this.bvhWorker?.dispose?.();
        } catch {
          // Ignore worker teardown error
        }
        this.bvhWorker = null;
        const internal = this.tracer as unknown as InternalTracerFields;
        if (internal._generator) {
          internal._generator.bvh = null;
          internal._generator._bvhWorker = null;
        }
      }

      if (!builtAsync) {
        this.tracer.setScene(scene, camera);
      }

      this.active = true;
      this.paused = false;
      this.tracer.pausePathTracing = false;
      this.tracer.enablePathTracing = true;
      this.tracer.reset();
      onStatus({ phase: "rendering", samples: 0, targetSamples: this.targetSamples });
      return true;
    } catch (err) {
      // Restore raster scene cleanly on any WebGL limitation
      this.restorePhysicalGlass();
      if (this.skyDomeRef) this.skyDomeRef.visible = true;
      if (this.prevBackground !== null) scene.background = this.prevBackground;
      if (this.prevEnv !== null) scene.environment = this.prevEnv;
      scene.environmentIntensity = this.prevEnvIntensity;
      this.active = false;
      onStatus({
        phase: "error",
        samples: 0,
        targetSamples: this.targetSamples,
        message:
          err instanceof Error
            ? `真光追初始化失败：${err.message}`
            : "当前 GPU 暂不支持真光追扩展，已保持实时渲染。",
      });
      return false;
    }
  }

  public syncEnvironmentAndLights(
    scene: THREE.Scene,
    sample: SolarAtmosphereSample,
    weatherDarken: number
  ): void {
    if (!this.active || !this.tracer) return;
    if (this.equirectEnv) this.equirectEnv.dispose();
    this.equirectEnv = buildEquirectSkyDataTexture(
      sample,
      weatherDarken,
      this.mobileSafeMode ? 256 : 512,
      this.mobileSafeMode ? 128 : 256
    );
    scene.environment = this.equirectEnv;
    scene.background = this.equirectEnv;
    scene.environmentIntensity = sample.isNight ? 0.35 : 0.85;
    this.tracer.updateEnvironment();
    this.tracer.updateLights();
    this.tracer.updateMaterials();
    this.tracer.reset();
  }

  public notifyCameraMoved(): void {
    if (!this.active || !this.tracer) return;
    this.tracer.updateCamera();
  }

  public renderFrame(): number {
    if (!this.active || !this.tracer) return 0;
    if (!this.paused && this.tracer.samples < this.targetSamples) {
      this.tracer.renderSample();
    }
    return Math.floor(this.tracer.samples);
  }

  public deactivate(scene: THREE.Scene): void {
    if (!this.active) return;
    this.active = false;
    this.paused = false;
    this.restorePhysicalGlass();
    if (this.skyDomeRef) {
      this.skyDomeRef.visible = true;
    }
    scene.background = this.prevBackground;
    scene.environment = this.prevEnv;
    scene.environmentIntensity = this.prevEnvIntensity;
    if (this.equirectEnv) {
      this.equirectEnv.dispose();
      this.equirectEnv = null;
    }
  }

  /** Captures the current WebGL canvas as a clean PNG download (works even when preserveDrawingBuffer is false). */
  public downloadSnapshot(renderer: THREE.WebGLRenderer, filename: string): void {
    if (this.active && this.tracer) {
      // Pause path tracing during snapshot so renderSample() blits the already-accumulated
      // target texture onto the canvas cleanly in <1ms without launching a new raytracing pass.
      const prevPaused = this.tracer.pausePathTracing;
      this.tracer.pausePathTracing = true;
      this.tracer.renderSample();
      this.tracer.pausePathTracing = prevPaused;
    }
    const dataUrl = renderer.domElement.toDataURL("image/png");
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  public dispose(): void {
    this.restorePhysicalGlass();
    this.equirectEnv?.dispose();
    this.equirectEnv = null;
    try {
      this.bvhWorker?.dispose?.();
    } catch {
      // Ignore worker cleanup error
    }
    this.bvhWorker = null;

    if (this.tracer) {
      // Guard against three-gpu-pathtracer@0.0.23 upstream bug where `dispose()` references `_renderQuad` instead of `_quad`
      const internal = this.tracer as unknown as InternalTracerFields;
      try {
        internal._quad?.dispose?.();
        internal._quad?.material?.dispose?.();
        internal._pathTracer?.dispose?.();
        internal._lowResPathTracer?.dispose?.();
      } catch {
        // Ignore partial disposal error
      }
      this.tracer = null;
    }
    this.active = false;
  }
}
