# Kitchen Hub — Spotify Control Center + Art Display — Spec

A Raspberry Pi touchscreen display for the kitchen that serves as a Spotify remote (controlling playback on Sonos speakers) and, when idle, cycles through classic modern art pulled from major museum collections around the world.

---

## Goals

- Control Spotify playback routing to any Sonos room from a touch UI
- Show currently playing track with album art, progress bar, controls
- When idle (no active playback, or after N minutes), enter **Art Mode**:
  - Full-screen artwork from museum APIs
  - Themed slideshows (Impressionism, Modernism, Abstract, etc.)
  - Artwork title, artist, museum, year shown as overlay
- Looks beautiful on a touchscreen — this is a kitchen display, it should be ambient

---

## Hardware

### Recommended Pi
**Raspberry Pi 5 (4GB)** — best choice for this use case:
- Fast enough for smooth UI, image decoding (art slideshow), and simultaneous network calls
- Handles Chromium kiosk well; Pi 4 can struggle with smooth animations
- 4GB RAM is comfortable for Spotify API + SoCo + image cache running together

**Avoid:** Pi Zero 2W (underpowered for simultaneous UI + network + image decoding), Pi 4 2GB (borderline sluggish for art mode)

### Display
**5" DSI Touchscreen, 800×480** — recommended options:
- **Waveshare 5" DSI** — connects via ribbon cable, clean install, good driver support
- **Raspberry Pi Official 5" Display** (2024) — first-party, best driver support, 720×1280 portrait

- Same LAN as Sonos speaker(s)
- Internet access for Spotify Web API + museum image fetching

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python | Primary language |
| UI Framework | **Chromium kiosk** (Flask + HTML/CSS) | 800×480 has enough room for rich layout; CSS crossfades for art mode are beautiful |
| Spotify Control | **Spotify Web API** (OAuth) | Official, full-featured |
| Sonos Control | **SoCo** (Python lib, local UPnP) | No cloud, auto-discovers on LAN |
| Museum Images | Met, AIC, Cleveland APIs (no key needed) | Free, CC0, no rate limit issues |
| Image Cache | Local disk (`~/.kitchen-hub/art-cache/`) | Pre-fetch images, avoid latency |
| Config | `config.yaml` | Sonos room names, Spotify credentials, themes |

---

## Spotify Integration

Uses the **Spotify Web API** — no audio routing through the Pi. Sonos handles audio natively via Spotify Connect.

### Architecture
```
Spotify App / Kitchen UI → [Spotify Web API] → Sonos (Spotify Connect, built-in)
                                                       ↑
Raspberry Pi (SoCo) ─────────[LAN UPnP]───────────────┘
```

- Pi sends commands to Spotify Web API (play, pause, next, seek, select device)
- Sonos appears as a "device" in Spotify Connect — Pi selects it as active device
- SoCo used for Sonos-specific controls (volume, room grouping) over local UPnP

### Spotify Web API Auth

OAuth 2.0 with PKCE (no backend needed for initial setup):
- Scopes needed: `user-read-playback-state`, `user-modify-playback-state`, `user-read-currently-playing`, `playlist-read-private`, `playlist-modify-private`, `playlist-modify-public`
- Token stored locally, auto-refreshed
- Library: `spotipy` (Python)

```python
import spotipy
from spotipy.oauth2 import SpotifyOAuth

sp = SpotifyOAuth(
    client_id="...",
    client_secret="...",
    redirect_uri="http://localhost:8888/callback",
    scope="user-read-playback-state user-modify-playback-state"
)
```

### Key API Calls

