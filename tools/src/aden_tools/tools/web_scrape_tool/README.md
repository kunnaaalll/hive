# Web Scrape Tool

Scrape and extract content from webpages with optional dynamic rendering and Markdown support.

## Description

Use when you need to read the content of a specific URL, extract data from a website, or read articles/documentation. Supports both static scraping (fast) and dynamic rendering (via Playwright) for modern SPAs. Can return content in plain text or structured Markdown.

## Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `url` | str | Yes | - | URL of the webpage to scrape |
| `selector` | str | No | `None` | CSS selector to target specific content |
| `include_links` | bool | No | `False` | Include extracted links in the response |
| `max_length` | int | No | `50000` | Maximum length of extracted content (1000-500000) |
| `render_js` | bool | No | `False` | Enable dynamic rendering using Playwright (required for modern JS-heavy sites) |
| `output_format` | str | No | `"text"` | Format of extracted content: `"text"` or `"markdown"` |

## Environment Variables

This tool does not require any environment variables.

## Error Handling

Returns error dicts for common issues:
- `Security violation: <error>` - URL blocked due to safety rules (SSRF protection)
- `HTTP <status>: Failed to fetch URL` - Server returned error status
- `No elements found matching selector: <selector>` - CSS selector matched nothing
- `Scraping failed: <error>` - Playwright or parsing error

## Notes

- URLs without protocol are automatically prefixed with `https://`
- **Dynamic Mode**: Use `render_js=True` for sites built with React, Next.js, etc.
- **Markdown**: Use `output_format="markdown"` to preserve semantic structure (headers, tables).
- **Ethics**: Automatically respects `robots.txt` rules and identifies as `AdenBot/1.0`.
- **Security**: For safety, the tool blocks access to internal/private IP addresses (localhost, private network, etc.).
