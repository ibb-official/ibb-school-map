import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { QualityTier } from "@/data/types";
import { CampusNavigationController, computeAdaptiveFov } from "./cameraNavigation";
import { CampusSceneEngineHandle, EngineMountOptions } from "./engineTypes";
import { projectCampusPins, updateCompassHeading } from "./pinProjection";

interface ClonedMatRecord {
  material: THREE.MeshStandardMaterial;
  baseEmissive: THREE.Color;
  baseEmissiveIntensity: number;
}

function computeClassicDpr(quality: QualityTier): number {
  const raw = window.devicePixelRatio || 1;
  switch (quality) {
    case "low":
      return 1.0;
    case "medium":
      return Math.min(raw, 1.5);
    case "high":
      return Math.min(raw, 2.0);
    case "ultra":
      return Math.min(Math.max(raw, 2.0), 3.0);
  }
}

function computeClassicShadowRes(quality: QualityTier, maxTexSize: number): number {
  if (quality === "low") return 0;
  if (quality === "medium") return Math.min(1024, maxTexSize);
  if (quality === "high") return Math.min(2048, maxTexSize);
  return Math.min(4096, maxTexSize);
}

/**
 * Classic (Standard) 3D Campus Map Engine:
 * - Zero external /textures/* downloads (uses self-contained quantized classic GLBs)
 * - Zero postprocessing / N8AO / path-tracer / weather / astronomy JS loaded
 * - Clean bright daylight presentation faithful to the classic map
 * - Unrestricted 4-tier quality scaling (low / medium / high / ultra) on all devices
 */
