import os
import json

def extract_structure(base_path, exclude_dirs=None):
    """
    Recursively extracts the directory structure and file contents starting from base_path,
    excluding specified directories.
    
    Args:
        base_path (str): The root directory path to start extraction.
        exclude_dirs (set, optional): A set of directory names to exclude. Defaults to None.
        
    Returns:
        dict: A nested dictionary representing the directory structure and file contents.
    """
    if exclude_dirs is None:
        exclude_dirs = set()
    structure = {}
    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path):
            if item in exclude_dirs:
                print(f"Skipping directory: {item_path}")
                continue
            # Recursively extract subdirectories
            structure[item] = extract_structure(item_path, exclude_dirs)
        else:
            # Read file content
            if "package" in item:
                print(f"Skipping file: {item_path}")
                continue
            try:
                with open(item_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (UnicodeDecodeError, PermissionError) as e:
                # If the file is binary or unreadable, represent content as None or a placeholder
                print(f"Cannot read file: {item_path}. Reason: {e}")
                content = None
            structure[item] = content
    return structure

def main():
    # Specify the path to the project directory you want to extract
    PROJECT_PATH = "./"  # Change this to your project directory
    
    # Specify directories to exclude
    EXCLUDE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build","exclude"}  # Add or remove as needed
    
    if not os.path.exists(PROJECT_PATH):
        print(f"Error: The directory '{PROJECT_PATH}' does not exist.")
        return
    
    # Extract the structure with exclusions
    project_structure = extract_structure(PROJECT_PATH, exclude_dirs=EXCLUDE_DIRS)
    
    # Serialize the structure to a JSON file for easy viewing
    output_file = "exclude/project_structure.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(project_structure, f, ensure_ascii=False, indent=4)
        print(f"Project structure has been extracted and saved to '{output_file}'.")
    except IOError as e:
        print(f"Failed to write to '{output_file}'. Reason: {e}")

if __name__ == "__main__":
    main()
