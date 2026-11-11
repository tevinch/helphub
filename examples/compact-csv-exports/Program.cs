using CsvHelper;
using System.Globalization;

if (args.Length > 1)
    throw new ArgumentException("Usage: dotnet run -- [output-directory]");
var output = args.Length == 1 ? Path.GetFullPath(args[0]) : Path.Combine(Directory.GetCurrentDirectory(), "output");
Directory.CreateDirectory(output);
var rows = new[]
{
    new SparseRow { Id = 1, Name = "Café, large" },
    new SparseRow { Id = 2, Name = "A \"quoted\" name" },
    new SparseRow { Id = 3, Name = "line one\r\nline two" },
    new SparseRow { Id = 4, Name = null },
    new SparseRow { Id = 5, Name = "" },
};
var options = new CsvWriterOptions { NullValue = "NULL" };
string?[] notes = ["new column", "x;y", "A note", null, ""];
var evolved = rows.Select((row, i) =>
    new EvolvedSparseRow { Id = row.Id, Name = row.Name, Note = notes[i] }).ToArray();
var plain = rows.Select(row => new PlainRow { Id = row.Id, Name = row.Name }).ToArray();
var plainExpanded = evolved.Select(row =>
    new PlainExpandedRow { Id = row.Id, Note = row.Note, Name = row.Name }).ToArray();

WriteFile("baseline.csv", rows);
WriteFile("compact.csv", rows, new CompactRowWriter());
WriteFile("evolved-default.csv", evolved);
WriteFile("evolved.csv", evolved, new ExpandedRowWriter());
WriteFile("names-first.csv", evolved, new NamesFirstWriter());
WriteFile("declaration-before.csv", plain);
WriteFile("declaration-after.csv", plainExpanded);
WriteFile("empty.csv", Array.Empty<SparseRow>(), new CompactRowWriter());
WriteFile("semicolon.csv", evolved, new NamesFirstWriter(), options with { Separator = ';', NewLine = "\n" });
WriteFile("headerless.csv", evolved, new ExpandedRowWriter(), options with { HasHeader = false });
// This call still uses the original generated sparse layout.
WriteFile("default-after.csv", rows);

var pairs = rows.Select(row => new string?[] { row.Id.ToString(CultureInfo.InvariantCulture), row.Name }).ToArray();
var expanded = evolved.Select(row => new string?[] {
    row.Id.ToString(CultureInfo.InvariantCulture), row.Note, row.Name }).ToArray();
var namesFirst = evolved.Select(row => new string?[] {
    row.Name, row.Id.ToString(CultureInfo.InvariantCulture), row.Note }).ToArray();
var sparse = pairs.Select(row => new string?[] {
    row[0], "", "", "", "", "", "", "", "", "", row[1] }).ToArray();
var evolvedSparse = expanded.Select(row => new string?[] {
    row[0], "", "", "", "", row[1], "", "", "", "", row[2] }).ToArray();
string[] sparseHeader = ["ID", "", "", "", "", "", "", "", "", "", "Name"];
CheckFile("baseline.csv", sparseHeader, sparse);
CheckFile("compact.csv", ["ID", "Name"], pairs);
CheckFile("evolved-default.csv", ["ID", "", "", "", "", "Note", "", "", "", "", "Name"], evolvedSparse);
CheckFile("evolved.csv", ["ID", "Note", "Name"], expanded);
CheckFile("names-first.csv", ["Name", "ID", "Note"], namesFirst);
CheckFile("declaration-before.csv", ["ID", "Name"], pairs);
CheckFile("declaration-after.csv", ["ID", "Note", "Name"], expanded);
CheckFile("empty.csv", ["ID", "Name"], []);
CheckFile("semicolon.csv", ["Name", "ID", "Note"], namesFirst, ';');
CheckFile("headerless.csv", ["ID", "Note", "Name"], expanded, hasHeader: false);
CheckFile("default-after.csv", sparseHeader, sparse);

// Exercise the actual generated sparse reader after all per-export writers have run.
using (var reader = CsvReader.FromFile(Path.Combine(output, "default-after.csv"),
    new CsvReaderOptions { NullValues = ["NULL"] }))
{
    var readBack = reader.GetRecords<SparseRow>().ToArray();
    if (readBack.Length != rows.Length ||
        !readBack.Select(row => (row.Id, row.Name)).SequenceEqual(rows.Select(row => (row.Id, row.Name))))
        throw new InvalidOperationException("Original sparse read mapping or typed values changed.");
}
if (!File.ReadAllBytes(Path.Combine(output, "baseline.csv")).SequenceEqual(
    File.ReadAllBytes(Path.Combine(output, "default-after.csv"))))
    throw new InvalidOperationException("Per-call writers changed the default export.");
using (var reader = CsvReader.FromFile(Path.Combine(output, "evolved-default.csv"),
    new CsvReaderOptions { NullValues = ["NULL"] }))
{
    var readBack = reader.GetRecords<EvolvedSparseRow>().ToArray();
    if (readBack.Length != evolved.Length ||
        !readBack.Select(row => (row.Id, row.Note, row.Name)).SequenceEqual(
            evolved.Select(row => (row.Id, row.Note, row.Name))))
        throw new InvalidOperationException("Evolved sparse read positions 0, 5 and 10 changed.");
}
Console.WriteLine($"PASS: 11 complete exports, every native-read field/row, both sparse read mappings and per-call isolation ({output})");

void WriteFile<T>(string file, IEnumerable<T> records, CsvRecordWriter<T>? schema = null,
    CsvWriterOptions? settings = null)
{
    using var writer = CsvWriter.ToFile(Path.Combine(output, file), settings ?? options);
    if (schema is null)
        writer.WriteRecords(records);
    else
        writer.WriteRecords(records, schema);
}

void CheckFile(string file, string[] header, string?[][] expected, char separator = ',', bool hasHeader = true)
{
    using var reader = CsvReader.FromFile(Path.Combine(output, file),
        new CsvReaderOptions { Separator = separator, NullValues = ["NULL"], HasHeader = hasHeader });
    if (hasHeader)
    {
        reader.GetFieldIndex(header[0]); // Independently force the native header read, even with no data.
        if (!reader.Headers.SequenceEqual(header))
            throw new InvalidOperationException($"{file}: wrong complete header.");
    }
    var count = 0;
    while (reader.Read())
    {
        if (count >= expected.Length || reader.FieldCount != header.Length)
            throw new InvalidOperationException($"{file}: wrong row or field count.");
        for (var column = 0; column < header.Length; column++)
            if (reader.GetStringOrNull(column) != expected[count][column])
                throw new InvalidOperationException($"{file}: row {count}, column {column} differs.");
        count++;
    }
    if (count != expected.Length)
        throw new InvalidOperationException($"{file}: missing complete data rows.");
}
