# VSCode-Style Tab System Design

> 2026-06-09 · Multi-tab editing for simultaneous article writing and reading

## 1. Problem

Currently, PeerPedia's editor supports only one article at a time. When an author is writing and needs to reference another article, or wants to work on multiple articles simultaneously, they must navigate away from the editor — losing context and risking unsaved work.

**Goal:** VSCode-like tab-based navigation where authors can open multiple editor/article tabs simultaneously, switch between them without losing state, and only lose unsaved work when explicitly closing a tab.

## 2. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tab scope | Editor + Article pages | Covers the reference-while-writing workflow |
| URL behavior | URL follows active tab | Enables refresh recovery, bookmarking, and shareable URLs |
| Close dirty tab | Confirm dialog (Save / Discard / Cancel) | Matches VSCode behavior |
| Tab bar position | Below NavBar | Closest to VSCode's toolbar+tab layout |
| Browser back/forward | Switch tab history | Matches browser tab mental model |

## 3. Architecture

```
App.vue
├── NavBar              (existing, unchanged)
├── TabBar 🆕            VSCode-style tab bar
└── <router-view>        KeepAlive caches EditorPage + ArticlePage
    ├── EditorPage       (one cached instance per articleId)
    ├── ArticlePage      (one cached instance per articleId)
    └── Other pages      (not cached, no tabs)
```

## 4. Data Model

```typescript
interface Tab {
  id: string         // equals routePath, e.g. "/edit/abc123"
  type: "editor" | "article"
  title: string      // article title or "Untitled"
  dirty: boolean     // unsaved changes dot (editor only)
  icon: "edit" | "eye"
}
```

Tabs are managed in a Pinia store (`useTabStore`). The store is the single source of truth for which tabs are open. Each tab's `id` is its route path — this guarantees uniqueness and makes lookup O(1).

## 5. Tab Lifecycle

```
OPEN:   click link → router.push → tabStore.openTab(route) → add or activate
SWITCH: click tab  → router.push → KeepAlive activates cached component
CLOSE:  click × →
        ├─ dirty=true  → switch to tab → confirm dialog → save/discard → close
        └─ dirty=false → close immediately → navigate to adjacent tab
REFRESH: localStorage restore → rebuild tab list → navigate to last active
```

## 6. Files Changed

### 6.1 New: `frontend/src/stores/useTabStore.ts`

Pinia store. Public API:

```
openTab(route)          // add tab or activate existing
closeTab(tabId)         // remove tab, handle dirty state
activateTab(tabId)      // router.push to tab's route
updateTab(tabId, patch) // update title/dirty on existing tab
restoreTabs()           // load from localStorage on app mount
```

Fields: `tabs: Tab[]`, `activeTabId: string`.

Persists tab list (metadata only, no content) to localStorage on every mutation. Content is restored separately via existing `useDraftPersistence` on component mount.

### 6.2 New: `frontend/src/components/TabBar.vue`

VSCode-style horizontal tab bar. Visual spec:

```
┌──────────────────────────────────────────────────────────────┐
│  NavBar                                              [avatar]│
├──────────────────────────────────────────────────────────────┤
│  ● edit: Untitled   │  👁 量子力学导论   │  ● edit: 相对论   │
├──────────────────────────────────────────────────────────────┤
│  [editor / article content]                                  │
```

- Each tab: icon (lucide) + title text + dirty dot (●) + close button (× on hover)
- Active tab: `bg-card` highlight + bottom border accent
- Inactive tabs: muted, no bottom border
- Scrollable horizontally if too many tabs (`overflow-x-auto`)
- Dirty dot replaces close button icon when visible; close button shows on hover
- Close button click → emit `close-tab` event with tab id

Props: none (reads from `useTabStore` directly).
Emits: `close-tab(tabId)`.

### 6.3 Modified: `frontend/src/App.vue`

Changes:

1. **Import and render TabBar** between NavBar and `<main>`, only when `tabStore.tabs.length > 0`
2. **Expand KeepAlive**: `:include="['EditorPage', 'ArticlePage']"` (was `"EditorPage"` only)
3. **Adjust main layout**: when tabs are visible, add a subtle border between TabBar and content area
4. **Restore tabs on mount**: call `tabStore.restoreTabs()` in `onMounted`

No changes to NavBar, AuthModal, or other layout elements.

