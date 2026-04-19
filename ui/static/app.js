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

// Initial load + poll every 10 seconds
loadStatus();
loadDevices();
setInterval(loadStatus, 10_000);
