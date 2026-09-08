"""Embedding client using GitHub Copilot's embedding API."""

import os
import json
import uuid
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


GITHUB_API_BASE_URL = 'https://api.github.com'
COPILOT_TOKEN_URL = f'{GITHUB_API_BASE_URL}/copilot_internal/v2/token'
COPILOT_EMBEDDINGS_URL = 'https://api.githubcopilot.com/embeddings'

COPILOT_VERSION = '0.26.7'
VSCODE_VERSION = '1.98.0'
API_VERSION = '2025-04-01'

DEFAULT_EMBEDDING_MODEL = 'text-embedding-3-small-inference'
MAX_BATCH_SIZE = 100


@dataclass
class EmbeddingResult:
    embeddings: List[List[float]]
    model: str
    dimensions: int
    token_usage: Dict[str, int]
    time_seconds: float


class EmbeddingClientError(Exception):
    pass


class EmbeddingClient:
    """Client for generating embeddings via GitHub Copilot API."""

    def __init__(self, model=DEFAULT_EMBEDDING_MODEL):
        self.model = model
        self._github_token = None
        self._copilot_token = None
        self._copilot_token_expires = None

        # Proxy configuration
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        self._proxies = None
        if http_proxy or https_proxy:
            self._proxies = {}
            if http_proxy:
                self._proxies['http'] = http_proxy
            if https_proxy:
                self._proxies['https'] = https_proxy

    def _get_proxies(self):
        """Get proxy configuration."""
        return self._proxies

    def _load_github_token(self):
        """Load GitHub token from Copilot apps.json."""
        if self._github_token:
            return self._github_token

        local_app_data = os.environ.get('LOCALAPPDATA', '')
        if not local_app_data:
            raise EmbeddingClientError(
                'LOCALAPPDATA environment variable not set. '
                'Cannot find GitHub Copilot token.'
            )

        apps_json_path = Path(local_app_data) / 'github-copilot' / 'apps.json'
        if not apps_json_path.exists():
            raise EmbeddingClientError(
                f'GitHub Copilot apps.json not found at {apps_json_path}. '
                'Ensure GitHub Copilot is installed and authenticated.'
            )

        try:
            with open(apps_json_path, 'r') as f:
                apps_data = json.load(f)
        except Exception as e:
            raise EmbeddingClientError(f'Failed to read apps.json: {str(e)}')

        for key, value in apps_data.items():
            if isinstance(value, dict) and 'oauth_token' in value:
                self._github_token = value['oauth_token']
                return self._github_token

        raise EmbeddingClientError(
            'No oauth_token found in apps.json. '
            'Ensure GitHub Copilot is authenticated.'
        )

    def _get_github_headers(self):
        """Get headers for GitHub API requests."""
        token = self._load_github_token()
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'token {token}',
            'editor-version': f'vscode/{VSCODE_VERSION}',
            'editor-plugin-version': f'copilot-chat/{COPILOT_VERSION}',
            'user-agent': f'GitHubCopilotChat/{COPILOT_VERSION}',
            'x-github-api-version': API_VERSION,
        }

    def _get_copilot_headers(self):
        """Get headers for Copilot API requests."""
        token = self._get_copilot_token()
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}',
            'copilot-integration-id': 'vscode-chat',
            'x-request-id': str(uuid.uuid4()),
        }

    def _get_copilot_token(self):
        """Get or refresh the Copilot API token."""
        now = time.time()

        # Check if we have a valid cached token (25-minute expiry buffer)
        if self._copilot_token and self._copilot_token_expires:
            if now < self._copilot_token_expires - (25 * 60):
                return self._copilot_token

        headers = self._get_github_headers()

        try:
            response = requests.get(
                COPILOT_TOKEN_URL,
                headers=headers,
                proxies=self._get_proxies(),
                timeout=30,
                verify=False,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise EmbeddingClientError(f'Failed to get Copilot token: {str(e)}')

        data = response.json()
        self._copilot_token = data['token']

        if 'expires_at' in data:
            self._copilot_token_expires = data['expires_at']
        else:
            # Default 30 min expiry
            self._copilot_token_expires = now + (30 * 60)

        return self._copilot_token

    def embed(self, texts: Union[str, List[str]], model=None) -> EmbeddingResult:
        """Generate embeddings for one or more texts."""
        start_time = time.time()

        if isinstance(texts, str):
            texts = [texts]

        model = model or self.model
        all_embeddings = []
        total_usage = {'prompt_tokens': 0, 'total_tokens': 0}

        # Process in batches
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i:i + MAX_BATCH_SIZE]

            payload = {
                'input': batch,
                'model': model,
            }

            headers = self._get_copilot_headers()

            try:
                response = requests.post(
                    COPILOT_EMBEDDINGS_URL,
                    headers=headers,
                    json=payload,
                    proxies=self._get_proxies(),
                    timeout=60,
                    verify=False,
                )
                response.raise_for_status()
            except requests.RequestException as e:
                raise EmbeddingClientError(f'Embedding API request failed: {str(e)}')

            response_data = response.json()

            # Sort by index to ensure correct order
            batch_data = sorted(response_data['data'], key=lambda x: x['index'])
            batch_embeddings = [item['embedding'] for item in batch_data]
            all_embeddings.extend(batch_embeddings)

            # Accumulate token usage
            if 'usage' in response_data:
                usage = response_data['usage']
                total_usage['prompt_tokens'] += usage.get('prompt_tokens', 0)
                total_usage['total_tokens'] += usage.get('total_tokens', 0)

        elapsed = time.time() - start_time

        dimensions = len(all_embeddings[0]) if all_embeddings else 0

        return EmbeddingResult(
            embeddings=all_embeddings,
            model=model,
            dimensions=dimensions,
            token_usage=total_usage,
            time_seconds=round(elapsed, 3),
        )

    def embed_single(self, text: str, model=None) -> List[float]:
        """Generate embedding for a single text."""
        result = self.embed([text], model=model)
        return result.embeddings[0]


_embedding_client = None


def get_embedding_client(model=DEFAULT_EMBEDDING_MODEL) -> EmbeddingClient:
    """Get or create the embedding client singleton."""
    global _embedding_client
    if _embedding_client is None or _embedding_client.model != model:
        _embedding_client = EmbeddingClient(model=model)
    return _embedding_client
