import json
import os
from pathlib import Path

def process_json_files(json_file_paths: list[str], output_dir: str = "output") -> None:
    """
    Process JSON files and organize their contents based on folder structure
    
    Args:
        json_file_paths: List of paths to JSON files
        output_dir: Output directory path
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    for json_path in json_file_paths:
        # Create directory based on JSON file location
        json_dir = os.path.join(output_dir, Path(json_path).parent.name)
        os.makedirs(json_dir, exist_ok=True)
        
        # Read JSON file
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Group data by folder
        grouped_data = {}
        for file_path, items in data.items():
            # Extract folder name from file path
            path_parts = Path(file_path).parts
            if len(path_parts) >= 3:  # Ensure we have enough path components
                folder_name = path_parts[2]  # Get the third component
                if folder_name not in grouped_data:
                    grouped_data[folder_name] = []
                grouped_data[folder_name].extend(items)
        
        # Write grouped data to separate JSON files
        for folder_name, items in grouped_data.items():
            output_file = os.path.join(json_dir, f"{folder_name}.json")
            with open(output_file, 'w') as f:
                json.dump(items, f, indent=2)

def main():
    # Example usage
    json_paths = ["./Dominion/pipeline_state.json"]
    output_directory = "neww"
    process_json_files(json_paths, output_directory)

if __name__ == "__main__":
    main()