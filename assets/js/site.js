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
