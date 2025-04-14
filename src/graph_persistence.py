import os
import pickle
from pathlib import Path

# Define default location to store property graph index
PROPERTY_GRAPH_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "property_graph_store")

def save_property_graph_index(index, file_name=None, directory=None):
    """
    Save the PropertyGraphIndex to disk for later use.
    
    Args:
        index: PropertyGraphIndex object to save
        file_name (str, optional): Name for the saved file. Defaults to 'property_graph_index.pickle'.
        directory (str, optional): Directory to save the file. Defaults to PROPERTY_GRAPH_DIR.
    
    Returns:
        str: Path to the saved file or None if save failed
    """
    if not index:
        print("No index to save!", flush=True)
        return None
        
    try:
        # Use default directory if none specified
        if directory is None:
            directory = PROPERTY_GRAPH_DIR
            
        # Use default filename if none specified
        if file_name is None:
            file_name = "property_graph_index.pickle"
        
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
        
        # Full path to save file
        save_path = os.path.join(directory, file_name)
        
        print(f"Saving PropertyGraphIndex to {save_path}...", flush=True)
        
        # Save the index using pickle
        with open(save_path, 'wb') as f:
            pickle.dump(index, f)
            
        print(f"PropertyGraphIndex saved successfully to {save_path}", flush=True)
        return save_path
    except Exception as e:
        print(f"Error saving PropertyGraphIndex: {e}", flush=True)
        return None
        
def load_property_graph_index(file_path=None):
    """
    Load a previously saved PropertyGraphIndex from disk.
    
    Args:
        file_path (str, optional): Path to the saved index file. If None, uses default path.
    
    Returns:
        PropertyGraphIndex: The loaded index or None if loading failed
    """
    try:
        # Use default path if none specified
        if file_path is None:
            file_path = os.path.join(PROPERTY_GRAPH_DIR, "property_graph_index.pickle")
            
        if not os.path.exists(file_path):
            print(f"PropertyGraphIndex file not found at {file_path}", flush=True)
            return None
            
        print(f"Loading PropertyGraphIndex from {file_path}...", flush=True)
        
        # Load the index using pickle
        with open(file_path, 'rb') as f:
            index = pickle.load(f)
            
        print(f"PropertyGraphIndex loaded successfully from {file_path}", flush=True)
        return index
    except Exception as e:
        print(f"Error loading PropertyGraphIndex: {e}", flush=True)
        return None

def find_most_recent_index():
    """
    Find the most recently created PropertyGraphIndex file in the storage directory.
    
    Returns:
        str: Path to the most recent index file or None if no index files exist
    """
    try:
        # Ensure directory exists
        if not os.path.exists(PROPERTY_GRAPH_DIR):
            print(f"PropertyGraph directory not found at {PROPERTY_GRAPH_DIR}", flush=True)
            return None
            
        # Get all pickle files in the directory
        pickle_files = [os.path.join(PROPERTY_GRAPH_DIR, f) for f in os.listdir(PROPERTY_GRAPH_DIR) 
                      if f.endswith('.pickle') and 'property_graph_index' in f]
        
        if not pickle_files:
            print(f"No PropertyGraphIndex files found in {PROPERTY_GRAPH_DIR}", flush=True)
            return None
            
        # Find the most recent file by modification time
        most_recent_file = max(pickle_files, key=os.path.getmtime)
        print(f"Found most recent PropertyGraphIndex file: {most_recent_file}", flush=True)
        return most_recent_file
    except Exception as e:
        print(f"Error finding most recent PropertyGraphIndex: {e}", flush=True)
        return None
        
def load_most_recent_index():
    """
    Load the most recently created PropertyGraphIndex from disk.
    
    Returns:
        PropertyGraphIndex: The loaded index or None if loading failed
    """
    most_recent_file = find_most_recent_index()
    if most_recent_file:
        return load_property_graph_index(most_recent_file)
    return None
        
def find_most_recent_index():
    """
    Find the most recently created PropertyGraphIndex file in the storage directory.
    
    Returns:
        str: Path to the most recent index file or None if no index files exist
    """
    try:
        # Ensure directory exists
        if not os.path.exists(PROPERTY_GRAPH_DIR):
            print(f"PropertyGraph directory not found at {PROPERTY_GRAPH_DIR}", flush=True)
            return None
            
        # Get all pickle files in the directory
        pickle_files = [os.path.join(PROPERTY_GRAPH_DIR, f) for f in os.listdir(PROPERTY_GRAPH_DIR) 
                      if f.endswith('.pickle') and 'property_graph_index' in f]
        
        if not pickle_files:
            print(f"No PropertyGraphIndex files found in {PROPERTY_GRAPH_DIR}", flush=True)
            return None
            
        # Find the most recent file by modification time
        most_recent_file = max(pickle_files, key=os.path.getmtime)
        print(f"Found most recent PropertyGraphIndex file: {most_recent_file}", flush=True)
        return most_recent_file
    except Exception as e:
        print(f"Error finding most recent PropertyGraphIndex: {e}", flush=True)
        return None
        
def load_most_recent_index():
    """
    Load the most recently created PropertyGraphIndex from disk.
    
    Returns:
        PropertyGraphIndex: The loaded index or None if loading failed
    """
    most_recent_file = find_most_recent_index()
    if most_recent_file:
        return load_property_graph_index(most_recent_file)
    return None
