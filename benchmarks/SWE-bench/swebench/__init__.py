__version__ = "2.1.6"

from swebench.collect.build_dataset import main as build_dataset
from swebench.collect.get_tasks_pipeline import main as get_tasks_pipeline
from swebench.collect.print_pulls import main as print_pulls
from swebench.harness.constants import (
    KEY_INSTANCE_ID,
    KEY_MODEL,
    KEY_PREDICTION,
    MAP_REPO_VERSION_TO_SPECS,
)
from swebench.harness.docker_build import (
    build_base_images,
    build_env_images,
    build_image,
    build_instance_image,
    build_instance_images,
    close_logger,
    setup_logger,
)
from swebench.harness.docker_utils import (
    cleanup_container,
    copy_to_container,
    exec_run_with_timeout,
    list_images,
    remove_image,
)
from swebench.harness.grading import (
    ResolvedStatus,
    TestStatus,
    compute_fail_to_pass,
    compute_pass_to_pass,
    get_eval_report,
    get_logs_eval,
    get_resolution_status,
)
from swebench.harness.log_parsers import MAP_REPO_TO_PARSER
from swebench.harness.run_evaluation import main as run_evaluation
from swebench.harness.utils import get_environment_yml, get_requirements
from swebench.versioning.constants import (
    MAP_REPO_TO_VERSION_PATHS,
    MAP_REPO_TO_VERSION_PATTERNS,
)
from swebench.versioning.get_versions import (
    get_version,
    get_versions_from_build,
    get_versions_from_web,
    map_version_to_task_instances,
)
from swebench.versioning.utils import split_instances
