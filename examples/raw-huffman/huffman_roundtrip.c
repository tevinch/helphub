/* SPDX-License-Identifier: MIT */
/* Original consumer example; uses the installed, unmodified zlib library. */
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <zlib.h>

#define CHUNK_SIZE 16384

static int compression_error(const char *operation, int status) {
    fprintf(stderr, "%s: %s (%d)\n", operation, zError(status), status);
    return 0;
}

static int compress_stream(FILE *input, FILE *packed, uintmax_t *input_bytes,
                           uintmax_t *packed_bytes) {
    unsigned char incoming[CHUNK_SIZE], outgoing[CHUNK_SIZE];
    z_stream stream = {0};
    int status = deflateInit2(&stream, Z_DEFAULT_COMPRESSION, Z_DEFLATED,
                              -MAX_WBITS, 8, Z_HUFFMAN_ONLY);
    if (status != Z_OK)
        return compression_error("deflateInit2", status);

    for (;;) {
        size_t count = fread(incoming, 1, sizeof incoming, input);
        if (ferror(input)) {
            perror("read input");
            deflateEnd(&stream);
            return 0;
        }
        *input_bytes += count;
        stream.next_in = incoming;
        stream.avail_in = (uInt)count;
        int flush = feof(input) ? Z_FINISH : Z_NO_FLUSH;

        do {
            stream.next_out = outgoing;
            stream.avail_out = sizeof outgoing;
            status = deflate(&stream, flush);
            if (status != Z_OK && status != Z_STREAM_END) {
                deflateEnd(&stream);
                return compression_error("deflate", status);
            }
            size_t produced = sizeof outgoing - stream.avail_out;
            if (fwrite(outgoing, 1, produced, packed) != produced) {
                perror("write packed output");
                deflateEnd(&stream);
                return 0;
            }
            *packed_bytes += produced;
            if (status == Z_STREAM_END)
                break;
        } while (stream.avail_in != 0 || stream.avail_out == 0 || flush == Z_FINISH);

        if (status == Z_STREAM_END)
            break;
    }
    status = deflateEnd(&stream);
    return status == Z_OK || compression_error("deflateEnd", status);
}

static int inflate_stream(FILE *packed, FILE *restored, uintmax_t *restored_bytes) {
    unsigned char incoming[CHUNK_SIZE], outgoing[CHUNK_SIZE];
    z_stream stream = {0};
    int status = inflateInit2(&stream, -MAX_WBITS);
    if (status != Z_OK)
        return compression_error("inflateInit2", status);

    for (;;) {
        size_t count = fread(incoming, 1, sizeof incoming, packed);
        if (ferror(packed)) {
            perror("read packed output");
            inflateEnd(&stream);
            return 0;
        }
        if (count == 0) {
            fprintf(stderr, "Packed stream ended before Z_STREAM_END.\n");
            inflateEnd(&stream);
            return 0;
        }
        stream.next_in = incoming;
        stream.avail_in = (uInt)count;
        do {
            stream.next_out = outgoing;
            stream.avail_out = sizeof outgoing;
            status = inflate(&stream, Z_NO_FLUSH);
            if (status != Z_OK && status != Z_STREAM_END) {
                inflateEnd(&stream);
                return compression_error("inflate", status);
            }
            size_t produced = sizeof outgoing - stream.avail_out;
            if (fwrite(outgoing, 1, produced, restored) != produced) {
                perror("write restored output");
                inflateEnd(&stream);
                return 0;
            }
            *restored_bytes += produced;
            if (status == Z_STREAM_END)
                break;
        } while (stream.avail_out == 0);

        if (status == Z_STREAM_END) {
            int trailing = stream.avail_in != 0 || fgetc(packed) != EOF;
            if (trailing || ferror(packed)) {
                fprintf(stderr, "Unexpected bytes or read error after packed stream.\n");
                inflateEnd(&stream);
                return 0;
            }
            break;
        }
    }
    status = inflateEnd(&stream);
    return status == Z_OK || compression_error("inflateEnd", status);
}

static int same_contents(FILE *input, FILE *restored) {
    unsigned char left[CHUNK_SIZE], right[CHUNK_SIZE];
    if (fseek(input, 0, SEEK_SET) != 0 || fseek(restored, 0, SEEK_SET) != 0) {
        perror("rewind for comparison");
        return 0;
    }
    for (;;) {
        size_t left_size = fread(left, 1, sizeof left, input);
        size_t right_size = fread(right, 1, sizeof right, restored);
        if (ferror(input) || ferror(restored)) {
            perror("read for comparison");
            return 0;
        }
        if (left_size != right_size || memcmp(left, right, left_size) != 0) {
            fprintf(stderr, "Restored bytes differ from input.\n");
            return 0;
        }
        if (left_size == 0)
            return 1;
    }
}

int main(int argc, char **argv) {
    FILE *input = NULL, *packed = NULL, *restored = NULL;
    uintmax_t input_bytes = 0, packed_bytes = 0, restored_bytes = 0;
    int created_packed = 0, created_restored = 0, verified = 0;

    if (argc != 4) {
        fprintf(stderr, "Usage: %s INPUT PACKED RESTORED\nOutputs must be new files.\n", argv[0]);
        return 1;
    }
    input = fopen(argv[1], "rb");
    if (input == NULL) {
        perror("open input");
        goto cleanup;
    }
    /* Exclusive creation refuses existing files, including the input path. */
    packed = fopen(argv[2], "w+bx");
    if (packed == NULL) {
        perror("create packed output (must not exist)");
        goto cleanup;
    }
    created_packed = 1;
    restored = fopen(argv[3], "w+bx");
    if (restored == NULL) {
        perror("create restored output (must not exist)");
        goto cleanup;
    }
    created_restored = 1;

    if (!compress_stream(input, packed, &input_bytes, &packed_bytes))
        goto cleanup;
    if (fflush(packed) != 0 || fseek(packed, 0, SEEK_SET) != 0) {
        perror("rewind packed output");
        goto cleanup;
    }
    if (!inflate_stream(packed, restored, &restored_bytes))
        goto cleanup;
    if (fflush(restored) != 0) {
        perror("flush restored output");
        goto cleanup;
    }
    if (!same_contents(input, restored))
        goto cleanup;
    verified = 1;

cleanup:
    if (input != NULL && fclose(input) != 0)
        verified = 0;
    if (packed != NULL && fclose(packed) != 0)
        verified = 0;
    if (restored != NULL && fclose(restored) != 0)
        verified = 0;
    if (!verified) {
        if (created_packed && remove(argv[2]) != 0)
            perror("remove incomplete packed output");
        if (created_restored && remove(argv[3]) != 0)
            perror("remove incomplete restored output");
        return 1;
    }
    printf("zlib headers %s; runtime %s\n", ZLIB_VERSION, zlibVersion());
    printf("Input %" PRIuMAX "; packed %" PRIuMAX "; restored %" PRIuMAX
           " bytes; verified byte for byte.\n", input_bytes, packed_bytes, restored_bytes);
    return 0;
}
