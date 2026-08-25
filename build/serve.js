// Minimal static file server for the screenshot runs. Puppeteer needs the
// pages on http:// rather than file:// because player.js fetch()es the .hex.
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = process.argv[2] || process.cwd();
const PORT = Number(process.argv[3] || 8123);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.hex': 'text/plain; charset=utf-8',
  '.img': 'application/octet-stream',
  '.png': 'image/png',
  '.json': 'application/json',
};

const server = http.createServer((req, res) => {
  const rel = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '');
  const file = path.resolve(ROOT, rel || 'index.html');
  if (!file.startsWith(path.resolve(ROOT))) {
    res.writeHead(403).end('forbidden');
    return;
  }
  fs.readFile(file, (err, data) => {
    if (err) {
      res.writeHead(404).end('not found');
      return;
    }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream' });
    res.end(data);
  });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log('serving ' + ROOT + ' on http://127.0.0.1:' + PORT);
});
