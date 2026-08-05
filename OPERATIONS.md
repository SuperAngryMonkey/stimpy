# OPERATIONS — Stimpy

Deploy, run, verify, troubleshoot.

**Target:** LXC 206 (`stimpy`) on **proxlab** (`10.0.1.9` / TS `100.105.71.57`),
Debian 12.

Reach the LXC from a Proxmox shell with `pct enter 206` on proxlab, or over
SSH/Tailscale once joined.

## Deploy

```
# On stimpy, as root
apt update && apt install -y python3-venv git
useradd -r -s /usr/sbin/nologin stimpy || true

git clone <repo-url> /opt/stimpy
cd /opt/stimpy
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
chown -R stimpy:stimpy /opt/stimpy
```

## Run under systemd

```
cp /opt/stimpy/stimpy.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now stimpy
systemctl status stimpy
```

Logs:

```
journalctl -u stimpy -f
```

## Verify (do this in order, first time)

1. Service is up:
   ```
   curl -s http://localhost:5000/health
   ```
   Expect `dominos_reachable: true`.

2. Confirm codes still match the live menu (sanity, not required every time):
   ```
   curl -s "http://localhost:5000/menu?q=pan"
   curl -s "http://localhost:5000/menu?q=ham"
   curl -s "http://localhost:5000/menu?q=pineapple"
   ```
   Expect `P12IPAZA`, `H`, `N` present.

3. Dry run — validates + prices, places nothing:
   ```
   curl -s -X POST http://localhost:5000/dryrun
   ```
   Expect `{"ok":true,"amount":"<price>",...}`. THIS is the real proof the
   stack works end to end.

4. Only when you actually want pizza — open the page and press Feed Me, or:
   ```
   curl -s -X POST http://localhost:5000/order
   ```

## Troubleshoot

| Symptom | Likely cause | Fix |
|---|---|---|
| `/health` shows `dominos_reachable: false` | Box can't reach Domino's | Check egress / DNS. It was 200 at build; something changed. |
| `/dryrun` returns 502 / 403 | Domino's blocking the request | Confirm residential IP. UA injection should handle it; if not, the UA string in `config.py` may need refreshing. |
| Validation fails (`ok:false` at validate) | Store closed, item unavailable, or code drift | Check store hours; re-verify codes via `/menu`. |
| Order rejected but dry run passed | New customer/address scrutiny | Place one manual order via dominos.com to seed the record (see HANDOFF). |
| Service won't start | venv path / perms | `journalctl -u stimpy -e`; check `chown` and `.venv` exist. |

## Changing the order

Edit `/opt/stimpy/config.py`, then:

```
systemctl restart stimpy
curl -s -X POST http://localhost:5000/dryrun   # re-verify
```

## Updating codes after a Domino's menu change

```
curl -s "http://localhost:5000/menu?q=<term>"
```
Read the new code, update `config.py`, restart, dry-run.

## If everything 403s

Dominos rejects business/datacenter/cloud IPs. Stimpy must egress from a
residential connection (proxlab at home). Verify with:
`curl -s https://ifconfig.me` from the LXC — if that IP is not the home
WAN address, fix routing before touching the app.
