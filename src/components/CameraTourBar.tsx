"use client";

import { CameraTourStop } from "@/data/types";

interface CameraTourBarProps {
  tours: CameraTourStop[];
  activeTourId: string | null;
  onSelectTour: (tour: CameraTourStop) => void;
}

export function CameraTourBar({
  tours,
  activeTourId,
  onSelectTour,
}: CameraTourBarProps) {
  if (tours.length === 0) return null;

  return (
    <div className="tour-dock" role="toolbar" aria-label="精选导览视角">
      {tours.map((tour) => {
        const active = tour.id === activeTourId;
        return (
          <button
            key={tour.id}
            type="button"
            className={`tour-pill ${active ? "tour-pill-active" : ""}`}
            onClick={() => onSelectTour(tour)}
            title={tour.subtitle}
          >
            {tour.title}
          </button>
        );
      })}
    </div>
  );
}
