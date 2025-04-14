
import logging
import sys
import os

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
# logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

from llama_index.core import SimpleDirectoryReader, PropertyGraphIndex, Settings
from llama_index.core.graph_stores.types import Entity, Relation, Property
from llama_index.llms.openai import OpenAI # Or your preferred LLM
from llama_index.embeddings.huggingface import HuggingFaceEmbedding # Or your preferred embedding model
# from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore # Example for Neo4j

# --- Configuration ---
# Make sure OPENAI_API_KEY is set in your environment variables
# Or configure LLM/embeddings manually:
# Settings.llm = OpenAI(model="gpt-4o-mini") # Or other LLM
# Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Optional: Configure Graph Store (e.g., Neo4j)
# NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
# NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
# NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
# graph_store = Neo4jPropertyGraphStore(
#     username=NEO4J_USERNAME,
#     password=NEO4J_PASSWORD,
#     url=NEO4J_URI,
# )
# Use default in-memory store if graph_store is not defined
graph_store = None

# --- Define Graph Schema for Python Code ---
entities = [
    Entity("Module", ["Name of the Python module"]),
    Entity("Class", ["Name of the class defined in the code"]),
    Entity("Function", ["Name of the function or method defined"]),
    Entity("Method", ["Name of a method defined within a class"]),
    Entity("Variable", ["Name of a variable or attribute"]),
    Entity("Import", ["Name of the imported module or object"]),
    Entity("CodeLine", ["An individual line of code"]),
    Entity("DocString", ["Documentation string for a module, class, function, or method"]),
    Entity("Argument", ["Function or method argument"]),
]

relations = [
    Relation("IMPORTS", ["Relation indicating a module imports another module or object"]),
    Relation("DEFINES_CLASS", ["Relation indicating a module defines a class"]),
    Relation("DEFINES_FUNCTION", ["Relation indicating a module defines a function"]),
    Relation("DEFINES_METHOD", ["Relation indicating a class defines a method"]),
    Relation("DEFINES_VARIABLE", ["Relation indicating a module, class, or function defines a variable"]),
    Relation("CALLS_FUNCTION", ["Relation indicating a function calls another function"]),
    Relation("HAS_ATTRIBUTE", ["Relation indicating a class has a specific attribute (variable or method)"]),
    Relation("INSTANCE_OF", ["Relation indicating a variable is an instance of a class"]),
    Relation("INHERITS_FROM", ["Relation indicating a class inherits from another class"]),
    Relation("HAS_DOCSTRING", ["Relation indicating an entity has a documentation string"]),
    Relation("CONTAINS_LINE", ["Relation indicating a module, class, function, or method contains a specific line of code"]),
    Relation("HAS_ARGUMENT", ["Relation indicating a function or method has a specific argument"]),
    Relation("LINE_NUMBER", ["Relation associating an entity with its line number in the source file"]),
    Relation("FOLLOWS", ["Relation indicating a code line follows another code line"]),
]

# --- Load Python Code using AST Parser ---
from src.ast_parser import parse_python_files, parse_python_file
from llama_index.core import Document
from llama_index.core.graph_stores.types import EntityNode, Property
import re

# Assuming your code is in the 'src' directory relative to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir) # Go up one level from src
code_dir = os.path.join(project_root, "src")

print(f"Loading Python files from: {code_dir}")
all_documents = []

