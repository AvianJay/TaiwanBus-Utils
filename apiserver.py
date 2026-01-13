from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import taiwanbus
import youbike
import asyncio
import json
import os
import time
import threading
import math

app = FastAPI()

default_config = {
    "host": "0.0.0.0",
    "port": 5284,
    "ssl": False,
    "sslcert": "fullchain.pem",
    "sslkey": "privkey.pem",
    "auto_update_database": True,
    "auto_update_database_cooldown": 1440,
    "database_dir": False # False: use default | (str): dir name
}
cfgupdated = False

if os.path.exists("config.apiserver.json"):
    config = json.load(open("config.apiserver.json", "r"))
    for k in default_config.keys():
        if k not in config.keys():
            config[k] = default_config[k]
            cfgupdated = True
    if cfgupdated:
        json.dump(config, open("config.apiserver.json", "w"), ensure_ascii=False, indent=4)
        print("INFO: 已經更新了config.apiserver.json，請檢查！")
else:
    print("INFO: First start!")
    config = default_config
    json.dump(config, open("config.apiserver.json", "w"), ensure_ascii=False, indent=4)
    print("INFO: 已經更新了config.apiserver.json，請檢查！")

def auto_update_database():
    while True:
        print("INFO: Start updating TaiwanBus database...")
        try:
            taiwanbus.update_database(info=True)
            print("INFO: Update done.")
            time.sleep(config["auto_update_database_cooldown"] * 60)
        except Exception as e:
            print(f"ERROR: {e}")

# Haversine distance calculation in meters
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in meters."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# Pydantic response model for nearest bus endpoints
class NearestBusResponse(BaseModel):
    bus_lat: float = Field(..., description="Current latitude of the nearest bus")
    bus_lon: float = Field(..., description="Current longitude of the nearest bus")
    distance_meters: float = Field(..., description="Distance between the reference point and the bus in meters")
    eta_seconds: Optional[int] = Field(None, description="Estimated time of arrival in seconds (if available)")


@app.get("/", response_class=HTMLResponse)
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

    <a href="youbike">YouBikePython API</a>
    
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


@app.get("/search")
def search(
    type: str = Query(..., description="Search type: 'stop' or 'route'"),
    query: str = Query(..., description="Search query string"),
    provider: str = Query(..., description="Provider: 'tcc', 'tpe', or 'twn'")
):
    supported_types = ["stop", "route"]

    if type not in supported_types:
        raise HTTPException(status_code=400, detail=f"Unsupported type '{type}'. Supported types: {supported_types}")
    
    taiwanbus.update_provider(provider)
    
    try:
        if type == "stop":
            if provider == "twn":
                raise HTTPException(status_code=400, detail="Provider 'twn' does not support stop searches.")
            stops = asyncio.run(taiwanbus.fetch_stops_by_name(query))
            return stops
        
        elif type == "route":
            routes = asyncio.run(taiwanbus.fetch_routes_by_name(query))
            return routes
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/getroutestop")
def getroutestop(
    stopid: int = Query(..., description="Stop ID"),
    routekey: int = Query(..., description="Route key"),
    provider: str = Query(..., description="Provider: 'tcc', 'tpe', or 'twn'")
):
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
        
        return stop_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nearest_bus_by_coord", response_model=NearestBusResponse)
