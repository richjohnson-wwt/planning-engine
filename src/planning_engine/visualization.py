"""
Visualization utilities for route planning results.
"""

import folium
import html
import json
from pathlib import Path
from typing import List
from .models import PlanResult, TeamDay, Site


def generate_folium_map(result: PlanResult, output_path: Path) -> Path:
    """
    Generate an interactive Folium map from planning results.
    
    Creates an HTML map with:
    - Color-coded markers for each team with cluster color families
    - Route lines connecting sites in visit order
    - Popups with site details
    - Legend showing team colors grouped by cluster
    
    Args:
        result: PlanResult containing team_days with sites
        output_path: Path where the HTML map should be saved
        
    Returns:
        Path to the generated HTML file
    """
    # Define color families for clusters (each cluster gets a color family)
    # Expanded to support 25+ clusters with distinct, visually different colors
    # Each cluster gets a set of related colors for its teams
    cluster_color_families = {
        0: ['blue', 'darkblue', 'lightblue', 'cadetblue'],
        1: ['red', 'darkred', 'lightred', 'pink'],
        2: ['green', 'darkgreen', 'lightgreen'],
        3: ['purple', 'darkpurple'],
        4: ['orange', 'darkorange'],
        5: ['beige', 'lightgray'],
        6: ['gray', 'darkgray'],
        7: ['black'],
        8: ['white'],
        9: ['cadetblue', 'lightblue'],
        10: ['pink', 'lightred'],
        11: ['lightgreen', 'green'],
        12: ['darkpurple', 'purple'],
        13: ['darkorange', 'orange'],
        14: ['darkblue', 'blue'],
        15: ['darkred', 'red'],
        16: ['darkgreen', 'green'],
        17: ['lightgray', 'gray'],
        18: ['beige', 'lightgray'],
        19: ['cadetblue', 'blue'],
        20: ['pink', 'red'],
        21: ['lightgreen', 'darkgreen'],
        22: ['purple', 'darkpurple'],
        23: ['orange', 'darkorange'],
        24: ['gray', 'black'],
    }
    
    # Fallback colors if we have more clusters than defined families
    # Highly diverse color palette to maximize visual distinction
    fallback_colors = [
        'blue', 'red', 'green', 'purple', 'orange', 
        'darkred', 'darkblue', 'darkgreen', 'darkpurple', 'cadetblue',
        'pink', 'lightblue', 'lightgreen', 'lightred', 'beige',
        'gray', 'darkgray', 'lightgray', 'black', 'white',
        'darkorange'
    ]
    
    def get_team_color(team_day: TeamDay) -> str:
        """Get color for a team based on cluster and team ID."""
        if team_day.cluster_id is not None:
            # Use cluster color family
            color_family = cluster_color_families.get(
                team_day.cluster_id,
                fallback_colors
            )
            # Use team_id to pick a color from the family
            color_index = (team_day.team_id - 1) % len(color_family)
            return color_family[color_index]
        else:
            # No clustering, use fallback colors
            return fallback_colors[team_day.team_id % len(fallback_colors)]
    
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
    
    # Track which teams we've seen for the legend (store team_day objects for sorting)
    teams_used = []
    
    # Add routes for each team_day
    for team_day in result.team_days:
        if not team_day.sites:
            continue
            
        teams_used.append(team_day)
        color = get_team_color(team_day)
        
        # Use team_label if available, otherwise fall back to team_id
        team_display = team_day.team_label if team_day.team_label else f"Team {team_day.team_id}"
        
        # Create route line connecting sites in order
        route_coords = [[site.lat, site.lon] for site in team_day.sites]
        
        if len(route_coords) > 1:
            # Simple text for route popup
            route_popup = f"{team_display} - {team_day.date if team_day.date else 'No date'}"
            folium.PolyLine(
                route_coords,
                color=color,
                weight=3,
                opacity=0.7,
                popup=route_popup
            ).add_to(m)
        
        # Add numbered markers for each site in visit order
        for idx, site in enumerate(team_day.sites, 1):
            # Sanitize backticks and other JS-breaking chars, then HTML escape
            # Backticks break JS template literals when Folium embeds content
            safe_name = html.escape(site.name.replace('`', "'"))
            safe_address = html.escape(site.address.replace('`', "'")) if site.address else 'No address'
            safe_date = str(team_day.date) if team_day.date else 'Not scheduled'
            
            # Build popup content with HTML-escaped data
            popup_html = f"""
            <div style="font-family: Arial; min-width: 200px;">
                <h4 style="margin: 0 0 10px 0; color: {color};">Stop #{idx}</h4>
                <b>{safe_name}</b><br>
                {safe_address}<br>
                <hr style="margin: 10px 0;">
                <b>Team:</b> {team_display}<br>
                <b>Date:</b> {safe_date}<br>
                <b>Service Time:</b> {site.service_minutes} min<br>
                <b>Coordinates:</b> {site.lat:.4f}, {site.lon:.4f}
            </div>
            """
            
            # Use IFrame for popup to handle escaping properly
            iframe = folium.IFrame(popup_html, width=300, height=200)
            popup = folium.Popup(iframe, max_width=300)
            
            # Create marker with number icon
            # Sanitize backticks in tooltip (they break JS template literals)
            sanitized_name = site.name.replace('`', "'")
            tooltip_text = f"{team_display} - Stop {idx}: {sanitized_name}"
            folium.Marker(
                location=[site.lat, site.lon],
                popup=popup,
                tooltip=tooltip_text,
                icon=folium.Icon(
                    color=color,
                    icon='info-sign',
                    prefix='glyphicon'
                )
            ).add_to(m)
    
    # Add legend grouped by cluster
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
    
    # Sort teams by cluster_id (if present) and then by team_id
    # Remove duplicates by using a dict keyed by (cluster_id, team_id)
    unique_teams = {}
    for td in teams_used:
        key = (td.cluster_id if td.cluster_id is not None else -1, td.team_id)
        if key not in unique_teams:
            unique_teams[key] = td
    
    # Sort by cluster (None/-1 first), then by team_id
    sorted_teams = sorted(unique_teams.values(), 
                         key=lambda td: (td.cluster_id if td.cluster_id is not None else -1, td.team_id))
    
    current_cluster = None
    for td in sorted_teams:
        # Add cluster header if we're starting a new cluster
        if td.cluster_id is not None and td.cluster_id != current_cluster:
            if current_cluster is not None:
                legend_html += '<hr style="margin: 8px 0; border: 0; border-top: 1px solid #ccc;">'
            legend_html += f'<p style="margin: 5px 0; font-weight: bold; color: #555;">Cluster {td.cluster_id + 1}</p>'
            current_cluster = td.cluster_id
        
        color = get_team_color(td)
        team_display = td.team_label if td.team_label else f"Team {td.team_id}"
        legend_html += f'<p style="margin: 5px 0; padding-left: 10px;"><span style="color: {color};">●</span> {team_display}</p>'
    
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
