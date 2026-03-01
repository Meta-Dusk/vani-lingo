import os, json

def load_json_file(file_name: str):
    def debug_print(msg: str) -> None:
        print(f"[load_json_file]: {msg}")
    
    # Gather all potential base directories for assets
    potential_dirs = [
        # The official Flet variable (often absolute on mobile)
        os.getenv("FLET_ASSETS_DIR"),
        
        # Relative to the script (PC dev)
        os.path.join(os.path.dirname(__file__), "assets"),
        
        # Standard relative path
        "assets"
    ]
    
    debug_print(f"Attempting to find file: {file_name}")
    
    # Filter out None values and look for the file
    for directory in filter(None, potential_dirs):
        json_path = os.path.join(directory, file_name)
        
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    debug_print(f"Successfully loaded data from: {json_path}")
                    return json.load(f)
            except Exception as e:
                debug_print(f"Error reading {json_path}: {e}")
                continue