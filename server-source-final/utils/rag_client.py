"""RAG (Retrieval-Augmented Generation) client using ChromaDB for vector storage."""

import ast
import re
import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import time

import chromadb
from chromadb.config import Settings

from .embedding_client import get_embedding_client, EmbeddingClientError


DEFAULT_STORAGE_PATH = Path.home() / '.mcp-rag-data'
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 100

CODE_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.cpp', '.c', '.h'}
MARKDOWN_EXTENSIONS = {'.md', '.markdown', '.mdx'}


@dataclass
class ChunkResult:
    chunks: List[str]
    metadata: List[Dict[str, Any]]


@dataclass
class SearchResult:
    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


class RAGClientError(Exception):
    pass


class RAGClient:
    """RAG client using ChromaDB for vector storage and retrieval."""

    def __init__(self, storage_path=None, embedding_model='text-embedding-3-small-inference'):
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_STORAGE_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.storage_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self.embedding_client = get_embedding_client(embedding_model)

    def _generate_doc_id(self, content, metadata=None):
        """Generate a document ID from content hash."""
        hash_input = content
        if metadata and 'source' in metadata:
            hash_input = f"{metadata['source']}:{content}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _chunk_content(self, content: str, strategy: str = 'auto', chunk_size: int = DEFAULT_CHUNK_SIZE,
                       chunk_overlap: int = DEFAULT_CHUNK_OVERLAP, metadata: Dict = None) -> 'ChunkResult':
        """Chunk content according to the specified strategy."""
        metadata = metadata or {}

        if strategy == 'auto':
            strategy = self._detect_chunking_strategy(content, metadata)

        if strategy == 'none':
            chunks = [content]
        elif strategy == 'code':
            chunks = self._chunk_code(content, metadata.get('source', ''))
        elif strategy == 'markdown':
            chunks = self._chunk_markdown(content)
        elif strategy == 'semantic':
            chunks = self._chunk_semantic(content, chunk_size, chunk_overlap)
        elif strategy == 'fixed':
            chunks = self._chunk_fixed(content, chunk_size, chunk_overlap)
        else:
            raise RAGClientError(f'Unknown chunking strategy: {strategy}')

        chunk_metadata = []
        for i, chunk in enumerate(chunks):
            chunk_meta = metadata.copy()
            chunk_meta.update({
                'chunk_index': i,
                'chunk_total': len(chunks),
                'chunk_strategy': strategy,
                'indexed_at': datetime.now().isoformat(),
            })
            chunk_metadata.append(chunk_meta)

        return ChunkResult(chunks=chunks, metadata=chunk_metadata)

    def _detect_chunking_strategy(self, content, metadata=None):
        """Auto-detect the best chunking strategy."""
        if metadata and 'source' in metadata:
            ext = Path(metadata['source']).suffix.lower()
            if ext in CODE_EXTENSIONS:
                return 'code'
            if ext in MARKDOWN_EXTENSIONS:
                return 'markdown'
        return 'semantic'

    def _chunk_code(self, content: str, source: str = '') -> List[str]:
        """
        Chunk code intelligently based on file extension.
        Supports Python with AST, JS/TS with function boundaries,
        falls back to fixed-size chunks for other languages.
        """
        ext = Path(source).suffix.lower()

        if ext == '.py':
            try:
                return self._chunk_python_ast(content)
            except Exception:
                pass

        if ext in {'.js', '.ts', '.jsx', '.tsx'}:
            return self._chunk_js_functions(content)

        return self._chunk_fixed(content, 1500, 150)

    def _chunk_python_ast(self, content: str) -> List[str]:
        """Chunk Python code using AST to respect function/class boundaries."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._chunk_fixed(content, 1500, 150)

        chunks = []
        lines = content.split('\n')

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                start_line = node.lineno - 1
                end_line = node.end_lineno
                chunk = '\n'.join(lines[start_line:end_line])
                chunks.append(chunk)

        if chunks:
            return chunks

        return self._chunk_fixed(content, 1500, 150)

    def _chunk_js_functions(self, content: str) -> List[str]:
        """Chunk JavaScript/TypeScript code by function boundaries."""
        patterns = [
            r'(?:export\s+)?(?:async\s+)?function\s+\w+',
            r'(?:export\s+)?class\s+\w+',
            r'(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\(',
            r'(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?function',
        ]

        combined = '|'.join(patterns)
        matches = list(re.finditer(combined, content))

        if not matches:
            return self._chunk_fixed(content, 1500, 150)

        chunks = []

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)

        if not chunks:
            return self._chunk_fixed(content, 1500, 150)

        return chunks

    def _chunk_markdown(self, content: str) -> List[str]:
        """Chunk markdown by headers (## h2 primarily)."""
        sections = re.split(r'\n##\s+', content)
        chunks = []

        for i, section in enumerate(sections):
            if i > 0:
                section = '## ' + section

            if len(section) > 3000:
                subsections = re.split(r'\n###\s+', section)
                for j, subsection in enumerate(subsections):
                    if j > 0:
                        subsection = '### ' + subsection
                    if subsection.strip():
                        chunks.append(subsection.strip())
            elif section.strip():
                chunks.append(section.strip())

        if not chunks:
            return [content]

        return chunks

    def _chunk_semantic(self, content: str, chunk_size: int = DEFAULT_CHUNK_SIZE,
                        overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
        """
        Chunk text at semantic boundaries (paragraphs/sentences).
        More intelligent than fixed chunking.
        """
        paragraphs = re.split(r'\n\n+', content)
        chunks = []
        current_chunk = ''
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_length = len(para)

            if current_length + para_length > chunk_size and current_chunk:
                chunks.append(current_chunk)
                # Keep overlap from end of previous chunk
                if overlap > 0:
                    overlap_text = current_chunk[-overlap:]
                    current_chunk = overlap_text + '\n\n' + para
                    current_length = len(overlap_text) + para_length
                else:
                    current_chunk = para
                    current_length = para_length
            else:
                if current_chunk:
                    current_chunk += '\n\n' + para
                    current_length += para_length
                else:
                    current_chunk = para
                    current_length = para_length

        if current_chunk:
            chunks.append(current_chunk)

        if not chunks:
            return [content]

        return chunks

    def _chunk_fixed(self, content: str, chunk_size: int = DEFAULT_CHUNK_SIZE,
                     overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
        """Simple fixed-size chunking with overlap."""
        if not content:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            if chunk:
                chunks.append(chunk)
            start += chunk_size - overlap

        if not chunks:
            return [content]

        return chunks

    def add_document(self, content, doc_id=None, collection='default',
                     metadata=None, chunk_strategy='auto',
                     chunk_size=DEFAULT_CHUNK_SIZE,
                     chunk_overlap=DEFAULT_CHUNK_OVERLAP):
        """Add a document to the RAG index."""
        start_time = time.time()

        try:
            base_id = doc_id or self._generate_doc_id(content, metadata)

            chunk_result = self._chunk_content(
                content,
                strategy=chunk_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                metadata=metadata,
            )

            embeddings = self.embedding_client.embed(chunk_result.chunks)

            col = self.client.get_or_create_collection(
                name=collection,
                metadata={'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')},
            )

            chunk_ids = []
            chunk_metadatas = []

            for i, chunk_meta in enumerate(chunk_result.metadata):
                chunk_id = f'{base_id}_chunk_{i}'
                chunk_ids.append(chunk_id)

                merged_meta = dict(metadata or {})
                merged_meta.update(chunk_meta)
                merged_meta['doc_id'] = base_id
                merged_meta['chunk_index'] = i
                merged_meta['total_chunks'] = len(chunk_result.chunks)
                chunk_metadatas.append(merged_meta)

            col.add(
                ids=chunk_ids,
                embeddings=embeddings.embeddings,
                documents=chunk_result.chunks,
                metadatas=chunk_metadatas,
            )

            elapsed = time.time() - start_time

            return {
                'doc_id': base_id,
                'chunks_created': len(chunk_ids),
                'collection': collection,
                'time_seconds': round(elapsed, 3),
                'embedding_model': embeddings.model,
                'dimensions': embeddings.dimensions,
                'token_usage': embeddings.token_usage,
            }

        except EmbeddingClientError as e:
            raise RAGClientError(f'Embedding error: {str(e)}')
        except Exception as e:
            raise RAGClientError(f'Failed to add document: {str(e)}')

    def search(self, query, collection='default', n_results=5,
               filter=None, min_score=0.0):
        """Search for documents matching the query."""
        try:
            col = self.client.get_collection(name=collection)
        except Exception:
            return []

        try:
            query_embedding = self.embedding_client.embed_single(query)
        except EmbeddingClientError as e:
            raise RAGClientError(f'Embedding error: {str(e)}')

        query_params = {
            'query_embeddings': [query_embedding],
            'n_results': n_results,
        }
        if filter:
            query_params['where'] = filter

        results = col.query(**query_params)

        search_results = []
        if results and results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                distance = results['distances'][0][i] if results.get('distances') else 0
                score = 1.0 / (1.0 + distance)

                if score < min_score:
                    continue

                search_results.append(SearchResult(
                    doc_id=doc_id,
                    content=results['documents'][0][i] if results.get('documents') else '',
                    score=score,
                    metadata=results['metadatas'][0][i] if results.get('metadatas') else {},
                ))

        return search_results

    def delete(self, doc_ids=None, filter=None, collection='default',
               delete_collection=False):
        """Delete documents from the index."""
        if delete_collection:
            try:
                self.client.delete_collection(name=collection)
                return {'deleted': True, 'collection': collection}
            except Exception as e:
                raise RAGClientError(f'Failed to delete collection: {str(e)}')

        try:
            col = self.client.get_collection(name=collection)
        except Exception:
            raise RAGClientError(f'Collection not found: {collection}')

        if doc_ids:
            # Look up chunk IDs by doc_id metadata
            all_deleted = []
            for doc_id in doc_ids:
                try:
                    results = col.get(where={'doc_id': doc_id})
                    if results and results['ids']:
                        col.delete(ids=results['ids'])
                        all_deleted.extend(results['ids'])
                except Exception:
                    pass

            return {'deleted_chunks': len(all_deleted), 'doc_ids': doc_ids}

        elif filter:
            try:
                results = col.get(where=filter)
                if results and results['ids']:
                    col.delete(ids=results['ids'])
                    return {'deleted_chunks': len(results['ids']), 'filter': filter}
                return {'deleted_chunks': 0, 'filter': filter}
            except Exception as e:
                raise RAGClientError(f'Failed to delete by filter: {str(e)}')
        else:
            return {'error': 'Provide doc_ids, filter, or delete_collection=True'}

    def list_collections(self):
        """List all collections."""
        collections = self.client.list_collections()
        result = []
        for col in collections:
            result.append({
                'name': col.name,
                'document_count': col.count(),
                'metadata': col.metadata,
            })
        return result

    def get_stats(self, collection='default'):
        """Get statistics for a collection."""
        try:
            col = self.client.get_collection(name=collection)
        except Exception:
            raise RAGClientError(f'Collection not found: {collection}')

        all_docs = col.get()
        doc_count = col.count()

        sources = set()
        languages = set()
        total_chars = 0

        if all_docs and all_docs.get('metadatas'):
            for meta in all_docs['metadatas']:
                if meta.get('source'):
                    sources.add(meta['source'])
                if meta.get('language'):
                    languages.add(meta['language'])

        if all_docs and all_docs.get('documents'):
            for doc in all_docs['documents']:
                total_chars += len(doc) if doc else 0

        return {
            'collection': collection,
            'document_count': doc_count,
            'unique_sources': list(sources),
            'total_characters': total_chars,
            'languages': list(languages),
            'metadata': col.metadata,
        }


_rag_client = None


def get_rag_client(storage_path=None) -> RAGClient:
    """Get or create the RAG client singleton."""
    global _rag_client
    if _rag_client is None:
        _rag_client = RAGClient(storage_path=storage_path)
    return _rag_client
