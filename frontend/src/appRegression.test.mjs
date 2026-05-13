import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./App.vue', import.meta.url), 'utf8')

function extractFunction(name) {
  const marker = `function ${name}(`
  const start = source.indexOf(marker)
  if (start === -1) {
    throw new Error(`${name} function not found`)
  }
  let depth = 0
  let bodyStart = -1
  for (let i = start; i < source.length; i += 1) {
    const ch = source[i]
    if (ch === '{') {
      depth += 1
      if (bodyStart === -1) bodyStart = i
    } else if (ch === '}') {
      depth -= 1
      if (bodyStart !== -1 && depth === 0) {
        return source.slice(start, i + 1)
      }
    }
  }
  throw new Error(`${name} function body not found`)
}

const setActiveView = extractFunction('setActiveView')
if (!setActiveView.includes("view === 'graph'") || !setActiveView.includes('loadGraph()')) {
  throw new Error('setActiveView must load graph data when opening the graph view')
}
if (!setActiveView.includes("view === 'config'") || !setActiveView.includes('loadInvites()')) {
  throw new Error('setActiveView must load admin invites when opening the config view')
}

const sparkPoints = extractFunction('sparkPoints')
if (!/days\.length\s*===\s*1|days\.length\s*<\s*2/.test(sparkPoints)) {
  throw new Error('sparkPoints must handle a single activity day without dividing by zero')
}

if (!source.includes('recent_notes: []')) {
  throw new Error('homeStats must initialize recent_notes for note activity feed data')
}

const homeFeedIndex = source.indexOf('const homeFeedItems = computed')
if (homeFeedIndex === -1 || !source.slice(homeFeedIndex, homeFeedIndex + 2200).includes('homeStats.value.recent_notes')) {
  throw new Error('homeFeedItems must include recent notes from /api/stats')
}

if (!source.includes('function openNoteFromHome')) {
  throw new Error('homepage note activity items must open the source note')
}
