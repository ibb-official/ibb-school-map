import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { CAMPUS_LIGHTS } from "@/data/campusLights";
import { AtmosphereState, QualityTier, WeatherMode } from "@/data/types";
import { AtmosphereSkySystem } from "./atmosphereSky";
import { CampusNavigationController, computeAdaptiveFov } from "./cameraNavigation";
import { CampusSceneEngineHandle, EngineMountOptions } from "./engineTypes";
import { LightingAndWeatherSystem } from "./lightingAndWeather";
import type { PathTracerController, PathTracerStatus } from "./pathTracerController";
import { PBRMaterialSystem, UpgradedMaterialBuckets } from "./pbrMaterialSystem";
import { projectCampusPins, updateCompassHeading } from "./pinProjection";
import type { PostProcessingPipeline } from "./postProcessingPipeline";
import { computeSolarAtmosphere, formatTimeHours } from "./sunAstronomy";

const WEATHER_DARKEN_MAP: Record<WeatherMode, number> = {
  clear: 0.0,
  cloudy: 0.45,
  misty: 0.55,
  snowy: 0.62,
  rainy: 0.85,
};

const INITIAL_PT_STATUS: PathTracerStatus = {
  phase: "idle",
  samples: 0,
  targetSamples: 128,
};

function computeEnhancedDpr(quality: QualityTier): number {
  const raw = window.devicePixelRatio || 1;
  switch (quality) {
    case "low":
      return 1.0;
    case "medium":
      return Math.min(raw, 1.5);
    case "high":
      return Math.min(raw, 2.0);
    case "ultra":
      return Math.min(Math.max(raw, 2.0), 2.5);
  }
}

interface EmissiveBackup {
  material: THREE.MeshStandardMaterial;
  emissive: THREE.Color;
  emissiveIntensity: number;
}

/**
 * Enhanced ArchViz 3D Campus Engine (dynamically imported ONLY when enhancedMap === true):
 * - Full 24h Beijing astronomy sky + 5 weather modes + interior/campus night lights
 * - Strictly resource-gated PBR textures per quality tier (low/medium/high/ultra)
 * - Dynamically imports PostProcessingPipeline (postprocessing + n8ao) ONLY at high/ultra
 * - Lazily imports PathTracerController (three-gpu-pathtracer) ONLY when user enables Path Tracing
 * - Zero artificial device-based caps: all devices support full Ultra quality
 */
