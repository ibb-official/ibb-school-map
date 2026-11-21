"use client";

import { useEffect, useRef } from "react";
import { CameraTourStop } from "@/data/types";

interface CameraTourBarProps {
  tours: CameraTourStop[];
  activeTourId: string | null;
  onSelectTour: (tour: CameraTourStop) => void;
  elevatedForVpad?: boolean;
}

export function CameraTourBar({
  tours,
  activeTourId,
  onSelectTour,
  elevatedForVpad = false,
}: CameraTourBarProps) {
  const pillRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  useEffect(() => {
    if (!activeTourId) return;
    const el = pillRefs.current.get(activeTourId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }
  }, [activeTourId]);

  if (tours.length === 0) return null;

  return (
    <div
      className={`hud-tour-dock${elevatedForVpad ? " hud-tour-dock-raised" : ""}`}
      role="toolbar"
      aria-label="精选导览视角"
    >
      <div className="hud-tour-scroll">
        {tours.map((tour) => {
          const active = tour.id === activeTourId;
          return (
            <button
              key={tour.id}
              ref={(el) => {
                if (el) pillRefs.current.set(tour.id, el);
                else pillRefs.current.delete(tour.id);
              }}
              type="button"
              className={`hud-tour-pill${active ? " hud-tour-pill-active" : ""}`}
              onClick={() => onSelectTour(tour)}
              title={tour.subtitle}
            >
              {tour.title}
            </button>
          );
        })}
      </div>
    </div>
  );
}
