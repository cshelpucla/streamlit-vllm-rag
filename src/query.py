\
import time
import os
import asyncio
import nest_asyncio
import dash_bootstrap_components as dbc
# Make sure dcc is imported
from dash import html, dcc
from llama_index.core import Settings # Import Settings to potentially access configured LLM
# Correct the import path for Response again
from llama_index.core.base.response.schema import Response
# Import the HTML conversion utility
from src.html_utils import convert_file_to_html
# Import the file explainer
from src.file_explainer import explain_file

# Apply nest_asyncio to enable nested event loops
nest_asyncio.apply()

def handle_query(query_text, index, llm, cancel_event=None):
    """
    Processes a user query using the LlamaIndex query engine and displays results with sources.
    Works with both VectorStoreIndex and PropertyGraphIndex.

    Args:
        query_text (str): The user's query.
        index (Union[VectorStoreIndex, PropertyGraphIndex]): The LlamaIndex index object.
        llm: The configured LLM instance from LlamaIndex.
        cancel_event (threading.Event, optional): Event to signal query cancellation.

    Returns:
        dash component: HTML Div containing the query results, sources, or an error alert.
    """
    if not query_text:
        print("Query attempt failed: No query text provided.", flush=True)
        return dbc.Alert("Please enter a query.", color="warning")

    if index is None:
        print("Error: Index is None. Aborting query.", flush=True)
        return dbc.Alert("Error: Please index the files before querying.", color="danger")

    print(f"Index type: {type(index)}. Proceeding with query.", flush=True)
    try:
        # Configure query engine.
        # For PropertyGraphIndex, we might need specific retriever modes or query kwargs.
        # Let's try the default first. LlamaIndex often handles this transparently.
        # If issues arise, we might need: index.as_query_engine(retriever_mode="graph", ...)
        query_engine_kwargs = {
            "llm": llm,
            "similarity_top_k": 3, # Relevant for vector index, might be ignored/different for graph
            "include_metadata": True # Ensure metadata (like file_path) is included if available
        }
        # Add specific kwargs if it's a graph index (adjust based on LlamaIndex version/behavior)
        # from llama_index.core import PropertyGraphIndex # Import if needed for type check
        # if isinstance(index, PropertyGraphIndex):
        #     query_engine_kwargs["retriever_mode"] = "graph" # Example, check documentation
        #     query_engine_kwargs["verbose"] = True # Example for debugging graph queries

        print(f"Creating query engine with kwargs: {query_engine_kwargs}", flush=True)
        query_engine = index.as_query_engine(**query_engine_kwargs)
        print("Query engine created.", flush=True)

        # Perform query using async approach
        print(f"Performing query: '{query_text}'", flush=True)
        print("--- Calling LLM via query_engine.aquery() --- ", flush=True)
        start_time = time.time()
        
        # Check for cancellation before starting query
        if cancel_event and cancel_event.is_set():
            print("Query cancelled before execution", flush=True)
            return dbc.Alert("Query cancelled by user.", color="warning")
            
        # Define an async function that includes cancellation checks
        async def run_query_with_cancellation():
            # Create a task for the query
            query_task = asyncio.create_task(query_engine.aquery(query_text))
            
            # While the query is running, periodically check for cancellation
            while not query_task.done():
                if cancel_event and cancel_event.is_set():
                    print("Cancellation requested during query execution", flush=True)
                    # Try to cancel the asyncio task
                    query_task.cancel()
                    return None
                # Wait a short time before checking again
                await asyncio.sleep(0.1)
                
            # If we get here, the task completed without cancellation
            return await query_task
            
        # Run the query with cancellation support
        response_or_none = asyncio.get_event_loop().run_until_complete(run_query_with_cancellation())
        
        # Check if the query was cancelled
        if cancel_event and cancel_event.is_set():
            end_time = time.time()
            print(f"Query cancelled after {end_time - start_time:.2f} seconds", flush=True)
            return dbc.Alert("Query cancelled by user.", color="warning")
            
        # If we get here, we have a valid response
        response: Response = response_or_none
        end_time = time.time()
        print("--- LLM call via query_engine.aquery() completed --- ", flush=True)
        print(f"Query completed in {end_time - start_time:.2f} seconds.", flush=True)
        # print(f"Raw response object: {response}", flush=True) # More detailed logging if needed

        # Extract source file paths (might work differently for graph nodes)
        source_files = set() # Use a set to store unique file paths
        if response.source_nodes:
            print(f"Found {len(response.source_nodes)} source nodes.", flush=True)
            for node_with_score in response.source_nodes:
                node = node_with_score.node
                # Graph nodes might have different metadata structure
                file_path = node.metadata.get('file_path', None) # Safely get file_path
                if file_path:
                    source_files.add(file_path)
                    # print(f"  Source Node Score: {node_with_score.score:.4f}, File: {file_path}", flush=True)
                else:
                    # Log other potentially useful metadata for graph nodes
                    print(f"  Warning: Source node missing 'file_path'. Metadata: {node.metadata}", flush=True)
        else:
            print("No source nodes found in the response.", flush=True)

        # Create styled list items for source files with clickable links
        source_list_items = []
        if source_files:
            # Ensure static directory exists for HTML files
            static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'generated_html')
            os.makedirs(static_dir, exist_ok=True)
            
            for file in sorted(list(source_files)):
                try:
                    # Convert file to HTML if it exists
                    if os.path.exists(file):
                        html_path = convert_file_to_html(file)
                        # Create a card with a clickable link and explain button
                        source_card = dbc.Card(
                            dbc.CardBody([
                                dbc.Row([
                                    # File link column
                                    dbc.Col([
                                        html.A(
                                            [
                                                html.I(className="fas fa-file-code mr-2"),  # File icon
                                                html.Code(file, className="text-monospace")  # File path in monospace font
                                            ],
                                            href=html_path,  # Link to generated HTML
                                            target="_blank",  # Open in new tab
                                            className="text-decoration-none",  # Remove underline
                                            title="Click to view file contents"  # Tooltip
                                        )
                                    ], width=8),  # Take up 8/12 of the row
                                    
                                    # Explain button column
                                    dbc.Col([
                                        dbc.Button(
                                            [html.I(className="fas fa-lightbulb mr-1"), "Explain"],
                                            id={"type": "explain-button", "index": file},
                                            color="info",
                                            size="sm",
                                            className="float-right"
                                        )
                                    ], width=4)  # Take up 4/12 of the row
                                ]),
                                
                                # Container for explanation, initially hidden
                                html.Div(
                                    id={"type": "file-explanation", "index": file},
                                    style={"display": "none"},
                                    className="mt-3"
                                )
                            ]),
                            className="mb-2 p-2",  # Add margin and padding
                            style={'backgroundColor': '#f8f9fa'}  # Light background color
                        )
                    else:
                        # File doesn't exist, show non-clickable version
                        source_card = dbc.Card(
                            dbc.CardBody([
                                html.I(className="fas fa-exclamation-triangle mr-2 text-warning"),
                                html.Code(file, className="text-monospace"),
                                html.Small(" (file not found)", className="text-muted ml-2")
                            ]),
                            className="mb-2 p-2",
                            style={'backgroundColor': '#f8f9fa'}
                        )
                except Exception as e:
                    print(f"Error processing source file {file}: {e}", flush=True)
                    # Create a card with error message
                    source_card = dbc.Card(
                        dbc.CardBody([
                            html.Code(file, className="text-monospace"),
                            html.Small(f" (error: {str(e)})", className="text-danger ml-2")
                        ]),
                        className="mb-2 p-2",
                        style={'backgroundColor': '#fff0f0'}  # Light red background for errors
                    )
                
                source_list_items.append(html.Li(source_card, style={'listStyleType': 'none'}))  # Remove bullet points
        else:
            # Provide more context if no file paths found, especially for graph index
            source_list_items.append(html.Li("No specific source files identified (metadata might differ for graph index)."))


        # Display results and sources
        return html.Div([
            html.H5("Query Result:"),
            html.P(f"(Responded in {end_time - start_time:.2f} seconds)"),
            # Use dcc.Markdown to render the response string as HTML
            dbc.Card(dbc.CardBody(dcc.Markdown(str(response.response), dangerously_allow_html=True))),
            html.H6("Sources:", className="mt-4 mb-2"), # Add margin
            # Use a Div instead of Ul for cleaner rendering without default list styling
            html.Div(source_list_items)
        ])
    except Exception as e:
        print(f"Error processing query: {e}", flush=True)
        # import traceback
        # print(traceback.format_exc(), flush=True) # Uncomment for detailed traceback
        return dbc.Alert(f"Error processing query: {e}", color="danger")

