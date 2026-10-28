using System.Collections.Concurrent;
using System.IO.Abstractions;
using System.Text;
using Testably.Abstractions.Testing;
using FileReadPolicyExample;
using Testably.Abstractions.Testing.FileSystem;

await VerifyNativeStrategyLimitation();

var backing = new MockFileSystem();
var directory = backing.Path.GetFullPath("sample");
backing.Directory.CreateDirectory(directory);
var first = backing.Path.Combine(directory, "myFile1.txt");
var second = backing.Path.Combine(directory, "myFile2.txt");
var expected = Encoding.UTF8.GetBytes("first file ✓");
var blockedContent = Encoding.UTF8.GetBytes("second file stays present");
backing.File.WriteAllBytes(first, expected);
backing.File.WriteAllBytes(second, blockedContent);
var calls = new ConcurrentQueue<string>();
IFileSystem fileSystem = ReadPolicy.Create(backing, second, calls.Enqueue);

// This service knows only the standard IFileSystem interface.
var service = new FileReaderService(fileSystem);
await service.Check(directory, first, second, expected);
Console.WriteLine("PASS: list both, read first, deny second, list both again, read first again.");

await ExpectDenied(() => fileSystem.File.ReadAllBytesAsync(second), second);
await ExpectDenied(() => fileSystem.File.ReadAllBytesAsync(second, CancellationToken.None), second);

using var cancellation = new CancellationTokenSource();
cancellation.Cancel();
foreach (var path in new[] { first, second })
{
    var native = await Failure(() => backing.File.ReadAllBytesAsync(path, cancellation.Token));
    var proxied = await Failure(() => fileSystem.File.ReadAllBytesAsync(path, cancellation.Token));
    Check(native.Exception is OperationCanceledException, "Native mock did not observe cancellation.");
    Check(proxied.Exception.GetType() == native.Exception.GetType(), "Cancellation exception type changed.");
    Check(proxied.Synchronous == native.Synchronous, "Cancellation timing changed.");
    Check(proxied.Exception.Message == native.Exception.Message, "Cancellation message changed.");
    Check(proxied.Exception.HResult == native.Exception.HResult, "Cancellation HResult changed.");
    Check(((OperationCanceledException)proxied.Exception).CancellationToken ==
          ((OperationCanceledException)native.Exception).CancellationToken, "Native cancellation metadata changed.");
}
var concurrent = Enumerable.Range(0, 12).Select(index => Task.Run(async () =>
{
    if (index % 2 == 0)
        Check((await fileSystem.File.ReadAllBytesAsync(first)).SequenceEqual(expected), "Concurrent allowed read changed.");
    else await ExpectDenied(() => fileSystem.File.ReadAllBytesAsync(second), second);
}));
await Task.WhenAll(concurrent);

var relativeSecond = backing.Path.GetRelativePath(backing.Directory.GetCurrentDirectory(), second);
await ExpectDenied(() => fileSystem.File.ReadAllBytesAsync(relativeSecond), second);
var otherDirectory = backing.Path.Combine(directory, "other");
fileSystem.Directory.CreateDirectory(otherDirectory);
var sameName = backing.Path.Combine(otherDirectory, "myFile2.txt");
fileSystem.File.WriteAllText(sameName, "different path");
Check(fileSystem.File.ReadAllText(sameName) == "different path", "Unconfigured synchronous calls did not forward.");
Check(Encoding.UTF8.GetString(await fileSystem.File.ReadAllBytesAsync(sameName)) == "different path", "Filename comparison blocked a different path.");
try
{
    await fileSystem.File.ReadAllBytesAsync(backing.Path.Combine(directory, "absent.txt"));
    throw new Exception("Missing-file read unexpectedly succeeded.");
}
catch (FileNotFoundException) { }
Check(ReferenceEquals(fileSystem.Directory, fileSystem.Directory), "Directory proxy was not reused.");
Check(ReferenceEquals(fileSystem.Path, backing.Path), "Path getter was replaced.");
Check(backing.File.ReadAllBytes(second).SequenceEqual(blockedContent), "Denied read changed original content.");
foreach (var invalid in new string?[] { "bad\0path", null, "", " " })
{
    var native = await Failure(() => backing.File.ReadAllBytesAsync(invalid!));
    var proxied = await Failure(() => fileSystem.File.ReadAllBytesAsync(invalid!));
    Check(proxied.Exception.GetType() == native.Exception.GetType(), "Native path failure type changed.");
    Check(proxied.Synchronous == native.Synchronous, "Native path failure timing changed.");
    Check(proxied.Exception.Message == native.Exception.Message, "Native path failure message changed.");
    Check(proxied.Exception.HResult == native.Exception.HResult, "Native path failure HResult changed.");
}
Check(calls.Any(call => call.StartsWith("Directory.GetFiles:", StringComparison.Ordinal)), "No independent enumeration trace.");
Check(calls.Count(call => call.StartsWith("File.ReadAllBytesAsync:", StringComparison.Ordinal)) >= 20, "Async read interceptor did not run.");
Console.WriteLine("PASS: native error semantics, explicit/default tokens, cancellation, concurrent/repeated reads, canonical paths, forwarding and unchanged content.");
Console.WriteLine("All checks passed.");

