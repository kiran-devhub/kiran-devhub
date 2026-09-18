# Setup guide

This repo is a GitHub **profile README** repository. Everything below assumes you're
setting it up for the account `kiran-devhub`.

## 1. Create the special repository

GitHub only turns a README into a profile page if the repo is named **exactly** your
username.

1. On GitHub, create a new repository named `kiran-devhub` (must match the username
   exactly, case-insensitive).
2. Make it **public**.
3. Push the contents of this folder to it as the `main` branch:

   ```bash
   git init
   git remote add origin https://github.com/kiran-devhub/kiran-devhub.git
   git checkout -b main
   git add .
   git commit -m "init: profile dashboard"
   git push -u origin main
   ```

4. Visit `https://github.com/kiran-devhub` — the README should render as your profile
   page immediately.

## 2. Enable the refresh workflow

The repo ships with [`.github/workflows/profile.yml`](.github/workflows/profile.yml),
which refreshes the live stats/language/radar cards daily and commits any changes.

1. Go to your repo's **Settings → Actions → General**.
2. Under "Workflow permissions", select **Read and write permissions** (the workflow
   needs this to commit updated SVGs back to `main`).
3. Go to the **Actions** tab and manually run **"Refresh profile assets"** once to
   confirm it works (Actions → Refresh profile assets → Run workflow).

No extra secrets are required — the workflow uses the automatically-provided
`secrets.GITHUB_TOKEN`, which is enough to call the public GitHub REST API endpoints
`scripts/cards.py` and `scripts/languages.py` use.

If the very first run shows "live stats unavailable" placeholder cards, that's usually
just the default token's rate limit on a brand-new repo — re-run the workflow a minute
later, or check the Action's log output for the actual HTTP error.

## 3. Customize your content

| What | Where | How |
|---|---|---|
| Name, role, focus, location, status | `scripts/banner/generate.py` → `info_lines` | Edit the tuples, then `python3 scripts/banner/generate.py` |
| Full skills lists + radar levels | `assets/skills.json` | Edit, then `python3 scripts/radar.py` |
| Featured repositories | `assets/projects.json` **and** the repo names hardcoded in the "Featured repositories" section of `README.md` | Replace `REPLACE_WITH_REAL_REPO_*` in both places |
| Quick links (GitHub/portfolio/email) | `scripts/banner/generate.py` → `links` list | Edit the `(label, href, icon)` tuples, then regenerate |
| Portrait photo | `assets/source/kiran.png` | Swap the file (same crop framing assumptions — see below), then regenerate |

### Regenerating the banner after changing the photo

```bash
pip install -r scripts/banner/requirements.txt
python3 scripts/banner/generate.py
```

This rewrites `assets/banner-dark.svg` and `assets/banner-light.svg`. If your
replacement photo is framed very differently (face not roughly centered, much more or
less headroom), open `scripts/banner/generate.py` and adjust `CROP_BOX` — it's a
`(left, top, right, bottom)` pixel box against your *source* image's own resolution.
A quick way to find good numbers: crop your image in any image editor first, note the
box you used, and translate that back to pixel coordinates.

### Regenerating everything at once

```bash
python3 scripts/banner/generate.py
python3 scripts/radar.py --config assets/skills.json --out assets
GITHUB_TOKEN=<token> python3 scripts/cards.py --username kiran-devhub --out assets
GITHUB_TOKEN=<token> python3 scripts/languages.py --username kiran-devhub --out assets
```

(`GITHUB_TOKEN` is optional locally — omit it and you'll just hit the lower
unauthenticated rate limit, or get a placeholder card if you're already over it.)

## 4. Preview without pushing

Open [`preview.html`](preview.html) directly in a browser to see both the dark and
light banner side by side before you commit — useful for checking the morph animation
timing and theme contrast without waiting on GitHub's cache.

## 5. About the contribution activity graph

The "Contribution activity" section in `README.md` embeds a live SVG from the
community [`github-readme-activity-graph`](https://github.com/Ashutosh00710/github-readme-activity-graph)
service. That's a deliberate choice: real contribution-calendar data requires GitHub's
GraphQL API with a `read:user` scoped token, which is a bigger dependency than the
plain REST calls the rest of this repo's scripts use. If you'd rather not depend on a
third-party host, you can:

- self-host that project's API (it's open source), or
- replace the section with a static snapshot you regenerate periodically via a GraphQL
  script of your own.

## 6. Troubleshooting broken images

- **Images show as broken links right after pushing**: GitHub's raw-content cache can
  take a minute to catch up on a brand-new repo. Hard-refresh after a minute.
- **Branch name mismatch**: all paths in `README.md` are repository-relative (e.g.
  `assets/banner-dark.svg`), which resolve against whatever your default branch is.
  If you push to `master` instead of `main`, nothing needs to change — relative paths
  don't encode the branch name.
- **SVG doesn't animate**: some non-browser SVG viewers (and some markdown previewers)
  don't run SMIL animations. It animates correctly in an actual browser viewing your
  GitHub profile page.
- **Dark/light variant not switching**: this depends on the viewer's OS/browser theme
  preference (`prefers-color-scheme`), not a GitHub setting — toggle your OS theme to
  see the other variant.

## 7. File map

```
README.md                     the profile page itself
SETUP.md                      this file
preview.html                  local dark/light preview, no push required
assets/
  source/kiran.png            source portrait used by the banner generator
  banner-dark.svg              hero banner, dark theme
  banner-light.svg             hero banner, light theme
  card-stats-dark.svg          live GitHub stats card, dark theme
  card-stats-light.svg         live GitHub stats card, light theme
  metrics.languages.svg        top-languages bar chart (live data)
  radar-langs-dark.svg         language mix radar, dark theme
  radar-langs-light.svg        language mix radar, light theme
  radar-dark.svg               self-declared skills radar, dark theme
  radar-light.svg              self-declared skills radar, light theme
  skills.json                  edit this to change skills lists + radar levels
  projects.json                edit this to change featured repositories
  langmix.json                 auto-generated cache of language byte data
scripts/
  banner/generate.py           builds banner-dark.svg / banner-light.svg
  banner/halftone.py           photo/glyph -> dot-field conversion
  banner/requirements.txt      numpy + Pillow
  style.py                     shared theme tokens for cards/languages/radar
  cards.py                     builds card-stats-*.svg from the GitHub REST API
  languages.py                 builds metrics.languages.svg + radar-langs-*.svg
  radar.py                     builds radar-*.svg from assets/skills.json
.github/workflows/profile.yml  scheduled + manual refresh workflow
```
