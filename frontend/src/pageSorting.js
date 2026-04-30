function timestampValue(page) {
  return String(page.updated || page.created || '')
}

function importRank(page) {
  return [page.last_imported_at ? '1' : '0', String(page.last_imported_at || timestampValue(page))]
}

function compareText(a, b, key) {
  return String(a[key] || '').localeCompare(String(b[key] || ''), 'zh-CN')
}

export function sortKnowledgePages(pages, sortBy = 'imported_desc') {
  const sorted = pages.slice()
  switch (sortBy) {
    case 'imported_asc':
      sorted.sort((a, b) => {
        const left = importRank(a)
        const right = importRank(b)
        return right[0].localeCompare(left[0]) || left[1].localeCompare(right[1])
      })
      break
    case 'updated_desc':
      sorted.sort((a, b) => String(b.updated || '').localeCompare(String(a.updated || '')))
      break
    case 'updated_asc':
      sorted.sort((a, b) => String(a.updated || '').localeCompare(String(b.updated || '')))
      break
    case 'created_desc':
      sorted.sort((a, b) => String(b.created || '').localeCompare(String(a.created || '')))
      break
    case 'title_asc':
      sorted.sort((a, b) => compareText(a, b, 'title'))
      break
    case 'imported_desc':
    default:
      sorted.sort((a, b) => {
        const left = importRank(a)
        const right = importRank(b)
        return right[0].localeCompare(left[0]) || right[1].localeCompare(left[1])
      })
  }
  return sorted
}
