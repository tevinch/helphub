# Share an HTTP client header with Connect

An application can share its ordinary HTTP `User-Agent` default across Connect clients while preserving each call's own value. Use a client interceptor that checks **presence**, rather than whether the value is empty:

```go
func DefaultUserAgent(value string) connect.ClientInterceptor {
    return func(next connect.ClientFunc) connect.ClientFunc {
        return func(ctx context.Context, spec connect.Spec) (connect.ClientStream, error) {
            info, _ := connect.CallInfoForClientContext(ctx)
            header := info.RequestHeader()
            if !header.Has("User-Agent") {
                header.Set("User-Agent", value)
            }
            return next(ctx, spec)
        }
    }
}
```

`connect.Client` supplies the per-call `CallInfo` before invoking its interceptors. The complete helper, including imports, is in `default.go`.

Reuse that interceptor with your configured HTTP client and service URL:

```go
shared := DefaultUserAgent("application-client/1.0")
first := connect.NewClient(connecthttp.NewTransport(httpClient, baseURL), shared)
second := connect.NewClient(connecthttp.NewTransport(httpClient, baseURL), shared)
```

Pass each `*connect.Client` to your usual generated service-client constructor. The tests use public native low-level RPC calls and already-generated protobuf wrapper messages so they run without installing a code generator.

For one call, derive its context before invoking your service method:

```go
ctx, info := connect.NewClientContext(ctx)
info.RequestHeader().Set("User-Agent", "request-client/2.0")
// Invoke the service method with ctx.
```

To suppress the header instead, use `Set("User-Agent", "")` or `SetValues("User-Agent", nil)`. Both are present values, so the interceptor leaves them alone; the native HTTP transport sends no ordinary User-Agent header for those cases. A `Get(...) == ""` check would incorrectly replace them with the application default.

The interceptor keeps no mutable shared state. Each concurrent call needs its **own** context/CallInfo; do not mutate or share one call's headers while it is running. The native gRPC-Web `X-User-Agent` header is handled separately by the transport. This helper does not set or replace it.

## Run the complete checks

Requires Go 1.26 or later. This example pins **Connect Go v2.0.2** and **protobuf v1.36.11**. From this directory:

```sh
go mod download
go mod verify
go test -count=1 -v ./...
go test -race -count=1 ./...
```

The tests run a task-owned loopback HTTP server and complete 50 real unary RPCs across Connect and gRPC-Web: two independent clients, two service paths, defaults, per-call overrides, empty/nil suppression, repeated calls and concurrent calls. They check each response body, the actual HTTP headers and path observed before protocol handling, and the native server's request metadata. Exactly 25 completed request receipts are required for each protocol.

A separate native call without the interceptor establishes the gRPC-Web `X-User-Agent` baseline; all helper cases must leave it unchanged. Omitted-interceptor, empty-value and unconditional-overwrite controls fail against actual received headers. These are scripted native HTTP tests, not validation in the original application or human manual testing. Streaming, gRPC over HTTP/2 and browser clients are outside these checks.

The macOS/arm64 results cover ordinary HTTP tests with Go 1.27.2. Race verification uses a separate Go 1.27.2 Linux/amd64 run. See the native [client/interceptor contract](https://github.com/connectrpc/connect-go/blob/v2.0.2/connect.go), [presence-aware HTTP defaults](https://github.com/connectrpc/connect-go/blob/v2.0.2/connecthttp/header.go) and [gRPC-Web header behavior](https://github.com/connectrpc/connect-go/blob/v2.0.2/connecthttp/protocol_grpc.go). This uses existing APIs and changes no Connect source. Connect and protobuf retain their upstream licenses; the license here covers this example.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
