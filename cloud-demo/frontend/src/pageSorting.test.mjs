import assert from 'node:assert/strict'
import { sortKnowledgePages } from './pageSorting.js'

const pages = [
  { slug: 'updated-only', title: 'B', updated: '2026-04-30' },
  { slug: 'older-import', title: 'C', updated: '2026-04-29', last_imported_at: '2026-04-29T10:05:00' },
  { slug: 'newer-import', title: 'A', updated: '2026-04-28', last_imported_at: '2026-04-30T10:05:00' },
]

assert.deepEqual(
  sortKnowledgePages(pages, 'imported_desc').map((page) => page.slug),
  ['newer-import', 'older-import', 'updated-only'],
)

assert.deepEqual(
  sortKnowledgePages(pages, 'title_asc').map((page) => page.slug),
  ['newer-import', 'updated-only', 'older-import'],
)

assert.deepEqual(
  pages.map((page) => page.slug),
  ['updated-only', 'older-import', 'newer-import'],
)
