# Git Commit Best Practices Guide

## Conventional Commits Format

Use this format for ALL commits:

```
<type>(<scope>): <short description>

<optional body>

<optional footer>
```

### Types (Most Common)

| Type | When to Use | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(music): add multi-platform search` |
| `fix` | Bug fix | `fix(music): resolve SoundCloud HLS error` |
| `docs` | Documentation only | `docs: add deployment guide` |
| `style` | Code style (formatting, no logic change) | `style: fix indentation in music.py` |
| `refactor` | Code restructuring (no feature/fix) | `refactor(music): extract platform logic` |
| `perf` | Performance improvement | `perf(music): optimize stream extraction` |
| `test` | Adding tests | `test(music): add platform fallback tests` |
| `chore` | Maintenance tasks | `chore: update dependencies` |
| `build` | Build system changes | `build: update Dockerfile` |
| `ci` | CI/CD changes | `ci: add GitHub Actions workflow` |

### Scope (Optional but Recommended)

The part of codebase affected:
- `music` - Music cog
- `moderation` - Moderation cog
- `web` - Web dashboard
- `docker` - Docker/deployment
- `config` - Configuration files

### Description Rules

✅ **DO:**
- Use imperative mood ("add" not "added" or "adds")
- Start with lowercase
- No period at the end
- Keep under 50 characters
- Be specific and clear

❌ **DON'T:**
- "Fixed stuff"
- "Updated files"
- "Some changes"
- "WIP"

---

## Your Current Changes

You modified `src/cogs/music.py` with:
- Multi-platform music support (YouTube, SoundCloud, JioSaavn, Bandcamp)
- Cookie-based YouTube authentication
- Bug fixes (HLS format, duration formatting)

### Recommended Commit Strategy

**Option 1: Single Commit (Simple)**
```bash
git add .
git commit -m "feat(music): add multi-platform support with cookie auth

- Add YouTube cookie authentication to bypass bot detection
- Implement fallback system (YouTube → SoundCloud → JioSaavn → Bandcamp)
- Fix SoundCloud HLS stream playback
- Fix duration formatting for float values
- Add platform tracking throughout playback flow"
```

**Option 2: Multiple Commits (Better - Atomic Changes)**

```bash
# Commit 1: Core feature
git add src/cogs/music.py
git commit -m "feat(music): add multi-platform search with fallback

