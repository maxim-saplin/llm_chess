# Publishing to Test PyPI

This repository is configured to publish the `llm-chess` package to Test PyPI.

## GitHub Secret Configuration

The workflow requires a GitHub secret named `TEST_PYPI_API_TOKEN` to be set up in the repository settings.

### Setting up the secret:

1. Go to the repository Settings
2. Navigate to Secrets and variables > Actions
3. Click "New repository secret"
4. Name: `TEST_PYPI_API_TOKEN`
5. Value: Use the Test PyPI API token provided in the issue/task
6. Click "Add secret"

**Note:** The API token should be obtained from Test PyPI (https://test.pypi.org/manage/account/#api-tokens) or use the token provided in your deployment instructions. Never commit API tokens to the repository.

## Publishing Methods

The workflow can be triggered in two ways:

### 1. Automatic Publishing (via Git Tags)

Push a version tag to trigger automatic publishing:

```bash
git tag v0.0.1
git push origin v0.0.1
```

### 2. Manual Publishing (via Workflow Dispatch)

You can also manually trigger the workflow from the GitHub Actions tab:

1. Go to Actions tab
2. Select "Publish to Test PyPI" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

## Verifying the Package

After publishing, you can verify the package at:
https://test.pypi.org/project/llm-chess/

## Installing from Test PyPI

To install the package from Test PyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ llm-chess
```

Note: Dependencies may need to be installed from the regular PyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ llm-chess
```
