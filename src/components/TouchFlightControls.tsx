"use client";

import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { FlightInputVector } from "@/data/types";

interface TouchFlightControlsProps {
  inputRef: React.MutableRefObject<FlightInputVector>;
}

const MAX_STICK_RADIUS = 34;
const DEADZONE_RATIO = 0.12;

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

  // Guarantee zero residual drift if component unmounts or window loses focus
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
    window.addEventListener("blur", resetAll);
    return () => {
      window.removeEventListener("blur", resetAll);
      resetAll();
    };
  }, [inputRef]);

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
    ev.stopPropagation();
    if (stickPointerIdRef.current !== null) return;
    const rect = ev.currentTarget.getBoundingClientRect();
    stickCenterRef.current = {
      x: rect.left + rect.width * 0.5,
      y: rect.top + rect.height * 0.5,
    };
    stickPointerIdRef.current = ev.pointerId;
    setStickActive(true);
    ev.currentTarget.setPointerCapture(ev.pointerId);
    updateStickFromClient(ev.clientX, ev.clientY);
  };

  const handleStickMove = (ev: React.PointerEvent<HTMLDivElement>) => {
    if (stickPointerIdRef.current !== ev.pointerId) return;
    ev.stopPropagation();
    updateStickFromClient(ev.clientX, ev.clientY);
  };

  const handleStickEnd = (ev: React.PointerEvent<HTMLDivElement>) => {
    if (stickPointerIdRef.current !== ev.pointerId) return;
    ev.stopPropagation();
    stickPointerIdRef.current = null;
    setStickActive(false);
    setKnobOffset({ x: 0, y: 0 });
    inputRef.current.moveX = 0;
    inputRef.current.moveZ = 0;
    if (ev.currentTarget.hasPointerCapture(ev.pointerId)) {
      ev.currentTarget.releasePointerCapture(ev.pointerId);
    }
  };

  const handleUpDown = (ev: React.PointerEvent<HTMLButtonElement>) => {
    ev.stopPropagation();
    upPointerIdRef.current = ev.pointerId;
    ev.currentTarget.setPointerCapture(ev.pointerId);
    setUpHeld(true);
    syncVertical(true, downPointerIdRef.current !== null);
  };

  const handleUpEnd = (ev: React.PointerEvent<HTMLButtonElement>) => {
    if (upPointerIdRef.current !== ev.pointerId) return;
    ev.stopPropagation();
    upPointerIdRef.current = null;
    setUpHeld(false);
    syncVertical(false, downPointerIdRef.current !== null);
    if (ev.currentTarget.hasPointerCapture(ev.pointerId)) {
      ev.currentTarget.releasePointerCapture(ev.pointerId);
    }
  };

  const handleDownDown = (ev: React.PointerEvent<HTMLButtonElement>) => {
    ev.stopPropagation();
    downPointerIdRef.current = ev.pointerId;
    ev.currentTarget.setPointerCapture(ev.pointerId);
    setDownHeld(true);
    syncVertical(upPointerIdRef.current !== null, true);
  };

  const handleDownEnd = (ev: React.PointerEvent<HTMLButtonElement>) => {
    if (downPointerIdRef.current !== ev.pointerId) return;
    ev.stopPropagation();
    downPointerIdRef.current = null;
    setDownHeld(false);
    syncVertical(upPointerIdRef.current !== null, false);
    if (ev.currentTarget.hasPointerCapture(ev.pointerId)) {
      ev.currentTarget.releasePointerCapture(ev.pointerId);
    }
  };

  return (
    <>
      {/* Bottom-Left Analog Virtual Joystick (WASD equivalent) */}
      <div className="vpad-joystick-anchor" aria-label="平面移动虚拟摇杆">
        <div
          className={`vpad-joystick-base${stickActive ? " vpad-joystick-active" : ""}`}
          onPointerDown={handleStickDown}
          onPointerMove={handleStickMove}
          onPointerUp={handleStickEnd}
          onPointerCancel={handleStickEnd}
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
      <div className="vpad-altitude-anchor" role="group" aria-label="视角升降控制">
        <button
          type="button"
          className={`vpad-alt-btn${upHeld ? " vpad-alt-btn-active" : ""}`}
          onPointerDown={handleUpDown}
          onPointerUp={handleUpEnd}
          onPointerCancel={handleUpEnd}
          onContextMenu={(e) => e.preventDefault()}
          aria-label="按住上升视角"
          title="按住上升（等同 Space）"
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
          onPointerDown={handleDownDown}
          onPointerUp={handleDownEnd}
          onPointerCancel={handleDownEnd}
          onContextMenu={(e) => e.preventDefault()}
          aria-label="按住下降视角"
          title="按住下降（等同 Shift）"
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
