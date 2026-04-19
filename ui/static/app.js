const browseButton = document.getElementById('browse-button');
const hidePlaylistsButton = document.getElementById('hide-playlists-button');
const playlistPanel = document.getElementById('playlist-panel');
const playlistList = document.getElementById('playlist-list');
const trackTitle = document.getElementById('track-title');
const trackSubtitle = document.getElementById('track-subtitle');
const playbackDevice = document.getElementById('playback-device');
const artworkCaption = document.getElementById('artwork-caption');
const albumArtImg = document.getElementById('album-art-img');
const albumArtPlaceholder = document.getElementById('album-art-placeholder');
const pauseButton = document.getElementById('pause-button');
const prevButton = document.getElementById('prev-button');
const nextButton = document.getElementById('next-button');
const themeButtons = Array.from(document.querySelectorAll('[data-theme]'));

let isPlaying = false;

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const err = new Error(`Request failed: ${response.status}`);
    err.status = response.status;
    try { const body = await response.json(); err.message = body.error || err.message; } catch {}
    throw err;
  }
  return response.json();
}

let _devices = [];

function activeDeviceName() {
  const active = _devices.find(d => d.is_active);
  return active ? active.name : (_devices[0] ? _devices[0].name : null);
}

async function loadDevices() {
  try {
    const payload = await fetchJson('/api/devices');
    _devices = payload.devices || [];
  } catch { _devices = []; }
}

function showPlaylists() {
  playlistPanel.hidden = false;
  hidePlaylistsButton.hidden = false;
  browseButton.hidden = true;
}

function hidePlaylists() {
  playlistPanel.hidden = true;
  hidePlaylistsButton.hidden = true;
  browseButton.hidden = false;
}

function updateAlbumArt(url) {
  if (url) {
    albumArtImg.src = url;
    albumArtImg.hidden = false;
    albumArtPlaceholder.hidden = true;
  } else {
    albumArtImg.hidden = true;
    albumArtPlaceholder.hidden = false;
  }
}

function renderPlaylists(playlists) {
  if (!playlists.length) {
    playlistList.innerHTML = '<p class="muted">No playlists available yet.</p>';
    return;
  }

  playlistList.innerHTML = '';
  playlists.forEach((playlist) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'playlist-card';
    button.dataset.playlistId = playlist.id;
    button.innerHTML = `
      <span class="playlist-name">${playlist.name}</span>
      <span class="playlist-meta">Tap to shuffle on Kitchen</span>
    `;
    button.addEventListener('click', async () => {
      button.disabled = true;
      trackTitle.textContent = `Starting ${playlist.name}…`;
      try {
        await fetchJson(`/api/playlists/${playlist.id}/play`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ device_name: activeDeviceName() }),
        });
        trackTitle.textContent = playlist.name;
        trackSubtitle.textContent = 'Shuffle playback requested';
        playbackDevice.textContent = activeDeviceName() ? `Playing on ${activeDeviceName()}` : 'Playback started';
        hidePlaylists();
      } catch (error) {
        if (error.status === 409) {
          trackTitle.textContent = 'No Spotify device found';
          trackSubtitle.textContent = 'Open Spotify on your Sonos or another device, then try again.';
        } else {
          trackTitle.textContent = 'Could not start playlist';
          trackSubtitle.textContent = error.message;
        }
      } finally {
        button.disabled = false;
      }
    });
    playlistList.appendChild(button);
  });
}

async function loadPlaylists() {
  playlistList.innerHTML = '<p class="muted">Loading playlists…</p>';
  try {
    const payload = await fetchJson('/api/playlists');
    renderPlaylists(payload.playlists || []);
  } catch (error) {
    playlistList.innerHTML = `<p class="muted">Failed to load playlists: ${error.message}</p>`;
  }
}

async function loadStatus() {
  try {
    const payload = await fetchJson('/api/status');
    const playback = payload.playback;
    if (playback?.track) {
      trackTitle.textContent = playback.track.title || 'Unknown track';
      trackSubtitle.textContent = `${playback.track.artist || 'Unknown'} · ${playback.track.album || 'Unknown album'}`;
      playbackDevice.textContent = playback.device_name ? `Playing on ${playback.device_name}` : 'No active device';
      updateAlbumArt(playback.track.album_art_url);
      isPlaying = playback.is_playing;
      pauseButton.textContent = isPlaying ? '⏸' : '▶';
      pauseButton.title = isPlaying ? 'Pause' : 'Resume';
    } else {
      updateAlbumArt(null);
    }
  } catch (error) {
    playbackDevice.textContent = `Status unavailable: ${error.message}`;
  }
}

async function previewTheme(themeName) {
  artworkCaption.textContent = `Loading ${themeName}…`;
  try {
    const payload = await fetchJson(`/api/art/next?theme=${encodeURIComponent(themeName)}`);
    const artwork = payload.artwork;
    artworkCaption.textContent = `${artwork.title} — ${artwork.artist} (${artwork.museum})`;
  } catch (error) {
    artworkCaption.textContent = `Failed to load ${themeName}: ${error.message}`;
  }
}

