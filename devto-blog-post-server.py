import os
import requests
import logging
from dotenv import load_dotenv
from typing import List, Optional
from mcp.server.fastmcp import FastMCP

# Configure logging to avoid printing to stdout, as recommended for MCP servers.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the FastMCP server with a descriptive name.
# This name will be visible to clients connecting to your MCP server.
mcp = FastMCP("DevToBlogPublisher")

load_dotenv()


def _mask_key(key: str) -> str:
    """Return a masked representation of a secret for safe logging (shows first and last 2 chars)."""
    if not key:
        return "<missing>"
    if len(key) <= 6:
        return key[0] + "*" * (len(key) - 2) + key[-1]
    return f"{key[:2]}...{key[-2:]}"


@mcp.tool()
def debug_env() -> str:
    """Return debug information about environment variables (masked). Useful for diagnosing 401s.

    This does NOT reveal the full API key. It only indicates presence and a masked form.
    """
    # Ensure .env is loaded if present
    try:
        load_dotenv()
    except Exception:
        pass

    devto_api_key = os.getenv("DEVTO_API_KEY")
    if devto_api_key:
        return f"DEVTO_API_KEY present, masked={_mask_key(devto_api_key)}"
    return "DEVTO_API_KEY not present in environment"

@mcp.tool()
def publish_blog_to_devto(
    title: str,
    body_markdown: str,
    tags: Optional[List[str]] = None,
    published: bool = False,
    series: Optional[str] = None,
    canonical_url: Optional[str] = None,
    cover_image: Optional[str] = None,
    dry_run: bool = False,
) -> str:
    """
    Publishes a blog post to dev.to.

    Args:
        title (str): The title of the blog post.
        body_markdown (str): The content of the blog post in Markdown format.
        tags (Optional[List[str]]): A list of tags for the blog post (e.g., ["python", "webdev"]).
        published (bool): Set to True to publish immediately, False to save as a draft.
        series (Optional[str]): The name of the series this article belongs to.
        canonical_url (Optional[str]): The canonical URL of the article if it's cross-posted.
        cover_image (Optional[str]): URL of the cover image for the article.

    Returns:
        str: A message indicating the success or failure of the publishing operation,
             including the article URL if successful.
    """
    logging.info(f"Attempting to publish blog post: '{title}' to dev.to")

    # Retrieve the Dev.to API key from environment variables.
    # It's crucial to keep your API key secure and not hardcode it.
    devto_api_key = os.getenv("DEVTO_API_KEY")
    if not devto_api_key:
        logging.error("DEVTO_API_KEY environment variable not set.")
        return "Error: DEVTO_API_KEY environment variable is not set. Please set it to publish articles."

    # Log masked key presence for diagnostics (never log the full key)
    logging.info(f"DEVTO_API_KEY present: {_mask_key(devto_api_key)}")

    # If caller requested a dry run (useful when invoking via remote LLM/test), do not call the API
    if dry_run:
        logging.info("Dry run enabled - not sending request to Dev.to")
        return f"Dry run: prepared article payload for '{title}' (tags={tags}, published={published})"

    # Dev.to API endpoint for creating articles.
    DEVTO_API_URL = "https://dev.to/api/articles"

    # Prepare the headers for the API request.
    headers = {
        "Content-Type": "application/json",
        "api-key": devto_api_key
    }

    # Construct the article data payload.
    article_data = {
        "article": {
            "title": title,
            "body_markdown": body_markdown,
            "published": published,
        }
    }

    # Add optional fields if they are provided.
    if tags:
        article_data["article"]["tags"] = tags
    if series:
        article_data["article"]["series"] = series
    if canonical_url:
        article_data["article"]["canonical_url"] = canonical_url
    if cover_image:
        article_data["article"]["cover_image"] = cover_image

    try:
        # Make the POST request to the Dev.to API.
        response = requests.post(DEVTO_API_URL, headers=headers, json=article_data)

        # Try to parse the response body for better error messages
        try:
            response_json = response.json()
        except ValueError:
            response_json = None

        # Handle authorization error separately to give a clear actionable message
        if response.status_code == 401:
            logging.error("Dev.to API responded with 401 Unauthorized. Check your DEVTO_API_KEY.")
            details = None
            if response_json:
                details = response_json.get("error") or response_json
            else:
                details = response.text
            return f"Error: Dev.to API returned 401 Unauthorized. Please verify your DEVTO_API_KEY. Details: {details}"

        if response.status_code == 201:
            article_url = (response_json or {}).get("url")
            logging.info(f"Article '{title}' published successfully! URL: {article_url}")
            return f"Article published successfully! URL: {article_url}"

        # Other non-successful responses
        error_message = None
        if response_json:
            # Dev.to sometimes puts an error message in the JSON
            error_message = response_json.get("error") or response_json
        else:
            error_message = response.text

        logging.error(f"Failed to publish article '{title}'. Status code: {response.status_code}, Error: {error_message}")
        return f"Failed to publish article. Status code: {response.status_code}, Error: {error_message}"

    except requests.exceptions.RequestException as e:
        logging.error(f"Network or API request error: {e}")
        return f"An error occurred during the API request: {e}"
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return f"An unexpected error occurred: {e}"

# This block ensures the MCP server runs when the script is executed directly.
if __name__ == "__main__":
    logging.info("Starting Dev.to Blog Publisher MCP Server...")
    mcp.run(transport='stdio')