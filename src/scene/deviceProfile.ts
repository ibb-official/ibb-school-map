/**
 * Shared responsive layout breakpoint matching phone/tablet portrait (<= 860px)
 * and phone landscape (height <= 500px with coarse touch pointer).
 *
 * NOTE: Used strictly for UI shell layout (desktop drawers vs mobile bottom sheets).
 * Never used to throttle or cap 3D graphics quality on any device.
 */
export const MOBILE_SHELL_MEDIA_QUERY =
  "(max-width: 860px), (max-height: 500px) and (pointer: coarse)";

export function isCompactViewport(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia(MOBILE_SHELL_MEDIA_QUERY).matches;
}
