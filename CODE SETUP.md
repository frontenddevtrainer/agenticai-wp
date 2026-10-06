# Running the Lab Code on Mac or Windows

A step-by-step guide for attendees: install Python, set up the course environment, add your API key, and run the labs.
Takes about **20–30 minutes** the first time. Do it **before Day 1** if you can.

> Linux / Ubuntu users: follow the Mac steps. The commands are the same.

---

## What you'll install

| Tool | Why | Required? |
|---|---|---|
| **Miniforge** (conda) | Installs Python 3.13 and keeps course packages in their own environment | ✅ |
| **VS Code** or **PyCharm** | Editor to read and run the code | ✅ (either one) |
| **Git** | Download the course repo | Optional (you can download a ZIP instead) |
| **Ollama** | Runs a free local AI model (Day 1 Lab 3; later days) | Recommended |
| **OpenRouter API key** | Access to Claude models | ✅ (the facilitator may provide one) |

---

## Step 1 — Install Miniforge (Python + conda)

### 🍎 Mac

1. Open **Terminal** (press `Cmd + Space`, type *Terminal*, press Enter).
2. Run:
   ```bash
   curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
   bash Miniforge3-$(uname)-$(uname -m).sh -b -p "$HOME/miniforge3"
   "$HOME/miniforge3/bin/conda" init zsh
   ```
3. **Close Terminal and open it again.** You should now see `(base)` at the start of the prompt.
4. Check:
   ```bash
   conda --version
   ```

> Homebrew users can instead run `brew install --cask miniforge`, then `conda init zsh` and reopen Terminal.

### 🪟 Windows

1. Download the installer: **https://github.com/conda-forge/miniforge/releases/latest** → `Miniforge3-Windows-x86_64.exe`.
2. Run it. Choose **"Just Me"** and keep the default options.
3. Open the Start menu and launch **Miniforge Prompt**. **Use this window for all commands in this guide.**
4. Check:
   ```bat
   conda --version
   ```

> Want to use normal PowerShell instead? In Miniforge Prompt run `conda init powershell`, then reopen PowerShell.
> If PowerShell blocks scripts, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

---

## Step 2 — Get the course code

**Option A: Git**

| Mac (Terminal) | Windows (Miniforge Prompt) |
|---|---|
| `xcode-select --install` (first time only, installs git) | install Git from https://git-scm.com/download/win |
| `cd ~ && mkdir -p code && cd code` | `cd %USERPROFILE% && mkdir code && cd code` |
| `git clone <repo-url> agentic-workshop` | `git clone <repo-url> agentic-workshop` |

**Option B: ZIP.** Download the ZIP the facilitator shares and unzip it into a folder such as
`~/code/agentic-workshop` (Mac) or `C:\Users\<you>\code\agentic-workshop` (Windows).

---

## Step 3 — Create the course environment (once)

Same commands on Mac and Windows:

```bash
conda create -n meridian python=3.13 -y
conda activate meridian
python --version          # should print Python 3.13.x
```

**Every time you open a new terminal, run `conda activate meridian` first.** The prompt should show `(meridian)`.

---

## Step 4 — Get an OpenRouter API key

1. Go to **https://openrouter.ai** → sign in → **Keys** → **Create Key** (name it `meridian-<yourname>`).
   Set a **credit limit** on the key. (Your facilitator may give you a key instead.)
2. Copy the key (it starts with `sk-or-v1-`). **Treat it like a password:** never paste it into code, chat or screenshots.

---

## Step 5 — Set up and run Day 1

Go into the Day 1 code folder:

| Mac | Windows |
|---|---|
| `cd ~/code/agentic-workshop/day1-foundations/code` | `cd %USERPROFILE%\code\agentic-workshop\day1-foundations\code` |

Install the packages:

```bash
pip install -r requirements.txt
```

Create your `.env` file from the template:

| Mac | Windows |
|---|---|
| `cp .env.example .env` | `copy .env.example .env` |

Open `.env` in your editor and replace the placeholder with your key:

```
OPENROUTER_API_KEY=sk-or-v1-your-real-key
MODEL=anthropic/claude-opus-5.5
OLLAMA_MODEL=qwen3:8b
```

Run the labs:

```bash
python lab2_first_call.py
python lab4_is_agent.py transcripts/t3_agent_loop.json
```

✅ **Success looks like:** three bullet points about chargebacks, then `stop_reason: end_turn`, and the token counts.

