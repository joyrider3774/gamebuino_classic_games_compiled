"""Generate index.html for the Gamebuino Classic web collection from site.json."""
import os, re, json, html, datetime

BUILD = r"C:\gbbuild"
SITE = os.environ.get("GB_SITE", r"C:\github\gamebuino_classic_games_compiled")

# entries that read a data file off the SD card, so the player mounts the
# shared card image for them (see mksd.py for what is on it)
NEEDS_SD = {'B-Rally', 'gamebuino-community-rpg', 'sd_map_test', 'Wolfenduino', 'Gamebookuino'}

CSS = """
  :root {
    color-scheme: dark;
    --bg: #0a0d0c;
    --panel: #121716;
    --panel-border: #22302c;
    --text: #e6efec;
    --muted: #93a8a2;
    /* the Nokia 5110 panel the Gamebuino Classic uses: unlit green-grey,
       lit blue-white backlight, near-black pixels */
    --lcd-off: #8fa79a;
    --lcd-on: #cedde7;
    --lcd-ink: #404040;
    --accent: #7fd4c1;
    --link: #7fd4ff;
  }

  * { box-sizing: border-box; }

  html, body {
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--text);
    font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }

  a { color: var(--link); }

  header {
    padding: 3em 1.5em 1.5em;
    text-align: center;
    background:
      radial-gradient(ellipse at top, rgba(127, 212, 193, 0.10), transparent 60%),
      var(--bg);
    border-bottom: 1px solid var(--panel-border);
  }

  header h1 {
    margin: 0 0 0.3em;
    font-size: 2em;
    letter-spacing: 0.02em;
  }

  header h1 .logo {
    display: inline-block;
    padding: 0.1em 0.45em;
    border-radius: 4px;
    background: var(--lcd-on);
    color: #2b2b2b;
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    letter-spacing: -0.02em;
  }

  header p {
    margin: 0.3em auto;
    color: var(--muted);
    max-width: 46em;
  }

  header .links { margin-top: 1em; font-size: 0.95em; }
  header .links a { margin: 0 0.6em; }

  .toolbar {
    position: sticky;
    top: 0;
    z-index: 5;
    background: rgba(10, 13, 12, 0.94);
    backdrop-filter: blur(6px);
    border-bottom: 1px solid var(--panel-border);
    padding: 0.7em 1.5em;
    display: flex;
    gap: 0.6em;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
  }

  .toolbar input[type=search] {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 5px;
    color: var(--text);
    padding: 0.45em 0.8em;
    font: inherit;
    font-size: 0.9em;
    min-width: 16em;
  }

  .toolbar input[type=search]:focus {
    outline: none;
    border-color: var(--accent);
  }

  .toolbar .tab {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 5px;
    color: var(--muted);
    padding: 0.45em 0.9em;
    font: inherit;
    font-size: 0.9em;
    cursor: pointer;
  }

  .toolbar .tab[aria-pressed="true"] {
    color: #0a0d0c;
    background: var(--accent);
    border-color: var(--accent);
    font-weight: 600;
  }

  .toolbar .count { color: var(--muted); font-size: 0.85em; }

  main { max-width: 1280px; margin: 0 auto; padding: 2em 1.5em 4em; }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1.3em;
  }

  .card {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: transform 0.15s ease, border-color 0.15s ease;
  }

  .card:hover { transform: translateY(-3px); border-color: var(--accent); }
  .card[hidden] { display: none; }

  /* Screenshots are native 84x48 upscaled 4x; keep them blocky rather than
     letting the browser smooth them into mush. */
  .card .shot {
    width: 100%;
    aspect-ratio: 84 / 48;
    display: block;
    object-fit: cover;
    background: var(--lcd-on);
    image-rendering: pixelated;
    image-rendering: crisp-edges;
  }

  .card .noshot {
    width: 100%;
    aspect-ratio: 84 / 48;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--lcd-off);
    color: #4a4a4a;
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    font-size: 0.8em;
    text-align: center;
    padding: 1em;
  }

  .card .body {
    padding: 0.85em 1em 1em;
    display: flex;
    flex-direction: column;
    flex: 1;
    gap: 0.35em;
  }

  .card h2 { margin: 0; font-size: 1.02em; line-height: 1.3; }
  .card h2 a { color: var(--text); text-decoration: none; }
  .card h2 a:hover { color: var(--accent); }

  .card .by { color: var(--muted); font-size: 0.85em; }
  .card .desc { color: var(--muted); font-size: 0.85em; margin: 0.15em 0 0; }

  .card .meta {
    color: #6f837d;
    font-size: 0.75em;
    margin-top: auto;
    padding-top: 0.7em;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4em 0.8em;
  }

  .card .actions {
    display: flex;
    gap: 0.6em;
    align-items: center;
    flex-wrap: wrap;
    padding-top: 0.7em;
  }

  .play-button {
    display: inline-block;
    background: var(--accent);
    color: #08110e;
    font-weight: 600;
    text-decoration: none;
    padding: 0.4em 0.85em;
    border-radius: 5px;
    font-size: 0.88em;
  }

  .play-button:hover { background: #a5efe0; }

  .dl-button {
    display: inline-block;
    background: transparent;
    color: var(--muted);
    border: 1px solid var(--panel-border);
    text-decoration: none;
    padding: 0.4em 0.7em;
    border-radius: 5px;
    font-size: 0.88em;
  }

  .dl-button:hover { color: var(--accent); border-color: var(--accent); }

  .src-link { font-size: 0.82em; color: var(--muted); text-decoration: none; }
  .src-link:hover { color: var(--link); }

  .badge {
    border: 1px solid var(--panel-border);
    border-radius: 3px;
    padding: 0 0.4em;
    color: var(--muted);
  }

  .badge.flag {
    border-color: #4d5f59;
    color: #b6cdc5;
  }

  #empty { color: var(--muted); text-align: center; padding: 3em 0; }
  #empty[hidden] { display: none; }

  footer {
    max-width: 1280px;
    margin: 0 auto;
    padding: 0 1.5em 3em;
    color: var(--muted);
    font-size: 0.85em;
  }

  footer hr { border: none; border-top: 1px solid var(--panel-border); margin: 2em 0 1.2em; }
  footer h3 { color: var(--text); font-size: 0.95em; margin: 1.4em 0 0.4em; }

  footer .controls-table {
    display: inline-grid;
    grid-template-columns: repeat(2, auto);
    gap: 0.2em 1.2em;
    margin: 0.6em 0 0;
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  }

  footer .controls-table span.key { color: var(--accent); }

  #game-overlay {
    position: fixed;
    inset: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.9);
    padding: 2vh 2vw;
  }

  #game-overlay.hidden { display: none; }

  #game-modal {
    position: relative;
    width: 760px;
    height: 620px;
    max-width: 100%;
    max-height: 100%;
    background: #000;
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
  }

  #game-frame { width: 100%; height: 100%; border: 0; display: block; }

  #game-close-button {
    position: absolute;
    top: 0.4em;
    right: 0.5em;
    z-index: 1;
    background: rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.4);
    color: #eee;
    border-radius: 4px;
    width: 1.8em;
    height: 1.8em;
    line-height: 1.6em;
    text-align: center;
    padding: 0;
    font-size: 1em;
    cursor: pointer;
  }

  #game-close-button:hover { background: rgba(0, 0, 0, 0.85); }
"""

