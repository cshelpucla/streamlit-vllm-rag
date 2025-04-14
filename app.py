import dash
import dash_bootstrap_components as dbc
import os # Keep os import if needed for run command later

# Import components from the src package
from src.layout import create_layout
from src.callbacks import register_callbacks
# Configuration might be implicitly handled by callbacks now,
# but importing them ensures they are loaded if needed elsewhere.
from src.config import configure_llama_index, initialize_chroma

# --- Initialize Dash App ---
# Using Bootstrap themes for better styling
# Configure long callback manager with diskcache
from dash import DiskcacheManager
import diskcache
cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheManager(cache)

app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP], 
                suppress_callback_exceptions=True,
                background_callback_manager=long_callback_manager)
server = app.server # Expose Flask server for potential WSGI deployment

# --- App State Initialization ---
# Use app.server to store state accessible across callbacks
# Initialize these attributes to None or default values
app.server.directory_path = None
app.server.index = None
app.server.index_type = None # Added to track index type ('vector' or 'graph')

# Note: CHROMA_COLLECTION is now initialized within callbacks.py

# --- Configure LlamaIndex and ChromaDB (Optional Initial Setup) ---
# The original code configured these within callbacks.
# If you prefer to configure ONCE at startup (and settings are static),
# uncomment the following lines. Otherwise, configuration happens in callbacks.
# print("Performing initial LlamaIndex and ChromaDB setup...", flush=True)
# try:
#     EMBED_MODEL, LLM = configure_llama_index()
#     # The collection is now initialized and stored in callbacks.py
#     # COLLECTION = initialize_chroma() # This might be redundant now
#     print("Initial setup complete.", flush=True)
# except Exception as e:
#     print(f"Error during initial setup: {e}", flush=True)
    # Decide how to handle startup errors (e.g., exit, log, continue with limited functionality)

# --- App Layout ---
app.layout = create_layout()

# --- Register Callbacks ---
# The callbacks need access to the 'app' object to register themselves
# and potentially access app.server state.
register_callbacks(app)

# --- Run the App ---
if __name__ == '__main__':
    # Set debug=False for production
    # Use host='0.0.0.0' to make it accessible on the network
    app.run(debug=True, host='0.0.0.0', port=8050) # Default Dash port is 8050
