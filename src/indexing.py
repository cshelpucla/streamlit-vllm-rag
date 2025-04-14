import os
import time
import json
from pathlib import Path
import nest_asyncio # Added to handle event loop issues
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings, PropertyGraphIndex, StorageContext
from llama_index.core import Document
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.graph_stores import SimplePropertyGraphStore # Added for Property Graph
from llama_index.core.graph_stores.types import EntityNode, Relation # Added for enhanced schema
from src.ast_parser import parse_python_file, parse_python_files


def load_schema_from_json(schema_path):
    """
    Load entity-relationship schema from a JSON file.
    
    Args:
        schema_path (str): Path to the JSON schema file
        
    Returns:
        tuple: (entities, relations, entity_types, relation_types)
    """
    try:
        with open(schema_path, 'r') as f:
            schema_data = json.load(f)
            
        entities = [
            EntityNode(
                entity_type=item["entity_type"],
                name=item["entity_type"],  # Use entity_type as the name
                properties={
                    f"property_{i}": prop for i, prop in enumerate(item["properties"])
                }
            ) 
            for item in schema_data.get("entities", [])
        ]
        
        relations = [
            Relation(
                rel_type=item["rel_type"],
                label=item["rel_type"],  # Use rel_type as the label
                source_id="placeholder_source_id",  # Placeholder values since these will be assigned during extraction
                target_id="placeholder_target_id",  # Placeholder values since these will be assigned during extraction
                properties={
                    f"property_{i}": prop for i, prop in enumerate(item["properties"])
                }
            ) 
            for item in schema_data.get("relations", [])
        ]
        
        # For backward compatibility with code that might use string lists
        entity_types = [entity.name for entity in entities]
        relation_types = [relation.label for relation in relations]
        
        return entities, relations, entity_types, relation_types
    
    except Exception as e:
        print(f"Error loading schema from {schema_path}: {e}", flush=True)
        # Fallback to empty schema
        return [], [], [], []


# Define the schema paths - make it configurable
PYTHON_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema", "python_schema.json")
SQL_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema", "sql_schema.json")

# Load the Python schema from the JSON file
python_entities, python_relations, python_entity_types, python_relation_types = load_schema_from_json(PYTHON_SCHEMA_PATH)

# Load the SQL schema from the JSON file
sql_entities, sql_relations, sql_entity_types, sql_relation_types = load_schema_from_json(SQL_SCHEMA_PATH)

# Combine schemas for use in indexing
entities = python_entities + sql_entities
relations = python_relations + sql_relations
entity_types = python_entity_types + sql_entity_types
relation_types = python_relation_types + sql_relation_types


