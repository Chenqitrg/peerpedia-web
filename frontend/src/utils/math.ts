// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

import katex from 'katex'

/** Render KaTeX math spans in compiled HTML to actual rendered math.
 *
 * Backend compilation wraps math in <span class="katex-display">$$...$$</span>
 * and <span class="katex-inline">$...$</span>. Vue's v-html strips <script>
 * tags, so the backend's renderMathInElement call never executes. Instead,
 * call this function on the HTML string before passing it to v-html.
 */
export function renderMathInHtml(html: string): string {
  let result = html
  // Display math: $$...$$
  result = result.replace(
    /<span class="katex-display">\$\$(.+?)\$\$<\/span>/gs,
    (_, tex) => {
      try {
        return katex.renderToString(tex.trim(), {
          displayMode: true,
          throwOnError: false,
        })
      } catch {
        return _
      }
    },
  )
  // Inline math: $...$
  result = result.replace(
    /<span class="katex-inline">\$(.+?)\$<\/span>/gs,
    (_, tex) => {
      try {
        return katex.renderToString(tex.trim(), {
          displayMode: false,
          throwOnError: false,
        })
      } catch {
        return _
      }
    },
  )
  return result
}