JS = """
  // Play/title links stay real <a href> targets so right-click / middle-click
  // / ctrl-click "open in new tab" and the no-JS fallback keep working; a
  // plain left-click instead loads the same URL into an iframe overlay.
  // Closing resets the iframe to about:blank rather than just hiding it -
  // otherwise the emulator (and its audio) would keep running invisibly.
  var gameOverlay = document.getElementById('game-overlay');
  var gameFrame = document.getElementById('game-frame');

  function openGame(url) {
    gameFrame.src = url;
    gameOverlay.classList.remove('hidden');
  }

  function closeGame() {
    gameOverlay.classList.add('hidden');
    gameFrame.src = 'about:blank';
  }

  document.querySelectorAll('a[data-play]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)
        return;
      e.preventDefault();
      openGame(link.getAttribute('href'));
    });
  });

  document.getElementById('game-close-button').addEventListener('click', closeGame);

  gameOverlay.addEventListener('click', function (e) {
    if (e.target === gameOverlay) closeGame();
  });

  window.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !gameOverlay.classList.contains('hidden')) closeGame();
  });

  // ---- filtering -------------------------------------------------------
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  var search = document.getElementById('search');
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tab'));
  var countEl = document.getElementById('count');
  var emptyEl = document.getElementById('empty');
  var kind = 'all';
  var source = null;

  function apply() {
    var q = search.value.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (card) {
      var okKind = (kind === 'all') || (card.dataset.kind === kind);
      var okSource = !source || (card.dataset.source === source);
      var okText = !q || card.dataset.search.indexOf(q) !== -1;
      var show = okKind && okSource && okText;
      card.hidden = !show;
      if (show) shown++;
    });
    countEl.textContent = shown + (shown === 1 ? ' entry' : ' entries');
    emptyEl.hidden = shown !== 0;
  }

  search.addEventListener('input', apply);
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      // the three kind tabs and the source tab are one exclusive group
      kind = tab.dataset.kind || 'all';
      source = tab.dataset.source || null;
      tabs.forEach(function (t) { t.setAttribute('aria-pressed', String(t === tab)); });
      apply();
    });
  });
  apply();
"""


