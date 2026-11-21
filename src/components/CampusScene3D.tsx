"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { MapControls } from "three/examples/jsm/controls/MapControls.js";
import { CAMPUS_LIGHTS } from "@/data/campusLights";
import { CATEGORY_COLORS } from "@/data/places";
import { AtmosphereState, CampusMeta, CampusPlace, WeatherMode } from "@/data/types";
import { AtmosphereSkySystem } from "@/scene/atmosphereSky";
import { LightingAndWeatherSystem } from "@/scene/lightingAndWeather";
import { PathTracerController, PathTracerStatus } from "@/scene/pathTracerController";
import { PBRMaterialSystem, UpgradedMaterialBuckets } from "@/scene/pbrMaterialSystem";
import { PostProcessingPipeline } from "@/scene/postProcessingPipeline";
import { computeSolarAtmosphere, formatTimeHours } from "@/scene/sunAstronomy";
import { AtmosphereDock } from "./AtmosphereDock";

interface CampusScene3DProps {
  campus: CampusMeta;
  places: CampusPlace[];
  selectedPlaceId: string | null;
  atmosphere: AtmosphereState;
  showPins: boolean;
  cameraFlightRequest: {
    id: number;
    cameraPos: [number, number, number];
    cameraTarget: [number, number, number];
  } | null;
  onSelectPlace: (placeId: string | null) => void;
  onAtmosphereChange: (patch: Partial<AtmosphereState>) => void;
  onSyncBeijingNow: () => void;
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

export function CampusScene3D({
  campus,
  places,
  selectedPlaceId,
  atmosphere,
  showPins,
  cameraFlightRequest,
  onSelectPlace,
  onAtmosphereChange,
  onSyncBeijingNow,
  onWebGLError,
}: CampusScene3DProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const pinElsRef = useRef<Map<string, HTMLButtonElement>>(new Map());
  const compassDialRef = useRef<HTMLDivElement | null>(null);

  const [loadProgress, setLoadProgress] = useState<number>(0);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);
  const [hoveredPlaceId, setHoveredPlaceId] = useState<string | null>(null);
  const [pathTracerStatus, setPathTracerStatus] = useState<PathTracerStatus>(INITIAL_PT_STATUS);

  // Refs synced to imperative Three.js loop without restarting WebGL context
  const onSelectRef = useRef(onSelectPlace);
  onSelectRef.current = onSelectPlace;

  const onAtmoChangeRef = useRef(onAtmosphereChange);
  onAtmoChangeRef.current = onAtmosphereChange;

  const onErrorRef = useRef(onWebGLError);
  onErrorRef.current = onWebGLError;

  const placesRef = useRef(places);
  placesRef.current = places;

  const hoveredRef = useRef(hoveredPlaceId);
  hoveredRef.current = hoveredPlaceId;

  const showPinsRef = useRef(showPins);
  showPinsRef.current = showPins;

  const atmosphereRef = useRef(atmosphere);
  atmosphereRef.current = atmosphere;

  const liveTimeHoursRef = useRef(atmosphere.timeHours);
  if (!atmosphere.autoPlay) {
    liveTimeHoursRef.current = atmosphere.timeHours;
  }

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

