# GitHub Setup Instructions

**Status:** Repository exists locally with 31 commits but NOT yet pushed to GitHub.

---

## Step 1: Create GitHub Repository

**Option A: Via GitHub Web Interface (Recommended)**

1. Go to https://github.com/new
2. **Repository name:** `bio-systems-engineering`
3. **Description:** "Publication-grade repository for systematic running performance optimization using MLOps principles"
4. **Visibility:** 
   - ✅ **Public** (for portfolio/publication)
   - or Private (if you want to review first)
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click **"Create repository"**

**Option B: Via GitHub CLI (if installed)**
```bash
gh repo create bio-systems-engineering --public --source=. --remote=origin
```

---

## Step 2: Add Remote and Push

Once you've created the repository on GitHub, run these commands:

```bash
cd /Users/tomriddle1/Holistic-Performance-Enhancement/cultivation/scripts/running/bio-systems-engineering

# Add the remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/bio-systems-engineering.git

# Verify remote was added
git remote -v

# Push all commits to GitHub
git push -u origin main

# Verify push succeeded
git log --oneline -1
```

---

## Step 3: Verify on GitHub

After pushing, visit:
```
https://github.com/YOUR_USERNAME/bio-systems-engineering
```

**Expected to see:**
- ✅ README.md as landing page
- ✅ 31 commits
- ✅ MIT License badge
- ✅ All source code in `src/biosystems/`
- ✅ Reports and documentation

---

## Step 4: Add Repository Topics (Optional but Recommended)

On GitHub repository page:
1. Click "⚙️ Manage topics"
2. Add topics:
   - `running`
   - `mlops`
   - `performance-optimization`
   - `data-science`
   - `python`
   - `sports-analytics`
   - `physiological-metrics`
   - `n-equals-1`
   - `longitudinal-study`

---

## Step 5: Update Your Profile

Add link to your:
- LinkedIn profile
- Portfolio website
- Resume

**Link format:**
```
🔬 Bio-Systems Engineering
Publication-grade running performance optimization system
https://github.com/YOUR_USERNAME/bio-systems-engineering
```

---

## ⚠️ Pre-Push Security Checklist

**CRITICAL: Verify before pushing!**

```bash
# 1. Check no raw GPS files
find . -name "*.fit" -o -name "*.gpx" | grep -v ".git"
# Should return: (empty - no results)

# 2. Check no API keys
git log --all --full-history --source -- '*secret*' '*key*' '*.env'
# Should return: (empty - no results)

# 3. Check .gitignore is working
git status --ignored | grep "data/raw"
# Should show: data/raw/ is ignored

# 4. Final verification
cat .gitignore | grep -E "(\.fit|\.gpx|data/raw|\.env)"
# Should show these patterns are blocked
```

**All clear?** ✅ Safe to push!

---

## Common Issues

### Issue: "fatal: remote origin already exists"
**Solution:**
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/bio-systems-engineering.git
```

### Issue: Push rejected (non-fast-forward)
**Solution:** You likely initialized with README on GitHub. Either:
```bash
# Option 1: Force push (if repository is empty/new)
git push -u origin main --force

# Option 2: Pull and merge (if you added files on GitHub)
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### Issue: Authentication failed
**Solution:** Use GitHub token or SSH key
```bash
# SSH method (recommended)
git remote set-url origin git@github.com:YOUR_USERNAME/bio-systems-engineering.git
```

---

## Quick Command Summary

```bash
# Full setup (replace YOUR_USERNAME)
cd /Users/tomriddle1/Holistic-Performance-Enhancement/cultivation/scripts/running/bio-systems-engineering
git remote add origin https://github.com/YOUR_USERNAME/bio-systems-engineering.git
git push -u origin main

# Verify
git remote -v
git log --oneline | head -5
```

---

## After Pushing

**Update README.md badges** (optional):

```markdown
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
```

**Add to your profile:**
- Pin this repository on your GitHub profile
- Add repository link to LinkedIn
- Reference in resume/CV

---

**Ready to push? Run the commands above!**
