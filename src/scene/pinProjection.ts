import * as THREE from "three";
import { CampusPlace, PlaceCategory } from "@/data/types";

const PIN_CATEGORY_PRIORITY: Record<PlaceCategory, number> = {
  gate: 0,
  heritage: 1,
  sports: 2,
  corridor: 3,
  academic: 4,
};

const projVec = new THREE.Vector3();
const acceptedPinBoxes: { x0: number; y0: number; x1: number; y1: number }[] = [];

export function updateCompassHeading(
  camera: THREE.PerspectiveCamera,
  target: THREE.Vector3,
  compassDialEl: HTMLDivElement | null
): void {
  if (!compassDialEl) return;
  const vdx = target.x - camera.position.x;
  const vdz = target.z - camera.position.z;
  if (Math.hypot(vdx, vdz) > 0.05) {
    const rotCss = `${((Math.atan2(-vdx, -vdz) * 180) / Math.PI).toFixed(1)}deg`;
    compassDialEl.style.setProperty("--compass-rot", rotCss);
  }
}

export function projectCampusPins(
  camera: THREE.PerspectiveCamera,
  canvasWidth: number,
  canvasHeight: number,
  places: CampusPlace[],
  pinEls: Map<string, HTMLButtonElement>,
  selectedPlaceId: string | null,
  showPins: boolean,
  isCompactViewport: boolean
): void {
  if (!showPins) return;

  const cullOverlap = isCompactViewport || canvasWidth <= 860;

  if (!cullOverlap) {
    for (const place of places) {
      const el = pinEls.get(place.id);
      if (!el) continue;
      projVec.set(place.position[0], place.position[1], place.position[2]);
      projVec.project(camera);
      if (projVec.z > 1 || projVec.z < -1) {
        el.style.opacity = "0";
        el.style.pointerEvents = "none";
        continue;
      }
      const sx = (projVec.x * 0.5 + 0.5) * canvasWidth;
      const sy = (-projVec.y * 0.5 + 0.5) * canvasHeight;
      if (sx < -40 || sx > canvasWidth + 40 || sy < -40 || sy > canvasHeight + 40) {
        el.style.opacity = "0";
        el.style.pointerEvents = "none";
        continue;
      }
      el.style.opacity = "1";
      el.style.pointerEvents = "auto";
      el.style.left = `${sx.toFixed(1)}px`;
      el.style.top = `${sy.toFixed(1)}px`;
    }
    return;
  }

  acceptedPinBoxes.length = 0;
  const safeRightEdge = canvasWidth - 60;
  const safeBottomEdge = canvasHeight - 84;
  const orderedPlaces = [...places].sort((a, b) => {
    if (a.id === selectedPlaceId) return -1;
    if (b.id === selectedPlaceId) return 1;
    return PIN_CATEGORY_PRIORITY[a.category] - PIN_CATEGORY_PRIORITY[b.category];
  });

  for (const place of orderedPlaces) {
    const el = pinEls.get(place.id);
    if (!el) continue;
    projVec.set(place.position[0], place.position[1], place.position[2]);
    projVec.project(camera);
    if (projVec.z > 1 || projVec.z < -1) {
      el.style.opacity = "0";
      el.style.pointerEvents = "none";
      continue;
    }
    const sx = (projVec.x * 0.5 + 0.5) * canvasWidth;
    const sy = (-projVec.y * 0.5 + 0.5) * canvasHeight;
    const isSel = place.id === selectedPlaceId;

    const estW = Math.min(126, 28 + place.shortName.length * 11.5) + 10;
    const estH = 34;
    const x0 = sx - estW * 0.5;
    const x1 = sx + estW * 0.5;
    const y0 = sy - estH;
    const y1 = sy + 4;

    if (
      isSel
        ? sx < 14 || sx > canvasWidth - 14 || sy < 26 || sy > canvasHeight - 24
        : x0 < 10 || x1 > safeRightEdge || y0 < 56 || y1 > safeBottomEdge
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
