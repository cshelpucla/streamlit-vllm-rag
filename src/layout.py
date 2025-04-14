import dash_bootstrap_components as dbc
from dash import html, dcc

def create_layout():
    """Creates the Dash application layout with a sidebar and main content area."""

    # Define the sidebar content (Steps 1 and 2)
    sidebar = dbc.Col([
        html.H4("Indexing Controls", className="text-center mb-3"),
        dbc.Card([
            dbc.CardHeader("Step 1: Select Python Code Directory"),
            dbc.CardBody([
                dcc.Upload(
                    id='upload-directory',
                    children=html.Div([
                        'Drag and Drop Directory or ',
                        html.A('Select Directory')
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px 0' # Adjusted margin
                    },
                    multiple=True
                ),
                html.Div(id='upload-status'),
                dbc.Input(
                    id="directory-path-input",
                    placeholder="Or type directory path here...",
                    type="text",
                    className="mt-2"
                ),
                html.Div(id='file-list-container', className="mt-3", style={'maxHeight': '150px', 'overflowY': 'auto'}), # Added scroll
            ])
        ], className="mb-4"),

        dbc.Card([
            dbc.CardHeader("Step 2: Index Python Files"),
            dbc.CardBody([
                dbc.Label("Select Indexing Method:"), # Added label
                dbc.RadioItems( # Added RadioItems for selection
                    options=[
                        {'label': 'Vector Store (ChromaDB)', 'value': 'vector'},
                        {'label': 'Property Graph (Simple)', 'value': 'graph'},
                    ],
                    value='vector', # Default value
                    id='indexing-method-radio',
                    inline=True, # Display options horizontally
                    className="mb-3" # Add margin below
                ),
                dbc.Button("Index Files", id="index-button", color="primary", className="w-100"), # Full width button
                html.Div(id='indexing-status', className="mt-3")
            ])
        ], className="mb-4"),
    ], width=4, className="bg-light p-4", style={'height': '100vh', 'overflowY': 'auto'}) # Sidebar styling

    # Define the main content area (Step 3)
    content = dbc.Col([
        html.H4("Query Your Codebase", className="text-center mb-3"),
        dbc.Card([
            dbc.CardHeader("Step 3: Query Python Code"),
            dbc.CardBody([
                dbc.Textarea(
                    id="query-input",
                    placeholder="Ask a question about your Python code...",
                    style={"height": "150px"} # Increased height
                ),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Submit Query", id="query-button", color="success", className="mt-3 w-100"), # Full width button
                    ], width=9),
                    dbc.Col([
                        dbc.Button("Cancel", id="cancel-query-button", color="danger", className="mt-3 w-100", disabled=True), # Cancel button
                    ], width=3),
                ]),
                # Add loading spinner for query execution
                dbc.Spinner(
                    id="query-spinner",
                    color="primary",
                    type="grow",
                    fullscreen=False,
                    children=html.Div(id="spinner-container", style={"height": "50px", "display": "none"}),
                    spinner_style={"width": "3rem", "height": "3rem"}
                ),
                html.Div(id='query-results', className="mt-4", style={'maxHeight': 'calc(100vh - 350px)', 'overflowY': 'auto'}) # Adjusted height and scroll
            ])
        ])
    ], width=8, className="p-4") # Content area padding

    # Combine sidebar and content within the main layout
    layout = dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Python Code RAG System (Refactored)", className="my-4 text-center"))
        ]),
        dbc.Row([
            sidebar,
            content
        ], className="g-0") # g-0 removes gutters between columns for seamless look
    ], fluid=True) # Use fluid container for full width

    return layout
