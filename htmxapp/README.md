Start server
```bash
python main.py
```

## Development
Render in jupyter
```python
import sys
from IPython.core.display import display, HTML
from starlette.testclient import TestClient

PATH_TO_CONCRETE = "/Users/..."  # Replace
sys.path.append(PATH_TO_CONCRETE)

# Import local copy
from htmxapp.main import app

# Render HTML inline. Print directly to see raw html
d = lambda x: display(HTML(x))

# Fetch fasthtml server
client = TestClient(app)
r = client.get("/")
d(r.text)
```
