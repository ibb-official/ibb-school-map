"use client";

import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { FlightInputVector } from "@/data/types";

interface TouchFlightControlsProps {
  inputRef: React.MutableRefObject<FlightInputVector>;
}

const MAX_STICK_RADIUS = 34;
const DEADZONE_RATIO = 0.12;

function trySetPointerCapture(el: HTMLElement, pointerId: number): void {
  try {
    el.setPointerCapture(pointerId);
  } catch {
    // Some touch browsers may throw if pointer is synthetic or already released
  }
}

function tryReleasePointerCapture(el: HTMLElement, pointerId: number): void {
  try {
    if (el.hasPointerCapture(pointerId)) {
      el.releasePointerCapture(pointerId);
    }
  } catch {
    // Ignore release errors on detached or already-released pointers
  }
}

/**
 * Cross-platform virtual flight controls (usable with both touch multi-touch & desktop mouse):
 * - Bottom-left analog joystick -> horizontal plane flight (equivalent to WASD)
 * - Bottom-right altitude keys -> smooth vertical ascend/descend (equivalent to Space / Shift)
 */
export function TouchFlightControls({ inputRef }: TouchFlightControlsProps) {
  const [knobOffset, setKnobOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [stickActive, setStickActive] = useState<boolean>(false);
  const [upHeld, setUpHeld] = useState<boolean>(false);
  const [downHeld, setDownHeld] = useState<boolean>(false);

  const joystickRef = useRef<HTMLDivElement | null>(null);
  const altitudeGroupRef = useRef<HTMLDivElement | null>(null);
  const stickPointerIdRef = useRef<number | null>(null);
  const stickCenterRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const upPointerIdRef = useRef<number | null>(null);
  const downPointerIdRef = useRef<number | null>(null);

  const syncVertical = useCallback(
    (up: boolean, down: boolean) => {
      inputRef.current.moveY = (up ? 1 : 0) - (down ? 1 : 0);
    },
    [inputRef]
  );

  const releaseStick = useCallback(() => {
    stickPointerIdRef.current = null;
    setStickActive(false);
    setKnobOffset({ x: 0, y: 0 });
    inputRef.current.moveX = 0;
    inputRef.current.moveZ = 0;
  }, [inputRef]);

  const releaseUp = useCallback(() => {
    upPointerIdRef.current = null;
    setUpHeld(false);
    syncVertical(false, downPointerIdRef.current !== null);
  }, [syncVertical]);

  const releaseDown = useCallback(() => {
    downPointerIdRef.current = null;
    setDownHeld(false);
    syncVertical(upPointerIdRef.current !== null, false);
  }, [syncVertical]);

  // Block native browser touch/long-press gestures (iOS callout/loupe, Android long-press/contextmenu,
  // drag, text selection) via non-passive DOM listeners without blocking Pointer Events.
  useEffect(() => {
    const targets = [joystickRef.current, altitudeGroupRef.current].filter(
      (el): el is HTMLDivElement => el !== null
    );
    if (targets.length === 0) return;

    const preventBrowserGesture = (ev: Event) => {
      if (ev.cancelable) {
        ev.preventDefault();
      }
    };

    for (const el of targets) {
      el.addEventListener("touchstart", preventBrowserGesture, { passive: false });
      el.addEventListener("touchmove", preventBrowserGesture, { passive: false });
      el.addEventListener("gesturestart", preventBrowserGesture, { passive: false });
      el.addEventListener("gesturechange", preventBrowserGesture, { passive: false });
      el.addEventListener("contextmenu", preventBrowserGesture);
      el.addEventListener("selectstart", preventBrowserGesture);
      el.addEventListener("dragstart", preventBrowserGesture);
    }

    return () => {
      for (const el of targets) {
        el.removeEventListener("touchstart", preventBrowserGesture);
        el.removeEventListener("touchmove", preventBrowserGesture);
        el.removeEventListener("gesturestart", preventBrowserGesture);
        el.removeEventListener("gesturechange", preventBrowserGesture);
        el.removeEventListener("contextmenu", preventBrowserGesture);
        el.removeEventListener("selectstart", preventBrowserGesture);
        el.removeEventListener("dragstart", preventBrowserGesture);
      }
    };
  }, []);

  // Guarantee zero residual drift if component unmounts, tab hides, window blurs, or pointer ends off-target
  useEffect(() => {
    const resetAll = () => {
      stickPointerIdRef.current = null;
      upPointerIdRef.current = null;
      downPointerIdRef.current = null;
      setStickActive(false);
      setKnobOffset({ x: 0, y: 0 });
      setUpHeld(false);
      setDownHeld(false);
      inputRef.current.moveX = 0;
      inputRef.current.moveZ = 0;
      inputRef.current.moveY = 0;
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        resetAll();
      }
    };

    const handleGlobalPointerEnd = (ev: PointerEvent) => {
      if (stickPointerIdRef.current === ev.pointerId) {
        releaseStick();
      }
      if (upPointerIdRef.current === ev.pointerId) {
        releaseUp();
      }
      if (downPointerIdRef.current === ev.pointerId) {
        releaseDown();
      }
    };

    window.addEventListener("blur", resetAll);
    window.addEventListener("pointerup", handleGlobalPointerEnd);
    window.addEventListener("pointercancel", handleGlobalPointerEnd);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.removeEventListener("blur", resetAll);
      window.removeEventListener("pointerup", handleGlobalPointerEnd);
      window.removeEventListener("pointercancel", handleGlobalPointerEnd);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      resetAll();
    };
  }, [inputRef, releaseStick, releaseUp, releaseDown]);

  const updateStickFromClient = (clientX: number, clientY: number) => {
    const dx = clientX - stickCenterRef.current.x;
    const dy = clientY - stickCenterRef.current.y;
    const dist = Math.hypot(dx, dy);
    const clampedDist = Math.min(dist, MAX_STICK_RADIUS);
    const angle = Math.atan2(dy, dx);
    const clampedX = Math.cos(angle) * clampedDist;
    const clampedY = Math.sin(angle) * clampedDist;

    setKnobOffset({ x: clampedX, y: clampedY });

    const normMag = clampedDist / MAX_STICK_RADIUS;
    if (normMag < DEADZONE_RATIO) {
      inputRef.current.moveX = 0;
      inputRef.current.moveZ = 0;
      return;
    }

    const rescaled = (normMag - DEADZONE_RATIO) / (1 - DEADZONE_RATIO);
    // Gentle precision curve for micro-adjustments, brisk full-deflection cruising
    const curved = rescaled * (0.4 + 0.6 * rescaled);
    inputRef.current.moveX = Math.cos(angle) * curved;
    // Screen upward (-Y) maps to forward (+moveZ)
    inputRef.current.moveZ = -Math.sin(angle) * curved;
  };

  const handleStickDown = (ev: React.PointerEvent<HTMLDivElement>) => {
    if (ev.pointerType === "mouse" && ev.button !== 0) return;
    ev.preventDefault();
    ev.stopPropagation();
    if (stickPointerIdRef.current !== null) return;
    const rect = ev.currentTarget.getBoundingClientRect();
    stickCenterRef.current = {
      x: rect.left + rect.width * 0.5,
      y: rect.top + rect.height * 0.5,
    };
    stickPointerIdRef.current = ev.pointerId;
    setStickActive(true);
    trySetPointerCapture(ev.currentTarget, ev.pointerId);
    updateStickFromClient(ev.clientX, ev.clientY);
  };

  const handleStickMove = (ev: React.PointerEvent<HTMLDivElement>) => {
    if (stickPointerIdRef.current !== ev.pointerId) return;
    ev.preventDefault();
    ev.stopPropagation();
    updateStickFromClient(ev.clientX, ev.clientY);
  };

  const handleStickEnd = (ev: React.PointerEvent<HTMLDivElement>) => {
    if (stickPointerIdRef.current !== ev.pointerId) return;
    ev.stopPropagation();
    releaseStick();
    tryReleasePointerCapture(ev.currentTarget, ev.pointerId);
  };

  const handleUpDown = (ev: React.PointerEvent<HTMLButtonElement>) => {
    if (ev.pointerType === "mouse" && ev.button !== 0) return;
    ev.preventDefault();
    ev.stopPropagation();
    if (upPointerIdRef.current !== null) return;
    upPointerIdRef.current = ev.pointerId;
    trySetPointerCapture(ev.currentTarget, ev.pointerId);
    setUpHeld(true);
    syncVertical(true, downPointerIdRef.current !== null);
  };

  const handleUpEnd = (ev: React.PointerEvent<HTMLButtonElement>) => {
    if (upPointerIdRef.current !== ev.pointerId) return;
    ev.stopPropagation();
    releaseUp();
    tryReleasePointerCapture(ev.currentTarget, ev.pointerId);
  };

  const handleDownDown = (ev: React.PointerEvent<HTMLButtonElement>) => {
    if (ev.pointerType === "mouse" && ev.button !== 0) return;
    ev.preventDefault();
    ev.stopPropagation();
    if (downPointerIdRef.current !== null) return;
    downPointerIdRef.current = ev.pointerId;
    trySetPointerCapture(ev.currentTarget, ev.pointerId);
    setDownHeld(true);
    syncVertical(upPointerIdRef.current !== null, true);
  };

  const handleDownEnd = (ev: React.PointerEvent<HTMLButtonElement>) => {
    if (downPointerIdRef.current !== ev.pointerId) return;
    ev.stopPropagation();
    releaseDown();
    tryReleasePointerCapture(ev.currentTarget, ev.pointerId);
  };

  return (
    <>
      {/* Bottom-Left Analog Virtual Joystick (WASD equivalent) */}
      <div className="vpad-joystick-anchor" aria-label="平面移动虚拟摇杆">
        <div
          ref={joystickRef}
          className={`vpad-joystick-base${stickActive ? " vpad-joystick-active" : ""}`}
          draggable={false}
          onPointerDown={handleStickDown}
          onPointerMove={handleStickMove}
          onPointerUp={handleStickEnd}
          onPointerCancel={handleStickEnd}
          onLostPointerCapture={handleStickEnd}
          onContextMenu={(e) => e.preventDefault()}
          onDragStart={(e) => e.preventDefault()}
          role="application"
          aria-label="拖动摇杆进行前后左右移动"
        >
          <span className="vpad-dir-tick vpad-dir-n" aria-hidden="true">W</span>
          <span className="vpad-dir-tick vpad-dir-s" aria-hidden="true">S</span>
          <span className="vpad-dir-tick vpad-dir-w" aria-hidden="true">A</span>
          <span className="vpad-dir-tick vpad-dir-e" aria-hidden="true">D</span>
          <div
            className="vpad-joystick-thumb"
            style={{
              transform: `translate3d(${knobOffset.x.toFixed(1)}px, ${knobOffset.y.toFixed(1)}px, 0)`,
            }}
          />
        </div>
      </div>

      {/* Bottom-Right Vertical Altitude Controls (Space / Shift equivalent) */}
      <div
        ref={altitudeGroupRef}
        className="vpad-altitude-anchor"
        role="group"
        aria-label="视角升降控制"
      >
        <button
          type="button"
          className={`vpad-alt-btn${upHeld ? " vpad-alt-btn-active" : ""}`}
          draggable={false}
          onPointerDown={handleUpDown}
          onPointerUp={handleUpEnd}
          onPointerCancel={handleUpEnd}
          onLostPointerCapture={handleUpEnd}
          onContextMenu={(e) => e.preventDefault()}
          onDragStart={(e) => e.preventDefault()}
          aria-label="按住上升视角（等同 Space）"
        >
          <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
            <path
              d="M10 4.5 4.5 11.5h11L10 4.5Z"
              fill="currentColor"
            />
          </svg>
          <span>上升</span>
        </button>

        <span className="vpad-alt-divider" aria-hidden="true" />

        <button
          type="button"
          className={`vpad-alt-btn${downHeld ? " vpad-alt-btn-active" : ""}`}
          draggable={false}
          onPointerDown={handleDownDown}
          onPointerUp={handleDownEnd}
          onPointerCancel={handleDownEnd}
          onLostPointerCapture={handleDownEnd}
          onContextMenu={(e) => e.preventDefault()}
          onDragStart={(e) => e.preventDefault()}
          aria-label="按住下降视角（等同 Shift）"
        >
          <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
            <path
              d="M10 15.5 15.5 8.5h-11L10 15.5Z"
              fill="currentColor"
            />
          </svg>
          <span>下降</span>
        </button>
      </div>
    </>
  );
}
