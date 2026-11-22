import * as THREE from "three";
import { MapControls } from "three/examples/jsm/controls/MapControls.js";
import { CampusMeta, CameraSnapshot, FlightInputVector } from "@/data/types";

export interface FlightGoal {
  pos: THREE.Vector3;
  target: THREE.Vector3;
}

const MIN_CAMERA_Y = 1.5;
const MAX_CAMERA_Y = 190;
const MIN_TARGET_Y = -1;
const MAX_TARGET_Y = 48;

/**
 * Compensates vertical FOV on portrait viewports so the horizontal framing
 * stays wide enough to show the whole campus without clipping east/west wings.
 */
export function computeAdaptiveFov(width: number, height: number): number {
  const aspect = width / Math.max(height, 1);
  if (aspect >= 0.85) return 42;
  const baseHalfTan = Math.tan(THREE.MathUtils.degToRad(21));
  const clampedAspect = Math.max(aspect, 0.5);
  const adaptedRad = 2 * Math.atan((baseHalfTan / clampedAspect) * 0.78);
  return THREE.MathUtils.clamp(THREE.MathUtils.radToDeg(adaptedRad), 42, 62);
}

function isEditableElement(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.isContentEditable) return true;
  if (target.closest('[role="dialog"], [role="menu"], [role="listbox"]')) return true;
  return false;
}

/**
 * Unified 3D navigation controller shared across Classic & Enhanced engines:
 * - Touch gestures: strictly single-finger PAN + two-finger DOLLY_ROTATE (no rotate-mode switching)
 * - Keyboard: W/A/S/D (and arrows) horizontal camera-relative flight + Space ascend + Shift descend
 * - On-screen virtual controls: analog joystick (moveX/moveZ) + vertical up/down keys (moveY)
 * - Smooth exponential camera flights & instant due-North alignment
 */
export class CampusNavigationController {
  public readonly controls: MapControls;
  public flightGoal: FlightGoal | null = null;

  private readonly camera: THREE.PerspectiveCamera;
  private readonly campus: CampusMeta;
  private readonly virtualInputRef: { current: FlightInputVector };
  private readonly onCameraMoved?: () => void;

  private readonly pressedKeys = new Set<string>();
  private readonly forwardVec = new THREE.Vector3();
  private readonly rightVec = new THREE.Vector3();
  private readonly moveDelta = new THREE.Vector3();
  private readonly worldUp = new THREE.Vector3(0, 1, 0);

  constructor(
    camera: THREE.PerspectiveCamera,
    domElement: HTMLElement,
    campus: CampusMeta,
    virtualInputRef: { current: FlightInputVector },
    initialSnapshot?: CameraSnapshot | null,
    onCameraMoved?: () => void
  ) {
    this.camera = camera;
    this.campus = campus;
    this.virtualInputRef = virtualInputRef;
    this.onCameraMoved = onCameraMoved;

    if (initialSnapshot) {
      camera.position.set(...initialSnapshot.position);
    } else {
      camera.position.set(...campus.defaultCameraPos);
    }

    const controls = new MapControls(camera, domElement);
    if (initialSnapshot) {
      controls.target.set(...initialSnapshot.target);
    } else {
      controls.target.set(...campus.defaultCameraTarget);
    }

    const isCoarse =
      typeof window !== "undefined" &&
      window.matchMedia("(pointer: coarse)").matches;

    controls.enableDamping = true;
    controls.dampingFactor = isCoarse ? 0.1 : 0.08;
    controls.screenSpacePanning = false;
    controls.minDistance = 2.6;
    controls.maxDistance = 260;
    controls.minPolarAngle = isCoarse ? 0.12 : 0;
    controls.maxPolarAngle = Math.PI / 2 - 0.015;

    // Strictly retain drag/pan mode on touch devices (no single-finger rotate mode)
    controls.touches = {
      ONE: THREE.TOUCH.PAN,
      TWO: THREE.TOUCH.DOLLY_ROTATE,
    };

    if (isCoarse) {
      controls.panSpeed = 0.92;
      controls.rotateSpeed = 0.72;
      controls.zoomSpeed = 0.92;
    }

    controls.update();
    this.controls = controls;

    controls.addEventListener("start", this.handleControlsStart);
    controls.addEventListener("change", this.handleControlsChange);
    window.addEventListener("keydown", this.handleKeyDown, { passive: false });
    window.addEventListener("keyup", this.handleKeyUp);
    window.addEventListener("blur", this.clearKeys);
    document.addEventListener("visibilitychange", this.handleVisibilityChange);
  }

