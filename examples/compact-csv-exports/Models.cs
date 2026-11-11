using CsvHelper;

// These positions describe the sparse input format; the example leaves them intact.
[CsvRecord]
public partial class SparseRow
{
    [CsvColumn("ID", Index = 0)]
    public int Id { get; set; }

    [CsvColumn("Name", Index = 10)]
    public string? Name { get; set; }
}

// A new sparse input column fits between 0 and 10. Existing positions stay unchanged.
[CsvRecord]
public partial class EvolvedSparseRow
{
    [CsvColumn("ID", Index = 0)]
    public int Id { get; set; }

    [CsvColumn("Note", Index = 5)]
    public string? Note { get; set; }

    [CsvColumn("Name", Index = 10)]
    public string? Name { get; set; }
}

// For headered models that need no positional read mapping, declaration order is simpler.
[CsvRecord]
public partial class PlainRow
{
    [CsvColumn("ID")]
    public int Id { get; set; }

    public string? Name { get; set; }
}

[CsvRecord]
public partial class PlainExpandedRow
{
    [CsvColumn("ID")]
    public int Id { get; set; }

    public string? Note { get; set; }

    public string? Name { get; set; }
}
