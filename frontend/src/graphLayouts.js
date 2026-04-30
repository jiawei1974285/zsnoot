export const GRAPH_LAYOUTS = [
  { value: 'force', label: '线索网络' },
  { value: 'type', label: '按类型分组' },
  { value: 'community', label: '按线索簇分组' },
  { value: 'radial', label: '放射布局' },
]

export function groupNodesBy(nodes, key) {
  const groups = new Map()
  nodes.forEach((node) => {
    const value = node[key] ?? 'unknown'
    if (!groups.has(value)) groups.set(value, [])
    groups.get(value).push(node)
  })
  return groups
}

export function layoutTargets(nodes, layout, width = 920, height = 520) {
  const center = { x: width / 2, y: height / 2 }
  if (!nodes.length) return new Map()

  if (layout === 'type') {
    const types = Array.from(groupNodesBy(nodes, 'type').keys())
    const columns = Math.max(types.length, 1)
    const targets = new Map()
    types.forEach((type, index) => {
      const group = nodes.filter((node) => node.type === type)
      const x = ((index + 1) * width) / (columns + 1)
      group.forEach((node, row) => {
        targets.set(node.id, {
          x,
          y: ((row + 1) * height) / (group.length + 1),
        })
      })
    })
    return targets
  }

  if (layout === 'community') {
    const communities = Array.from(groupNodesBy(nodes, 'community').keys())
    const radius = Math.min(width, height) * 0.32
    const targets = new Map()
    communities.forEach((community, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(communities.length, 1) - Math.PI / 2
      const groupCenter = {
        x: center.x + Math.cos(angle) * radius,
        y: center.y + Math.sin(angle) * radius,
      }
      nodes
        .filter((node) => node.community === community)
        .forEach((node, row, group) => {
          const innerAngle = (Math.PI * 2 * row) / Math.max(group.length, 1)
          targets.set(node.id, {
            x: groupCenter.x + Math.cos(innerAngle) * Math.min(54, 18 + group.length * 5),
            y: groupCenter.y + Math.sin(innerAngle) * Math.min(54, 18 + group.length * 5),
          })
        })
    })
    return targets
  }

  if (layout === 'radial') {
    const sorted = [...nodes].sort((a, b) => (b.linkCount || 0) - (a.linkCount || 0))
    const targets = new Map()
    sorted.forEach((node, index) => {
      if (index === 0) {
        targets.set(node.id, center)
        return
      }
      const ring = 120 + Math.floor((index - 1) / 8) * 86
      const angle = (Math.PI * 2 * (index - 1)) / Math.min(8, Math.max(sorted.length - 1, 1))
      targets.set(node.id, {
        x: center.x + Math.cos(angle) * ring,
        y: center.y + Math.sin(angle) * ring,
      })
    })
    return targets
  }

  return new Map(nodes.map((node) => [node.id, center]))
}
