# Markdown to Confluence Sync

This Action copies the contents of a Markdown `.md` file or folder to a Confluence cloud parent page.

## Getting Started

```yml
push:
  branches:
    - develop
  paths:
    - 'docs/**'

jobs:
  dev:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: axro-gmbh/markdown-to-confluence-sync@1.0
        with:
          input_directory: docs
          exclude_files: this.md,that.md
          cloud: company
          space_key: ${{ secrets.CONFLUENCE_SPACE_KEY }}
          parent_page_id: ${{ secrets.JIRA_SCRIPTS_PARENT_PAGE_ID }}
          user: ${{ secrets.JIRA_USER }}
          token: ${{ secrets.JIRA_TOKEN }}
```

## Authentication

Uses a token for the REST API v2.

## Input variables

- `input_directory`: The folder you want to sync

- `input_file`: If you don't want to sync a folder, you can also sync a single markdown file.

*WARNING! USE ONLY ONE OF THE VARIABLES! (but one of them is required)*

- `cloud`: The ID can be found by looking at your confluence domain

- `space_key`: The space key of the page

- `parent_page_id`: The parent page ID of the page you want to create a child page under

- `user`: The user that generated the access token

- `token`: the Confluence API token.

*Optional*:

- `exclude_files`: If there are files in the folder you would want to exclude

## Where you can find the data (cloud, space_key, parent_page_id, API-Token) in Confluence

### Cloud, Space Key and Parent Page ID

You can find the data in the URL of the page you want to sync to:
`https://<cloud>.atlassian.net/wiki/spaces/<space_key>/pages/<parent_page_id>/...`

### API-Token

Create your api token in your Atlassian account settings: https://id.atlassian.com/manage-profile/security/api-tokens

