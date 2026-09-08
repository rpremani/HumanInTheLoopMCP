"""OpenShift token retrieval via Playwright browser automation.

Flow:
1. Navigate to console URL
2. Click "standard" auth provider if present
3. Fill credentials (username/password)
4. Click #signOnButton (submit)
5. Open User menu
6. Click "Copy login command"
7. Click "Display Token"
8. Extract sha256~ token from page
"""

import os
import re
import asyncio
import subprocess
from typing import Optional
from dataclasses import dataclass


@dataclass
class TokenResult:
    success: bool
    token: Optional[str] = None
    error: Optional[str] = None
    server: Optional[str] = None
    expires_at: Optional[str] = None


def _extract_sha256_token(text):
    """Extract sha256~ token from text."""
    if not text:
        return None
    match = re.search(r'(sha256~[A-Za-z0-9_-]+)', text)
    return match.group(1) if match else None


def _extract_server_url(text):
    """Extract server URL from text, stripping HTML tags."""
    if not text:
        return None
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    # Try --server= pattern
    match = re.search(r'--server=\s*(https://[^\s]+)', clean)
    if match:
        return match.group(1)
    # Try oc login pattern
    match = re.search(r'oc login (https://[^\s]+)', clean)
    if match:
        return match.group(1)
    return None


