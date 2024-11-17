import pandas as pd
import numpy as np
from typing import Tuple, Dict, List
import logging

def compare_csv_files(file1_path: str, file2_path: str, tolerance: float = 0.01) -> Tuple[bool, Dict]:
    """
    Compare two CSV files for similarity.
    
    Args:
        file1_path: Path to first CSV file
        file2_path: Path to second CSV file
        tolerance: Floating point comparison tolerance (default: 0.01)
        
    Returns:
        Tuple containing:
        - Boolean indicating if files are similar
        - Dictionary with detailed comparison results
    """
    try:
        # Read CSV files
        df1 = pd.read_csv(file1_path)
        df2 = pd.read_csv(file2_path)
        
        results = {
            "are_similar": False,
            "differences": {},
            "shape_match": False,
            "columns_match": False,
            "data_match": False
        }
        
        # Compare basic properties
        if df1.shape != df2.shape:
            results["differences"]["shape"] = {
                "file1": df1.shape,
                "file2": df2.shape
            }
            return False, results
        else:
            results["shape_match"] = True
            
        # Compare column names
        if list(df1.columns) != list(df2.columns):
            results["differences"]["columns"] = {
                "file1_columns": list(df1.columns),
                "file2_columns": list(df2.columns),
                "missing_in_file1": list(set(df2.columns) - set(df1.columns)),
                "missing_in_file2": list(set(df1.columns) - set(df2.columns))
            }
            return False, results
        else:
            results["columns_match"] = True
            
        # Compare data by column
        data_differences = {}
        
        for column in df1.columns:
            if df1[column].dtype in [np.float64, np.float32, np.int64, np.int32]:
                # Numeric comparison with tolerance
                if not np.allclose(df1[column].fillna(0), 
                                 df2[column].fillna(0), 
                                 rtol=tolerance):
                    data_differences[column] = "Numeric values differ"
            else:
                # String/categorical comparison
                if not (df1[column].fillna("") == df2[column].fillna("")).all():
                    # Find specific differences
                    mask = df1[column].fillna("") != df2[column].fillna("")
                    diff_indices = mask[mask].index.tolist()
                    differences = {
                        idx: {
                            "file1": str(df1.loc[idx, column]),
                            "file2": str(df2.loc[idx, column])
                        }
                        for idx in diff_indices[:5]  # Show first 5 differences
                    }
                    data_differences[column] = differences
        
        if data_differences:
            results["differences"]["data"] = data_differences
            return False, results
        
        # If we get here, files are similar
        results["are_similar"] = True
        results["data_match"] = True
        return True, results
    
    except Exception as e:
        logging.error(f"Error comparing CSV files: {str(e)}")
        raise

def print_comparison_results(results: Dict) -> None:
    """
    Print formatted comparison results.
    
    Args:
        results: Dictionary containing comparison results
    """
    print("\nCSV Comparison Results:")
    print("-" * 50)
    
    print(f"Files are {'similar' if results['are_similar'] else 'different'}")
    print(f"Shape match: {results['shape_match']}")
    print(f"Columns match: {results['columns_match']}")
    print(f"Data match: {results['data_match']}")
    
    if results["differences"]:
        print("\nDifferences found:")
        for diff_type, details in results["differences"].items():
            print(f"\n{diff_type.capitalize()} differences:")
            print(details)

# Example usage
if __name__ == "__main__":
    try:
        file1_path = "./wordpress-to-shopify_20241116_131313.csv"
        file2_path = "file2.csv"
        
        are_similar, results = compare_csv_files(file1_path, file2_path)
        print_comparison_results(results)
        
    except Exception as e:
        print(f"Error: {str(e)}")