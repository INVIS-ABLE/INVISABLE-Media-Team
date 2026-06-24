# Cloudflare lockdown for `media.invisable.co.uk`

The media PWA/API must **not** be publicly accessible. This folder pins down how the
single allowed endpoint is exposed and protected.

```
Public internet ──▶ Cloudflare edge ──▶ Cloudflare Access (Zero Trust)
                                              │  (only Stephen's login passes)
                                              ▼
                                   Cloudflare Tunnel (cloudflared)
                                              │
                                              ▼
                              Server · core API + PWA  http://localhost:8080
                                   /app  (PWA)   /api  (desktop API)
```

Everything else on the server — PostgreSQL, ChromaDB, n8n admin, Postiz admin,
ComfyUI, and the worker control ports — is **never** given a public hostname. It
stays on the LAN / docker network only.

## 1. Tunnel (expose only the PWA/API)

Use [`cloudflared-config.example.yml`](cloudflared-config.example.yml):

```bash
cloudflared tunnel login
cloudflared tunnel create invisable-media
cloudflared tunnel route dns invisable-media media.invisable.co.uk
# copy the example config to /etc/cloudflared/config.yml, fill in the UUID, then:
cloudflared service install
```

The ingress has exactly one hostname (`media.invisable.co.uk → localhost:8080`) and a
`404` catch-all. No other service is tunnelled.

## 2. Access (allow only approved users)

Create a **self-hosted** Access application for `media.invisable.co.uk`
([`access-application.example.json`](access-application.example.json)) with two
policies:

1. **Allow Stephen** — `decision: allow`, include `SteveTG10@outlook.com`, require a
   login method. Optionally widen to the `invisable.co.uk` email domain, or add
   Google / Microsoft / one-time-PIN login methods.
2. **Block everyone else** — `decision: deny`, include `everyone`.

The public now gets the Cloudflare Access login screen and cannot reach the app
without an approved identity.

## 3. How the desktop app authenticates

Cloudflare Access protects the **browser/PWA** session. The desktop app talks to the
**API** with a separate server-issued bearer token (set `INVISABLE_DESKTOP_TOKEN` on
the server; paste the same token into the app's Settings → Authentication, where it
is stored in the OS keychain).

If an embedded webview can't complete the Access login (some IdPs block framed
logins), the app offers an **"open in external browser"** fallback, and at home the
5090 simply uses the **LAN URL** (`http://SERVER-LAN-IP:8080`), bypassing the tunnel
entirely. See the main [desktop README](../README.md#cloudflare-access--login).

> Service-token alternative: to let the desktop app call the API *through* Cloudflare
> (not just the LAN), create an Access **service token** and add a policy that
> includes that service token for the `/api` paths, then send its
> `CF-Access-Client-Id` / `CF-Access-Client-Secret` headers. The bearer token above
> is the simpler default for LAN + tunnel-with-browser-login.
