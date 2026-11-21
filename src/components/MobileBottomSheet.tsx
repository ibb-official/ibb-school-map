"use client";

import React, { useEffect, useRef, useState } from "react";

export type SheetSnap = "peek" | "expanded";

interface MobileBottomSheetProps {
  open: boolean;
  onClose: () => void;
  ariaLabel: string;
  variant?: "single" | "two-stage";
  snap?: SheetSnap;
  onSnapChange?: (next: SheetSnap) => void;
  modalBackdrop?: boolean;
  header?: React.ReactNode;
  peekContent?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function MobileBottomSheet({
  open,
  onClose,
  ariaLabel,
  variant = "single",
  snap = "expanded",
  onSnapChange,
  modalBackdrop = true,
  header,
  peekContent,
  children,
  className = "",
}: MobileBottomSheetProps) {
  const [dragOffset, setDragOffset] = useState<number>(0);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  const dragStateRef = useRef<{
    pointerId: number;
    startY: number;
    startTime: number;
    lastY: number;
  } | null>(null);

  const isPeek = variant === "two-stage" && snap === "peek";
  const showBackdrop = open && modalBackdrop && !isPeek;

  useEffect(() => {
    if (!open) {
      setDragOffset(0);
      setIsDragging(false);
      dragStateRef.current = null;
      return;
    }

    const handleKeyDown = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") {
        if (variant === "two-stage" && snap === "expanded" && onSnapChange) {
          onSnapChange("peek");
        } else {
          onClose();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, variant, snap, onSnapChange, onClose]);

  if (!open) return null;

  const beginDrag = (ev: React.PointerEvent<HTMLElement>) => {
    const target = ev.target as HTMLElement | null;
    if (target?.closest("button, a, input, select, textarea")) {
      return;
    }
    dragStateRef.current = {
      pointerId: ev.pointerId,
      startY: ev.clientY,
      startTime: performance.now(),
      lastY: ev.clientY,
    };
    setIsDragging(true);
    ev.currentTarget.setPointerCapture(ev.pointerId);
  };

  const moveDrag = (ev: React.PointerEvent<HTMLElement>) => {
    const st = dragStateRef.current;
    if (!st || st.pointerId !== ev.pointerId) return;
    const dy = ev.clientY - st.startY;
    st.lastY = ev.clientY;

    if (dy < 0) {
      const resisted = isPeek ? Math.max(dy, -140) : Math.max(dy * 0.22, -32);
      setDragOffset(resisted);
    } else {
      setDragOffset(Math.min(dy, 360));
    }
  };

  const endDrag = (ev: React.PointerEvent<HTMLElement>) => {
    const st = dragStateRef.current;
    if (!st || st.pointerId !== ev.pointerId) return;
    const dy = st.lastY - st.startY;
    const dt = Math.max(performance.now() - st.startTime, 1);
    const velocity = dy / dt;

    dragStateRef.current = null;
    setIsDragging(false);
    setDragOffset(0);

    if (ev.currentTarget.hasPointerCapture(ev.pointerId)) {
      ev.currentTarget.releasePointerCapture(ev.pointerId);
    }

    if (variant === "two-stage") {
      if (isPeek) {
        if (dy < -32 || velocity < -0.35) {
          onSnapChange?.("expanded");
        } else if (dy > 44 || velocity > 0.45) {
          onClose();
        }
      } else {
        if (dy > 130 || velocity > 0.72) {
          onClose();
        } else if (dy > 42 || velocity > 0.32) {
          onSnapChange?.("peek");
        }
      }
      return;
    }

    if (dy > 54 || velocity > 0.42) {
      onClose();
    }
  };

  const handleBackdropClick = () => {
    if (variant === "two-stage" && snap === "expanded" && onSnapChange) {
      onSnapChange("peek");
    } else {
      onClose();
    }
  };

  return (
    <>
      {showBackdrop && (
        <div
          className="s2-sheet-backdrop"
          onClick={handleBackdropClick}
          aria-hidden="true"
        />
      )}
      <section
        role="dialog"
        aria-modal={showBackdrop}
        aria-label={ariaLabel}
        className={`s2-sheet ${isPeek ? "s2-sheet-peek" : "s2-sheet-expanded"} ${
          isDragging ? "s2-sheet-dragging" : ""
        } ${className}`.trim()}
        style={
          dragOffset !== 0
            ? { transform: `translate3d(0, ${dragOffset.toFixed(1)}px, 0)` }
            : undefined
        }
      >
        <div
          className="s2-sheet-drag-zone"
          onPointerDown={beginDrag}
          onPointerMove={moveDrag}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
        >
          <div className="s2-sheet-handle" aria-hidden="true">
            <span className="s2-sheet-handle-pill" />
          </div>
          {header && <div className="s2-sheet-header">{header}</div>}
        </div>

        {isPeek && peekContent ? (
          <div
            className="s2-sheet-peek-body"
            onPointerDown={beginDrag}
            onPointerMove={moveDrag}
            onPointerUp={endDrag}
            onPointerCancel={endDrag}
          >
            {peekContent}
          </div>
        ) : (
          <div className="s2-sheet-body">{children}</div>
        )}
      </section>
    </>
  );
}
