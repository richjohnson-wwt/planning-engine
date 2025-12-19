import pandas as pd
from pathlib import Path


def parse_excel_to_csv(
    file_path: str,
    output_path: str,
    column_mapping: dict[str, str] | None = None
) -> Path:
    """
    Parse an Excel file, rename columns according to mapping, and save to CSV.
    
    Args:
        file_path: Path to the input Excel file
        output_path: Path where the CSV file should be saved
        column_mapping: Dict mapping standard field names to Excel column names.
                       Format: {standard_name: excel_column_name}
                       Example: {"site_id": "Location", "street1": "MyStreet1"}
                       If None, includes all columns with original names.
        
    Returns:
        Path to the created CSV file
        
    Raises:
        FileNotFoundError: If the Excel file doesn't exist
        ValueError: If mapped columns don't exist in the Excel file
    """
    # Read Excel file with openpyxl engine
    df = pd.read_excel(file_path, engine='openpyxl')
    
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
    
    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    
    return output_file
