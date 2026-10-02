# Route fuel optimizer API

Django REST API that plans a US driving route, picks cost-effective truck stops under a 500-mile vehicle range, and returns map geometry plus total fuel spend at 10 mpg.

**Author:** Andrew Mogbeyiromore

## Behavior

- `POST /api/v1/routes/plan/` with `{"start": "Dallas, TX", "finish": "Chicago, IL"}`.
- Start and finish are geocoded with OpenStreetMap Nominatim (US only).
- The driving route comes from the public OSRM demo server in a single call (`overview=full`, GeoJSON).
- Truck-stop prices come from the OPIS sheet in `data/fuel-prices.csv`. Stations are matched to city centroids from `data/us_cities.csv` and held in memory with a k-d tree. Each request only searches stations that sit in a 12-mile corridor around the route.
- The vehicle starts with a full tank. Stops are chosen with the linear “fill or not to fill” policy: buy at the cheapest reachable station; fill the tank only when nothing cheaper lies within the next 500 miles; otherwise buy just enough to reach the cheaper station.
- `fuel.gallons_consumed` is `distance / 10`. `fuel.total_fuel_cost_usd` is money spent at stops (the opening tank is not billed).
- Geocode and route payloads are written to the on-disk cache. A repeat pair of cities does not call Nominatim or OSRM again.

Nominatim plus OSRM is at most three outbound HTTP calls on a cache miss, and zero on a hit.

## Setup

Python 3.12+ recommended.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py runserver
```

Replace the fuel file if you were given a different sheet:

```text
data/fuel-prices.csv
```

Expected columns: `OPIS Truckstop ID`, `Truckstop Name`, `Address`, `City`, `State`, `Rack ID`, `Retail Price`.

Open http://127.0.0.1:8000/ for a Leaflet map, or import `postman_collection.json`.

```bash
python manage.py test planner
```

## Response shape

```json
{
  "vehicle": { "range_miles": 500.0, "mpg": 10.0, "starts_with_full_tank": true },
  "start": { "query": "Dallas, TX", "display_name": "...", "latitude": 32.77, "longitude": -96.79 },
  "finish": { "query": "Chicago, IL", "display_name": "...", "latitude": 41.87, "longitude": -87.62 },
  "route": {
    "distance_miles": 925.4,
    "duration_minutes": 800.0,
    "map_url": "https://www.openstreetmap.org/directions?...",
    "geometry": { "type": "LineString", "coordinates": [[-96.79, 32.77], "..."] }
  },
  "fuel": {
    "gallons_consumed": 92.54,
    "gallons_purchased": 43.10,
    "total_fuel_cost_usd": 128.45,
    "stops": [
      {
        "sequence": 1,
        "name": "PILOT TRAVEL CENTER",
        "city": "Joliet",
        "state": "IL",
        "retail_price_usd": 3.199,
        "gallons": 21.4,
        "cost_usd": 68.46,
        "miles_from_start": 410.2
      }
    ]
  }
}
```

Station coordinates are city-level. That is enough to place markers on the highway corridor without geocoding 8,000 street addresses at request time.
