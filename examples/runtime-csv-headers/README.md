# Runtime headers with generated CsvHelper records

CsvHelper 34 can write runtime-selected column names while its source generator still serializes the data records. Write the header first, then call `WriteRecords`:

```csharp
using var csv = CsvWriter.Create(destination, options, leaveOpen: true);
csv.WriteHeader(labels.VehicleName, labels.Speed, labels.Notes, labels.ObservedOn);
csv.WriteRecords(records);
```

`WriteHeader` accepts ordinary runtime strings, including resource/localizer results. It escapes them as CSV fields and ends the header record. `WriteRecords` adds its generated header only when nothing has been written yet, so this produces one header followed by generated data rows. Do not add `EndRecord()` after `WriteHeader()`.

The included `CsvExport.Write` also checks `options.HasHeader`: set it to `false` when the export should have no header. It retains the caller's separator, format provider, null marker and line endings, and leaves the destination open. There is no global mapping registration or replacement record writer.

Keep the runtime names in the same order as the generated columns. The example pins that order with `[CsvColumn(Index = ...)]`; update both when changing the model. Its extra date field uses `[CsvFormat("d")]` so the caller's culture controls the short date. The same approach works with your own record's fields and existing format attributes.

## Try it

Requires the .NET 10 SDK and, for the separate output check, Python 3. The project pins the current stable **CsvHelper 34.0.0**, including its native source generator. From this directory:

```sh
dotnet restore --locked-mode
dotnet build -c Release --no-restore
dotnet run -c Release --no-build
python3 verify_output.py
```

`Program.cs` selects two English header sets at runtime: en-US with a comma separator and en-GB with a semicolon. The output files in `output/` show complete generated records, Unicode, escaped quotes, both separators, embedded line breaks, a null marker and different date formats. Repeated exports use fresh writers; an empty export still has its selected header, and the explicit header opt-out has data only.

For adoption, copy `CsvExport.cs`'s two native calls into your export, pass your runtime labels and existing `CsvWriterOptions`, and keep the record's `[CsvRecord] partial` declaration and generator reference. Reading localized names is a separate operation; this example addresses export.

## Verification and scope

The console runs six complete export workflows through the real 34.0.0 writer and generated mapping. It checks the native header, all typed values through a real CsvReader, actual culture-specific text and null formatting, no duplicate header, repeated writers, empty data and `HasHeader = false`. Python's independent standard CSV reader then checks every field of every complete output file against literal expected values. The source was verified with .NET SDK 10.0.402/runtime 10.0.13 and Python 3.12.4 on macOS.

The native automatic-header baseline failed to supply the runtime labels. Omitting the runtime header and explicitly adding another generated header also failed the full output checks. These are scripted consumer checks; the original application's exports and human manual validation were not performed.

See CsvHelper's official [writing guide](https://joshclose.github.io/CsvHelper/writing.html#writing-csvrecord-types), [culture settings](https://joshclose.github.io/CsvHelper/writing.html#cultures) and [34 migration guide](https://github.com/JoshClose/CsvHelper/blob/master/docs/releases/v34.0.0/migration.md). This example changes no CsvHelper source or generator behavior. CsvHelper retains its upstream license; this repository licenses only this example.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