  private readonly handleControlsStart = (): void => {
    this.flightGoal = null;
  };

  private readonly handleControlsChange = (): void => {
    this.onCameraMoved?.();
  };

  private readonly clearKeys = (): void => {
    this.pressedKeys.clear();
  };

  private readonly handleVisibilityChange = (): void => {
    if (document.hidden) {
      this.pressedKeys.clear();
    }
  };

  private readonly handleKeyDown = (ev: KeyboardEvent): void => {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (isEditableElement(ev.target)) return;

    const code = ev.code;
    const isNavKey =
      code === "KeyW" ||
      code === "KeyA" ||
      code === "KeyS" ||
      code === "KeyD" ||
      code === "ArrowUp" ||
      code === "ArrowDown" ||
      code === "ArrowLeft" ||
      code === "ArrowRight" ||
      code === "Space" ||
      code === "ShiftLeft" ||
      code === "ShiftRight";

    if (!isNavKey) return;

    // Prevent Space from activating a focused button or scrolling when navigating 3D space
    if (code === "Space") {
      const active = document.activeElement;
      const isFocusedButton =
        active instanceof HTMLElement &&
        (active.tagName === "BUTTON" || active.getAttribute("role") === "button");
      if (isFocusedButton) return;
      ev.preventDefault();
    }

    if (code.startsWith("Arrow")) {
      ev.preventDefault();
    }

    this.pressedKeys.add(code);
    this.flightGoal = null;
  };

  private readonly handleKeyUp = (ev: KeyboardEvent): void => {
    this.pressedKeys.delete(ev.code);
  };

  public flyTo(pos: [number, number, number], target: [number, number, number]): void {
    this.flightGoal = {
      pos: new THREE.Vector3(...pos),
      target: new THREE.Vector3(...target),
    };
  }

  public alignNorth(): void {
    const dx = this.camera.position.x - this.controls.target.x;
    const dz = this.camera.position.z - this.controls.target.z;
    const horizDist = Math.max(Math.hypot(dx, dz), 12);
    const camY = Math.max(this.camera.position.y, this.controls.target.y + 8);
    this.flightGoal = {
      pos: new THREE.Vector3(this.controls.target.x, camY, this.controls.target.z + horizDist),
      target: this.controls.target.clone(),
    };
  }

  public getSnapshot(): CameraSnapshot {
    return {
      position: [this.camera.position.x, this.camera.position.y, this.camera.position.z],
      target: [this.controls.target.x, this.controls.target.y, this.controls.target.z],
    };
  }

