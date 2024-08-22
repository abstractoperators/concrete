Start server
```bash
python main.py
```

## Development
Render in jupyter
```python
import sys
from IPython.core.display import display, HTML
from htmxapp.main import app
from starlette.testclient import TestClient

# Render HTML inline. Print directly to see raw html
d = lambda x: display(HTML(x))
sys.path.append('/Users/kentgang/git/concrete/')

# Fetch fasthtml server
client = TestClient(app)
r = client.get("/")
d(r.text)
```