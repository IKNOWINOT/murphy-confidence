# Extraction Guide — murphy-confidence

This guide walks you through taking the files prepared in
`standalone-repos/murphy-confidence/` and turning them into a live, published,
community-ready GitHub repository.

---

## Step 1: Create the new repository on GitHub

1. Go to https://github.com/new
2. Repository name: `murphy-confidence`
3. Owner: `IKNOWINOT`
4. Description: `MFGC confidence scoring and safety gates for AI agents. Zero dependencies.`
5. Visibility: **Public**
6. Do NOT initialise with a README, .gitignore, or license (you'll push those)
7. Click **Create repository**

---

## Step 2: Copy all files into the new repo

```bash
# In a clean directory on your machine:
git clone https://github.com/IKNOWINOT/murphy-confidence.git
cd murphy-confidence

# Copy everything from the prepared directory:
cp -r /path/to/Murphy-System/standalone-repos/murphy-confidence/. .

# Commit and push:
git add .
git commit -m "feat: initial extraction from Murphy System v0.1.0"
git push origin main
```

---

## Step 3: Add GitHub repository topics

In the repository settings → **Topics**, add:

```
ai-agents  ai-safety  confidence-scoring  guardrails  human-in-the-loop
autonomous-agent  llm  mfgc  murphy  python  zero-dependency
```

These topics drive GitHub search discoverability.

Also set the **Homepage** URL to:
```
https://github.com/IKNOWINOT/Murphy-System
```

---

## Step 4: Set up GitHub Sponsors

1. Go to https://github.com/sponsors
2. Click **Get sponsored**
3. Complete the application (US or international bank account required)
4. Once approved, the `FUNDING.yml` you copied will automatically show a
   **Sponsor** button on the repository

The `FUNDING.yml` is already configured:
```yaml
github: IKNOWINOT
custom:
  - "https://github.com/IKNOWINOT/Murphy-System"
```

---

## Step 5: Set up PyPI trusted publisher (OIDC)

This enables the `publish.yml` workflow to publish without storing API keys.

1. Create an account at https://pypi.org (or log in)
2. Go to https://pypi.org/manage/account/publishing/
3. Add a new **pending trusted publisher**:
   - **PyPI Project Name**: `murphy-confidence`
   - **Owner**: `IKNOWINOT`
   - **Repository name**: `murphy-confidence`
   - **Workflow name**: `publish.yml`
   - **Environment name**: *(leave blank)*
4. Click **Add**

---

## Step 6: Enable GitHub Discussions

1. Go to the repository **Settings** → **Features**
2. Enable **Discussions**
3. Create starter categories:
   - 💬 General
   - 🙏 Q&A
   - 💡 Ideas
   - 🎉 Show and Tell

---

## Step 7: Create the first release (triggers PyPI publish)

1. Go to the repository **Releases** → **Create a new release**
2. Tag: `v0.1.0`
3. Title: `v0.1.0 — Initial release`
4. Description: paste the CHANGELOG.md entry for 0.1.0
5. Click **Publish release**

This triggers the `publish.yml` workflow which:
- Builds the wheel and sdist with `python -m build`
- Publishes to PyPI using OIDC (no API key needed)

After ~2 minutes, `pip install murphy-confidence` will work worldwide.

---

## Step 8: Post to communities (in this order)

### Hacker News — Show HN

Title:
> Show HN: murphy-confidence – Structured confidence scoring and safety gates for AI agents (zero deps)

Opening paragraph:
> I extracted the confidence gating layer from my autonomous AI orchestration system (Murphy System) into a standalone zero-dependency Python library. The formula C(t) = w_g·G(x) + w_d·D(x) − κ·H(x) weights generative quality, domain determinism, and hazard with phase-locked schedules that make the engine progressively stricter as execution approaches. In other words: same inputs, different strictness at brainstorm vs. execute.

Post at: https://news.ycombinator.com/submit

### Reddit

- **r/LocalLLaMA** — focus on agent safety and the gate system
- **r/MachineLearning** — focus on the formula and the phase-locked weights
- **r/Python** — focus on the zero-dependency, pure-stdlib angle

Post title template:
> murphy-confidence — a structured confidence gate for AI agents (Python, zero deps, feedback welcome)

### Dev.to / Hashnode

Write a 1000-word post titled:
> "How murphy-confidence decides whether your AI agent should act (and when to stop it)"

Walk through the formula, the 7 phases, and a FastAPI middleware example.

---

## Step 9: SEO checklist

- [ ] Repository description is set (≤ 160 chars, includes keywords)
- [ ] Topics/tags are set (see Step 3)
- [ ] Homepage URL is set
- [ ] Social preview image uploaded (Settings → Social preview) — use a
  screenshot of the README formula block or the pipeline table
- [ ] README has keyword-rich text (ai safety, confidence scoring, ai agents,
  guardrails, human-in-the-loop, llm safety) — already done ✓
- [ ] README badges are rendering correctly after first push to PyPI
- [ ] GitHub Pages is NOT enabled (would conflict with the PyPI README)

---

## Step 10: Link back to Murphy System

The README already has a "Part of Murphy System" section.  Make sure the
main Murphy System README also links to murphy-confidence once it's live:

```markdown
## Standalone libraries

- [murphy-confidence](https://github.com/IKNOWINOT/murphy-confidence) — 
  MFGC confidence scoring and safety gates. Extracted from Murphy System.
  Zero dependencies. `pip install murphy-confidence`
```

---

## What you do NOT need to do

- No PyPI account password or API token — the trusted publisher handles it
- No manual wheel building — the publish workflow handles it
- No manual documentation site — the README is the documentation

---

## Checklist summary

- [ ] Created `IKNOWINOT/murphy-confidence` repository on GitHub
- [ ] Pushed all files from `standalone-repos/murphy-confidence/`
- [ ] Added repository topics
- [ ] Set up GitHub Sponsors
- [ ] Configured PyPI trusted publisher
- [ ] Enabled GitHub Discussions
- [ ] Created `v0.1.0` release (triggers PyPI publish)
- [ ] Verified `pip install murphy-confidence` works
- [ ] Posted to Hacker News / Reddit / Dev.to
- [ ] Uploaded social preview image
- [ ] Added backlink from Murphy System README
