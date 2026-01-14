import requests
import time
from planning_engine.models import Site
from planning_engine.data_prep.geocode_cache import get_cache

API_KEY = "58c0f7b0515d4094bb6a48ab559290f3"


def batch_geocode_sites(addresses: list[str]) -> list[dict]:
    """
    Geocode a list of addresses using the Geoapify batch API.
    
    Checks the shared cache first to avoid unnecessary API calls.
    Only geocodes addresses that are not already cached.
    
    Args:
        addresses: List of address strings to geocode
        
    Returns:
        List of geocoding results with lat/lon coordinates
        
    Raises:
        Exception: If the geocoding job fails
    """
    if not addresses:
        return []
    
    cache = get_cache()
    
    # Parse addresses and check cache
    # Addresses are expected in format: "street, city, state zip"
    parsed_addresses = []
    address_to_index = {}  # Map cache key to original index
    
    for idx, addr_str in enumerate(addresses):
        # Parse the address string
        parts = [p.strip() for p in addr_str.split(',')]
        if len(parts) >= 3:
            street = parts[0]
            city = parts[1]
            # State and zip might be together in last part
            state_zip = parts[2].split()
            state = state_zip[0] if state_zip else ''
            zip_code = state_zip[1] if len(state_zip) > 1 else None
            
            # Clean up ZIP code - remove .0 if it's a float string
            if zip_code and '.' in zip_code:
                try:
                    # Convert to float then int to remove decimal
                    zip_code = str(int(float(zip_code)))
                except (ValueError, TypeError):
                    pass  # Keep original if conversion fails
            
            parsed_addresses.append((street, city, state, zip_code))
            cache_key = cache._hash_address(street, city, state, zip_code)
            address_to_index[cache_key] = idx
        else:
            # Malformed address, will need to geocode it
            parsed_addresses.append((addr_str, '', '', None))
            cache_key = cache._hash_address(addr_str, '', '', None)
            address_to_index[cache_key] = idx
    
    # Batch check cache
    print(f"Checking cache for {len(parsed_addresses)} addresses...")
    cache_results = cache.batch_get(parsed_addresses)
    
    # Separate cached vs uncached addresses
    cached_count = sum(1 for v in cache_results.values() if v is not None)
    uncached_indices = []
    uncached_addresses = []
    results = [None] * len(addresses)  # Pre-allocate results array
    
    for cache_key, cache_result in cache_results.items():
        idx = address_to_index[cache_key]
        if cache_result is not None:
            # Use cached result - convert to Geoapify API response format
            # The API returns results with lat/lon at the top level
            results[idx] = {
                'lat': cache_result['lat'],
                'lon': cache_result['lon'],
                'properties': {
                    'lat': cache_result['lat'],
                    'lon': cache_result['lon'],
                    'formatted': cache_result['formatted'],
                    'street': cache_result['street1'],
                    'city': cache_result['city'],
                    'state': cache_result['state'],
                    'postcode': cache_result['zip']
                }
            }
        else:
            # Need to geocode this address
            uncached_indices.append(idx)
            uncached_addresses.append(addresses[idx])
    
    print(f"✓ Cache hit: {cached_count}/{len(addresses)} addresses ({cached_count*100//len(addresses)}%)")
    
    # If all addresses were cached, return immediately
    if not uncached_addresses:
        print("✓ All addresses found in cache - no API calls needed!")
        return results
    
    print(f"Geocoding {len(uncached_addresses)} new addresses via API...")
    
    # Geocode uncached addresses via API
    # Correct Geoapify batch API URL (note: apiKey not api_key)
    url = f"https://api.geoapify.com/v1/batch/geocode/search?apiKey={API_KEY}"
    
    # Start the batch geocoding job
    response = requests.post(url, json=uncached_addresses)
    
    # Check for HTTP errors (202 Accepted is correct for async batch jobs)
    if response.status_code not in [200, 202]:
        raise Exception(f"Failed to start geocoding job (HTTP {response.status_code}): {response.text}")
    
    # Parse the response - it should have status "pending" initially
    job_data = response.json()
    
    # Check if the job was created successfully
    if "id" not in job_data or "url" not in job_data:
        raise Exception(f"Invalid response from Geoapify: {job_data}")
    
    job_url = job_data["url"]  # Get the job status URL
    print(f"✓ Geocoding job created successfully")
    print(f"  Job ID: {job_data['id']}")
    print(f"  Status: {job_data.get('status', 'unknown')}")

    # Poll for completion with timeout
    # For large batches (500+ addresses), geocoding can take 10-15 minutes
    max_attempts = 240  # 20 minutes max (240 attempts * 5 seconds = 1200 seconds)
    attempts = 0
    
    print(f"Waiting for geocoding to complete (max {max_attempts * 5 // 60} minutes)...")
    
    while attempts < max_attempts:
        attempts += 1
        status_resp = requests.get(job_url)
        
        # Only print status every 6 attempts (30 seconds) to reduce noise
        if attempts % 6 == 0 or attempts == 1:
            elapsed_minutes = (attempts * 5) // 60
            print(f"  [{elapsed_minutes}m] Polling attempt {attempts}/{max_attempts}: HTTP {status_resp.status_code}")
        
        # When the job is finished, status code is 200 and the response IS the results array
        if status_resp.status_code == 200:
            api_results = status_resp.json()
            # Results should be a list of geocoded addresses
            if isinstance(api_results, list):
                print(f"✓ Geocoding completed: {len(api_results)} addresses processed")
                
                # Cache the new results
                print("Caching newly geocoded addresses...")
                cache_entries = []
                for i, api_result in enumerate(api_results):
                    idx = uncached_indices[i]
                    
                    # Extract data from API result
                    # Geoapify batch API returns flat structure with lat/lon at top level
                    lat = api_result.get('lat')
                    lon = api_result.get('lon')
                    
                    if lat and lon:
                        # Parse the original address
                        street, city, state, zip_code = parsed_addresses[idx]
                        
                        # Prepare cache entry
                        cache_entries.append({
                            'street': street,
                            'city': city,
                            'state': state,
                            'zip': zip_code,
                            'lat': lat,
                            'lon': lon,
                            'formatted': api_result.get('formatted')
                        })
                        
                        # Add to results array with both flat and nested structure
                        # for compatibility with downstream code
                        results[idx] = {
                            'lat': lat,
                            'lon': lon,
                            'properties': api_result  # Store full result in properties
                        }
                
                # Batch cache all new results
                if cache_entries:
                    cache.batch_set(cache_entries)
                    print(f"✓ Cached {len(cache_entries)} new addresses")
                
                return results
            else:
                raise Exception(f"Unexpected response format: {type(api_results)}")
        
        # When still pending, status code is 202 and response has status field
        elif status_resp.status_code == 202:
            status_data = status_resp.json()
            print(f"  Status data: {status_data}")
            if status_data.get("status") == "failed":
                raise Exception(f"Geocoding job failed: {status_data.get('message', 'Unknown error')}")
            print(f"Geocoding in progress... waiting 5 seconds")
            time.sleep(5)
        
        else:
            # Log the full response for debugging
            print(f"Unexpected HTTP status {status_resp.status_code}")
            print(f"Response body: {status_resp.text[:500]}")  # First 500 chars
            raise Exception(f"Unexpected HTTP status {status_resp.status_code}: {status_resp.text[:200]}")
    
    # Timeout reached
    raise Exception(f"Geocoding job timed out after {max_attempts * 5} seconds. Job may still be processing.")
