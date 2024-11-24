# My code is shit.
# unzlib.py: tool to uncompress zlib things
# because the response of yahoo api is zlib
import sys
import zlib
import requests
import argparse

def decompress(data):
    return zlib.decompress(data)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Unzlib")
    subparsers = parser.add_subparsers(dest="cmd")
    parser_web = subparsers.add_parser("web", help="get data with web")
    parser_file = subparsers.add_parser("file", help="get data with file")
    parser_web.add_argument("url", help="URL", type=str)
    parser_web.add_argument("-o", "--output", help="output file", type=str, default=None, dest="out")
    parser_file.add_argument("file", help="input filename", type=str)
    parser_file.add_argument("-o", "--output", help="output file", type=str, default=None, dest="out")
    args = parser.parse_args()
    if args.cmd=="web":
        r = requests.get(args.url).content
        dec = decompress(r)
    elif args.cmd=="file":
        d = open(args.file, "r").read()
        dec = decompress(d)
    if args.out:
        open(args.out, "w").write(dec)
        print("Decompressed data saved to", args.out)
    else:
        print(dec)