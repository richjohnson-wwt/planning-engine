"""
Team Schedule CSV Generation

Generates CSV schedules for individual teams based on planning results.
CSV format is suitable for import into Smartsheet and other spreadsheet applications.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import csv

from planning_engine.team_schedule import _prepare_team_schedule_data


def generate_team_schedule_csv(
    workspace_name: str,
    state_abbr: str,
    team_id: str,
    output_path: Path
) -> bool:
    """
    Generate a CSV schedule for a specific team.
    
    The CSV includes one row per site with columns for:
    - Team information
    - Route/Day information
    - Site details
    - Contact information
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        team_id: Team ID to generate schedule for
        output_path: Path where CSV should be saved
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get prepared data using existing helper
        data = _prepare_team_schedule_data(workspace_name, state_abbr, team_id)
        if not data:
            return False
        
        team_info = data['team_info']
        metadata = data['metadata']
        team_routes = data['team_routes']
        
        # Define CSV columns
        fieldnames = [
            'Team ID',
            'Team Name',
            'Team City',
            'Team Contact',
            'Team Phone',
            'Route Number',
            'Day',
            'Route Label',
            'Total Sites',
            'Total Distance (mi)',
            'Total Time (hrs)',
            'Site Number',
            'Site ID',
            'Site Name',
            'Street Address',
            'City',
            'State',
            'Zip',
            'Service Time (min)',
            'Contact Name',
            'Contact Phone'
        ]
        
        # Open CSV file for writing
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Process each route
            for route_idx, route in enumerate(team_routes, 1):
                day = route.get('day', 1)
                route_label = route.get('team_label', f'{team_id}-R{route_idx}')
                sites = route.get('sites', [])
                total_distance = route.get('total_distance_miles', 0)
                total_time = route.get('total_time_hours', 0)
                
                # Write one row per site
                for site_idx, site in enumerate(sites, 1):
                    row = {
                        'Team ID': team_id,
                        'Team Name': team_info.team_name or '',
                        'Team City': team_info.city or '',
                        'Team Contact': team_info.contact_name or '',
                        'Team Phone': team_info.contact_phone or '',
                        'Route Number': route_idx,
                        'Day': day,
                        'Route Label': route_label,
                        'Total Sites': len(sites),
                        'Total Distance (mi)': f"{total_distance:.1f}",
                        'Total Time (hrs)': f"{total_time:.1f}",
                        'Site Number': site_idx,
                        'Site ID': site.get('id', ''),
                        'Site Name': site.get('name', ''),
                        'Street Address': site.get('address', ''),
                        'City': site.get('city', ''),
                        'State': site.get('state', ''),
                        'Zip': site.get('zip', ''),
                        'Service Time (min)': site.get('service_minutes', 60),
                        'Contact Name': site.get('contact_name', ''),
                        'Contact Phone': site.get('contact_phone', '')
                    }
                    writer.writerow(row)
        
        print(f"✓ Generated CSV schedule: {output_path}")
        return True
    
    except Exception as e:
        print(f"Error generating CSV schedule: {e}")
        import traceback
        traceback.print_exc()
        return False