---

## Step 6 — Run Day 2

Each day has its own `code/` folder with its own `.env`. Repeat the `.env` step there.

| Mac | Windows |
|---|---|
| `cd ../../day2-single-agent-patterns/code` | `cd ..\..\day2-single-agent-patterns\code` |
| `cp .env.example .env` (then add your key) | `copy .env.example .env` (then add your key) |

```bash
pip install -r requirements.txt
python lab1_react_agent.py
python lab1_react_agent.py "Is BOLT over its processing limit?"
python lab2_plan_and_execute.py
python lab3_reflexion.py
python lab4_break_it.py
```

✅ **Success looks like** (Lab 1): lines like `[turn 1] lookup_merchant(...)`, `[turn 2] get_fx_rate(...)`, then
`ANSWER: ... OVER_LIMIT ... 104.4%`.

---

## Step 7 (recommended) — Install Ollama for local models

| Mac | Windows |
|---|---|
| Download from **https://ollama.com/download** and open the app | Download the Windows installer from **https://ollama.com/download** and run it |

Then, in your terminal:

```bash
ollama pull qwen3:8b             # ~5 GB, do this on good Wi-Fi
ollama run qwen3:8b "Say ready"  # quick test (Ctrl+D to exit)
```

Now Day 1 Lab 3 works:

```bash
cd <path>/day1-foundations/code
python lab3_side_by_side.py
```

> Laptop with less than 16 GB RAM? Pull a smaller model (e.g. a 2–4B one from ollama.com) and set `OLLAMA_MODEL` in `.env`.

**No internet or no API key?** You can run the labs against a local model that supports tools. In `.env`:

```
BASE_URL=http://localhost:11434
OPENROUTER_API_KEY=ollama
MODEL=qwen3:8b
```

Answers will be weaker than Claude's, but the code runs the same way.

---

## Step 8 — Running the code in your editor

### VS Code (Mac & Windows)
1. Install **VS Code** and the **Python** extension (by Microsoft).
2. **File → Open Folder…** → choose the course folder.
3. Press `Cmd+Shift+P` (Mac) / `Ctrl+Shift+P` (Windows) → **Python: Select Interpreter** → pick the one with
   **`meridian`** in its name.
4. Open a lab file, then click **▶ Run Python File** (top right).
5. **Important:** the scripts look for `.env` and `llm.py` in the **same folder**. If you see `KeyError: 'OPENROUTER_API_KEY'`,
   open the terminal in VS Code, `cd` into that day's `code` folder, and run `python <file>.py` there.

### PyCharm (Mac & Windows)
1. **Open** the course folder.
2. **Settings → Project → Python Interpreter → Add Interpreter → Conda Environment → Use existing → `meridian`.**
3. Right-click a lab file → **Run**.
4. If it can't find `.env`: **Run → Edit Configurations…** → set **Working directory** to that day's `code` folder.

---

## Troubleshooting

| Problem | Mac fix | Windows fix |
|---|---|---|
| `conda: command not found` / not recognised | reopen Terminal; or run `~/miniforge3/bin/conda init zsh` | use **Miniforge Prompt**, or run `conda init powershell` |
| Prompt doesn't show `(meridian)` | `conda activate meridian` | `conda activate meridian` |
| `ModuleNotFoundError: No module named 'anthropic'` | you're not in the env: `conda activate meridian`, then `pip install -r requirements.txt` | same |
| `KeyError: 'OPENROUTER_API_KEY'` | `.env` missing, or you're running from the wrong folder: `cd` into that day's `code` folder | same; also check the file isn't called `.env.txt` (turn on *View → File name extensions* in Explorer) |
| `401` / authentication error | wrong or expired key in `.env` | same |
| `402` Payment Required | the key's credit limit is used up: ask the facilitator | same |
| `404` model not found | use `anthropic/claude-opus-5.5` exactly (with the `anthropic/` prefix) | same |
| `ConnectionError` to `localhost:11434` | Ollama isn't running: open the Ollama app | start Ollama from the Start menu |
| Corporate laptop blocks downloads | ask IT to allow: conda-forge, pypi.org, openrouter.ai, ollama.com | same |
| `python` opens the Microsoft Store | — | you're not in the conda env: open **Miniforge Prompt** and `conda activate meridian` |

---

## Quick reference (every session)

```bash
conda activate meridian
cd <course-folder>/<dayN-...>/code
python <lab_file>.py
```