static async Task VerifyNativeStrategyLimitation()
{
    var native = new MockFileSystem(options => options.SimulatingOperatingSystem(SimulationMode.Windows));
    const string root = @"C:\sample";
    native.Directory.CreateDirectory(root);
    native.File.WriteAllText(native.Path.Combine(root, "myFile1.txt"), "one");
    native.File.WriteAllText(native.Path.Combine(root, "myFile2.txt"), "two");
    var checkedPaths = new List<string>();
    native.WithAccessControlStrategy(new DefaultAccessControlStrategy((path, _) =>
    {
        checkedPaths.Add(path);
        return !path.EndsWith("myFile2.txt", StringComparison.Ordinal);
    }));
    try { native.Directory.GetFiles(root); throw new Exception("Native path-only ACL unexpectedly allowed enumeration."); }
    catch (UnauthorizedAccessException) { }
    Check(checkedPaths.Contains(root), "Native ACL directory callback was never called.");
    Check(checkedPaths.Contains(native.Path.Combine(root, "myFile2.txt")), "Native ACL blocked-file callback was never called.");
    var preserved = ReadPolicy.Create(native, native.Path.Combine(root, "myFile2.txt"));
    try { preserved.Directory.GetFiles(root); throw new Exception("Wrapping removed an existing ACL restriction."); }
    catch (UnauthorizedAccessException) { }
    var denied = await Failure(() => native.File.ReadAllBytesAsync(native.Path.Combine(root, "myFile2.txt")));
    Check(denied.Exception is UnauthorizedAccessException && denied.Synchronous,
        "Pinned native async-read denial changed; review the policy semantics.");
    var proxied = await Failure(() => preserved.File.ReadAllBytesAsync(native.Path.Combine(root, "myFile2.txt")));
    Check(proxied.Exception.GetType() == denied.Exception.GetType() && proxied.Synchronous == denied.Synchronous,
        "Read denial type or timing differs from the native mock.");
    Check(proxied.Exception.Message == denied.Exception.Message && proxied.Exception.HResult == denied.Exception.HResult,
        "Read denial message or HResult differs from the native mock.");
    await ExpectDenied(() => preserved.File.ReadAllBytesAsync(native.Path.Combine(root, "myFile2.txt").ToUpperInvariant()),
        native.Path.Combine(root, "myFile2.txt"));
    Console.WriteLine("PASS: native Windows-simulated path-only ACL reproduces enumeration failure and synchronous read denial.");
}

static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
static async Task ExpectDenied(Func<Task<byte[]>> read, string path)
{
    var failure = await Failure(read);
    Check(failure.Exception is UnauthorizedAccessException, "Unexpected denial type.");
    Check(failure.Exception.Message == $"Access to the path '{path}' is denied.", "Unexpected denial message.");
    Check(failure.Synchronous, "Pinned native mock denies async reads synchronously.");
}
static async Task<(Exception Exception, bool Synchronous)> Failure(Func<Task<byte[]>> read)
{
    Task<byte[]> task;
    try { task = read(); }
    catch (Exception exception) { return (exception, true); }
    try { await task; }
    catch (Exception exception) { return (exception, false); }
    throw new Exception("An operation expected to fail succeeded.");
}

internal sealed class FileReaderService(IFileSystem fileSystem)
{
    public async Task Check(string directory, string first, string second, byte[] expected)
    {
        for (var attempt = 0; attempt < 2; attempt++)
        {
            var files = fileSystem.Directory.GetFiles(directory);
            if (!files.Order(StringComparer.Ordinal).SequenceEqual(new[] { first, second }.Order(StringComparer.Ordinal)))
                throw new Exception("Both original files must be listed.");
            if (!(await fileSystem.File.ReadAllBytesAsync(first)).SequenceEqual(expected))
                throw new Exception("First file content was not preserved.");
            try { await fileSystem.File.ReadAllBytesAsync(second); throw new Exception("The blocked file was readable."); }
            catch (UnauthorizedAccessException exception) when (exception.Message == $"Access to the path '{second}' is denied.") { }
        }
    }
}
