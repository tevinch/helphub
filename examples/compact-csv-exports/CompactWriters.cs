using CsvHelper;

// Pass this instance to WriteRecords; it does not replace the generated writer.
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

public sealed class ExpandedRowWriter : CsvRecordWriter<EvolvedSparseRow>
{
    public override int FieldCount => 3;

    public override void WriteHeader(CsvWriter writer)
    {
        WriteColumnName(writer, "ID");
        WriteColumnName(writer, "Note");
        WriteColumnName(writer, "Name");
    }

    public override void Write(CsvWriter writer, EvolvedSparseRow record)
    {
        writer.WriteField(record.Id);
        writer.WriteField(record.Note);
        writer.WriteField(record.Name);
    }
}

public sealed class NamesFirstWriter : CsvRecordWriter<EvolvedSparseRow>
{
    public override int FieldCount => 3;

    public override void WriteHeader(CsvWriter writer)
    {
        WriteColumnName(writer, "Name");
        WriteColumnName(writer, "ID");
        WriteColumnName(writer, "Note");
    }

    public override void Write(CsvWriter writer, EvolvedSparseRow record)
    {
        writer.WriteField(record.Name);
        writer.WriteField(record.Id);
        writer.WriteField(record.Note);
    }
}