  // 1. Initialize WebGL2 ArchViz engine + PBR/CSM/Sky/PostProcessing/PathTracer whenever campus switches
  useEffect(() => {
    const container = hostRef.current;
    if (!container) return;

    let disposed = false;
    setIsLoaded(false);
    setLoadProgress(5);
    setHoveredPlaceId(null);
    setPathTracerStatus(INITIAL_PT_STATUS);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: false, // Handled cleanly by EffectComposer MSAA + SMAA (and jittered AA in PathTracer)
        powerPreference: "high-performance",
        preserveDrawingBuffer: true, // Enables crisp PNG export from GPU PathTracer
      });
    } catch {
      onErrorRef.current("当前浏览器或设备无法创建 WebGL 上下文，已切换为 2D 校园平面图。");
      return;
    }

    const width = Math.max(container.clientWidth, 320);
    const height = Math.max(container.clientHeight, 320);
    const initAtmo = atmosphereRef.current;
    const initDpr =
      initAtmo.quality === "smooth"
        ? Math.min(window.devicePixelRatio || 1, 1.5)
        : Math.min(window.devicePixelRatio || 1, 2);

    renderer.setPixelRatio(initDpr);
    renderer.setSize(width, height);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    // EffectComposer applies AgX tone mapping; switch to ACESFilmic only while PathTracer draws directly
    renderer.toneMapping = THREE.NoToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

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
    scene.fog = fog;

    const camera = new THREE.PerspectiveCamera(42, width / height, 0.45, 960);
    camera.position.set(...campus.defaultCameraPos);

    const controls = new MapControls(camera, renderer.domElement);
    controls.target.set(...campus.defaultCameraTarget);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = false;
    controls.minDistance = 3.2;
    controls.maxDistance = 260;
    controls.maxPolarAngle = Math.PI / 2 - 0.015;
    controls.update();

    // Subsystems: Atmospheric Sky + Dynamic PMREM IBL, PBR Material System, CSM & Night Lighting/Weather, Post-Processing, True PathTracer
    const skySystem = new AtmosphereSkySystem(renderer);
    scene.add(skySystem.domeMesh);
    skySystem.update(
      initSample,
      WEATHER_DARKEN_MAP[initAtmo.weather],
      0,
      scene,
      true
    );

    const pbrSystem = new PBRMaterialSystem(renderer);
    const campusLights = CAMPUS_LIGHTS[campus.id] ?? [];
    const lightingWeather = new LightingAndWeatherSystem(
      scene,
      camera,
      campus.defaultCameraTarget,
      campusLights,
      initAtmo.quality
    );

    // Subtle far-horizon ground apron that adapts seamlessly across sunset, night, rain & snow
    const horizonGeo = new THREE.CircleGeometry(480, 48);
    horizonGeo.rotateX(-Math.PI / 2);
    const horizonMat = new THREE.MeshStandardMaterial({
      color: initSample.hemiGroundColor.clone().lerp(initSample.fogColor, 0.52),
      roughness: 0.94,
      metalness: 0.0,
    });
    lightingWeather.setupMaterialForCSM(horizonMat);
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
      initAtmo.quality
    );
    const pathTracer = new PathTracerController();

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

    // Load GLB Model & upgrade all materials to CC0 PBR + Sobel Normals + Physical Glass + CSM
    const loader = new GLTFLoader();
    loader.load(
      campus.modelUrl,
      (gltf) => {
        if (disposed) return;
        const loadedRoot = gltf.scene;

        // 1. Upgrade materials (PBR, normal/ORM, foliage cards, physical glass, water, weather shaders)
        const buckets = pbrSystem.upgradeLoadedScene(loadedRoot);

        // 2. Chain Cascaded Shadow Maps onto all upgraded PBR/weather materials
        lightingWeather.setupMaterialsForCSM(loadedRoot);

        // 3. Index selectable building nodes without cloning materials (non-destructive OutlineEffect!)
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

    // Pointer picking (hover + click vs drag)
    const raycaster = new THREE.Raycaster();
    const pointerNdc = new THREE.Vector2();
    let downX = 0;
    let downY = 0;

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
      downX = ev.clientX;
      downY = ev.clientY;
    };

    const handlePointerMove = (ev: PointerEvent) => {
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
      const dist = Math.hypot(ev.clientX - downX, ev.clientY - downY);
      if (dist >= 6) return;
      const hit = getHitPlaceId(ev.clientX, ev.clientY);
      if (hit) {
        onSelectRef.current(hit);
      }
    };

    renderer.domElement.addEventListener("pointerdown", handlePointerDown);
    renderer.domElement.addEventListener("pointermove", handlePointerMove);
    renderer.domElement.addEventListener("pointerup", handlePointerUp);

    // ResizeObserver for crisp layout across split drawers & mobile screens
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.max(entry.contentRect.width, 200);
        const h = Math.max(entry.contentRect.height, 200);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
        postPipeline.setSize(w, h);
        lightingWeather.csm.updateFrustums();
        if (pathTracer.isActive()) {
          pathTracer.notifyCameraMoved();
        }
      }
    });
    ro.observe(container);

    // Render loop + direct DOM projection for floating 3D pins
    const clock = new THREE.Clock();
    const projVec = new THREE.Vector3();
    const snowTint = new THREE.Color(0xeef4fa);
    let elapsedSec = 0;
    let lastAutoPlaySyncMs = 0;
    let lastPtSamplesReported = -1;
    let rafId = 0;

    const animate = () => {
      if (disposed) return;
      rafId = window.requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.05);
      elapsedSec += dt;

      const handles = sceneHandlesRef.current;
      const atmo = atmosphereRef.current;
      const isPT = pathTracer.isActive();

      // Advance continuous timelapse cleanly at 60fps when autoPlay is enabled
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

      // Smooth fly-to transitions
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

      // Clamp target within calibrated ENU pan envelope so camera never gets lost
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

      // Compute physical Beijing solar & multi-weather atmosphere
      const currentHours = liveTimeHoursRef.current;
      const sample = computeSolarAtmosphere(currentHours, atmo.weather);

      // Update distance fog & far horizon ground apron
      fog.color.copy(sample.fogColor);
      fog.density = sample.fogDensity;
      if (!isPT && scene.background instanceof THREE.Color) {
        scene.background.copy(sample.fogColor);
      }
      horizonMat.color
        .copy(sample.hemiGroundColor)
        .lerp(sample.fogColor, 0.52)
        .lerp(snowTint, sample.snowCoverage * 0.82);
      horizonMat.roughness = THREE.MathUtils.lerp(0.95, 0.24, sample.wetness * 0.65);

      // Keep atmospheric sky dome centered on camera so horizon never clips
      skySystem.domeMesh.position.copy(camera.position);
      if (!isPT) {
        skySystem.update(sample, WEATHER_DARKEN_MAP[atmo.weather], elapsedSec, scene, false);
      }

      // Tick PBR weather uniforms (rain puddles, snow blanket, wind sway, animated water normals)
      pbrSystem.tick(
        elapsedSec,
        sample.wetness,
        sample.snowCoverage,
        sample.windStrength,
        sample.nightFactor,
        handles?.buckets?.waterMaterials ?? []
      );

      // Update Cascaded Shadow Maps, 7-bucket school interior lighting, floodlights, PointLight pool & particles
      lightingWeather.update(
        sample,
        currentHours,
        atmo.weather,
        camera,
        handles?.buckets ?? null,
        dt,
        elapsedSec,
        isPT
      );

      // Render Track B (True GPU Path Tracing) or Track A (Real-time N8AO + SSR/SSGI + Bloom + AgX + SMAA)
      if (isPT) {
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = sample.exposure * 0.92;
        const samples = pathTracer.renderFrame();
        if (samples !== lastPtSamplesReported) {
          lastPtSamplesReported = samples;
          setPathTracerStatus({
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

      // Live compass heading
      const compassDialEl = compassDialRef.current;
      if (compassDialEl) {
        const vdx = controls.target.x - camera.position.x;
        const vdz = controls.target.z - camera.position.z;
        if (Math.hypot(vdx, vdz) > 0.05) {
          const rotDeg = (Math.atan2(-vdx, -vdz) * 180) / Math.PI;
          compassDialEl.style.setProperty("--compass-rot", `${rotDeg.toFixed(1)}deg`);
        }
      }

      // Project floating HTML pins smoothly without React re-renders
      const cw = renderer.domElement.clientWidth;
      const ch = renderer.domElement.clientHeight;
      if (showPinsRef.current) {
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
      }
    };

    rafId = window.requestAnimationFrame(animate);

    return () => {
      disposed = true;
      window.cancelAnimationFrame(rafId);
      ro.disconnect();
      controls.removeEventListener("start", cancelFlight);
      controls.removeEventListener("change", handleControlsChange);
      controls.dispose();
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      renderer.domElement.removeEventListener("pointermove", handlePointerMove);
      renderer.domElement.removeEventListener("pointerup", handlePointerUp);
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
  }, [campus]);

  // 2. Dynamic quality tier updates (N8AO / SSR / SSGI / DPR / PointLight budget)
  useEffect(() => {
    const h = sceneHandlesRef.current;
    if (!h) return;
    h.postPipeline.setQuality(atmosphere.quality);
    h.lightingWeather.setQuality(atmosphere.quality);
    const targetDpr =
      atmosphere.quality === "smooth"
        ? Math.min(window.devicePixelRatio || 1, 1.5)
        : Math.min(window.devicePixelRatio || 1, 2);
    h.renderer.setPixelRatio(targetDpr);
    const w = Math.max(hostRef.current?.clientWidth ?? 320, 200);
    const hPx = Math.max(hostRef.current?.clientHeight ?? 320, 200);
    h.renderer.setSize(w, hPx);
    h.postPipeline.setSize(w, hPx);
  }, [atmosphere.quality]);

  // 3. True GPU Path Tracing activation / deactivation lifecycle
  useEffect(() => {
    const h = sceneHandlesRef.current;
    if (!h || !isLoaded || !h.loadedRoot) return;
    let cancelled = false;

    if (atmosphere.pathTracingActive) {
      h.postPipeline.setHighlightedObjects([], "none");
      h.lightingWeather.setPathTracingMode(true);
      const sample = computeSolarAtmosphere(atmosphereRef.current.timeHours, atmosphereRef.current.weather);
      // Force one immediate lighting update so interior emissives & pathTraceSunLight match before BVH sync
      h.lightingWeather.update(
        sample,
        atmosphereRef.current.timeHours,
        atmosphereRef.current.weather,
        h.camera,
        h.buckets,
        0.016,
        0,
        true
      );
      void h.pathTracer
        .activate(
          h.renderer,
          h.scene,
          h.camera,
          h.loadedRoot,
          h.skySystem.domeMesh,
          sample,
          (status) => {
            if (!cancelled) setPathTracerStatus(status);
          }
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
      setPathTracerStatus(INITIAL_PT_STATUS);
    }

    return () => {
      cancelled = true;
    };
  }, [atmosphere.pathTracingActive, isLoaded]);

  // 4. Sync Path Tracer environment & interior lights live if user adjusts time/weather during Path Tracing
  useEffect(() => {
    const h = sceneHandlesRef.current;
    if (!h || !h.pathTracer.isActive()) return;
    const sample = computeSolarAtmosphere(atmosphere.timeHours, atmosphere.weather);
    h.lightingWeather.update(
      sample,
      atmosphere.timeHours,
      atmosphere.weather,
      h.camera,
      h.buckets,
      0.016,
      0,
      true
    );
    h.pathTracer.syncEnvironmentAndLights(h.scene, sample);
  }, [atmosphere.timeHours, atmosphere.weather]);

  // 5. Non-destructive selection / hover OutlineEffect (preserves PBR materials, glass & night windows!)
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

  // 6. Trigger smooth fly-to camera transition on tour stop or building focus
  useEffect(() => {
    const h = sceneHandlesRef.current;
    if (!h || !cameraFlightRequest) return;
    h.flightGoal = {
      pos: new THREE.Vector3(...cameraFlightRequest.cameraPos),
      target: new THREE.Vector3(...cameraFlightRequest.cameraTarget),
    };
  }, [cameraFlightRequest]);

  const handleAlignNorth = () => {
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
  };

  const handleExportPhoto = () => {
    const h = sceneHandlesRef.current;
    if (!h) return;
    const timeTag = formatTimeHours(atmosphere.timeHours).replace(":", "");
    h.pathTracer.downloadSnapshot(
      h.renderer,
      `bj166-${campus.id}-pathtraced-${timeTag}-${atmosphere.weather}.png`
    );
  };

  return (
    <>
      <div
        ref={hostRef}
        className="scene-canvas-host"
        aria-label={`${campus.name} 三维交互画布`}
      />

      {/* Interactive live 3D directional compass (click to align camera due North) */}
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

      {/* Floating Atmospheric Lighting, 24h Solar Time, Weather & GPU Path Tracing Dock */}
      {isLoaded && (
        <AtmosphereDock
          state={atmosphere}
          pathTracerStatus={pathTracerStatus}
          shifted={Boolean(selectedPlaceId)}
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
            含 CC0 法线贴图、物理透视玻璃、浅层室内灯光与实时光追 ({loadProgress}%)
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${loadProgress}%` }} />
          </div>
        </div>
      )}

      <div className="controls-hint-pill">
        左键拖拽平移 · 右键/双指旋转 · 滚轮缩放 · 右上角调节时间/天气/真光追
      </div>
    </>
  );
}