def short_83(e, used):
    """A DOS 8.3 filename for the download.

    The Gamebuino Classic's loader reads short names off a FAT card, so
    "Worlds-Hardest-Game-Gamebuino.hex" is no use on real hardware. The file
    keeps its descriptive name in this repository; only the name the browser
    saves it under is shortened, and it is kept unique across the collection.
    """
    base = re.sub(r'[^A-Z0-9]', '', e['title'].upper())
    # a good few of these are literally named "Gamebuino <something>"; the
    # prefix says nothing here and would eat all eight characters
    if len(base) > 9 and base.startswith('GAMEBUINO'):
        base = base[9:]
    base = base or re.sub(r'[^A-Z0-9]', '', e['slug'].upper()) or 'GAME'

    name, n = base[:8], 1
    while name in used:
        n += 1
        suffix = str(n)
        name = base[:8 - len(suffix)] + suffix
    used.add(name)
    return name + '.HEX'


def card_html(e):
    title = html.escape(e['title'])
    # the hex/sd URLs are fetched by player.html, so they must be relative
    # to webemulator/, not to this page
    play = ('webemulator/player.html?hex=../' + e['hex']
            + '&amp;title=' + html.escape(e['title'].replace(' ', '+')))
    if e['slug'] in NEEDS_SD:
        play += '&amp;sd=sdcard.img'

    if e['shot']:
        art = ('<img class="shot" src="%s" alt="%s screenshot" loading="lazy" width="336" height="192">'
               % (e['shot'], title))
    else:
        art = '<div class="noshot">no preview<br>available</div>'

    bits = ['<div class="card" data-kind="%s" data-source="%s" data-search="%s">' % (
        e['top'],
        'binary' if e.get('precompiled') else 'source',
        html.escape((e['title'] + ' ' + e['author'] + ' ' + e['desc'] + ' ' + e['slug']
                     + (' binary only precompiled' if e.get('precompiled') else '')).lower())),
        '  ' + art,
        '  <div class="body">',
        '    <h2><a href="%s" data-play>%s</a></h2>' % (play, title)]

    if e['author']:
        bits.append('    <div class="by">by %s</div>' % html.escape(e['author']))
    if e['desc']:
        bits.append('    <p class="desc">%s</p>' % html.escape(e['desc']))

    meta = []
    if e['license']:
        lic = e['license']
        short = lic if len(lic) < 26 else lic.split('(')[0].split('\u2014')[0].strip()[:24] + '\u2026'
        meta.append('<span class="badge" title="%s">%s</span>' % (html.escape(lic), html.escape(short)))
    if e['flash']:
        meta.append('<span>%s KB flash</span>' % round(e['flash']['bytes'] / 1024, 1))
    if e.get('precompiled'):
        meta.append('<span class="badge flag" title="No source for this one survives anywhere. '
                    'The archive recovered a compiled binary only, so it cannot be rebuilt.">'
                    'binary&nbsp;only</span>')
    elif e['prebuilt']:
        meta.append('<span class="badge flag" title="Source exists, but this ships the author\u2019s own '
                    'prebuilt .hex rather than a rebuild">prebuilt&nbsp;hex</span>')
    if meta:
        bits.append('    <div class="meta">%s</div>' % ''.join(meta))

    actions = ['<a class="play-button" href="%s" data-play>&#9654; Play</a>' % play]
    # The Gamebuino's own loader reads 8.3 names off the card, so the file is
    # offered under one -- the copy on disk keeps its descriptive slug.
    actions.append('<a class="dl-button" href="%s" download="%s" '
                   'title="Download %s &ndash; ready to copy onto a Gamebuino SD card">'
                   '&#11015; .hex</a>' % (e['hex'], e['dl'], e['dl']))
    if e['url']:
        actions.append('<a class="src-link" href="%s" target="_blank" rel="noopener">Original repo</a>' % html.escape(e['url']))
    # Only entries the archive really holds as files get an archived link. For
    # a submodule that folder is just a commit pointer, so the upstream repo
    # above is the only place the source actually is.
    if e.get('archive'):
        actions.append('<a class="src-link" href="%s" target="_blank" rel="noopener">Archived source</a>' % html.escape(e['archive']))
    bits.append('    <div class="actions">%s</div>' % ''.join(actions))

    bits += ['  </div>', '</div>']
    return '\n      '.join(bits)