def perform_indexing(directory_path, collection, embed_model):
    """
    Loads Python documents from a directory and indexes them into ChromaDB.
    Uses AST parser for Python files to extract structured information.

    Args:
        directory_path (str): The path to the directory containing Python files.
        collection (chromadb.Collection): The ChromaDB collection object.
        embed_model: The embedding model instance from LlamaIndex.

    Returns:
        tuple: (status_message, index_object or None)
    """
    if not directory_path or not os.path.isdir(directory_path):
        return "Error: Invalid or no directory path provided.", None

    print(f"Attempting to index directory: {directory_path}", flush=True)
    try:
        vector_store = ChromaVectorStore(chroma_collection=collection)

        # Process Python files with AST parser and other files with SimpleDirectoryReader
        all_documents = []
        
        # First process Python files with AST parser
        print("Processing Python files with AST parser...", flush=True)
        python_files_count = 0
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        # Parse Python file with AST
                        ast_data = parse_python_file(file_path)
                        
                        # Create structured text from AST data
                        structured_text = f"File: {ast_data['path']}\n\n"
                        
                        # Add docstring if available
                        if ast_data.get('doc_string'):
                            structured_text += f"Description: {ast_data['doc_string']}\n\n"
                        
                        # Add imports
                        if ast_data.get('imports'):
                            structured_text += "Imports:\n"
                            for imp in ast_data['imports']:
                                alias_str = f" as {imp['alias']}" if imp['alias'] else ""
                                structured_text += f"- {imp['name']}{alias_str}\n"
                            structured_text += "\n"
                        
                        # Add classes
                        if ast_data.get('classes'):
                            structured_text += "Classes:\n"
                            for cls in ast_data['classes']:
                                base_str = f"({', '.join(cls['base_classes'])})" if cls['base_classes'] else ""
                                structured_text += f"- class {cls['name']}{base_str}\n"
                                if cls.get('doc_string'):
                                    structured_text += f"  Description: {cls['doc_string']}\n"
                                
                                # Add methods
                                if cls.get('methods'):
                                    structured_text += "  Methods:\n"
                                    for method in cls['methods']:
                                        args_str = ", ".join([arg['name'] for arg in method['args']])
                                        structured_text += f"  - {method['name']}({args_str})\n"
                                        if method.get('doc_string'):
                                            structured_text += f"    Description: {method['doc_string']}\n"
                                structured_text += "\n"
                        
                        # Add functions
                        if ast_data.get('functions'):
                            structured_text += "Functions:\n"
                            for func in ast_data['functions']:
                                args_str = ", ".join([arg['name'] for arg in func['args']])
                                structured_text += f"- {func['name']}({args_str})\n"
                                if func.get('doc_string'):
                                    structured_text += f"  Description: {func['doc_string']}\n"
                            structured_text += "\n"
                        
                        # Create a document with the structured information
                        doc = Document(text=structured_text, metadata={"file_path": file_path, "file_type": "python"})
                        all_documents.append(doc)
                        python_files_count += 1
                    except Exception as e:
                        print(f"Error parsing Python file {file_path}: {e}", flush=True)
                        # Fall back to simple text extraction for failed files
                        with open(file_path, 'r', encoding='utf-8') as f:
                            text = f.read()
                            doc = Document(text=text, metadata={"file_path": file_path, "file_type": "python_raw"})
                            all_documents.append(doc)
        
        print(f"Processed {python_files_count} Python files with AST parser.", flush=True)
        
        # Now process non-Python files with SimpleDirectoryReader
        print("Loading non-Python documents...", flush=True)
        reader = SimpleDirectoryReader(
            input_dir=directory_path,
            required_exts=[".sql"],  # Only include SQL files here since Python is handled separately
            recursive=True
        )
        other_documents = reader.load_data()
        print(f"Loaded {len(other_documents)} SQL documents.", flush=True)
        
        # Combine all documents
        all_documents.extend(other_documents)
        print(f"Total documents to index: {len(all_documents)}", flush=True)

        if not all_documents:
            print("Warning: No documents found to index.", flush=True)
            return "Warning: No Python or SQL files found in the selected directory.", None

        # Create index
        print("Creating index...", flush=True)
        start_time = time.time()

        # Ensure the correct embed_model is used for indexing
        index = VectorStoreIndex.from_documents(
            all_documents,
            vector_store=vector_store,
            embed_model=embed_model # Pass the configured embed_model
        )
        end_time = time.time()
        print("Index object created successfully.", flush=True)

        status_message = f"Indexing complete in {end_time - start_time:.2f} seconds. Index stored."
        return status_message, index
    except Exception as e:
        print(f"Error during indexing: {e}", flush=True)
        # import traceback
        # print(traceback.format_exc(), flush=True) # Uncomment for detailed traceback
        return f"Error during indexing: {e}", None

