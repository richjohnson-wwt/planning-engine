"""
Team Schedule PDF Generation

Generates professional PDF schedules for individual teams based on planning results.
Each schedule includes route assignments, site details, and contact information.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from planning_engine.core.workspace import get_workspace_path
from planning_engine.models import Team


def load_latest_plan_result(workspace_name: str, state_abbr: str) -> Optional[Dict]:
    """
    Load the latest planning result JSON for a workspace and state.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation (e.g., "LA", "NC")
        
    Returns:
        Dictionary with metadata and result, or None if not found
    """
    workspace_path = get_workspace_path(workspace_name)
    output_dir = workspace_path / "output" / state_abbr
    
    if not output_dir.exists():
        return None
    
    # Find all JSON result files
    json_files = [
        f for f in output_dir.iterdir()
        if f.is_file() and f.name.startswith("route_plan_") and f.suffix == ".json"
    ]
    
    if not json_files:
        return None
    
    # Get the most recent file by modification time
    latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
    
    try:
        with open(latest_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading plan result: {e}")
        return None


def load_team_info(workspace_name: str, state_abbr: str, team_id: str) -> Optional[Team]:
    """
    Load team information from teams.csv.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        team_id: Team ID to look up
        
    Returns:
        Team object or None if not found
    """
    import pandas as pd
    
    workspace_path = get_workspace_path(workspace_name)
    teams_file = workspace_path / "cache" / state_abbr / "teams.csv"
    
    if not teams_file.exists():
        return None
    
    try:
        df = pd.read_csv(teams_file)
        team_row = df[df['team_id'] == team_id]
        
        if team_row.empty:
            return None
        
        # Convert to Team model
        team_data = team_row.iloc[0].to_dict()
        
        # Handle NaN values - convert to appropriate defaults based on field type
        for key, value in team_data.items():
            if pd.isna(value):
                # notes field requires a string, not None
                if key == 'notes':
                    team_data[key] = ''
                else:
                    team_data[key] = None
        
        return Team(**team_data)
    except Exception as e:
        print(f"Error loading team info: {e}")
        return None


def generate_team_schedule_pdf(
    workspace_name: str,
    state_abbr: str,
    team_id: str,
    output_path: Path
) -> bool:
    """
    Generate a PDF schedule for a specific team.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        team_id: Team ID to generate schedule for
        output_path: Path where PDF should be saved
        
    Returns:
        True if successful, False otherwise
    """
    # Load planning results
    plan_data = load_latest_plan_result(workspace_name, state_abbr)
    if not plan_data:
        print(f"No planning results found for {workspace_name}/{state_abbr}")
        return False
    
    # Load team information
    team_info = load_team_info(workspace_name, state_abbr, team_id)
    if not team_info:
        print(f"Team {team_id} not found")
        return False
    
    # Extract team days for this team
    result = plan_data.get('result', {})
    metadata = plan_data.get('metadata', {})
    team_days = result.get('team_days', [])
    
    # Filter team days for this specific team
    # Try matching by team_label first (e.g., "C1-T1", "T1")
    # If no match, try matching by numeric team_id (for compatibility)
    team_routes = [td for td in team_days if td.get('team_label') == team_id]
    
    if not team_routes:
        # Try matching by numeric team_id
        try:
            numeric_team_id = int(team_id)
            team_routes = [td for td in team_days if td.get('team_id') == numeric_team_id]
        except (ValueError, TypeError):
            pass
    
    if not team_routes:
        print(f"No routes found for team {team_id}")
        return False
    
    # Create PDF
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Container for PDF elements
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=6,
        spaceBefore=12
    )
    
    normal_style = styles['Normal']
    
    # Title
    story.append(Paragraph("Team Route Schedule", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Team Information Section
    story.append(Paragraph("Team Information", heading_style))
    
    team_info_data = [
        ['Team ID:', team_id],
        ['Team Name:', team_info.team_name],
        ['City:', team_info.city],
        ['Contact:', team_info.contact_name or 'N/A'],
        ['Phone:', team_info.contact_phone or 'N/A'],
        ['Email:', team_info.contact_email or 'N/A'],
    ]
    
    if team_info.cluster_id is not None:
        team_info_data.append(['Cluster:', f'Cluster {team_info.cluster_id}'])
    
    team_info_table = Table(team_info_data, colWidths=[1.5*inch, 4.5*inch])
    team_info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1f2937')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(team_info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Planning Information
    story.append(Paragraph("Planning Details", heading_style))
    
    planning_info_data = [
        ['Workspace:', metadata.get('workspace', 'N/A')],
        ['State:', metadata.get('state_abbr', 'N/A')],
        ['Generated:', datetime.fromisoformat(metadata.get('timestamp', '')).strftime('%Y-%m-%d %H:%M') if metadata.get('timestamp') else 'N/A'],
        ['Total Routes:', str(len(team_routes))],
        ['Max Route Duration:', f"{metadata.get('max_route_minutes', 480)} minutes"],
    ]
    
    planning_info_table = Table(planning_info_data, colWidths=[1.5*inch, 4.5*inch])
    planning_info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1f2937')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(planning_info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Route Details
    story.append(Paragraph("Route Assignments", heading_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Sort routes by date if available
    team_routes_sorted = sorted(team_routes, key=lambda x: x.get('date', ''))
    
    for idx, route in enumerate(team_routes_sorted, 1):
        # Route header
        route_date = route.get('date', 'N/A')
        route_header = f"Route {idx}"
        if route_date != 'N/A':
            route_header += f" - {route_date}"
        
        story.append(Paragraph(route_header, ParagraphStyle(
            'RouteHeader',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=6,
            spaceBefore=8
        )))
        
        # Route summary
        service_mins = route.get('service_minutes', 0)
        travel_mins = route.get('travel_minutes', 0)
        route_mins = route.get('route_minutes', 0)
        break_mins = route.get('break_minutes', 0)
        num_sites = len(route.get('site_ids', []))
        
        summary_data = [
            ['Sites:', str(num_sites)],
            ['Service Time:', f"{service_mins} min"],
            ['Travel Time:', f"{travel_mins} min"],
            ['Break Time:', f"{break_mins} min"],
            ['Total Route Time:', f"{route_mins} min ({route_mins/60:.1f} hours)"],
        ]
        
        summary_table = Table(summary_data, colWidths=[1.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#4b5563')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 0.1*inch))
        
        # Sites table
        sites = route.get('sites', [])
        if sites:
            # Create a small paragraph style for table cells
            cell_style = ParagraphStyle(
                'CellStyle',
                parent=normal_style,
                fontSize=8,
                leading=10,
                wordWrap='CJK'
            )
            
            site_data = [['#', 'Site ID', 'Name', 'Address', 'Service (min)']]
            
            for site_idx, site in enumerate(sites, 1):
                # Use Paragraph for Name and Address to enable text wrapping
                name_para = Paragraph(site.get('name', 'N/A'), cell_style)
                address_para = Paragraph(site.get('address', 'N/A'), cell_style)
                
                site_data.append([
                    str(site_idx),
                    site.get('id', 'N/A'),
                    name_para,
                    address_para,
                    str(site.get('service_minutes', 60))
                ])
            
            sites_table = Table(site_data, colWidths=[0.3*inch, 0.8*inch, 1.5*inch, 2.8*inch, 0.8*inch])
            sites_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                
                # Data rows
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1f2937')),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (-1, 1), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
                
                # Padding - increased for better spacing
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(sites_table)
        
        story.append(Spacer(1, 0.2*inch))
        
        # Add page break between routes (except for the last one)
        if idx < len(team_routes_sorted):
            story.append(PageBreak())
    
    # Build PDF
    try:
        doc.build(story)
        return True
    except Exception as e:
        print(f"Error building PDF: {e}")
        return False


def generate_all_team_schedules(
    workspace_name: str,
    state_abbr: str,
    output_dir: Optional[Path] = None
) -> Dict[str, Path]:
    """
    Generate PDF schedules for all teams in a state.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        output_dir: Optional output directory (defaults to workspace/output/{state}/schedules)
        
    Returns:
        Dictionary mapping team_id to PDF file path
    """
    import pandas as pd
    
    # Default output directory
    if output_dir is None:
        workspace_path = get_workspace_path(workspace_name)
        output_dir = workspace_path / "output" / state_abbr / "schedules"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load teams list
    workspace_path = get_workspace_path(workspace_name)
    teams_file = workspace_path / "cache" / state_abbr / "teams.csv"
    
    if not teams_file.exists():
        print(f"No teams file found: {teams_file}")
        return {}
    
    try:
        df = pd.read_csv(teams_file)
        team_ids = df['team_id'].tolist()
    except Exception as e:
        print(f"Error reading teams file: {e}")
        return {}
    
    # Generate schedules
    generated_files = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for team_id in team_ids:
        pdf_filename = f"schedule_{team_id}_{timestamp}.pdf"
        pdf_path = output_dir / pdf_filename
        
        success = generate_team_schedule_pdf(
            workspace_name,
            state_abbr,
            team_id,
            pdf_path
        )
        
        if success:
            generated_files[team_id] = pdf_path
            print(f"✓ Generated schedule for {team_id}: {pdf_path}")
        else:
            print(f"✗ Failed to generate schedule for {team_id}")
    
    return generated_files
