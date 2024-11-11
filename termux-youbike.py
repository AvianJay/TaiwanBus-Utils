# My code is shit.
# Require Termux:API
# not done yet.
# 針對空位檢測。
import time
import json
import youbike
import subprocess
import argparse
import math

globaldata = {"recentnotify": ""}

def echo(*msg, level="INFO"):
    total = ""
    for m in msg:
        total += f"{m} "
    total = total.strip()
    print(f"[{level}] {total}")

def measure(lat1, lon1, lat2, lon2):
    R = 6378.137  # Radius of earth in KM
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    
    a = math.sin(dLat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    d = R * c
    return d * 1000  # meters

def send_notify(title, msg):
    if not globaldata["recentnotify"] == title + msg:
        os.system(f"termux-notification -t \"{title}\" -i termuxyoubike -c \"{msg}\"")
        globaldata["recentnotify"] = title + msg

def gentext(station):
    available = station['parking_spaces'] - station['available_spaces']
    if available == 0:
        return "已經沒有空位了。"
    elif available <= 3:
        return "空位很少，要賭一把嗎？"
    else:
        return "臥槽你真幸運。"

def get_location(provider="gps"):
    ret = subprocess.Popen(["termux-location", "-p", provider]).read()
    return json.loads(ret)

def checknear(lat, lon, distance, provider="gps"):
    echo("Start checking device's location...")
    location = get_location(provider)
    echo("Got location")
    nd = measure(lat, lon, location["latitude"], location["longitude"])
    echo("Distance:", nd)
    if nd <= distance:
        return True
    else:
        return False

def checkuntilnear(lat, lon, distance, provider="gps", checktime=180):
    while True:
        echo("Start checking...")
        if checknear(lat, lon, distance, provider):
            echo("Reached the specified distance.")
            break
        time.sleep(checktime)

def main(args):
    if args.cmd == "location":
        echo("Getting data...")
        data = youbike.getstationbyid(args.id)
        checkuntilnear(data["lat"], data["lng"], args.distance)
        echo("Getting data...")
        data = youbike.getstationbyid(args.id)
        echo("Sending notify...")
        send_notify(f'[YBP]{data["name_tw"]}', f"你已到達站點附近，剩下 {data['parking_spaces'] - data['available_spaces']} 個空位。{gentext(data)}")

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="YouBikePython for Termux")
    subparsers = parser.add_subparsers(dest="cmd")
    parser_location = subparsers.add_parser("location", help="檢測位置模式")
    parser_time = subparsers.add_parser("time", help="持續發送模式")
    parser_location.add_argument("id", help="站點ID", type=str)
    parser_location.add_argument("-d", "--distance", help="距離（公尺）", type=int, dest="distance", default=500)
    parser_time.add_argument("id", help="站點ID", type=str)
    parser_time.add_argument("-t", "--time", help="發送間隔時間", type=int, dest="time", default=60)
    args = parser.parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        print()
        echo("Stopping!")
        sys.exit(0)