def perform_graph_indexing(directory_path, llm, embed_model):
    """
    Loads Python documents from a directory and indexes them into a Simple Property Graph,
    using the defined schema and the default LLM-based extraction.
    Uses AST parser for Python files to extract structured information.

    Args:
        directory_path (str): The path to the directory containing Python files.
        llm: The language model instance from LlamaIndex Settings.
        embed_model: The embedding model instance from LlamaIndex Settings.

    Returns:
        tuple: (status_message, index_object or None)
    """
    nest_asyncio.apply() # Apply nest_asyncio patch
    if not directory_path or not os.path.isdir(directory_path):
        return "Error: Invalid or no directory path provided.", None

    print(f"Attempting to graph index directory: {directory_path}", flush=True)
    try:
        # Process Python files with AST parser and other files with SimpleDirectoryReader
        all_documents = []
        
        # First process Python files with AST parser
        print("Processing Python files with AST parser for graph indexing...", flush=True)
        python_files_count = 0
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        # Parse Python file with AST
                        ast_data = parse_python_file(file_path)
                        
                        # Create structured text from AST data
                        structured_text = f"File: {ast_data['path']}\n\n"
                        
                        # Add docstring if available
                        if ast_data.get('doc_string'):
                            structured_text += f"Description: {ast_data['doc_string']}\n\n"
                        
                        # Add imports
                        if ast_data.get('imports'):
                            structured_text += "Imports:\n"
                            for imp in ast_data['imports']:
                                alias_str = f" as {imp['alias']}" if imp['alias'] else ""
                                structured_text += f"- {imp['name']}{alias_str}\n"
                            structured_text += "\n"
                        
                        # Add classes
                        if ast_data.get('classes'):
                            structured_text += "Classes:\n"
                            for cls in ast_data['classes']:
                                base_str = f"({', '.join(cls['base_classes'])})" if cls['base_classes'] else ""
                                structured_text += f"- class {cls['name']}{base_str}\n"
                                if cls.get('doc_string'):
                                    structured_text += f"  Description: {cls['doc_string']}\n"
                                
                                # Add methods
                                if cls.get('methods'):
                                    structured_text += "  Methods:\n"
                                    for method in cls['methods']:
                                        args_str = ", ".join([arg['name'] for arg in method['args']])
                                        structured_text += f"  - {method['name']}({args_str})\n"
                                        if method.get('doc_string'):
                                            structured_text += f"    Description: {method['doc_string']}\n"
                                structured_text += "\n"
                        
                        # Add functions
                        if ast_data.get('functions'):
                            structured_text += "Functions:\n"
                            for func in ast_data['functions']:
                                args_str = ", ".join([arg['name'] for arg in func['args']])
                                structured_text += f"- {func['name']}({args_str})\n"
                                if func.get('doc_string'):
                                    structured_text += f"  Description: {func['doc_string']}\n"
                            structured_text += "\n"
                        
                        # Create a document with the structured information - include extra metadata for graph indexing
                        doc = Document(
                            text=structured_text, 
                            metadata={
                                "file_path": file_path, 
                                "file_type": "python",
                                "has_ast": True,
                                "classes": [cls["name"] for cls in ast_data.get("classes", [])],
                                "functions": [func["name"] for func in ast_data.get("functions", [])],
                            }
                        )
                        all_documents.append(doc)
                        python_files_count += 1
                    except Exception as e:
                        print(f"Error parsing Python file {file_path} for graph indexing: {e}", flush=True)
                        # Fall back to simple text extraction for failed files
                        with open(file_path, 'r', encoding='utf-8') as f:
                            text = f.read()
                            doc = Document(text=text, metadata={"file_path": file_path, "file_type": "python_raw"})
                            all_documents.append(doc)
        
        print(f"Processed {python_files_count} Python files with AST parser for graph indexing.", flush=True)
        
        # Now process non-Python files with SimpleDirectoryReader
        print("Loading non-Python documents for graph indexing...", flush=True)
        reader = SimpleDirectoryReader(
            input_dir=directory_path,
            required_exts=[".sql"],  # Only include SQL files here since Python is handled separately
            recursive=True
        )
        other_documents = reader.load_data()
        print(f"Loaded {len(other_documents)} SQL documents for graph indexing.", flush=True)
        
        # Combine all documents
        all_documents.extend(other_documents)
        documents = all_documents
        print(f"Total documents for graph indexing: {len(documents)}", flush=True)

        if not documents:
            print("Warning: No documents found for graph index.", flush=True)
            return "Warning: No Python files found in the selected directory.", None

        # Create graph store (in-memory for now)
        print("Creating SimplePropertyGraphStore...", flush=True)
        graph_store = SimplePropertyGraphStore()
        storage_context = StorageContext.from_defaults(graph_store=graph_store)

        # Use the predefined entities and relations
        print("Using predefined KG schema for extraction...", flush=True)

        # Create Property Graph Index using the specific schema
        print("Creating PropertyGraphIndex using KG schema...", flush=True)
        start_time = time.time()

        index = PropertyGraphIndex.from_documents(
            documents,
            property_graph_store=graph_store, # Use the in-memory store via storage_context is preferred but this works too
            # storage_context=storage_context, # Alternative way to pass the store
            entities=entities, # Pass the enhanced Entity objects with descriptions
            relations=relations, # Pass the enhanced Relation objects with descriptions
            llm=llm,  # Pass the LLM for extraction based on schema
            embed_model=embed_model, # Pass embed model
            show_progress=True,
        )

        end_time = time.time()
        print("Property Graph Index object created successfully.", flush=True)

        # Save the property graph index to disk
        from datetime import datetime
        from src.graph_persistence import save_property_graph_index
        
        # Generate a timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"property_graph_index_{timestamp}.pickle"
        
        # Save the index
        save_path = save_property_graph_index(index, file_name=filename)
        
        if save_path:
            status_message = f"Graph indexing complete in {end_time - start_time:.2f} seconds. Index stored at {save_path}"
        else:
            status_message = f"Graph indexing complete in {end_time - start_time:.2f} seconds. Index stored in memory only (save failed)."
            
        return status_message, index
    except Exception as e:
        print(f"Error during graph indexing: {e}", flush=True)
        # import traceback
        # print(traceback.format_exc(), flush=True) # Uncomment for detailed traceback
        return f"Error during graph indexing: {e}", None
