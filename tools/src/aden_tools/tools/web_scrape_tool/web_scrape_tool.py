import asyncio
import os
import ipaddress
import socket
from typing import Any, List
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from fastmcp import FastMCP
from markdownify import markdownify as md

# Cache for robots.txt parsers (domain -> parser)
_robots_cache: dict[str, RobotFileParser | None] = {}

# User-Agent for the scraper - identifies as a bot for transparency
USER_AGENT = "AdenBot/1.0 (https://adenhq.com; web scraping tool)"

# Browser-like User-Agent for actual page requests
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _is_internal_ip(hostname: str) -> bool:
    """
    Check if a hostname resolves to a private or loopback IP address.
    """
    try:
        # Check if it's already an IP
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        # Not a direct IP, try to resolve
        try:
            # We use 80 as a dummy port for better resolution compatibility
            addr_info = socket.getaddrinfo(hostname, 80)
            for item in addr_info:
                ip_str = item[4][0]
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    return True
            return False # All resolved IPs are public
        except (socket.gaierror, ValueError):
            # If we can't resolve it, check for common local names
            local_names = ("localhost", "localhost.localdomain", "local")
            if hostname.lower().strip(".") in local_names:
                return True
            return False # Allow it to proceed, Playwright/httpx will fail naturally if it's invalid


def _validate_url_security(url: str) -> tuple[bool, str]:
    """
    Validate URL to prevent SSRF and unsafe protocols.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"Unsupported protocol: {parsed.scheme}. Only http/https are allowed."
        
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: No hostname found."
            
        if _is_internal_ip(hostname):
            return False, f"Access to internal/private address is blocked: {hostname}"
            
        return True, ""
    except Exception as e:
        return False, f"URL validation failed: {str(e)}"


async def _get_robots_parser_async(base_url: str, timeout: float = 10.0) -> RobotFileParser | None:
    """
    Fetch and parse robots.txt for a domain asynchronously.
    """
    if base_url in _robots_cache:
        return _robots_cache[base_url]
    
    robots_url = f"{base_url}/robots.txt"
    parser = RobotFileParser()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                robots_url,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=timeout,
            )
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
            _robots_cache[base_url] = parser
            return parser
        else:
            _robots_cache[base_url] = None
            return None
    except (httpx.TimeoutException, httpx.RequestError):
        return None


async def _is_allowed_by_robots_async(url: str) -> tuple[bool, str]:
    """
    Check if URL is allowed by robots.txt asynchronously.
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path or "/"
    
    parser = await _get_robots_parser_async(base_url)
    
    if parser is None:
        return True, "No robots.txt found or not accessible"
    
    if parser.can_fetch(USER_AGENT, path) and parser.can_fetch("*", path):
        return True, "Allowed by robots.txt"
    else:
        return False, f"Blocked by robots.txt for path: {path}"


def register_tools(mcp: FastMCP) -> None:
    """Register web scrape tools with the MCP server."""

    @mcp.tool()
    async def web_scrape(
        url: str,
        selector: str | None = None,
        include_links: bool = False,
        max_length: int = 50000,
        respect_robots_txt: bool = True,
        render_js: bool = False,
        output_format: str = "text",
    ) -> dict:
        """
        Scrape and extract content from a webpage. Supports dynamic rendering and Markdown.

        Use when you need to read content from modern SPAs, documentation, or articles.

        Args:
            url: URL of the webpage to scrape
            selector: CSS selector to target specific content
            include_links: Include extracted links in the response
            max_length: Maximum length of extracted content (1000-500000)
            respect_robots_txt: Whether to respect robots.txt rules (default: True)
            render_js: Enable dynamic rendering using Playwright (required for SPAs)
            output_format: Format of the content ('text' or 'markdown')
        """
        try:
            # 1. Validation of the raw input
            parsed_raw = urlparse(url)
            
            # If no scheme, default to https
            if not parsed_raw.scheme:
                url = "https://" + url
                parsed_raw = urlparse(url)

            # 2. SSRF Protection & Protocol Validation
            allowed_url, error_msg = _validate_url_security(url)
            if not allowed_url:
                return {"error": f"Security violation: {error_msg}", "url": url}

            # 3. Check robots.txt if enabled
            if respect_robots_txt:
                allowed, reason = await _is_allowed_by_robots_async(url)
                if not allowed:
                    return {
                        "error": f"Scraping blocked: {reason}",
                        "blocked_by_robots_txt": True,
                        "url": url,
                    }

            # Validate settings
            if max_length < 1000: max_length = 1000
            elif max_length > 500000: max_length = 500000
            
            html_content = ""
            page_title = ""
            page_description = ""
            resolved_url = url

            if render_js:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(user_agent=BROWSER_USER_AGENT)
                    page = await context.new_page()
                    
                    try:
                        await page.goto(url, wait_until="networkidle", timeout=60000)
                        html_content = await page.content()
                        page_title = await page.title()
                        resolved_url = page.url
                        
                        # Get description from meta (optional, don't wait/timeout)
                        try:
                            meta_desc_handle = await page.query_selector('meta[name="description"]')
                            if meta_desc_handle:
                                page_description = await meta_desc_handle.get_attribute("content") or ""
                        except Exception:
                            page_description = ""
                            
                    finally:
                        await browser.close()
            else:
                # Static scrape using httpx
                async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                    response = await client.get(
                        url,
                        headers={
                            "User-Agent": BROWSER_USER_AGENT,
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        }
                    )
                
                if response.status_code != 200:
                    return {"error": f"HTTP {response.status_code}: Failed to fetch URL"}

                content_type = response.headers.get("content-type", "").lower()
                if not any(t in content_type for t in ["text/html", "application/xhtml+xml"]):
                    return {"error": f"Skipping non-HTML content ({content_type})", "url": url}
                
                html_content = response.text
                resolved_url = str(response.url)

            # Process HTML with BeautifulSoup for cleaning / extraction
            soup = BeautifulSoup(html_content, "html.parser")
            
            if not render_js:
                title_tag = soup.find("title")
                if title_tag: page_title = title_tag.get_text(strip=True)
                
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc: page_description = meta_desc.get("content", "")

            # Remove noise
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
                tag.decompose()

            # Target content
            if selector:
                content_elem = soup.select_one(selector)
                if not content_elem:
                    return {"error": f"No elements found matching selector: {selector}"}
                target_html = str(content_elem)
            else:
                main_content = (
                    soup.find("article") or soup.find("main") or 
                    soup.find(attrs={"role": "main"}) or 
                    soup.find(class_=["content", "post", "entry"]) or 
                    soup.find("body")
                )
                target_html = str(main_content) if main_content else html_content

            # Convert to results
            if output_format.lower() == "markdown":
                content = md(target_html, heading_style="ATX")
            else:
                content = BeautifulSoup(target_html, "html.parser").get_text(separator=" ", strip=True)

            # Cleanup whitespace
            content = " ".join(content.split())
            if len(content) > max_length:
                content = content[:max_length] + "..."

            result = {
                "url": resolved_url,
                "title": page_title,
                "description": page_description,
                "content": content,
                "length": len(content),
                "format": output_format,
            }
            
            if include_links:
                links = []
                for a in soup.find_all("a", href=True)[:50]:
                    href = a["href"]
                    link_text = a.get_text(strip=True)
                    if link_text and href:
                        links.append({"text": link_text, "href": href})
                result["links"] = links

            return result

        except Exception as e:
            return {"error": f"Scraping failed: {str(e)}"}