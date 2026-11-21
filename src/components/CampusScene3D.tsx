"use client";

import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { MapControls } from "three/examples/jsm/controls/MapControls.js";
import { CAMPUS_LIGHTS } from "@/data/campusLights";
import { CATEGORY_COLORS } from "@/data/places";
import {
  AtmosphereState,
  CampusMeta,
  CampusPlace,
  PlaceCategory,
  QualityTier,
  WeatherMode,
} from "@/data/types";
import { AtmosphereSkySystem } from "@/scene/atmosphereSky";
import { detectDeviceProfile, DeviceProfile } from "@/scene/deviceProfile";
import { LightingAndWeatherSystem } from "@/scene/lightingAndWeather";
import { PathTracerController, PathTracerStatus } from "@/scene/pathTracerController";
import { PBRMaterialSystem, UpgradedMaterialBuckets } from "@/scene/pbrMaterialSystem";
import { PostProcessingPipeline } from "@/scene/postProcessingPipeline";
import { computeSolarAtmosphere, formatTimeHours } from "@/scene/sunAstronomy";
import { AtmosphereDock } from "./AtmosphereDock";

export type TouchNavMode = "rotate" | "pan";

interface CampusScene3DProps {
  campus: CampusMeta;
  places: CampusPlace[];
  selectedPlaceId: string | null;
  atmosphere: AtmosphereState;
  userSelectedQuality: boolean;
  showPins: boolean;
  touchNavMode: TouchNavMode;
  isMobileShell: boolean;
  mobileCompassDialRef?: React.RefObject<HTMLDivElement | null>;
  alignNorthRef?: React.MutableRefObject<(() => void) | null>;
  exportPhotoRef?: React.MutableRefObject<(() => void) | null>;
  cameraFlightRequest: {
    id: number;
    cameraPos: [number, number, number];
    cameraTarget: [number, number, number];
  } | null;
  onSelectPlace: (placeId: string | null) => void;
  onAtmosphereChange: (patch: Partial<AtmosphereState>) => void;
  onSyncBeijingNow: () => void;
  onPathTracerStatusChange?: (status: PathTracerStatus) => void;
  onLoadedChange?: (loaded: boolean) => void;
  onWebGLError: (message: string) => void;
}

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

const PIN_CATEGORY_PRIORITY: Record<PlaceCategory, number> = {
  gate: 0,
  heritage: 1,
  sports: 2,
  corridor: 3,
  academic: 4,
};

const TOUCH_HINT_SESSION_KEY = "bj166-map-touch-hint-seen";

/**
 * Compensates vertical FOV on portrait viewports so the horizontal framing
 * stays wide enough to show the whole campus without clipping east/west wings.
 */
function computeAdaptiveFov(width: number, height: number): number {
  const aspect = width / Math.max(height, 1);
  if (aspect >= 0.85) return 42;
  const baseHalfTan = Math.tan(THREE.MathUtils.degToRad(21));
  const clampedAspect = Math.max(aspect, 0.5);
  const adaptedRad = 2 * Math.atan((baseHalfTan / clampedAspect) * 0.78);
  return THREE.MathUtils.clamp(THREE.MathUtils.radToDeg(adaptedRad), 42, 62);
}

function computeTargetDpr(quality: QualityTier, profile: DeviceProfile): number {
  const rawDpr = window.devicePixelRatio || 1;
  if (profile.isMobileTier) {
    if (quality === "cinematic") return Math.min(rawDpr, 1.75);
    return Math.min(rawDpr, profile.recommendedDprCap);
  }
  if (quality === "cinematic") return Math.min(Math.max(rawDpr, 1.75), 2.5);
  if (quality === "smooth") return Math.min(rawDpr, 1.25);
  return Math.min(rawDpr, 2);
}

function applyTouchControlsMode(controls: MapControls, mode: TouchNavMode): void {
  controls.touches =
    mode === "rotate"
      ? { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN }
      : { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE };
}

