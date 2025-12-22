import pandas as pd
from pathlib import Path


def parse_excel_to_csv(
    file_path: str,
    output_path: str,
    column_mapping: dict[str, str] | None = None,
    sheet_name: str | None = None
) -> dict[str, Path]:
    """
    Parse an Excel file, rename columns according to mapping, and save to CSV files organized by state.
    
    Sites are grouped by state and written to separate folders:
    - data/workspace/{workspace}/input/{STATE}/addresses.csv
    
    Args:
        file_path: Path to the input Excel file
        output_path: Base path for output (e.g., data/workspace/{workspace}/input/addresses.csv)
                    State folders will be created under the parent directory
        column_mapping: Dict mapping standard field names to Excel column names.
                       Format: {standard_name: excel_column_name}
                       Example: {"site_id": "Location", "street1": "MyStreet1"}
                       If None, includes all columns with original names.
        sheet_name: Name of the Excel sheet to parse. If None, uses the first sheet (default pandas behavior).
        
    Returns:
        Dict mapping state names to their CSV file paths
        Example: {"LA": Path("data/workspace/foobar/input/LA/addresses.csv"), ...}
        
    Raises:
        FileNotFoundError: If the Excel file doesn't exist
        ValueError: If mapped columns don't exist in the Excel file or 'state' column is missing
    """
    # Read Excel file with openpyxl engine
    # If sheet_name is None, pandas will read the first sheet by default
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    
    # If column mapping is specified, validate and rename columns
    if column_mapping is not None:
        # Get the Excel column names from the mapping values
        excel_columns = list(column_mapping.values())
        
        # Check if all mapped columns exist in the Excel file
        missing_columns = set(excel_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(
                f"Columns not found in Excel file: {', '.join(missing_columns)}. "
                f"Available columns: {', '.join(df.columns)}"
            )
        
        # Select only the mapped columns
        df = df[excel_columns]
        
        # Create reverse mapping: excel_column_name -> standard_name
        reverse_mapping = {v: k for k, v in column_mapping.items()}
        
        # Rename columns to standard names
        df = df.rename(columns=reverse_mapping)
    
    # Validate that 'state' column exists
    if 'state' not in df.columns:
        raise ValueError(
            "Column 'state' is required for organizing sites by state. "
            "Make sure your column_mapping includes 'state'."
        )
    
    # Get base directory (parent of the output_path)
    base_output = Path(output_path)
    base_dir = base_output.parent
    
    # Group by state and save each state to its own folder
    state_files = {}
    states = df['state'].unique()
    
    for state in states:
        # Filter data for this state
        state_df = df[df['state'] == state]
        
        # Create state-specific directory
        state_dir = base_dir / str(state)
        state_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to state-specific CSV file
        state_file = state_dir / "addresses.csv"
        state_df.to_csv(state_file, index=False)
        
        state_files[str(state)] = state_file
        print(f"  ✓ Saved {len(state_df)} sites for state '{state}' to {state_file}")
    
    return state_files
