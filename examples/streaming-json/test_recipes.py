"""Consumer checks: real files, parser backends, and loopback HTTP streams."""
import io
import json
import socket
import tempfile
import threading
import tracemalloc
import unittest
from contextlib import contextmanager
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import ijson
import recipes


ROWS = [
    {"id": 1, "status": "active", "name": "Café 雨", "value": 3},
    {"id": 2, "status": "inactive", "name": "skip", "value": -1},
    {"id": 3, "status": "active", "name": "Lin", "value": 7},
]
EXPECTED = [{"id": 1, "name": "Café 雨"}, {"id": 3, "name": "Lin"}]
BODY = json.dumps(ROWS, ensure_ascii=False).encode()
HTTP_BODY = json.dumps([
    ROWS[0], dict(ROWS[1], padding="x" * 100_000), ROWS[2]
], ensure_ascii=False).encode()


class SmallReads(io.BytesIO):
    """Reject eager reads and expose whether results precede EOF."""
    def __init__(self, body, width=7):
        super().__init__(body)
        self.width = width
        self.calls = []

    def read(self, size=-1):
        self.calls.append(size)
        if size < 0:
            raise AssertionError("The consumer tried to read the whole input")
        return super().read(min(size, self.width))

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


@contextmanager
def server():
    hits = []
    sent = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_GET(self):
            hits.append(self.path)
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/ok")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            broken = self.path == "/broken" or (
                self.path == "/retry" and hits.count("/retry") == 1
            )
            payload = HTTP_BODY[:-8] if broken else HTTP_BODY
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            # Split UTF-8 characters in the first part, then send bounded blocks.
            chunks = [payload[n:n + 1] for n in range(min(200, len(payload)))]
            chunks.extend(payload[n:n + 4096] for n in range(200, len(payload), 4096))
            for chunk in chunks:
                self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                sent.append(len(chunk))
                self.wfile.flush()
            if broken:
                self.close_connection = True
                self.connection.shutdown(socket.SHUT_WR)
            else:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()

    host = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=host.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{host.server_port}", hits, sent
    finally:
        host.shutdown()
        host.server_close()
        worker.join(timeout=2)
        assert not worker.is_alive()


class RecipesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.target = self.directory / "active.json"

    def test_array_transform_writes_complete_output(self):
        # Dropping the filter, transformation, or final array bracket breaks this.
        count = recipes.write_active(SmallReads(BODY), self.target)
        self.assertEqual(count, 2)
        self.assertEqual(json.loads(self.target.read_text()), EXPECTED)

    def test_empty_and_all_inactive_arrays(self):
        for body in [b"[]", b'[{"id":1,"status":"inactive"}]']:
            self.assertEqual(recipes.write_active(io.BytesIO(body), self.target), 0)
            self.assertEqual(json.loads(self.target.read_text()), [])

    def test_malformed_tail_preserves_existing_file(self):
        self.target.write_bytes(b"previous result")
        with self.assertRaises(ijson.JSONError):
            recipes.write_active(io.BytesIO(BODY[:-1]), self.target)
        self.assertEqual(self.target.read_bytes(), b"previous result")
        self.assertEqual(list(self.directory.iterdir()), [self.target])

    def test_first_result_arrives_before_eof(self):
        source = SmallReads(BODY, width=1)
        rows = recipes.active_rows(source)
        self.assertEqual(next(rows, None), EXPECTED[0])
        self.assertLess(source.tell(), len(BODY))
        self.assertTrue(source.calls)
        self.assertEqual(list(rows), [EXPECTED[1]])

    def test_ndjson_processes_every_top_level_value(self):
        raw = b' {"value": 2}\n{"value": -3}\n{"value": 1.5}\n'
        self.assertEqual(list(recipes.ndjson_rows(SmallReads(raw))), [
            {"value": 2}, {"value": -3}, {"value": Decimal("1.5")}
        ])

    def test_ndjson_without_multiple_values_is_a_negative_control(self):
        with self.assertRaises(ijson.JSONError):
            list(ijson.items(io.BytesIO(b'{"v":1}\n{"v":2}'), ""))

    def test_ndjson_truncated_last_record_is_not_ignored(self):
        with self.assertRaises(ijson.JSONError):
            list(recipes.ndjson_rows(io.BytesIO(b'{"v":1}\n{"v":')))

    def test_ndjson_filter_writes_all_rows_and_preserves_file_on_bad_tail(self):
        raw = b"\n".join(json.dumps(row).encode() for row in ROWS)
        self.assertEqual(recipes.write_active(SmallReads(raw), self.target, ndjson=True), 2)
        self.assertEqual(json.loads(self.target.read_text()), EXPECTED)
        before = self.target.read_bytes()
        with self.assertRaises(ijson.JSONError):
            recipes.write_active(SmallReads(raw + b'\n{"id":'), self.target, ndjson=True)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(list(self.directory.iterdir()), [self.target])

    def test_graphql_data_and_nested_values(self):
        raw = b'{"data":[{"id":1,"nested":[true,null,{"x":2}]},{"id":2}],"other":9}'
        self.assertEqual(list(recipes.graphql_rows(SmallReads(raw))), [
            {"id": 1, "nested": [True, None, {"x": 2}]}, {"id": 2}
        ])

    def test_graphql_errors_in_either_order_preserve_destination(self):
        for raw in [
            b'{"errors":[{"message":"not available"}]}',
            b'{"data":[{"id":1}],"errors":[{"message":"late error"}]}',
            b'{"errors":[{"message":"first error"}],"data":[{"id":1}]}',
        ]:
            self.target.write_bytes(b"previous result")
            with self.assertRaises(recipes.GraphQLError):
                recipes.write_graphql(SmallReads(raw), self.target)
            self.assertEqual(self.target.read_bytes(), b"previous result")
            self.assertEqual(list(self.directory.iterdir()), [self.target])

    def test_graphql_empty_arrays_and_scalars(self):
        self.assertEqual(list(recipes.graphql_rows(io.BytesIO(b'{"errors":[],"data":[]}'))), [])
        self.assertEqual(list(recipes.graphql_rows(io.BytesIO(b'{"data":[1,"x",null,true]}'))), [1, "x", None, True])

    def test_graphql_numeric_export_stays_numeric(self):
        recipes.write_graphql(io.BytesIO(b'{"data":[{"score":1.5,"nested":[2.25]}]}'), self.target)
        self.assertEqual(json.loads(self.target.read_text()), [{"score": 1.5, "nested": [2.25]}])

    def test_single_string_is_not_fragmented_by_small_reads(self):
        value = "雨Café" * 4096
        raw = json.dumps({"text": value}, ensure_ascii=False).encode()
        self.assertEqual(recipes.string_event_lengths(SmallReads(raw, 31)), [len(value)])

    def test_chunked_value_is_consumed_without_combining_it(self):
        source = SmallReads(b'{"chunks":["Caf","\xc3\xa9 ","\xe9\x9b\xa8"]}', 1)
        pieces = recipes.text_chunks(source)
        self.assertEqual(next(pieces, None), "Caf")
        self.assertLess(source.tell(), len(source.getvalue()))
        self.assertEqual("Caf" + "".join(pieces), "Café 雨")

    def test_chunked_value_rejects_non_string_items(self):
        with self.assertRaises(ValueError):
            list(recipes.text_chunks(io.BytesIO(b'{"chunks":["ok",null]}')))

    def test_running_statistics_preserve_decimal_values(self):
        raw = b'[{"value":2},{"value":-3},{"value":1.5},{"value":4}]'
        self.assertEqual(recipes.statistics(SmallReads(raw)), {
            "count": 4, "sum": Decimal("4.5"), "min": -3, "max": 4,
            "mean": Decimal("1.125")
        })
        self.assertEqual(recipes.statistics(io.BytesIO(b"[]")), {
            "count": 0, "sum": 0, "min": None, "max": None, "mean": None
        })

    def test_statistics_accepts_ndjson_and_rejects_non_numbers(self):
        result = recipes.statistics(io.BytesIO(b'{"value":-2}\n{"value":3.5}\n'), ndjson=True)
        self.assertEqual(result, {
            "count": 2, "sum": Decimal("1.5"), "min": -2,
            "max": Decimal("3.5"), "mean": Decimal("0.75")
        })
        for bad in [b"null", b"true", b'"3"']:
            with self.assertRaises(ValueError):
                recipes.statistics(io.BytesIO(b'[{"value":' + bad + b'}]'))

    def test_aggregation_does_not_retain_all_rows(self):
        # A tenfold input increase must not retain tenfold Python object state.
        def peak(count):
            raw = io.BytesIO(b"[" + b'{"value":1},' * (count - 1) + b'{"value":1}]')
            tracemalloc.start()
            try:
                result = recipes.statistics(raw)
                top = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()
            self.assertEqual(result["count"], count)
            self.assertEqual(result["sum"], count)
            return top
        small, large = peak(10000), peak(100000)
        self.assertLess(large, small + 1_000_000)

    def test_both_http_clients_restart_without_duplicate_output(self):
        for client in ["requests", "httpx"]:
            with self.subTest(client=client), server() as (base, hits, sent):
                observed = []
                original = recipes.active_rows

                def observe(source, **options):
                    attempt = []
                    observed.append(attempt)
                    for row in original(source, **options):
                        attempt.append(row["id"])
                        yield row

                with patch.object(recipes, "active_rows", observe):
                    count = recipes.download_active(base + "/retry", self.target, client=client)
                self.assertEqual(count, 2)
                self.assertEqual(json.loads(self.target.read_text()), EXPECTED)
                self.assertEqual(observed, [[1], [1, 3]])
                self.assertEqual(hits, ["/retry", "/retry"])
                self.assertGreater(sum(sent), len(HTTP_BODY))
                self.assertEqual(list(self.directory.iterdir()), [self.target])

    def test_http_exhausted_attempts_preserve_existing_file(self):
        for client in ["requests", "httpx"]:
            self.target.write_bytes(b"previous result")
            with self.subTest(client=client), server() as (base, hits, sent):
                with self.assertRaises(Exception):
                    recipes.download_active(base + "/broken", self.target, client=client)
                self.assertEqual(hits, ["/broken", "/broken"])
                self.assertTrue(sent)
            self.assertEqual(self.target.read_bytes(), b"previous result")
            self.assertEqual(list(self.directory.iterdir()), [self.target])

    def test_http_redirect_is_not_followed(self):
        for client in ["requests", "httpx"]:
            self.target.write_bytes(b"previous result")
            with self.subTest(client=client), server() as (base, hits, sent):
                with self.assertRaises(Exception):
                    recipes.download_active(base + "/redirect", self.target, client=client)
                self.assertEqual(hits, ["/redirect"])
                self.assertFalse(sent)
            self.assertEqual(self.target.read_bytes(), b"previous result")


if __name__ == "__main__":
    unittest.main(verbosity=2)
