\
import dash
from dash.dependencies import Input, Output, State, ALL
from dash import html, dcc, ctx # Ensure dcc and ctx are imported
import dash_bootstrap_components as dbc
import os
import base64
import io
import time
import threading
from threading import Event

# Import necessary functions and classes from your src package
from src.config import configure_llama_index, initialize_chroma
from src.indexing import perform_indexing, perform_graph_indexing # Import both indexing functions
from src.query import handle_query
from src.graph_persistence import load_most_recent_index # Import function to load most recent index
from src.file_explainer import explain_file # Import file explainer function

# Global variables to hold configured models and Chroma collection (initialized once)
# These are configured when the first callback needing them runs.
EMBED_MODEL = None
LLM = None
CHROMA_COLLECTION = None

# Global variables for query cancellation
QUERY_RUNNING = False
CANCEL_EVENT = Event()  # Used to signal query cancellation

def register_callbacks(app):
    """Registers all callbacks for the Dash application."""
    global EMBED_MODEL, LLM, CHROMA_COLLECTION

    def ensure_configuration():
        """Internal helper to configure LlamaIndex and ChromaDB if not already done."""
        global EMBED_MODEL, LLM, CHROMA_COLLECTION
        if EMBED_MODEL is None or LLM is None:
            print("Configuring LlamaIndex models...", flush=True)
            EMBED_MODEL, LLM = configure_llama_index()
            print("LlamaIndex models configured.", flush=True)
        if CHROMA_COLLECTION is None:
            print("Initializing ChromaDB collection...", flush=True)
            CHROMA_COLLECTION = initialize_chroma()
            print("ChromaDB collection initialized.", flush=True)
            
        # Try to load the most recent PropertyGraph index if one exists
        if not hasattr(app.server, 'index') or app.server.index is None:
            print("Looking for existing PropertyGraph index to load...", flush=True)
            graph_index = load_most_recent_index()
            if graph_index:
                print("Successfully loaded PropertyGraph index from disk.", flush=True)
                app.server.index = graph_index
                app.server.index_type = 'graph'
                return True
            else:
                print("No existing PropertyGraph index found or load failed.", flush=True)
                
        return False

    @app.callback(
        [Output('upload-status', 'children'),
         Output('file-list-container', 'children'),
         Output('directory-path-input', 'value')],
        [Input('upload-directory', 'contents')],
        [State('upload-directory', 'filename'),
         State('upload-directory', 'last_modified'),
         State('directory-path-input', 'value')]
    )
    def update_directory_path(list_of_contents, list_of_names, list_of_dates, current_path_input):
        ctx = dash.callback_context
        if not ctx.triggered:
            # No trigger, return default empty state
            return None, None, current_path_input or ""

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'upload-directory' and list_of_contents is not None:
            # Assuming the user uploads files from a single directory structure
            # We need to infer the common directory path.
            # This part is tricky with dcc.Upload as it gives file paths, not a directory.
            # A common approach is to take the directory of the *first* uploaded file.
            if list_of_names:
                # Heuristic: Assume the first file's path indicates the intended directory
                # This might need refinement depending on how users upload.
                # For simplicity, let's just display the names for now.
                # A better approach might involve asking the user to confirm the root.

                # Let's try to find a common parent directory if multiple files are uploaded
                common_path = os.path.commonpath([name for name in list_of_names if '/' in name or '\\\\' in name]) if list_of_names else None
                if not common_path and list_of_names: # Handle case where only files in root are uploaded
                     common_path = "." # Or decide on a different representation

                # Store the inferred path (or maybe just signal readiness)
                # For now, let's just update the input field if it's empty
                derived_path = common_path if common_path else (os.path.dirname(list_of_names[0]) if list_of_names else "")

                # Display uploaded file names
                file_list_items = [html.Li(name) for name in list_of_names]
                file_list_display = html.Ul(file_list_items)
                status_message = dbc.Alert(f"Received {len(list_of_names)} files. Using inferred path: '{derived_path}'. Please verify.", color="info")

                # Update the app state (directory path)
                app.server.directory_path = derived_path # Store the derived path

                # Update the input field only if it was empty or to reflect the new upload
                return status_message, file_list_display, derived_path

            else:
                return dbc.Alert("No files uploaded.", color="warning"), None, current_path_input

        # If triggered by something else or no content, keep existing state
        # This part might need adjustment based on desired behavior for manual path input
        return dash.no_update, dash.no_update, current_path_input


    @app.callback(
        Output('indexing-status', 'children'),
        [Input('index-button', 'n_clicks')],
        [State('directory-path-input', 'value'),
         State('indexing-method-radio', 'value')] # Get selected indexing method
    )
    def index_files(n_clicks, directory_path, indexing_method):
        if n_clicks is None or n_clicks < 1:
            return dash.no_update # Or "Click 'Index Files' to begin."

        # Ensure models/DB are configured before indexing
        ensure_configuration()

        # Use the path from the input field as the primary source
        final_directory_path = directory_path.strip() if directory_path else None

        if not final_directory_path:
             # Fallback to path derived from upload if input is empty
             final_directory_path = getattr(app.server, 'directory_path', None)

        if not final_directory_path:
            print("Indexing attempt failed: No directory path provided.", flush=True)
            return dbc.Alert("Error: Please select or enter a directory path.", color="danger")

        print(f"Starting indexing for directory: {final_directory_path} using method: {indexing_method}", flush=True)
        status_message = "Starting indexing..."
        index_object = None
        start_time = time.time()

        try:
            if indexing_method == 'vector':
                print("Using Vector Store (ChromaDB) indexing.", flush=True)
                status_message, index_object = perform_indexing(final_directory_path, CHROMA_COLLECTION, EMBED_MODEL)
                app.server.index_type = 'vector' if index_object else None
            elif indexing_method == 'graph':
                print("Using Property Graph (Simple) indexing.", flush=True)
                # Pass LLM and Embed Model from global scope (or Settings)
                status_message, index_object = perform_graph_indexing(final_directory_path, LLM, EMBED_MODEL)
                app.server.index_type = 'graph' if index_object else None
            else:
                status_message = "Error: Unknown indexing method selected."
                app.server.index_type = None

            # Store the index object in the app server state regardless of type
            app.server.index = index_object

            end_time = time.time()
            print(f"Indexing process completed in {end_time - start_time:.2f} seconds.", flush=True)

            if "Error" in status_message or "Warning" in status_message:
                 print(f"Indexing status: {status_message}", flush=True)
                 return dbc.Alert(status_message, color="danger" if "Error" in status_message else "warning")
            else:
                 print(f"Indexing successful: {status_message}", flush=True)
                 return dbc.Alert(status_message, color="success")

        except Exception as e:
            app.server.index = None
            app.server.index_type = None
            print(f"Unhandled exception during indexing: {e}", flush=True)
            # import traceback
            # print(traceback.format_exc(), flush=True)
            return dbc.Alert(f"An unexpected error occurred during indexing: {e}", color="danger")


    @app.callback(
        [
            Output('query-results', 'children'),
            Output('spinner-container', 'style'),
            Output('cancel-query-button', 'disabled')
        ],
        [Input('query-button', 'n_clicks'),
         Input('cancel-query-button', 'n_clicks')],
        [State('query-input', 'value')]
    )
    def run_query(query_n_clicks, cancel_n_clicks, query_text):
        global QUERY_RUNNING, CANCEL_EVENT
        
        # Get the ID of the component that triggered this callback
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'no-id'
        
        # Show spinner by making its container visible
        spinner_visible = {"height": "50px", "display": "block"}
        spinner_hidden = {"height": "50px", "display": "none"}
        
        # Handle cancel button click
        if triggered_id == 'cancel-query-button':
            if QUERY_RUNNING:
                print("Query cancellation requested", flush=True)
                CANCEL_EVENT.set()  # Signal cancellation
                return dbc.Alert("Query cancelled by user.", color="warning"), spinner_hidden, True
            return dash.no_update, dash.no_update, dash.no_update
            
        # Handle initial state or no clicks
        if query_n_clicks is None or query_n_clicks < 1:
            return "", spinner_hidden, True  # No query submitted yet, spinner hidden, cancel button disabled

        # Ensure models are configured before querying
        ensure_configuration()

        # Retrieve the index object and its type from app state
        index = getattr(app.server, 'index', None)
        index_type = getattr(app.server, 'index_type', None) # Get the stored index type

        if index is None:
            print("Query attempt failed: Index not available.", flush=True)
            return dbc.Alert("Error: Please index files before querying.", color="danger"), spinner_hidden, True

        if not query_text:
            print("Query attempt failed: No query text.", flush=True)
            return dbc.Alert("Please enter a query.", color="warning"), spinner_hidden, True

        print(f"Handling query with index type: {index_type}", flush=True)
        
        # Reset cancellation event
        CANCEL_EVENT.clear()
        
        try:
            # Mark query as running and enable cancel button
            QUERY_RUNNING = True
            
            # Process the query with the spinner visible
            print("Starting query execution - showing spinner", flush=True)
            
            # Run query with cancellation support
            def query_with_cancel():
                nonlocal result
                try:
                    result = handle_query(query_text, index, LLM, cancel_event=CANCEL_EVENT)
                except Exception as e:
                    result = dbc.Alert(f"An error occurred while processing your query: {str(e)}", color="danger")
                finally:
                    QUERY_RUNNING = False
            
            result = None
            query_thread = threading.Thread(target=query_with_cancel)
            query_thread.start()
            
            # Wait for the thread to complete or a timeout (if needed)
            query_thread.join(timeout=None)  # No timeout, will return when query completes
            
            print("Query execution complete - hiding spinner", flush=True)
            
            # Handle potential cancellation
            if CANCEL_EVENT.is_set():
                return dbc.Alert("Query cancelled by user.", color="warning"), spinner_hidden, True
                
            # Return result and hide spinner
            return result, spinner_hidden, True
            
        except Exception as e:
            QUERY_RUNNING = False
            print(f"Error during query execution: {e}", flush=True)
            # Hide spinner, show error, disable cancel button
            return dbc.Alert(f"An error occurred while processing your query: {str(e)}", color="danger"), spinner_hidden, True
            
    @app.callback(
        Output({"type": "file-explanation", "index": dash.MATCH}, "children"),
        Output({"type": "file-explanation", "index": dash.MATCH}, "style"),
        Input({"type": "explain-button", "index": dash.MATCH}, "n_clicks"),
        State({"type": "explain-button", "index": dash.MATCH}, "id"),
        prevent_initial_call=True
    )
    def show_file_explanation(n_clicks, button_id):
        """
        Handle clicks on "Explain" buttons to show file explanations.
        
        Args:
            n_clicks: Number of times the button has been clicked
            button_id: The ID of the button that was clicked, containing the file path
        
        Returns:
            Tuple of (explanation content, display style)
        """
        if n_clicks is None or n_clicks < 1:
            return dash.no_update, dash.no_update
        
        file_path = button_id["index"]
        print(f"Generating explanation for file: {file_path}", flush=True)
        
        # Show loading spinner
        explanation_content = [
            dbc.Spinner(spinner_style={"width": "3rem", "height": "3rem"}),
            html.Div("Generating explanation, please wait...", className="text-muted mt-2")
        ]
        # Show the explanation container
        container_style = {"display": "block", "padding": "10px", "backgroundColor": "#f0f7ff", "borderRadius": "5px"}
        
        # We need to return this immediately to show the loading state
        return explanation_content, container_style
        
    @app.callback(
        Output({"type": "file-explanation", "index": dash.MATCH}, "children", allow_duplicate=True),
        Input({"type": "explain-button", "index": dash.MATCH}, "n_clicks"),
        State({"type": "explain-button", "index": dash.MATCH}, "id"),
        prevent_initial_call=True,
        background=True,
        running=[
            (Output({"type": "explain-button", "index": dash.MATCH}, "disabled"), True, False)
        ]
    )
    def generate_file_explanation(n_clicks, button_id):
        """
        Generate an explanation for the file using the vLLM-based file explainer.
        This is a separate callback that runs in the background.
        
        Args:
            n_clicks: Number of times the button has been clicked
            button_id: The ID of the button that was clicked, containing the file path
            
        Returns:
            Content for the explanation container
        """
        if n_clicks is None or n_clicks < 1:
            raise dash.exceptions.PreventUpdate
            
        file_path = button_id["index"]
        print(f"Processing explanation for file: {file_path}", flush=True)
        
        try:
            # Call the file explainer
            explanation_data, error = explain_file(file_path)
            
            if error:
                print(f"Error explaining file {file_path}: {error}", flush=True)
                return [
                    html.H5("Error Generating Explanation", className="text-danger"),
                    html.P(error)
                ]
            
            print(f"Successfully generated explanation for {file_path}", flush=True)
            
            return [
                html.H5("File Explanation", className="mb-3"),
                html.Div([
                    html.Strong("File: "), html.Span(explanation_data["file_name"]),
                    html.Br(),
                    html.Strong("Type: "), html.Span(explanation_data["file_type"]),
                    html.Br(),
                    html.Strong("Processing Time: "), html.Span(f"{explanation_data['processing_time']} seconds")
                ], className="mb-3"),
                html.Hr(),
                dcc.Markdown(explanation_data["explanation"], className="explanation-text")
            ]
            
        except Exception as e:
            print(f"Exception while generating explanation: {str(e)}", flush=True)
            return [
                html.H5("Error Generating Explanation", className="text-danger"),
                html.P(f"An unexpected error occurred: {str(e)}")
            ]
