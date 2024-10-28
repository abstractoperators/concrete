import datetime
import re
import subprocess  # nosec B404
import sys


def get_lines_changed(file_path):
    result = subprocess.run(  # nosec B603, B404, B607
        ['git', 'diff', '--cached', '--numstat', file_path],
        check=True,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        added, removed, _ = result.stdout.strip().split('\t')
        return f'+{added}, -{removed}'
    return ""


def update_last_edited(file_paths):
    last_updated_pattern = re.compile(r'^Last Updated:.*$', re.MULTILINE)
    lines_changed_pattern = re.compile(r'^Lines Changed:.*$', re.MULTILINE)
    date_str = f'Last Updated: {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}'

    for file_path in file_paths:
        lines_changed = get_lines_changed(file_path)
        if lines_changed != "":
            lines_changed_str = f'Lines Changed: {lines_changed}'
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Replacing existing respects placement if it already exists, and adds it to the top if it doesn't.
            if lines_changed_pattern.search(content):
                content = lines_changed_pattern.sub(lines_changed_str, content)
            else:
                content = lines_changed_str + '\n\n' + content

            if last_updated_pattern.search(content):
                new_content = last_updated_pattern.sub(date_str, content)
            else:
                new_content = date_str + '\n\n' + content

            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_content)


if __name__ == "__main__":
    update_last_edited(sys.argv[1:])
    subprocess.run(['git', 'add', '-u'], check=True)  # nosec B603 B607
    # footgun https://stackoverflow.com/questions/58398995/black-as-pre-commit-hook-always-fails-my-commits
