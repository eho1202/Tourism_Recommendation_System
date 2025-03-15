import pandas as pd
from pathlib import Path

def load_csv(filename: str):
    """
    Load a CSV file from the datasets folder.
    """
    # Get the absolute path to the datasets folder
    datasets_path = Path(__file__).parent
    csv_path = datasets_path / filename

    # Load the CSV file
    return pd.read_csv(csv_path)