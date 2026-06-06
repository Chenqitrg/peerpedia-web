import { computed, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'

type ArticleStatus = 'draft' | 'sedimentation' | 'published' | string

const STATUS_LABELS: Record<string, string> = {
  published: 'Published',
  sedimentation: 'In Pool',
  draft: 'Draft',
}

const STATUS_KEYS: Record<string, string> = {
  published: 'status.published',
  sedimentation: 'status.sedimentation',
  draft: 'status.draft',
}

const STATUS_CLASSES: Record<string, string> = {
  published: 'badge-published',
  sedimentation: 'badge-sedimentation',
}

const DEFAULT_CLASS = 'badge-draft'

/**
 * Returns { label, class } for a given article status string.
 * Use useStatusLabel() for reactive i18n-aware labels.
 */
export function getStatusInfo(status: ArticleStatus): { label: string; class: string } {
  return {
    label: STATUS_LABELS[status] || status,
    class: STATUS_CLASSES[status] || DEFAULT_CLASS,
  }
}

/**
 * Returns a computed i18n-aware status label.
 * Usage: const statusLabel = useStatusLabel(articleStatus)
 */
export function useStatusLabel(status: Ref<string> | (() => string)) {
  const { t } = useI18n()
  return computed(() => {
    const s = typeof status === 'function' ? status() : status.value
    const key = STATUS_KEYS[s]
    return key ? t(key) : s
  })
}
