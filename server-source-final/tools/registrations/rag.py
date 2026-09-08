"""
RAG Tool Registrations for Human-in-the-Loop MCP Server.

Registers tools for:
- Document indexing (single and bulk)
- Semantic search
- Collection management
"""

from typing import Optional

from tools.rag import (
    add_document_tool,
    add_folder_tool,
    search_tool,
    delete_tool,
    list_collections_tool,
    get_stats_tool,
)


def register_rag_tools(mcp):

    @mcp.tool(name='rag_add_document', description='Add a single document to the RAG index with control over chunking strategy and metadata.')
    async def rag_add_document(content: str, doc_id: str = None, collection: str = "default", metadata: dict = None, chunk_strategy: str = "auto", chunk_size: int = 1000, chunk_overlap: int = 100):
        return await add_document_tool(
            content=content, doc_id=doc_id, collection=collection,
            metadata=metadata, chunk_strategy=chunk_strategy,
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    @mcp.tool(name='rag_add_folder', description='Bulk index an entire folder with automatic file discovery, smart chunking, and language detection.')
    async def rag_add_folder(folder_path: str, collection: str = "default", file_patterns: list = None, exclude_patterns: list = None, recursive: bool = True, chunk_strategy: str = "auto", chunk_size: int = 1000, chunk_overlap: int = 100, max_file_size_kb: int = 500, dry_run: bool = False):
        return await add_folder_tool(
            folder_path=folder_path, collection=collection,
            file_patterns=file_patterns, exclude_patterns=exclude_patterns,
            recursive=recursive, chunk_strategy=chunk_strategy,
            chunk_size=chunk_size, chunk_overlap=chunk_overlap,
            max_file_size_kb=max_file_size_kb, dry_run=dry_run
        )

    @mcp.tool(name='rag_search', description='Semantic search across indexed documents using natural language queries with optional metadata filtering.')
    async def rag_search(query: str, collection: str = "default", n_results: int = 5, filter: dict = None, min_score: float = 0.0):
        return await search_tool(
            query=query, collection=collection, n_results=n_results,
            filter=filter, min_score=min_score
        )

    @mcp.tool(name='rag_delete', description='Delete documents from the RAG index by ID, filter, or delete entire collections.')
    async def rag_delete(doc_ids: list = None, filter: dict = None, collection: str = "default", delete_collection: bool = False):
        return await delete_tool(
            doc_ids=doc_ids, filter=filter, collection=collection,
            delete_collection=delete_collection
        )

    @mcp.tool(name='rag_list_collections', description='List all available RAG collections and their basic information.')
    async def rag_list_collections():
        return await list_collections_tool()

    @mcp.tool(name='rag_get_stats', description='Get detailed statistics about a specific collection.')
    async def rag_get_stats(collection: str = "default"):
        return await get_stats_tool(collection=collection)
