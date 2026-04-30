export function normalizeKnowledgeSources(sources = []) {
  return sources
    .filter((source) => source && source.slug && source.type)
    .map((source) => ({
      slug: String(source.slug),
      type: String(source.type),
      title: String(source.title || source.slug),
    }))
}
