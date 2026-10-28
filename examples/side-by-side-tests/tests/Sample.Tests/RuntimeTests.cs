using System.Runtime.InteropServices;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Sample.Library;

namespace Sample.Tests;

[TestClass]
public sealed class RuntimeTests
{
    public TestContext TestContext { get; set; } = null!;

    [TestMethod]
    public void TestsActuallyRunOnNet8()
    {
        TestContext.WriteLine($"Test process runtime: {RuntimeInformation.FrameworkDescription}");
        TestContext.WriteLine($"Environment.Version: {Environment.Version}");
        Assert.AreEqual(8, Environment.Version.Major);
        Assert.IsTrue(RuntimeInformation.FrameworkDescription.StartsWith(".NET 8."));
    }

    [TestMethod]
    public void LibraryIgnoresEmptyAndWhitespaceOnlyLines()
    {
        Assert.AreEqual(2, LineCounter.CountNonEmpty("alpha\n\n \r\nbeta\n"));
    }
}
