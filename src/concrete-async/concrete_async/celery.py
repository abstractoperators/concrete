from celery import Celery

from . import celeryconfig

app = Celery("concrete_async")
app.config_from_object(celeryconfig)

print("Loading celery app")
if __name__ == "__main__":
    app.start()
