# site/: the published project page and the images the repository shares

**Reader:** anyone editing the public page at
[egorkhaklin.github.io/polaris-id](https://egorkhaklin.github.io/polaris-id/),
or looking for the logo and the Atlas captures.
**Job:** hold one copy of each published artifact, so the page and the README
can never disagree about what Polaris looks like.

`.github/workflows/pages.yml` uploads this directory as the site root on every
push that touches it. Nothing here is generated at build time: what is
committed is what is served, so opening `index.html` from a clone shows the
same page a visitor sees.

## What is here

| File | What it is | Read by |
|---|---|---|
| `index.html` | The whole page: markup, styles and content in one file | The published site |
| `tokens.css` | The design tokens, under the same names `polaris_web/static/polaris.css` uses | `index.html` |
| `404.html` | The not-found page, in the same styling | GitHub Pages |
| `robots.txt` | Crawl policy: one page, nothing private | Crawlers |
| `favicon.svg` | The tab icon | `index.html`, `404.html` |
| `polaris_logo_clean.png` | The emblem, 440 x 440, drawn at 180 to 220 CSS pixels | `index.html`, the repository `README.md` |
| `atlas-globe.png` | The Atlas at continental zoom | `index.html`, `README.md`, the Open Graph preview |
| `atlas-street.png` | The Atlas at street level | `index.html` |
| `atlas-subject.png` | Subject-focus investigation | `index.html` |

## Conventions

- One copy of every binary. The repository `README.md` links into this
  directory rather than keeping a second copy, which is how the two front
  doors stay in step.
- The captures come from the running application, at the version named in the
  README caption. Re-take all three together after any change to the Atlas
  chrome, or the page starts showing software that no longer exists.
- The captures carry notional data. The page says so in the caption, in the
  alt text, and in a badge over each figure, because the label has to survive
  a crop.
- Outbound links to repository documents are absolute `github.com/.../blob/main`
  URLs. A relative link would 404 on the published site, whose root is this
  directory.
