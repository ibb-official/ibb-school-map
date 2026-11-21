import * as THREE from "three";
import type { WebGLPathTracer } from "three-gpu-pathtracer";
import { SolarAtmosphereSample } from "./sunAstronomy";

export interface PathTracerStatus {
  phase: "idle" | "building" | "rendering" | "error";
  samples: number;
  targetSamples: number;
  message?: string;
}

/**
 * Ensures quantized glTF BufferAttributes (Int16/Int8 from KHR_mesh_quantization)
 * are cleanly expanded to standard Float32 attributes before BVH scene merging.
 */
function normalizeGeometryForPathTracer(root: THREE.Object3D): void {
  root.traverse((obj) => {
    if (!(obj as THREE.Mesh).isMesh) return;
    const mesh = obj as THREE.Mesh;
    const geo = mesh.geometry;
    if (!geo) return;

    for (const attrName of ["position", "normal", "uv", "color"] as const) {
      const attr = geo.getAttribute(attrName);
      if (!attr) continue;
      const isFloat32 = attr.array instanceof Float32Array && !attr.normalized && !(attr as THREE.InterleavedBufferAttribute).isInterleavedBufferAttribute;
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

/**
 * Generates an HDR Equirectangular sky texture matching the current Beijing solar time
 * & twilight glow for physically accurate Multiple Importance Sampling (MIS) in GPU Path Tracing.
 */
function buildEquirectSkyDataTexture(sample: SolarAtmosphereSample, width = 512, height = 256): THREE.DataTexture {
  const data = new Float32Array(width * height * 4);
  const sunDir = sample.sunDir.clone().normalize();
  const night = sample.nightFactor;
  const tw = sample.twilightGlow;

  const dayZen = new THREE.Color(0x1e57b8);
  const dayHor = new THREE.Color(0xc2ddf5);
  const twZen = new THREE.Color(0x21306b);
  const twHor = new THREE.Color(0xff7936);
  const nightZen = new THREE.Color(0x030714);
  const nightHor = new THREE.Color(0x10192e);

  const zen = dayZen.clone().lerp(twZen, tw * 0.88).lerp(nightZen, night);
  const hor = dayHor.clone().lerp(twHor, tw * 0.94).lerp(nightHor, night);
  const gnd = sample.hemiGroundColor.clone().multiplyScalar(sample.isNight ? 0.14 : 0.45);
  const sunCol = sample.keyLightColor.clone();
  const dir = new THREE.Vector3();
  const col = new THREE.Color();

  for (let y = 0; y < height; y++) {
    // v=0 bottom (-Y), v=1 top (+Y)
    const v = y / (height - 1);
    const phi = (1.0 - v) * Math.PI; // 0 = +Y zenith, pi = -Y nadir
    const sinPhi = Math.sin(phi);
    const cosPhi = Math.cos(phi);

    for (let x = 0; x < width; x++) {
      const u = x / (width - 1);
      const theta = u * Math.PI * 2.0 - Math.PI;
      dir.set(sinPhi * Math.sin(theta), cosPhi, sinPhi * Math.cos(theta)).normalize();

      if (dir.y >= 0) {
        const hCurve = Math.pow(1.0 - dir.y, 2.8);
        col.copy(zen).lerp(hor, hCurve);
        // Solar aureole + bright HDR physical sun disc for crisp bounced lighting
        const sDot = Math.max(dir.dot(sunDir), 0);
        if (!sample.isNight) {
          const halo = Math.pow(sDot, 12.0) * (0.45 + 1.1 * tw);
          const disc = sDot > 0.9985 ? 18.0 : 0.0;
          col.r += sunCol.r * (halo + disc);
          col.g += sunCol.g * (halo + disc);
          col.b += sunCol.b * (halo + disc);
        }
      } else {
        col.copy(gnd).lerp(hor, Math.exp(dir.y * 6.0) * 0.45);
      }

      const idx = (y * width + x) * 4;
      const gain = sample.isNight ? 0.55 : 1.15;
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
 * physically refractive campus windows showing 3D interiors, and 2K/4K photo export.
 */
export class PathTracerController {
  private tracer: WebGLPathTracer | null = null;
  private equirectEnv: THREE.DataTexture | null = null;
  private prevBackground: THREE.Color | THREE.Texture | THREE.CubeTexture | null = null;
  private prevEnv: THREE.Texture | null = null;
  private skyDomeRef: THREE.Object3D | null = null;
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

  public async activate(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    camera: THREE.PerspectiveCamera,
    loadedRoot: THREE.Object3D,
    skyDome: THREE.Object3D,
    sample: SolarAtmosphereSample,
    onStatus: (status: PathTracerStatus) => void,
    mobileSafeMode = false
  ): Promise<boolean> {
    if (this.active) return true;
    this.mobileSafeMode = mobileSafeMode;
    if (mobileSafeMode) {
      this.targetSamples = 64;
    }
    onStatus({ phase: "building", samples: 0, targetSamples: this.targetSamples, message: "正在构建光线追踪 BVH 加速结构..." });

    try {
      const mod = await import("three-gpu-pathtracer");
      const { WebGLPathTracer: PTClass } = mod;

      // Prepare scene geometry & hide giant shader sky dome (replaced by MIS Equirectangular HDR sky)
      normalizeGeometryForPathTracer(loadedRoot);
      this.skyDomeRef = skyDome;
      skyDome.visible = false;
      scene.updateMatrixWorld(true);

      this.prevBackground = scene.background;
      this.prevEnv = scene.environment;

      if (this.equirectEnv) this.equirectEnv.dispose();
      this.equirectEnv = buildEquirectSkyDataTexture(
        sample,
        mobileSafeMode ? 256 : 512,
        mobileSafeMode ? 128 : 256
      );
      scene.environment = this.equirectEnv;
      scene.background = this.equirectEnv;

      if (!this.tracer) {
        this.tracer = new PTClass(renderer);
      }
      this.tracer.bounces = mobileSafeMode ? 2 : 4;
      this.tracer.transmissiveBounces = mobileSafeMode ? 2 : 4;
      this.tracer.multipleImportanceSampling = true;
      this.tracer.filterGlossyFactor = 0.5;
      this.tracer.dynamicLowRes = true;
      this.tracer.lowResScale = mobileSafeMode ? 0.35 : 0.45;
      this.tracer.renderScale = mobileSafeMode ? 0.65 : 1.0;
      if (mobileSafeMode) {
        this.tracer.tiles.set(3, 3);
      } else {
        this.tracer.tiles.set(2, 2);
      }

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

      this.active = true;
      this.paused = false;
      this.tracer.pausePathTracing = false;
      this.tracer.enablePathTracing = true;
      this.tracer.reset();
      onStatus({ phase: "rendering", samples: 0, targetSamples: this.targetSamples });
      return true;
    } catch (err) {
      // Restore raster scene cleanly on any WebGL limitation
      if (this.skyDomeRef) this.skyDomeRef.visible = true;
      if (this.prevBackground !== null) scene.background = this.prevBackground;
      if (this.prevEnv !== null) scene.environment = this.prevEnv;
      this.active = false;
      onStatus({
        phase: "error",
        samples: 0,
        targetSamples: this.targetSamples,
        message: err instanceof Error ? `真光追初始化失败：${err.message}` : "当前 GPU 暂不支持真光追扩展，已保持实时类光追渲染。",
      });
      return false;
    }
  }

  public syncEnvironmentAndLights(scene: THREE.Scene, sample: SolarAtmosphereSample): void {
    if (!this.active || !this.tracer) return;
    if (this.equirectEnv) this.equirectEnv.dispose();
    this.equirectEnv = buildEquirectSkyDataTexture(
      sample,
      this.mobileSafeMode ? 256 : 512,
      this.mobileSafeMode ? 128 : 256
    );
    scene.environment = this.equirectEnv;
    scene.background = this.equirectEnv;
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
    if (this.skyDomeRef) {
      this.skyDomeRef.visible = true;
    }
    scene.background = this.prevBackground;
    scene.environment = this.prevEnv;
    if (this.equirectEnv) {
      this.equirectEnv.dispose();
      this.equirectEnv = null;
    }
  }

  /** Captures the current WebGL canvas as a clean PNG download (works even when preserveDrawingBuffer is false). */
  public downloadSnapshot(renderer: THREE.WebGLRenderer, filename: string): void {
    if (this.active && this.tracer) {
      // Ensure the latest accumulated framebuffer is presented immediately before readback
      const prevPaused = this.tracer.pausePathTracing;
      this.tracer.pausePathTracing = false;
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
    this.equirectEnv?.dispose();
    this.equirectEnv = null;
    this.tracer?.dispose();
    this.tracer = null;
    this.active = false;
  }
}
