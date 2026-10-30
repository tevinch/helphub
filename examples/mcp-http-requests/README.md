# Test a Quarkus MCP server with curl

List tools and call one directly over HTTP using curl and JSON files. This example includes a small Quarkus server with a `greet` tool and requests for both supported communication modes.

Protocol version **2026-07-28 is stateless**: each request includes its own metadata and routing headers. Protocol version **2025-11-25 is stateful**: initialize a session first and send its ID with subsequent requests. The two modes use the same `/mcp` endpoint.

## Start the example server

Use JDK 17 or later, Maven 3.9 or later, and curl with `--fail-with-body` support (7.76 or later). The POM pins Quarkus MCP Server 2.0.4 and the Quarkus 3.33.3.1 version declared by that release.

From this directory:

```sh
mvn package
java -jar target/quarkus-app/quarkus-run.jar
```

Keep that terminal running. In a second terminal, return to this directory to send the requests below. The example listens at `http://localhost:18080/mcp`.

For an existing server, use its URL, tool name and arguments. `tools/list` returns the names and input schemas needed to construct a call. In stateless mode, `Mcp-Method` must match the JSON `method`, and `Mcp-Name` must match `params.name` for a tool call.

## Stateless requests: 2026-07-28

List tools:

```sh
curl --silent --show-error --fail-with-body http://localhost:18080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: tools/list' \
  --data-binary @requests/stateless-list.json
```

The result should contain `greet`, with a string `name` argument. Call it twice with different arguments:

```sh
curl --silent --show-error --fail-with-body http://localhost:18080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: greet' \
  --data-binary @requests/stateless-call-ada.json

curl --silent --show-error --fail-with-body http://localhost:18080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: greet' \
  --data-binary @requests/stateless-call-lin.json
```

Expect response IDs `2` and `3`, containing `Hello, Ada!` and `Hello, Lin!`. The JSON files include the protocol version, client information and capabilities under `params._meta`. Each ordinary request completes independently. This mode has no session ID or initialization handshake, and no session to terminate with `DELETE`.

## Stateful requests: 2025-11-25

Initialize and save the response headers:

```sh
mkdir -p request-output

curl --silent --show-error --fail-with-body http://localhost:18080/mcp \
  -D request-output/initialize-headers.txt \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-11-25' \
  --data-binary @requests/initialize.json

mcp_session_id="$(awk 'tolower($1) == "mcp-session-id:" {gsub("\r", "", $2); print $2}' request-output/initialize-headers.txt)"
test -n "$mcp_session_id"
```

The initialization result should select `2025-11-25` and include server information and tool capabilities. Keep the same shell for the remaining commands so `mcp_session_id` stays available.

Send the initialization notification, then list tools:

```sh
curl --silent --show-error --fail-with-body http://localhost:18080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-11-25' \
  -H "Mcp-Session-Id: $mcp_session_id" \
  --data-binary @requests/initialized.json

curl --silent --show-error --fail-with-body http://localhost:18080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-11-25' \
  -H "Mcp-Session-Id: $mcp_session_id" \
  --data-binary @requests/stateful-list.json
```

The notification is accepted with HTTP `202` and an empty body. The list response has ID `11`. Use the session for two calls:

```sh
curl --silent --show-error --fail-with-body http://localhost:18080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-11-25' \
  -H "Mcp-Session-Id: $mcp_session_id" \
  --data-binary @requests/stateful-call-ada.json

curl --silent --show-error --fail-with-body http://localhost:18080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-11-25' \
  -H "Mcp-Session-Id: $mcp_session_id" \
  --data-binary @requests/stateful-call-lin.json
```

Expect IDs `12` and `13` with the same two greeting results. Finish the session:

```sh
curl --silent --show-error --fail-with-body -X DELETE http://localhost:18080/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-11-25' \
  -H "Mcp-Session-Id: $mcp_session_id"
```

An old session ID is no longer usable after termination. Start a new initialization sequence for another session. Stop the local example server with Ctrl+C when finished.

## Requests and responses

The JSON-RPC `id` connects each response to its request. Inspect both the HTTP status and JSON-RPC body: `--fail-with-body` detects HTTP failures, while a JSON-RPC error may also arrive in an HTTP-success response.

The example returns ordinary JSON responses. Tools that use progress, sampling or other streaming features may return SSE events instead; these simple greeting requests do not exercise those features. Traffic logging can show messages the server received, but it does not construct a missing client request.

## Validation

Checked with Quarkus MCP Server 2.0.4, Quarkus 3.33.3.1, Temurin JDK 21.0.12.1, Maven 3.10.0 and curl 8.7.1 on macOS. Tool listing and two calls returned the matching IDs and greetings in both modes. The stateful notification returned HTTP `202`, termination returned `200`, and a request using the terminated session returned `404`. The included server binds to localhost and enables the native CORS filter.

The original `2026-07-28` `tools/list` request in [question 1100](https://github.com/quarkiverse/quarkus-mcp-server/issues/1100) completes normally against this server. The earlier hang was not reproduced or fixed. This example supplies the complete native request sequence for listing and calling tools.

See the official [HTTP quickstart](https://docs.quarkiverse.io/quarkus-mcp-server/dev/getting-started-http.html), [transport modes](https://docs.quarkiverse.io/quarkus-mcp-server/dev/concepts-transports.html), and [development tools](https://docs.quarkiverse.io/quarkus-mcp-server/dev/guides-development-tools.html).

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
