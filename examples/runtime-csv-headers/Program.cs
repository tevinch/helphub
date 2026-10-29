using System.Globalization;
using System.Text;
using CsvHelper;

var outputDirectory = args.Length == 0 ? "output" : args[0];
Directory.CreateDirectory(outputDirectory);
if (!CsvRecordWriter.IsRegistered<ExportModel>())
    throw new InvalidOperationException("The native generated record writer did not register.");

ExportModel[] records = [
    new("Bus 🚍, \"Express\"\r\nLine 2", 1234.5m, null, new DateTime(2026, 11, 30)),
    new("Shuttle; blue", 7.25m, "Keep \"quotes\", commas; and\nnewlines", new DateTime(2026, 12, 1)),
];
var usLabels = new ExportLabels("Vehicle, name", "Speed", "Notes", "Observed on");
var gbLabels = new ExportLabels("Vehicle name", "Speed", "Remarks", "Observation date");
var usOptions = new CsvWriterOptions {
    Separator = ',', FormatProvider = CultureInfo.GetCultureInfo("en-US"), NullValue = "(missing)",
};
var gbOptions = new CsvWriterOptions {
    Separator = ';', FormatProvider = CultureInfo.GetCultureInfo("en-GB"), NullValue = "(missing)",
};
int completed = 0;
foreach (var name in new[] { "us-first", "gb-first", "gb-repeat", "us-repeat", "us-empty", "us-no-header" })
{
    bool us = name.StartsWith("us-", StringComparison.Ordinal);
    var labels = us ? usLabels : gbLabels;
    bool includesHeader = name != "us-no-header";
    var options = (us ? usOptions : gbOptions) with { HasHeader = includesHeader };
    var items = name.EndsWith("-empty", StringComparison.Ordinal) ? Array.Empty<ExportModel>() : records;
    var text = new StringBuilder();
    using (var destination = new StringWriter(text, CultureInfo.InvariantCulture))
    {
        CsvExport.Write(destination, items, labels, options);
        // The destination belongs to the caller and remains usable.
        destination.Write("");
    }
    string csv = text.ToString();
    File.WriteAllText(Path.Combine(outputDirectory, name + ".csv"), csv, new UTF8Encoding(false));
    string[] expectedHeaders = [labels.VehicleName, labels.Speed, labels.Notes, labels.ObservedOn];
    var readerOptions = new CsvReaderOptions {
        Separator = options.Separator, FormatProvider = options.FormatProvider,
        NullValues = ["(missing)"], HasHeader = includesHeader,
    };
    using (var reader = CsvReader.FromText(csv, readerOptions))
    {
        if (includesHeader)
        {
            reader.GetFieldIndex(expectedHeaders[0]); // Forces the actual native header read.
            if (!reader.Headers.SequenceEqual(expectedHeaders))
                throw new InvalidOperationException("Runtime-selected header is missing or out of order: " + string.Join(" | ", reader.Headers));
        }
        var actual = reader.GetRecords<ExportModel>().ToArray();
        if (!actual.SequenceEqual(items))
            throw new InvalidOperationException("Every generated data row must round-trip exactly, with no extra header.");
    }
    // Check the actual formatted text too; a symmetric reader/writer mistake cannot satisfy this.
    using (var reader = CsvReader.FromText(csv, readerOptions))
    {
        int count = 0;
        while (reader.Read())
        {
            if (reader.GetString(1) != (count == 0 ? "1234.5" : "7.25"))
                throw new InvalidOperationException("Caller number formatting changed.");
            string expectedDate = us
                ? (count == 0 ? "11/30/2026" : "12/1/2026")
                : (count == 0 ? "30/11/2026" : "01/12/2026");
            if (reader.GetString(3) != expectedDate)
                throw new InvalidOperationException("Caller date culture changed: " + reader.GetString(3));
            if (count == 0 && reader.GetString(2) != "(missing)")
                throw new InvalidOperationException("Caller null marker changed.");
            count++;
        }
        if (count != items.Length) throw new InvalidOperationException("Unexpected data row count.");
    }
    if (options.HasHeader != includesHeader || options.NewLine != "\r\n" || !usOptions.HasHeader || !gbOptions.HasHeader)
        throw new InvalidOperationException("Caller options changed.");
    completed++;
}
if (completed != 6) throw new InvalidOperationException("Every export workflow must run.");
Console.WriteLine("PASS: generated exports, runtime headers, culture/options, repeated writers, empty input and header opt-out (6 workflows).");
