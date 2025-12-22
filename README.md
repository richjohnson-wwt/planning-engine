
# User request features

Custom Parameters:
* Team Assignments – allocate routes based on number of teams
    * Auto-calculate number of teams needed
    * Or divide based on regions and/or number of sites
* Time Estimation – estimate time per site and total project duration
    * Set Project Start/End Dates
    * Define working hours per day
    * Set number of sites per day per team
    * Set the run rate across the regions that can be completed per each bridge/cut
    * Set hours to complete each site; also by t shirt size
    * Load in breaks; fire, holidays, blackout dates
    * Can a region be completed before a break comes or push to start after the break
* Routing –
    * Team radius based on region – not to go over x amount of miles (avoidance of overnight travel)
* Craw, Walk, Run – Ramp Phase approach
 


# Workflow

1. Create workspace

```
    curl -X 'POST' \
        'http://127.0.0.1:8000/workspace' \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d '{
        "workspace_name": "foo"
    }'
```

2. Parse Excel

```
    curl -X 'POST' \
        'http://127.0.0.1:8000/parse-excel' \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d '{
    "column_mapping": {
        "city": "City",
        "site_id": "Lab name",
        "state": "State",
        "street1": "Address (Location)",
        "zip": "Zip Code"
    },
    "file_path": "/Users/johnsori/Downloads/AscensionClean.xlsx",
    "workspace_name": "foo"
    }'
```

3. Geocode

```
    curl -X 'POST' \
        'http://127.0.0.1:8000/geocode' \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d '{
            "state_abbr": "LA",
        "workspace_name": "foo"
    }'
```

4. Cluster

```
    curl -X 'POST' \
        'http://127.0.0.1:8000/cluster' \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d '{
            "state_abbr": "LA",
        "workspace_name": "foo"
    }'
```

5. Plan

```
    curl -X 'POST' \
    'http://127.0.0.1:8000/plan' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{
        "workspace": "foo",
        "use_clusters": true,
        "state_abbr": "LA",
        "team_config": {
            "teams": 2,
            "workday": {
            "start": "09:00:00",
        "end": "17:00:00"
        }
    },
    "start_date": "2025-01-06",
    "end_date": "2025-01-06",
    "max_route_minutes": 480,
    "service_minutes_per_site": 60,
    "holidays": [],
    }'
```


## Multi day notes 


Mode 1: Fixed Crews → How Long Will It Take?
request = PlanRequest(
    workspace="foo",
    state_abbr="LA",
    sites=150_sites,
    start_date=date(2025, 1, 1),    # Start when ready
    end_date=None,                   # ❓ Calculate this!
    team_config=TeamConfig(teams=3, workday=...),  # Fixed: only 3 crews
    max_route_minutes=480,
    service_minutes_per_site=60,
)

# Multi-day scheduler will:
# 1. Calculate capacity: 3 crews × 8 sites/day = 24 sites/day
# 2. Calculate days needed: 150 sites ÷ 24 = ~7 days
# 3. Generate work days starting from start_date
# 4. Call plan_single_day_vrp() for each of those 7 days
# 5. Return: "Will take 7 work days with 3 crews"

result = plan_multi_day_schedule(request)
# Output: 21 team-days (7 days × 3 crews)


#Mode 2: Fixed Dates → How Many Crews Needed?
request = PlanRequest(
    workspace="foo",
    state_abbr="LA",
    sites=150_sites,
    start_date=None,                 # ❓ Calculate this!
    end_date=date(2025, 1, 31),      # Must finish by Jan 31
    team_config=TeamConfig(teams=None, workday=...),  # ❓ Calculate this!
    max_route_minutes=480,
    service_minutes_per_site=60,
)

# Multi-day scheduler will:
# 1. Calculate work days: 5 days (Jan 1-31)
# 2. Calculate required capacity: 150 sites ÷ 5 days = 30 sites/day
# 3. Calculate crews needed: 30 sites/day ÷ 8 sites/crew = 4 crews
# 4. Call plan_single_day_vrp() for each day with 4 crews
# 5. Return: "Need 4 crews to complete in 5 days"

result = plan_multi_day_schedule(request)
# Output: 20 team-days (5 days × 4 crews)



#Mode 1: Fixed Crews → Calculate Duration
# "I have 3 crews. How long will it take to complete 150 sites?"

request = PlanRequest(
    workspace="foo",
    state_abbr="LA",
    start_date=date(2025, 1, 1),     # Start date
    end_date=None,                    # Will be calculated
    team_config=TeamConfig(teams=3, workday=...),  # Fixed: only 3 crews
    # ... other params
)

result = plan_multi_day_schedule(request)

# Scheduler will:
# 1. Calculate capacity: 3 crews × 8 sites/day = 24 sites/day
# 2. Calculate days: 150 ÷ 24 = 7 days needed
# 3. Generate 7 work days from start_date
# 4. Call plan_single_day_vrp() for each day
# 5. Return: "7 days with 3 crews = 21 team-days"


#Mode 2: Fixed Dates → Calculate Crews
# "I need to finish 150 sites by Jan 5. How many crews do I need?"

request = PlanRequest(
    workspace="foo",
    state_abbr="LA",
    start_date=date(2025, 1, 1),     # Must start Jan 1
    end_date=date(2025, 1, 5),       # Must finish Jan 5 (5 days)
    # team_config.teams will be calculated automatically
    # ... other params
)

result = plan_multi_day_schedule(request)

# Scheduler will:
# 1. Calculate work days: 5 days
# 2. Calculate required: 150 ÷ 5 = 30 sites/day
# 3. Calculate crews: 30 ÷ 8 = 4 crews needed
# 4. Call plan_single_day_vrp() for each day with 4 crews
# 5. Return: "4 crews for 5 days = 20 team-days"