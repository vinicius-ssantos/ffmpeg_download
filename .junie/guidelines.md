# Development Guidelines

## Build / Configuration

1. Use **Python 3.9+** (repository currently tested with Python 3.12).
2. Install project dependencies:
   ```bash
   pip install requests beautifulsoup4 playwright
   python -m playwright install
   ```
3. Copy `credenciais.json.exemplo` to `credenciais.json` and fill in your login credentials.
4. To authenticate and cache session cookies run:
   ```bash
   python login_facimpacta.py credenciais.json
   ```
5. To scrape lesson links run:
   ```bash
   python coletar_aulas.py <COURSE_URL> --out lessons.json
   ```

## Testing

1. Install test dependencies (pytest is used):
   ```bash
   pip install pytest
   ```
2. Run all tests with:
   ```bash
   pytest -q
   ```
3. New tests should live in files named `test_*.py` at the repository root.
   They may use either `unittest` or `pytest` style.  Tests must not depend
   on network access; mock HTTP requests as needed.
4. Example test for `_extrai_token` in `login_facimpacta.py`:
   ```python
   from login_facimpacta import _extrai_token

   def test_extrai_token():
       html = '<meta name="csrf-token" content="abc">'
       assert _extrai_token(html) == 'abc'
   ```
5. Always run the full test suite before committing.

## Additional Development Information

- Code follows standard PEP 8 style and uses type annotations.
- Commit messages should be in the imperative mood and concise.
- `session_cookies.json` contains authentication cookies and is created by
  `login_facimpacta.py`.  Keep this file out of version control.
- `coletar_aulas.py` uses Playwright in headless mode to extract lesson URLs.
  Ensure Playwright is installed and Chromium is downloaded before running.
