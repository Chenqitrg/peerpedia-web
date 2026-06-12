import { ref, type Ref } from 'vue'

const FAILURE_THRESHOLD = 1

// Exponential backoff: after N consecutive failures, multiply the base interval.
// Server unreachability is a *normal state* in Tauri mode — we back off to
// avoid flooding the console with resource-load errors.
// Schedule: [failureThreshold, multiplier]
const BACKOFF_MULTIPLIERS: [number, number][] = [
  [3,  3],   // after  3 failures: 3× base interval
  [6, 12],   // after  6 failures: 12× base interval
  [10, 30],  // after 10 failures: 30× base interval
]

// Module-level singleton — all callers share the same isOnline state.
const isOnline: Ref<boolean> = ref(false)
let intervalId: ReturnType<typeof setInterval> | null = null
let consecutiveFailures = 0
let baseIntervalMs = 10_000
let currentIntervalMs = baseIntervalMs

// Stored at module level so _reschedule can reference the ping implementation.
let _pingImpl: (() => Promise<void>) | null = null

function _pickMultiplier(failureCount: number): number {
  let mul = 1
  for (const [threshold, m] of BACKOFF_MULTIPLIERS) {
    if (failureCount >= threshold) mul = m
  }
  return mul
}

function _reschedule(nextMs: number) {
  if (intervalId !== null && _pingImpl) {
    clearInterval(intervalId)
    intervalId = setInterval(_pingImpl, nextMs)
  }
  currentIntervalMs = nextMs
}

export function useNetworkStatus() {

  async function ping(): Promise<void> {
    // navigator.onLine is instant and free — skip fetch when browser knows
    // the network interface is down.
    if (!navigator.onLine) {
      isOnline.value = false
      return
    }
    try {
      const resp = await fetch('http://localhost:8080/health')
      if (resp.ok) {
        consecutiveFailures = 0
        // Reset to base interval on recovery.
        if (currentIntervalMs !== baseIntervalMs && intervalId !== null) {
          _reschedule(baseIntervalMs)
        }
        isOnline.value = true
      } else {
        consecutiveFailures++
        if (consecutiveFailures >= FAILURE_THRESHOLD) {
          isOnline.value = false
        }
      }
    } catch {
      consecutiveFailures++
      if (consecutiveFailures >= FAILURE_THRESHOLD) {
        isOnline.value = false
      }
    }
    // Apply backoff multiplier on failure.
    const mul = _pickMultiplier(consecutiveFailures)
    const targetMs = baseIntervalMs * mul
    if (targetMs > currentIntervalMs && intervalId !== null) {
      _reschedule(targetMs)
    }
  }

  // Store for module-level _reschedule to reference.
  _pingImpl = ping

  // Exposed for tests — reset singleton state between test cases.
  function _resetForTest() {
    isOnline.value = false
    stopPing()
    consecutiveFailures = 0
    baseIntervalMs = 10_000
    currentIntervalMs = baseIntervalMs
    _pingImpl = null
  }

  function startPing(intervalMs = 30000): void {
    if (typeof fetch === 'undefined') return
    stopPing()
    consecutiveFailures = 0
    baseIntervalMs = intervalMs
    currentIntervalMs = intervalMs
    _pingImpl = ping
    ping()
    intervalId = setInterval(ping, intervalMs)
  }

  function stopPing(): void {
    if (intervalId !== null) {
      clearInterval(intervalId)
      intervalId = null
    }
  }

  return { isOnline, startPing, stopPing, _resetForTest }
}
