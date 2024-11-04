# My code is shit.
# unzlib.py: tool to uncompress zlib things
# because the response of yahoo api is zlib
import sys
import zlib

def decompress(filename, output):
    open(output, "wb").write(zlib.decompress(open(filename, "rb").read()))

if __name__ == "__main__":
    if not len(sys.argv) == 3:
        print("Usage:", sys.argv[0], "[Input filename] [Output filename]")
        sys.exit(1)
    print("Decompressing", sys.argv[0])
    decompress(sys.argv[1], sys.argv[2])
    print("Decompressed file saved to", sys.argv[2])