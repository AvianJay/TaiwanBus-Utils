from flask import Flask, request, render_template, redirect, url_for, jsonify
import taiwanbus
import asyncio
import json
import os
app = Flask(__name__)

default_config = {
    "host": "0.0.0.0",
    "port": 5284,
    "ssl": False,
    "sslcert": "fullchain.pem",
    "sslkey": "privkey.pem"
}
cfgupdated = False

if os.path.exists("config.apiserver.json"):
    config = json.load(open("config.apiserver.json", "r"))
    for k in default_config.keys():
        if k not in config.keys():
            config[k] = default_config[k]
            cfgupdated = True
    if cfgupdated:
        json.dump(config, open("config.apiserver.json", "w"))
        print("已經更新了config.apiserver.json，請檢查！")
else:
    config = default_config
    json.dump(config, open("config.apiserver.json", "w"))
    print("已經更新了config.apiserver.json，請檢查！")

@app.route("/")
def index():
    return '''
<!DOCTYPE HTML>
<html>
<head>
    <meta charset="utf-8">
    <title>TaiwanBus API</title>
    <script>
        async function fetchData(apiUrl, params) {
            const url = new URL(apiUrl);
            Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));

            try {
                const response = await fetch(url);
                const data = await response.json();
                renderResult(data);
            } catch (error) {
                console.error("Error fetching data:", error);
                document.getElementById("result").innerHTML = "<p>取得資料錯誤</p>";
            }
        }

        function renderResult(data) {
            const resultDiv = document.getElementById("result");
            resultDiv.innerHTML = "";  // Clear previous result
            
            if (Array.isArray(data)) {
                // If it's an array, render as a table
                const table = document.createElement("table");
                table.border = "1";
                const headerRow = document.createElement("tr");

                // Extract headers from first object keys
                Object.keys(data[0]).forEach(key => {
                    const th = document.createElement("th");
                    th.innerText = key;
                    headerRow.appendChild(th);
                });
                table.appendChild(headerRow);

                // Render rows
                data.forEach(item => {
                    const row = document.createElement("tr");
                    Object.values(item).forEach(value => {
                        const td = document.createElement("td");
                        td.innerText = value;
                        row.appendChild(td);
                    });
                    table.appendChild(row);
                });
                resultDiv.appendChild(table);
            } else if (typeof data === "object") {
                // If it's an object, render as a list
                const ul = document.createElement("ul");
                for (const [key, value] of Object.entries(data)) {
                    const li = document.createElement("li");
                    li.innerText = `${key}: ${value}`;
                    ul.appendChild(li);
                }
                resultDiv.appendChild(ul);
            } else {
                // Fallback for other data types
                resultDiv.innerText = JSON.stringify(data, null, 2);
            }
        }

        function handleSearch() {
            const type = document.getElementById("type").value;
            const query = document.getElementById("query").value;
            const provider = document.getElementById("provider").value;

            fetchData(window.location.href + "search", { type, query, provider });
        }

        function handleRouteStop() {
            const stopid = document.getElementById("stopid").value;
            const routekey = document.getElementById("routekey").value;
            const provider = document.getElementById("provider").value;

            fetchData(window.location.href + "getroutestop", { stopid, routekey, provider });
        }
    </script>
</head>
<body>
    <h1>TaiwanBus API GUI</h1>
    
    <h2>搜尋</h2>
    <label>Type:</label>
    <select id="type">
        <option value="stop">Stop</option>
        <option value="route">Route</option>
    </select>
    <label>關鍵字:</label>
    <input id="query" type="text">
    <label>區域:</label>
    <input id="provider" type="text" value="tcc">
    <button onclick="handleSearch()">搜尋</button>

    <h2>取得路線中站點資訊</h2>
    <label>站點ID:</label>
    <input id="stopid" type="text">
    <label>路線ID:</label>
    <input id="routekey" type="text">
    <label>區域:</label>
    <input id="provider" type="text" value="tcc">
    <button onclick="handleRouteStop()">獲取</button>

    <h2>結果</h2>
    <div id="result">
        <p>還沒有取得資料。</p>
    </div>
</body>
</html>
'''


@app.route("/search")
def search():
    # Check required parameters
    required_args = ["type", "query", "provider"]
    for arg in required_args:
        if arg not in request.args:
            return jsonify({"error": "Invalid request. Missing required parameters."}), 400
    
    search_type = request.args.get("type")
    query = request.args.get("query")
    provider = request.args.get("provider")
    supported_types = ["stop", "route"]

    if search_type not in supported_types:
        return jsonify({"error": f"Unsupported type '{search_type}'. Supported types: {supported_types}"}), 400
    
    taiwanbus.update_provider(provider)
    
    try:
        if search_type == "stop":
            if provider == "twn":
                return jsonify({"error": "Provider 'twn' does not support stop searches."}), 400
            stops = asyncio.run(taiwanbus.fetch_stops_by_name(query))
            return jsonify(stops)
        
        elif search_type == "route":
            routes = asyncio.run(taiwanbus.fetch_routes_by_name(query))
            return jsonify(routes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/getroutestop")
def getroutestop():
    required_args = ["stopid", "routekey", "provider"]
    for arg in required_args:
        if arg not in request.args:
            return jsonify({"error": "Invalid request. Missing required parameters."}), 400

    stopid = int(request.args.get("stopid"))
    routekey = int(request.args.get("routekey"))
    provider = request.args.get("provider")

    taiwanbus.update_provider(provider)
    
    try:
        route = asyncio.run(taiwanbus.fetch_route(routekey))[0]
        route_info = asyncio.run(taiwanbus.get_complete_bus_info(routekey))
        stop_info = {}

        for path_id, path_data in route_info.items():
            for stop in path_data["stops"]:
                if stop["stop_id"] == stopid:
                    stop_info.update(stop)
                    stop_info["route_name"] = route["route_name"]
                    
                    if stop_info.get("msg"):
                        stop_info["generated_info"] = f"{route['route_name']} - {stop_info['stop_name']} {stop_info['msg']}"
                    elif stop_info.get("sec") and int(stop_info["sec"]) > 0:
                        minutes = int(stop_info["sec"]) // 60
                        seconds = int(stop_info["sec"]) % 60
                        stop_info["generated_info"] = f"{route['route_name']} - {stop_info['stop_name']} 還有 {minutes} 分 {seconds} 秒"
                    else:
                        stop_info["generated_info"] = f"{route['route_name']} - {stop_info['stop_name']} 進站中"
                    
                    if stop_info.get("bus"):
                        for bus in stop_info["bus"]:
                            bus_id = bus["id"]
                            bus_full = "已滿" if bus["full"] == "1" else "未滿"
                            stop_info["generated_info"] += f" [{bus_id} {bus_full}]"
        
        return jsonify(stop_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    if config["ssl"]:
        app.run(host=config["host"], port=config["port"], ssl_context=(config["sslcert"], config["sslkey"]))
    else:
        app.run(host=config["host"], port=config["port"])
