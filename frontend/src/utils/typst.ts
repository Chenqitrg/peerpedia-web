/**
 * Sanitize Typst-compiled SVG for dark-theme display.
 * - Strips root width/height attrs so CSS can drive responsive sizing
 * - Strips Typst's full-page white background shape (the page rectangle).
 *   Typst renders this as <path class="typst-shape" fill="#ffffff" d="M 0 0v …"/>.
 *
 * NOTE: this only affects the inline SVG preview. PDF output (compiled
 * separately via `typst compile --format pdf`) is never touched.
 */
export function sanitizeTypstSvg(svg: string): string {
  return svg
    // Remove root SVG width/height attributes for responsive sizing.
    // Keep viewBox so the SVG scales proportionally.
    .replace(/<svg([^>]*?)>/i, (_, attrs: string) => {
      const cleaned = attrs
        .replace(/\s+width\s*=\s*"[^"]*"/i, '')
        .replace(/\s+height\s*=\s*"[^"]*"/i, '')
      return `<svg${cleaned}>`
    })
    // Remove Typst's page background — a <path> with class="typst-shape"
    // and a white fill. It is always the first element after <svg> and
    // draws the full page rectangle via path commands.
    .replace(
      /<path\b[^>]*\bclass\s*=\s*["']typst-shape["'][^>]*\bfill\s*=\s*["']\s*#(?:fff(?:fff)?|FFF(?:FFF)?)\s*["'][^>]*\/>/g,
      '',
    )
    // Fallback: remove any <rect> with white fill (older Typst versions,
    // or alternative SVG generators).
    .replace(
      /<rect\b[^>]*\bfill\s*=\s*["']\s*(?:white|#fff(?:fff)?|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))\s*["'][^>]*\/?>\s*(?:<\/rect>)?/gi,
      '',
    )
}
