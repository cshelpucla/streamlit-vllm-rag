import ast
import os
from typing import Dict, List, Any, Optional


class PythonAstParser:
    """
    A parser that uses the Python AST module to analyze Python code files and extract
    structured information about classes, functions, methods, and their relationships.
    """
    
    def __init__(self):
        self.file_info = {}
        
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a Python file and extract its structure using AST.
        
        Args:
            file_path (str): Path to the Python file to parse
            
        Returns:
            Dict[str, Any]: Structured information about the file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                code = file.read()
                
            # Parse the code into an AST
            tree = ast.parse(code)
            
            # Extract file-level information
            file_info = {
                'path': file_path,
                'name': os.path.basename(file_path),
                'imports': [],
                'classes': [],
                'functions': [],
                'doc_string': ast.get_docstring(tree),
            }
            
            # First, extract top-level definitions directly from the module body
            for node in tree.body:
                # Extract top-level imports
                if isinstance(node, ast.Import):
                    for name in node.names:
                        file_info['imports'].append({
                            'name': name.name,
                            'alias': name.asname
                        })
                        
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for name in node.names:
                        file_info['imports'].append({
                            'name': f"{module}.{name.name}",
                            'alias': name.asname
                        })
                
                # Extract top-level functions
                elif isinstance(node, ast.FunctionDef):
                    function_info = {
                        'name': node.name,
                        'args': self._extract_args(node.args),
                        'doc_string': ast.get_docstring(node),
                        'lineno': node.lineno
                    }
                    file_info['functions'].append(function_info)
                
                # Extract top-level classes
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'base_classes': [self._get_name(base) for base in node.bases],
                        'methods': [],
                        'doc_string': ast.get_docstring(node),
                        'lineno': node.lineno
                    }
                    
                    # Find methods in the class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                'name': item.name,
                                'args': self._extract_args(item.args),
                                'doc_string': ast.get_docstring(item),
                                'lineno': item.lineno
                            }
                            class_info['methods'].append(method_info)
                    
                    file_info['classes'].append(class_info)
            
            # Extract additional information using ast.walk for more comprehensive analysis
            for node in ast.walk(tree):
                # Check for decorators on functions or methods
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    # Extract decorator information if present
                    if node.decorator_list:
                        decorators = []
                        for decorator in node.decorator_list:
                            decorator_name = self._get_name(decorator)
                            decorators.append(decorator_name)
                        
                        # Find the function in either functions or methods and add decorator info
                        for func in file_info['functions']:
                            if func['name'] == node.name and 'decorators' not in func:
                                func['decorators'] = decorators
                        
                        # Check methods in all classes
                        for cls in file_info['classes']:
                            for method in cls['methods']:
                                if method['name'] == node.name and 'decorators' not in method:
                                    method['decorators'] = decorators
                
                # Extract function return hint if available
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    if node.returns:
                        return_hint = self._get_name(node.returns)
                        
                        # Add return hint to the function info
                        for func in file_info['functions']:
                            if func['name'] == node.name and 'return_hint' not in func:
                                func['return_hint'] = return_hint
                        
                        # Check methods in all classes
                        for cls in file_info['classes']:
                            for method in cls['methods']:
                                if method['name'] == node.name and 'return_hint' not in method:
                                    method['return_hint'] = return_hint
                
            # Generate descriptions for functions and methods based on docstrings, args, and return hints
            self._generate_function_descriptions(file_info)
                
            # No longer needed as we process top-level functions directly from tree.body:
            # Extract top-level functions
            # elif isinstance(node, ast.FunctionDef) and isinstance(node.parent, ast.Module):
            
            return file_info
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {
                'path': file_path,
                'name': os.path.basename(file_path),
                'error': str(e)
            }
    
    def _get_name(self, node):
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        else:
            return "Unknown"
    
    def _extract_args(self, args):
        """Extract function/method arguments."""
        arg_list = []
        
        # Add positional arguments
        for arg in args.args:
            arg_info = {'name': arg.arg, 'annotation': None, 'default': None}
            if arg.annotation:
                arg_info['annotation'] = self._get_name(arg.annotation)
            arg_list.append(arg_info)
        
        # Add defaults for positional arguments
        if args.defaults:
            default_offset = len(args.args) - len(args.defaults)
            for i, default in enumerate(args.defaults):
                arg_index = default_offset + i
                if arg_index < len(arg_list):
                    arg_list[arg_index]['default'] = "has_default"  # Just indicate there's a default
        
        # Add *args if present
        if args.vararg:
            arg_list.append({
                'name': f"*{args.vararg.arg}",
                'annotation': None if not args.vararg.annotation else self._get_name(args.vararg.annotation),
                'default': None
            })
        
        # Add **kwargs if present
        if args.kwarg:
            arg_list.append({
                'name': f"**{args.kwarg.arg}",
                'annotation': None if not args.kwarg.annotation else self._get_name(args.kwarg.annotation),
                'default': None
            })
        
        return arg_list
        
    def _generate_function_descriptions(self, file_info):
        """
        Generate descriptive summaries for functions and methods based on their 
        signatures, docstrings, arguments, and return hints.
        """
        # Process top-level functions
        for func in file_info['functions']:
            description = self._create_function_description(
                func['name'], 
                func.get('args', []), 
                func.get('doc_string', ''),
                func.get('return_hint', None),
                func.get('decorators', [])
            )
            func['description'] = description
            
        # Process methods in all classes
        for cls in file_info['classes']:
            for method in cls['methods']:
                # Include class context in method descriptions
                description = self._create_function_description(
                    method['name'], 
                    method.get('args', []), 
                    method.get('doc_string', ''),
                    method.get('return_hint', None),
                    method.get('decorators', []),
                    class_name=cls['name']
                )
                method['description'] = description
                
    def _create_function_description(self, name, args, docstring, return_hint=None, 
                                     decorators=None, class_name=None):
        """
        Create a descriptive summary of a function or method based on available information.
        
        Args:
            name (str): Function or method name
            args (list): List of argument dictionaries
            docstring (str): Function or method docstring
            return_hint (str): Return type annotation if available
            decorators (list): List of decorator names if available
            class_name (str): Class name if this is a method
            
        Returns:
            str: A descriptive summary of the function or method
        """
        # Start with the function type (method or function)
        if class_name:
            description = f"Method '{name}' in class '{class_name}'"
        else:
            description = f"Function '{name}'"
            
        # Add decorator information
        if decorators and len(decorators) > 0:
            decorator_str = ', '.join(f'@{d}' for d in decorators)
            description += f" decorated with {decorator_str}"
            
        # Add argument information
        if args:
            arg_names = [arg['name'] for arg in args]
            description += f" takes parameters: {', '.join(arg_names)}"
            
            # Add information about typed arguments
            typed_args = [arg for arg in args if arg.get('annotation')]
            if typed_args:
                typed_arg_str = ', '.join(f"{arg['name']}: {arg['annotation']}" for arg in typed_args)
                description += f". Typed parameters: {typed_arg_str}"
                
        # Add return type if available
        if return_hint:
            description += f". Returns {return_hint}"
            
        # Add docstring summary if available
        if docstring:
            # Extract the first sentence or line as a summary
            summary = docstring.strip().split('\n')[0].strip()
            # If summary is very long, truncate it
            if len(summary) > 100:
                summary = summary[:97] + "..."
            description += f". Summary: {summary}"
            
        return description


def parse_python_file(file_path: str) -> Dict[str, Any]:
    """
    Utility function to parse a single Python file using the AST parser.
    
    Args:
        file_path (str): Path to the Python file to parse
        
    Returns:
        Dict[str, Any]: Structured information about the file
    """
    parser = PythonAstParser()
    return parser.parse_file(file_path)


def parse_python_files(directory_path: str) -> List[Dict[str, Any]]:
    """
    Parse all Python files in the given directory and its subdirectories.
    
    Args:
        directory_path (str): Path to the directory containing Python files
        
    Returns:
        List[Dict[str, Any]]: List of structured information about each file
    """
    results = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                file_info = parse_python_file(file_path)
                results.append(file_info)
    return results
