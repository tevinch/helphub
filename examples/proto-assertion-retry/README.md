# Reuse a protobuf assertion inside `EventuallyWithT`

A custom assertion does not need all of `testing.TB`. Give it the methods it actually calls so the same helper accepts both `*testing.T` and the callback's `*assert.CollectT`:

```go
type HelperT interface {
    assert.TestingT // Errorf(format string, args ...any)
    Helper()
}

func AssertProtoEqual(t HelperT, want, got any, msgAndArgs ...any) {
    t.Helper()
    if diff := cmp.Diff(want, got, protocmp.Transform()); diff != "" {
        assert.Fail(t, fmt.Sprintf("not equal (-want +got):\n%s", diff), msgAndArgs...)
    }
}
```

The complete imports and helper are in [protoequal.go](protoequal.go). Its protobuf comparison and failure message follow [the original helper in this question](https://github.com/stretchr/testify/issues/1862#issuecomment-4184457854).

This extends [the maintainer's `assert.TestingT` suggestion](https://github.com/stretchr/testify/issues/1862#issuecomment-4383242493) with `Helper()`, which the posted helper also calls. `assert.TestingT` alone does not declare that method. Testify **1.12.1** already supplies both methods on `*CollectT`; no copied collector, polling loop or full `testing.TB` adapter is required.

## Use it in the callback

```go
assert.EventuallyWithT(t, func(c *assert.CollectT) {
    got := readCurrentMessage()
    AssertProtoEqual(c, want, got, "readiness")
}, 2*time.Second, 10*time.Millisecond)
```

Here `readCurrentMessage()` represents your existing read operation returning a protobuf message. The complete runnable test in [protoequal_test.go](protoequal_test.go) uses real generated protobuf messages, returning `pending` for two attempts and `ready` for the third.

Pass **`c`** to the helper inside the callback. Passing the outer `t` would mark the whole test failed on an intermediate mismatch. Each callback's collector records that attempt's errors; a later clean attempt can succeed. On timeout, Testify copies the last completed attempt's errors to the outer test and reports that the condition was never satisfied.

`CollectT.Helper()` is a no-op marker in this release. This interface shares assertion code; it does not make `CollectT` a complete `testing.TB`. Helpers that use cleanup, temporary directories, skipping, parallel subtests or other methods need separate treatment. Perform fixture setup outside the polling callback, and do not call the real test's fatal methods from that callback's goroutine.

## Run the complete checks

Use Go **1.23 or newer**. The module pins Testify **1.12.1**, go-cmp **0.7.0** and protobuf **1.36.12**.

```sh
go test -count=1 -v ./...
go test -race -count=1 ./...
```

The checks compile both accepted targets, compare equal nested protobuf messages, recover from two failed comparisons, and run an always-unequal comparison to a real timeout in a separate test process. The parent requires exit status 1, a protobuf diff containing both expected/actual values, timeout diagnostics and an independently counted callback execution. That child test is intentionally skipped in the ordinary parent run; its separate failing run is required and checked by the parent.

Two compiler controls also check the exact adoption gap: the original `testing.TB` signature rejects `*CollectT`, and changing only to `assert.TestingT` rejects the helper's `t.Helper()` call. These controls must fail for the expected type errors, while the two-method version passes.

These are scripted Go tests, including the real protobuf comparison and Testify retry implementation. They do not establish behavior in the requester's end-to-end environment or confirm adoption.

References: [Testify 1.12.1 collector and polling implementation](https://github.com/stretchr/testify/blob/v1.12.1/assert/assertions.go), [protobuf comparison transforms](https://pkg.go.dev/google.golang.org/protobuf/testing/protocmp), [Go testing goroutine rules](https://pkg.go.dev/testing#T).

## Optional coffee

This example is free. If it saved you time and you would like to buy me a coffee, a contribution is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