```python
# Get current playback
sp.current_playback()

# Play/pause
sp.start_playback(device_id=sonos_device_id)
sp.pause_playback()

# Next/previous
sp.next_track()
sp.previous_track()

# List available devices (find Sonos)
sp.devices()  # Returns Sonos rooms as Spotify Connect devices

# Transfer playback to a Sonos room
sp.transfer_playback(device_id=sonos_device_id)

# Seek
sp.seek_track(position_ms=30000)

# Volume (via Spotify)
sp.volume(volume_percent=60, device_id=sonos_device_id)

# List user playlists (paginated)
sp.current_user_playlists(limit=50, offset=0)

# Start shuffle playback from a playlist
sp.shuffle(state=True, device_id=sonos_device_id)
sp.start_playback(device_id=sonos_device_id, context_uri=playlist_uri)

# Get the current playback queue
sp.queue()  # Returns { "currently_playing": ..., "queue": [...] }

# Skip to a specific track in the queue (by skipping N times — no direct jump API)
sp.next_track()  # Repeat as needed; or reorder via queue reorder endpoint

# Add track to queue
sp.add_to_queue(uri=track_uri, device_id=sonos_device_id)
```

**Note:** Spotify Web API has no direct "jump to position N in queue" endpoint. Queue reordering requires using the **playlist** reorder endpoint when the context is a playlist:
```python
sp.playlist_reorder_items(playlist_id, range_start, insert_before, range_length=1)
```
For queue-only reordering (outside a playlist context), the approach is to skip tracks programmatically.

---

## Sonos Integration

**SoCo** for local control (volume, grouping, room discovery):

```bash
pip install soco
```

```python
import soco

# Auto-discover all Sonos zones
zones = soco.discover()

# Get room by name
kitchen = next(z for z in zones if z.player_name == "Kitchen")

# Volume control
kitchen.volume = 40

# Group rooms
living_room.join(kitchen)  # Sync Living Room → Kitchen
```

Sonos rooms appear as Spotify Connect devices automatically — use `sp.devices()` to find their IDs.

---

## Art Mode — Museum APIs

When idle, cycle through curated artwork. All APIs are free, no key required (except Harvard), CC0 licensed.

### Sources

| Museum | Base URL | Notes |
|---|---|---|
| **The Met** | `https://collectionapi.metmuseum.org/public/collection/v1/` | 470K+ works, CC0, 80 req/s |
| **Art Institute of Chicago** | `https://api.artic.edu/api/v1/` | IIIF images, CC0, 60 req/min |
| **Cleveland Museum of Art** | `https://openaccess-api.clevelandart.org/api/` | CC0, JPEG/TIFF, no key |
| **Rijksmuseum** | `https://data.rijksmuseum.nl/` | Dutch masters, free new API |

### Image Fetching Examples

**Met — search Impressionism:**
```
GET https://collectionapi.metmuseum.org/public/collection/v1/search?q=impressionism&hasImages=true&isPublicDomain=true
GET https://collectionapi.metmuseum.org/public/collection/v1/objects/{id}
→ use `primaryImage` field
```

**AIC — search by movement:**
```
GET https://api.artic.edu/api/v1/artworks/search?q=impressionism&fields=id,title,artist_display,image_id,date_display,is_public_domain
→ image URL: https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg
```

**Cleveland — CC0 with images:**
```
GET https://openaccess-api.clevelandart.org/api/artworks/?cc0=1&has_image=1&type=Painting
→ `images.web.url` field for 900px JPEG
```

### Art Themes

Pre-defined theme playlists, each a search query across one or more museums:

| Theme | Query Terms | Museums |
|---|---|---|
| Impressionism | `impressionism`, `monet`, `renoir`, `degas` | Met, AIC, Rijksmuseum |
| Abstract | `abstract`, `kandinsky`, `mondrian`, `rothko` | Met, AIC, Cleveland |
| Dutch Masters | `rembrandt`, `vermeer`, `dutch golden age` | Rijksmuseum, Met |
| Modernism | `modernism`, `picasso`, `matisse`, `cézanne` | Met, AIC |
| Landscapes | `landscape`, `nature`, `plein air` | Met, AIC, Cleveland |
| Portraits | `portrait` | All |

Themes rotate on a schedule or user can tap to switch.

### Image Caching Strategy

- On startup (or nightly), pre-fetch ~50 images per theme into `~/.kitchen-hub/art-cache/{theme}/`
- Store metadata (title, artist, year, museum) as `{image_id}.json` alongside image
- Rotate through cached images in slideshow; background thread refreshes cache
- Avoids any latency during display

