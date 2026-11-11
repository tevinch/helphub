# Compact CSV exports with sparse read mappings

CsvHelper 34 writes `[CsvColumn(Index = n)]` at the absolute output position `n`. A model with indices 0 and 10 produces eleven columns, including the empty positions. The official [column-order documentation](https://github.com/JoshClose/CsvHelper/blob/v34.0.0/docs/pages/records.md#columns) describes this behavior.

For a headered model that needs no positional read mapping, omit `Index` and place members in the desired declaration order. The generator writes constructor parameters first, then other members in declaration order, with base members first. `PlainRow` and `PlainExpandedRow` in [Models.cs](Models.cs) demonstrate adding a middle column without numbering any members.

If a shared model must retain its sparse input positions, give each export its own native `CsvRecordWriter<T>`:

```csharp
using var csv = CsvWriter.ToFile("compact.csv", options);
csv.WriteRecords(rows, new CompactRowWriter());
```

[CompactWriters.cs](CompactWriters.cs) contains the complete two-column writer:

```csharp
public sealed class CompactRowWriter : CsvRecordWriter<SparseRow>
{
    public override int FieldCount => 2;

    public override void WriteHeader(CsvWriter writer)
    {
        WriteColumnName(writer, "ID");
        WriteColumnName(writer, "Name");
    }

    public override void Write(CsvWriter writer, SparseRow record)
    {
        writer.WriteField(record.Id);
        writer.WriteField(record.Name);
    }
}
```

The header and data methods write fields only. `WriteRecords` ends the records and applies `HasHeader`; do not call `EndRecord` inside these methods. Native `WriteField` handles quoting, escaping and writer options.

The original model keeps `ID` at 0 and `Name` at 10. The evolved model adds `Note` at 5, with those existing positions unchanged. `ExpandedRowWriter` exports `ID,Note,Name` in three compact columns, and `NamesFirstWriter` exports that same model as `Name,ID,Note`. Adding a column changes the explicit writer's header, fields and `FieldCount`; existing read indices need no renumbering. Passing the writer per call leaves other exports and the generated read mapping available.

This is the documented [explicit-record-writer overload](https://github.com/JoshClose/CsvHelper/blob/v34.0.0/docs/pages/writing.md#writing-csvrecord-types). It does not change the meaning of `Index` or add a sparse-order setting. Each custom writer chooses its fields and formatting explicitly; mapping attributes such as `CsvFormat` and custom converters are not automatically copied into its `WriteField` calls. For a new generated export type, the declaration-order approach is usually shorter.

## Run the example

Requires the .NET 8 SDK and Python 3. The project pins **CsvHelper 34.0.0**, including its source generator. From this directory:

```sh
dotnet restore --locked-mode
dotnet build -c Release --no-restore
dotnet run -c Release --no-build
python3 verify_output.py
```

Both programs accept an optional output directory. For example:

```sh
dotnet run -c Release --no-build -- /tmp/compact-csv-output
python3 verify_output.py /tmp/compact-csv-output
```

Use an empty output directory for the independent check. The verifier expects exactly the files in the following table.

| File | Complete export |
| --- | --- |
| `baseline.csv` | Original generated layout, eleven columns at positions 0–10 |
| `compact.csv` | The same objects, two columns |
| `evolved-default.csv` | Evolved generated layout, values at 0, 5 and 10 |
| `evolved.csv` | Evolved model, three compact columns |
| `names-first.csv` | Same evolved model, another column order |
| `declaration-before.csv` | Headered two-column model without indices |
| `declaration-after.csv` | A middle declaration added, three columns without renumbering |
| `empty.csv` | Explicit header with zero data rows |
| `semicolon.csv` | Explicit layout with semicolon separators and LF record endings |
| `headerless.csv` | Three compact columns with `HasHeader = false` |
| `default-after.csv` | Original generated output again, byte-for-byte unchanged |

The fixture includes accented text, commas, semicolons, quotes, an embedded CRLF, nulls and empty strings. It uses `NullValue = "NULL"` and matching reader `NullValues` to distinguish a null from an empty string; choose a marker that does not occur as an ordinary value in your own data.

## Verification and scope

The console reopens every persisted file through a real `CsvReader`, checks the complete header and every field of every row, and runs the generated typed readers against the original and evolved sparse files. Python's separate standard CSV reader and encoder compare all eleven files against literal expected fields and exact UTF-8 bytes.

Checked with .NET SDK 8.0.426/runtime 8.0.32 and Python 3.12.4 on macOS arm64. Negative checks rejected a generated default writer substituted for the compact writer, an incorrect exported value, an omitted evolved index, changed or missing data, and an unwanted header. These are scripted consumer checks; the original application and human manual validation were not performed.

Copy the writer for the layout you need, adjust its explicit fields and matching `FieldCount`, and pass it to your existing writer call. The example changes no CsvHelper source or generator behavior. CsvHelper retains its upstream license; this repository licenses only this example.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