export function CampusScene3D({
  campus,
  places,
  selectedPlaceId,
  atmosphere,
  userSelectedQuality,
  showPins,
  touchNavMode,
  isMobileShell,
  mobileCompassDialRef,
  alignNorthRef,
  exportPhotoRef,
  cameraFlightRequest,
  onSelectPlace,
  onAtmosphereChange,
  onSyncBeijingNow,
  onPathTracerStatusChange,
  onLoadedChange,
  onWebGLError,
}: CampusScene3DProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const pinElsRef = useRef<Map<string, HTMLButtonElement>>(new Map());
  const compassDialRef = useRef<HTMLDivElement | null>(null);
  const profileRef = useRef<DeviceProfile | null>(null);
  const appliedQualityRef = useRef<QualityTier>(atmosphere.quality);

  const [loadProgress, setLoadProgress] = useState<number>(0);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);
  const [hoveredPlaceId, setHoveredPlaceId] = useState<string | null>(null);
  const [pathTracerStatus, setPathTracerStatus] = useState<PathTracerStatus>(INITIAL_PT_STATUS);
  const [showTouchHint, setShowTouchHint] = useState<boolean>(false);

  // Refs synced to imperative Three.js loop without restarting WebGL context
  const onSelectRef = useRef(onSelectPlace);
  onSelectRef.current = onSelectPlace;

  const onAtmoChangeRef = useRef(onAtmosphereChange);
  onAtmoChangeRef.current = onAtmosphereChange;

  const onErrorRef = useRef(onWebGLError);
  onErrorRef.current = onWebGLError;

  const onPtStatusRef = useRef(onPathTracerStatusChange);
  onPtStatusRef.current = onPathTracerStatusChange;

  const onLoadedChangeRef = useRef(onLoadedChange);
  onLoadedChangeRef.current = onLoadedChange;

  const placesRef = useRef(places);
  placesRef.current = places;

  const selectedPlaceIdRef = useRef(selectedPlaceId);
  selectedPlaceIdRef.current = selectedPlaceId;

  const hoveredRef = useRef(hoveredPlaceId);
  hoveredRef.current = hoveredPlaceId;

  const showPinsRef = useRef(showPins);
  showPinsRef.current = showPins;

  const atmosphereRef = useRef(atmosphere);
  atmosphereRef.current = atmosphere;

  const userSelectedQualityRef = useRef(userSelectedQuality);
  userSelectedQualityRef.current = userSelectedQuality;

  const touchNavModeRef = useRef<TouchNavMode>(touchNavMode);
  touchNavModeRef.current = touchNavMode;

  const isMobileShellRef = useRef<boolean>(isMobileShell);
  isMobileShellRef.current = isMobileShell;

  const mobileCompassRef = useRef(mobileCompassDialRef);
  mobileCompassRef.current = mobileCompassDialRef;

  const liveTimeHoursRef = useRef(atmosphere.timeHours);
  if (!atmosphere.autoPlay) {
    liveTimeHoursRef.current = atmosphere.timeHours;
  }

  const updatePathTracerStatus = useCallback((status: PathTracerStatus) => {
    setPathTracerStatus(status);
    onPtStatusRef.current?.(status);
  }, []);

  // Imperative handles for dynamic atmosphere, highlights, path tracing & camera flights
  const sceneHandlesRef = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    controls: MapControls;
    skySystem: AtmosphereSkySystem;
    pbrSystem: PBRMaterialSystem;
    lightingWeather: LightingAndWeatherSystem;
    postPipeline: PostProcessingPipeline;
    pathTracer: PathTracerController;
    horizonMat: THREE.MeshStandardMaterial;
    nodeMeshes: Map<string, THREE.Mesh[]>;
    loadedRoot: THREE.Object3D | null;
    buckets: UpgradedMaterialBuckets | null;
    flightGoal: {
      pos: THREE.Vector3;
      target: THREE.Vector3;
    } | null;
  } | null>(null);

  const handleAlignNorth = useCallback(() => {
    const h = sceneHandlesRef.current;
    if (!h) return;
    const { camera, controls } = h;
    const dx = camera.position.x - controls.target.x;
    const dz = camera.position.z - controls.target.z;
    const horizDist = Math.max(Math.hypot(dx, dz), 12);
    const camY = Math.max(camera.position.y, controls.target.y + 8);
    h.flightGoal = {
      pos: new THREE.Vector3(controls.target.x, camY, controls.target.z + horizDist),
      target: controls.target.clone(),
    };
  }, []);

  const handleExportPhoto = useCallback(() => {
    const h = sceneHandlesRef.current;
    if (!h) return;
    const atmo = atmosphereRef.current;
    const timeTag = formatTimeHours(atmo.timeHours).replace(":", "");
    h.pathTracer.downloadSnapshot(
      h.renderer,
      `bj166-${campus.id}-pathtraced-${timeTag}-${atmo.weather}.png`
    );
  }, [campus.id]);

  // Register imperative actions for mobile action rail / bottom sheet
  useEffect(() => {
    if (alignNorthRef) alignNorthRef.current = handleAlignNorth;
    if (exportPhotoRef) exportPhotoRef.current = handleExportPhoto;
    return () => {
      if (alignNorthRef) alignNorthRef.current = null;
      if (exportPhotoRef) exportPhotoRef.current = null;
    };
  }, [alignNorthRef, exportPhotoRef, handleAlignNorth, handleExportPhoto]);

  // Brief first-time touch gesture guide on mobile once 3D scene finishes loading
  useEffect(() => {
    if (!isLoaded || !isMobileShell) return;
    try {
      if (window.sessionStorage.getItem(TOUCH_HINT_SESSION_KEY)) return;
      window.sessionStorage.setItem(TOUCH_HINT_SESSION_KEY, "1");
    } catch {
      // Ignore storage access restrictions
    }
    setShowTouchHint(true);
    const timer = window.setTimeout(() => setShowTouchHint(false), 3800);
    return () => window.clearTimeout(timer);
  }, [isLoaded, isMobileShell]);

  // 1. Initialize WebGL2 ArchViz engine + PBR/World-Locked Shadows/Sky/PostProcessing/PathTracer
  useEffect(() => {
    const container = hostRef.current;
    if (!container) return;

    let disposed = false;
    setIsLoaded(false);
    onLoadedChangeRef.current?.(false);
    setLoadProgress(5);
    setHoveredPlaceId(null);
    updatePathTracerStatus(INITIAL_PT_STATUS);

    // Synchronously probe mobile capabilities BEFORE allocating WebGL/MSAA/shadow buffers
    const profile = detectDeviceProfile();
    profileRef.current = profile;

    const initAtmo = atmosphereRef.current;
    const effectiveInitQuality: QualityTier =
      profile.isMobileTier && !userSelectedQualityRef.current
        ? "smooth"
        : initAtmo.quality;
    appliedQualityRef.current = effectiveInitQuality;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: false, // Handled cleanly by EffectComposer hardware MSAA (and jittered AA in PathTracer)
        powerPreference: "high-performance",
        // Disable persistent drawing buffer on mobile Tile-GPUs for higher FPS & lower battery draw
        preserveDrawingBuffer: !profile.isMobileTier,
      });
    } catch {
      onErrorRef.current("当前浏览器或设备无法创建 WebGL 上下文，已切换为 2D 校园平面图。");
      return;
    }

    const width = Math.max(container.clientWidth, 320);
    const height = Math.max(container.clientHeight, 320);
    const initDpr = computeTargetDpr(effectiveInitQuality, profile);

    renderer.setPixelRatio(initDpr);
    renderer.setSize(width, height);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    // EffectComposer applies AgX tone mapping; switch to ACESFilmic only while PathTracer draws directly
    renderer.toneMapping = THREE.NoToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.domElement.style.touchAction = "none";

    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    const handleContextLost = (e: Event) => {
      e.preventDefault();
      if (!disposed) {
        onErrorRef.current("WebGL 图形上下文已释放，已切换为 2D 交互平面图。");
      }
    };
    renderer.domElement.addEventListener("webglcontextlost", handleContextLost);

    const scene = new THREE.Scene();
    const initSample = computeSolarAtmosphere(initAtmo.timeHours, initAtmo.weather);
    const fog = new THREE.FogExp2(initSample.fogColor.getHex(), initSample.fogDensity);
    scene.background = initSample.fogColor.clone();
    scene.fog = initSample.fogDensity > 0.00001 ? fog : null;

    const camera = new THREE.PerspectiveCamera(
      computeAdaptiveFov(width, height),
      width / height,
      0.5,
      1200
    );
    camera.position.set(...campus.defaultCameraPos);

    const controls = new MapControls(camera, renderer.domElement);
    controls.target.set(...campus.defaultCameraTarget);
    controls.enableDamping = true;
    controls.dampingFactor = profile.isCoarsePointer ? 0.1 : 0.08;
    controls.screenSpacePanning = false;
    controls.minDistance = 3.2;
    controls.maxDistance = 260;
    controls.minPolarAngle = profile.isCoarsePointer ? 0.14 : 0;
    controls.maxPolarAngle = profile.isCoarsePointer
      ? Math.PI / 2 - 0.04
      : Math.PI / 2 - 0.015;
    if (profile.isCoarsePointer || profile.isMobileTier) {
      controls.rotateSpeed = 0.72;
      controls.panSpeed = 0.85;
      controls.zoomSpeed = 0.9;
      applyTouchControlsMode(controls, touchNavModeRef.current);
    }
    controls.update();

    // Subsystems: Atmospheric Sky + Dynamic PMREM IBL, PBR Material System, World-Locked Shadows & Lights, Post-Processing, True PathTracer
    const skySystem = new AtmosphereSkySystem(renderer);
    scene.add(skySystem.domeMesh);
    skySystem.update(
      initSample,
      WEATHER_DARKEN_MAP[initAtmo.weather],
      0,
      scene,
      true
    );

    const pbrSystem = new PBRMaterialSystem(renderer, profile.maxAnisotropyCap);
    const campusLights = CAMPUS_LIGHTS[campus.id] ?? [];
    const lightingWeather = new LightingAndWeatherSystem(
      scene,
      campus.id,
      campus.defaultCameraTarget,
      campusLights,
      effectiveInitQuality
    );
    const maxShadowTex = Math.min(
      renderer.capabilities.maxTextureSize,
      profile.maxShadowMapSize
    );
    lightingWeather.setQuality(effectiveInitQuality, maxShadowTex);

    // Subtle far-horizon ground apron that adapts seamlessly across sunset, night, rain & snow
    const horizonGeo = new THREE.CircleGeometry(480, 48);
    horizonGeo.rotateX(-Math.PI / 2);
    const horizonMat = new THREE.MeshStandardMaterial({
      color: initSample.hemiGroundColor.clone().lerp(initSample.fogColor, 0.52),
      roughness: 0.94,
      metalness: 0.0,
    });
    const horizonMesh = new THREE.Mesh(horizonGeo, horizonMat);
    horizonMesh.position.set(campus.defaultCameraTarget[0], -0.24, campus.defaultCameraTarget[2]);
    horizonMesh.receiveShadow = true;
    horizonMesh.name = "__horizon_apron";
    scene.add(horizonMesh);

    const postPipeline = new PostProcessingPipeline(
      renderer,
      scene,
      camera,
      width,
      height,
      effectiveInitQuality,
      profile.isMobileTier
    );
    const pathTracer = new PathTracerController();
    pathTracer.targetSamples = profile.isMobileTier
      ? 64
      : effectiveInitQuality === "cinematic"
        ? 256
        : 128;

    const nodeMeshes = new Map<string, THREE.Mesh[]>();
    const selectableMeshes: THREE.Mesh[] = [];
    const validPlaceIds = new Set(placesRef.current.map((p) => p.meshNodeName));

    sceneHandlesRef.current = {
      renderer,
      scene,
      camera,
      controls,
      skySystem,
      pbrSystem,
      lightingWeather,
      postPipeline,
      pathTracer,
      horizonMat,
      nodeMeshes,
      loadedRoot: null,
      buckets: null,
      flightGoal: null,
    };

    const cancelFlight = () => {
      if (sceneHandlesRef.current) {
        sceneHandlesRef.current.flightGoal = null;
      }
    };
    const handleControlsChange = () => {
      if (pathTracer.isActive()) {
        pathTracer.notifyCameraMoved();
      }
    };
    controls.addEventListener("start", cancelFlight);
    controls.addEventListener("change", handleControlsChange);

    // Load GLB Model & upgrade all materials to CC0 PBR + Sobel Normals + Physical Glass
    const loader = new GLTFLoader();
    loader.load(
      campus.modelUrl,
      (gltf) => {
        if (disposed) return;
        const loadedRoot = gltf.scene;

        // 1. Upgrade materials (PBR, normal/ORM, foliage cards, physical glass, water, weather shaders)
        const buckets = pbrSystem.upgradeLoadedScene(loadedRoot);

        // 2. Index selectable building nodes without cloning materials (non-destructive OutlineEffect!)
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
        if (sceneHandlesRef.current) {
          sceneHandlesRef.current.loadedRoot = loadedRoot;
          sceneHandlesRef.current.buckets = buckets;
        }
        setLoadProgress(100);
        setIsLoaded(true);
        onLoadedChangeRef.current?.(true);
      },
      (evt) => {
        if (disposed) return;
        if (evt.total > 0) {
          setLoadProgress(Math.min(96, Math.round((evt.loaded / evt.total) * 100)));
        } else {
          setLoadProgress((prev) => Math.min(88, prev + 8));
        }
      },
      () => {
        if (!disposed) {
          onErrorRef.current("三维模型加载受阻，已为您切换为交互式 2D 校园平面图。");
        }
      }
    );

    // Multi-touch-safe pointer picking (ignores pinch/rotate; skips expensive raycasts on touch move)
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
      if (pathTracer.isActive()) {
        renderer.domElement.style.cursor = "grab";
        return;
      }
      const hit = getHitPlaceId(ev.clientX, ev.clientY);
      renderer.domElement.style.cursor = hit ? "pointer" : "grab";
      if (hit !== hoveredRef.current) {
        setHoveredPlaceId(hit);
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
        onSelectRef.current(hit);
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

    // ResizeObserver for crisp HiDPI layout & portrait FOV compensation across rotations & drawers
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.max(entry.contentRect.width, 200);
        const h = Math.max(entry.contentRect.height, 200);
        camera.aspect = w / h;
        camera.fov = computeAdaptiveFov(w, h);
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
        postPipeline.setSize(w, h);
        if (pathTracer.isActive()) {
          pathTracer.notifyCameraMoved();
        }
      }
    });
    ro.observe(container);

    // Render loop + direct DOM projection with mobile screen-space collision culling
    const clock = new THREE.Clock();
    const projVec = new THREE.Vector3();
    const snowTint = new THREE.Color(0xeef4fa);
    let elapsedSec = 0;
    let lastAutoPlaySyncMs = 0;
    let lastPtSamplesReported = -1;
    let rafId = 0;

    const acceptedPinBoxes: { x0: number; y0: number; x1: number; y1: number }[] = [];

    const animate = () => {
      if (disposed || document.hidden) {
        rafId = 0;
        return;
      }
      rafId = window.requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.05);
      elapsedSec += dt;

      const handles = sceneHandlesRef.current;
      const atmo = atmosphereRef.current;
      const isPT = pathTracer.isActive();

      if (atmo.autoPlay && !isPT) {
        liveTimeHoursRef.current = (liveTimeHoursRef.current + dt * 1.15) % 24;
        const nowMs = performance.now();
        if (nowMs - lastAutoPlaySyncMs > 120) {
          lastAutoPlaySyncMs = nowMs;
          onAtmoChangeRef.current({ timeHours: liveTimeHoursRef.current });
        }
      } else {
        liveTimeHoursRef.current = atmo.timeHours;
      }

      if (handles?.flightGoal) {
        const alpha = 1 - Math.exp(-5.4 * dt);
        camera.position.lerp(handles.flightGoal.pos, alpha);
        controls.target.lerp(handles.flightGoal.target, alpha);
        if (
          camera.position.distanceTo(handles.flightGoal.pos) < 0.08 &&
          controls.target.distanceTo(handles.flightGoal.target) < 0.08
        ) {
          camera.position.copy(handles.flightGoal.pos);
          controls.target.copy(handles.flightGoal.target);
          handles.flightGoal = null;
        }
        if (isPT) {
          pathTracer.notifyCameraMoved();
        }
      }

      controls.target.x = THREE.MathUtils.clamp(
        controls.target.x,
        campus.panBounds.minX,
        campus.panBounds.maxX
      );
      controls.target.z = THREE.MathUtils.clamp(
        controls.target.z,
        campus.panBounds.minZ,
        campus.panBounds.maxZ
      );
      controls.target.y = THREE.MathUtils.clamp(controls.target.y, -1, 24);
      controls.update();

      const currentHours = liveTimeHoursRef.current;
      const sample = computeSolarAtmosphere(currentHours, atmo.weather);

      // Update weather fog (zero distance fog in clear weather so compact campus stays sharp!)
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
      horizonMat.color
        .copy(sample.hemiGroundColor)
        .lerp(sample.fogColor, 0.52)
        .lerp(snowTint, sample.snowCoverage * 0.82);
      horizonMat.roughness = THREE.MathUtils.lerp(0.95, 0.24, sample.wetness * 0.65);

      skySystem.domeMesh.position.copy(camera.position);
      if (!isPT) {
        skySystem.update(sample, WEATHER_DARKEN_MAP[atmo.weather], elapsedSec, scene, false);
      }

      // Tick PBR weather uniforms (rain puddles, snow blanket, animated water normals)
      pbrSystem.tick(
        elapsedSec,
        sample.wetness,
        sample.snowCoverage,
        sample.windStrength,
        sample.nightFactor,
        handles?.buckets?.waterMaterials ?? []
      );

      // Update world-locked shadows, 7-bucket school interior lighting, fixed campus lamps & particles
      lightingWeather.update(
        sample,
        currentHours,
        atmo.weather,
        handles?.buckets ?? null,
        dt,
        elapsedSec,
        isPT
      );

      if (isPT) {
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = sample.exposure * 0.92;
        const samples = pathTracer.renderFrame();
        if (samples !== lastPtSamplesReported) {
          lastPtSamplesReported = samples;
          updatePathTracerStatus({
            phase: "rendering",
            samples,
            targetSamples: pathTracer.targetSamples,
          });
        }
      } else {
        renderer.toneMapping = THREE.NoToneMapping;
        postPipeline.updateFrame(sample.wetness, sample.nightFactor, sample.twilightGlow);
        postPipeline.render(dt);
      }

      // Live compass heading (syncs both desktop & mobile dials with zero React re-renders)
      const vdx = controls.target.x - camera.position.x;
      const vdz = controls.target.z - camera.position.z;
      if (Math.hypot(vdx, vdz) > 0.05) {
        const rotCss = `${((Math.atan2(-vdx, -vdz) * 180) / Math.PI).toFixed(1)}deg`;
        if (compassDialRef.current) {
          compassDialRef.current.style.setProperty("--compass-rot", rotCss);
        }
        const mDial = mobileCompassRef.current?.current;
        if (mDial) {
          mDial.style.setProperty("--compass-rot", rotCss);
        }
      }

      // Project floating HTML pins smoothly without React re-renders
      const cw = renderer.domElement.clientWidth;
      const ch = renderer.domElement.clientHeight;
      if (showPinsRef.current) {
        const cullOverlap = isMobileShellRef.current || cw <= 860;
        const currentSelectedId = selectedPlaceIdRef.current;

        if (!cullOverlap) {
          for (const place of placesRef.current) {
            const el = pinElsRef.current.get(place.id);
            if (!el) continue;
            projVec.set(place.position[0], place.position[1], place.position[2]);
            projVec.project(camera);
            if (projVec.z > 1 || projVec.z < -1) {
              el.style.opacity = "0";
              el.style.pointerEvents = "none";
              continue;
            }
            const sx = (projVec.x * 0.5 + 0.5) * cw;
            const sy = (-projVec.y * 0.5 + 0.5) * ch;
            if (sx < -40 || sx > cw + 40 || sy < -40 || sy > ch + 40) {
              el.style.opacity = "0";
              el.style.pointerEvents = "none";
              continue;
            }
            el.style.opacity = "1";
            el.style.pointerEvents = "auto";
            el.style.left = `${sx.toFixed(1)}px`;
            el.style.top = `${sy.toFixed(1)}px`;
          }
        } else {
          // Mobile screen-space collision culling: keep selected & key landmarks visible,
          // automatically reveal secondary labels as the user pinches closer!
          acceptedPinBoxes.length = 0;
          const safeRightEdge = cw - 62;
          const safeBottomEdge = ch - 76;
          const orderedPlaces = [...placesRef.current].sort((a, b) => {
            if (a.id === currentSelectedId) return -1;
            if (b.id === currentSelectedId) return 1;
            return PIN_CATEGORY_PRIORITY[a.category] - PIN_CATEGORY_PRIORITY[b.category];
          });

          for (const place of orderedPlaces) {
            const el = pinElsRef.current.get(place.id);
            if (!el) continue;
            projVec.set(place.position[0], place.position[1], place.position[2]);
            projVec.project(camera);
            if (projVec.z > 1 || projVec.z < -1) {
              el.style.opacity = "0";
              el.style.pointerEvents = "none";
              continue;
            }
            const sx = (projVec.x * 0.5 + 0.5) * cw;
            const sy = (-projVec.y * 0.5 + 0.5) * ch;
            const isSel = place.id === currentSelectedId;

            const estW = Math.min(126, 28 + place.shortName.length * 11.5) + 10;
            const estH = 34;
            const x0 = sx - estW * 0.5;
            const x1 = sx + estW * 0.5;
            const y0 = sy - estH;
            const y1 = sy + 4;

            if (
              isSel
                ? sx < 14 || sx > cw - 14 || sy < 26 || sy > ch - 24
                : x0 < 8 || x1 > safeRightEdge || y0 < 10 || y1 > safeBottomEdge
            ) {
              el.style.opacity = "0";
              el.style.pointerEvents = "none";
              continue;
            }

            let collides = false;
            if (!isSel) {
              for (let i = 0; i < acceptedPinBoxes.length; i++) {
                const b = acceptedPinBoxes[i];
                if (x0 < b.x1 && x1 > b.x0 && y0 < b.y1 && y1 > b.y0) {
                  collides = true;
                  break;
                }
              }
            }

            if (collides) {
              el.style.opacity = "0";
              el.style.pointerEvents = "none";
              continue;
            }

            acceptedPinBoxes.push({ x0, y0, x1, y1 });
            el.style.opacity = "1";
            el.style.pointerEvents = "auto";
            el.style.left = `${sx.toFixed(1)}px`;
            el.style.top = `${sy.toFixed(1)}px`;
          }
        }
      }
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

    return () => {
      disposed = true;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      if (rafId) window.cancelAnimationFrame(rafId);
      ro.disconnect();
      controls.removeEventListener("start", cancelFlight);
      controls.removeEventListener("change", handleControlsChange);
      controls.dispose();
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      renderer.domElement.removeEventListener("pointermove", handlePointerMove);
      renderer.domElement.removeEventListener("pointerup", handlePointerUp);
      renderer.domElement.removeEventListener("pointercancel", handlePointerCancel);
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLost);

      pathTracer.deactivate(scene);
      pathTracer.dispose();
      postPipeline.dispose();
      lightingWeather.dispose();
      skySystem.dispose();

      const buckets = sceneHandlesRef.current?.buckets;
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
      sceneHandlesRef.current = null;
    };
  }, [campus, updatePathTracerStatus]);

  // 2. Live touch navigation mode toggle (single-finger Rotate vs Pan) without WebGL reload
  useEffect(() => {
    const h = sceneHandlesRef.current;
    const profile = profileRef.current;
    if (!h || !profile) return;
    if (profile.isCoarsePointer || profile.isMobileTier) {
      applyTouchControlsMode(h.controls, touchNavMode);
    }
  }, [touchNavMode]);

  // 3. Dynamic quality tier updates (Ultra 4K shadows, supersampled HiDPI, full-res N8AO, CAS sharpening)
  useEffect(() => {
    const h = sceneHandlesRef.current;
    const profile = profileRef.current;
    if (!h || !profile) return;
    if (appliedQualityRef.current === atmosphere.quality) return;
    appliedQualityRef.current = atmosphere.quality;

    h.postPipeline.setQuality(atmosphere.quality);
    const maxShadowTex = Math.min(
      h.renderer.capabilities.maxTextureSize,
      profile.maxShadowMapSize
    );
    h.lightingWeather.setQuality(atmosphere.quality, maxShadowTex);
    h.pathTracer.targetSamples = profile.isMobileTier
      ? 64
      : atmosphere.quality === "cinematic"
        ? 256
        : 128;

    const targetDpr = computeTargetDpr(atmosphere.quality, profile);
    h.renderer.setPixelRatio(targetDpr);
    const w = Math.max(hostRef.current?.clientWidth ?? 320, 200);
    const hPx = Math.max(hostRef.current?.clientHeight ?? 320, 200);
    h.renderer.setSize(w, hPx);
    h.postPipeline.setSize(w, hPx);
  }, [atmosphere.quality]);

  // 4. True GPU Path Tracing activation / deactivation lifecycle (mobile-safe parameters when on phone)
  useEffect(() => {
    const h = sceneHandlesRef.current;
    if (!h || !isLoaded || !h.loadedRoot) return;
    let cancelled = false;

    if (atmosphere.pathTracingActive) {
      h.postPipeline.setHighlightedObjects([], "none");
      h.lightingWeather.setPathTracingMode(true);
      const sample = computeSolarAtmosphere(atmosphereRef.current.timeHours, atmosphereRef.current.weather);
      h.lightingWeather.update(
        sample,
        atmosphereRef.current.timeHours,
        atmosphereRef.current.weather,
        h.buckets,
        0.016,
        0,
        true
      );
      const mobileSafe = Boolean(profileRef.current?.isMobileTier);
      void h.pathTracer
        .activate(
          h.renderer,
          h.scene,
          h.camera,
          h.loadedRoot,
          h.skySystem.domeMesh,
          sample,
          (status) => {
            if (!cancelled) updatePathTracerStatus(status);
          },
          mobileSafe
        )
        .then((ok) => {
          if (cancelled) return;
          if (!ok) {
            h.lightingWeather.setPathTracingMode(false);
            h.renderer.toneMapping = THREE.NoToneMapping;
            onAtmoChangeRef.current({ pathTracingActive: false });
          }
        });
    } else if (h.pathTracer.isActive()) {
      h.pathTracer.deactivate(h.scene);
      h.lightingWeather.setPathTracingMode(false);
      h.renderer.toneMapping = THREE.NoToneMapping;
      const sample = computeSolarAtmosphere(atmosphereRef.current.timeHours, atmosphereRef.current.weather);
      h.skySystem.update(sample, WEATHER_DARKEN_MAP[atmosphereRef.current.weather], 0, h.scene, true);
      updatePathTracerStatus(INITIAL_PT_STATUS);
    }

    return () => {
      cancelled = true;
    };
  }, [atmosphere.pathTracingActive, isLoaded, updatePathTracerStatus]);

  // 5. Sync Path Tracer environment & interior lights live if user adjusts time/weather during Path Tracing
  useEffect(() => {
    const h = sceneHandlesRef.current;
    if (!h || !h.pathTracer.isActive()) return;
    const sample = computeSolarAtmosphere(atmosphere.timeHours, atmosphere.weather);
    h.lightingWeather.update(
      sample,
      atmosphere.timeHours,
      atmosphere.weather,
      h.buckets,
      0.016,
      0,
      true
    );
    h.pathTracer.syncEnvironmentAndLights(h.scene, sample);
  }, [atmosphere.timeHours, atmosphere.weather]);

  // 6. Non-destructive selection / hover OutlineEffect (preserves PBR materials, glass & night windows!)
  useEffect(() => {
    const h = sceneHandlesRef.current;
    if (!h || !isLoaded) return;
    if (atmosphere.pathTracingActive) {
      h.postPipeline.setHighlightedObjects([], "none");
      return;
    }
    if (selectedPlaceId) {
      h.postPipeline.setHighlightedObjects(h.nodeMeshes.get(selectedPlaceId) ?? [], "selected");
    } else if (hoveredPlaceId) {
      h.postPipeline.setHighlightedObjects(h.nodeMeshes.get(hoveredPlaceId) ?? [], "hovered");
    } else {
      h.postPipeline.setHighlightedObjects([], "none");
    }
  }, [selectedPlaceId, hoveredPlaceId, isLoaded, atmosphere.pathTracingActive]);

  // 7. Trigger smooth fly-to camera transition on tour stop or building focus
  useEffect(() => {
    const h = sceneHandlesRef.current;
    if (!h || !cameraFlightRequest) return;
    h.flightGoal = {
      pos: new THREE.Vector3(...cameraFlightRequest.cameraPos),
      target: new THREE.Vector3(...cameraFlightRequest.cameraTarget),
    };
  }, [cameraFlightRequest]);

  return (
    <>
      <div
        ref={hostRef}
        className="scene-canvas-host"
        aria-label={`${campus.name} 三维交互画布`}
      />

      {/* Desktop interactive live 3D directional compass (mobile uses compact compass in action rail) */}
      <button
        type="button"
        className={`compass-3d-widget${selectedPlaceId ? " compass-3d-widget-shifted" : ""}`}
        onClick={handleAlignNorth}
        title="实时方向指北针（红针指北，点击一键回正为上北下南）"
        aria-label="方向指北针：点击回正为上北下南"
      >
        <div ref={compassDialRef} className="compass-dial">
          <span className="compass-cardinal compass-cardinal-n">北</span>
          <span className="compass-cardinal compass-cardinal-e">东</span>
          <span className="compass-cardinal compass-cardinal-s">南</span>
          <span className="compass-cardinal compass-cardinal-w">西</span>
          <svg
            viewBox="0 0 40 40"
            width="40"
            height="40"
            className="compass-needle-svg"
            aria-hidden="true"
          >
            <circle cx="20" cy="20" r="14" fill="none" stroke="rgba(11,63,112,0.16)" strokeWidth="1" />
            <polygon points="20,7 16.4,20 20,18.2 23.6,20" fill="#c9332b" />
            <polygon points="20,33 16.4,20 20,21.8 23.6,20" fill="#94a3b8" />
            <circle cx="20" cy="20" r="2.1" fill="#0b3f70" />
          </svg>
        </div>
        <span className="compass-sublabel">回正北向</span>
      </button>

      {/* Desktop Floating Atmospheric Dock (mobile opens AtmosphereDock inside bottom sheet) */}
      {isLoaded && !isMobileShell && (
        <AtmosphereDock
          state={atmosphere}
          pathTracerStatus={pathTracerStatus}
          shifted={Boolean(selectedPlaceId)}
          variant="floating"
          onChange={onAtmosphereChange}
          onSyncBeijingNow={onSyncBeijingNow}
          onExportPhoto={handleExportPhoto}
        />
      )}

      {showPins && isLoaded && !atmosphere.pathTracingActive && (
        <div className="pins-overlay-layer" aria-label="三维空间点位标签层">
          {places.map((place) => {
            const selected = place.id === selectedPlaceId;
            return (
              <button
                key={place.id}
                ref={(el) => {
                  if (el) {
                    pinElsRef.current.set(place.id, el);
                  } else {
                    pinElsRef.current.delete(place.id);
                  }
                }}
                type="button"
                className={`pin-3d-btn ${selected ? "pin-3d-btn-selected" : ""}`}
                onClick={() => onSelectPlace(place.id)}
                title={place.name}
              >
                <span
                  className="pin-dot"
                  style={{ backgroundColor: CATEGORY_COLORS[place.category] }}
                />
                <span>{place.shortName}</span>
              </button>
            );
          })}
        </div>
      )}

      {!isLoaded && (
        <div className="scene-status-hud" role="status" aria-live="polite">
          <div style={{ fontSize: "14px", fontWeight: 700 }}>
            正在加载 {campus.shortName} 写实 PBR 3D 校园模型...
          </div>
          <div style={{ fontSize: "12px", opacity: 0.85, marginTop: "4px" }}>
            含 CC0 法线贴图、物理透视玻璃与昼夜实时光影 ({loadProgress}%)
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${loadProgress}%` }} />
          </div>
        </div>
      )}

      {showTouchHint && isMobileShell && (
        <button
          type="button"
          className="mobile-touch-hint-toast"
          onClick={() => setShowTouchHint(false)}
          aria-label="关闭触屏手势提示"
        >
          {touchNavMode === "rotate"
            ? "单指旋转视角 · 双指缩放平移 · 点击建筑看详情"
            : "单指平移地图 · 双指缩放旋转 · 点击建筑看详情"}
        </button>
      )}

      <div className="controls-hint-pill">
        左键拖拽平移 · 右键/双指旋转 · 滚轮缩放 · 右上角调节时间/天气/真光追
      </div>
    </>
  );
}
