"""
Complete workflow example: Excel → Geocode → Cluster → Plan with OR-Tools

This demonstrates the full pipeline:
1. parse_excel: Load addresses from Excel
2. geocode: Get lat/lon coordinates
3. cluster: (Optional) Group sites by geographic proximity
4. load_sites_from_workspace: Load geocoded/clustered sites
5. plan: Optimize routes with OR-Tools solver
"""

from datetime import time, date
from planning_engine import (
    new_workspace,
    parse_excel,
    geocode,
    cluster,
    load_sites_from_workspace,
    plan
)
from planning_engine.models import PlanRequest, TeamConfig, Workday

# Configuration
WORKSPACE_NAME = "complete_workflow_demo2"
EXCEL_FILE = "examples/acme.xlsx"  # Your Excel file with addresses

# Column mapping: maps your Excel columns to standard fields
COLUMN_MAPPING = {
    "site_id": "Location",      # Your Excel column for site ID
    "street1": "MyStreet1",        # Your Excel column for street address
    "city": "MyCity",              # Your Excel column for city
    "state": "MyState",            # Your Excel column for state
    "zip": "MyZip",                # Your Excel column for zip code
    # "street2": "Suite",        # Optional: secondary address line
}

def main():
    print("="*60)
    print("COMPLETE WORKFLOW: Excel → Geocode → Cluster → Plan")
    print("="*60)
    
    # Step 1: Create workspace
    print("\n[1/5] Creating workspace...")
    workspace_path = new_workspace(WORKSPACE_NAME)
    print(f"✓ Workspace created at: {workspace_path}")
    
    # Step 2: Parse Excel file
    print("\n[2/5] Parsing Excel file...")
    addresses_csv = parse_excel(
        workspace_name=WORKSPACE_NAME,
        file_path=EXCEL_FILE,
        column_mapping=COLUMN_MAPPING
    )
    print(f"✓ Addresses saved to: {addresses_csv}")
    
    # Step 3: Geocode addresses
    print("\n[3/5] Geocoding addresses...")
    geocoded_csv = geocode(WORKSPACE_NAME)
    print(f"✓ Geocoded data saved to: {geocoded_csv}")
    
    # Step 4: (Optional) Cluster sites
    print("\n[4/5] Clustering sites...")
    try:
        clustered_csv = cluster(WORKSPACE_NAME)
        print(f"✓ Clustered data saved to: {clustered_csv}")
        use_clustered = True
    except Exception as e:
        print(f"⚠ Clustering skipped: {e}")
        use_clustered = False
    
    # Step 5: Load sites and plan routes
    print("\n[5/5] Planning optimized routes with OR-Tools...")
    
    # If clustered, plan separately for each cluster to avoid infeasible routing
    # (e.g., sites in LA and NC are too far apart to route together)
    if use_clustered:
        import pandas as pd
        from pathlib import Path
        
        # Read clustered data to determine number of clusters
        clustered_csv = Path("data") / "workspace" / WORKSPACE_NAME / "cache" / "clustered.csv"
        df = pd.read_csv(clustered_csv)
        num_clusters = df['cluster_id'].nunique()
        
        print(f"  Found {num_clusters} clusters - planning routes separately for each cluster")
        
        all_team_days = []
        all_sites = []
        
        for cluster_id in range(num_clusters):
            print(f"\n  Planning cluster {cluster_id}...")
            
            # Load sites for this cluster
            cluster_sites = load_sites_from_workspace(
                workspace_name=WORKSPACE_NAME,
                use_clustered=True,
                cluster_id=cluster_id
            )
            all_sites.extend(cluster_sites)
            
            # Configure team for this cluster
            team_config = TeamConfig(
                teams=1,  # 1 crew per cluster
                workday=Workday(start=time(hour=8, minute=0), end=time(hour=17, minute=0))
            )
            
            # Create plan request for this cluster
            request = PlanRequest(
                workspace=WORKSPACE_NAME,
                sites=cluster_sites,
                team_config=team_config,
                # OR-Tools specific fields
                start_date=date(2025, 1, 6),  # Monday
                end_date=date(2025, 1, 10),   # Friday (5 days)
                num_crews_available=1,
                max_route_minutes=480,  # 8 hours
                break_minutes=30,
                holidays=[],
                max_sites_per_crew_per_day=5,
                minimize_crews=True,
            )
            
            # Run planning for this cluster
            cluster_result = plan(request)
            
            # Adjust team IDs to be unique across clusters
            for td in cluster_result.team_days:
                td.team_id = td.team_id + (cluster_id * 10)  # Cluster 0: teams 1-9, Cluster 1: teams 11-19, etc.
            
            all_team_days.extend(cluster_result.team_days)
            print(f"    ✓ Cluster {cluster_id}: {len(cluster_result.team_days)} team-days scheduled")
        
        # Combine results from all clusters
        from planning_engine.models import PlanResult
        result = PlanResult(team_days=all_team_days)
        sites = all_sites
        
    else:
        # No clustering - plan all sites together
        sites = load_sites_from_workspace(
            workspace_name=WORKSPACE_NAME,
            use_clustered=False
        )
        
        # Configure team
        team_config = TeamConfig(
            teams=2,  # 2 crews available
            workday=Workday(start=time(hour=8, minute=0), end=time(hour=17, minute=0))
        )
        
        # Create plan request with OR-Tools parameters
        request = PlanRequest(
            workspace=WORKSPACE_NAME,
            sites=sites,
            team_config=team_config,
            # OR-Tools specific fields for optimized routing
            start_date=date(2025, 1, 6),  # Monday
            end_date=date(2025, 1, 10),   # Friday (5 days)
            num_crews_available=2,
            max_route_minutes=480,  # 8 hours
            break_minutes=30,
            holidays=[],
            max_sites_per_crew_per_day=5,
            minimize_crews=True,
        )
        
        # Run planning
        result = plan(request)
    
    # Display and save results
    print("\n" + "="*60)
    print("OPTIMIZED ROUTE PLAN")
    print("="*60)
    
    # Group by team
    team_schedule = {}
    for td in result.team_days:
        if td.team_id not in team_schedule:
            team_schedule[td.team_id] = []
        team_schedule[td.team_id].append(td)
    
    # Build output text
    output_lines = []
    output_lines.append("="*60)
    output_lines.append("OPTIMIZED ROUTE PLAN")
    output_lines.append("="*60)
    output_lines.append("")
    
    for team_id in sorted(team_schedule.keys()):
        team_line = f"Team/Crew {team_id}:"
        print(f"\n{team_line}")
        output_lines.append(team_line)
        
        for idx, td in enumerate(team_schedule[team_id], 1):
            site_names = [s.name for s in sites if s.id in td.site_ids]
            day_line = f"  Day {idx}: {len(td.site_ids)} sites ({td.route_minutes} minutes)"
            print(day_line)
            output_lines.append(day_line)
            
            for site_name in site_names:
                site_line = f"    - {site_name}"
                print(site_line)
                output_lines.append(site_line)
        
        output_lines.append("")
    
    # Summary
    total_sites = len(set(site_id for td in result.team_days for site_id in td.site_ids))
    summary_lines = [
        "="*60,
        f"Total sites scheduled: {total_sites}/{len(sites)}",
        f"Total team-days used: {len(result.team_days)}",
        "="*60
    ]
    
    print(f"\n{'='*60}")
    print(f"Total sites scheduled: {total_sites}/{len(sites)}")
    print(f"Total team-days used: {len(result.team_days)}")
    print(f"{'='*60}")
    
    output_lines.extend(summary_lines)
    
    # Write outputs to workspace output directory
    from pathlib import Path
    import json
    output_dir = Path("data") / "workspace" / WORKSPACE_NAME / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save human-readable text output
    output_file_txt = output_dir / "route_plan.txt"
    with open(output_file_txt, 'w') as f:
        f.write('\n'.join(output_lines))
    
    # Save complete JSON output with all data
    output_file_json = output_dir / "route_plan.json"
    result_dict = result.model_dump()  # Convert Pydantic model to dict
    with open(output_file_json, 'w') as f:
        json.dump(result_dict, f, indent=2)
    
    print(f"\n✓ Results saved to:")
    print(f"  - Text summary: {output_file_txt}")
    print(f"  - Complete JSON: {output_file_json}")

if __name__ == "__main__":
    main()
