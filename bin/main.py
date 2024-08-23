#!/usr/bin/env python
"""
This syncs markdown files from a file or folder to Confluence as child pages
of a given parent, with their docstring, HTML formatted.
It uses v2 of the Confluence API, and can exclude files.
If selecting a single file, it assumes the file you want to sync is in the main repo directory.
"""

import os
import sys
import requests
from markdown import markdown
from mdx_gfm import GithubFlavoredMarkdownExtension


def load_environment_variables():
    """
    Load environment variables and check for required values.
    """
    env_var_names = {
        "cloud": "INPUT_CLOUD",
        "user": "INPUT_USER",
        "token": "INPUT_TOKEN",
        "parent_page_id": "INPUT_PARENT_PAGE_ID",
        "space_key": "INPUT_SPACE_KEY",
    }

    envs = {}
    for var_name, env_name in env_var_names.items():
        envs[var_name] = os.environ[env_name]
        if not envs[var_name]:
            print(f"Missing value for {var_name}")
            sys.exit(1)

    if "INPUT_INPUT_FILE" in os.environ and os.environ["INPUT_INPUT_FILE"]:
        envs["input_file"] = os.environ["INPUT_INPUT_FILE"]
    if "INPUT_INPUT_DIRECTORY" in os.environ and os.environ["INPUT_INPUT_DIRECTORY"]:
        envs["input_directory"] = os.environ["INPUT_INPUT_DIRECTORY"]
    if "INPUT_EXCLUDE_FILES" in os.environ and os.environ["INPUT_EXCLUDE_FILES"]:
        envs["exclude_files"] = os.environ["INPUT_EXCLUDE_FILES"]
    if "INPUT_FULL_WIDTH" in os.environ and os.environ["INPUT_FULL_WIDTH"]:
        envs["full_width"] = os.environ["INPUT_FULL_WIDTH"]

    envs["space_id"] = get_key_by_space_id(envs)
    if not envs["space_id"]:
        print(f"Space ID for key {envs["space_key"]} not found.")
        sys.exit(1)

    return envs


def read_markdown_file(md_file):
    """
    Read a markdown file.
    """
    with open(md_file, encoding="utf-8") as f:
        return f.read()


def render_html(md_content):
    """
    Render the page so Confluence understands it
    """
    return markdown(md_content, extensions=[GithubFlavoredMarkdownExtension()])


