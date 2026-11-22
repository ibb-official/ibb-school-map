/**
 * Local no-op replacement for `@react-spectrum/s2`'s external Typekit font loader.
 * Prevents 49 CSP-blocked requests to `use.typekit.net` on every page load while
 * relying on crisp local CJK / system UI font stacks defined in `globals.css`.
 */
export function Fonts() {
  return null;
}
