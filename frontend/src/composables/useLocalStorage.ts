// Typed localStorage utility — the single abstraction that owns all
// localStorage access. Callers wrap in ref()/Pinia stores where reactive
// state matters; this module only provides safe serialized I/O.
//
// All functions catch and return fallback on any error (quota exceeded,
// disabled in private browsing, corrupt JSON, etc.) — never throws.

const LS = typeof window !== 'undefined' ? window.localStorage : null

// ── String ───────────────────────────────────────────────────────────────

export function loadString(key: string, fallback?: string): string | null {
  if (!LS) return fallback ?? null
  try {
    const v = LS.getItem(key)
    return v !== null ? v : (fallback ?? null)
  } catch {
    return fallback ?? null
  }
}

export function saveString(key: string, value: string): void {
  if (!LS) return
  try { LS.setItem(key, value) } catch { /* quota or private browsing */ }
}

// ── JSON ─────────────────────────────────────────────────────────────────

export function loadJSON<T>(key: string, fallback?: T): T | null {
  if (!LS) return fallback ?? null
  try {
    const raw = LS.getItem(key)
    if (raw === null) return fallback ?? null
    return JSON.parse(raw) as T
  } catch {
    return fallback ?? null
  }
}

export function saveJSON(key: string, value: unknown): void {
  if (!LS) return
  try { LS.setItem(key, JSON.stringify(value)) } catch { /* quota */ }
}

// ── Remove ───────────────────────────────────────────────────────────────

export function remove(key: string): void {
  if (!LS) return
  try { LS.removeItem(key) } catch { /* disabled */ }
}
