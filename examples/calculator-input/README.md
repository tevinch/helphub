# Retry calculator input without an exception

Use `TryParse` to check input before doing arithmetic. It returns `false` for invalid input, so the calculator can explain the problem and ask again.

The [original question](https://github.com/yusufdincel/Basic-Calculator/issues/1) mentions `Convert.ToInt32`, while its current source reads fractional operands with `Single.Parse`. For that source, use `float.TryParse` at **every** operand prompt, including the retry after a zero divisor. Converting a retry to an integer would change the accepted input.

Copy this method into the existing program's class:

```csharp
static float? ReadNumber(string prompt)
{
    while (true)
    {
        Console.Write(prompt);
        string text = Console.ReadLine();
        if (text == null)
            return null;
        float value;
        if (float.TryParse(text, out value) && !float.IsNaN(value) && !float.IsInfinity(value))
            return value;
        Console.WriteLine("Enter a finite number.");
    }
}
```

Call it where the original code reads an operand:

```csharp
float? input = ReadNumber("First number: ");
if (!input.HasValue)
    return;
float first = input.Value;
```

Use the same pattern for the second operand and zero-divisor retries. Keep these operands as `float`: remove the original block that converts parsed operands to `Int32` to check whether they are whole numbers. Those conversions can throw for valid floating-point values outside the integer range and are unnecessary for the arithmetic.

`null` means the input stream ended; the caller should return instead of calculating with a missing value. A successful parse can still produce `NaN` or infinity, including overflow to infinity on modern .NET, so the additional checks reject those values. Parsing uses `CurrentCulture`, matching the original `Single.Parse` default. For example, a German locale uses a decimal comma. This overload also accepts the culture's thousands separator; it is not a strict decimal-only validator.

This pattern uses APIs available in .NET Framework 4.7.2 and needs no package or project upgrade. The standalone project below targets .NET 8; it is a separate runnable demonstration, not a requirement for using the method in the existing project.

## Run the complete example

With the .NET 8 SDK and runtime installed:

```sh
dotnet run
```

Enter a first number, an operation, and a second number for binary operations. The example supports `+`, `-`, `*`, `/`, `%` and `sqrt`. After a result it starts the next calculation. End input with Ctrl+D on Unix, or Ctrl+Z followed by Enter on Windows.

For an English locale, enter these lines:

```text
hello
1.5
+
2.25
4
*
3
```

The calculator asks again after `hello`, then prints `Result: 1.5 + 2.25 = 3.75` and `Result: 4 * 3 = 12`. Division retains fractional results, such as `3 / 2 = 1.5`. Invalid operations and zero divisors are retried; negative square roots and arithmetic overflow are reported before the next calculation.

The arithmetic uses `Single` precision, as in the original fractional calculator. It is not arbitrary-precision arithmetic, and decimal fractions can be rounded. This is a fresh small example rather than a copy of the original project.

## If the input must be an integer

Use `int.TryParse` instead. Check its Boolean result; the `out` value alone does not tell you whether parsing succeeded.

```csharp
string text = Console.ReadLine();
int value;
if (int.TryParse(text, out value))
    Console.WriteLine(value);
else
    Console.WriteLine("Enter a 32-bit integer.");
```

This accepts signed 32-bit integers and rejects values outside `-2147483648` to `2147483647`. It rejects fractional input rather than rounding it. Put the check in a retry loop when the program should keep asking, and check `text == null` separately when reaching the end of input should exit.

## Verify

With Python 3 available:

```sh
python3 verify.py
```

The verifier builds a temporary copy and runs actual console processes through invalid input, successful arithmetic, repeated calculations, six operations, zero divisors, domain errors, nonfinite values and end of input. It also compiles and runs the integer snippet above. A German-locale check verifies decimal-comma input. An optional first argument selects a different `dotnet` executable.

Verified with .NET SDK 8.0.426/runtime 8.0.32 on macOS using C# 7.3. These were scripted checks; the original .NET Framework application and Windows console were not run.

References: [Single.TryParse](https://learn.microsoft.com/en-us/dotnet/api/system.single.tryparse?view=netframework-4.7.2), [Int32.TryParse](https://learn.microsoft.com/en-us/dotnet/api/system.int32.tryparse?view=netframework-4.7.2).

## Optional coffee

This example is free. If it saves you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
