import assert from 'node:assert/strict'
import { normalizeKnowledgeSources } from './chatSources.js'

assert.deepEqual(
  normalizeKnowledgeSources([
    { slug: 'case-a', type: 'cases', title: 'Case A' },
    { title: 'No Link' },
    null,
  ]),
  [{ slug: 'case-a', type: 'cases', title: 'Case A' }],
)
