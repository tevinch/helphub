# List files while denying one async read

A test may need `Directory.GetFiles` to list two files, while `File.ReadAllBytesAsync` can read only one. Testably's `DefaultAccessControlStrategy` decides access from a path and its extension data; it does not receive the operation. Denying a file there can also prevent enumeration.

This example keeps the application on `IFileSystem`. A small test-only [Castle interface proxy](https://www.castleproject.org/projects/dynamicproxy/) forwards calls to `MockFileSystem` and rejects `ReadAllBytesAsync` for one full path. The files remain in the mock.

```sh
dotnet restore --locked-mode
dotnet run --no-restore
```

Requires the .NET 8 SDK. Packages are pinned to Testably.Abstractions.Testing 7.1.1 and Castle.Core 5.2.1; `packages.lock.json` pins the dependency graph.

The executable checks this complete sequence twice:

1. List `myFile1.txt` and `myFile2.txt`.
2. Read the exact bytes of `myFile1.txt`.
3. Observe `UnauthorizedAccessException` when reading `myFile2.txt`.
4. List both files again and successfully read the first again.

It also checks concurrent reads, default and explicit cancellation tokens, relative paths, another directory containing the same filename, native failure details for malformed paths, forwarded operations, and unchanged original content. A separate Windows-simulated fixture reproduces the path-only ACL enumeration failure and verifies that wrapping an existing ACL does not remove its restriction.

## Use in a test

Copy `ReadPolicy.cs` into your test project and reference the two packages above. Seed a fresh mock, then pass the returned `IFileSystem` to your existing service:

```csharp
using System.IO.Abstractions;
using Testably.Abstractions.Testing;
using FileReadPolicyExample;

var mock = new MockFileSystem();
var folder = mock.Path.GetFullPath("sample");
mock.Directory.CreateDirectory(folder);
var first = mock.Path.Combine(folder, "myFile1.txt");
var second = mock.Path.Combine(folder, "myFile2.txt");
mock.File.WriteAllText(first, "one");
mock.File.WriteAllText(second, "two");

IFileSystem fileSystem = ReadPolicy.Create(mock, second);
var paths = fileSystem.Directory.GetFiles(folder); // both files
var bytes = await fileSystem.File.ReadAllBytesAsync(first);
try
{
    await fileSystem.File.ReadAllBytesAsync(second);
}
catch (UnauthorizedAccessException)
{
    // Exercise the application's unreadable-file handling.
}
```

Use this operation-specific setup instead of installing a path-only ACL callback that denies the same file. If the backing mock already denies enumeration, the proxy preserves that failure. The helper does not change the mock's ACL settings or content.

## Scope and behavior

This is a test policy for `IFile.ReadAllBytesAsync`, not a new native ACL feature or a security boundary. Other methods, including `ReadAllText`, streams and `FileInfo` entry points, retain their underlying behavior. Objects reached through another object's `FileSystem` property are also the backing mock. Use the returned root `IFileSystem` for the demonstrated calls.

The helper normalizes paths using the backing mock. Windows-style paths compare without case; other paths compare with case. Unmatched calls and pre-cancelled calls proceed to the native mock with their original arguments. In pinned Testably 7.1.1, async-read access denial and pre-cancellation throw synchronously; the example verifies and preserves those observable behaviors, including native cancellation metadata. It does not claim full Windows ACL fidelity.

Castle generates proxies at runtime, so this example targets ordinary .NET test execution rather than NativeAOT. Validation was scripted on macOS arm64 with .NET SDK 8.0.426/runtime 8.0.32, including Windows simulation. It does not establish native Windows testing or original-requester adoption.

See [Testably's access-control guide](https://docs.testably.org/Abstractions/file-system/access-control/) and [the original usage question](https://github.com/Testably/Testably.Abstractions/issues/1158).

## Optional coffee

The example is free. If it saves you time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
