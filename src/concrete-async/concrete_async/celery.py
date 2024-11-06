from celery import Celery

from concrete.models import clients  # noqa

from . import celeryconfig

app = Celery("concrete_async")
app.config_from_object(celeryconfig)


if __name__ == "__main__":
    app.start()