export async function mountEnhancedEngine(
  options: EngineMountOptions
): Promise<CampusSceneEngineHandle | null> {
  const {
    container,
    campus,
    places,
    quality,
    initialSelectedPlaceId,
    initialShowPins,
    initialCompactViewport,
    initialSnapshot,
    initialAtmosphere,
    pinElsRef,
    compassDialRef,
    virtualInputRef,
    onProgress,
    onLoaded,
    onSelectPlace,
    onWebGLError,
    onAtmosphereChange,
    onPathTracerStatusChange,
  } = options;

  const usePostPipeline = quality === "high" || quality === "ultra";

  let disposed = false;
  let selectedPlaceId = initialSelectedPlaceId;
  let hoveredPlaceId: string | null = null;
  let showPins = initialShowPins;
  let isCompactViewport = initialCompactViewport;
  let isSceneLoaded = false;

  let atmosphere: AtmosphereState = initialAtmosphere ?? {
    timeHours: 9.5,
    syncBeijingTime: true,
    weather: "clear",
    autoPlay: false,
    pathTracingActive: false,
  };
  let liveTimeHours = atmosphere.timeHours;

  onLoaded(false);
  onProgress(5);
  onPathTracerStatusChange?.(INITIAL_PT_STATUS);

  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({
      antialias: !usePostPipeline && quality !== "low",
      powerPreference: "high-performance",
      preserveDrawingBuffer: false,
    });
  } catch {
    onWebGLError("当前浏览器或设备无法创建 WebGL 上下文，请开启硬件加速后重试。");
    return null;
  }

  const width = Math.max(container.clientWidth, 320);
  const height = Math.max(container.clientHeight, 320);
  renderer.setPixelRatio(computeEnhancedDpr(quality));
  renderer.setSize(width, height);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = usePostPipeline
    ? THREE.NoToneMapping
    : THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type =
    quality === "low" ? THREE.PCFShadowMap : THREE.PCFSoftShadowMap;
  renderer.domElement.style.touchAction = "none";

  container.innerHTML = "";
  container.appendChild(renderer.domElement);

  const handleContextLost = (e: Event) => {
    e.preventDefault();
    if (!disposed) {
      onWebGLError("WebGL 图形上下文已释放，请点击重新加载三维地图。");
    }
  };
  renderer.domElement.addEventListener("webglcontextlost", handleContextLost);

  const scene = new THREE.Scene();
  const initSample = computeSolarAtmosphere(atmosphere.timeHours, atmosphere.weather);
  const fog = new THREE.FogExp2(initSample.fogColor.getHex(), initSample.fogDensity);
  scene.background = initSample.fogColor.clone();
  scene.fog = initSample.fogDensity > 0.00001 ? fog : null;

  const camera = new THREE.PerspectiveCamera(
    computeAdaptiveFov(width, height),
    width / height,
    0.5,
    1200
  );

  let pathTracer: PathTracerController | null = null;
  const nav = new CampusNavigationController(
    camera,
    renderer.domElement,
    campus,
    virtualInputRef,
    initialSnapshot,
    () => {
      if (pathTracer?.isActive()) {
        pathTracer.notifyCameraMoved();
      }
    }
  );

  const skySystem = new AtmosphereSkySystem(renderer);
  scene.add(skySystem.domeMesh);
  skySystem.update(
    initSample,
    WEATHER_DARKEN_MAP[atmosphere.weather],
    0,
    scene,
    true
  );

  const pbrSystem = new PBRMaterialSystem(renderer, quality);
  const campusLights = CAMPUS_LIGHTS[campus.id] ?? [];
  const lightingWeather = new LightingAndWeatherSystem(
    scene,
    campus.id,
    campus.defaultCameraTarget,
    campusLights,
    quality
  );
  lightingWeather.setQuality(quality, renderer.capabilities.maxTextureSize);

  const horizonGeo = new THREE.CircleGeometry(480, 48);
  horizonGeo.rotateX(-Math.PI / 2);
  const horizonDayBase = new THREE.Color(0xcfdbe6);
  const horizonMat = new THREE.MeshStandardMaterial({
    color: horizonDayBase
      .clone()
      .lerp(initSample.hemiGroundColor, initSample.nightFactor * 0.85)
      .lerp(initSample.fogColor, 0.62),
    roughness: 0.94,
    metalness: 0.0,
  });
  const horizonMesh = new THREE.Mesh(horizonGeo, horizonMat);
  horizonMesh.position.set(campus.defaultCameraTarget[0], -0.24, campus.defaultCameraTarget[2]);
  horizonMesh.receiveShadow = true;
  horizonMesh.name = "__horizon_apron";
  scene.add(horizonMesh);

  // Dynamically import postprocessing + N8AO ONLY at high / ultra quality!
  let postPipeline: PostProcessingPipeline | null = null;
  if (usePostPipeline) {
    const ppMod = await import("./postProcessingPipeline");
    if (disposed) {
      renderer.dispose();
      return null;
    }
    postPipeline = new ppMod.PostProcessingPipeline(
      renderer,
      scene,
      camera,
      width,
      height,
      quality
    );
  }

  const nodeMeshes = new Map<string, THREE.Mesh[]>();
  const selectableMeshes: THREE.Mesh[] = [];
  const validPlaceIds = new Set(places.map((p) => p.meshNodeName));

  // Fallback emissive highlight backup used only when postPipeline is not loaded (low/medium)
  const activeEmissiveBackups: EmissiveBackup[] = [];
  let loadedRoot: THREE.Object3D | null = null;
  let buckets: UpgradedMaterialBuckets | null = null;

  const restoreFallbackEmissive = () => {
    for (const rec of activeEmissiveBackups) {
      rec.material.emissive.copy(rec.emissive);
      rec.material.emissiveIntensity = rec.emissiveIntensity;
    }
    activeEmissiveBackups.length = 0;
  };

  const syncHighlights = () => {
    if (!isSceneLoaded) return;
    const isPT = Boolean(pathTracer?.isActive());
    if (postPipeline) {
      if (isPT) {
        postPipeline.setHighlightedObjects([], "none");
      } else if (selectedPlaceId) {
        postPipeline.setHighlightedObjects(nodeMeshes.get(selectedPlaceId) ?? [], "selected");
      } else if (hoveredPlaceId) {
        postPipeline.setHighlightedObjects(nodeMeshes.get(hoveredPlaceId) ?? [], "hovered");
      } else {
        postPipeline.setHighlightedObjects([], "none");
      }
      return;
    }

    restoreFallbackEmissive();
    if (isPT) return;
    const targetId = selectedPlaceId ?? hoveredPlaceId;
    if (!targetId) return;
    const meshes = nodeMeshes.get(targetId) ?? [];
    const seen = new Set<THREE.Material>();
    const tintHex = selectedPlaceId ? 0x2856e8 : 0x2d74da;
    const tintIntensity = selectedPlaceId ? 0.24 : 0.14;
    for (const m of meshes) {
      const mats = Array.isArray(m.material) ? m.material : [m.material];
      for (const mat of mats) {
        if (!mat || seen.has(mat)) continue;
        seen.add(mat);
        const std = mat as THREE.MeshStandardMaterial;
        if (std.isMeshStandardMaterial && std.emissive) {
          activeEmissiveBackups.push({
            material: std,
            emissive: std.emissive.clone(),
            emissiveIntensity: std.emissiveIntensity,
          });
          std.emissive.setHex(tintHex);
          std.emissiveIntensity = Math.max(std.emissiveIntensity, tintIntensity);
        }
      }
    }
  };

  let ptRequestSeq = 0;
  const syncPathTracerLifecycle = async () => {
    if (!isSceneLoaded || !loadedRoot) return;
    const seq = ++ptRequestSeq;

    if (atmosphere.pathTracingActive) {
      if (pathTracer?.isActive()) return;
      postPipeline?.setHighlightedObjects([], "none");
      restoreFallbackEmissive();
      lightingWeather.setPathTracingMode(true);
      const sample = computeSolarAtmosphere(atmosphere.timeHours, atmosphere.weather);
      lightingWeather.update(
        sample,
        atmosphere.timeHours,
        atmosphere.weather,
        buckets,
        0.016,
        0,
        true
      );

      if (!pathTracer) {
        const ptMod = await import("./pathTracerController");
        if (disposed || seq !== ptRequestSeq) return;
        pathTracer = new ptMod.PathTracerController();
      }

      const ok = await pathTracer.activate(
        renderer,
        scene,
        camera,
        loadedRoot,
        skySystem.domeMesh,
        sample,
        WEATHER_DARKEN_MAP[atmosphere.weather],
        (status) => {
          if (!disposed && seq === ptRequestSeq) {
            onPathTracerStatusChange?.(status);
          }
        },
        quality
      );

      if (disposed || seq !== ptRequestSeq) return;
      if (!ok) {
        lightingWeather.setPathTracingMode(false);
        renderer.toneMapping = usePostPipeline
          ? THREE.NoToneMapping
          : THREE.ACESFilmicToneMapping;
        onAtmosphereChange?.({ pathTracingActive: false });
      }
    } else if (pathTracer?.isActive()) {
      pathTracer.deactivate(scene);
      lightingWeather.setPathTracingMode(false);
      renderer.toneMapping = usePostPipeline
        ? THREE.NoToneMapping
        : THREE.ACESFilmicToneMapping;
      const sample = computeSolarAtmosphere(atmosphere.timeHours, atmosphere.weather);
      skySystem.update(sample, WEATHER_DARKEN_MAP[atmosphere.weather], 0, scene, true);
      onPathTracerStatusChange?.(INITIAL_PT_STATUS);
      syncHighlights();
    }
  };

  // Load Enhanced GLB Model
  const loader = new GLTFLoader();
  loader.load(
    campus.enhancedModelUrl,
    (gltf) => {
      if (disposed) return;
      loadedRoot = gltf.scene;
      buckets = pbrSystem.upgradeLoadedScene(loadedRoot);

      loadedRoot.traverse((obj) => {
        if (validPlaceIds.has(obj.name)) {
          const placeId = obj.name;
          const meshesForNode: THREE.Mesh[] = [];
          obj.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
              const mesh = child as THREE.Mesh;
              mesh.userData.placeId = placeId;
              selectableMeshes.push(mesh);
              meshesForNode.push(mesh);
            }
          });
          nodeMeshes.set(placeId, meshesForNode);
        }
      });

      scene.add(loadedRoot);
      isSceneLoaded = true;
      onProgress(100);
      onLoaded(true);
      syncHighlights();
      if (atmosphere.pathTracingActive) {
        void syncPathTracerLifecycle();
      }
    },
    (evt) => {
      if (disposed) return;
      if (evt.total > 0) {
        onProgress(Math.min(96, Math.round((evt.loaded / evt.total) * 100)));
      } else {
        onProgress(60);
      }
    },
    () => {
      if (!disposed) {
        onWebGLError("增强版三维校园模型加载失败，请检查网络后重试。");
      }
    }
  );

  // Multi-touch-safe pointer picking
  const raycaster = new THREE.Raycaster();
  const pointerNdc = new THREE.Vector2();
  const activePointers = new Set<number>();
  let primaryPointerId: number | null = null;
  let downX = 0;
  let downY = 0;
  let downTime = 0;
  let hadMultiTouch = false;

  const getHitPlaceId = (clientX: number, clientY: number): string | null => {
    if (selectableMeshes.length === 0) return null;
    const rect = renderer.domElement.getBoundingClientRect();
    pointerNdc.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    pointerNdc.y = -((clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointerNdc, camera);
    const hits = raycaster.intersectObjects(selectableMeshes, false);
    if (hits.length > 0) {
      const pid = hits[0].object.userData.placeId;
      return typeof pid === "string" ? pid : null;
    }
    return null;
  };

  const handlePointerDown = (ev: PointerEvent) => {
    activePointers.add(ev.pointerId);
    if (activePointers.size === 1) {
      primaryPointerId = ev.pointerId;
      downX = ev.clientX;
      downY = ev.clientY;
      downTime = performance.now();
      hadMultiTouch = false;
    } else {
      hadMultiTouch = true;
      primaryPointerId = null;
    }
  };

  const handlePointerMove = (ev: PointerEvent) => {
    if (ev.pointerType !== "mouse") return;
    if (pathTracer?.isActive()) {
      renderer.domElement.style.cursor = "grab";
      return;
    }
    const hit = getHitPlaceId(ev.clientX, ev.clientY);
    renderer.domElement.style.cursor = hit ? "pointer" : "grab";
    if (hit !== hoveredPlaceId) {
      hoveredPlaceId = hit;
      syncHighlights();
    }
  };

  const handlePointerUp = (ev: PointerEvent) => {
    activePointers.delete(ev.pointerId);
    const isCleanTap =
      !hadMultiTouch &&
      primaryPointerId === ev.pointerId &&
      activePointers.size === 0;
    if (activePointers.size === 0) {
      primaryPointerId = null;
      hadMultiTouch = false;
    }
    if (!isCleanTap) return;

    const dist = Math.hypot(ev.clientX - downX, ev.clientY - downY);
    const elapsed = performance.now() - downTime;
    const maxTapDist = ev.pointerType === "touch" ? 12 : 6;
    if (dist >= maxTapDist || (ev.pointerType === "touch" && elapsed > 380)) return;

    const hit = getHitPlaceId(ev.clientX, ev.clientY);
    if (hit) {
      onSelectPlace(hit);
    }
  };

  const handlePointerCancel = (ev: PointerEvent) => {
    activePointers.delete(ev.pointerId);
    if (activePointers.size === 0) {
      primaryPointerId = null;
      hadMultiTouch = false;
    }
  };

  renderer.domElement.addEventListener("pointerdown", handlePointerDown);
  renderer.domElement.addEventListener("pointermove", handlePointerMove);
  renderer.domElement.addEventListener("pointerup", handlePointerUp);
  renderer.domElement.addEventListener("pointercancel", handlePointerCancel);

  const ro = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const w = Math.max(entry.contentRect.width, 200);
      const h = Math.max(entry.contentRect.height, 200);
      camera.aspect = w / h;
      camera.fov = computeAdaptiveFov(w, h);
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      postPipeline?.setSize(w, h);
      if (pathTracer?.isActive()) {
        pathTracer.notifyCameraMoved();
      }
    }
  });
  ro.observe(container);

  const clock = new THREE.Clock();
  const snowTint = new THREE.Color(0xeef4fa);
  let elapsedSec = 0;
  let lastAutoPlaySyncMs = 0;
  let lastPtSamplesReported = -1;
  let rafId = 0;

  const animate = () => {
    if (disposed || document.hidden) {
      rafId = 0;
      return;
    }
    rafId = window.requestAnimationFrame(animate);
    const dt = Math.min(clock.getDelta(), 0.05);
    elapsedSec += dt;

    const isPT = Boolean(pathTracer?.isActive());

    if (atmosphere.autoPlay && !isPT) {
      liveTimeHours = (liveTimeHours + dt * 1.15) % 24;
      const nowMs = performance.now();
      if (nowMs - lastAutoPlaySyncMs > 120) {
        lastAutoPlaySyncMs = nowMs;
        onAtmosphereChange?.({ timeHours: liveTimeHours });
      }
    } else {
      liveTimeHours = atmosphere.timeHours;
    }

    nav.update(dt);

    const sample = computeSolarAtmosphere(liveTimeHours, atmosphere.weather);
    if (sample.fogDensity > 0.00001) {
      fog.color.copy(sample.fogColor);
      fog.density = sample.fogDensity;
      scene.fog = fog;
    } else {
      scene.fog = null;
    }
    if (!isPT && scene.background instanceof THREE.Color) {
      scene.background.copy(sample.fogColor);
    }
    horizonDayBase
      .setHex(0xcfdbe6)
      .lerp(sample.hemiGroundColor, sample.nightFactor * 0.85);
    horizonMat.color
      .copy(horizonDayBase)
      .lerp(sample.fogColor, 0.62)
      .lerp(snowTint, sample.snowCoverage * 0.82);
    horizonMat.roughness = THREE.MathUtils.lerp(0.95, 0.24, sample.wetness * 0.65);

    skySystem.domeMesh.position.copy(camera.position);
    if (!isPT) {
      skySystem.update(sample, WEATHER_DARKEN_MAP[atmosphere.weather], elapsedSec, scene, false);
    }

    pbrSystem.tick(
      elapsedSec,
      sample.wetness,
      sample.snowCoverage,
      sample.windStrength,
      sample.nightFactor,
      buckets?.waterMaterials ?? []
    );

    lightingWeather.update(
      sample,
      liveTimeHours,
      atmosphere.weather,
      buckets,
      dt,
      elapsedSec,
      isPT
    );

    if (isPT && pathTracer) {
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = sample.exposure * 0.96;
      const samples = pathTracer.renderFrame();
      if (samples !== lastPtSamplesReported) {
        lastPtSamplesReported = samples;
        onPathTracerStatusChange?.({
          phase: "rendering",
          samples,
          targetSamples: pathTracer.targetSamples,
        });
      }
    } else if (postPipeline) {
      renderer.toneMapping = THREE.NoToneMapping;
      renderer.toneMappingExposure = sample.exposure;
      postPipeline.updateFrame(sample.wetness, sample.nightFactor, sample.twilightGlow);
      postPipeline.render(dt);
    } else {
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = sample.exposure * 0.98;
      renderer.render(scene, camera);
    }

    updateCompassHeading(camera, nav.controls.target, compassDialRef.current);
    projectCampusPins(
      camera,
      renderer.domElement.clientWidth,
      renderer.domElement.clientHeight,
      places,
      pinElsRef.current,
      selectedPlaceId,
      showPins && !isPT,
      isCompactViewport
    );
  };

  const handleVisibilityChange = () => {
    if (disposed) return;
    if (document.hidden) {
      if (rafId) {
        window.cancelAnimationFrame(rafId);
        rafId = 0;
      }
    } else if (!rafId) {
      clock.getDelta();
      rafId = window.requestAnimationFrame(animate);
    }
  };
  document.addEventListener("visibilitychange", handleVisibilityChange);

  rafId = window.requestAnimationFrame(animate);

  return {
    flyTo: (pos, target) => nav.flyTo(pos, target),
    alignNorth: () => nav.alignNorth(),
    getCameraSnapshot: () => nav.getSnapshot(),
    setSelectedPlaceId: (id) => {
      selectedPlaceId = id;
      syncHighlights();
    },
    setShowPins: (show) => {
      showPins = show;
    },
    setIsCompactViewport: (compact) => {
      isCompactViewport = compact;
    },
    setAtmosphere: (next) => {
      const prev = atmosphere;
      atmosphere = next;
      if (!next.autoPlay) {
        liveTimeHours = next.timeHours;
      }
      if (next.pathTracingActive !== prev.pathTracingActive) {
        void syncPathTracerLifecycle();
      } else if (
        pathTracer?.isActive() &&
        (next.timeHours !== prev.timeHours || next.weather !== prev.weather)
      ) {
        const sample = computeSolarAtmosphere(next.timeHours, next.weather);
        lightingWeather.update(sample, next.timeHours, next.weather, buckets, 0.016, 0, true);
        pathTracer.syncEnvironmentAndLights(scene, sample, WEATHER_DARKEN_MAP[next.weather]);
      }
    },
    exportPhoto: () => {
      if (!pathTracer) return;
      const timeTag = formatTimeHours(atmosphere.timeHours).replace(":", "");
      pathTracer.downloadSnapshot(
        renderer,
        `bj166-${campus.id}-pathtraced-${timeTag}-${atmosphere.weather}.png`
      );
    },
    dispose: () => {
      disposed = true;
      ptRequestSeq++;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      if (rafId) window.cancelAnimationFrame(rafId);
      ro.disconnect();
      nav.dispose();
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      renderer.domElement.removeEventListener("pointermove", handlePointerMove);
      renderer.domElement.removeEventListener("pointerup", handlePointerUp);
      renderer.domElement.removeEventListener("pointercancel", handlePointerCancel);
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLost);

      restoreFallbackEmissive();
      pathTracer?.deactivate(scene);
      pathTracer?.dispose();
      postPipeline?.dispose();
      lightingWeather.dispose();
      skySystem.dispose();

      if (buckets) {
        for (const t of buckets.disposables.textures) t.dispose();
        for (const m of buckets.disposables.materials) m.dispose();
      }
      pbrSystem.dispose();

      const disposedTextures = new Set<THREE.Texture>();
      scene.traverse((obj) => {
        if ((obj as THREE.Mesh).isMesh) {
          const m = obj as THREE.Mesh;
          m.geometry.dispose();
          const mats = Array.isArray(m.material) ? m.material : [m.material];
          for (const mat of mats) {
            if (!mat) continue;
            const std = mat as THREE.MeshStandardMaterial;
            for (const tex of [std.map, std.normalMap, std.roughnessMap, std.metalnessMap, std.aoMap]) {
              if (tex && !disposedTextures.has(tex)) {
                disposedTextures.add(tex);
                tex.dispose();
              }
            }
            mat.dispose();
          }
        }
      });

      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    },
  };
}
