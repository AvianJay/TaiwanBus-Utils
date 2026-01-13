"""
Tests for the nearest bus endpoints in the TaiwanBus API.
Uses pytest and FastAPI TestClient.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from apiserver import app, haversine_distance

client = TestClient(app)


# Mock data for testing
MOCK_BUS_DATA = [
    {
        "id": "12345",
        "lat": "24.1234",
        "lon": "120.6789",
        "sec": "120",
        "msg": "",
        "t": "1",
        "bus": [
            {"id": "ABC-123", "full": "0"}
        ]
    },
    {
        "id": "12346",
        "lat": "24.1300",
        "lon": "120.6800",
        "sec": "300",
        "msg": "",
        "t": "1",
        "bus": [
            {"id": "DEF-456", "full": "1"}
        ]
    }
]

MOCK_STOP_INFO = [
    {
        "stop_id": 12345,
        "stop_name": "Test Stop",
        "lat": 24.1234,
        "lon": 120.6789,
        "route_key": 100,
        "path_id": 1,
        "sequence": 1
    }
]

MOCK_EMPTY_BUS_DATA = []


class TestHaversineDistance:
    """Tests for the Haversine distance calculation function."""
    
    def test_same_point_returns_zero(self):
        """Distance between same point should be 0."""
        distance = haversine_distance(24.0, 120.0, 24.0, 120.0)
        assert distance == 0.0
    
    def test_known_distance(self):
        """Test with known coordinates and expected approximate distance."""
        # Distance between two points roughly 1km apart
        lat1, lon1 = 24.0, 120.0
        lat2, lon2 = 24.009, 120.0  # ~1km north
        distance = haversine_distance(lat1, lon1, lat2, lon2)
        assert 900 < distance < 1100  # Should be approximately 1000 meters
    
    def test_distance_is_non_negative(self):
        """Distance should always be non-negative."""
        distance = haversine_distance(24.0, 120.0, -24.0, -120.0)
        assert distance >= 0


class TestNearestBusByCoord:
    """Tests for the /nearest_bus_by_coord endpoint."""
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.update_provider')
    def test_happy_path_with_valid_coordinates(self, mock_update_provider, mock_getbus):
        """Test successful response with valid coordinates and route_id."""
        mock_getbus.return_value = MOCK_BUS_DATA
        
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 24.1234, "lon": 120.6789, "route_id": 100, "provider": "tcc"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "bus_lat" in data
        assert "bus_lon" in data
        assert "distance_meters" in data
        assert isinstance(data["bus_lat"], float)
        assert isinstance(data["bus_lon"], float)
        assert isinstance(data["distance_meters"], float)
        assert data["distance_meters"] >= 0
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.update_provider')
    def test_response_includes_eta_when_available(self, mock_update_provider, mock_getbus):
        """Test that eta_seconds is included when available in the data."""
        mock_getbus.return_value = MOCK_BUS_DATA
        
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 24.1234, "lon": 120.6789, "route_id": 100, "provider": "tcc"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # eta_seconds may be present or None
        assert "eta_seconds" in data
    
    def test_invalid_latitude_too_high(self):
        """Test validation error for latitude > 90."""
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 123, "lon": 120.0, "route_id": 100}
        )
        
        assert response.status_code == 422
    
    def test_invalid_latitude_too_low(self):
        """Test validation error for latitude < -90."""
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": -100, "lon": 120.0, "route_id": 100}
        )
        
        assert response.status_code == 422
    
    def test_invalid_longitude_too_high(self):
        """Test validation error for longitude > 180."""
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 24.0, "lon": 200, "route_id": 100}
        )
        
        assert response.status_code == 422
    
    def test_invalid_longitude_too_low(self):
        """Test validation error for longitude < -180."""
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 24.0, "lon": -200, "route_id": 100}
        )
        
        assert response.status_code == 422
    
    def test_missing_latitude_parameter(self):
        """Test error when latitude is missing."""
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lon": 120.0, "route_id": 100}
        )
        
        assert response.status_code == 422
    
    def test_missing_longitude_parameter(self):
        """Test error when longitude is missing."""
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 24.0, "route_id": 100}
        )
        
        assert response.status_code == 422
    
    def test_missing_route_id_parameter(self):
        """Test error when route_id is missing."""
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 24.0, "lon": 120.0}
        )
        
        assert response.status_code == 422
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.update_provider')
    def test_no_buses_available(self, mock_update_provider, mock_getbus):
        """Test 404 response when no buses are available."""
        mock_getbus.return_value = MOCK_EMPTY_BUS_DATA
        
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 24.0, "lon": 120.0, "route_id": 100}
        )
        
        assert response.status_code == 404
        assert "detail" in response.json()
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.update_provider')
    def test_no_buses_with_positions(self, mock_update_provider, mock_getbus):
        """Test 404 when buses exist but have no valid positions."""
        mock_getbus.return_value = [
            {
                "id": "12345",
                "lat": "0",
                "lon": "0",
                "sec": "120",
                "msg": "",
                "bus": [{"id": "ABC-123", "full": "0"}]
            }
        ]
        
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 24.0, "lon": 120.0, "route_id": 100}
        )
        
        assert response.status_code == 404


class TestNearestBusByStop:
    """Tests for the /nearest_bus_by_stop endpoint."""
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.fetch_stop')
    @patch('taiwanbus.update_provider')
    def test_happy_path_with_valid_stop_id(self, mock_update_provider, mock_fetch_stop, mock_getbus):
        """Test successful response with valid stop_id."""
        mock_fetch_stop.return_value = MOCK_STOP_INFO
        mock_getbus.return_value = MOCK_BUS_DATA
        
        response = client.get(
            "/nearest_bus_by_stop",
            params={"stop_id": 12345, "provider": "tcc"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "bus_lat" in data
        assert "bus_lon" in data
        assert "distance_meters" in data
        assert isinstance(data["bus_lat"], float)
        assert isinstance(data["bus_lon"], float)
        assert isinstance(data["distance_meters"], float)
        assert data["distance_meters"] >= 0
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.fetch_stop')
    @patch('taiwanbus.update_provider')
    def test_with_route_id_filter(self, mock_update_provider, mock_fetch_stop, mock_getbus):
        """Test with optional route_id filter."""
        mock_fetch_stop.return_value = MOCK_STOP_INFO
        mock_getbus.return_value = MOCK_BUS_DATA
        
        response = client.get(
            "/nearest_bus_by_stop",
            params={"stop_id": 12345, "route_id": 100, "provider": "tcc"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "bus_lat" in data
        assert "bus_lon" in data
        assert "distance_meters" in data
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.fetch_stop')
    @patch('taiwanbus.update_provider')
    def test_response_includes_eta_when_available(self, mock_update_provider, mock_fetch_stop, mock_getbus):
        """Test that eta_seconds is included when available."""
        mock_fetch_stop.return_value = MOCK_STOP_INFO
        mock_getbus.return_value = MOCK_BUS_DATA
        
        response = client.get(
            "/nearest_bus_by_stop",
            params={"stop_id": 12345, "provider": "tcc"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "eta_seconds" in data
    
    def test_missing_stop_id_parameter(self):
        """Test error when stop_id is missing."""
        response = client.get(
            "/nearest_bus_by_stop",
            params={"provider": "tcc"}
        )
        
        assert response.status_code == 422
    
    @patch('taiwanbus.fetch_stop')
    @patch('taiwanbus.update_provider')
    def test_non_existent_stop_id(self, mock_update_provider, mock_fetch_stop):
        """Test 404 response for non-existent stop_id."""
        mock_fetch_stop.return_value = []
        
        response = client.get(
            "/nearest_bus_by_stop",
            params={"stop_id": 99999, "provider": "tcc"}
        )
        
        assert response.status_code == 404
        assert "detail" in response.json()
        assert "not found" in response.json()["detail"].lower()
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.fetch_stop')
    @patch('taiwanbus.update_provider')
    def test_no_buses_on_route(self, mock_update_provider, mock_fetch_stop, mock_getbus):
        """Test 404 when stop exists but no buses are on the route."""
        mock_fetch_stop.return_value = MOCK_STOP_INFO
        mock_getbus.return_value = MOCK_EMPTY_BUS_DATA
        
        response = client.get(
            "/nearest_bus_by_stop",
            params={"stop_id": 12345, "provider": "tcc"}
        )
        
        assert response.status_code == 404
        assert "detail" in response.json()
    
    @patch('taiwanbus.fetch_stop')
    @patch('taiwanbus.update_provider')
    def test_stop_without_coordinates(self, mock_update_provider, mock_fetch_stop):
        """Test error when stop exists but has no coordinates."""
        mock_fetch_stop.return_value = [
            {
                "stop_id": 12345,
                "stop_name": "Test Stop",
                "lat": 0,
                "lon": 0,
                "route_key": 100
            }
        ]
        
        response = client.get(
            "/nearest_bus_by_stop",
            params={"stop_id": 12345, "provider": "tcc"}
        )
        
        assert response.status_code == 400
        assert "coordinates" in response.json()["detail"].lower()


class TestDistanceCalculationInEndpoints:
    """Test that distance values are reasonable in endpoint responses."""
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.update_provider')
    def test_distance_is_non_negative_by_coord(self, mock_update_provider, mock_getbus):
        """Ensure distance_meters is always non-negative for nearest_bus_by_coord."""
        mock_getbus.return_value = MOCK_BUS_DATA
        
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 24.1234, "lon": 120.6789, "route_id": 100}
        )
        
        assert response.status_code == 200
        assert response.json()["distance_meters"] >= 0
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.fetch_stop')
    @patch('taiwanbus.update_provider')
    def test_distance_is_non_negative_by_stop(self, mock_update_provider, mock_fetch_stop, mock_getbus):
        """Ensure distance_meters is always non-negative for nearest_bus_by_stop."""
        mock_fetch_stop.return_value = MOCK_STOP_INFO
        mock_getbus.return_value = MOCK_BUS_DATA
        
        response = client.get(
            "/nearest_bus_by_stop",
            params={"stop_id": 12345, "provider": "tcc"}
        )
        
        assert response.status_code == 200
        assert response.json()["distance_meters"] >= 0
    
    @patch('taiwanbus.getbus')
    @patch('taiwanbus.update_provider')
    def test_distance_within_reasonable_range(self, mock_update_provider, mock_getbus):
        """Test that distance is within Earth's circumference (sanity check)."""
        mock_getbus.return_value = MOCK_BUS_DATA
        
        response = client.get(
            "/nearest_bus_by_coord",
            params={"lat": 24.1234, "lon": 120.6789, "route_id": 100}
        )
        
        assert response.status_code == 200
        # Maximum possible distance on Earth is ~20,000 km (half circumference)
        assert response.json()["distance_meters"] < 20000000
