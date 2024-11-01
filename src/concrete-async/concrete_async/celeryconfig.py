# TODO: unification of settings for various libraries and modules
broker_url = "pyamqp://localhost"
result_backend = "rpc://localhost"

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

task_default_queue = "concrete"

task_routes = {
    "operators.developer.*": {"queue": "developers"},
    "operators.executive.*": {"queue": "executives"},
}

hostname = "localhost"

broker_connection_retry_on_startup = True
# TODO: Route agnostic. Should be able to scale horizontally or vertically
