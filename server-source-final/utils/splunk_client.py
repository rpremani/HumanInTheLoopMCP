"""Splunk REST API client for log search."""

import os
import time
import json
import requests
import urllib3
from typing import Optional, List, Dict
from dataclasses import dataclass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class SearchResult:
    total_count: int
    events: List[Dict]
    messages: List[str]
    is_complete: bool


class SplunkClientError(Exception):
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SplunkClient:
    def __init__(self):
        self.base_url = os.environ.get('SPLUNK_URL')
        token = os.environ.get('SPLUNK_TOKEN')
        username = os.environ.get('SPLUNK_USERNAME')
        password = os.environ.get('SPLUNK_PASSWORD')

        if not self.base_url:
            raise SplunkClientError("SPLUNK_URL environment variable is required")

        if not token and not (username and password):
            raise SplunkClientError(
                "Either SPLUNK_TOKEN or SPLUNK_USERNAME+SPLUNK_PASSWORD is required"
            )

        self.session = requests.Session()
        self.session.verify = False

        if token:
            self.session.headers.update({
                'Authorization': f'Bearer {token}',
            })
        else:
            self.session.auth = (username, password)

    def _post(self, endpoint, data, params=None):
        url = f'{self.base_url}/services{endpoint}'
        try:
            response = self.session.post(url, data=data, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            raise SplunkClientError(f'Request failed: {str(e)}')

        if response.status_code >= 400:
            raise SplunkClientError(
                f'Splunk API error: {response.status_code}',
                status_code=response.status_code,
            )

        return response

    def _get(self, endpoint, params=None):
        url = f'{self.base_url}/services{endpoint}'
        if params is None:
            params = {}
        params['output_mode'] = 'json'

        try:
            response = self.session.get(url, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            raise SplunkClientError(f'Request failed: {str(e)}')

        if response.status_code >= 400:
            raise SplunkClientError(
                f'Splunk API error: {response.status_code}',
                status_code=response.status_code,
            )

        return response.json()

    def search(self, query, earliest_time='-1h', latest_time='now',
               max_results=100, timeout_seconds=60):
        data = {
            'search': f'search {query}',
            'earliest_time': earliest_time,
            'latest_time': latest_time,
            'output_mode': 'json',
        }

        response = self._post('/search/jobs', data=data)

        # Extract SID from response
        try:
            sid = response.json()['sid']
        except (json.JSONDecodeError, KeyError):
            # Fallback: try XML parsing
            import re
            match = re.search(r'<sid>(.*?)</sid>', response.text)
            if match:
                sid = match.group(1)
            else:
                raise SplunkClientError("Could not extract search job SID")

        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            status_response = self._get(f'/search/jobs/{sid}')
            dispatch_state = status_response.get('entry', [{}])[0].get(
                'content', {}
            ).get('dispatchState', '')

            if dispatch_state == 'DONE':
                break

            if dispatch_state == 'FAILED':
                raise SplunkClientError("Search job failed")

            time.sleep(1)

        # Get results
        results_response = self._get(
            f'/search/jobs/{sid}/results',
            params={'count': max_results},
        )

        events = results_response.get('results', [])
        messages = [m.get('text', '') for m in results_response.get('messages', [])]

        return SearchResult(
            total_count=len(events),
            events=events,
            messages=messages,
            is_complete=True,
        )

    def search_errors(self, index=None, source=None, sourcetype=None,
                      host=None, time_range='-1h', max_results=50):
        parts = []

        if index:
            parts.append(f'index="{index}"')
        if source:
            parts.append(f'source="{source}"')
        if sourcetype:
            parts.append(f'sourcetype="{sourcetype}"')
        if host:
            parts.append(f'host="{host}"')

        parts.append('(ERROR OR FATAL OR Exception)')

        query = ' '.join(parts)

        return self.search(
            query,
            earliest_time=time_range,
            max_results=max_results,
        )

    def search_by_trace_id(self, trace_id, index=None, time_range='-1h'):
        parts = []

        if index:
            parts.append(f'index="{index}"')

        parts.append(f'"{trace_id}"')
        query = ' '.join(parts) + ' | sort _time'

        return self.search(
            query,
            earliest_time=time_range,
            max_results=200,
        )

    def get_error_summary(self, index=None, source=None, time_range='-1h'):
        parts = []

        if index:
            parts.append(f'index="{index}"')
        if source:
            parts.append(f'source="{source}"')

        parts.append('(ERROR OR FATAL OR Exception)')
        query = ' '.join(parts) + (
            ' | rex field=_raw "(?<error_type>\\w+Exception|\\w+Error)"'
            ' | stats count by error_type | sort -count | head 20'
        )

        result = self.search(query, earliest_time=time_range)

        return {
            'total_errors': sum(int(e.get('count', 0)) for e in result.events),
            'by_type': result.events,
        }


_client_instance = None


def get_splunk_client() -> SplunkClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = SplunkClient()
    return _client_instance