def main():
    entries = json.load(open(os.path.join(BUILD, 'site.json')))
    used = set()
    for e in entries:
        e['dl'] = short_83(e, used)
    games = sum(1 for e in entries if e['top'] == 'games')
    tools = sum(1 for e in entries if e['top'] == 'tools')
    binary = sum(1 for e in entries if e.get('precompiled'))
    built = datetime.date.today().isoformat()

    cards = '\n\n      '.join(card_html(e) for e in entries)

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 32 32%27%3E%3Crect width=%2732%27 height=%2732%27 rx=%274%27 fill=%27%23121716%27/%3E%3Crect x=%274%27 y=%278%27 width=%2724%27 height=%2714%27 fill=%27%23cedde7%27/%3E%3Crect x=%277%27 y=%2711%27 width=%274%27 height=%274%27 fill=%27%23404040%27/%3E%3Crect x=%2714%27 y=%2715%27 width=%274%27 height=%274%27 fill=%27%23404040%27/%3E%3Crect x=%2721%27 y=%2711%27 width=%274%27 height=%274%27 fill=%27%23404040%27/%3E%3C/svg%3E">
<title>Gamebuino Classic Games</title>
<meta name="description" content="{games} Gamebuino Classic games and {tools} tools, compiled from archived source and playable in the browser.">
<style>{CSS}</style>
</head>
<body>

<header>
  <h1><span class="logo">GAMEBUINO</span> Classic &mdash; playable in your browser</h1>
  <p>Every Gamebuino Classic game and tool whose source could still be found, compiled
     from that source and running here on Myndale&rsquo;s Simbuino HTML5 emulator.
     The console was an ATmega328 handheld with an 84&times;48 Nokia&nbsp;5110 screen,
     and its community wiki &mdash; along with most of what it linked to &mdash; is long gone from the live web.</p>
  <p><strong>{games}</strong> games and <strong>{tools}</strong> tools. Nothing here is my own work:
     every entry is someone else&rsquo;s game, credited below with its own licence.</p>
  <div class="links">
    <a href="https://github.com/joyrider3774/gamebuino_classic_source_codes" target="_blank" rel="noopener">The source archive</a>
    &middot;
    <a href="https://github.com/Myndale/Simbuino" target="_blank" rel="noopener">Simbuino emulator</a>
    &middot;
    <a href="https://github.com/joyrider3774/gamebuino_classic_vircon32" target="_blank" rel="noopener">The Vircon32 port</a>
    &middot;
    <a href="https://github.com/joyrider3774/gamebuino_classic_sdl" target="_blank" rel="noopener">The SDL port</a>
  </div>