  /**
   * Advances camera flight, WASD/Space/Shift keyboard movement, virtual joystick/altitude input,
   * and MapControls damping. Returns true if any free-flight movement occurred this frame.
   */
  public update(dt: number): boolean {
    let moved = false;

    // 1. Collect combined input from keyboard + optional virtual touch joystick / altitude buttons
    let inputX = 0;
    let inputZ = 0;
    let inputY = 0;

    if (this.pressedKeys.has("KeyW") || this.pressedKeys.has("ArrowUp")) inputZ += 1;
    if (this.pressedKeys.has("KeyS") || this.pressedKeys.has("ArrowDown")) inputZ -= 1;
    if (this.pressedKeys.has("KeyD") || this.pressedKeys.has("ArrowRight")) inputX += 1;
    if (this.pressedKeys.has("KeyA") || this.pressedKeys.has("ArrowLeft")) inputX -= 1;
    if (this.pressedKeys.has("Space")) inputY += 1;
    if (this.pressedKeys.has("ShiftLeft") || this.pressedKeys.has("ShiftRight")) inputY -= 1;

    const vInput = this.virtualInputRef.current;
    inputX += vInput.moveX;
    inputZ += vInput.moveZ;
    inputY += vInput.moveY;

    const horizLen = Math.hypot(inputX, inputZ);
    if (horizLen > 1) {
      inputX /= horizLen;
      inputZ /= horizLen;
    }
    inputY = THREE.MathUtils.clamp(inputY, -1, 1);

    const hasManualInput = horizLen > 0.01 || Math.abs(inputY) > 0.01;
    if (hasManualInput) {
      this.flightGoal = null;
      moved = true;

      // Altitude-adaptive speed: gentle at pedestrian scale, brisk at aerial overview
      const orbitDist = this.camera.position.distanceTo(this.controls.target);
      const refHeight = Math.max(this.camera.position.y, orbitDist * 0.55);
      const horizSpeed = THREE.MathUtils.clamp(refHeight * 0.65, 8.5, 58);
      const vertSpeed = THREE.MathUtils.clamp(refHeight * 0.48, 6.5, 42);

      // Compute camera-relative horizontal basis on XZ plane
      this.camera.getWorldDirection(this.forwardVec);
      this.forwardVec.y = 0;
      if (this.forwardVec.lengthSq() < 1e-5) {
        this.forwardVec.set(0, 0, -1);
      } else {
        this.forwardVec.normalize();
      }
      this.rightVec.crossVectors(this.forwardVec, this.worldUp).normalize();

      this.moveDelta
        .set(0, 0, 0)
        .addScaledVector(this.rightVec, inputX * horizSpeed * dt)
        .addScaledVector(this.forwardVec, inputZ * horizSpeed * dt);

      // Vertical displacement with safe floor/ceiling clamping applied identically to camera & target
      let dy = inputY * vertSpeed * dt;
      const nextCamY = this.camera.position.y + dy;
      if (nextCamY < MIN_CAMERA_Y) {
        dy = MIN_CAMERA_Y - this.camera.position.y;
      } else if (nextCamY > MAX_CAMERA_Y) {
        dy = MAX_CAMERA_Y - this.camera.position.y;
      }
      const nextTargetY = this.controls.target.y + dy;
      if (nextTargetY < MIN_TARGET_Y) {
        dy = Math.max(dy, MIN_TARGET_Y - this.controls.target.y);
      } else if (nextTargetY > MAX_TARGET_Y) {
        dy = Math.min(dy, MAX_TARGET_Y - this.controls.target.y);
      }
      this.moveDelta.y = dy;

      this.camera.position.add(this.moveDelta);
      this.controls.target.add(this.moveDelta);
    }

    // 2. Smooth exponential fly-to transition
    if (this.flightGoal) {
      const alpha = 1 - Math.exp(-5.4 * dt);
      this.camera.position.lerp(this.flightGoal.pos, alpha);
      this.controls.target.lerp(this.flightGoal.target, alpha);
      moved = true;
      if (
        this.camera.position.distanceTo(this.flightGoal.pos) < 0.08 &&
        this.controls.target.distanceTo(this.flightGoal.target) < 0.08
      ) {
        this.camera.position.copy(this.flightGoal.pos);
        this.controls.target.copy(this.flightGoal.target);
        this.flightGoal = null;
      }
    }

    // 3. Clamp target within calibrated campus ENU pan bounds & shift camera equally so orbit distance never warps
    const prevX = this.controls.target.x;
    const prevZ = this.controls.target.z;
    const clampedX = THREE.MathUtils.clamp(
      prevX,
      this.campus.panBounds.minX,
      this.campus.panBounds.maxX
    );
    const clampedZ = THREE.MathUtils.clamp(
      prevZ,
      this.campus.panBounds.minZ,
      this.campus.panBounds.maxZ
    );
    if (clampedX !== prevX || clampedZ !== prevZ) {
      this.controls.target.x = clampedX;
      this.controls.target.z = clampedZ;
      this.camera.position.x += clampedX - prevX;
      this.camera.position.z += clampedZ - prevZ;
    }

    this.controls.target.y = THREE.MathUtils.clamp(
      this.controls.target.y,
      MIN_TARGET_Y,
      MAX_TARGET_Y
    );
    this.camera.position.y = THREE.MathUtils.clamp(
      this.camera.position.y,
      MIN_CAMERA_Y,
      MAX_CAMERA_Y
    );

    this.controls.update();

    if (moved) {
      this.onCameraMoved?.();
    }
    return moved;
  }

  public dispose(): void {
    this.controls.removeEventListener("start", this.handleControlsStart);
    this.controls.removeEventListener("change", this.handleControlsChange);
    window.removeEventListener("keydown", this.handleKeyDown);
    window.removeEventListener("keyup", this.handleKeyUp);
    window.removeEventListener("blur", this.clearKeys);
    document.removeEventListener("visibilitychange", this.handleVisibilityChange);
    this.pressedKeys.clear();
    this.controls.dispose();
  }
}