def get_page_title(md_file):
    """
    Extract the page title from the Markdown title if not set use filename
    """
    with open(md_file, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if first_line.startswith('# '):
            return first_line[2:].strip()
    return os.path.splitext(os.path.basename(md_file))[0]


def process_directory(envs, links):
    """
    Process a directory of markdown files
    """
    md_directory = os.path.join(
        os.environ["GITHUB_WORKSPACE"], envs["input_directory"]
    )
    if envs.get("exclude_files"):
        exclude_files = envs["exclude_files"].split(",")
    else:
        exclude_files = []

    for root, _, files in os.walk(md_directory):
        for f in files:
            if f.endswith(".md") and f not in exclude_files:
                md_file = os.path.join(root, f)
                links = process_file(md_file, envs, links)

    return links


def update_confluence_page(envs, config, links):
    """
    Update a Confluence page
    """
    update_url = (
        f"https://{envs['cloud']}.atlassian.net/wiki/api/v2/pages/{config['page_id']}"
    )
    headers = {"Content-Type": "application/json"}
    update_content = {
        "id": config["page_id"],
        "status": "current",
        "version": {"number": config["new_version"]},
        "title": config["page_title"],
        "body": {"value": config["html"], "representation": "storage"},
    }

    update_response = requests.put(
        update_url,
        json=update_content,
        auth=(envs["user"], envs["token"]),
        headers=headers,
        timeout=10,
    )

    if update_response.status_code == 200:
        updated_link = (
                f"https://{envs['cloud']}.atlassian.net/wiki"
                + update_response.json()["_links"]["webui"]
        )
        links.append(f"{config['page_title']}: {updated_link}")
        print(f"{config['page_title']}: Success. New version: {config['new_version']}")
    else:
        print(
            f"{config['page_title']}: Failed. HTTP status code: {update_response.status_code}"
        )


def create_confluence_page(envs, page_title, html, links):
    """
    Create a Confluence page
    """
    url = f"https://{envs['cloud']}.atlassian.net/wiki/api/v2/pages"
    content = {
        "spaceId": envs["space_id"],
        "status": "current",
        "title": page_title,
        "parentId": envs["parent_page_id"],
        "body": {"value": html, "representation": "storage"},
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    response = requests.post(
        url,
        json=content,
        auth=(envs["user"], envs["token"]),
        headers=headers,
        timeout=10,
    )
    if response.status_code == 200:
        if envs.get("full_width"):
            set_full_width_page(envs, response.json()["id"])
        link = (
                f"https://{envs['cloud']}.atlassian.net/wiki"
                + response.json()["_links"]["webui"]
        )
        links.append(f"{page_title}: {link}")
        print(f"{page_title}: Content upload successful.")
    else:
        print(f"{page_title}: Failed. HTTP status code: {response.status_code}")


def set_full_width_page(envs, page_id):
    """
    Set the page to full width
    """
    url = f"https://{envs['cloud']}.atlassian.net/wiki/api/v2/pages/{page_id}/properties"
    content = {
        "key": "content-appearance-published",
        "value": "full-width"
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    response = requests.post(
        url,
        json=content,
        auth=(envs["user"], envs["token"]),
        headers=headers,
        timeout=10,
    )


def process_file(md_file, envs, links):
    """
    Process a file and ensure formatting
    """
    new_version = None
    md_content = read_markdown_file(md_file)
    html = render_html(md_content)
    page_title = get_page_title(md_file)
    page_id, current_version, existing_content = find_page_by_title(page_title, envs)

    if current_version:
        new_version = current_version + 1

    if page_id:
        # Compare existing content with the new content and update if necessary
        if html != existing_content:
            update_confluence_page(
                envs,
                {
                    "page_id": page_id,
                    "page_title": page_title,
                    "html": html,
                    "new_version": new_version,
                },
                links,
            )
        else:
            print(f"{page_title}: Identical content, no update required.")
    else:
        # Create a new Confluence page
        create_confluence_page(envs, page_title, html, links)

    return links


def find_page_by_title(page_title, envs):
    """
    Find a Confluence page by title.
    """

    url = f"https://{envs['cloud']}.atlassian.net/wiki/api/v2/pages"
    params = {
        "title": page_title,
    }
    headers = {"Accept": "application/json"}
    response = requests.get(
        url,
        params=params,
        auth=(envs["user"], envs["token"]),
        headers=headers,
        timeout=10,
    )
    if response.status_code == 200:
        data = response.json()

        if data.get("results"):
            page_id = data["results"][0]["id"]
            version_number = data["results"][0]["version"]["number"]
            existing_content = None
            return page_id, version_number, existing_content

    return None, None, None


def get_key_by_space_id(envs):
    """
    Get the key by space ID
    """
    url = f"https://{envs['cloud']}.atlassian.net/wiki/api/v2/spaces/"
    headers = {"Accept": "application/json"}
    response = requests.get(
        url,
        auth=(envs["user"], envs["token"]),
        headers=headers,
        timeout=10,
    )
    if response.status_code == 200:
        data = response.json()
        for space in data["results"]:
            if space["key"] == envs["space_key"]:
                return space["id"]

    return None


def main():
    """
    Main function that orchestrates it all
    """
    envs = load_environment_variables()

    links = []
    if "input_file" in envs:
        # Process a single file
        single_file = os.path.join(os.environ["GITHUB_WORKSPACE"], envs["input_file"])
        links = process_file(single_file, envs, links)
    elif "input_directory" in envs:
        # Process a directory of markdown files
        links = process_directory(envs, links)
    else:
        # Handle the case where neither are provided
        print("No specific input provided.")
        sys.exit(1)

    print(links)


if __name__ == "__main__":
    main()
