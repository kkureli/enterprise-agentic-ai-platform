import { GITHUB_REPO_URL, LINKEDIN_PROFILE_URL } from '../lib/portfolioLinks'

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M12 2C6.477 2 2 6.586 2 12.253c0 4.53 2.865 8.37 6.839 9.722.5.094.682-.222.682-.493 0-.243-.009-.888-.014-1.743-2.782.617-3.369-1.38-3.369-1.38-.455-1.183-1.11-1.498-1.11-1.498-.908-.637.069-.624.069-.624 1.004.072 1.532 1.057 1.532 1.057.892 1.568 2.341 1.115 2.91.853.091-.664.35-1.115.636-1.372-2.22-.259-4.555-1.143-4.555-5.087 0-1.124.39-2.043 1.029-2.764-.103-.26-.446-1.302.098-2.714 0 0 .84-.276 2.75 1.055A9.34 9.34 0 0 1 12 6.844a9.34 9.34 0 0 1 2.504.346c1.909-1.331 2.748-1.055 2.748-1.055.546 1.412.202 2.454.1 2.714.64.721 1.028 1.64 1.028 2.764 0 3.954-2.339 4.825-4.566 5.079.359.317.679.943.679 1.901 0 1.372-.013 2.478-.013 2.815 0 .274.18.593.688.492C19.138 20.62 22 16.78 22 12.253 22 6.586 17.523 2 12 2z"
      />
    </svg>
  )
}

function LinkedInIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M20.447 20.452H16.89v-5.569c0-1.328-.025-3.037-1.852-3.037-1.853 0-2.136 1.447-2.136 2.942v5.664H9.351V9h3.414v1.561h.047c.476-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a1.99 1.99 0 1 1 0-3.98 1.99 1.99 0 0 1 0 3.98zM7.119 20.452H3.552V9h3.567v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
      />
    </svg>
  )
}

export function HeaderSocialLinks() {
  return (
    <nav className="header-social" aria-label="Portfolio links">
      <a
        className="header-social__link"
        href={GITHUB_REPO_URL}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="View project on GitHub"
      >
        <GitHubIcon />
      </a>
      <a
        className="header-social__link"
        href={LINKEDIN_PROFILE_URL}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="View LinkedIn profile"
      >
        <LinkedInIcon />
      </a>
    </nav>
  )
}