export function mountClassicEngine(options: EngineMountOptions): CampusSceneEngineHandle | null {
  const {
    container,
    campus,
    places,
    quality,
    initialSelectedPlaceId,
    initialShowPins,
    initialCompactViewport,
    initialSnapshot,
    pinElsRef,
    compassDialRef,
    virtualInputRef,
    onProgress,
    onLoaded,
    onSelectPlace,
    onWebGLError,
  } = options;

  let disposed = false;
  let selectedPlaceId = initialSelectedPlaceId;
  let hoveredPlaceId: string | null = null;
  let showPins = initialShowPins;
  let isCompactViewport = initialCompactViewport;
  let isSceneReady = false;

  onLoaded(false);
  onProgress(6);

  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({
      antialias: quality !== "low",
      powerPreference: "high-performance",
    });
  } catch {
    onWebGLError("当前浏览器或设备无法创建 WebGL 上下文，请开启硬件加速后重试。");
    return null;
  }

  const width = Math.max(container.clientWidth, 320);
  const height = Math.max(container.clientHeight, 320);
  const shadowRes = computeClassicShadowRes(quality, renderer.capabilities.maxTextureSize);

  renderer.setPixelRatio(computeClassicDpr(quality));
  renderer.setSize(width, height);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = shadowRes > 0;
  renderer.shadowMap.type =
    quality === "medium" ? THREE.PCFShadowMap : THREE.PCFSoftShadowMap;
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
  const bgHex = 0xd9e8f7;
  scene.background = new THREE.Color(bgHex);
  scene.fog = new THREE.FogExp2(bgHex, 0.0012);

  let pmrem: THREE.PMREMGenerator | null = null;
  let envTarget: THREE.WebGLRenderTarget | null = null;
  if (quality !== "low") {
    pmrem = new THREE.PMREMGenerator(renderer);
    const roomEnv = new RoomEnvironment();
    envTarget = pmrem.fromScene(roomEnv, 0.04);
    scene.environment = envTarget.texture;
    scene.environmentIntensity = 0.78;
    roomEnv.dispose();
  }

  const camera = new THREE.PerspectiveCamera(
    computeAdaptiveFov(width, height),
    width / height,
    0.5,
    900
  );

  const nav = new CampusNavigationController(
    camera,
    renderer.domElement,
    campus,
    virtualInputRef,
    initialSnapshot
  );

  const hemiLight = new THREE.HemisphereLight(
    0xddeeff,
    0x9ea6b2,
    quality === "low" ? 0.92 : 0.72
  );
  scene.add(hemiLight);

  const sunLight = new THREE.DirectionalLight(0xfff7ea, quality === "low" ? 2.1 : 2.3);
  sunLight.position.set(78, 108, 52);
  if (shadowRes > 0) {
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.set(shadowRes, shadowRes);
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 380;
    const extent = campus.id === "west" ? 132 : 98;
    sunLight.shadow.camera.left = -extent;
    sunLight.shadow.camera.right = extent;
    sunLight.shadow.camera.top = extent;
    sunLight.shadow.camera.bottom = -extent;
    sunLight.shadow.bias = -0.00045;
    sunLight.shadow.normalBias = 0.025;
  }
  scene.add(sunLight);

  const horizonGeo = new THREE.CircleGeometry(460, 48);
  horizonGeo.rotateX(-Math.PI / 2);
  const horizonMat = new THREE.MeshStandardMaterial({
    color: 0xd1dae3,
    roughness: 0.96,
    metalness: 0,
  });
  const horizonMesh = new THREE.Mesh(horizonGeo, horizonMat);
  horizonMesh.position.set(campus.defaultCameraTarget[0], -0.24, campus.defaultCameraTarget[2]);
  horizonMesh.receiveShadow = shadowRes > 0;
  horizonMesh.name = "__horizon_apron";
  scene.add(horizonMesh);

  const nodeMaterials = new Map<string, ClonedMatRecord[]>();
  const selectableMeshes: THREE.Mesh[] = [];
  const validPlaceIds = new Set(places.map((p) => p.meshNodeName));

  const applyHighlights = () => {
    for (const [nodeId, records] of nodeMaterials.entries()) {
      const isSelected = nodeId === selectedPlaceId;
      const isHovered = nodeId === hoveredPlaceId;
      for (const rec of records) {
        if (isSelected) {
          rec.material.emissive.setHex(0x2856e8);
          rec.material.emissiveIntensity = 0.26;
        } else if (isHovered) {
          rec.material.emissive.setHex(0x2d74da);
          rec.material.emissiveIntensity = 0.16;
        } else {
          rec.material.emissive.copy(rec.baseEmissive);
          rec.material.emissiveIntensity = rec.baseEmissiveIntensity;
        }
      }
    }
  };

  const hwMaxAniso = renderer.capabilities.getMaxAnisotropy();
  const targetAniso = Math.min(
    quality === "low" ? 1 : quality === "medium" ? 4 : quality === "high" ? 8 : hwMaxAniso,
    hwMaxAniso
  );

  const loader = new GLTFLoader();
  loader.load(
    campus.classicModelUrl,
    (gltf) => {
      if (disposed) return;
      const loadedRoot = gltf.scene;
      const enableShadows = shadowRes > 0;

      loadedRoot.traverse((obj) => {
        if (validPlaceIds.has(obj.name)) {
          const placeId = obj.name;
          const clonedForNode: ClonedMatRecord[] = [];
          obj.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
              const mesh = child as THREE.Mesh;
              mesh.castShadow = enableShadows;
              mesh.receiveShadow = enableShadows;
              mesh.userData.placeId = placeId;
              selectableMeshes.push(mesh);

              const cloneOne = (m: THREE.Material): THREE.Material => {
                if ((m as THREE.MeshStandardMaterial).isMeshStandardMaterial) {
                  const cloned = (m as THREE.MeshStandardMaterial).clone();
                  if (cloned.map) {
                    cloned.map.anisotropy = targetAniso;
                  }
                  clonedForNode.push({
                    material: cloned,
                    baseEmissive: cloned.emissive.clone(),
                    baseEmissiveIntensity: cloned.emissiveIntensity,
                  });
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
          mesh.castShadow = enableShadows;
          mesh.receiveShadow = enableShadows;
          const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          for (const mat of mats) {
            const std = mat as THREE.MeshStandardMaterial | undefined;
            if (std?.map) {
              std.map.anisotropy = targetAniso;
            }
          }
        }
      });

      scene.add(loadedRoot);
      isSceneReady = true;
      applyHighlights();
      onProgress(100);
      onLoaded(true);
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
        onWebGLError("三维校园模型加载失败，请检查网络后重试。");
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
    const hit = getHitPlaceId(ev.clientX, ev.clientY);
    renderer.domElement.style.cursor = hit ? "pointer" : "grab";
    if (hit !== hoveredPlaceId) {
      hoveredPlaceId = hit;
      if (isSceneReady) applyHighlights();
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
    }
  });
  ro.observe(container);

  const clock = new THREE.Clock();
  let rafId = 0;

  const animate = () => {
    if (disposed || document.hidden) {
      rafId = 0;
      return;
    }
    rafId = window.requestAnimationFrame(animate);
    const dt = Math.min(clock.getDelta(), 0.05);

    nav.update(dt);
    renderer.render(scene, camera);

    updateCompassHeading(camera, nav.controls.target, compassDialRef.current);
    projectCampusPins(
      camera,
      renderer.domElement.clientWidth,
      renderer.domElement.clientHeight,
      places,
      pinElsRef.current,
      selectedPlaceId,
      showPins,
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
      if (isSceneReady) applyHighlights();
    },
    setShowPins: (show) => {
      showPins = show;
    },
    setIsCompactViewport: (compact) => {
      isCompactViewport = compact;
    },
    dispose: () => {
      disposed = true;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      if (rafId) window.cancelAnimationFrame(rafId);
      ro.disconnect();
      nav.dispose();
      renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      renderer.domElement.removeEventListener("pointermove", handlePointerMove);
      renderer.domElement.removeEventListener("pointerup", handlePointerUp);
      renderer.domElement.removeEventListener("pointercancel", handlePointerCancel);
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

      sunLight.shadow.map?.dispose();
      envTarget?.dispose();
      pmrem?.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    },
  };
}
