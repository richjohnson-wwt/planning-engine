# How to Use the /plan Endpoint in Swagger UI

## Step-by-Step Instructions

### 1. Open Swagger UI
Navigate to: http://localhost:8000/docs

### 2. Find the /plan Endpoint
Scroll down to find the `POST /plan` endpoint and click on it to expand.

### 3. Click "Try it out"
Click the "Try it out" button in the top right of the endpoint section.

### 4. Paste the Request Body
Copy and paste the JSON below into the request body text area:

```json
{
  "workspace": "foobar",
  "sites": [
    {
      "id": "6308",
      "name": "Baton Rouge - Siegen Ln",
      "lat": 30.368906215424257,
      "lon": -91.07398901894588,
      "service_minutes": 60
    },
    {
      "id": "6309",
      "name": "Baton Rouge - Airline Hwy",
      "lat": 30.3990097,
      "lon": -91.05528163576336,
      "service_minutes": 60
    },
    {
      "id": "6310",
      "name": "Baton Rouge - Burbank Dr",
      "lat": 30.361727345634744,
      "lon": -91.12668377744508,
      "service_minutes": 60
    },
    {
      "id": "6311",
      "name": "Baton Rouge - Florida Blvd",
      "lat": 30.462157750000003,
      "lon": -91.03467109638676,
      "service_minutes": 60
    },
    {
      "id": "6312",
      "name": "Baton Rouge - Foster Dr",
      "lat": 30.44433616520245,
      "lon": -91.13859982450536,
      "service_minutes": 60
    },
    {
      "id": "6315",
      "name": "Baton Rouge - Sherwood Forest",
      "lat": 30.43304554920043,
      "lon": -91.05721648053286,
      "service_minutes": 60
    },
    {
      "id": "6316",
      "name": "Baton Rouge - Airline Hwy 2",
      "lat": 30.47065180026431,
      "lon": -91.1083460306244,
      "service_minutes": 60
    },
    {
      "id": "6801",
      "name": "Charlotte - Forest Point",
      "lat": 35.13746634384619,
      "lon": -80.90362354241172,
      "service_minutes": 60
    },
    {
      "id": "6803",
      "name": "Gastonia - Franklin Blvd",
      "lat": 35.25789690909091,
      "lon": -81.11611009090909,
      "service_minutes": 60
    },
    {
      "id": "6804",
      "name": "Charlotte - Harris Blvd",
      "lat": 35.2251502,
      "lon": -80.7258758,
      "service_minutes": 60
    },
    {
      "id": "6807",
      "name": "Charlotte - Westinghouse",
      "lat": 35.112507050000005,
      "lon": -80.92056662880883,
      "service_minutes": 60
    },
    {
      "id": "6808",
      "name": "Concord - Concord Pkwy",
      "lat": 35.39289714798798,
      "lon": -80.62150019444249,
      "service_minutes": 60
    },
    {
      "id": "6812",
      "name": "Concord - Lyles Ln",
      "lat": 35.36641787153482,
      "lon": -80.71286778228583,
      "service_minutes": 60
    },
    {
      "id": "6815",
      "name": "Shelby - Earl Rd",
      "lat": 35.27804438949521,
      "lon": -81.53696866988174,
      "service_minutes": 60
    },
    {
      "id": "6819",
      "name": "Charlotte - Tryon St",
      "lat": 35.323173499999996,
      "lon": -80.7328899610506,
      "service_minutes": 60
    }
  ],
  "team_config": {
    "teams": 2,
    "workday": {
      "start": "09:00:00",
      "end": "17:00:00"
    }
  },
  "start_date": "2025-01-06",
  "end_date": "2025-01-06",
  "num_crews_available": 2,
  "max_route_minutes": 480,
  "service_minutes_per_site": 60,
  "holidays": [],
  "max_sites_per_crew_per_day": 8,
  "minimize_crews": true
}
```

### 5. Click "Execute"
Click the blue "Execute" button to send the request.

### 6. View the Response
Scroll down to see the response. You should see:
- **Response Code**: 200 (success)
- **Response Body**: JSON with `team_days` showing the optimized routes and `unassigned` count

## Understanding the Request Parameters

### Required Fields:
- **workspace**: Your workspace name ("foobar")
- **sites**: Array of site objects with id, name, lat, lon, service_minutes
- **team_config**: Team configuration with number of teams and workday hours

### OR-Tools Specific Fields (for optimized routing):
- **start_date**: Start date for planning (YYYY-MM-DD format)
- **end_date**: End date for planning
- **num_crews_available**: Hard limit on number of crews (2 in this example)
- **max_route_minutes**: Maximum minutes per route (480 = 8 hours)
- **service_minutes_per_site**: Default service time per site (60 min)

### Expected Results:
With 15 sites, 2 crews, and 480 min max per route:
- Each crew can handle ~8 sites (480 min ÷ 60 min/site)
- With 2 crews, you can schedule ~16 sites max
- Since you have 15 sites, all should be scheduled across 2 crews
- Routes will be geographically optimized (LA sites together, NC sites together)

## Alternative: Simpler Request (Without OR-Tools)

If you want to test without OR-Tools optimization, omit `start_date` and `end_date`:

```json
{
  "workspace": "foobar",
  "sites": [...],
  "team_config": {
    "teams": 2,
    "workday": {
      "start": "09:00:00",
      "end": "17:00:00"
    }
  }
}
```

This will use simple assignment (all sites to team 1).

## Troubleshooting

### If you get a validation error:
- Check that all required fields are present
- Verify date format is "YYYY-MM-DD"
- Verify time format is "HH:MM:SS"
- Ensure lat/lon are valid numbers

### If the request times out:
- The OR-Tools solver can take 30+ seconds for complex problems
- This is normal for the first request
- Wait for the response - it will complete

### If you get unassigned sites:
- This means the constraints are too tight
- Try increasing `max_route_minutes` or `num_crews_available`
- Or reduce the number of sites