browseButton?.addEventListener('click', async () => {
  showPlaylists();
  await Promise.all([loadPlaylists(), loadDevices()]);
});

hidePlaylistsButton?.addEventListener('click', () => {
  hidePlaylists();
});

pauseButton?.addEventListener('click', async () => {
  try {
    if (isPlaying) {
      await fetchJson('/api/playback/pause', { method: 'POST' });
      isPlaying = false;
      pauseButton.textContent = '▶';
      pauseButton.title = 'Resume';
    } else {
      await fetchJson('/api/playback/resume', { method: 'POST' });
      isPlaying = true;
      pauseButton.textContent = '⏸';
      pauseButton.title = 'Pause';
    }
  } catch (error) {
    playbackDevice.textContent = `Control error: ${error.message}`;
  }
});

nextButton?.addEventListener('click', async () => {
  try {
    await fetchJson('/api/playback/next', { method: 'POST' });
    setTimeout(loadStatus, 800);
  } catch (error) {
    playbackDevice.textContent = `Control error: ${error.message}`;
  }
});

prevButton?.addEventListener('click', async () => {
  try {
    await fetchJson('/api/playback/prev', { method: 'POST' });
    setTimeout(loadStatus, 800);
  } catch (error) {
    playbackDevice.textContent = `Control error: ${error.message}`;
  }
});

themeButtons.forEach((button) => {
  button.addEventListener('click', async () => {
    await previewTheme(button.dataset.theme);
  });
});

// Show placeholder on startup until first status poll resolves
updateAlbumArt(null);

// ── Screensaver ───────────────────────────────────────────────────────────────

const screensaver = document.getElementById('screensaver');
const screensaverImg = document.getElementById('screensaver-img');
const screensaverCaption = document.getElementById('screensaver-caption');

let _idleTimeoutMs = 30 * 60 * 1000; // default 30 min, overridden from /api/config
let _slideshowIntervalMs = 30 * 1000;
let _idleTimer = null;
let _slideshowTimer = null;
let _screensaverActive = false;
let _currentTheme = null; // last theme tapped, or null → random from config

async function fetchNextArt() {
  const url = _currentTheme
    ? `/api/art/next?theme=${encodeURIComponent(_currentTheme)}`
    : '/api/art/next';
  try {
    const payload = await fetchJson(url);
    return payload.artwork;
  } catch {
    return null;
  }
}

async function advanceScreensaverArt() {
  const art = await fetchNextArt();
  if (!art) return;

  // Crossfade: fade out, swap src, fade in
  screensaverImg.style.opacity = '0';
  await new Promise(r => setTimeout(r, 600));
  screensaverImg.src = art.image_url || '';
  screensaverCaption.textContent =
    art.title && art.artist
      ? `${art.title} — ${art.artist}${art.year ? ` (${art.year})` : ''}`
      : '';
  screensaverImg.style.opacity = '1';
}

function startScreensaver() {
  if (_screensaverActive) return;
  _screensaverActive = true;
  screensaver.classList.add('is-active');
  screensaver.removeAttribute('aria-hidden');
  advanceScreensaverArt();
  _slideshowTimer = setInterval(advanceScreensaverArt, _slideshowIntervalMs);
}

function stopScreensaver() {
  if (!_screensaverActive) return;
  _screensaverActive = false;
  screensaver.classList.remove('is-active');
  screensaver.setAttribute('aria-hidden', 'true');
  clearInterval(_slideshowTimer);
  _slideshowTimer = null;
  resetIdleTimer();
}

function resetIdleTimer() {
  clearTimeout(_idleTimer);
  _idleTimer = setTimeout(startScreensaver, _idleTimeoutMs);
}

// Dismiss screensaver on any interaction
screensaver.addEventListener('click', stopScreensaver);
screensaver.addEventListener('touchstart', stopScreensaver, { passive: true });

// Reset idle timer on any user interaction with the main UI
['click', 'touchstart', 'keydown', 'mousemove'].forEach(evt => {
  document.addEventListener(evt, () => {
    if (!_screensaverActive) resetIdleTimer();
  }, { passive: true });
});

// Track which theme the user last tapped so screensaver uses same theme
themeButtons.forEach(button => {
  button.addEventListener('click', () => {
    _currentTheme = button.dataset.theme;
  });
});

// Load timings from server config then start idle timer
(async () => {
  try {
    const cfg = await fetchJson('/api/config');
    _idleTimeoutMs = (cfg.idle_timeout_seconds || 1800) * 1000;
    _slideshowIntervalMs = (cfg.slideshow_interval_seconds || 30) * 1000;
  } catch { /* use defaults */ }
  resetIdleTimer();
})();

// Initial load + poll every 10 seconds
loadStatus();
loadDevices();
setInterval(loadStatus, 10_000);
