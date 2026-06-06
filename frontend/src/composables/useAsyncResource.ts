import { computed } from 'vue'
import { useAsyncState } from '@vueuse/core'
import type { UseAsyncStateOptions } from '@vueuse/core'

/**
 * Wraps VueUse's useAsyncState with a unified error extraction pattern.
 * Eliminates the boilerplate error computed duplicated across 8 pages.
 */
export function useAsyncResource<T>(
  fetcher: () => Promise<T>,
  initialValue: T | null = null,
  options: UseAsyncStateOptions<false, T | null> = {},
) {
  const { state, isLoading, error: rawError, execute } = useAsyncState(
    fetcher,
    initialValue,
    { shallow: false, ...options },
  )

  const error = computed(() => {
    const e = rawError.value as any
    return e?.userMessage || e?.response?.data?.detail || e?.message || ''
  })

  return { data: state, loading: isLoading, error, execute }
}
