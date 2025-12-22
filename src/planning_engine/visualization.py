"""
Visualization utilities for route planning results.
"""

import folium
from pathlib import Path
from typing import List
from .models import PlanResult, TeamDay, Site


def generate_folium_map(result: PlanResult, output_path: Path) -> Path:
    """
    Generate an interactive Folium map from planning results.
    
    Creates an HTML map with:
    - Color-coded markers for each team
    - Route lines connecting sites in visit order
    - Popups with site details
    - Legend showing team colors
    
    Args:
        result: PlanResult containing team_days with sites
        output_path: Path where the HTML map should be saved
        
    Returns:
        Path to the generated HTML file
    """
    # Define colors for different teams (cycling through if more teams than colors)
    team_colors = [
        'blue', 'red', 'green', 'purple', 'orange', 
        'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen',
        'cadetblue', 'darkpurple', 'pink', 'lightblue', 'lightgreen',
        'gray', 'black', 'lightgray'
    ]
    
    # Collect all sites to determine map center
    all_sites = []
    for team_day in result.team_days:
        if team_day.sites:
            all_sites.extend(team_day.sites)
    
    if not all_sites:
        # No sites to map
        return None
    
    # Calculate center point (average of all coordinates)
    center_lat = sum(site.lat for site in all_sites) / len(all_sites)
    center_lon = sum(site.lon for site in all_sites) / len(all_sites)
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Track which teams we've seen for the legend
    teams_used = set()
    
    # Add routes for each team_day
    for team_day in result.team_days:
        if not team_day.sites:
            continue
            
        team_id = team_day.team_id
        teams_used.add(team_id)
        color = team_colors[team_id % len(team_colors)]
        
        # Create route line connecting sites in order
        route_coords = [[site.lat, site.lon] for site in team_day.sites]
        
        if len(route_coords) > 1:
            folium.PolyLine(
                route_coords,
                color=color,
                weight=3,
                opacity=0.7,
                popup=f"Team {team_id} - {team_day.date if team_day.date else 'No date'}"
            ).add_to(m)
        
        # Add numbered markers for each site in visit order
        for idx, site in enumerate(team_day.sites, 1):
            # Build popup content
            popup_html = f"""
            <div style="font-family: Arial; min-width: 200px;">
                <h4 style="margin: 0 0 10px 0; color: {color};">Stop #{idx}</h4>
                <b>{site.name}</b><br>
                {site.address if site.address else 'No address'}<br>
                <hr style="margin: 10px 0;">
                <b>Team:</b> {team_id}<br>
                <b>Date:</b> {team_day.date if team_day.date else 'Not scheduled'}<br>
                <b>Service Time:</b> {site.service_minutes} min<br>
                <b>Coordinates:</b> {site.lat:.4f}, {site.lon:.4f}
            </div>
            """
            
            # Create marker with number icon
            folium.Marker(
                location=[site.lat, site.lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Team {team_id} - Stop {idx}: {site.name}",
                icon=folium.Icon(
                    color=color,
                    icon='info-sign',
                    prefix='glyphicon'
                )
            ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; 
                border:2px solid grey; z-index:9999; 
                background-color:white;
                padding: 10px;
                font-size:14px;
                font-family: Arial;
                ">
    <p style="margin: 0 0 10px 0;"><b>Team Routes</b></p>
    '''
    
    for team_id in sorted(teams_used):
        color = team_colors[team_id % len(team_colors)]
        legend_html += f'<p style="margin: 5px 0;"><span style="color: {color};">●</span> Team {team_id}</p>'
    
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add title
    title_html = '''
    <div style="position: fixed; 
                top: 10px; left: 50px; 
                z-index:9999; 
                background-color:white;
                padding: 10px;
                border:2px solid grey;
                font-size:16px;
                font-family: Arial;
                font-weight: bold;
                ">
    Route Planning Map
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Save map
    m.save(str(output_path))
    
    return output_path
