"""
File explainer module using vLLM to generate explanations of code files.

This module provides functions to take a file, send its contents to an LLM 
using vLLM request syntax, and receive back an explanation of what the file does.
"""

import os
import json
import requests
import time
from typing import Dict, Any, Optional, List, Tuple
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default vLLM server settings - can be overridden with environment variables
VLLM_API_URL = os.environ.get("VLLM_API_URL", "http://localhost:8000/v1/completions")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "meta-llama/Llama-2-13b-chat-hf")
VLLM_MAX_TOKENS = int(os.environ.get("VLLM_MAX_TOKENS", "15000"))
VLLM_TEMPERATURE = float(os.environ.get("VLLM_TEMPERATURE", "0.2"))


def read_file_content(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Read the content of a file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        Tuple of (file content, error message if any)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, None
    except Exception as e:
        error_msg = f"Error reading file {file_path}: {str(e)}"
        logger.error(error_msg)
        return "", error_msg


def determine_file_type(file_path: str) -> str:
    """
    Determine the type of file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File type descriptor string
    """
    extension = os.path.splitext(file_path)[1].lower()
    
    file_types = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.html': 'HTML',
        '.css': 'CSS',
        '.sql': 'SQL',
        '.json': 'JSON',
        '.md': 'Markdown',
        '.txt': 'Text',
        '.sh': 'Shell Script',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.c': 'C',
        '.cpp': 'C++',
        '.java': 'Java',
        '.rb': 'Ruby',
    }
    
    return file_types.get(extension, 'Unknown')


def create_explanation_prompt(file_content: str, file_path: str, file_type: str) -> str:
    """
    Create a prompt for the LLM to explain the file content.
    
    Args:
        file_content: The content of the file to explain
        file_path: The path to the file
        file_type: The type of the file
        
    Returns:
        A prompt string for the LLM
    """
    file_name = os.path.basename(file_path)
    
    prompt = f"""As an expert software developer, please analyze and explain the following {file_type} code file named '{file_name}'.
Focus on:
1. The overall purpose and functionality of this code
2. The main components and their relationships
3. Key functions/methods and what they do
4. Any important design patterns or architectural choices
5. Dependencies and external integrations
6. Potential issues or areas for improvement

Here is the file content:

```{file_type.lower()}
{file_content}
```

Please provide a comprehensive but concise explanation that would help a developer understand this code.
"""
    return prompt


def send_vllm_request(prompt: str, 
                      api_url: str = VLLM_API_URL,
                      model: str = VLLM_MODEL,
                      max_tokens: int = VLLM_MAX_TOKENS,
                      temperature: float = VLLM_TEMPERATURE) -> Tuple[Optional[str], Optional[str]]:
    """
    Send a request to the vLLM API and get the response.
    
    Args:
        prompt: The prompt to send to the LLM
        api_url: URL of the vLLM API endpoint
        model: Name of the model to use
        max_tokens: Maximum number of tokens to generate
        temperature: Temperature parameter for generation
        
    Returns:
        Tuple of (response text, error message if any)
    """
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.info(f"Sending request to vLLM API at {api_url}")
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            error_msg = f"API request failed with status code {response.status_code}: {response.text}"
            logger.error(error_msg)
            return None, error_msg
        
        response_data = response.json()
        
        # Extract the generated text based on vLLM response format
        if "choices" in response_data and len(response_data["choices"]) > 0:
            generated_text = response_data["choices"][0].get("text", "")
            return generated_text, None
        else:
            error_msg = "Unexpected response format from API"
            logger.error(error_msg)
            return None, error_msg
            
    except Exception as e:
        error_msg = f"Error calling vLLM API: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


