Exactly — that’s why most tutorials and guides just call it `venv`. It’s not a hard rule, but it’s a **convention** that makes everything simpler:

* IDEs like VS Code auto-detect it
* `.gitignore` patterns are standard
* Switching between projects becomes predictable
* Documentation and examples online all assume `venv`

Since you’re happy with that, let’s proceed with a **ready-to-go workflow using `venv`** inside your project. I’ll write it step-by-step for both **WSL/Linux** and **macOS**, including `pip-tools` and a minimal project skeleton.

---

# **1️⃣ Create project folder**

```bash
mkdir -p ~/projects/minimal-backtest
cd ~/projects/minimal-backtest
```

---

# **2️⃣ Create virtual environment (`venv`)**

```bash
python3 -m venv venv
```

* This creates a folder `venv/` inside the project
* Fully isolated Python environment

---

# **3️⃣ Activate the virtual environment**

```bash
# Linux / WSL
source venv/bin/activate

# macOS
source venv/bin/activate
```

Prompt changes to `(venv)`.

---

# **4️⃣ Upgrade pip & install pip-tools**

```bash
pip install --upgrade pip
pip install pip-tools
```

---

# **5️⃣ Create requirements.in**

```bash
touch requirements.in
```

Add minimal dependencies for your first project:

```
numpy
pandas
matplotlib
scipy
```

---

# **6️⃣ Compile and install**

```bash
pip-compile requirements.in   # generates requirements.txt
pip-sync requirements.txt     # installs pinned dependencies
```

✅ Now your `venv` has all dependencies pinned.

---

# **7️⃣ Create basic project structure**

```bash
mkdir src notebooks tests data
touch README.md
```

* `src/` → Python modules
* `notebooks/` → Jupyter notebooks (optional)
* `tests/` → unit tests
* `data/` → any CSV/parquet files

---

# **8️⃣ VS Code setup**

1. Open `~/projects/minimal-backtest` in VS Code
2. Select **Python interpreter** → point to `~/projects/minimal-backtest/venv/bin/python`
3. Configure `.vscode/settings.json` (optional):

```json
{
    "python.pythonPath": "venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.analysis.extraPaths": ["src"]
}
```

> Now VS Code knows exactly which environment to use.

---

# **9️⃣ Quick activate/deactivate cheat**

```bash
# Activate
source venv/bin/activate

# Deactivate
deactivate
```

---

# **10️⃣ Git setup**

Add to `.gitignore`:

```
venv/
__pycache__/
*.pyc
```

> Keeps your virtual environment out of version control.

---

If you want, I can **also add a minimal backtest Python skeleton** with `src/backtest.py`, a notebook, and sample structure, so you can literally start coding your first train-side project immediately.

Do you want me to do that next?


For your venv to appear as an option inside any notebook

```
python -m ipykernel install --user --name=mbte --display-name "Python (mbte)"
```

Once you have a pyproject.toml file, install your project in editable mode
```
pip install -e .
```
You don't need to re-run after updating pip-tools package
