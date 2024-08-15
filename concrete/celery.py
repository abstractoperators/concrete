from celery import Celery

app = Celery(
    'concrete',
    broker='pyamqp://',
    include=['concrete.operators'],
)

if __name__ == '__main__':
    app.start()
