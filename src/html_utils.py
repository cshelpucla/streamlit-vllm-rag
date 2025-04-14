import os
import html
from dash import html as html_components
from pathlib import Path

def convert_file_to_html(file_path, output_dir='static/generated_html'):
    """
    Converts a text file to HTML format with styling and saves it in the specified output directory.
    
    Args:
        file_path (str): Path to the file to convert
        output_dir (str): Directory to save the HTML file
        
    Returns:
        str: Path to the generated HTML file relative to the server root
    """
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate a safe filename for the HTML output
        base_name = os.path.basename(file_path)
        safe_name = f"{base_name.replace('.', '_')}.html"
        output_path = os.path.join(output_dir, safe_name)
        
        # Read the original file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Escape HTML special characters
        escaped_content = html.escape(content)
        
        # Create styled HTML content
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{base_name}</title>
    <style>
        body {{ 
            font-family: monospace;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .file-container {{
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 10px;
            background-color: white;
            max-height: 80vh;
            overflow: auto;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        pre {{
            margin: 0;
            white-space: pre-wrap;
            word-break: keep-all;
        }}
        .file-path {{
            font-weight: bold;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="file-container">
        <div class="file-path">{file_path}</div>
        <pre>{escaped_content}</pre>
    </div>
</body>
</html>
"""
        
        # Write HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        # Return relative path that can be used in an href
        return f"/{output_path}"
        
    except Exception as e:
        print(f"Error converting file to HTML: {e}")
        return None