---

## UI Layout

### Playlist Selector Screen (v1)

Entry point when no playback is active (or user taps a "Browse" button from Now Playing). Displays user's Spotify playlists in a scrollable grid/list. Selecting a playlist immediately begins shuffle playback on the active Sonos device.

```
┌─────────────────────────────────────┐
│  ♫  Kitchen Hub        [Now Playing]│
├─────────────────────────────────────┤
│  Your Playlists                     │
│                                     │
│  ┌──────────┐  ┌──────────┐        │
│  │ [Cover]  │  │ [Cover]  │        │
│  │ Morning  │  │ Chill    │        │
│  │ Vibes    │  │ Lounge   │        │
│  └──────────┘  └──────────┘        │
│  ┌──────────┐  ┌──────────┐        │
│  │ [Cover]  │  │ [Cover]  │        │
│  │ Dinner   │  │ Jazz     │        │
│  │ Party    │  │ Evening  │        │
│  └──────────┘  └──────────┘        │
│                ↕ scroll             │
└─────────────────────────────────────┘
```

- Tapping a playlist: enables shuffle → starts playback → switches to Now Playing screen
- Playlists fetched from `sp.current_user_playlists()`, paginated, cover art shown
- A "Browse" button on the Now Playing screen navigates here

### Now Playing Mode

```
┌─────────────────────────────────────┐
│  ♫  Kitchen Hub          [Browse]🔊│
├─────────────────────────────────────┤
│                                     │
│       [Album Art — large]           │
│                                     │
│  Song Title                         │
│  Artist · Album                     │
│                                     │
│  ━━━━━━●━━━━━━━━━━  2:14 / 4:03    │
│                                     │
│  [⏮]  [⏸]  [⏭]        🔊 ────●─  │
│                                     │
│  Playing on: Kitchen                │
│  [ Kitchen ] [ Living Room ] [ All ]│
└─────────────────────────────────────┘
```

### Art Mode (Idle)

```
┌─────────────────────────────────────┐
│                                     │
│                                     │
│         [Full-screen artwork]       │
│                                     │
│                                     │
│                                     │
├─────────────────────────────────────┤
│  "Water Lilies" — Claude Monet      │
│  1906 · The Art Institute of Chicago│
│  [◀ Prev]  Impressionism  [Next ▶]  │
│            [Change Theme]           │
└─────────────────────────────────────┘
```

- Tap anywhere on art = return to Now Playing
- Bottom strip shows artwork info + navigation
- Smooth crossfade between images (configurable interval, default 30s)
- Dims display after extended idle (configurable)

### Queue Management Screen (v2)

Accessible via a "Queue" button on the Now Playing screen. Shows the upcoming tracks in the playback queue; user can reorder or remove them.

```
┌─────────────────────────────────────┐
│  ← Now Playing       Up Next 🔀     │
├─────────────────────────────────────┤
│  Now Playing:                       │
│  🎵 Song Title — Artist             │
├─────────────────────────────────────┤
│  1. [Art] Next Track — Artist    ✕  │
│      ══════════════════════ [drag]  │
│  2. [Art] Track Two  — Artist    ✕  │
│      ══════════════════════ [drag]  │
│  3. [Art] Track Three— Artist    ✕  │
│      ══════════════════════ [drag]  │
│  4. [Art] Track Four — Artist    ✕  │
│  ...                                │
│                ↕ scroll             │
└─────────────────────────────────────┘
```

- Queue fetched from `sp.queue()`
- Drag handle (≡) on each row allows reordering; uses `sp.playlist_reorder_items()` when context is a playlist
- ✕ button removes track from queue (skips past it)
- Shuffle indicator (🔀) shows current shuffle state; tap to toggle
- Changes apply immediately via Spotify Web API

---

## Features

