# TaiwanBus API Documentation

本文件描述了 `apiserver.py` 提供的 RESTful API 端點。這些 API 主要分為 **TaiwanBus API** (公車資訊) 與 **YouBike API** (YouBike 資訊) 兩大類。

所有請求預設為 `GET` 方法。

---

## 🚌 TaiwanBus API

### 1. 搜尋站點或路線 (`/search`)

搜尋公車路線或站點資訊。

*   **URL:** `/search`
*   **Method:** `GET`
*   **參數 (Query Parameters):**

| 參數名 | 必填 | 說明 | 範例 |
| :--- | :--- | :--- | :--- |
| `type` | 是 | 搜尋類型，支援 `stop` (站點) 或 `route` (路線) | `route` |
| `query` | 是 | 搜尋關鍵字 | `307` |
| `provider` | 是 | 服務提供者代號 (例如: `tcc`, `twn` 等) | `tcc` |

*   **備註:** `provider='twn'` 不支援 `stop` 搜尋。

### 2. 取得路線中站點資訊 (`/getroutestop`)

查詢特定路線上某個站點的詳細即時資訊 (包含到站時間等)。

*   **URL:** `/getroutestop`
*   **Method:** `GET`
*   **參數 (Query Parameters):**

| 參數名 | 必填 | 說明 | 範例 |
| :--- | :--- | :--- | :--- |
| `stopid` | 是 | 站點 ID | `12345` |
| `routekey` | 是 | 路線 ID (Route Key) | `67890` |
| `provider` | 是 | 服務提供者代號 | `tcc` |

*   **回傳:** JSON 物件，包含該站點在該路線上的詳細資訊，以及由後端產生的 `generated_info` (例如："307 - 板橋公車站 還有 3 分 20 秒")。

### 3. 根據座標取得附近站點 (`/getstopsbypos`)

根據經緯度搜尋附近的公車站點。

*   **URL:** `/getstopsbypos`
*   **Method:** `GET`
*   **參數 (Query Parameters):**

| 參數名 | 必填 | 說明 | 預設值 | 範例 |
| :--- | :--- | :--- | :--- | :--- |
| `lat` | 是 | 緯度 | - | `25.033` |
| `lon` | 是 | 經度 | - | `121.565` |
| `provider` | 是 | 服務提供者代號 | - | `tcc` |
| `distance` | 否 | 搜尋半徑 (公尺)，最大 1000 | `100` | `500` |
| `routekey` | 否 | 若提供，則只篩選特定路線的站點 | - | `67890` |

*   **備註:** 不支援 `provider='twn'`。

### 4. 取得經過站點資訊 (`/getstopspassby`)

查詢指定站點 ID 附近的站點 (通常用於查詢轉乘資訊或同一站牌的其他路線)。

*   **URL:** `/getstopspassby`
*   **Method:** `GET`
*   **參數 (Query Parameters):**

| 參數名 | 必填 | 說明 | 預設值 | 範例 |
| :--- | :--- | :--- | :--- | :--- |
| `stopid` | 是 | 基準站點 ID | - | `12345` |
| `provider` | 是 | 服務提供者代號 | - | `tcc` |
| `radius` | 否 | 搜尋半徑 (公尺)，最大 1000 | `100` | `200` |

*   **備註:** 不支援 `provider='twn'`。

---

## 🚲 YouBike API

### 1. 搜尋 YouBike 站點 (`/youbike/search`)

*   **URL:** `/youbike/search`
*   **Method:** `GET`
*   **參數 (Query Parameters):**

| 參數名 | 必填 | 說明 | 範例 |
| :--- | :--- | :--- | :--- |
| `keyword` | 是 | 搜尋關鍵字 (站名) | `捷運` |

### 2. 根據座標取得 YouBike 站點 (`/youbike/location`)

*   **URL:** `/youbike/location`
*   **Method:** `GET`
*   **參數 (Query Parameters):**

| 參數名 | 必填 | 說明 | 範例 |
| :--- | :--- | :--- | :--- |
| `lat` | 是 | 緯度 | `25.033` |
| `lon` | 是 | 經度 | `121.565` |
| `distance` | 否 | 距離參數 | `500` |

### 3. 根據 ID 取得 YouBike 站點 (`/youbike/id`)

*   **URL:** `/youbike/id`
*   **Method:** `GET`
*   **參數 (Query Parameters):**

| 參數名 | 必填 | 說明 | 範例 |
| :--- | :--- | :--- | :--- |
| `id` | 是 | 站點 ID | `500101001` |

### 4. 取得所有 YouBike 站點 (`/youbike/all`)

*   **URL:** `/youbike/all`
*   **Method:** `GET`
*   **說明:** 回傳所有快取的 YouBike 站點資訊。

### 5. 原始資料相容端點 (Original Data Endpoints)

為了相容性或特定資料格式需求，提供以下路由：

*   `/youbike/original/json/station-yb2.json`: 取得所有站點 (完整資訊)。
*   `/youbike/original/json/station-min-yb2.json`: 取得所有站點 (精簡版，不含停車資訊 `parkinginfo=False`)。
*   `/youbike/original/json/area-all.json`: 取得所有區域資訊。

---

## 🖥️ GUI 介面

伺服器亦提供簡單的 HTML 測試介面：

*   `/`: TaiwanBus API 測試首頁。
*   `/youbike`: YouBike API 測試首頁。