</header>

<div class="toolbar">
  <input type="search" id="search" placeholder="Search by name, author or description&hellip;" autocomplete="off">
  <button class="tab" type="button" data-kind="all" aria-pressed="true">All</button>
  <button class="tab" type="button" data-kind="games" aria-pressed="false">Games ({games})</button>
  <button class="tab" type="button" data-kind="tools" aria-pressed="false">Tools ({tools})</button>
  <button class="tab" type="button" data-source="binary" aria-pressed="false">Binary only ({binary})</button>
  <span class="count" id="count"></span>
</div>

<main>
  <div class="grid">

      {cards}

  </div>
  <p id="empty" hidden>Nothing matches that search.</p>
</main>

<footer>
  <hr>

  <h3>Controls</h3>
  <p>Every game runs in the same emulator, with the same keys:</p>
  <div class="controls-table">
    <span><span class="key">Arrows</span> or <span class="key">ESDF</span></span><span>D-pad</span>
    <span><span class="key">X</span> or <span class="key">K</span></span><span>A button</span>
    <span><span class="key">Z</span> or <span class="key">L</span></span><span>B button</span>
    <span><span class="key">C</span> or <span class="key">R</span></span><span>C button</span>
  </div>
  <p>Most games open on a title screen and start with <span class="key">A</span>.
     On a phone, on-screen buttons appear instead.</p>

  <h3>How this was built</h3>
  <p>Each entry was compiled from the archived source with the Arduino IDE 1.8.19 AVR
     toolchain, targeting the ATmega328 at 16&nbsp;MHz, against Gamebuino Classic library 0.5.2.
     A number of sketches needed small fixes to build on a modern avr-gcc &mdash; mostly
     <code>PROGMEM</code> data that now has to be <code>const</code>, the removed
     <code>prog_uchar</code> type, and pre-2014 library API calls. Those fixes were applied to
     build-time copies; the source archive itself is untouched.
     A few entries ship only as a prebuilt <code>.hex</code> from their own author and are
     marked as such.
     Screenshots were captured by running each build in the emulator under headless Chrome.</p>

  <h3>Credits</h3>
  <p>The emulator is <a href="https://github.com/Myndale/Simbuino" target="_blank" rel="noopener">Simbuino4Web</a>
     by Mark Feldman (&ldquo;Myndale&rdquo;), MIT-licensed, adapted here into a standalone page
     that loads a game from a URL.
     The Gamebuino Classic and its library are by Aur&eacute;lien Rodot and contributors.
     Every game and tool belongs to its own author and keeps its own licence &mdash; see each card,
     and the <a href="https://github.com/joyrider3774/gamebuino_classic_source_codes" target="_blank" rel="noopener">source archive</a>
     for the full licence notes. Several entries have <em>no licence specified at all</em> by
     their original author; that is noted rather than assumed permissive.</p>

  <p style="margin-top:2em">Built {built}.</p>
</footer>

<div id="game-overlay" class="hidden">
  <div id="game-modal">
    <button id="game-close-button" aria-label="Close">&times;</button>
    <iframe id="game-frame" allow="autoplay; fullscreen" allowfullscreen></iframe>
  </div>
</div>

<script>{JS}</script>

</body>
</html>
"""
    out = os.path.join(SITE, 'index.html')
    open(out, 'w', encoding='utf-8').write(doc)
    print('wrote', out, len(doc), 'bytes,', len(entries), 'cards')


if __name__ == '__main__':
    main()
