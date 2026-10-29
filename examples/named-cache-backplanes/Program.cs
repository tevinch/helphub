using System.Collections.Concurrent;
using Microsoft.Extensions.DependencyInjection;
using StackExchange.Redis;
using ZiggyCreatures.Caching.Fusion;
using ZiggyCreatures.Caching.Fusion.Backplane;

var endpoint = Environment.GetEnvironmentVariable("REDIS_ENDPOINT") ?? "127.0.0.1:6399";
var shareConnection = args.Contains("--shared-multiplexer");
if (args.Any(a => a != "--shared-multiplexer"))
    throw new ArgumentException("Usage: dotnet run -- [--shared-multiplexer]");
var scope = "named-cache-example:" + Guid.NewGuid().ToString("N") + ":";
using var observer = await ConnectionMultiplexer.ConnectAsync(endpoint);
var db = observer.GetDatabase();
var sentinel = scope + "unrelated";
await db.StringSetAsync(sentinel, "keep-me");

using var connectionA = shareConnection ? await ConnectionMultiplexer.ConnectAsync(endpoint) : null;
using var connectionB = shareConnection ? await ConnectionMultiplexer.ConnectAsync(endpoint) : null;
var factoryCallsA = 0;
var factoryCallsB = 0;
using var replicaA = CacheSetup.Create(endpoint, scope, connectionA is null ? null : () =>
{
    Interlocked.Increment(ref factoryCallsA);
    return Task.FromResult<IConnectionMultiplexer>(connectionA);
});
using var replicaB = CacheSetup.Create(endpoint, scope, connectionB is null ? null : () =>
{
    Interlocked.Increment(ref factoryCallsB);
    return Task.FromResult<IConnectionMultiplexer>(connectionB);
});
var pa = replicaA.GetRequiredService<IFusionCacheProvider>();
var pb = replicaB.GetRequiredService<IFusionCacheProvider>();
var ad = pa.GetDefaultCache();
var an = pa.GetCache("MyNamedCache");
var bd = pb.GetDefaultCache();
var bn = pb.GetCache("MyNamedCache");
var notices = new ConcurrentQueue<(string Cache, string? Key, BackplaneMessageAction Action)>();
foreach (var cache in new[] { ad, an, bd, bn })
    cache.Events.Backplane.MessageReceived += (_, e) =>
        notices.Enqueue((cache.InstanceId, e.Message.CacheKey, e.Message.Action));

try
{
    await ad.SetAsync("item", "default-0");
    await an.SetAsync("item", "named-0");
    Equal("default-0", await bd.GetOrDefaultAsync<string>("item"), "initial default");
    Equal("named-0", await bn.GetOrDefaultAsync<string>("item"), "initial named");
    Console.WriteLine("Initial reads loaded both peer memory caches.");

    await SetAndObserve(ad, bd, "default-1");
    Equal("named-0", await bn.GetOrDefaultAsync<string>("item"), "default update leaves named unchanged");
    await SetAndObserve(an, bn, "named-1");
    Equal("default-1", await bd.GetOrDefaultAsync<string>("item"), "named update leaves default unchanged");
    await SetAndObserve(bd, ad, "default-2");
    await SetAndObserve(bn, an, "named-2");

    await RemoveAndObserve(ad, bd);
    Equal("named-2", await bn.GetOrDefaultAsync<string>("item"), "default removal leaves named unchanged");
    await SetAndObserve(ad, bd, "default-3");
    await RemoveAndObserve(bn, an);
    Equal("default-3", await ad.GetOrDefaultAsync<string>("item"), "named removal leaves default unchanged");
    await SetAndObserve(an, bn, "named-3");

    var channels = (RedisResult[])(await observer.GetServer(observer.GetEndPoints()[0]).ExecuteAsync("PUBSUB", "CHANNELS", scope + "*"))!;
    Equal(2, channels.Length, "separate default/named subscription channels");
    Equal(true, await db.KeyExistsAsync("v2:" + scope + FusionCacheOptions.DefaultCacheName + ":item"), "default L2 key exists");
    Equal(true, await db.KeyExistsAsync("v2:" + scope + "MyNamedCache:item"), "named L2 key exists");
    Equal("keep-me", (string?)await db.StringGetAsync(sentinel), "unrelated Redis content");
    if (shareConnection)
    {
        Equal(2, factoryCallsA, "replica A's shared factory really ran for both adapters");
        Equal(2, factoryCallsB, "replica B's shared factory really ran for both adapters");
        Console.WriteLine("Shared multiplexer: coherence verified while both caches stay alive; coordinated lifetime required.");
    }
    else
    {
        ad.Dispose();
        bd.Dispose();
        var until = DateTime.UtcNow.AddSeconds(5);
        while (await ChannelCount() != 1 && DateTime.UtcNow < until)
            await Task.Delay(20);
        Equal(1, await ChannelCount(), "default channel actually unsubscribed on both replicas");
        await SetAndObserve(an, bn, "named-after-default-dispose");
        await SetAndObserve(bn, an, "named-after-default-dispose-2");
        Equal("keep-me", (string?)await db.StringGetAsync(sentinel), "unrelated content after disposal");
        Console.WriteLine("Independent connections: named caches still synchronize after default caches are disposed.");
    }
    Console.WriteLine("PASS: two replicas, two caches, both directions, Set/Remove/reuse, separate channels and keys.");
}

finally
{
    // Only this run's keys are touched. Never flush a Redis database.
    await db.KeyDeleteAsync(new RedisKey[] { sentinel, "v2:" + scope + FusionCacheOptions.DefaultCacheName + ":item", "v2:" + scope + "MyNamedCache:item" });
}

async Task<int> ChannelCount()
{
    var result = (RedisResult[])(await observer.GetServer(observer.GetEndPoints()[0])
        .ExecuteAsync("PUBSUB", "CHANNELS", scope + "*"))!;
    return result.Length;
}

async Task SetAndObserve(IFusionCache writer, IFusionCache peer, string value)
{
    var start = notices.Count;
    await writer.SetAsync("item", value);
    await WaitFor(peer, start, BackplaneMessageAction.EntrySet, value);
}

async Task RemoveAndObserve(IFusionCache writer, IFusionCache peer)
{
    var start = notices.Count;
    await writer.RemoveAsync("item");
    await WaitFor(peer, start, BackplaneMessageAction.EntryRemove, null);
}

async Task WaitFor(IFusionCache peer, int start, BackplaneMessageAction action, string? expected)
{
    var until = DateTime.UtcNow.AddSeconds(5);
    string? actual = null;
    var key = scope + peer.CacheName + ":item";
    do
    {
        actual = await peer.GetOrDefaultAsync<string>("item");
        var received = notices.ToArray().Skip(start).Any(n => n.Cache == peer.InstanceId && n.Key == key && n.Action == action);
        if (actual == expected && received)
        {
            Console.WriteLine($"{peer.CacheName}: {action} -> {actual ?? "<missing>"}");
            return;
        }
        await Task.Delay(20);
    } while (DateTime.UtcNow < until);
    throw new InvalidOperationException($"Peer {peer.CacheName} did not complete {action}: expected {expected ?? "<missing>"}, actual {actual ?? "<missing>"}; matching receive required.");
}

static void Equal<T>(T expected, T actual, string check)
{
    if (!EqualityComparer<T>.Default.Equals(expected, actual))
        throw new InvalidOperationException($"{check}: expected {expected}, actual {actual}");
}
