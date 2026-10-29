using Microsoft.Extensions.Caching.StackExchangeRedis;
using Microsoft.Extensions.DependencyInjection;
using StackExchange.Redis;
using ZiggyCreatures.Caching.Fusion;
using ZiggyCreatures.Caching.Fusion.Backplane.StackExchangeRedis;
using ZiggyCreatures.Caching.Fusion.Serialization.SystemTextJson;

internal static class CacheSetup
{
    public static ServiceProvider Create(string endpoint, string scope, Func<Task<IConnectionMultiplexer>>? sharedConnection = null)
    {
        var services = new ServiceCollection();
        foreach (var name in new[] { FusionCacheOptions.DefaultCacheName, "MyNamedCache" })
        {
            // DI owns each L2 RedisCache; FusionCache only borrows it.
            services.AddKeyedSingleton<RedisCache>(name, (_, _) =>
                new RedisCache(new RedisCacheOptions { Configuration = endpoint }));
            services.AddFusionCache(name)
                .WithOptions(o =>
                {
                    o.WaitForInitialBackplaneSubscribe = true;
                    o.EnableSyncEventHandlersExecution = true;
                    o.BackplaneChannelPrefix = scope + name;
                })
                .WithCacheKeyPrefix(scope + name + ":")
                .WithDefaultEntryOptions(o =>
                {
                    o.Duration = TimeSpan.FromMinutes(5);
                    o.AllowBackgroundBackplaneOperations = false;
                    o.AllowBackgroundDistributedCacheOperations = false;
                    o.ReThrowBackplaneExceptions = true;
                    o.ReThrowDistributedCacheExceptions = true;
                })
                .WithSerializer(new FusionCacheSystemTextJsonSerializer())
                .WithDistributedCache(sp => sp.GetRequiredKeyedService<RedisCache>(name))
                .WithStackExchangeRedisBackplane(o =>
                {
                    o.Configuration = endpoint;
                    o.ConnectionMultiplexerFactory = sharedConnection;
                });
        }
        return services.BuildServiceProvider();
    }
}
