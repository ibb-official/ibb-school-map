"use client";

import { SegmentedControl, SegmentedControlItem } from "@react-spectrum/s2/SegmentedControl";
import { CAMPUSES } from "@/data/campuses";
import { CampusId } from "@/data/types";

interface CampusSwitcherProps {
  campusId: CampusId;
  onChange: (next: CampusId) => void;
  compact?: boolean;
}

export function CampusSwitcher({ campusId, onChange, compact = false }: CampusSwitcherProps) {
  return (
    <div
      className="hud-island hud-campus-island"
      title={`${CAMPUSES[campusId].name} · ${CAMPUSES[campusId].address}`}
    >
      <SegmentedControl
        aria-label="切换西校区或东校区"
        selectedKey={campusId}
        onSelectionChange={(key) => {
          if (key === "west" || key === "east") {
            onChange(key);
          }
        }}
      >
        <SegmentedControlItem id="west">
          {compact ? "西校" : "西校区"}
        </SegmentedControlItem>
        <SegmentedControlItem id="east">
          {compact ? "东校" : "东校区"}
        </SegmentedControlItem>
      </SegmentedControl>
    </div>
  );
}