### 6.4 Modified: `frontend/src/pages/EditorPage.vue`

Changes:

1. **Register tab on mount**: `tabStore.openTab(route)` to register this editor as a tab
2. **Sync dirty state**: watch `isClean` → `tabStore.updateTab(route.fullPath, { dirty: !clean, title })`
3. **Support close-with-save flow**: when EditorPage is activated as part of a dirty-close flow, show confirmation dialog. Three buttons:
   - "Save & Close" → `saveDraft()` → `tabStore.closeTab(id)`
   - "Discard" → `tabStore.closeTab(id)`
   - "Cancel" → dismiss dialog, stay on tab

   This dialog matches the existing commit popup pattern (positioned near the save button).
4. **On unmount/beforeRouteLeave**: do NOT auto-save. The user's explicit save action is the only path to persistence.

### 6.5 Modified: `frontend/src/pages/ArticlePage.vue`

Changes:

1. **Register tab on mount**: `tabStore.openTab(route)` if the route matches `/article/:id`
2. **Update title**: when article loads, `tabStore.updateTab(route.fullPath, { title: article.title })`
3. **Clean up on unmount** (if navigated away normally): no cleanup needed — tabs only close via explicit × click

### 6.6 No Changes

- **NavBar.vue** — all navigation links already use `router.push`, which automatically triggers `openTab` via `router.afterEach` hook
- **Router config** — no route changes needed; tab tracking is done in a navigation guard
- **useDraftPersistence** — unchanged; each EditorPage instance uses it independently

## 7. Navigation Guard

A single `router.afterEach` hook in `useTabStore` (registered on app init) intercepts navigation to tab-tracked routes:

```typescript
router.afterEach((to) => {
  if (to.path.startsWith('/edit') || to.path.startsWith('/article')) {
    tabStore.openTab(to)
  }
})
```

This ensures ALL paths to these pages (NavBar clicks, router-link, programmatic push) automatically create tabs.

## 8. Refresh Recovery

On app mount:

1. `tabStore.restoreTabs()` reads `peerpedia_tabs` from localStorage
2. Reconstructs `Tab[]` (id, type, title — no dirty state, all assumed clean)
3. Navigates to the last active tab's route
4. Each EditorPage/ArticlePage component loads its content independently via existing `onMounted` logic (draft persistence or API fetch)

Caveat: unsaved content in editor tabs that were dirty before refresh IS preserved because `useDraftPersistence` saves to localStorage/Tauri SQLite on every content change. The dirty indicator itself resets on refresh (acceptable tradeoff for simplicity).

## 9. Edge Cases

| Scenario | Behavior |
|----------|----------|
| Open same article twice | Activate existing tab (no duplicate) |
| Close last tab | Navigate to `/` (home), hide TabBar |
| Close only tab with unsaved changes | Same confirm flow; after close → home |
| Navigate away via browser back | Switch to previous tab (not close) |
| Navigate to non-tab page (home, search, pool) | TabBar stays visible; active tab loses highlight |
| Tauri offline mode | All tab state is local; no server dependency |
| Very long title | Truncate with ellipsis at ~20 chars |
| Too many tabs (>10) | Horizontal scroll; no tab minimum width below 120px |

## 10. Non-Goals (Out of Scope)

- Tab drag-and-drop reordering (future)
- Tab context menu (close others, close all, close to right)
- Split panes for side-by-side editing (separate feature)
- Tab groups / pinned tabs
- Ctrl+Tab quick switcher (future)

## 11. Verification

1. **Open multiple tabs**: Navigate to /edit → type content → click article link in NavBar → verify both appear as tabs
2. **Switch without loss**: Type in editor tab → switch to article tab → switch back → content preserved
3. **Dirty indicator**: Edit content without saving → verify dirty dot appears on editor tab → switch away → dot remains
4. **Close clean tab**: × on article tab → tab closes, adjacent tab activates
5. **Close dirty tab**: × on dirty editor tab → confirm dialog appears → "Save & Close" saves draft and closes → "Discard" closes without saving
6. **Refresh recovery**: Open 3 tabs → refresh browser → all 3 tabs restored, last active tab focused
7. **Existing tests**: All EditorPage and ArticlePage unit tests still pass (tab store is mocked)
8. **Manual**: `cd frontend && npm run dev`, open multiple tabs, verify all behaviors above
