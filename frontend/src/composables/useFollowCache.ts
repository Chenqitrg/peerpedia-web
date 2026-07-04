// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

// Offline cache for follow data using localStorage.
// Cache keys are namespaced and never collide with real article UUIDs.

import { getFeedCache } from '../api/feed'
import type { FeedCacheResponse } from '../api/feed'
import type { ArticleDetail, ArticleSource, ArticleSummary, UserProfile, UserSummary } from '../api/types'

const FOLLOW_IDS_PREFIX = '_follow_ids_'
const COUNTS_PREFIX = '_counts_'
const FOLLOWING_USERS_PREFIX = '_following_users_'
const FEED_PREFIX = '_feed_'
const USER_ARTICLES_PREFIX = '_user_articles_'
const USER_PROFILE_PREFIX = '_user_profile_'
const ARTICLE_PREFIX = '_article_'

function idsKey(userId: string): string { return `${FOLLOW_IDS_PREFIX}${userId}` }
function countsKey(userId: string): string { return `${COUNTS_PREFIX}${userId}` }
function followingUsersKey(userId: string): string { return `${FOLLOWING_USERS_PREFIX}${userId}` }
function feedKey(userId: string): string { return `${FEED_PREFIX}${userId}` }
function userArticlesKey(userId: string): string { return `${USER_ARTICLES_PREFIX}${userId}` }
function articleKey(articleId: string): string { return `${ARTICLE_PREFIX}${articleId}` }

function getItem<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) as T : null
  } catch { return null }
}

function setItem(key: string, value: unknown): void {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* quota exceeded, ignore */ }
}

export function useFollowCache() {

  async function refreshCache(userId: string): Promise<void> {
    try {
      const data: FeedCacheResponse = await getFeedCache()

      setItem(idsKey(userId), {
        ids: data.following_ids,
        cached_at: new Date().toISOString(),
      })

      setItem(countsKey(userId), {
        following: data.following_ids.length,
        cached_at: new Date().toISOString(),
      })

      const articles = data.articles.map(a => ({
        id: a.id, title: a.title, status: a.status, authors: a.authors,
        commit_hash: a.commit_hash, fork_count: a.fork_count,
        forked_from: a.forked_from, score: a.score, created_at: a.created_at,
      }))
      setItem(feedKey(userId), { articles, cached_at: new Date().toISOString() })
    } catch { /* fire-and-forget */ }
  }

  async function getCachedFollowingIds(userId: string): Promise<string[] | null> {
    const parsed = getItem<{ ids: string[] }>(idsKey(userId))
    return parsed?.ids ? parsed.ids : null
  }

  async function getCachedCounts(userId: string): Promise<{ follower?: number; following?: number } | null> {
    return getItem(idsKey(userId)) ? getItem(countsKey(userId)) : null
  }

  async function setCachedCounts(userId: string, counts: { follower?: number; following?: number }): Promise<void> {
    setItem(countsKey(userId), { ...counts, cached_at: new Date().toISOString() })
  }

  async function getCachedFollowingUsers(_userId: string): Promise<UserSummary[] | null> {
    return getItem<UserSummary[]>(followingUsersKey(_userId))
  }

  async function setCachedFollowingUsers(userId: string, users: UserSummary[]): Promise<void> {
    setItem(followingUsersKey(userId), { users, cached_at: new Date().toISOString() })
  }

  async function getCachedFeed(userId: string): Promise<FeedCacheResponse['articles'] | null> {
    const parsed = getItem<{ articles: FeedCacheResponse['articles'] }>(feedKey(userId))
    return parsed?.articles ? parsed.articles : null
  }

  async function getCachedUserArticles(userId: string): Promise<ArticleSummary[] | null> {
    const parsed = getItem<{ articles: ArticleSummary[] }>(userArticlesKey(userId))
    return parsed?.articles ? parsed.articles : null
  }

  async function setCachedUserArticles(userId: string, articles: ArticleSummary[]): Promise<void> {
    setItem(userArticlesKey(userId), { articles, cached_at: new Date().toISOString() })
  }

  async function getCachedUserProfile(userId: string): Promise<UserProfile | null> {
    return getItem<UserProfile>(`${USER_PROFILE_PREFIX}${userId}`)
  }

  async function setCachedUserProfile(userId: string, profile: UserProfile): Promise<void> {
    setItem(`${USER_PROFILE_PREFIX}${userId}`, { ...profile, cached_at: new Date().toISOString() })
  }

  async function getCachedArticle(articleId: string): Promise<{ detail: ArticleDetail; source: ArticleSource } | null> {
    const parsed = getItem<{ detail: ArticleDetail; source: ArticleSource }>(articleKey(articleId))
    return parsed?.detail ? parsed : null
  }

  async function setCachedArticle(articleId: string, detail: ArticleDetail, source: ArticleSource): Promise<void> {
    setItem(articleKey(articleId), { detail, source, cached_at: new Date().toISOString() })
  }

  return {
    refreshCache,
    getCachedFollowingIds,
    getCachedCounts,
    setCachedCounts,
    getCachedFollowingUsers,
    setCachedFollowingUsers,
    getCachedFeed,
    getCachedUserArticles,
    setCachedUserArticles,
    getCachedUserProfile,
    setCachedUserProfile,
    getCachedArticle,
    setCachedArticle,
  }
}
