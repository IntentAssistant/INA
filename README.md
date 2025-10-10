# INA (Intentional Computing Assistant)

**Intent Assistant (INA)** is an experimental platform for our ongoing research on aligned intention monitoring.  

- ⬇️ **Download the latest macOS build:** [`INA-v0.5.0.dmg`](INA-v0.5.0.dmg)

The source code accompanies our forthcoming publication and project site:

- 📄 ArXiv preprint: _(link coming soon)_  
- 🌐 Project page: _(link coming soon)_

INA is a macOS assistant that helps you stay aligned with your stated intentions.  
It captures the current screen (with your permission), analyzes the context using an LLM, and gives lightweight nudges when your activity drifts away from the task you set for yourself. User feedback is looped back into the model prompts so the system learns your personal notion of “on task”.

> This repository is the open-source release of the original KAIST AI research prototype (often referred to as AIM).  
> Everything runs locally on your Mac and talks directly to the LLM provider you configure—no backend server required.

---

## Highlights
- **Real-time activity checks** – grabs a scaled screenshot every few seconds and classifies the activity with an LLM.
- **Direct LLM integration** – works with OpenAI GPT-4o family or Google Gemini via API keys you provide.
- **Feedback-aware learning** – thumbs-up / thumbs-down responses trigger reflection prompts that refine future judgments.
- **All-local storage** – screenshots stay in RAM; logs, JSON traces, and configuration files live under `~/INA_Data` and `~/.intention_app`.
- **macOS-native UI** – PyQt6 dashboard with Rubicon-ObjC bridges for menu bar integration, screen-capture privacy, and notification control.

---

## Repository Layout

| Path | What it contains |
| --- | --- |
| `src/app.py` | Entry point for the PyQt dashboard, notification manager, and capture/LLM loops. |
| `src/ui/` | All widgets (dashboard, dialogs, settings, notifications) and the feedback/reflection manager. |
| `src/config/` | App constants, prompt templates, and the API configuration manager that persists user settings. |
| `src/utils/` | Screen/app detection helpers, direct LLM clients, launch-at-login helpers, etc. |
| `src/logging/` | Local storage utilities writing `_llm_results.json`, `_feedbacks.json`, `_reflections.json`, etc. |
| `google/` | Namespace stub so py2app can bundle Google’s `google-genai` package (see below). |
| `rubicon/` | Namespace stub so py2app can bundle `rubicon-objc` (macOS Objective‑C bridge). |
| `setup.py` | py2app configuration used to create a standalone `.app`. |
| `build_dmg.sh`, `create_dmg_background.py` | Convenience scripts for producing a DMG release. |
| `architecture.md` | Extra diagrams and notes on the overall system design. |

### Why the `google/` and `rubicon/` folders exist
Both directories only contain a minimal `__init__.py`. They make py2app treat Google’s namespace packages (`google.genai`) and Rubicon’s Objective‑C bridge (`rubicon.objc`) as regular packages during bundling. **Do not delete them** unless you replace them with an equivalent packaging shim—without them, the packaged app will crash at runtime with `ModuleNotFoundError`.

---

## Getting Started

### Prerequisites
- macOS 10.15 (Catalina) or later
- Python 3.9 or later (3.11 recommended)
- Command-line tools: `xcode-select --install`

### Set up a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Run the app
```bash
python main.py
```

On first launch the app requests macOS permissions for **Screen Recording**, **Accessibility**, and **Notifications**.  
Grant them via System Settings so that the dashboard can observe the screen and show nudges.

You can also use the helper script which prefers the system Python and warns about conda environments:
```bash
./run_app.sh
```

---

## Configuring LLM Access

INA calls the LLM APIs directly; you supply the API key.

### Configure inside the app
1. Launch the app.  
2. Open **Settings → Models** (or follow the first-run prompt).  
3. Choose **OpenAI GPT** or **Google Gemini**.  
4. Paste your API key and pick a model.  
5. Use **Test API Key** to verify connectivity.  
6. Save. The encrypted config is stored locally in `~/.intention_app/api_config.json`.

> ℹ️ For security and clarity, environment-variable based configuration is intentionally disabled. All credentials are entered and managed through the in-app settings screen.

Supported models (as of v0.5):
- **OpenAI**: `gpt-4o`, `gpt-4o-mini`, or a custom model string.
- **Google**: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.0-flash`, etc.

#### Estimated Token Costs
Assuming an average of **26,500 input tokens** and **40 output tokens** per inference, running every **2 seconds** (≈1,800 inferences/hour):

| Model | Price per hour (USD) |
| --- | ---:|
| GPT-4o mini | 7.20 |
| GPT-5 | 60.00 |
| GPT-5 mini | 12.00 |
| GPT-4.1 | 96.00 |
| Gemini 2.5 Pro | 60.00 |
| Gemini 2.5 Flash | 14.50 |
| Gemini 2.5 Flash-Lite *(recommended)* | 4.80 |
| Gemini 2.0 Flash | 4.80 |
| Gemini 2.0 Flash-Lite | 3.60 |

---

## Data & Logging

| Location | Purpose |
| --- | --- |
| `~/INA_Data/session_data/<task_session>/` | Session-specific JSON logs (`_llm_results.json`, `_feedbacks.json`, `_reflections.json`). |
| `~/INA_Data/logs/` | Console output captured via `main.py`’s tee logger. |
| `~/.intention_app/api_config.json` | Stored API keys, model selections, windowing preferences. |

Screenshots are never written to disk—they remain in memory long enough to be encoded for the LLM request.

---

## Building a macOS App Bundle

Create a standalone `.app` using py2app:
```bash
python setup.py py2app
```
The bundle appears in `dist/INA.app`. Because of the namespace shims mentioned earlier, the required Google and Rubicon modules are baked into the bundle.

To produce a signed DMG (for distribution within a lab or research group):
```bash
./build_dmg.sh
```
`create_dmg_background.py` regenerates the custom background graphic used by the DMG installer.

> ⚠️ If you remove the `google/` or `rubicon/` directories, py2app will no longer discover those namespace packages and the built app will crash when it tries to import `google.genai` or `rubicon.objc`.

---

## Development Notes
- The dashboard UI is written with PyQt6; macOS window behaviours (float-on-top, screen capture exclusion) are implemented through Rubicon-ObjC bridges.
- Prompt templates live in `src/config/prompts.py`. Reflections triggered by user feedback are parsed and saved in the session folder for transparency.
- Additional architecture notes and old design docs are in `architecture.md`.

---

## Contributing
1. Fork the repository and create a feature branch.  
2. Install dependencies via `requirements.txt` (see above).  
3. Run `python main.py` locally to verify changes.  
4. Keep new files ASCII when possible and document non-obvious logic with concise comments.  
5. Submit a pull request describing the change and any testing performed.

Bug reports and feature suggestions are welcome. Please include macOS version, Python version, and whether you’re running from source or a packaged app.

---

## License
This project is released under the MIT License. See [`LICENSE`](LICENSE) for details.