try:
    # Process Python files with AST parser
    print("Processing Python files with AST parser for detailed graph indexing...")
    python_files_info = parse_python_files(code_dir)
    print(f"Parsed {len(python_files_info)} Python files with AST parser.")
    
    for file_info in python_files_info:
        file_path = file_info['path']
        
        # Create a base document for the module
        module_doc = Document(
            text=f"Module: {file_info['name']}",
            metadata={
                "file_path": file_path,
                "entity_type": "Module",
                "name": file_info['name'],
            }
        )
        all_documents.append(module_doc)
        
        # Process line by line to create CodeLine entities
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                for i, line in enumerate(lines):
                    line_num = i + 1  # 1-based line numbering
                    line_doc = Document(
                        text=line.rstrip(),
                        metadata={
                            "file_path": file_path,
                            "entity_type": "CodeLine",
                            "line_number": line_num,
                            "module_name": file_info['name'],
                        }
                    )
                    all_documents.append(line_doc)
        except Exception as e:
            print(f"Error processing lines in {file_path}: {e}")
        
        # Add docstring if available
        if file_info.get('doc_string'):
            docstring_doc = Document(
                text=file_info['doc_string'],
                metadata={
                    "file_path": file_path,
                    "entity_type": "DocString",
                    "module_name": file_info['name'],
                    "owner_type": "Module",
                    "owner_name": file_info['name'],
                }
            )
            all_documents.append(docstring_doc)
        
        # Process imports
        for imp in file_info.get('imports', []):
            import_doc = Document(
                text=f"Import: {imp['name']}" + (f" as {imp['alias']}" if imp['alias'] else ""),
                metadata={
                    "file_path": file_path,
                    "entity_type": "Import",
                    "name": imp['name'],
                    "alias": imp['alias'],
                    "module_name": file_info['name'],
                }
            )
            all_documents.append(import_doc)
        
        # Process classes
        for cls in file_info.get('classes', []):
            class_doc = Document(
                text=f"Class: {cls['name']}" + (f" ({', '.join(cls['base_classes'])})" if cls['base_classes'] else ""),
                metadata={
                    "file_path": file_path,
                    "entity_type": "Class",
                    "name": cls['name'],
                    "base_classes": ",".join(cls['base_classes']),
                    "module_name": file_info['name'],
                    "line_number": cls['lineno'],
                }
            )
            all_documents.append(class_doc)
            
            # Add class docstring if available
            if cls.get('doc_string'):
                cls_docstring_doc = Document(
                    text=cls['doc_string'],
                    metadata={
                        "file_path": file_path,
                        "entity_type": "DocString",
                        "module_name": file_info['name'],
                        "owner_type": "Class",
                        "owner_name": cls['name'],
                    }
                )
                all_documents.append(cls_docstring_doc)
            
            # Process methods
            for method in cls.get('methods', []):
                args_str = ", ".join([arg['name'] for arg in method['args']])
                method_doc = Document(
                    text=f"Method: {method['name']}({args_str}) in class {cls['name']}",
                    metadata={
                        "file_path": file_path,
                        "entity_type": "Method",
                        "name": method['name'],
                        "class_name": cls['name'],
                        "module_name": file_info['name'],
                        "line_number": method['lineno'],
                    }
                )
                all_documents.append(method_doc)
                
                # Add method docstring if available
                if method.get('doc_string'):
                    method_docstring_doc = Document(
                        text=method['doc_string'],
                        metadata={
                            "file_path": file_path,
                            "entity_type": "DocString",
                            "module_name": file_info['name'],
                            "owner_type": "Method",
                            "owner_name": method['name'],
                            "class_name": cls['name'],
                        }
                    )
                    all_documents.append(method_docstring_doc)
                
                # Process method arguments
                for arg in method.get('args', []):
                    arg_doc = Document(
                        text=f"Argument: {arg['name']} in method {method['name']}",
                        metadata={
                            "file_path": file_path,
                            "entity_type": "Argument",
                            "name": arg['name'],
                            "method_name": method['name'],
                            "class_name": cls['name'],
                            "module_name": file_info['name'],
                            "annotation": arg.get('annotation'),
                            "has_default": arg.get('default') is not None,
                        }
                    )
                    all_documents.append(arg_doc)
        
        # Process functions
        for func in file_info.get('functions', []):
            args_str = ", ".join([arg['name'] for arg in func['args']])
            func_doc = Document(
                text=f"Function: {func['name']}({args_str})",
                metadata={
                    "file_path": file_path,
                    "entity_type": "Function",
                    "name": func['name'],
                    "module_name": file_info['name'],
                    "line_number": func['lineno'],
                    "description": func.get('description', ''),
                }
            )
            all_documents.append(func_doc)
            
            # Add function docstring if available
            if func.get('doc_string'):
                func_docstring_doc = Document(
                    text=func['doc_string'],
                    metadata={
                        "file_path": file_path,
                        "entity_type": "DocString",
                        "module_name": file_info['name'],
                        "owner_type": "Function",
                        "owner_name": func['name'],
                    }
                )
                all_documents.append(func_docstring_doc)
            
            # Process function arguments
            for arg in func.get('args', []):
                arg_doc = Document(
                    text=f"Argument: {arg['name']} in function {func['name']}",
                    metadata={
                        "file_path": file_path,
                        "entity_type": "Argument",
                        "name": arg['name'],
                        "function_name": func['name'],
                        "module_name": file_info['name'],
                        "annotation": arg.get('annotation'),
                        "has_default": arg.get('default') is not None,
                    }
                )
                all_documents.append(arg_doc)
    
    # Also load SQL files using SimpleDirectoryReader
    reader = SimpleDirectoryReader(
        input_dir=project_root,
        required_exts=[".sql"],
        recursive=True,
    )
    sql_documents = reader.load_data()
    print(f"Loaded {len(sql_documents)} SQL documents.")
    
    # Add SQL documents to all_documents
    for doc in sql_documents:
        doc.metadata["entity_type"] = "SQLScript"
        all_documents.append(doc)
    
    print(f"Total documents for graph indexing: {len(all_documents)}")
    
    if not all_documents:
        print("No documents found. Please check the directory paths.")
        sys.exit(1)
except Exception as e:
    print(f"Error processing files: {e}")
    sys.exit(1)

# --- Build the Property Graph Index ---
print("Building Property Graph Index with enhanced code structure...")
index = PropertyGraphIndex.from_documents(
    all_documents,
    llm=Settings.llm, # Uses default OpenAI if not set otherwise
    embed_model=Settings.embed_model, # Uses default OpenAI embedding if not set otherwise
    property_graph_store=graph_store,
    entities=entities,
    relations=relations,
    include_embeddings=True,
    show_progress=True,
)

print("Property Graph Index built successfully.")

# --- Optional: Persist Index (if using a persistent store) ---
# if graph_store:
#     index.storage_context.persist(persist_dir="./storage_graph")
#     print("Index persisted.")

# --- Optional: Example Query ---
# retriever = index.as_retriever()
# nodes = retriever.retrieve("What classes are defined in layout.py?")
# for node in nodes:
#     print(node.text)

# query_engine = index.as_query_engine()
# response = query_engine.query("Show me the functions defined in the Query class.")
# print(response)

print("Script finished.")

