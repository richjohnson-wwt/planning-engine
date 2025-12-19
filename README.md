
# User request features

Custom Parameters:
Team Assignments – allocate routes based on number of teams
Auto-calculate number of teams needed
Or divide based on regions and/or number of sites
Time Estimation – estimate time per site and total project duration
Set Project Start/End Dates
Define working hours per day
Set number of sites per day per team
Set the run rate across the regions that can be completed per each bridge/cut
Set hours to complete each site; also by t shirt size
Load in breaks; fire, holidays, blackout dates
Can a region be completed before a break comes or push to start after the break
Typical Weather patterns thought about; ie. outside work prob shouldn’t be done in MN during the winter; factor in starting Northern sites and work way south
Routing –
Team radius based on region – not to go over x amount of miles (avoidance of overnight travel)
Craw, Walk, Run – Ramp Phase approach
 
 
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
        "workspace_name": "foo"
    }'
```

5. Plan

    