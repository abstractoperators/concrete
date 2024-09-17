# TODO: unification of settings for various libraries and modules
broker_url = "pyamqp://"
result_backend = "rpc://"

task_serializer = "json"
result_serializer = "json"

task_default_queue = "concrete"

task_routes = {
    "operators.developer.*": {"queue": "developers"},
    "operators.executive.*": {"queue": "executives"},
}
