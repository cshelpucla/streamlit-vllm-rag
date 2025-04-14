\
import os
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.openai_like import OpenAILike # Using OpenAILike as in the original final version
import chromadb

# Load environment variables
load_dotenv()
print(f"Loaded VLLM_URL from .env: {os.getenv('VLLM_URL')}", flush=True)
print(f"Loaded OLLAMA_BASE_URL from .env: {os.getenv('OLLAMA_BASE_URL')}", flush=True)
print(f"Loaded EMBEDDING_MODEL from .env: {os.getenv('EMBEDDING_MODEL')}", flush=True)
print(f"Loaded MODEL_NAME from .env: {os.getenv('MODEL_NAME')}", flush=True)

# --- Configuration Variables ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
VLLM_API_URL = os.getenv("VLLM_URL", "http://localhost:8000/v1") # Default if not set
MODEL_NAME = os.getenv("MODEL_NAME", "llama3") # Default if not set
# Using the hardcoded URL from the original app.py for OpenAILike
OPENAI_LIKE_API_BASE = "http://192.168.68.91:8000/v1"
OPENAI_LIKE_API_KEY = "fake" # As used in the original

# --- LlamaIndex Configuration ---
def check_vllm_reachability(api_url):
    """Checks if the VLLM endpoint is reachable."""
    try:
        parsed_url = urlparse(api_url)
        base_vllm_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        health_url = f"{base_vllm_url}/health"
        print(f"Attempting to reach VLLM at: {health_url}", flush=True)
        response = requests.get(health_url, timeout=5)
        response.raise_for_status()
        print(f"VLLM endpoint reachable. Status code: {response.status_code}", flush=True)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not reach VLLM endpoint at {health_url}. Error: {e}", flush=True)
        # Depending on requirements, you might want to raise an error here
        # raise ConnectionError(f"Failed to connect to VLLM at {health_url}") from e
        return False

def configure_llama_index():
    """Configures LlamaIndex settings for embedding and LLM."""
    print(f"Using Ollama Embedding URL: {OLLAMA_BASE_URL}", flush=True)
    print(f"Using Embedding Model: {EMBEDDING_MODEL_NAME}", flush=True)
    embed_model = OllamaEmbedding(
        model_name=EMBEDDING_MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
    )

    print(f"Using LLM Model: {MODEL_NAME}", flush=True)
    print(f"Using OpenAILike API Base: {OPENAI_LIKE_API_BASE}", flush=True)

    # Check reachability before initializing LLM
    # Using OPENAI_LIKE_API_BASE for the check as it's the one being used
    check_vllm_reachability(OPENAI_LIKE_API_BASE)

    # Using OpenAILike as it was the final configuration in the original app.py
    llm = OpenAILike(
        model=MODEL_NAME,
        api_base=OPENAI_LIKE_API_BASE,
        api_key=OPENAI_LIKE_API_KEY,
        temperature=0.7, # Added temperature, adjust as needed
        context_window=25000,
        is_chat_model=True,
        is_function_calling_model=False,
    )

    # Configure LlamaIndex settings globally (can be overridden locally if needed)
    Settings.embed_model = embed_model
    Settings.llm = llm

    print("LlamaIndex Settings configured.", flush=True)
    return embed_model, llm # Return configured models

# --- ChromaDB Initialization ---
def initialize_chroma():
    """Initializes and returns the ChromaDB collection."""
    # Ensure the embedding model is configured in Settings first
    if not Settings.embed_model:
        # Try configuring if not already done (e.g., if called standalone)
        print("Warning: Settings.embed_model not configured. Attempting configuration.", flush=True)
        configure_llama_index()
        if not Settings.embed_model:
             raise ValueError("LlamaIndex Settings.embed_model must be configured before initializing Chroma.")

    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection_name = "python_code_collection"
    print(f"Getting or creating Chroma collection: '{collection_name}'", flush=True)
    collection = chroma_client.get_or_create_collection(collection_name)
    print(f"Chroma collection '{collection_name}' obtained/created successfully.", flush=True)
    return collection

# --- Initial Configuration Call (Optional) ---
# You might call configure_llama_index() here once at startup
# if you don't want it called repeatedly in callbacks.
# However, the original code called it in callbacks, so we'll stick to that pattern
# unless explicitly asked to change.
# EMBED_MODEL, LLM = configure_llama_index()
# COLLECTION = initialize_chroma()
