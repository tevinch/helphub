# Give each named cache its own Redis backplane

In FusionCache 2.9.0, a `RedisBackplane` stores one current channel and one set of incoming-message handlers. Passing the same object to two caches overwrites those fields; existing Redis callbacks also use that current handler. It does not maintain independent per-cache subscription state.

Use a separate backplane object for each cache. The native builder creates one for each registration:

```csharp
services.AddFusionCache()
    .WithStackExchangeRedisBackplane(o => o.Configuration = redisConnection);

services.AddFusionCache("MyNamedCache")
    .WithStackExchangeRedisBackplane(o => o.Configuration = redisConnection);
```

Keep your existing `WithDistributedCache(l2)` calls and each cache's other settings. If they share the same L2 key space, keep distinct cache-key prefixes as described in the official [named-cache guide](https://github.com/ZiggyCreatures/FusionCache/blob/v2.9.0/docs/NamedCaches.md). The same cache name and prefix must match across replicas.

## Sharing a multiplexer

A separate **backplane object** does not necessarily require a separate **multiplexer**. To retain one multiplexer per application instance while both caches are alive, give each builder its own adapter through the native extension:

```csharp
void ConfigureBackplane(RedisBackplaneOptions options)
{
    options.ConnectionMultiplexerFactory =
        () => Task.FromResult<IConnectionMultiplexer>(muxer);
}

services.AddFusionCache()
    .WithStackExchangeRedisBackplane(ConfigureBackplane);
services.AddFusionCache("MyNamedCache")
    .WithStackExchangeRedisBackplane(ConfigureBackplane);
```

The namespaces are `Microsoft.Extensions.DependencyInjection`, `StackExchange.Redis` and `ZiggyCreatures.Caching.Fusion.Backplane.StackExchangeRedis`.

There is a lifetime constraint in **2.9.0**: `RedisBackplane.Disconnect()` disposes its multiplexer, including one supplied by `ConnectionMultiplexerFactory`. Disposing or removing one cache's backplane can therefore close a shared multiplexer still needed by another cache or service. Use a shared factory only with a coordinated lifetime for all its consumers. Do not assume that the factory transfers no ownership. For caches that can be disposed independently, the first configuration above lets each backplane own its own connection.

The executable below checks both configurations. It uses separate L2 `RedisCache` instances owned by DI, matching cache names across two independent service providers, and distinct key prefixes. It changes no upstream source.

## Run the complete example

Requires .NET 10 and an isolated Redis instance. For example, start an existing `redis-server` in a separate terminal:

```sh
redis-server --bind 127.0.0.1 --port 6399 --save '' --appendonly no
```

Then, from this directory:

```sh
dotnet restore --locked-mode
dotnet build --no-restore -c Release
dotnet run --no-build -c Release
dotnet run --no-build -c Release -- --shared-multiplexer
```

`REDIS_ENDPOINT` can select a different test instance. The program creates a unique prefix and deletes only its own three keys; it never flushes a database.

The default run uses one backplane connection per cache. Both replicas first load default and named values into memory. It then checks updates in both directions, removals, continued use after removal, unchanged values in the other cache, actual backplane notifications, separate Redis channels and L2 keys, and an unrelated sentinel. Finally it disposes both default caches, independently observes their channel disappear, and confirms the named caches still synchronize in both directions.

The `--shared-multiplexer` run creates one multiplexer per replica, uses it in both distinct adapters, and checks that both connection factories actually run. It completes the same coherence checks while both caches stay alive. It does not perform independent cache disposal: that is the lifetime constraint described above.

Successful runs end with `PASS: two replicas, two caches, both directions, Set/Remove/reuse, separate channels and keys.` Exceptions make the process fail. A timeout requires both the expected peer value and the matching received notification; a dormant callback cannot silently pass.

## Verified scope

Native scripted integration was run on macOS arm64 with .NET SDK 10.0.402, runtime 10.0.13, Redis 8.10.3 and the locked package versions in this directory. The original shared-adapter composition left the peer's default memory value stale after an update; the separate-adapter composition completed the operation sequence above. These are local software checks, not a test of the requester's deployment or confirmation of adoption.

This example addresses adapter ownership and cache separation. It does not test Redis failover, reconnect recovery, rolling upgrades or production load. It is a configuration example, not a replacement backplane or a library patch.

See the official [backplane guide](https://github.com/ZiggyCreatures/FusionCache/blob/v2.9.0/docs/Backplane.md), [native builder extension](https://github.com/ZiggyCreatures/FusionCache/blob/v2.9.0/src/ZiggyCreatures.FusionCache.Backplane.StackExchangeRedis/StackExchangeRedisBackplaneExtensions.cs) and [RedisBackplane lifetime code](https://github.com/ZiggyCreatures/FusionCache/blob/v2.9.0/src/ZiggyCreatures.FusionCache.Backplane.StackExchangeRedis/RedisBackplane.cs).

## Optional coffee

This example is free. If it saved you some time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
