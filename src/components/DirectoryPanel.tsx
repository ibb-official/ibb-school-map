"use client";

import { ActionButton } from "@react-spectrum/s2/ActionButton";
import { CloseButton } from "@react-spectrum/s2/CloseButton";
import { SearchField } from "@react-spectrum/s2/SearchField";
import { CATEGORY_COLORS, CATEGORY_LABELS } from "@/data/places";
import { CampusMeta, CampusPlace, PlaceCategory } from "@/data/types";

interface DirectoryPanelProps {
  campus: CampusMeta;
  allPlacesCount: number;
  places: CampusPlace[];
  searchQuery: string;
  activeCategory: PlaceCategory | "all";
  selectedPlaceId: string | null;
  onSearchChange: (q: string) => void;
  onCategoryChange: (cat: PlaceCategory | "all") => void;
  onSelectPlace: (placeId: string) => void;
  onClose: () => void;
  embedded?: boolean;
}

export function DirectoryPanel({
  campus,
  allPlacesCount,
  places,
  searchQuery,
  activeCategory,
  selectedPlaceId,
  onSearchChange,
  onCategoryChange,
  onSelectPlace,
  onClose,
  embedded = false,
}: DirectoryPanelProps) {
  const inner = (
    <>
      <div className="dir-header">
        <div className="dir-title-row">
          <div>
            <h2 className="dir-title">{campus.name}</h2>
            <p className="dir-address">{campus.address}</p>
          </div>
          <CloseButton size="S" onPress={onClose} />
        </div>

        <SearchField
          aria-label="搜索建筑编号或名称"
          placeholder="搜索建筑或地点（如 B座、坡道、篮球场）"
          size="M"
          value={searchQuery}
          onChange={onSearchChange}
          UNSAFE_style={{ width: "100%" }}
        />

        <div className="dir-cat-row" role="group" aria-label="按建筑类别筛选">
          <ActionButton
            size="XS"
            isQuiet={activeCategory !== "all"}
            onPress={() => onCategoryChange("all")}
          >
            全部 ({allPlacesCount})
          </ActionButton>
          {(Object.keys(CATEGORY_LABELS) as PlaceCategory[]).map((cat) => (
            <ActionButton
              key={cat}
              size="XS"
              isQuiet={activeCategory !== cat}
              onPress={() => onCategoryChange(cat)}
            >
              {CATEGORY_LABELS[cat]}
            </ActionButton>
          ))}
        </div>
      </div>

      <div className="dir-list">
        {places.length === 0 ? (
          <div className="dir-empty">未找到匹配的建筑或地标</div>
        ) : (
          places.map((place) => {
            const active = place.id === selectedPlaceId;
            return (
              <button
                key={place.id}
                type="button"
                className={`dir-item-btn${active ? " dir-item-btn-active" : ""}`}
                onClick={() => onSelectPlace(place.id)}
              >
                <span
                  className="place-code-pill"
                  style={{ backgroundColor: CATEGORY_COLORS[place.category] }}
                >
                  {place.code}
                </span>
                <div className="dir-item-copy">
                  <div className="dir-item-name">{place.name}</div>
                  <div className="dir-item-meta">
                    {place.storiesLabel}
                    {place.photoRefs.length > 0
                      ? ` · 实拍照片 ×${place.photoRefs.length}`
                      : ""}
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </>
  );

  if (embedded) {
    return <div className="dir-sheet-wrap">{inner}</div>;
  }

  return (
    <aside className="hud-drawer hud-drawer-left" aria-label="校园建筑与景观目录">
      {inner}
    </aside>
  );
}
