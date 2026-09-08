"""GitHub API client for PR review operations."""

import os
import base64
import requests
import urllib3
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class PRFile:
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: Optional[str]
    previous_filename: Optional[str]


@dataclass
class PRComment:
    id: int
    user: str
    body: str
    created_at: str
    path: Optional[str] = None
    line: Optional[int] = None


@dataclass
class PRReview:
    id: int
    user: str
    state: str
    body: Optional[str]
    submitted_at: Optional[str]


@dataclass
class PRInfo:
    number: int
    title: str
    description: Optional[str]
    author: str
    state: str
    base_branch: str
    head_branch: str
    created_at: str
    updated_at: str
    mergeable: Optional[bool]
    mergeable_state: Optional[str]
    additions: int
    deletions: int
    changed_files_count: int
    commits_count: int
    files: List[PRFile]
    comments: List[PRComment]
    reviews: List[PRReview]
    labels: List[str]
    url: str


class GitHubClientError(Exception):
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class GitHubClient:
    BASE_URL = 'https://api.github.com'

    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN')
        self.base_url = os.environ.get('GITHUB_API_URL', self.BASE_URL)

        if not self.token:
            raise GitHubClientError("GITHUB_TOKEN environment variable is required")

        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
        })

    def _request(self, method, endpoint, **kwargs):
        url = f'{self.base_url}{endpoint}'
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
        except requests.exceptions.RequestException as e:
            raise GitHubClientError(f'Request failed: {str(e)}')

        if response.status_code >= 400:
            raise GitHubClientError(
                f'GitHub API error: {response.status_code}',
                status_code=response.status_code,
                response_body=response.text,
            )

        if response.status_code == 204:
            return {}

        return response.json()

    def _get(self, endpoint, **kwargs):
        return self._request('GET', endpoint, **kwargs)

    def _post(self, endpoint, **kwargs):
        return self._request('POST', endpoint, **kwargs)

    def _get_paginated(self, endpoint, per_page=100, max_items=None):
        items = []
        page = 1

        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(endpoint, params=params)

            if not response:
                break

            if isinstance(response, dict):
                for key in ('items', 'values', 'data'):
                    if key in response:
                        response = response[key]
                        break
                else:
                    items.append(response)
                    break
            else:
                items.extend(response)

            if max_items and len(items) >= max_items:
                items = items[:max_items]
                break

            if len(response) < per_page:
                break

            page += 1

        return items

    def get_pr(self, owner, repo, pr_number):
        return self._get(f'/repos/{owner}/{repo}/pulls/{pr_number}')

    def get_pr_files(self, owner, repo, pr_number):
        return self._get_paginated(f'/repos/{owner}/{repo}/pulls/{pr_number}/files')

    def get_pr_comments(self, owner, repo, pr_number):
        return self._get_paginated(f'/repos/{owner}/{repo}/pulls/{pr_number}/comments')

    def get_pr_reviews(self, owner, repo, pr_number):
        return self._get_paginated(f'/repos/{owner}/{repo}/pulls/{pr_number}/reviews')

    def get_issue_comments(self, owner, repo, pr_number):
        return self._get_paginated(f'/repos/{owner}/{repo}/issues/{pr_number}/comments')

    def get_file_content(self, owner, repo, path, ref):
        """Get file content from a repository.

        Retrieves the content of a file from GitHub, handling base64 decoding
        if necessary.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path to the file
            ref: Git reference (branch, tag, or SHA)

        Returns:
            The decoded file content as a string
        """
        response = self._get(
            f'/repos/{owner}/{repo}/contents/{path}',
            params={'ref': ref},
        )

        if response.get('encoding') == 'base64':
            content = base64.b64decode(response['content']).decode('utf-8')
        else:
            content = response.get('content', '')

        return content

    def get_pr_for_review(self, owner, repo, pr_number):
        """Get comprehensive PR information for review.

        Retrieves PR metadata, files, comments, and reviews in a single call.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            PRInfo dataclass with all PR information
        """
        pr = self.get_pr(owner, repo, pr_number)

        files_raw = self.get_pr_files(owner, repo, pr_number)
        files = [
            PRFile(
                filename=f['filename'],
                status=f['status'],
                additions=f.get('additions', 0),
                deletions=f.get('deletions', 0),
                changes=f.get('changes', 0),
                patch=f.get('patch'),
                previous_filename=f.get('previous_filename'),
            )
            for f in files_raw
        ]

        review_comments_raw = self.get_pr_comments(owner, repo, pr_number)

        issue_comments_raw = self.get_issue_comments(owner, repo, pr_number)

        comments = []
        for c in review_comments_raw:
            comments.append(PRComment(
                id=c['id'],
                user=c['user']['login'],
                body=c['body'],
                created_at=c['created_at'],
                path=c.get('path'),
                line=c.get('line') or c.get('original_line'),
            ))

        for c in issue_comments_raw:
            comments.append(PRComment(
                id=c['id'],
                user=c['user']['login'],
                body=c['body'],
                created_at=c['created_at'],
            ))

        comments.sort(key=lambda x: x.created_at)

        reviews_raw = self.get_pr_reviews(owner, repo, pr_number)
        reviews = [
            PRReview(
                id=r['id'],
                user=r['user']['login'],
                state=r['state'],
                body=r.get('body'),
                submitted_at=r.get('submitted_at'),
            )
            for r in reviews_raw
        ]

        return PRInfo(
            number=pr['number'],
            title=pr['title'],
            description=pr.get('body'),
            author=pr['user']['login'],
            state=pr['state'],
            base_branch=pr['base']['ref'],
            head_branch=pr['head']['ref'],
            created_at=pr['created_at'],
            updated_at=pr['updated_at'],
            mergeable=pr.get('mergeable'),
            mergeable_state=pr.get('mergeable_state'),
            additions=pr.get('additions', 0),
            deletions=pr.get('deletions', 0),
            changed_files_count=pr.get('changed_files', len(files)),
            commits_count=pr.get('commits', 0),
            files=files,
            comments=comments,
            reviews=reviews,
            labels=[l['name'] for l in pr.get('labels', [])],
            url=pr['html_url'],
        )

    def get_file_from_pr(self, owner, repo, pr_number, file_path, version='head'):
        """Get file content from a specific PR version.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            file_path: Path to file in the repo
            version: 'head' for PR version, 'base' for original

        Returns:
            File content as string
        """
        pr = self.get_pr(owner, repo, pr_number)

        if version == 'head':
            ref = pr['head']['sha']
        else:
            ref = pr['base']['sha']

        return self.get_file_content(owner, repo, file_path, ref)

    def create_review_comment(self, owner, repo, pr_number, body, commit_id=None,
                              path=None, line=None, side='RIGHT',
                              start_line=None, start_side=None):
        data = {
            'body': body,
            'commit_id': commit_id,
            'path': path,
            'side': side,
        }

        if line:
            data['line'] = line

        if start_line:
            data['start_line'] = start_line
            data['start_side'] = start_side or side

        return self._post(
            f'/repos/{owner}/{repo}/pulls/{pr_number}/comments',
            json=data,
        )

    def create_review(self, owner, repo, pr_number, event, body=None, comments=None):
        data = {'event': event}

        if body:
            data['body'] = body

        if comments:
            data['comments'] = comments

        return self._post(
            f'/repos/{owner}/{repo}/pulls/{pr_number}/reviews',
            json=data,
        )

    def add_issue_comment(self, owner, repo, pr_number, body):
        """Add a comment to an issue or pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Issue/PR number
            body: Comment body text

        Returns:
            API response dict
        """
        return self._post(
            f'/repos/{owner}/{repo}/issues/{pr_number}/comments',
            json={'body': body},
        )

    def _put(self, endpoint, **kwargs):
        return self._request('PUT', endpoint, **kwargs)

    def merge_pr(self, owner, repo, pr_number, merge_method='squash',
                 commit_title=None, commit_message=None):
        data = {'merge_method': merge_method}

        if commit_title:
            data['commit_title'] = commit_title

        if commit_message:
            data['commit_message'] = commit_message

        return self._put(
            f'/repos/{owner}/{repo}/pulls/{pr_number}/merge',
            json=data,
        )


def pr_info_to_dict(pr_info: PRInfo) -> Dict:
    result = asdict(pr_info)
    result['files'] = [asdict(f) for f in pr_info.files]
    result['comments'] = [asdict(c) for c in pr_info.comments]
    result['reviews'] = [asdict(r) for r in pr_info.reviews]
    return result


_client: Optional[GitHubClient] = None


def get_github_client() -> GitHubClient:
    global _client
    if _client is None:
        _client = GitHubClient()
    return _client
