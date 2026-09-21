# Kiran GitHub Profile — setup

This folder is intended to become the **profile repository** for `kiran-devhub`.

## 1. Create/open the profile repository

GitHub profile READMEs are shown when the repository name exactly matches your username:

`kiran-devhub/kiran-devhub`

Create that repository if it does not already exist.

## 2. Upload everything

Copy the contents of this folder into the root of `kiran-devhub/kiran-devhub` and push to `main`.

## 3. Enable the automatic refresh

The included `.github/workflows/profile.yml` runs daily and can also be started manually from:

**GitHub → Actions → Refresh GitHub Profile → Run workflow**

It regenerates:

- animated portrait/terminal banner
- both skill radars
- GitHub statistics
- recent repository cards
- top-language chart

## 4. Optional: add a stronger GitHub token

The built-in `GITHUB_TOKEN` is used automatically. If you want contribution-calendar data and broader API access, create a GitHub Personal Access Token and add it as a repository secret named:

`METRICS_TOKEN`

The workflow already prefers `METRICS_TOKEN` when present.

## 5. Customize later

- `assets/skills.json` → skill radar
- `assets/langmix.json` → development/security radar
- `assets/projects.json` → pin specific repositories and descriptions
- `scripts/banner/generate.py` → terminal banner content, colors, animation timing
- `README.md` → profile text and sections
- `assets/source/kiran.png` → source portrait used to generate the animated portrait

## Notes

The generated banner is intentionally self-hosted in the repository instead of depending on an external profile-card service. The GitHub activity graph in the README is the only external dynamic graph.
