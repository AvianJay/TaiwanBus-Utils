from flask import Flask, request, render_template, redirect, url_for
import taiwanbus
import asyncio
import json
app = Flask(__name__)

@app.route("/")
def index():
    return '''<!DOCTYPE HTML>
<html>
<head>
<meta charset="utf-8>
</head>
<body>
</body>
</html>
'''
    return "Hello from TaiwanBus API!"

@app.route("/search")
def search():
    required_args = ["type", "query", "provider"]
    for arg in required_args:
        if arg not in request.args:
            return "Invaild request."
    supported_types = ["stop", "route"]
    if request.args.get("type") not in supported_types:
        return "Invaild request."
    taiwanbus.update_provider(request.args.get("provider"))
    

@app.route("/getroutestop")
def getroutestop():
    required_args = ["stopid", "routekey", "provider"]
    for arg in required_args:
        if arg not in request.args:
            return "Invaild request."
    taiwanbus.update_provider(request.args.get("provider"))
    stop_info = {}
    route_info = asyncio.run(taiwanbus.fetch_route(int(request.args.get("routekey"))))
    route_info = asyncio.run(taiwanbus.get_complete_bus_info(int(request.args.get("routekey"))))
    for path_id, path_data in route_info.items():
        route_name = path_data["name"]
        stops = path_data["stops"]
        for i, stop in enumerate(stops):
            if stop["stop_id"] == int(request.args.get("stopid")):
                stop_info.update(stop)
                if stop_info["msg"]:
                    stop_info["generated_info"] = f"{stop_name} {msg}\n"
                elif stop_info["sec"] and int(stop_info["sec"]) > 0:
                    minutes = int(stop_info["sec"]) // 60
                    seconds = int(stop_info["sec"]) % 60
                    stop_info["generated_info"] = f"{stop_info["stop_name"]} 還有{minutes}分{seconds}秒"
                else:
                    stop_info["generated_info"] = f"{stop_info["stop_name"]} 進站中"

                if buses:
                    for bus in buses:
                        bus_id = bus["id"]
                        bus_full = "已滿" if bus["full"] == "1" else "未滿"
                        stop_info["generated_info"] += f" [{bus_id} {bus_full}]"
    return json.dumps(stop_info)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5284)