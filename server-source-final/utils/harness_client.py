"""Harness CD API client for deployments."""

import os
import time
import requests
import urllib3
from typing import Optional, List, Dict
from dataclasses import dataclass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class ExecutionStatus:
    execution_id: str
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: Optional[int] = None
    stages: List[Dict] = None
    harness_url: Optional[str] = None


@dataclass
class DeploymentResult:
    success: bool
    message: str
    service_name: str
    source_environment: str
    target_environment: str
    image_tag: str
    execution_id: Optional[str] = None
    harness_url: Optional[str] = None
    error: Optional[str] = None


class HarnessClientError(Exception):
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class HarnessClient:
    def __init__(self):
        self.api_url = os.environ.get('HARNESS_API_URL',
                                      'https://wellsfargo-prod.harness.io/gateway/pipeline/api')
        self.api_key = os.environ.get('HARNESS_API_KEY')
        self.account_id = os.environ.get('HARNESS_ACCOUNT_ID')
        self.org_id = os.environ.get('HARNESS_ORG_ID')
        self.project_id = os.environ.get('HARNESS_PROJECT_ID')
        self.pipeline_id = os.environ.get('HARNESS_PIPELINE_ID')
        self.ui_base_url = os.environ.get('HARNESS_UI_BASE_URL',
                                          'https://wellsfargo-prod.harness.io')

        if not self.api_key:
            raise HarnessClientError("HARNESS_API_KEY environment variable is required")

        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
        })
        self.session.verify = False

    def _request(self, method, url, params=None, data=None):
        try:
            response = self.session.request(
                method, url, params=params, json=data, timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise HarnessClientError(f'Request failed: {str(e)}')

        if response.status_code >= 400:
            raise HarnessClientError(
                f'Harness API error: {response.status_code}',
                status_code=response.status_code,
                response_body=response.text,
            )

        if response.status_code == 204:
            return {}

        return response.json()

    def _build_execution_url(self, execution_id):
        return (
            f'{self.ui_base_url}/ng/#/account/{self.account_id}'
            f'/cd/orgs/{self.org_id}/projects/{self.project_id}'
            f'/pipelines/{self.pipeline_id}/executions/{execution_id}/pipeline'
        )

    def get_pipeline_info(self, pipeline_id=None):
        pipeline_id = pipeline_id or self.pipeline_id
        url = f'{self.api_url}/pipelines/{pipeline_id}'
        params = {
            'accountIdentifier': self.account_id,
            'orgIdentifier': self.org_id,
            'projectIdentifier': self.project_id,
        }

        try:
            response = self._request('GET', url, params=params)
        except HarnessClientError:
            return None

        pipeline = response.get('data', {}).get('yamlPipeline')
        stages = self._extract_stages(pipeline) if pipeline else []

        return {
            'pipeline_id': pipeline_id,
            'name': response.get('data', {}).get('name'),
            'stages': stages,
        }

    def _extract_stages(self, pipeline):
        stages = []
        if not pipeline:
            return stages
        # Extract stage information from pipeline YAML structure
        if isinstance(pipeline, dict):
            for stage in pipeline.get('stages', []):
                stage_data = stage.get('stage', {})
                stages.append({
                    'identifier': stage_data.get('identifier'),
                    'name': stage_data.get('name'),
                    'type': stage_data.get('type'),
                })
        return stages

    def get_execution_status(self, execution_id):
        url = f'{self.api_url}/pipelines/execution/{execution_id}'
        params = {
            'accountIdentifier': self.account_id,
            'orgIdentifier': self.org_id,
            'projectIdentifier': self.project_id,
        }

        try:
            response = self._request('GET', url, params=params)
        except HarnessClientError:
            return ExecutionStatus(
                execution_id=execution_id,
                status='Unknown',
            )

        execution = response.get('data', {}).get('pipelineExecutionSummary', {})
        status = self._map_status(execution.get('status'))

        stages = []
        if execution.get('layoutNodeMap'):
            node_map = execution['pipelineExecutionSummary']['layoutNodeMap']
            for node in node_map.values():
                if node.get('nodeType') == 'STAGE':
                    stages.append({
                        'name': node.get('name'),
                        'status': self._map_status(node.get('status')),
                        'start_time': node.get('startTs'),
                        'end_time': node.get('endTs'),
                    })

        return ExecutionStatus(
            execution_id=execution_id,
            status=status,
            start_time=execution.get('startTs'),
            end_time=execution.get('endTs'),
            duration=(execution.get('endTs', 0) - execution.get('startTs', 0))
                     if execution.get('endTs') else None,
            stages=stages,
            harness_url=self._build_execution_url(execution_id),
        )

    def _map_status(self, status):
        status_map = {
            'Success': 'Success',
            'Running': 'Running',
            'Failed': 'Failed',
            'Aborted': 'Aborted',
            'Expired': 'Expired',
            'NotStarted': 'NotStarted',
            'ApprovalWaiting': 'ApprovalWaiting',
        }
        return status_map.get(status, status or 'Unknown')

    def trigger_deployment(self, image_tag, target_environment,
                           stage_identifier=None, input_set_id=None,
                           github_branch='develop'):
        base_url = self.ui_base_url
        url = f'{base_url}/gateway/pipeline/api/pipeline/execute/{self.pipeline_id}/stages'

        params = {
            'routingId': self.account_id,
            'accountIdentifier': self.account_id,
            'orgIdentifier': self.org_id,
            'projectIdentifier': self.project_id,
            'moduleType': '',
            'asyncPlanCreation': False,
        }

        if input_set_id:
            params['inputSetIdentifiers'] = input_set_id

        runtime_yaml = self._build_runtime_yaml(
            image_tag, github_branch, stage_identifier, target_environment,
        )

        data = {
            'runtimeInputYaml': runtime_yaml,
            'stageIdentifiers': [stage_identifier] if stage_identifier else [],
            'expressionValues': {},
        }

        try:
            response = self._request('POST', url, params=params, data=data)

            if response.get('status') == 'SUCCESS' and response.get('data'):
                plan_execution = response['data'].get('planExecution', {})
                execution_id = plan_execution.get('uuid')

                if execution_id:
                    return DeploymentResult(
                        success=True,
                        message='Deployment triggered successfully',
                        service_name='',
                        source_environment='',
                        target_environment=target_environment,
                        image_tag=image_tag,
                        execution_id=execution_id,
                        harness_url=self._build_execution_url(execution_id),
                    )

            return DeploymentResult(
                success=False,
                message='Failed to trigger deployment - no execution ID received',
                service_name='',
                source_environment='',
                target_environment=target_environment,
                image_tag=image_tag,
                error='No execution ID in response',
            )
        except HarnessClientError as e:
            return DeploymentResult(
                success=False,
                message=f'Failed to trigger deployment: {str(e)}',
                service_name='',
                source_environment='',
                target_environment=target_environment,
                image_tag=image_tag,
                error=str(e),
            )

    def _build_runtime_yaml(self, image_tag, github_branch, stage_identifier,
                            target_environment):
        yaml_content = (
            f'pipeline:\n'
            f'  identifier: {self.pipeline_id}\n'
            f'  stages:\n'
            f'    - stage:\n'
            f'        identifier: {stage_identifier}\n'
            f'        type: Deployment\n'
            f'        variables:\n'
            f'          - name: imageTag\n'
            f'            type: String\n'
            f'            value: {image_tag}\n'
            f'          - name: branch\n'
            f'            type: String\n'
            f'            value: {github_branch}'
        )
        return yaml_content

    def wait_for_deployment(self, execution_id, timeout_minutes=30,
                            poll_interval_seconds=15):
        max_wait_ms = timeout_minutes * 60
        start_time = time.time()
        terminal_states = ['Success', 'Failed', 'Aborted', 'Expired']

        while time.time() - start_time < max_wait_ms:
            status = self.get_execution_status(execution_id)

            if status.status in terminal_states:
                return status

            time.sleep(poll_interval_seconds)

        return ExecutionStatus(
            execution_id=execution_id,
            status='Timeout',
            harness_url=self._build_execution_url(execution_id),
        )

    def get_input_sets(self):
        url = f'{self.api_url}/inputSets'
        params = {
            'accountIdentifier': self.account_id,
            'orgIdentifier': self.org_id,
            'projectIdentifier': self.project_id,
            'pipelineIdentifier': self.pipeline_id,
        }

        try:
            response = self._request('GET', url, params=params)
        except HarnessClientError:
            return []

        if response.get('data', {}).get('content'):
            return [
                {
                    'identifier': item.get('identifier'),
                    'name': item.get('name'),
                }
                for item in response['data']['content']
            ]

        return []


_client_instance = None


def get_harness_client() -> HarnessClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = HarnessClient()
    return _client_instance