async def _maybe_click_standard(page, timeout_ms):
    """Click 'standard' auth provider button if present."""
    try:
        standard_btn = page.locator(
            'button:has-text("standard"), a:has-text("standard")'
        ).first
        await standard_btn.click(timeout=timeout_ms // 10)
        await page.wait_for_timeout(1000)
    except Exception:
        pass


async def _perform_login_if_needed(page, username, password, timeout_ms):
    """Fill login form and submit if login page is detected."""
    try:
        username_field = page.locator(
            'input[name="username"], input#inputUsername, input[type="text"]'
        ).first
        await username_field.fill(username, timeout=timeout_ms // 10)

        password_field = page.locator(
            'input[name="password"], input#inputPassword, input[type="password"]'
        ).first
        await password_field.fill(password, timeout=timeout_ms // 10)

        submit_btn = page.locator(
            '#signOnButton, button[type="submit"], input[type="submit"]'
        ).first
        await submit_btn.click()

        await page.wait_for_timeout(3000)
    except Exception:
        pass


async def get_token_via_playwright(api_url=None, username=None, password=None,
                                   console_url=None, headless=True,
                                   timeout_ms=60000):
    """Get OpenShift token via Playwright browser automation."""
    try:
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        return TokenResult(
            success=False,
            error='Playwright is not installed. Run: pip install playwright && playwright install chromium',
        )

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                channel='chrome',
                args=['--ignore-certificate-errors'],
            )
            try:
                context = await browser.new_context(
                    ignore_https_errors=True,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    viewport={'width': 1920, 'height': 1080},
                )

                page = await context.new_page()
                page.set_default_timeout(timeout_ms)

                try:
                    print(f'Navigating to {console_url}...')
                    await page.goto(console_url, wait_until='domcontentloaded',
                                    timeout=timeout_ms)
                    print('Page loaded, waiting for stabilization...')

                    await page.wait_for_timeout(2000)

                    print('Checking if login is needed...')
                    await _perform_login_if_needed(page, username, password, timeout_ms)
                    print('Login check complete')

                    # Open user menu
                    print('Opening user menu...')
                    user_menu = page.locator(
                        'button[aria-label="User menu"], '
                        'button:has-text("kube:admin"), '
                        '[data-test="user-dropdown"]'
                    ).first
                    await user_menu.click()
                    print('User menu opened')

                    # Click Copy login command
                    print("Clicking 'Copy login command'...")
                    async with page.expect_popup(timeout=timeout_ms) as popup_info:
                        await page.locator(
                            'a:has-text("Copy login command"), '
                            'button:has-text("Copy login command")'
                        ).first.click()

                    token_page = await popup_info.value
                    print('Login command page opened')

                    await token_page.wait_for_load_state('domcontentloaded',
                                                         timeout=timeout_ms)
                    await token_page.wait_for_timeout(2000)

                    # Check for auth in new window
                    print('Checking for auth in new window...')
                    await _maybe_click_standard(token_page, timeout_ms)
                    await token_page.wait_for_timeout(2000)

                    # Click Display Token
                    print("Clicking 'Display Token'...")
                    await token_page.locator(
                        'button:has-text("Display Token"), '
                        'a:has-text("Display Token")'
                    ).first.click()
                    await token_page.wait_for_timeout(1000)
                    print('Token displayed')

                    # Extract token and server URL
                    print('Extracting token and server URL...')
                    text_candidates = []

                    try:
                        first_text = await token_page.locator(
                            'code, pre, input[type="text"], '
                            '.pf-c-clipboard-copy__text'
                        ).first.text_content()
                        if first_text:
                            text_candidates.append(first_text)
                    except Exception:
                        pass

                    try:
                        html = await token_page.content()
                        text_candidates.append(html)
                    except Exception:
                        pass

                    token = None
                    server_url = None
                    for candidate in text_candidates:
                        if not token:
                            token = _extract_sha256_token(candidate)
                        if not server_url:
                            server_url = _extract_server_url(candidate)
                        if token and server_url:
                            break

                    if not token:
                        return TokenResult(
                            success=False,
                            error="Could not extract token from the 'Copy login command' flow. "
                                  "UI structure may have changed or login failed.",
                        )

                    print(f'Token extracted: {token[:20]}...')
                    if server_url:
                        print(f'Server URL extracted: {server_url}')
                    else:
                        print(f'Server URL not found, using provided API URL: {api_url}')
                        server_url = api_url

                    return TokenResult(
                        success=True,
                        token=token,
                        server=server_url,
                    )

                except PlaywrightTimeout:
                    return TokenResult(
                        success=False,
                        error='Timeout waiting for page to load. '
                              'Check credentials and network connectivity.',
                    )
            finally:
                await browser.close()
    except Exception as e:
        return TokenResult(
            success=False,
            error=f'Browser automation failed: {str(e)}',
        )


async def login_and_get_token(api_url=None, username=None, password=None,
                              use_oc_login=True, headless=True):
    """Login to OpenShift and get token, optionally running oc login."""
    api_url_for_login = api_url or os.environ.get('OPENSHIFT_API_URL')
    console_url = os.environ.get('OPENSHIFT_CONSOLE_URL')
    username = username or os.environ.get('OPENSHIFT_USERNAME')
    password = password or os.environ.get('OPENSHIFT_PASSWORD')

    if not console_url:
        return TokenResult(
            success=False,
            error='OPENSHIFT_CONSOLE_URL is required for browser-based login. '
                  'Set OPENSHIFT_CONSOLE_URL (the web console URL), then call ocp_login again.',
        )

    if not console_url:
        return TokenResult(
            success=False,
            error='OPENSHIFT_CONSOLE_URL is required',
        )
    if not username:
        return TokenResult(
            success=False,
            error='OPENSHIFT_USERNAME is required',
        )
    if not password:
        return TokenResult(
            success=False,
            error='OPENSHIFT_PASSWORD is required',
        )

    result = await get_token_via_playwright(
        api_url=console_url,
        username=username,
        password=password,
        console_url=console_url,
        headless=headless,
    )

    if result.success and result.token and use_oc_login:
        try:
            login_url = result.server or api_url_for_login or console_url

            print(f'Running oc login to {login_url}...')
            login_result = subprocess.run(
                ['oc', 'login', login_url, '--token', result.token,
                 '--insecure-skip-tls-verify'],
                capture_output=True,
                text=True,
                timeout=30,
            )

            print(f'oc login exit code: {login_result.returncode}')
            if login_result.stdout:
                print(f'oc login stdout: {login_result.stdout}')
            if login_result.stderr:
                print(f'oc login stderr: {login_result.stderr}')

            if login_result.returncode != 0:
                stderr = (login_result.stderr or '').strip()
                if stderr:
                    result.error = f'Warning: oc login failed (token still returned): {stderr}'
                else:
                    result.error = 'Warning: oc login failed (token still returned).'
        except Exception as e:
            print(f'oc login exception: {e}')
            result.error = f'Warning: oc login failed (token still returned): {str(e)}'

    return result


def get_cached_token():
    """Get cached token from oc CLI."""
    try:
        result = subprocess.run(
            ['oc', 'whoami', '-t'],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


async def ensure_valid_token(api_url=None, username=None, password=None):
    """Ensure we have a valid token, refreshing if needed."""
    try:
        result = subprocess.run(
            ['oc', 'whoami'],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            token = get_cached_token()
            return TokenResult(
                success=True,
                token=token,
                server=api_url or os.environ.get('OPENSHIFT_API_URL'),
            )
    except Exception:
        pass

    return await login_and_get_token(api_url, username, password)


def get_token_sync(api_url, username, password, console_url=None):
    """Synchronous wrapper for get_token_via_playwright."""
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                get_token_via_playwright(api_url, username, password, console_url),
            )
            return future.result(timeout=120)
    except RuntimeError:
        return asyncio.run(
            get_token_via_playwright(api_url, username, password, console_url),
        )


def login_sync(api_url=None, username=None, password=None, console_url=None):
    """Synchronous wrapper for login_and_get_token."""
    if console_url and not os.environ.get('OPENSHIFT_CONSOLE_URL'):
        os.environ['OPENSHIFT_CONSOLE_URL'] = console_url

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                login_and_get_token(api_url, username, password),
            )
            return future.result(timeout=120)
    except RuntimeError:
        return asyncio.run(
            login_and_get_token(api_url, username, password),
        )
