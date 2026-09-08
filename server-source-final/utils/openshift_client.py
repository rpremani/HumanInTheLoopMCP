"""OpenShift/Kubernetes API client."""

import os
import subprocess
import requests
import urllib3
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_oc_token():
    """Get token from current oc CLI session."""
    try:
        result = subprocess.run(
            ['oc', 'whoami', '-t'],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Verify token works
            verify = subprocess.run(
                ['oc', 'whoami'],
                capture_output=True, text=True, timeout=10,
            )
            if verify.returncode == 0:
                return result.stdout.strip()
    except Exception:
        pass
    return None


def get_token_via_oauth():
    """Get token via OAuth browser-based login."""
    try:
        username = os.environ.get('OPENSHIFT_USERNAME')
        password = os.environ.get('OPENSHIFT_PASSWORD')
        console_url = os.environ.get('OPENSHIFT_CONSOLE_URL')
        from utils.openshift_oauth import login_sync
        result = login_sync(api_url=None, username=username, password=password,
                            console_url=console_url)
        if result and result.success and result.token:
            return result.token
    except Exception:
        pass
    return None


def get_oc_server():
    """Get the current OpenShift server URL from oc CLI."""
    try:
        result = subprocess.run(
            ['oc', 'whoami', '--show-server'],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_oc_console_url():
    """Get the OpenShift console URL."""
    try:
        result = subprocess.run(
            ['oc', 'get', 'route', 'console', '-n', 'openshift-console',
             '-o', 'jsonpath={.spec.host}'],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return f'https://{result.stdout.strip()}'
    except Exception:
        pass
    return None


def validate_oc_session():
    """Validate the current oc CLI session."""
    result = {
        'logged_in': False,
        'user': None,
        'server': None,
        'token_valid': False,
        'project': None,
        'error': None,
    }

    try:
        server_result = subprocess.run(
            ['oc', 'config', 'view', '--minify', '-o',
             'jsonpath={.clusters[0].cluster.server}'],
            capture_output=True, text=True, timeout=10,
        )
        if server_result.returncode == 0:
            result['server'] = server_result.stdout.strip()

        user_result = subprocess.run(
            ['oc', 'whoami'],
            capture_output=True, text=True, timeout=10,
        )
        if user_result.returncode == 0:
            result['logged_in'] = True
            result['token_valid'] = True
            result['user'] = user_result.stdout.strip()

        project_result = subprocess.run(
            ['oc', 'project', '-q'],
            capture_output=True, text=True, timeout=10,
        )
        if project_result.returncode == 0:
            result['project'] = project_result.stdout.strip()

    except Exception as e:
        result['error'] = str(e)

    return result


@dataclass
class PodInfo:
    name: str
    namespace: str
    status: str
    ready: bool
    restart_count: int
    node: Optional[str]
    start_time: Optional[str]
    containers: List[str]
    conditions: List[Dict]


@dataclass
class DeploymentInfo:
    name: str
    namespace: str
    replicas_desired: int
    replicas_ready: int
    replicas_available: int
    image_tag: Optional[str]
    status: str
    is_healthy: bool
    is_degraded: bool
    health_percentage: float
    last_updated: Optional[str]
    pods_url: Optional[str]


class OpenShiftClientError(Exception):
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class OpenShiftClient:
    def __init__(self, api_url=None, token=None, console_url=None):
        self.api_url = (
            api_url
            or os.environ.get('OPENSHIFT_API_URL')
            or get_oc_server()
        )

        self.token = None

        if token:
            self.token = token

        if not self.token:
            self.token = os.environ.get('OPENSHIFT_TOKEN')

        if not self.token:
            self.token = get_oc_token()

        if not self.token:
            self.token = get_token_via_oauth()

        self.console_url = (
            console_url
            or os.environ.get('OPENSHIFT_CONSOLE_URL')
            or get_oc_console_url()
        )

        if not self.api_url:
            raise OpenShiftClientError(
                "OpenShift API URL not found. Options:\n"
                "1. Set OPENSHIFT_API_URL environment variable\n"
                "2. Run 'oc login <url>' to establish a session"
            )

        if not self.token:
            has_creds = (
                os.environ.get('OPENSHIFT_USERNAME')
                and os.environ.get('OPENSHIFT_PASSWORD')
            )
            if has_creds:
                raise OpenShiftClientError(
                    "OAuth login failed. Please check:\n"
                    "1. OPENSHIFT_USERNAME and OPENSHIFT_PASSWORD are correct\n"
                    "2. Playwright is installed: pip install playwright && playwright install chromium\n"
                    "3. Network can reach the OAuth endpoint"
                )

            raise OpenShiftClientError(
                "OpenShift token not found. Options:\n"
                "1. Set OPENSHIFT_TOKEN environment variable\n"
                "2. Run 'oc login' manually to establish a session\n"
                "3. For automated OAuth: set OPENSHIFT_USERNAME + OPENSHIFT_PASSWORD"
            )

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
        })
        self.session.verify = False

    def _request(self, method, endpoint, **kwargs):
        url = f'{self.api_url}{endpoint}'
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
        except requests.exceptions.RequestException as e:
            raise OpenShiftClientError(f'Request failed: {str(e)}')

        if response.status_code >= 400:
            raise OpenShiftClientError(
                f'OpenShift API error: {response.status_code}',
                status_code=response.status_code,
                response_body=response.text,
            )

        if response.status_code == 204:
            return {}

        return response.json()

    def _get(self, endpoint, **kwargs):
        return self._request('GET', endpoint, **kwargs)

    def get_deployment(self, namespace: str, deployment_name: str):
        try:
            endpoint = f'/apis/apps/v1/namespaces/{namespace}/deployments/{deployment_name}'
            data = self._get(endpoint)
            return self._map_deployment(data, namespace)
        except OpenShiftClientError as e:
            if e.status_code == 404:
                return None
            raise

    def list_deployments(self, namespace: str):
        endpoint = f'/apis/apps/v1/namespaces/{namespace}/deployments'
        data = self._get(endpoint)
        deployments = []
        for item in data.get('items', []):
            dep = self._map_deployment(item, namespace)
            if dep:
                deployments.append(dep)
        return deployments

    def _map_deployment(self, data, namespace):
        spec = data.get('spec', {})
        status = data.get('status', {})
        metadata = data.get('metadata', {})

        replicas_desired = spec.get('replicas', 0)
        replicas_ready = status.get('readyReplicas', 0)
        replicas_available = status.get('availableReplicas', 0)

        containers = spec.get('template', {}).get('spec', {}).get('containers', [])
        image_tag = None
        if containers:
            image = containers[0].get('image', '')
            if ':' in image:
                image_tag = image.split(':')[-1]

        is_healthy = replicas_ready == replicas_desired and replicas_desired > 0
        is_degraded = replicas_ready > 0 and replicas_ready < replicas_desired

        if is_healthy:
            dep_status = 'healthy'
        elif is_degraded:
            dep_status = 'degraded'
        elif replicas_desired == 0:
            dep_status = 'scaled_down'
        else:
            dep_status = 'unhealthy'

        health_percentage = (replicas_ready / replicas_desired * 100) if replicas_desired > 0 else 0

        pods_url = None
        if self.console_url:
            pods_url = (
                f'{self.console_url}/k8s/ns/{namespace}'
                f'/deployments/{metadata.get("name")}/pods'
            )

        return DeploymentInfo(
            name=metadata.get('name', ''),
            namespace=namespace,
            replicas_desired=replicas_desired,
            replicas_ready=replicas_ready,
            replicas_available=replicas_available,
            image_tag=image_tag,
            status=dep_status,
            is_healthy=is_healthy,
            is_degraded=is_degraded,
            health_percentage=health_percentage,
            last_updated=metadata.get('creationTimestamp'),
            pods_url=pods_url,
        )

    def get_pods(self, namespace: str, deployment_name: str = None,
                 label_selector: str = None) -> List[PodInfo]:
        endpoint = f'/api/v1/namespaces/{namespace}/pods'
        params = {}
        if label_selector:
            params['labelSelector'] = label_selector
        elif deployment_name:
            params['labelSelector'] = f'app={deployment_name}'

        data = self._get(endpoint, params=params)
        pods = []
        for item in data.get('items', []):
            pod = self._map_pod(item)
            if pod:
                if deployment_name:
                    labels = item.get('metadata', {}).get('labels', {})
                    if (labels.get('app') == deployment_name
                            or labels.get('app.kubernetes.io/name') == deployment_name):
                        pods.append(pod)
                else:
                    pods.append(pod)
        return pods

    def _map_pod(self, data) -> PodInfo:
        metadata = data.get('metadata', {})
        spec = data.get('spec', {})
        status = data.get('status', {})

        containers = [c.get('name') for c in spec.get('containers', [])]

        container_statuses = status.get('containerStatuses', [])
        restart_count = sum(cs.get('restartCount', 0) for cs in container_statuses)

        conditions = status.get('conditions', [])
        ready = any(
            c.get('type') == 'Ready' and c.get('status') == 'True'
            for c in conditions
        )

        return PodInfo(
            name=metadata.get('name', ''),
            namespace=metadata.get('namespace', ''),
            status=status.get('phase', 'Unknown'),
            ready=ready,
            restart_count=restart_count,
            node=spec.get('nodeName'),
            start_time=status.get('startTime'),
            containers=containers,
            conditions=conditions,
        )

    def get_pod_logs(self, namespace: str, pod_name: str, container: str = None,
                     tail_lines: int = 100, previous: bool = False) -> str:
        endpoint = f'/api/v1/namespaces/{namespace}/pods/{pod_name}/log'
        params = {'tailLines': tail_lines}
        if container:
            params['container'] = container
        if previous:
            params['previous'] = 'true'

        url = f'{self.api_url}{endpoint}'
        try:
            response = self.session.get(url, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            raise OpenShiftClientError(f'Request failed: {str(e)}')

        if response.status_code >= 400:
            raise OpenShiftClientError(
                f'Failed to get pod logs: {response.status_code}',
                status_code=response.status_code,
                response_body=response.text,
            )

        return response.text

    def get_pod_events(self, namespace: str, pod_name: str = None) -> List[Dict]:
        endpoint = f'/api/v1/namespaces/{namespace}/events'
        params = {}
        if pod_name:
            params['fieldSelector'] = f'involvedObject.name={pod_name}'

        data = self._get(endpoint, params=params)
        events = []
        for item in data.get('items', []):
            events.append({
                'type': item.get('type'),
                'reason': item.get('reason'),
                'message': item.get('message'),
                'count': item.get('count', 1),
                'first_timestamp': item.get('firstTimestamp'),
                'last_timestamp': item.get('lastTimestamp'),
                'source': item.get('source', {}).get('component'),
                'involved_object': item.get('involvedObject', {}).get('name'),
            })

        events.sort(key=lambda x: x.get('last_timestamp') or '', reverse=True)
        return events

    def check_deployment_health(self, namespace: str, deployment_name: str) -> Dict[str, Any]:
        deployment = self.get_deployment(namespace, deployment_name)

        if not deployment:
            return {
                'found': False,
                'healthy': False,
                'message': f'Deployment {deployment_name} not found in namespace {namespace}',
            }

        pods = self.get_pods(namespace, deployment_name)

        pod_summary = {
            'total': len(pods),
            'running': sum(1 for p in pods if p.status == 'Running'),
            'ready': sum(1 for p in pods if p.ready),
            'crashed': sum(1 for p in pods if p.restart_count > 5),
            'pending': sum(1 for p in pods if p.status == 'Pending'),
        }

        recent_events = []
        for pod in pods[:3]:
            events = self.get_pod_events(namespace, pod.name)
            warning_events = [e for e in events if e.get('type') == 'Warning'][:5]
            recent_events.extend(warning_events)

        return {
            'found': True,
            'deployment': asdict(deployment),
            'healthy': deployment.is_healthy,
            'status': deployment.status,
            'pods': pod_summary,
            'recent_warnings': recent_events[:10],
            'message': (
                f'Deployment is {deployment.status}. '
                f'{pod_summary["ready"]}/{pod_summary["total"]} pods ready.'
            ),
        }


_client_instance = None


def get_openshift_client() -> OpenShiftClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = OpenShiftClient()
    return _client_instance
