// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

import { type Ref } from 'vue'
import { useUserStore } from '../stores/useUserStore'
import { saveJSON, loadJSON } from './useLocalStorage'
import { addBookmark, removeBookmark } from '../api/bookmarks'
import { getArticle } from '../api/articles'
import type { ArticleSummary } from '../api/types'

/**
 * Shared bookmark toggle logic used by HomePage, PoolPage, UserPage,
 * SearchPage, and BookmarksPage.
 */
export function useBookmarkToggle(
  articles: Ref<ArticleSummary[]>,
  onError?: (msg: string) => void,
) {
  const userStore = useUserStore()

  async function _syncBookmarkCache(viewerId: string, articleId: string, add: boolean) {
    const cacheKey = `bookmarks-${viewerId}`
    const items = loadJSON<ArticleSummary[]>(cacheKey) || []
    let filtered = items.filter(a => a.id !== articleId)
    if (add) {
      let article = articles.value.find(a => a.id === articleId)
      if (!article) {
        try {
          const detail = await getArticle(articleId)
          article = { ...detail, abstract: null, content_preview: '' } as unknown as ArticleSummary
        } catch { /* skip */ }
      }
      if (article) {
        filtered.push({ ...article, is_bookmarked: true })
      }
    }
    saveJSON(cacheKey, filtered)
  }

  async function toggle(articleId: string, currentlyBookmarked: boolean) {
    if (!userStore.viewer) return
    const article = articles.value.find(a => a.id === articleId)
    if (!article) return

    // Silently ignore self-bookmark (prevents API call).
    if (article.is_own_article) return

    const previous = article.is_bookmarked
    article.is_bookmarked = !currentlyBookmarked

    try {
      if (currentlyBookmarked) {
        await removeBookmark(articleId)
        await _syncBookmarkCache(userStore.viewer.id, articleId, false)
      } else {
        await addBookmark(articleId)
        await _syncBookmarkCache(userStore.viewer.id, articleId, true)
      }
    } catch (e: any) {
      article.is_bookmarked = previous
      if (onError) {
        onError(e.userMessage || 'Failed to update bookmark')
      }
    }
  }

  /** Remove bookmark without toggling back (for BookmarksPage) */
  async function remove(articleId: string) {
    if (!userStore.viewer) return
    try {
      await removeBookmark(articleId)
      await _syncBookmarkCache(userStore.viewer.id, articleId, false)
      const idx = articles.value.findIndex(a => a.id === articleId)
      if (idx !== -1) {
        articles.value.splice(idx, 1)
      }
    } catch (e: any) {
      if (onError) {
        onError(e.userMessage || 'Failed to remove bookmark')
      }
    }
  }

  return { toggle, remove }
}
