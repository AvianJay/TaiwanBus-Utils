# My code is shit.
# Require Termux:API
# not done yet.
import time
import json
import youbike
import subprocess

def get_location(provider="gps"):
    ret = subprocess.popen(["termux-location", "-p", provider]).read()
    return json.loads(ret)

def checknear(lat, lon, distance, provider="gps"):
    location = get_location(provider)
    if abs(location["latitude"] - lat) <= distance and abs(location["longitude"] - lon) <= distance:
        return True
    else:
        return False

def checkuntilnear(lat, lon, distance, provider, checktime=180):
    while True:
        if checknear(lat, lon, distance, provider):
            break
        time.sleep(checktime)

def main(args):
    if args.cmd == "location":
        data = youbike.getdatabyid(args.id)
