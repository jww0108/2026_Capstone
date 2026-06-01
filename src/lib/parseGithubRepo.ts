const GITHUB_USERNAME_RE = /^[a-zA-Z0-9-]{1,39}$/
const GITHUB_REPO_RE = /^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+(\/tree\/[a-zA-Z0-9_./-]+)?$/

export function isValidGithubUsername(username: string): boolean {
  return GITHUB_USERNAME_RE.test(username.trim())
}

export function parseGithubRepoInput(input: string): string | null {
  const trimmed = input.trim()
  if (!trimmed) return null

  if (GITHUB_REPO_RE.test(trimmed)) {
    return trimmed
  }

  try {
    const url = trimmed.startsWith("http") ? new URL(trimmed) : new URL(`https://${trimmed}`)
    if (!url.hostname.replace(/^www\./, "").endsWith("github.com")) {
      return null
    }

    const parts = url.pathname.split("/").filter(Boolean)
    if (parts.length < 2) return null

    const [owner, repo, ...rest] = parts
    if (rest[0] === "tree" && rest.length >= 2) {
      const branchPath = rest.slice(1).join("/")
      const path = `${owner}/${repo}/tree/${branchPath}`
      return GITHUB_REPO_RE.test(path) ? path : null
    }

    const path = `${owner}/${repo}`
    return GITHUB_REPO_RE.test(path) ? path : null
  } catch {
    return null
  }
}

export function parseGithubRepoInputs(inputs: string[]): { repos: string[]; errors: string[] } {
  const repos: string[] = []
  const errors: string[] = []

  for (const input of inputs) {
    const trimmed = input.trim()
    if (!trimmed) continue
    const parsed = parseGithubRepoInput(trimmed)
    if (parsed) {
      repos.push(parsed)
    } else {
      errors.push(`유효하지 않은 레포 URL 또는 경로: ${trimmed}`)
    }
  }

  return { repos, errors }
}
