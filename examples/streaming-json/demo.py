"""Run the file recipes in a new output directory; no external HTTP requests."""
import io
import json
import sys
from pathlib import Path

import recipes


def main(directory):
    directory.mkdir()  # Refuse to overwrite an existing directory.
    array_path = directory / "rows.json"
    lines_path = directory / "rows.jsonl"
    with array_path.open("w", encoding="utf-8") as array, lines_path.open("w", encoding="utf-8") as lines:
        array.write("[")
        for number in range(10_000):
            row = {
                "id": number, "name": f"Café {number}", "value": number,
                "status": "active" if number % 2 == 0 else "inactive",
            }
            encoded = json.dumps(row, ensure_ascii=False)
            if number:
                array.write(",\n")
            array.write(encoded)
            lines.write(encoded + "\n")
        array.write("]\n")

    with array_path.open("rb") as source:
        print("array rows:", recipes.write_active(source, directory / "active.json"))
    with lines_path.open("rb") as source:
        print("NDJSON rows:", recipes.write_active(source, directory / "active-lines.json", ndjson=True))
    with array_path.open("rb") as source:
        print("statistics:", recipes.statistics(source))

    good = b'{"data":[{"id":1,"score":1.5,"nested":[true,null]}],"errors":[]}'
    destination = directory / "graphql.json"
    print("GraphQL rows:", recipes.write_graphql(io.BytesIO(good), destination))
    before = destination.read_bytes()
    try:
        recipes.write_graphql(io.BytesIO(b'{"data":[2],"errors":[{"message":"late error"}]}'), destination)
    except recipes.GraphQLError:
        assert destination.read_bytes() == before
        print("late GraphQL error: previous file preserved")

    value = "雨Café" * 4096
    single = json.dumps({"text": value}, ensure_ascii=False).encode()
    print("single string event lengths:", recipes.string_event_lengths(io.BytesIO(single)))
    chunks = io.BytesIO(b'{"chunks":["Caf","\xc3\xa9 ","\xe9\x9b\xa8"]}')
    print("chunked text characters:", sum(len(piece) for piece in recipes.text_chunks(chunks)))
    print("Files:", directory)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python demo.py NEW_OUTPUT_DIRECTORY")
    main(Path(sys.argv[1]))
