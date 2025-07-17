# Building and Publishing to PyPI

This document provides instructions for building and publishing the `mcp-vultr` package to PyPI.

## Prerequisites

1. **Install build tools:**
   ```bash
   pip install build twine
   ```

2. **Set up PyPI credentials:**
   - Create account on [PyPI](https://pypi.org/account/register/)
   - Create account on [TestPyPI](https://test.pypi.org/account/register/) for testing
   - Generate API tokens for both accounts
   - Configure credentials in `~/.pypirc`:
     ```ini
     [distutils]
     index-servers =
         pypi
         testpypi

     [pypi]
     username = __token__
     password = pypi-your-api-token-here

     [testpypi]
     repository = https://test.pypi.org/legacy/
     username = __token__
     password = pypi-your-test-api-token-here
     ```

## Building the Package

1. **Clean previous builds:**
   ```bash
   rm -rf build/ dist/ *.egg-info/
   ```

2. **Build the package:**
   ```bash
   python -m build
   ```

   This creates:
   - `dist/mcp_vultr-1.0.0-py3-none-any.whl` (wheel)
   - `dist/mcp-vultr-1.0.0.tar.gz` (source distribution)

3. **Verify the build:**
   ```bash
   python -m twine check dist/*
   ```

## Testing on TestPyPI

1. **Upload to TestPyPI:**
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

2. **Test installation from TestPyPI:**
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple mcp-vultr
   ```

3. **Test functionality:**
   ```bash
   mcp-vultr --help
   python -c "from mcp_vultr import VultrDNSClient; print('Import successful')"
   ```

## Publishing to PyPI

1. **Upload to PyPI:**
   ```bash
   python -m twine upload dist/*
   ```

2. **Verify publication:**
   - Check the package page: https://pypi.org/project/mcp-vultr/
   - Test installation: `pip install mcp-vultr`

## Version Management

1. **Update version in `_version.py`:**
   ```python
   __version__ = "1.1.0"
   ```

2. **Update version in `pyproject.toml`:**
   ```toml
   version = "1.1.0"
   ```

3. **Update CHANGELOG.md** with new version details

4. **Create git tag:**
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

## Automated Publishing (GitHub Actions)

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.x'
    - name: Install build dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

## Release Checklist

- [ ] Update version numbers
- [ ] Update CHANGELOG.md
- [ ] Run tests: `pytest`
- [ ] Check code quality: `black --check src tests && isort --check src tests`
- [ ] Type check: `mypy src`
- [ ] Build package: `python -m build`
- [ ] Check package: `twine check dist/*`
- [ ] Test on TestPyPI
- [ ] Create git tag
- [ ] Upload to PyPI
- [ ] Verify installation works
- [ ] Update documentation if needed

## Package Maintenance

### Dependencies
- Keep dependencies updated in `pyproject.toml`
- Test with latest versions of dependencies
- Consider version constraints for stability

### Documentation
- Keep README.md updated with new features
- Update API documentation for new methods
- Add examples for new functionality

### Testing
- Add tests for new features
- Maintain high test coverage
- Test against multiple Python versions

### Security
- Regularly update dependencies
- Monitor for security vulnerabilities
- Follow security best practices
