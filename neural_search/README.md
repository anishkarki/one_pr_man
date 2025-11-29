# OpenSearch Neural Search Tutorial

This folder contains a Jupyter Notebook (`neural_search_tutorial.ipynb`) that implements the [OpenSearch Neural Search Tutorial](https://docs.opensearch.org/latest/tutorials/vector-search/neural-search-tutorial/).

## Prerequisites
1.  **Running OpenSearch Cluster**: You must have OpenSearch running (e.g., via Docker).
2.  **ML Commons Plugin**: This is included in the official OpenSearch images.

## How to Run
1.  Open `neural_search_tutorial.ipynb` in VS Code.
2.  Ensure the `HOST`, `PORT`, and `AUTH` variables in the first code cell match your running OpenSearch instance.
    *   Default: `localhost:9200`, `admin:OpenSearch@2024`
3.  Run the cells sequentially.

## What it does
1.  **Configures Cluster**: Enables ML Commons to run on non-ML nodes (for single-node setups) and allows downloading models.
2.  **Registers Model**: Downloads and registers the `all-MiniLM-L6-v2` embedding model from HuggingFace.
3.  **Deploys Model**: Loads the model into memory.
4.  **Creates Pipeline**: Sets up an ingest pipeline to automatically generate embeddings for the `text` field.
5.  **Ingests Data**: Indexes sample documents.
6.  **Searches**: Performs a semantic search using the `neural` query type.

## Note on "Lightweight LLM"
This tutorial uses `all-MiniLM-L6-v2`, which is a small (approx 80MB) Transformer model optimized for sentence embeddings. It runs entirely within the OpenSearch process (via the ML Commons plugin), so no separate Docker container is needed for the model itself.
