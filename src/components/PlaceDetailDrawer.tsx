"use client";

import { useState } from "react";
import { ActionButton } from "@react-spectrum/s2/ActionButton";
import { Badge } from "@react-spectrum/s2/Badge";
import { Button, Text } from "@react-spectrum/s2/Button";
import { CloseButton } from "@react-spectrum/s2/CloseButton";
import { Content, Dialog, DialogContainer, Heading } from "@react-spectrum/s2/Dialog";
import { Divider } from "@react-spectrum/s2/Divider";
import ChevronDown from "@react-spectrum/s2/icons/ChevronDown";
import ChevronUp from "@react-spectrum/s2/icons/ChevronUp";
import Location from "@react-spectrum/s2/icons/Location";
import { CATEGORY_COLORS, CATEGORY_LABELS } from "@/data/places";
import { CampusPlace, PhotoReference } from "@/data/types";
import { MobileBottomSheet, SheetSnap } from "./MobileBottomSheet";

interface PlaceDetailDrawerProps {
  place: CampusPlace;
  isMobileShell?: boolean;
  mobileSnap?: SheetSnap;
  onMobileSnapChange?: (next: SheetSnap) => void;
  onClose: () => void;
  onFocus3D: (place: CampusPlace) => void;
}

export function PlaceDetailDrawer({
  place,
  isMobileShell = false,
  mobileSnap = "peek",
  onMobileSnapChange,
  onClose,
  onFocus3D,
}: PlaceDetailDrawerProps) {
  const [lightboxPhoto, setLightboxPhoto] = useState<PhotoReference | null>(null);

  const detailContent = (
    <div className="detail-sections">
      <Button
        variant="accent"
        size="M"
        UNSAFE_style={{ width: "100%" }}
        onPress={() => {
          onFocus3D(place);
          if (isMobileShell && onMobileSnapChange) {
            onMobileSnapChange("peek");
          }
        }}
      >
        <Location />
        <Text>飞至最佳 3D 观赏机位</Text>
      </Button>

      <section className="detail-section">
        <h3 className="detail-section-title">建筑概览</h3>
        <p className="detail-paragraph">{place.summary}</p>
      </section>

      <Divider size="S" />

      <section className="detail-section">
        <h3 className="detail-section-title">实景建模特征</h3>
        <ul className="detail-feature-list">
          {place.architecturalFeatures.map((feat, idx) => (
            <li key={idx}>{feat}</li>
          ))}
        </ul>
      </section>

      {place.historicalNote && (
        <section className="detail-history-callout">
          <div className="detail-history-title">校园人文脉络（公开文献）</div>
          <p className="detail-history-text">{place.historicalNote}</p>
        </section>
      )}

      <Divider size="S" />

      <section className="detail-section">
        <h3 className="detail-section-title">真实摄影对照存档</h3>
        {place.photoRefs.length === 0 ? (
          <p className="detail-empty-photos">
            该点位三维形态与色彩已依据 OSM 实测矢量轮廓与 Zoom-19 航拍正射影像校准；公开地面摄影资料持续补充中。
          </p>
        ) : (
          <div className="detail-photo-stack">
            {place.photoRefs.map((photo) => (
              <figure key={photo.src} className="detail-photo-card">
                <button
                  type="button"
                  className="detail-photo-trigger"
                  onClick={() => setLightboxPhoto(photo)}
                  aria-label={`放大查看照片：${photo.caption}`}
                >
                  <img
                    src={photo.src}
                    alt={photo.caption}
                    loading="lazy"
                    className="detail-photo-img"
                  />
                </button>
                <figcaption className="detail-photo-caption">
                  <div className="detail-photo-title">{photo.caption}</div>
                  <div className="detail-photo-meta">
                    拍摄年份：{photo.year} · 来源：{photo.sourceLabel}
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>
        )}
      </section>
    </div>
  );

  const photoLightbox = (
    <DialogContainer onDismiss={() => setLightboxPhoto(null)}>
      {lightboxPhoto && (
        <Dialog isDismissible size="L">
          <Heading slot="title">{lightboxPhoto.caption}</Heading>
          <Content>
            <img
              src={lightboxPhoto.src}
              alt={lightboxPhoto.caption}
              className="lightbox-photo-img"
            />
            <p className="detail-photo-meta" style={{ marginTop: "10px" }}>
              拍摄年份：{lightboxPhoto.year} · 来源：{lightboxPhoto.sourceLabel}
            </p>
          </Content>
        </Dialog>
      )}
    </DialogContainer>
  );

  if (isMobileShell) {
    const isExpanded = mobileSnap === "expanded";

    const sheetHeader = (
      <div className="place-sheet-header">
        <div
          className="place-sheet-title-area"
          onClick={() => onMobileSnapChange?.(isExpanded ? "peek" : "expanded")}
        >
          <div className="place-badge-row">
            <span
              className="place-code-pill"
              style={{ backgroundColor: CATEGORY_COLORS[place.category] }}
            >
              {place.code}
            </span>
            <Badge variant="neutral" fillStyle="subtle" size="S">
              {CATEGORY_LABELS[place.category]}
            </Badge>
            {place.photoRefs.length > 0 && (
              <Badge variant="informative" fillStyle="subtle" size="S">
                实拍 ×{place.photoRefs.length}
              </Badge>
            )}
          </div>
          <h2 className="detail-place-name">{place.name}</h2>
          <p className="detail-place-sub">{place.storiesLabel}</p>
        </div>

        <div className="place-sheet-actions">
          <ActionButton
            isQuiet
            size="S"
            onPress={() => onMobileSnapChange?.(isExpanded ? "peek" : "expanded")}
            aria-label={isExpanded ? "收起为摘要" : "展开完整详情"}
          >
            {isExpanded ? <ChevronDown /> : <ChevronUp />}
          </ActionButton>
          <CloseButton size="S" onPress={onClose} />
        </div>
      </div>
    );

    const peekContent = (
      <div className="place-peek-actions">
        <Button variant="accent" size="M" onPress={() => onFocus3D(place)}>
          <Location />
          <Text>最佳 3D 视角</Text>
        </Button>
        <Button
          variant="secondary"
          fillStyle="outline"
          size="M"
          onPress={() => onMobileSnapChange?.("expanded")}
        >
          详情与实拍图
        </Button>
      </div>
    );

    return (
      <>
        <MobileBottomSheet
          open
          onClose={onClose}
          ariaLabel={`${place.name} 详情面板`}
          variant="two-stage"
          snap={mobileSnap}
          onSnapChange={onMobileSnapChange}
          modalBackdrop
          header={sheetHeader}
          peekContent={peekContent}
        >
          <div className="detail-scroll-body">{detailContent}</div>
        </MobileBottomSheet>
        {photoLightbox}
      </>
    );
  }

  return (
    <>
      <aside className="hud-drawer hud-drawer-right" aria-label={`${place.name} 详情面板`}>
        <div className="detail-header">
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="place-badge-row">
              <span
                className="place-code-pill"
                style={{ backgroundColor: CATEGORY_COLORS[place.category] }}
              >
                {place.code}
              </span>
              <Badge variant="neutral" fillStyle="subtle" size="S">
                {CATEGORY_LABELS[place.category]}
              </Badge>
            </div>
            <h2 className="detail-place-name">{place.name}</h2>
            <p className="detail-place-sub">
              {place.storiesLabel} · ENU ({place.enu[0].toFixed(1)}m, {place.enu[1].toFixed(1)}m)
            </p>
          </div>
          <CloseButton size="S" onPress={onClose} />
        </div>

        <div className="detail-scroll-body">{detailContent}</div>
      </aside>
      {photoLightbox}
    </>
  );
}
