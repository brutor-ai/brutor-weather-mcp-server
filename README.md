# brutor-weather-mcp-server

A minimal **remote MCP server** that exposes a single weather tool over
streamable HTTP. It exists as a demo / smoke-test server for the
**Brutor AI Governance Platform** — something small and dependency-light
you can register in the Admin Console, route through the gateway, and
exercise guardrails / argument policies / audit against.

It is the **bare** variant: no authentication, no FastAPI wrapper —
just `FastMCP` running its built-in streamable-HTTP transport. 

---

## The tool

| Tool | Signature | Description |
|------|-----------|-------------|
| `get_current_weather` | `get_current_weather(city: str) -> str` | Geocodes the city, fetches current conditions, returns a formatted summary. |

It calls two **free, no-API-key** public services:

- [Nominatim](https://nominatim.openstreetmap.org/) (OpenStreetMap) — city → latitude/longitude.
- [Open-Meteo](https://open-meteo.com/) — coordinates → current temperature, wind, and weather code.

No credentials, no `.env` — clone and run.

---

## Requirements

- Python **3.13+** (see `.python-version`)
- Either [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`

---

## Run

### With uv (recommended)

```bash
uv run weather-mcp-server-remote.py
```

`uv` reads `pyproject.toml`, creates a virtualenv, installs `mcp` +
`httpx`, and starts the server in one step.

### With pip

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
python weather-mcp-server-remote.py
```

Either way you should see:

```
🚀 Starting MCP Weather Server on streamable HTTP...
🌐 MCP server will be available at: http://0.0.0.0:3012
```

---

## Configuration

The server takes two environment variables — both optional:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_HOST` | `0.0.0.0` | Bind address |
| `MCP_PORT` | `3012`    | Bind port |

```bash
# Run on a different port (e.g. to avoid a clash with another MCP server)
MCP_PORT=3099 uv run weather-mcp-server-remote.py
```

Port `3012` is this server's slot in the demo MCP server block —
`3010` mcp-app-map, `3011` fake-mcp, `3012` weather. Stay outside
that block when overriding.

---

## Endpoint

`FastMCP`'s streamable-HTTP transport serves the MCP protocol at the
**`/mcp`** path:

```
http://<MCP_HOST>:<MCP_PORT>/mcp
```

So with defaults the connectable URL is `http://localhost:3012/mcp`.

### Smoke test with curl

Streamable-HTTP MCP is **stateful** — every call after `initialize`
must carry the `Mcp-Session-Id` the server hands back. A bare
`tools/list` returns `Bad Request: Missing session ID`. Two steps:

```bash
# 1. Initialize — grab the session id from the response headers
$ curl -s -D - -X POST http://localhost:3012/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{ "protocolVersion":"2025-06-18", "clientInfo":{"name":"curl-smoke","version":"1.0"}, "capabilities":{}}}'
HTTP/1.1 200 OK
date: Wed, 20 May 2026 10:24:21 GMT
server: uvicorn
cache-control: no-cache, no-transform
connection: keep-alive
content-type: text/event-stream
mcp-session-id: 0b0cfcef9f2d4aa3920482a49441da22
x-accel-buffering: no
Transfer-Encoding: chunked

event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":false}},"serverInfo":{"name":"weather-assistant","version":"1.27.1"}}}

# 2. List tools, passing the session id back
curl -s -X POST http://localhost:3012/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -H "Mcp-Session-Id: 0b0cfcef9f2d4aa3920482a49441da22" -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
event: message
data: {"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"get_current_weather","description":"\nGets the current weather in a given location by using external service. \nFinds longitude and latitude for given city and fetches current temperature using Open-Meteo API.\n\nArgs:\n    city: Location of interest (city name)\n    \nReturns:\n    Weather information including temperature, conditions, and wind speed\n","inputSchema":{"properties":{"city":{"title":"City","type":"string"}},"required":["city"],"title":"get_current_weatherArguments","type":"object"},"outputSchema":{"properties":{"result":{"title":"Result","type":"string"}},"required":["result"],"title":"get_current_weatherOutput","type":"object"}}]}}
```

Step 2 returns an SSE `data:` line whose JSON `result.tools` array
contains `get_current_weather`. 

```

---

## Register it in the Brutor Admin Console

This is the point of the repo — drive it through the gateway:

1. Start the server (above). For the Brutor trial bundle running in
   Docker, bind it somewhere the gateway container can reach — on the
   same host, `http://host.docker.internal:3012/mcp` usually works;
   on a shared network, use the host's LAN IP, not `localhost`.
2. In the **Admin Console** → **MCP Servers** → **Configuration**,
   create a new MCP server:
   - **Base URL**: `http://<host>:3012/mcp`
   - **Auth type**: `None` (this is the bare variant)
3. Assign the server to a Resource Group so portal users / agents in
   that group can call it.
4. From the **User Portal**, ask a chat *"what's the weather in
   Berlin?"* — the model will discover `get_current_weather` as an MCP
   tool and call it through the gateway. Guardrails, argument
   policies, and the audit trail all apply on the way through.

---

### Call through the Brutor Gateway proxy with curl

Now make the call through the Brutor Gateway proxy. Get the MCP Server `endpoint` via 
the "Resources | MCP Servers | Configuration | <server> -> endpoint" link in the Admin Console.
Then generate an `API-KEY` for the Resource Group that should have access to the
MCP server, and put it in the shell's environment (never in a file you commit):

```bash
$ export BRUTOR_API_KEY=<the API key>
$ curl -s -X POST http://localhost:8100/v1/proxy/mcp/mcp-01KS2MQQS24X355MN7NK006Y28 -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -H "Mcp-Session-Id: 0b0cfcef9f2d4aa3920482a49441da22" -H "Authorization: Bearer $BRUTOR_API_KEY" -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
event: message
data: {"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"get_current_weather","description":"\nGets the current weather in a given location by using external service. \nFinds longitude and latitude for given city and fetches current temperature using Open-Meteo API.\n\nArgs:\n    city: Location of interest (city name)\n    \nReturns:\n    Weather information including temperature, conditions, and wind speed\n","inputSchema":{"properties":{"city":{"title":"City","type":"string"}},"required":["city"],"title":"get_current_weatherArguments","type":"object"},"outputSchema":{"properties":{"result":{"title":"Result","type":"string"}},"required":["result"],"title":"get_current_weatherOutput","type":"object"}}]}}
```

---

## What this is NOT

- **Not authenticated.** Anyone who can reach the port can call the
  tool. That's intentional for a local demo — the gateway is where
  access control lives. Do not expose this server directly to the
  internet.
- **Not production weather data.** It's a thin wrapper over two free
  public APIs with no caching or rate-limit handling. Fine for demos,
  not for a real product surface.
