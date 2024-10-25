import datetime
import os
import re
import subprocess
import sys


def get_lines_changed(file_path):
    try:
        # Get the diff of the staged changes for the file
        diff_output = subprocess.check_output(
            ['git', 'diff', '--cached', '--numstat', file_path], stderr=subprocess.STDOUT
        ).decode('utf-8')

        if diff_output:
            # The output format is: added\tremoved\tfilename
            added, removed, _ = diff_output.strip().split('\t')
            total_changed = int(added) + int(removed)
            return total_changed
        else:
            return 0
    except subprocess.CalledProcessError as e:
        print(f"Error computing lines changed for {file_path}: {e.output.decode('utf-8')}")
        return 0


def update_last_edited(file_paths):
    last_updated_pattern = re.compile(r'^Last Updated:.*$', re.MULTILINE)
    lines_changed_pattern = re.compile(r'^Lines Changed:.*$', re.MULTILINE)
    date_str = f'Last Updated: {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d UTC")}'

    for file_path in file_paths:
        lines_changed_str = f'Lines Changed: {get_lines_changed(file_path)}'
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
