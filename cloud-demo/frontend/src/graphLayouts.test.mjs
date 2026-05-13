import assert from 'node:assert/strict'
import { layoutTargets } from './graphLayouts.js'

const nodes = [
  { id: 'case-a', type: 'cases', community: 0, linkCount: 4 },
  { id: 'person-a', type: 'persons', community: 0, linkCount: 2 },
  { id: 'place-a', type: 'locations', community: 1, linkCount: 1 },
]

const typeTargets = layoutTargets(nodes, 'type', 900, 450)
assert.equal(typeTargets.size, 3)
assert.notEqual(typeTargets.get('case-a').x, typeTargets.get('person-a').x)

const communityTargets = layoutTargets(nodes, 'community', 900, 450)
assert.equal(communityTargets.size, 3)
assert.ok(Math.abs(communityTargets.get('case-a').x - communityTargets.get('person-a').x) < 160)

const radialTargets = layoutTargets(nodes, 'radial', 900, 450)
assert.deepEqual(radialTargets.get('case-a'), { x: 450, y: 225 })

console.log('graph layout tests passed')
