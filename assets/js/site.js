// Share button: native share sheet on phones, copy-link on desktop.
// Every outcome is shown to the reader — nothing fails silently.
document.querySelectorAll('.share').forEach(function (btn) {
  var status = btn.parentElement.querySelector('.share-status');
  btn.addEventListener('click', function () {
    var url = btn.dataset.shareUrl;
    var title = btn.dataset.shareTitle;
    if (navigator.share) {
      navigator.share({ title: title, url: url }).catch(function (err) {
        if (err.name !== 'AbortError') status.textContent = 'Could not open sharing: ' + err.message;
      });
      return;
    }
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(
        function () { status.textContent = 'Link copied.'; },
        function () { status.textContent = 'Copy this link: ' + url; }
      );
      return;
    }
    status.textContent = 'Copy this link: ' + url;
  });
});

// Words page: filter the glossary as you type.
var filter = document.getElementById('word-filter');
if (filter) {
  var strip = function (t) { return t.toLowerCase().replace(/['’ʼ]/g, '').replace(/[\u0591-\u05C7]/g, ''); };
  var rows = Array.prototype.slice.call(document.querySelectorAll('.gloss-item'));
  rows.forEach(function (r) { r.dataset.search = strip(r.textContent); });
  var empty = document.getElementById('word-empty');
  filter.addEventListener('input', function () {
    var q = strip(filter.value.trim());
    var shown = 0;
    rows.forEach(function (r) {
      var hit = !q || r.dataset.search.indexOf(q) !== -1;
      r.hidden = !hit;
      if (hit) shown++;
    });
    empty.hidden = shown !== 0;
  });
}

// Chapters page: mark today's chapter (day of the month).
// Day of the month in Eastern time, the same clock the daily study runs on.
var easternDay = Number(new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', day: 'numeric' }).format(new Date()));
var todayTile = document.querySelector('.ch-tile[href$="#ch-' + easternDay + '"]');
if (todayTile) todayTile.classList.add('is-today');

// Listen: play the narrated study. Lock-screen controls where the phone supports them.
document.querySelectorAll('.listen').forEach(function (box) {
  var audio = box.querySelector('audio');
  var btn = box.querySelector('.listen-play');
  var seek = box.querySelector('.listen-seek');
  var now = box.querySelector('.listen-now');
  var status = box.querySelector('.listen-status');
  var dragging = false;
  var fmt = function (t) { t = Math.max(0, Math.floor(t || 0)); return Math.floor(t / 60) + ':' + ('0' + (t % 60)).slice(-2); };
  var paint = function (t) {
    now.textContent = fmt(t);
    seek.style.setProperty('--fill', (seek.max > 0 ? (t / seek.max) * 100 : 0) + '%');
  };

  btn.addEventListener('click', function () {
    status.textContent = '';
    if (audio.paused) {
      box.classList.add('is-loading');
      var p = audio.play();
      if (p && p.catch) p.catch(function (err) {
        box.classList.remove('is-loading');
        if (err.name !== 'AbortError') status.textContent = 'Could not start the audio: ' + err.message;
      });
    } else {
      audio.pause();
    }
  });
  audio.addEventListener('playing', function () {
    box.classList.remove('is-loading');
    box.classList.add('is-playing');
    btn.setAttribute('aria-label', 'Pause');
    if ('mediaSession' in navigator && window.MediaMetadata) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: box.dataset.title, artist: 'Daily Proverbs',
        artwork: [{ src: box.dataset.art, sizes: '600x600', type: 'image/jpeg' }]
      });
    }
  });
  audio.addEventListener('pause', function () {
    box.classList.remove('is-playing', 'is-loading');
    btn.setAttribute('aria-label', 'Play');
  });
  audio.addEventListener('loadedmetadata', function () { if (isFinite(audio.duration)) seek.max = Math.round(audio.duration); });
  audio.addEventListener('timeupdate', function () { if (!dragging) { seek.value = audio.currentTime; paint(audio.currentTime); } });
  audio.addEventListener('ended', function () { seek.value = 0; paint(0); });
  audio.addEventListener('error', function () {
    box.classList.remove('is-playing', 'is-loading');
    status.textContent = 'The audio would not load here. Use Download MP3 instead.';
  });
  seek.addEventListener('input', function () { dragging = true; paint(Number(seek.value)); });
  var pending = null;
  seek.addEventListener('change', function () {
    dragging = false;
    if (audio.readyState === 0) { pending = Number(seek.value); audio.load(); }
    else audio.currentTime = Number(seek.value);
  });
  audio.addEventListener('loadedmetadata', function () {
    if (pending !== null) { audio.currentTime = pending; pending = null; }
  });
});

// Listen page: copy the podcast link for any podcast app.
document.querySelectorAll('[data-copy]').forEach(function (btn) {
  var status = btn.parentElement.querySelector('.share-status');
  btn.addEventListener('click', function () {
    var text = btn.dataset.copy;
    if (!navigator.clipboard) { status.textContent = 'Copy this link: ' + text; return; }
    navigator.clipboard.writeText(text).then(
      function () { status.textContent = 'Link copied. Paste it into your podcast app.'; },
      function () { status.textContent = 'Copy this link: ' + text; }
    );
  });
});
