"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { MapControls } from "three/examples/jsm/controls/MapControls.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { CATEGORY_COLORS } from "@/data/places";
import { CampusMeta, CampusPlace, LightingPreset } from "@/data/types";

interface CampusScene3DProps {
  campus: CampusMeta;
  places: CampusPlace[];
  selectedPlaceId: string | null;
  lightingPreset: LightingPreset;
  showPins: boolean;
  cameraFlightRequest: {
    id: number;
    cameraPos: [number, number, number];
    cameraTarget: [number, number, number];
  } | null;
  onSelectPlace: (placeId: string | null) => void;
  onWebGLError: (message: string) => void;
}

interface ClonedMatRecord {
  material: THREE.MeshStandardMaterial;
  baseEmissive: THREE.Color;
  baseEmissiveIntensity: number;
}

const LIGHTING_CONFIGS: Record<
  LightingPreset,
  {
    bg: number;
    fogDensity: number;
    sunPos: [number, number, number];
    sunColor: number;
    sunIntensity: number;
    hemiSky: number;
    hemiGround: number;
    hemiIntensity: number;
    envIntensity: number;
    ledBoost: number;
  }
> = {
  morning: {
    bg: 0xdce9f7,
    fogDensity: 0.0014,
    sunPos: [95, 86, 62],
    sunColor: 0xfff5e4,
    sunIntensity: 2.15,
    hemiSky: 0xdbeafe,
    hemiGround: 0x9ca3af,
    hemiIntensity: 0.65,
    envIntensity: 0.72,
    ledBoost: 1.0,
  },
  noon: {
    bg: 0xd7e7f6,
    fogDensity: 0.0011,
    sunPos: [42, 132, 36],
    sunColor: 0xffffff,
    sunIntensity: 2.35,
    hemiSky: 0xe0f2fe,
    hemiGround: 0xa1a8b3,
    hemiIntensity: 0.75,
    envIntensity: 0.85,
    ledBoost: 0.85,
  },
  sunset: {
    bg: 0xe6d6cb,
    fogDensity: 0.0017,
    sunPos: [-96, 44, 72],
    sunColor: 0xffc689,
    sunIntensity: 2.05,
    hemiSky: 0xfde6d2,
    hemiGround: 0x6b7280,
    hemiIntensity: 0.58,
    envIntensity: 0.62,
    ledBoost: 1.65,
  },
};

