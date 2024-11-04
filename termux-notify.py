# My code is shit.
# Bus notification for Termux.
# Termux:API is required.
import os
import sys
import time
import taiwanbus as twbus
import asyncio
import argparse

globaldata = {"route": "", "stop": "", "path": "", "sec": 0, "usersec": 0, "msg": "", "bus": [], "recentnotify": "", "realtime": False}


def echo(*msg, level="INFO"):
    total = ""
    for m in msg:
        total += f"{m} "
    total = total.strip()
    print(f"[{level}] {total}")


async def gettime(stopid):
    st = await twbus.fetch_stop(stopid)
    rn = await twbus.fetch_route(st[0]["route_key"])
    stop_info = {"route": rn[0]["route_name"], "stop": "", "sec": 0, "bus": {}, "msg": ""}
    route_info = await twbus.get_complete_bus_info(st[0]["route_key"])
    for path_id, path_data in route_info.items():
        route_name = path_data["name"]
        stops = path_data["stops"]
        for i, stop in enumerate(stops):
            if stop["stop_id"] == stopid:
                stop_info["stop"] = stop["stop_name"].strip()
                stop_info["msg"] = stop["msg"]
                stop_info["sec"] = stop["sec"]
                stop_info["bus"] = stop["bus"]
    return stop_info

async def gettimeformat(route, stopid):
    stop_info = ""
    route_info = await twbus.get_complete_bus_info(route)
    for path_id, path_data in route_info.items():
        route_name = path_data["name"]
        stops = path_data["stops"]
        for i, stop in enumerate(stops):
            if stop["stop_id"] == stopid:
                stop_name = stop["stop_name"].strip()
                msg = stop["msg"]
                sec = stop["sec"]
                buses = stop["bus"]
                
                if msg:
                    stop_info = f"{stop_name} {msg}\n"
                elif sec and int(sec) > 0:
                    minutes = int(sec) // 60
                    seconds = int(sec) % 60
                    stop_info = f"{stop_name} 還有{minutes}分{seconds}秒"
                else:
                    stop_info = f"{stop_name} 進站中"

                if buses:
                    for bus in buses:
                        bus_id = bus["id"]
                        bus_full = "已滿" if bus["full"] == "1" else "未滿"
                        stop_info += f" [{bus_id} {bus_full}]"
    return stop_info

def send_notify(title, msg):
    if not globaldata["recentnotify"] == title + msg:
        os.system(f"termux-notification -t \"{title}\" -i termuxtwbus -c \"{msg}\"")
        globaldata["recentnotify"] = title + msg

async def realtime_notify():
    while True:
        if globaldata["usersec"] >= globaldata["sec"]:
            stop_info = ""
            if globaldata["msg"]:
                stop_info = f"{globaldata['stop']} {globaldata['msg']}\n"
            elif globaldata["sec"] and globaldata["sec"] > 0:
                minutes = globaldata["sec"] // 60
                seconds = globaldata["sec"] % 60
                stop_info = f"{globaldata['stop']} 還有{minutes}分{seconds}秒"
            else:
                stop_info = f"{globaldata['stop']} 進站中"

            if globaldata["bus"]:
                for bus in globaldata["bus"]:
                    bus_id = bus["id"]
                    bus_full = "已滿" if bus["full"] == "1" else "未滿"
                    stop_info += f" [{bus_id} {bus_full}]"
            send_notify(f"{globaldata['route']}[{globaldata['path']}]", stop_info)
        # I know this will not work when time is set to bigger than 999999999.
        # because I'm too lazy lol
        # but i think no one will break?
        if globaldata["sec"] < 0:
            globaldata["sec"] = 999999999
        if not globaldata["realtime"]:
            globaldata["sec"] = 999999999
        await asyncio.sleep(.6)

async def realtime_counter():
    while True:
        globaldata["sec"] -= 1
        await asyncio.sleep(1)

async def main(args):
    if args.cmd == "keep":
        stop = await twbus.fetch_stop(stopid)
        routeid = stop[0]["route_key"]
        route = await twbus.fetch_route(routeid)
        while True:
            try:
                msg = await gettimeformat(routeid, args.stopid)
                echo("Got data", msg)
                send_notify(route[0]["route_name"], msg)
            except Exception as e:
                echo("無法更新公車資訊。你可能未連接至網際網路。", e, level="WARN")
            await asyncio.sleep(args.waittime)
    elif args.cmd == "time":
        path = await twbus.fetch_path_by_stop(args.stopid)
        globaldata["path"] = path[0]["path_name"]
        asyncio.create_task(realtime_notify())
        asyncio.create_task(realtime_counter())
        globaldata["usersec"] = args.intimenotify
        globaldata["sec"] = 999999
        globaldata["realtime"] = args.realtime
        while True:
            try:
                data = await gettime(args.stopid)
                echo("Got data", data["sec"])
                globaldata.update(data)
            except Exception as e:
                echo("無法更新公車資訊。你可能未連接至網際網路。", e, level="WARN")
            await asyncio.sleep(args.checktime)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="TaiwanBus for Termux")
    subparsers = parser.add_subparsers(dest="cmd")
    parser_keep = subparsers.add_parser("keep", help="持續發送模式")
    parser_time = subparsers.add_parser("time", help="在快到站的時候發送")
    parser_keep.add_argument("stopid", help="車站ID", type=int)
    parser_keep.add_argument("-t", "--time", help="發送間隔時間", type=int, dest="waittime", default=60)
    parser_time.add_argument("stopid", help="車站ID", type=int)
    parser_time.add_argument("-t", "--time", help="當公車在幾秒內到站提醒", type=int, dest="intimenotify", default=300)
    parser_time.add_argument("-c", "--checktime", help="檢查間隔時間", type=int, dest="checktime", default=60)
    parser_time.add_argument("-r", "--realtime", help="即時發送訊息", dest="realtime", action='store_true', default=False)
    args = parser.parse_args()
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("Stopping!")
        sys.exit(0)
