// Capture a screenshot of every built .hex by running it in the Simbuino4Web
// emulator under headless Chrome.
//
// Gamebuino Classic games nearly all boot into the library's own logo splash,
// then gb.titleScreen(), which waits for the A button. So for each game we let
// it run past the splash, grab the title screen, press A, let it run again and
// grab gameplay -- then keep whichever frame actually has something on it.
//
// usage: node shots.js [--only slug,slug] [--force]

const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const SITE = process.env.SITE_ROOT || 'C:/github/gamebuino_classic_games_compiled';
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8123';
const OUT = path.join(SITE, 'screenshots');
const SCALE = 4;                 // 84x48 -> 336x192
const CONCURRENCY = 4;

// how the frame is reached: run past the boot splash, then press A this many
// times with a pause after each, then let the game settle before grabbing
const PRE_FRAMES = 200;       // ~3.3 s
const A_PRESSES = 4;
const BETWEEN_FRAMES = 130;   // ~2.2 s after each press
const SETTLE_FRAMES = 200;    // ~3.3 s before the grab

// games that read data off an SD card need the card image mounted
const NEEDS_SD = new Set(['B-Rally', 'gamebuino-community-rpg', 'sd_map_test']);

// cruiser fires a bullet on A and dereferences a wild pointer doing it
// (X = 0x9306, past the end of RAM). The standalone Simbuino crashes on
// that too, so it is the game's own bug -- capture it flying instead.
const SKIP_A = new Set(['cruiser']);

const args = process.argv.slice(2);
const only = args.includes('--only')
  ? new Set(args[args.indexOf('--only') + 1].split(','))
  : null;
const force = args.includes('--force');

function listHex(dir) {
  const p = path.join(SITE, dir);
  if (!fs.existsSync(p)) return [];
  return fs.readdirSync(p)
    .filter(f => f.toLowerCase().endsWith('.hex'))
    .map(f => ({ slug: path.basename(f, path.extname(f)), dir }));
}

// Runs inside the page: rasterise the 84x48 LCD to a scaled PNG and score it.
const PAGE_HELPERS = `
  window.__grab = function (scale) {
    var src = document.getElementById('canvas');
    var img = src.getContext('2d').getImageData(0, 0, 84, 48);
    var d = img.data;

    // "lit" = a dark LCD pixel; the backlight colour is the light one
    var lit = 0, edges = 0;
    function on(x, y) { return d[(y * 84 + x) * 4] < 128 ? 1 : 0; }
    for (var y = 0; y < 48; y++) {
      for (var x = 0; x < 84; x++) {
        lit += on(x, y);
        if (x + 1 < 84 && on(x, y) !== on(x + 1, y)) edges++;
        if (y + 1 < 48 && on(x, y) !== on(x, y + 1)) edges++;
      }
    }

    var out = document.createElement('canvas');
    out.width = 84 * scale;
    out.height = 48 * scale;
    var ctx = out.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.mozImageSmoothingEnabled = false;
    ctx.webkitImageSmoothingEnabled = false;
    ctx.drawImage(src, 0, 0, out.width, out.height);
    return { png: out.toDataURL('image/png'), lit: lit / 4032, edges: edges };
  };
`;