export function CampusScene3D({
  campus,
  places,
  selectedPlaceId,
  lightingPreset,
  showPins,
  cameraFlightRequest,
  onSelectPlace,
  onWebGLError,
}: CampusScene3DProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const pinElsRef = useRef<Map<string, HTMLButtonElement>>(new Map());

  const [loadProgress, setLoadProgress] = useState<number>(0);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);
  const [hoveredPlaceId, setHoveredPlaceId] = useState<string | null>(null);

  // Refs synced to imperative Three.js loop without restarting WebGL context
  const onSelectRef = useRef(onSelectPlace);
  onSelectRef.current = onSelectPlace;

  const onErrorRef = useRef(onWebGLError);
  onErrorRef.current = onWebGLError;

  const placesRef = useRef(places);
  placesRef.current = places;

  const selectedRef = useRef(selectedPlaceId);
  selectedRef.current = selectedPlaceId;

  const hoveredRef = useRef(hoveredPlaceId);
  hoveredRef.current = hoveredPlaceId;

  const showPinsRef = useRef(showPins);
  showPinsRef.current = showPins;

  // Imperative scene handles for lighting updates, highlights & smooth flights
  const sceneHandlesRef = useRef<{
    scene: THREE.Scene;
    sunLight: THREE.DirectionalLight;
    hemiLight: THREE.HemisphereLight;
    camera: THREE.PerspectiveCamera;
    controls: MapControls;
    nodeMaterials: Map<string, ClonedMatRecord[]>;
    ledMaterials: ClonedMatRecord[];
    flightGoal: {
      pos: THREE.Vector3;
      target: THREE.Vector3;
    } | null;
  } | null>(null);

  // 1. Initialize Three.js WebGL2 engine + load GLB whenever campus changes
  useEffect(() => {
    const container = hostRef.current;
    if (!container) return;

    let disposed = false;
    setIsLoaded(false);
    setLoadProgress(5);
    setHoveredPlaceId(null);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        powerPreference: "high-performance",
      });
    } catch {
      onErrorRef.current("当前浏览器或设备无法创建 WebGL 上下文，已切换为 2D 校园平面图。");
      return;
    }

    const width = Math.max(container.clientWidth, 320);
    const height = Math.max(container.clientHeight, 320);

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
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
    const initialLight = LIGHTING_CONFIGS[lightingPreset];
    scene.background = new THREE.Color(initialLight.bg);
    scene.fog = new THREE.FogExp2(initialLight.bg, initialLight.fogDensity);
    scene.environmentIntensity = initialLight.envIntensity;

    const pmrem = new THREE.PMREMGenerator(renderer);
    const roomEnv = new RoomEnvironment();
    const envTarget = pmrem.fromScene(roomEnv, 0.04);
    scene.environment = envTarget.texture;
    roomEnv.dispose();

    const camera = new THREE.PerspectiveCamera(42, width / height, 0.5, 900);
    camera.position.set(...campus.defaultCameraPos);

    const controls = new MapControls(camera, renderer.domElement);
    controls.target.set(...campus.defaultCameraTarget);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = false;
    controls.minDistance = 12;
    controls.maxDistance = 260;
    controls.maxPolarAngle = Math.PI / 2 - 0.05;
    controls.update();

    const hemiLight = new THREE.HemisphereLight(
      initialLight.hemiSky,
      initialLight.hemiGround,
      initialLight.hemiIntensity
    );
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(
      initialLight.sunColor,
      initialLight.sunIntensity
    );
    sunLight.position.set(...initialLight.sunPos);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.set(2048, 2048);
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 360;
    sunLight.shadow.camera.left = -135;
    sunLight.shadow.camera.right = 135;
    sunLight.shadow.camera.top = 145;
    sunLight.shadow.camera.bottom = -145;
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);

    // Subtle far-horizon matte apron beneath model so campus never floats in void
    const horizonGeo = new THREE.CircleGeometry(460, 48);
    horizonGeo.rotateX(-Math.PI / 2);
    const horizonMat = new THREE.MeshStandardMaterial({
      color: 0xd1dae3,
      roughness: 0.96,
      metalness: 0,
    });
    const horizonMesh = new THREE.Mesh(horizonGeo, horizonMat);
    horizonMesh.position.set(campus.defaultCameraTarget[0], -0.24, campus.defaultCameraTarget[2]);
    horizonMesh.receiveShadow = true;
    horizonMesh.name = "__horizon_apron";
    scene.add(horizonMesh);

    const nodeMaterials = new Map<string, ClonedMatRecord[]>();
    const ledMaterials: ClonedMatRecord[] = [];
    const selectableMeshes: THREE.Mesh[] = [];
    const validPlaceIds = new Set(placesRef.current.map((p) => p.meshNodeName));

    sceneHandlesRef.current = {
      scene,
      sunLight,
      hemiLight,
      camera,
      controls,
      nodeMaterials,
      ledMaterials,
      flightGoal: null,
    };

    const cancelFlight = () => {
      if (sceneHandlesRef.current) {
        sceneHandlesRef.current.flightGoal = null;
      }
    };
    controls.addEventListener("start", cancelFlight);

    // Load GLB Model
    const loader = new GLTFLoader();
    let loadedRoot: THREE.Object3D | null = null;
    loader.load(
      campus.modelUrl,
      (gltf) => {
        if (disposed) return;
        loadedRoot = gltf.scene;

        loadedRoot.traverse((obj) => {
          // Top-level building/campus node names are attached either on obj or ancestor
          if (validPlaceIds.has(obj.name)) {
            const placeId = obj.name;
            const clonedForNode: ClonedMatRecord[] = [];
            obj.traverse((child) => {
              if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                mesh.userData.placeId = placeId;
                selectableMeshes.push(mesh);

                const cloneOne = (m: THREE.Material): THREE.Material => {
                  if ((m as THREE.MeshStandardMaterial).isMeshStandardMaterial) {
                    const cloned = (m as THREE.MeshStandardMaterial).clone();
                    const rec: ClonedMatRecord = {
                      material: cloned,
                      baseEmissive: cloned.emissive.clone(),
                      baseEmissiveIntensity: cloned.emissiveIntensity,
                    };
                    clonedForNode.push(rec);
                    if (cloned.name === "Mat_LED" || cloned.name === "Mat_StageLED") {
                      ledMaterials.push(rec);
                    }
                    return cloned;
                  }
                  return m;
                };

                if (Array.isArray(mesh.material)) {
                  mesh.material = mesh.material.map(cloneOne);
                } else if (mesh.material) {
                  mesh.material = cloneOne(mesh.material);
                }
              }
            });
            nodeMaterials.set(placeId, clonedForNode);
          } else if ((obj as THREE.Mesh).isMesh && !obj.userData.placeId) {
            const mesh = obj as THREE.Mesh;
            mesh.castShadow = true;
            mesh.receiveShadow = true;
          }
        });

        scene.add(loadedRoot);
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
      }
    });
    ro.observe(container);

    // Render loop + direct DOM projection for floating 3D pins
    const clock = new THREE.Clock();
    const projVec = new THREE.Vector3();
    let rafId = 0;

    const animate = () => {
      if (disposed) return;
      rafId = window.requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.05);

      const handles = sceneHandlesRef.current;
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
      renderer.render(scene, camera);

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
      controls.dispose();
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      renderer.domElement.removeEventListener("pointermove", handlePointerMove);
      renderer.domElement.removeEventListener("pointerup", handlePointerUp);
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLost);

      const disposedTextures = new Set<THREE.Texture>();
      scene.traverse((obj) => {
        if ((obj as THREE.Mesh).isMesh) {
          const m = obj as THREE.Mesh;
          m.geometry.dispose();
          const mats = Array.isArray(m.material) ? m.material : [m.material];
          for (const mat of mats) {
            if (!mat) continue;
            const std = mat as THREE.MeshStandardMaterial;
            if (std.map && !disposedTextures.has(std.map)) {
              disposedTextures.add(std.map);
              std.map.dispose();
            }
            mat.dispose();
          }
        }
      });

      envTarget.dispose();
      pmrem.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
      sceneHandlesRef.current = null;
    };
    // Intentionally re-initialize WebGL scene only when active campus switches
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campus]);

  // 2. Dynamic lighting preset updates without reloading the 3D model
  useEffect(() => {
    const h = sceneHandlesRef.current;
    if (!h) return;
    const cfg = LIGHTING_CONFIGS[lightingPreset];
    h.scene.background = new THREE.Color(cfg.bg);
    h.scene.fog = new THREE.FogExp2(cfg.bg, cfg.fogDensity);
    h.scene.environmentIntensity = cfg.envIntensity;
    h.sunLight.position.set(...cfg.sunPos);
    h.sunLight.color.setHex(cfg.sunColor);
    h.sunLight.intensity = cfg.sunIntensity;
    h.hemiLight.color.setHex(cfg.hemiSky);
    h.hemiLight.groundColor.setHex(cfg.hemiGround);
    h.hemiLight.intensity = cfg.hemiIntensity;

    for (const rec of h.ledMaterials) {
      rec.baseEmissiveIntensity = cfg.ledBoost;
      rec.material.emissiveIntensity = cfg.ledBoost;
    }
  }, [lightingPreset]);

  // 3. Apply per-node warm emissive tint when selected or hovered
  useEffect(() => {
    const h = sceneHandlesRef.current;
    if (!h) return;
    for (const [nodeId, records] of h.nodeMaterials.entries()) {
      const isSelected = nodeId === selectedPlaceId;
      const isHovered = nodeId === hoveredPlaceId;
      for (const rec of records) {
        if (isSelected) {
          rec.material.emissive.setHex(0xc26d18);
          rec.material.emissiveIntensity = 0.28;
        } else if (isHovered) {
          rec.material.emissive.setHex(0x1c6cae);
          rec.material.emissiveIntensity = 0.2;
        } else {
          rec.material.emissive.copy(rec.baseEmissive);
          rec.material.emissiveIntensity = rec.baseEmissiveIntensity;
        }
      }
    }
  }, [selectedPlaceId, hoveredPlaceId, isLoaded]);

  // 4. Trigger smooth fly-to camera transition on tour stop or building focus
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

      {showPins && isLoaded && (
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
            正在加载 {campus.shortName} 精细 3D 校园模型...
          </div>
          <div style={{ fontSize: "12px", opacity: 0.85, marginTop: "4px" }}>
            含砖墙材质、窗框凹进、门额文字牌匾 ({loadProgress}%)
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${loadProgress}%` }} />
          </div>
        </div>
      )}

      <div className="controls-hint-pill">
        左键拖拽平移 · 右键/双指旋转 · 滚轮缩放 · 点击建筑查看照片档案
      </div>
    </>
  );
}
