const http = require('http');
const { createHandlers } = require('netlify-cms-oauth-provider-node');

const port = Number(process.env.PORT || 3100);
const origin = process.env.CMS_ORIGIN || 'https://paper.adslab.icu';
const completeUrl = `${origin}/api/admin/auth/complete`;
const handlers = createHandlers({
  origin,
  completeUrl,
  adminPanelUrl: `${origin}/admin/`,
  oauthProvider: 'github',
}, { useEnv: true });

function send(res, status, body, headers = {}) {
  res.writeHead(status, { 'Content-Type': 'text/plain; charset=utf-8', ...headers });
  res.end(body);
}

async function handle(req, res) {
  const url = new URL(req.url, origin);

  if (req.method !== 'GET') {
    send(res, 405, 'Method Not Allowed');
    return;
  }

  if (url.pathname === '/api/admin/auth/begin') {
    const authorizationUrl = await handlers.begin();
    send(res, 302, 'Redirecting to GitHub...', { Location: authorizationUrl });
    return;
  }

  if (url.pathname === '/api/admin/auth/complete') {
    const code = url.searchParams.get('code');
    const content = await handlers.complete(code);
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(content);
    return;
  }

  if (url.pathname === '/health') {
    send(res, 200, 'ok');
    return;
  }

  send(res, 404, 'Not Found');
}

const server = http.createServer((req, res) => {
  handle(req, res).catch(error => {
    console.error(error);
    send(res, 500, 'OAuth service error');
  });
});

server.listen(port, '0.0.0.0', () => {
  console.log(`Paper knowledge base OAuth service listening on ${port}`);
});