### MVP
- [ ] Spotify OAuth login on first run, token stored + auto-refreshed
- [ ] Show current playback: track, artist, album art, progress bar
- [ ] Play / pause / next / previous controls
- [ ] Volume slider
- [ ] Sonos room selector (transfer playback between rooms)
- [ ] Auto-enter Art Mode when nothing is playing (or after 5 min idle)
- [ ] Art Mode: full-screen slideshow with artwork info overlay
- [ ] At least 3 themes (Impressionism, Abstract, Dutch Masters)
- [ ] Tap art to return to Now Playing
- [ ] Background image cache (pre-fetch on startup)
- [ ] **Playlist Selector screen** — scrollable grid of user's playlists with cover art
- [ ] Tapping a playlist enables shuffle and starts playback immediately
- [ ] "Browse" button on Now Playing navigates to Playlist Selector

### v2
- [ ] **Queue Management screen** — view upcoming tracks in queue
- [ ] Drag-to-reorder tracks in queue (playlist context via `playlist_reorder_items`)
- [ ] Remove tracks from queue (✕ button)
- [ ] Shuffle toggle on queue screen
- [ ] "Queue" button on Now Playing navigates to Queue screen

### Nice-to-Have
- [ ] Theme switcher UI in Art Mode
- [ ] Crossfade animation between artworks
- [ ] Display dims after 10 min (DPMS or pygame brightness)
- [ ] Search Spotify from the display
- [ ] Show Sonos grouping controls (join/unjoin rooms)
- [ ] Wake-word or motion sensor to exit art mode
- [ ] Liked songs / playlist quick-launch strip

---

## Project Structure

```
kitchen-hub/
├── SPEC.md
├── AGENTS.md
├── README.md
├── config.yaml
├── requirements.txt
├── main.py                  # Entry point
├── ui/
│   ├── app.py               # Main app, manages mode switching
│   ├── now_playing.py       # Spotify Now Playing screen
│   ├── playlist_selector.py # Playlist browser → shuffle launch (v1)
│   ├── queue_manager.py     # Queue view + drag-to-reorder (v2)
│   └── art_mode.py          # Slideshow screen
├── spotify/
│   ├── client.py            # spotipy wrapper, OAuth handling
│   └── playback.py          # Playback controls, device management, playlist/queue ops
├── sonos/
│   └── controller.py        # SoCo wrapper, room discovery/volume
├── art/
│   ├── fetcher.py           # Museum API clients (Met, AIC, Cleveland)
│   ├── cache.py             # Local image cache management
│   └── themes.py            # Theme definitions and query logic
└── tests/
    ├── test_spotify.py
    ├── test_sonos.py
    └── test_art_fetcher.py
```

---

## Config (config.yaml)

```yaml
spotify:
  client_id: ""         # From Spotify Developer Dashboard
  client_secret: ""     # Keep out of git
  redirect_uri: "http://localhost:8888/callback"

sonos:
  default_room: "Kitchen"
  rooms:
    - "Kitchen"
    - "Living Room"

art:
  idle_timeout_seconds: 300   # 5 minutes before Art Mode
  slideshow_interval_seconds: 30
  cache_dir: "~/.kitchen-hub/art-cache"
  images_per_theme: 50
  default_theme: "Impressionism"
  themes:
    - Impressionism
    - Abstract
    - Dutch Masters
    - Modernism
    - Landscapes

display:
  dim_after_seconds: 600      # 10 minutes
  brightness_idle: 30         # percent
  brightness_active: 100
```

---

## Dependencies

```
spotipy          # Spotify Web API
soco             # Sonos local UPnP control
requests         # Museum API image fetching
Pillow           # Image resizing/caching
pyyaml           # Config
pygame           # UI (if not using Chromium)
# OR: flask + flask-socketio for Chromium kiosk approach
```

---

## Open Questions

1. **UI framework:** Pygame vs Chromium kiosk? Pygame is simpler to deploy; Chromium enables richer CSS animations for art crossfades.
2. **Screen size/resolution:** Affects layout proportions.
3. **Spotify app registration:** Need client ID/secret from Spotify Developer Dashboard — have you set that up?
4. **Sonos room names:** What are your actual room names? (SoCo discovers them, but good for config defaults.)
5. **Art themes:** Any specific movements/periods you want? Any museums to prioritize?
6. **Run as service:** Auto-start on boot via systemd?
