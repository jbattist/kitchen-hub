# Kitchen Hub

Kitchen Hub is a Raspberry Pi touchscreen control surface for Spotify-on-Sonos playback plus ambient museum artwork when the system is idle.

## Current status

This repository now contains the first implementation scaffold:

- Flask app shell for kiosk UI
- JSON API endpoints for playback status, themes, and next artwork
- YAML config loader with typed dataclasses
- Theme registry for Art Mode
- Museum payload normalization helpers for Met, AIC, and Cleveland
- Sonos and Spotify wrapper modules ready for deeper integration

## Quick start

### Fish shell

```fish
python -m venv .venv
source .venv/bin/activate.fish
python -m ensurepip --upgrade
python -m pip install -r requirements.txt
python main.py
```

### POSIX shells (`bash`, `zsh`, `sh`)

```bash
python -m venv .venv
. .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install -r requirements.txt
python main.py
```

Then open <http://localhost:5000>.

## Run tests

### Fish shell

```fish
source .venv/bin/activate.fish
python -m pytest tests/ -q
```

### POSIX shells (`bash`, `zsh`, `sh`)

```bash
. .venv/bin/activate
python -m pytest tests/ -q
```