def nearest_bus_by_coord(
    lat: float = Query(..., ge=-90, le=90, description="Latitude of the reference point"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude of the reference point"),
    route_id: int = Query(..., description="Route ID (route_key) to filter buses"),
    provider: str = Query("tcc", description="Provider: 'tcc', 'tpe', or 'twn'")
):
    """
    Find the nearest bus to the given coordinates.
    Requires route_id to specify which route to search for buses.
    Returns the nearest bus position, distance, and ETA if available.
    """
    taiwanbus.update_provider(provider)
    
    try:
        buses_data = taiwanbus.getbus(route_id)
        
        if not buses_data:
            raise HTTPException(status_code=404, detail="No bus data available for the specified route")
        
        nearest_bus = None
        min_distance = float('inf')
        nearest_eta = None
        
        # Iterate through all stops and their associated buses
        for stop_data in buses_data:
            if "bus" in stop_data and stop_data["bus"]:
                # Get stop coordinates
                stop_lat = float(stop_data.get("lat", 0))
                stop_lon = float(stop_data.get("lon", 0))
                
                # Get ETA info for this stop
                eta_seconds = None
                if stop_data.get("sec"):
                    try:
                        eta_seconds = int(stop_data["sec"])
                    except (ValueError, TypeError):
                        eta_seconds = None
                
                # Check each bus at this stop
                for bus in stop_data["bus"]:
                    # Use stop coordinates as bus position (API provides stop-based position)
                    bus_lat = stop_lat
                    bus_lon = stop_lon
                    
                    if bus_lat == 0 and bus_lon == 0:
                        continue
                    
                    distance = haversine_distance(lat, lon, bus_lat, bus_lon)
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest_bus = {"lat": bus_lat, "lon": bus_lon}
                        nearest_eta = eta_seconds
        
        if nearest_bus is None:
            raise HTTPException(status_code=404, detail="No buses found matching the specified criteria")
        
        return NearestBusResponse(
            bus_lat=nearest_bus["lat"],
            bus_lon=nearest_bus["lon"],
            distance_meters=round(min_distance, 2),
            eta_seconds=nearest_eta if nearest_eta and nearest_eta > 0 else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nearest_bus_by_stop", response_model=NearestBusResponse)
def nearest_bus_by_stop(
    stop_id: int = Query(..., description="Stop ID to find nearest bus to"),
    route_id: Optional[int] = Query(None, description="Route ID (route_key) to filter buses"),
    provider: str = Query("tcc", description="Provider: 'tcc', 'tpe', or 'twn'")
):
    """
    Find the nearest bus to a specific stop.
    Uses the stop's coordinates to calculate distance to available buses.
    Returns the nearest bus position, distance, and ETA if available.
    """
    taiwanbus.update_provider(provider)
    
    try:
        # Get stop information to get coordinates
        stop_info = asyncio.run(taiwanbus.fetch_stop(stop_id))
        
        if not stop_info:
            raise HTTPException(status_code=404, detail=f"Stop with ID {stop_id} not found")
        
        stop = stop_info[0]
        stop_lat = float(stop.get("lat", 0))
        stop_lon = float(stop.get("lon", 0))
        
        if stop_lat == 0 and stop_lon == 0:
            raise HTTPException(status_code=400, detail="Stop coordinates not available")
        
        # Use route_id if provided, otherwise use the route_key from the stop
        target_route_id = route_id if route_id is not None else stop.get("route_key")
        
        if target_route_id is None:
            raise HTTPException(status_code=400, detail="No route information available for this stop")
        
        buses_data = taiwanbus.getbus(target_route_id)
        
        if not buses_data:
            raise HTTPException(status_code=404, detail="No bus data available for the specified route")
        
        nearest_bus = None
        min_distance = float('inf')
        nearest_eta = None
        
        # Iterate through all stops and their associated buses
        for bus_stop_data in buses_data:
            if "bus" in bus_stop_data and bus_stop_data["bus"]:
                # Get bus stop coordinates
                bus_stop_lat = float(bus_stop_data.get("lat", 0))
                bus_stop_lon = float(bus_stop_data.get("lon", 0))
                
                # Check if this is the target stop for ETA
                eta_seconds = None
                if str(bus_stop_data.get("id")) == str(stop_id):
                    if bus_stop_data.get("sec"):
                        try:
                            eta_seconds = int(bus_stop_data["sec"])
                        except (ValueError, TypeError):
                            eta_seconds = None
                
                # Check each bus at this stop
                for bus in bus_stop_data["bus"]:
                    bus_lat = bus_stop_lat
                    bus_lon = bus_stop_lon
                    
                    if bus_lat == 0 and bus_lon == 0:
                        continue
                    
                    distance = haversine_distance(stop_lat, stop_lon, bus_lat, bus_lon)
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest_bus = {"lat": bus_lat, "lon": bus_lon}
                        # Only use ETA if this bus is at the target stop
                        if str(bus_stop_data.get("id")) == str(stop_id):
                            nearest_eta = eta_seconds
        
        if nearest_bus is None:
            raise HTTPException(status_code=404, detail="No buses found on the route")
        
        return NearestBusResponse(
            bus_lat=nearest_bus["lat"],
            bus_lon=nearest_bus["lon"],
            distance_meters=round(min_distance, 2),
            eta_seconds=nearest_eta if nearest_eta and nearest_eta > 0 else None
        )
    except HTTPException:
        raise
    except taiwanbus.exceptions.UnsupportedDatabaseError:
        raise HTTPException(status_code=400, detail="Provider does not support stop queries")
    except taiwanbus.exceptions.DatabaseNotFoundError:
        raise HTTPException(status_code=500, detail="Database not found. Please update the database first.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/youbike", response_class=HTMLResponse)
def ybindex():
    return '''
<!DOCTYPE HTML>
<html>
<head>
    <meta charset="utf-8">
    <title>YouBikePython API</title>
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
            const keyword = document.getElementById("query").value;

            fetchData(window.location.href + "/search", { keyword });
        }

        function handleStation() {
            const id = document.getElementById("id").value;

            fetchData(window.location.href + "/id", { id });
        }

        function handleLocation() {
            const lat = document.getElementById("lat").value;
            const lon = document.getElementById("lon").value;
            const distance = document.getElementById("distance").value;

            fetchData(window.location.href + "/location", { lat, lon, distance });
        }
    </script>
</head>
<body>
    <h1>YouBikePython API GUI</h1>
    
    <h2>搜尋</h2>
    <label>關鍵字:</label>
    <input id="query" type="text">
    <button onclick="handleSearch()">搜尋</button>

    <h2>取得站點資訊</h2>
    <label>站點ID:</label>
    <input id="id" type="text">
    <button onclick="handleStation()">獲取</button>

    <h2>取得附近站點</h2>
    <label>經度:</label>
    <input id="lat" type="text">
    <label>緯度:</label>
    <input id="lon" type="text">
    <label>距離(公尺):</label>
    <input id="distance" type="text">
    <button onclick="handleLocation()">獲取</button>

    <h2>結果</h2>
    <div id="result">
        <p>還沒有取得資料。</p>
    </div>
</body>
</html>
'''


@app.get("/youbike/search")
def ybsearch(keyword: str = Query(..., description="Search keyword")):
    return youbike.getstationbyname(keyword)


@app.get("/youbike/location")
def yblocation(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    distance: float = Query(0, description="Distance in meters")
):
    return youbike.getstationbylocation(lat, lon, distance)

@app.get("/youbike/id")
def ybid(id: str = Query(..., description="Station ID")):
    return youbike.getstationbyid(id)


@app.get("/youbike/all")
def yball():
    return youbike.getallstations()

@app.get("/youbike/original/json/station-yb2.json")
def yboriginaljson():
    return youbike.getallstations()

@app.get("/youbike/original/json/station-min-yb2.json")
def yboriginalminjson():
    return youbike.getallstations(parkinginfo=False)

@app.get("/youbike/original/json/area-all.json")
def yboriginalareajson():
    return youbike.getallareas()

if __name__ == '__main__':
    import uvicorn
    if config["database_dir"]:
        if os.path.isfile(config["database_dir"]):
            print("ERROR: Database dir is a file! Using Default dir.")
        else:
            if not os.path.isdir(config["database_dir"]):
                os.mkdir(config["database_dir"])
            taiwanbus.home = config["database_dir"]
    if config["auto_update_database"]:
        print("INFO: Starting auto update database thread.")
        update_db_thread = threading.Thread(target=auto_update_database)
        update_db_thread.daemon = True
        update_db_thread.start()
    else:
        print("INFO: Disabled auto update database. Update on start.")
        taiwanbus.update_database()
        print("INFO: Update done.")
    if config["ssl"]:
        uvicorn.run(app, host=config["host"], port=config["port"], ssl_certfile=config["sslcert"], ssl_keyfile=config["sslkey"])
    else:
        uvicorn.run(app, host=config["host"], port=config["port"])
