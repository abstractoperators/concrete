import datetime
import re
import subprocess  # nosec B404
import sys
from pathlib import Path


def is_safe_filepath(file_path: str) -> bool:
    """Validate that the file path is safe to use."""
    path = Path(file_path).resolve()
    if not path.is_file():
        return False
    cmd = ['git', 'ls-files', '--error-unmatch', str(path)]
    subprocess.run(cmd, check=True, capture_output=True)  # nosec B603, B404
    return True


def get_lines_changed(file_path):
    if not is_safe_filepath(file_path):
        return 0
    cmd = ['git', 'diff', '--cached', '--numstat', file_path]

    result = subprocess.run(  # nosec B603, B404
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        added, removed, _ = result.stdout.strip().split('\t')
        return int(added) + int(removed)
    return 0


def update_last_edited(file_paths):
    last_updated_pattern = re.compile(r'^Last Updated:.*$', re.MULTILINE)
    lines_changed_pattern = re.compile(r'^Lines Changed:.*$', re.MULTILINE)
    date_str = f'Last Updated: {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}'

    for file_path in file_paths:
        lines_changed = get_lines_changed(file_path)
        if lines_changed > 0:
            lines_changed_str = f'Lines Changed: {lines_changed}'
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            if lines_changed_pattern.search(content):
                content = lines_changed_pattern.sub(lines_changed_str, content)
            else:
                content = lines_changed_str + '\n' + content

            if last_updated_pattern.search(content):
                new_content = last_updated_pattern.sub(date_str, content)
            else:
                new_content = date_str + '\n' + content

            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_content)


if __name__ == "__main__":
    update_last_edited(sys.argv[1:])
