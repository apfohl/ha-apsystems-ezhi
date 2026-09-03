# Energy Card Development Shell

Run the standalone shell from the repository root:

```sh
make dev
```

Open `http://localhost:8080`. The shell serves the card directly from
`custom_components/apsystems_ezhi/frontend/apsystems-ezhi-energy-card.js`, so
refreshing the browser picks up JavaScript edits without copying the file into
another project.

`make setup` validates the configured Go 1.27 toolchain and `make test-dev`
runs the shell's handler tests.

The default toolchain is `/opt/homebrew/Cellar/go/1.27.1/bin/go`. Override it
when needed, for example: `make GO=/usr/local/bin/go dev`.

The browser shim maps the card's two Home Assistant registry WebSocket calls to
these mock HTTP endpoints:

- `GET /api/device-registry`
- `GET /api/entity-registry`
- `GET /api/states?scenario=day|evening|idle|alarm|offline`

The scenario control fetches a new state payload and assigns it to the card's
mocked `hass` object. The shell also reports `hass-more-info` events when a
diagram node is clicked.
