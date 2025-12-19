

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

    