def explain_file(file_path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Generate an explanation for a file by sending its content to an LLM through vLLM.
    
    Args:
        file_path: Path to the file to explain
        
    Returns:
        Tuple of (explanation data dictionary, error message if any)
    """
    # Check if file exists
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    # Read file content
    file_content, error = read_file_content(file_path)
    if error:
        return None, error
    
    # Skip empty files
    if not file_content.strip():
        return None, f"File is empty: {file_path}"
    
    # Determine file type
    file_type = determine_file_type(file_path)
    
    # Create prompt
    prompt = create_explanation_prompt(file_content, file_path, file_type)
    
    # Send request to vLLM
    start_time = time.time()
    explanation, error = send_vllm_request(prompt)
    end_time = time.time()
    
    if error:
        return None, error
    
    # Create result dictionary
    result = {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "file_type": file_type,
        "explanation": explanation,
        "processing_time": round(end_time - start_time, 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return result, None


def explain_multiple_files(file_paths: List[str]) -> Dict[str, Any]:
    """
    Generate explanations for multiple files.
    
    Args:
        file_paths: List of file paths to explain
        
    Returns:
        Dictionary with explanation results and any errors
    """
    results = {
        "successful": [],
        "failed": [],
        "total_files": len(file_paths),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    for file_path in file_paths:
        explanation_data, error = explain_file(file_path)
        
        if error:
            results["failed"].append({
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "error": error
            })
        else:
            results["successful"].append(explanation_data)
    
    results["success_count"] = len(results["successful"])
    results["failure_count"] = len(results["failed"])
    
    return results


def save_explanations_to_file(explanations: Dict[str, Any], output_path: str) -> Tuple[bool, Optional[str]]:
    """
    Save explanation results to a JSON file.
    
    Args:
        explanations: Explanation results dictionary
        output_path: Path to save the JSON file
        
    Returns:
        Tuple of (success boolean, error message if any)
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(explanations, f, indent=2)
        
        return True, None
    except Exception as e:
        error_msg = f"Error saving explanations to {output_path}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def batch_process_directory(directory_path: str, 
                           output_path: str = None, 
                           file_pattern: str = ".py") -> Dict[str, Any]:
    """
    Process all matching files in a directory and generate explanations.
    
    Args:
        directory_path: Directory containing files to process
        output_path: Path to save the JSON results (optional)
        file_pattern: File extension pattern to match
        
    Returns:
        Dictionary with explanation results
    """
    if not os.path.isdir(directory_path):
        return {"error": f"Directory not found: {directory_path}"}
    
    # Find all matching files
    file_paths = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith(file_pattern):
                file_paths.append(os.path.join(root, file))
    
    if not file_paths:
        return {"error": f"No {file_pattern} files found in {directory_path}"}
    
    # Generate explanations
    explanations = explain_multiple_files(file_paths)
    
    # Save results if output path is provided
    if output_path:
        success, error = save_explanations_to_file(explanations, output_path)
        if not success:
            explanations["save_error"] = error
    
    return explanations


# Example usage if this script is run directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate explanations for code files using vLLM")
    parser.add_argument("--file", type=str, help="Path to a single file to explain")
    parser.add_argument("--dir", type=str, help="Directory containing files to explain")
    parser.add_argument("--pattern", type=str, default=".py", help="File pattern to match in directory mode")
    parser.add_argument("--output", type=str, help="Path to save explanation results as JSON")
    parser.add_argument("--url", type=str, help="vLLM API URL (overrides environment variable)")
    parser.add_argument("--model", type=str, help="Model to use (overrides environment variable)")
    
    args = parser.parse_args()
    
    # Override settings if provided
    if args.url:
        VLLM_API_URL = args.url
    if args.model:
        VLLM_MODEL = args.model
    
    results = None
    
    if args.file:
        explanation_data, error = explain_file(args.file)
        if error:
            results = {"error": error}
        else:
            results = explanation_data
    elif args.dir:
        results = batch_process_directory(args.dir, args.output, args.pattern)
    else:
        print("Please provide either --file or --dir argument")
        parser.print_help()
        exit(1)
    
    # If output path not provided or we're in single file mode without an output path
    if not args.output or (args.file and not args.output):
        print(json.dumps(results, indent=2))
