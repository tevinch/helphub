using System.IO.Abstractions;
using Castle.DynamicProxy;

namespace FileReadPolicyExample;

/// <summary>A test-only policy for IFile.ReadAllBytesAsync; other operations forward unchanged.</summary>
public static class ReadPolicy
{
    public static IFileSystem Create(IFileSystem backing, string blockedPath, Action<string>? observe = null)
    {
        ArgumentNullException.ThrowIfNull(backing);
        ArgumentException.ThrowIfNullOrEmpty(blockedPath);
        var fullPath = backing.Path.GetFullPath(blockedPath);
        var comparison = backing.Path.DirectorySeparatorChar == '\\'
            ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        var generator = new ProxyGenerator();
        var file = generator.CreateInterfaceProxyWithTarget<IFile>(backing.File,
            new ForwardingInterceptor(invocation =>
            {
                if (invocation.Method.Name != nameof(IFile.ReadAllBytesAsync)) return false;
                var path = invocation.Arguments[0] as string;
                observe?.Invoke($"File.ReadAllBytesAsync:{path}");
                var token = invocation.Arguments.Length > 1 && invocation.Arguments[1] is CancellationToken provided
                    ? provided : CancellationToken.None;
                // Native cancellation and path validation stay with the underlying mock.
                if (token.IsCancellationRequested || path is null) return false;
                string candidate;
                try { candidate = backing.Path.GetFullPath(path); }
                catch (Exception exception) when (exception is ArgumentException or NotSupportedException or PathTooLongException)
                {
                    // Let the actual read validate malformed paths and keep its own failure details.
                    return false;
                }
                if (!string.Equals(candidate, fullPath, comparison)) return false;
                throw new UnauthorizedAccessException($"Access to the path '{fullPath}' is denied.");
            }));
        var directory = generator.CreateInterfaceProxyWithTarget<IDirectory>(backing.Directory,
            new ForwardingInterceptor(invocation =>
            {
                if (invocation.Method.Name == nameof(IDirectory.GetFiles))
                    observe?.Invoke($"Directory.GetFiles:{invocation.Arguments[0]}");
                return false;
            }));
        return generator.CreateInterfaceProxyWithTarget<IFileSystem>(backing,
            new ForwardingInterceptor(invocation =>
            {
                if (invocation.Method.Name == "get_File") { invocation.ReturnValue = file; return true; }
                if (invocation.Method.Name == "get_Directory") { invocation.ReturnValue = directory; return true; }
                return false;
            }));
    }

    private sealed class ForwardingInterceptor(Func<IInvocation, bool> handled) : IInterceptor
    {
        public void Intercept(IInvocation invocation)
        {
            if (!handled(invocation)) invocation.Proceed();
        }
    }
}
