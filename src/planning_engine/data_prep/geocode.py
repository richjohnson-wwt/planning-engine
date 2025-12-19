import requests
import time
from planning_engine.models import Site

API_KEY = "58c0f7b0515d4094bb6a48ab559290f3"


def batch_geocode_sites(addresses: list[str]) -> list[dict]:
    """
    Geocode a list of addresses using the Geoapify batch API.
    
    Args:
        addresses: List of address strings to geocode
        
    Returns:
        List of geocoding results with lat/lon coordinates
        
    Raises:
        Exception: If the geocoding job fails
    """
    # Correct Geoapify batch API URL (note: apiKey not api_key)
    url = f"https://api.geoapify.com/v1/batch/geocode/search?apiKey={API_KEY}"
    
    # Start the batch geocoding job
    response = requests.post(url, json=addresses)
    
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

    # Poll for completion
    while True:
        status_resp = requests.get(job_url)
        
        # When the job is finished, status code is 200 and the response IS the results array
        if status_resp.status_code == 200:
            results = status_resp.json()
            # Results should be a list of geocoded addresses
            if isinstance(results, list):
                print(f"✓ Geocoding completed: {len(results)} addresses processed")
                return results
            else:
                raise Exception(f"Unexpected response format: {type(results)}")
        
        # When still pending, status code is 202 and response has status field
        elif status_resp.status_code == 202:
            status_data = status_resp.json()
            if status_data.get("status") == "failed":
                raise Exception(f"Geocoding job failed: {status_data.get('message', 'Unknown error')}")
            print(f"Geocoding in progress... waiting 5 seconds")
            time.sleep(5)
        
        else:
            raise Exception(f"Unexpected HTTP status {status_resp.status_code}: {status_resp.text}")
