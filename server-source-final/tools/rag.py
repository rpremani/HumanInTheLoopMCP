"""
RAG Tools for Human-in-the-Loop MCP Server

Provides tools for document indexing and semantic search:
- Add documents (single or folder)
- Semantic search
- Collection management
- Statistics and monitoring
"""

import sys
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.rag_client import get_rag_client, RAGClientError, SearchResult


async def add_document_tool(
    content: str,
    doc_id: str = None,
    collection: str = 'default',
    metadata: dict = None,
    chunk_strategy: str = 'auto',
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> Dict[str, Any]:
    try:
        client = get_rag_client()
        result = client.add_document(
            content=content,
            doc_id=doc_id,
            collection=collection,
            metadata=metadata,
            chunk_strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        return result
    except RAGClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


async def add_folder_tool(
    folder_path: str,
    collection: str = 'default',
    file_patterns: list = None,
    exclude_patterns: list = None,
    recursive: bool = True,
    chunk_strategy: str = 'auto',
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    max_file_size_kb: int = 500,
    dry_run: bool = False
) -> Dict[str, Any]:
    try:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return {'success': False, 'error': f'Folder not found: {folder_path}'}

        if file_patterns is None:
            file_patterns = ['*.py', '*.js', '*.ts', '*.tsx', '*.jsx', '*.md', '*.txt', '*.java', '*.go', '*.rs']

        if exclude_patterns is None:
            exclude_patterns = ['*test*', '*.min.js', 'node_modules/*', '.git/*', '__pycache__/*', '*.pyc']

        files_to_index = []
        files_skipped = []

        for pattern in file_patterns:
            if recursive:
                matched_files = folder.rglob(pattern)
            else:
                matched_files = folder.glob(pattern)

            for file_path in matched_files:
                excluded = False
                for exclude in exclude_patterns:
                    if file_path.match(exclude):
                        excluded = True
                        files_skipped.append({
                            'path': str(file_path),
                            'reason': f'excluded by pattern: {exclude}',
                        })
                        break

                if excluded:
                    continue

                file_size_kb = file_path.stat().st_size / 1024
                if file_size_kb > max_file_size_kb:
                    files_skipped.append({
                        'path': str(file_path),
                        'reason': f'exceeds max_file_size: {file_size_kb:.1f}KB > {max_file_size_kb}KB',
                    })
                    continue

                files_to_index.append(file_path)

        if dry_run:
            return {
                'success': True,
                'dry_run': True,
                'files_to_index': len(files_to_index),
                'files_skipped': len(files_skipped),
                'preview_files': [str(f) for f in files_to_index[:10]],
                'skipped_files': files_skipped[:10],
            }

        client = get_rag_client()
        files_processed = []
        total_chunks = 0
        total_chars = 0

        for file_path in files_to_index:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                total_chars += len(content)

                ext = file_path.suffix.lower()

                lang_map = {
                    '.py': 'python',
                    '.js': 'javascript',
                    '.ts': 'typescript',
                    '.tsx': 'typescript',
                    '.jsx': 'javascript',
                    '.java': 'java',
                    '.go': 'go',
                    '.rs': 'rust',
                    '.md': 'markdown',
                }

                language = lang_map.get(ext, 'text')

                metadata = {
                    'source': str(file_path),
                    'language': language,
                    'file_size': len(content),
                }

                result = client.add_document(
                    content=content,
                    collection=collection,
                    metadata=metadata,
                    chunk_strategy=chunk_strategy,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )

                if result['success']:
                    files_processed.append({
                        'path': str(file_path),
                        'chunks': result['chunks_created'],
                    })

                    total_chunks += result['chunks_created']
            except Exception as e:
                files_skipped.append({
                    'path': str(file_path),
                    'reason': f'error reading file: {str(e)}',
                })

        return {
            'success': True,
            'collection': collection,
            'files_processed': len(files_processed),
            'files_skipped': len(files_skipped),
            'chunks_created': total_chunks,
            'total_characters': total_chars,
            'files': files_processed[:20],
            'skipped_files': files_skipped,
        }
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


async def search_tool(
    query: str,
    collection: str = 'default',
    n_results: int = 5,
    filter: dict = None,
    min_score: float = 0.0
) -> Dict[str, Any]:
    try:
        client = get_rag_client()
        results = client.search(
            query=query,
            collection=collection,
            n_results=n_results,
            filter=filter,
            min_score=min_score,
        )

        formatted_results = []
        for result in results:
            formatted_results.append({
                'doc_id': result.doc_id,
                'content': result.content,
                'score': round(result.score, 4),
                'metadata': result.metadata,
            })

        return {
            'success': True,
            'query': query,
            'total_results': len(formatted_results),
            'results': formatted_results,
            'summary': _format_search_summary(query, formatted_results),
        }
    except RAGClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


def _format_search_summary(query: str, results: List[Dict]) -> str:
    if not results:
        return f"## No results found for: '{query}'"

    lines = [f"## Search Results for: '{query}'\n"]
    lines.append(f"Found {len(results)} relevant documents:\n")

    for i, result in enumerate(results[:5], 1):
        score = result['score']
        content = result['content']
        metadata = result['metadata']

        if len(content) > 200:
            content = content[:200] + '...'

        lines.append(f"**{i}. Score: {score:.2f}** ({metadata.get('source', 'unknown source')})")
        lines.append(f"```\n{content}\n```\n")

    return '\n'.join(lines)


async def delete_tool(
    doc_ids: list = None,
    filter: dict = None,
    collection: str = 'default',
    delete_collection: bool = False
) -> Dict[str, Any]:
    try:
        client = get_rag_client()
        result = client.delete(
            doc_ids=doc_ids,
            filter=filter,
            collection=collection,
            delete_collection=delete_collection,
        )

        return result
    except RAGClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


async def list_collections_tool() -> Dict[str, Any]:
    try:
        client = get_rag_client()
        collections = client.list_collections()

        return {
            'success': True,
            'total_collections': len(collections),
            'collections': collections,
        }
    except RAGClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}


async def get_stats_tool(collection: str = 'default') -> Dict[str, Any]:
    try:
        client = get_rag_client()
        stats = client.get_stats(collection=collection)
        return stats
    except RAGClientError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {str(e)}'}
