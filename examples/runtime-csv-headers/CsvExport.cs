using CsvHelper;

public sealed record ExportLabels(string VehicleName, string Speed, string Notes, string ObservedOn);

[CsvRecord]
public sealed partial record ExportModel(
    [CsvColumn(Index = 0)] string VehicleName,
    [CsvColumn(Index = 1)] decimal Speed,
    [CsvColumn(Index = 2)] string? Notes,
    [CsvColumn(Index = 3), CsvFormat("d")] DateTime ObservedOn);

public static class CsvExport
{
    public static void Write(TextWriter destination, IEnumerable<ExportModel> records,
        ExportLabels labels, CsvWriterOptions options)
    {
        using var csv = CsvWriter.Create(destination, options, leaveOpen: true);
        if (options.HasHeader)
            csv.WriteHeader(labels.VehicleName, labels.Speed, labels.Notes, labels.ObservedOn);
        csv.WriteRecords(records);
    }
}
