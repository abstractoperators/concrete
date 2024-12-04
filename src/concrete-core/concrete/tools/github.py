import base64
import io
import os
import tempfile
import zipfile

import requests
from concrete.clients import CLIClient
from concrete.tools import MetaTool
from concrete.tools.http import HTTPTool, RestApiTool


class GithubTool(metaclass=MetaTool):
    """
    Facilitates interactions with github through its Restful API
    """

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f'Bearer {os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")}',
        "X-GitHub-Api-Version": "2022-11-28",
    }

    @classmethod
    def create_pr(
        cls,
        org: str,
        repo: str,
        head: str,
        access_token: str,
        title: str,
        base: str = "main",
    ):
        """
        Make a pull request on the target repo

        e.g. make_pr('abstractoperators', 'concrete', 'kent/http-tool')

        Args
            org (str): The organization or accounts that owns the repo.
            repo (str): The name of the repository.
            head (str): The head branch being merged into the base.
            title (str): The title of the PR being created.
            base (str): The title of the branch that changes are being merged into.
        """
        url = f"https://api.github.com/repos/{org}/{repo}/pulls"
        json = {"title": f"[ABOP] {title}", "head": head, "base": base}
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            RestApiTool.post(url, headers=headers, json=json)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                CLIClient.emit("PR already exists.")
            else:
                CLIClient.emit("Failed to create PR: " + str(e))

    @classmethod
    def create_branch(
        cls,
        org: str,
        repo: str,
        new_branch: str,
        access_token: str,
        base_branch: str = "main",
    ):
        """
        Make a branch called new_branch from the latest commit on base_name

        Args
            org (str): Organization or account owning the repo
            repo (str): The name of the repository
            base_branch (str): The name of the branch to branch from.
            new_branch (str): The name of the new branch (e.g. 'michael/new-feature')
            access_token(str): Fine-grained token with at least 'Contents' repository write access.
                https://docs.github.com/en/rest/git/refs?apiVersion=2022-11-28#create-a-reference--fine-grained-access-tokens
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Get SHA of latest commit on base branch
        url = f"https://api.github.com/repos/{org}/{repo}/branches/{base_branch}"
        base_sha = RestApiTool.get(url, headers=headers)["commit"]["sha"]

        # Create new branch from base branch
        url = f"https://api.github.com/repos/{org}/{repo}/git/refs"
        json = {"ref": "refs/heads/" + new_branch, "sha": base_sha}
        try:
            RestApiTool.post(url=url, headers=headers, json=json)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                CLIClient.emit("Branch already exists.")
            else:
                CLIClient.emit("Failed to create branch: " + str(e))

    @classmethod
    def delete_branch(cls, org: str, repo: str, branch: str, access_token: str):
        """
        Deletes a branch from the target repo
        https://docs.github.com/en/rest/git/refs?apiVersion=2022-11-28#delete-a-reference

        Args
            org (str): Organization or account owning the rep
            repo (str): Repository name
            branch (str): Branch to delete
            access_token(str): Fine-grained token with at least 'Contents' repository write access.
        """
        url = f"https://api.github.com/repos/{org}/{repo}/git/refs/heads/{branch}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        resp = requests.delete(url, headers=headers, timeout=10)
        if resp.status_code == 204:
            CLIClient.emit(f"{branch} deleted successfully.")
        else:
            CLIClient.emit(f"Failed to delete {branch}." + str(resp.json()))

    @classmethod
    def put_file(
        cls,
        org: str,
        repo: str,
        branch: str,
        commit_message: str,
        path: str,
        file_contents: str,
        access_token: str,
    ):
        """
        Updates/Create a file on the target repo + commit.

        Args
            org (str): Organization or account owning the repo
            repo (str): The name of the repository
            branch (str): The branch that the commit is being made to.
            commit_message (str): The commit message.
            path: (str): Path relative to root of repo
            access_token(str): Fine-grained token with at least 'Contents' repository write access.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        # Get blob sha
        url = f"https://api.github.com/repos/{org}/{repo}/contents/{path}"
        json = {"ref": branch}
        resp = requests.get(url, headers=headers, params=json, timeout=10)

        # TODO switch to RestApiTool; Handle 404 better.
        if resp.status_code == 404:
            sha = None
        else:
            sha = resp.json().get("sha")

        url = f"https://api.github.com/repos/{org}/{repo}/contents/{path}"
        json = {
            "message": commit_message,
            "content": base64.b64encode(file_contents.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            json["sha"] = sha
        RestApiTool.put(url, headers=headers, json=json)

    @classmethod
    def get_diff(cls, org: str, repo: str, base: str, head: str, access_token: str) -> str:
        """
        Retrieves diff of base compared to compare.

        Args
            org (str): Organization or account owning the repo
            repo (str): The name of the repository
            base (str): The name of the branch to compare against.
            head (str): The name of the branch to compare
            access_token(str): Fine-grained token with at least 'Contents' repository read access.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = f"https://api.github.com/repos/{org}/{repo}/compare/{base}...{head}"
        diff_url = RestApiTool.get(url, headers=headers)["diff_url"]
        diff = RestApiTool.get(diff_url)
        return diff

    @classmethod
    def get_changed_files(
        cls, org: str, repo: str, base: str, head: str, access_token: str
    ) -> list[tuple[list[str], str]]:
        """
        Returns a list of changed files between two commits
        [([a/file_path, b/file_path], uncleaned_diff)]
        """
        diff = GithubTool.get_diff(org, repo, base, head, access_token)
        files_with_diffs = diff.split("diff --git")[1:]  # Skip the first empty element
        return [(file.split("\n", 1)[0].split(), file) for file in files_with_diffs]

    @classmethod
    def fetch_branch(cls, org: str, repo: str, branch: str, access_token: str) -> str:
        """
        Downloads contents of branches latest commit to dest_path.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = f"https://api.github.com/repos/{org}/{repo}/zipball/refs/heads/{branch}"

        dest_path = tempfile.mkdtemp(prefix="GithubTool-")

        content = HTTPTool.get(url, headers=headers)

        with zipfile.ZipFile(io.BytesIO(content)) as zip_ref:
            zip_ref.extractall(dest_path)
            top_level_dir = zip_ref.namelist()[0].split("/")[0]

        # Full path to the extracted directory.
        full_path = os.path.join(dest_path, top_level_dir)

        CLIClient.emit(f"{org}/{repo}/{branch} has been downloaded to '{full_path}'.")
        return full_path