Implement intelligent fallback system that tries multiple platforms:
- YouTube (primary, with cookie support)
- SoundCloud (fallback #1)
- JioSaavn (fallback #2)
- Bandcamp (fallback #3)

Each platform is tried in order until a song is found."

# Commit 2: Cookie support
git add src/cogs/music.py
git commit -m "feat(music): add YouTube cookie authentication

Add cookie file support to bypass YouTube bot detection on cloud platforms.
Cookies are optional and configured via YOUTUBE_COOKIE_FILE env var."

# Commit 3: Bug fixes
git add src/cogs/music.py
git commit -m "fix(music): resolve SoundCloud playback issues

- Fix FFmpeg HLS format error by allowing HLS streams for non-YouTube platforms
- Fix duration formatting error by converting float to int before division"

# Commit 4: Config files
git add .env.example Dockerfile TESTING.md
git commit -m "chore: add configuration templates and testing guide

- Add .env.example with cookie configuration
- Update Dockerfile with cookie file support
- Add TESTING.md for multi-platform verification"
```

---

## Step-by-Step: Making Good Commits

### Step 1: Review Changes
```bash
git status              # See what changed
git diff                # See exact changes
git diff --staged       # See staged changes
```

### Step 2: Stage Changes Selectively
```bash
# Stage specific files
git add src/cogs/music.py

# Stage parts of a file (interactive)
git add -p src/cogs/music.py

# Stage all changes
git add .
```

### Step 3: Write Good Commit Message
```bash
# Simple commit
git commit -m "feat(music): add multi-platform support"

# Detailed commit (opens editor)
git commit
```

### Step 4: Verify Commit
```bash
git log -1              # See last commit
git show                # See last commit with diff
```

---

## Commit Message Template

Save this as `.gitmessage` in your home directory:

```
# <type>(<scope>): <subject> (Max 50 char)
# |<----  Using a Maximum Of 50 Characters  ---->|

# Explain why this change is being made
# |<----   Try To Limit Each Line to a Maximum Of 72 Characters   ---->|

# Provide links or keys to any relevant tickets, articles or other resources
# Example: Github issue #23

# --- COMMIT END ---
# Type can be:
#    feat     (new feature)
#    fix      (bug fix)
#    refactor (refactoring code)
#    style    (formatting, missing semi colons, etc; no code change)
#    docs     (changes to documentation)
#    test     (adding or refactoring tests; no production code change)
#    chore    (updating build tasks etc; no production code change)
#    perf     (performance improvement)
# --------------------
# Remember to:
#   - Use imperative mood in subject line
#   - Do not end the subject line with a period
#   - Separate subject from body with a blank line
#   - Use the body to explain what and why vs. how
#   - Can use multiple lines with "-" for bullet points in body
```

Configure Git to use it:
```bash
git config --global commit.template ~/.gitmessage
```

---

## Quick Reference

### Good Examples ✅

```bash
feat(music): add SoundCloud support
fix(web): correct dashboard refresh rate
docs: update deployment guide for Render
refactor(music): extract stream URL logic
perf(music): cache platform search results
chore: update yt-dlp to latest version
```

### Bad Examples ❌

```bash
Updated stuff
Fixed things
WIP
asdfasdf
final commit
really final commit this time
```

---

## For Your Current Changes

I recommend **Option 1** (single commit) since all changes are related to the same feature:

```bash
git add .
git commit -m "feat(music): add multi-platform support with cookie auth

- Add YouTube cookie authentication to bypass bot detection on cloud platforms
- Implement intelligent fallback system (YouTube → SoundCloud → JioSaavn → Bandcamp)
- Fix SoundCloud HLS stream playback by allowing HLS for non-YouTube platforms
- Fix duration formatting to handle float values from SoundCloud
- Add platform tracking throughout search and playback flow
- Add .env.example template and TESTING.md guide"
```

Then push:
```bash
git push origin main
```

---

## Advanced: Interactive Staging

If you want to commit parts of a file separately:

```bash
# Interactive mode
git add -p src/cogs/music.py

# Options:
# y - stage this hunk
# n - don't stage this hunk
# s - split into smaller hunks
# e - manually edit the hunk
# q - quit
```

---

## Viewing History

```bash
# Pretty log
git log --oneline --graph --decorate --all

# Last 5 commits
git log -5 --oneline

# Commits by author
git log --author="YourName"

# Commits with diffs
git log -p
```

---

## Fixing Mistakes

### Amend Last Commit
```bash
# Change commit message
git commit --amend -m "new message"

# Add forgotten files
git add forgotten_file.py
git commit --amend --no-edit
```

### Undo Last Commit (Keep Changes)
```bash
git reset --soft HEAD~1
```

### Undo Last Commit (Discard Changes)
```bash
git reset --hard HEAD~1  # DANGEROUS!
```

---

## Summary

**For your current changes, run:**

```bash
# 1. Check what's changed
git status

# 2. Stage all changes
git add .

# 3. Commit with good message
git commit -m "feat(music): add multi-platform support with cookie auth

- Add YouTube cookie authentication to bypass bot detection
- Implement fallback system (YouTube → SoundCloud → JioSaavn → Bandcamp)
- Fix SoundCloud HLS playback and duration formatting
- Add configuration templates and testing guide"

# 4. Push to GitHub
git push origin main
```

**Remember:**
- ✅ Use conventional commit format
- ✅ Be specific and clear
- ✅ Use imperative mood
- ✅ Keep subject line under 50 chars
- ✅ Explain WHY in the body

This will make your commit history look professional and make it easy to understand what changed and why!
