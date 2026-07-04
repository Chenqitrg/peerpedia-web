# PeerPedia Web

Browser frontend for [PeerPedia Core](https://github.com/Chenqitrg/peerpedia-core). Pure Vue 3 SPA — no backend logic.

**Peer review as infrastructure. An open protocol for how knowledge is filtered, not a platform for how it's sold.**

同行评审即基础设施。

## What this is

A Vue 3 single-page application that connects to a running `peerpedia server` instance. Contains zero backend logic — all data goes through the PeerPedia Core HTTP API.

## What this is NOT

- NOT a desktop app (that will be a separate repo: `peerpedia-desktop`)
- NOT a backend (see [peerpedia-core](https://github.com/Chenqitrg/peerpedia-core))
- NOT a standalone product — you need a peerpedia-core server running


## Architecture

```
Browser (Vue 3 SPA)
    │
    ├── Axios → http://localhost:8080/api/v1 → peerpedia-core server
    │
    └── localStorage (offline cache and session persistence)
```

## Related

- [peerpedia-core](https://github.com/Chenqitrg/peerpedia-core) — the backend engine (Python CLI + HTTP server + Git storage)

## License

CC BY-NC-SA 4.0 — see [LICENSE](LICENSE).