async function shoot(browser, game) {
  const dest = path.join(OUT, game.slug + '.png');
  if (!force && fs.existsSync(dest)) return { slug: game.slug, skipped: true };

  const page = await browser.newPage();
  await page.setViewport({ width: 400, height: 300 });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  try {
    let url = `${BASE}/webemulator/player.html?hex=/${game.dir}/${encodeURIComponent(game.slug)}.hex`
            + `&title=${encodeURIComponent(game.slug)}`;
    if (NEEDS_SD.has(game.slug)) url += '&sd=/webemulator/sdcard.img';

    await page.goto(url, { waitUntil: 'load', timeout: 30000 });
    await page.evaluate(PAGE_HELPERS);
    await page.evaluate(`var PRE_FRAMES=${PRE_FRAMES},A_PRESSES=${A_PRESSES},BETWEEN_FRAMES=${BETWEEN_FRAMES},SETTLE_FRAMES=${SETTLE_FRAMES},PRESS_A=${!SKIP_A.has(game.slug)};`);

    const ok = await page.evaluate(async () => {
      const wait = ms => new Promise(r => setTimeout(r, ms));
      for (let i = 0; i < 100; i++) {
        if (window.SimbuinoPlayer.ready) return true;
        if (window.SimbuinoPlayer.error) return false;
        await wait(100);
      }
      return false;
    });
    if (!ok) {
      const err = await page.evaluate(() => window.SimbuinoPlayer.error);
      return { slug: game.slug, error: err || 'never became ready' };
    }

    const shot = await page.evaluate(async (scale) => {
      const P = window.SimbuinoPlayer;
      const blank = c => !c || c.lit < 0.02 || c.lit > 0.92;

      // Past the library's boot splash. gb.titleScreen() waits for A, and
      // plenty of these sit behind a menu, a difficulty select and a "get
      // ready" screen too, so press A several times with a pause after each
      // and let the game settle before taking the frame.
      await P.runFrames(PRE_FRAMES);
      const title = Object.assign({ tag: 'title' }, window.__grab(scale));

      const seen = [];
      for (let i = 0; i < (PRESS_A ? A_PRESSES : 0); i++) {
        await P.press('A', 10);
        await P.runFrames(BETWEEN_FRAMES);
        seen.push(Object.assign({ tag: 'press' + (i + 1) }, window.__grab(scale)));
      }
      if (!PRESS_A) await P.runFrames(BETWEEN_FRAMES * A_PRESSES);
      await P.runFrames(SETTLE_FRAMES);
      let c = Object.assign({ tag: 'settled' }, window.__grab(scale));

      // a wipe or a flashing screen can leave that frame empty; give it longer
      // and look again before deciding
      for (let retry = 0; retry < 2 && blank(c); retry++) {
        await P.runFrames(SETTLE_FRAMES * 2);
        c = Object.assign({ tag: 'settled' }, window.__grab(scale));
      }
      if (!blank(c)) return c;

      // The settled frame is what we want, but a few programs genuinely show
      // nothing there -- a paint tool opens on an empty canvas, a snake starts
      // as one pixel. Rather than leave the card with no image, fall back to
      // the richest frame actually seen, and to the title card last of all.
      const alt = seen.filter(x => !blank(x)).sort((a, b) => b.edges - a.edges)[0];
      if (alt) return alt;
      if (!blank(title)) return title;
      return Object.assign({ blank: true }, c);
    }, SCALE);

    if (shot.blank) return { slug: game.slug, error: 'nothing rendered at any point' };
    const pick = shot;

    fs.writeFileSync(dest, Buffer.from(pick.png.split(',')[1], 'base64'));
    return { slug: game.slug, tag: pick.tag, lit: +pick.lit.toFixed(3), edges: pick.edges };
  } catch (e) {
    return { slug: game.slug, error: e.message + (errors.length ? ' | ' + errors[0] : '') };
  } finally {
    await page.close();
  }
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  let games = [...listHex('games'), ...listHex('tools')];
  if (only) games = games.filter(g => only.has(g.slug));

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--mute-audio', '--no-sandbox', '--disable-dev-shm-usage',
           '--autoplay-policy=no-user-gesture-required'],
  });

  const queue = games.slice();
  const results = [];
  await Promise.all(Array.from({ length: CONCURRENCY }, async () => {
    while (queue.length) {
      const g = queue.shift();
      const r = await shoot(browser, g);
      results.push(r);
      const note = r.skipped ? 'skip' : r.error ? 'FAIL ' + r.error
        : `${r.tag === 'settled' ? '' : '[fallback ' + r.tag + '] '}lit=${r.lit} edges=${r.edges}`;
      console.log(`${results.length}/${games.length}  ${r.slug}  ${note}`);
    }
  }));

  await browser.close();
  fs.writeFileSync(path.join(OUT, '_report.json'), JSON.stringify(results, null, 1));
  const bad = results.filter(r => r.error);
  console.log(`\ncaptured ${results.filter(r => !r.error && !r.skipped).length}, skipped ${results.filter(r => r.skipped).length}, failed ${bad.length}`);
  bad.forEach(r => console.log('  FAIL ' + r.slug + ': ' + r.error));
})();
