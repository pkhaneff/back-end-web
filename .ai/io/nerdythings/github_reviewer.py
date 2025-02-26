import os
import re
from git import Git
from ai.chat_gpt import ChatGPT
from log import Log
from ai.ai_bot import AiBot
from env_vars import EnvVars
from repository.github import GitHub
from repository.repository import RepositoryError

PR_SUMMARY_COMMENT_IDENTIFIER = "<!-- PR SUMMARY COMMENT -->"
EXCLUDED_FOLDERS = {".ai/io/nerdythings", ".github/workflows"}

def main():
    vars = EnvVars()
    vars.check_vars()

    if os.getenv("GITHUB_EVENT_NAME") != "pull_request" or not vars.pull_number:
        Log.print_red("This action only runs on pull request events.")
        return

    github = GitHub(vars.token, vars.owner, vars.repo, vars.pull_number)
    ai = ChatGPT(vars.chat_gpt_token, vars.chat_gpt_model)

    changed_files = Git.get_diff_files(head_ref=vars.head_ref, base_ref=vars.base_ref)
    if not changed_files:
        Log.print_red("No changes detected.")
        return

    changed_files = [
        file for file in changed_files
        if not any(file.startswith(excluded) for excluded in EXCLUDED_FOLDERS)
    ]

    if not changed_files:
        Log.print_green("All changed files are excluded from review.")
        return

    Log.print_yellow(f"Filtered changed files: {changed_files}")

    update_pr_summary(changed_files, ai, github)

    reviewed_files = set()
    for file in changed_files:
        process_file(file, ai, github, vars, reviewed_files)

def update_pr_summary(changed_files, ai, github):
    Log.print_green("Updating PR description...")

    file_contents = []
    for file in changed_files:
        try:
            with open(file, 'r', encoding="utf-8", errors="replace") as f:
                content = f.read()
                file_contents.append(f"### {file}\n{content[:1000]}...\n")
        except FileNotFoundError:
            Log.print_yellow(f"File not found: {file}")
            continue

    if not file_contents:
        return

    Log.print_yellow(f"File contents before processing: {file_contents}")
    full_context = {file: (content[:1000] if isinstance(content, str) else "") for file, content in zip(changed_files, file_contents)}
    new_summary = ai.ai_request_summary(file_changes=full_context)

    pr_data = github.get_pull_request()
    current_body = pr_data.get("body") or ""

    if PR_SUMMARY_COMMENT_IDENTIFIER in current_body:
        updated_body = re.sub(
            f"{PR_SUMMARY_COMMENT_IDENTIFIER}.*",
            f"{PR_SUMMARY_COMMENT_IDENTIFIER}\n## PR Summary\n\n{new_summary}",
            current_body,
            flags=re.DOTALL
        )
    else:
        updated_body = f"{PR_SUMMARY_COMMENT_IDENTIFIER}\n## PR Summary\n\n{new_summary}\n\n{current_body}"

    try:
        github.update_pull_request(updated_body)
        Log.print_yellow("PR description updated successfully!")
    except RepositoryError as e:
        Log.print_red(f"Failed to update PR description: {e}")

def process_file(file, ai, github, vars, reviewed_files):
    if file in reviewed_files:
        Log.print_green(f"Skipping file {file} as it has already been reviewed.")
        return

    Log.print_green(f"Reviewing file: {file}")
    try:
        with open(file, 'r', encoding="utf-8", errors="replace") as f:
            file_content = f.read()
    except FileNotFoundError:
        Log.print_yellow(f"File not found: {file}")
        return

    file_diffs = Git.get_diff_in_file(head_ref=vars.head_ref, base_ref=vars.base_ref, file_path=file)
    if not file_diffs:
        Log.print_red(f"No diffs found for: {file}")
        return

    Log.print_green(f"AI analyzing changes in {file}...")
    response = ai.ai_request_diffs(code=file_content, diffs=file_diffs)

    # Truyền diff_lines cho hàm handle_ai_response
    handle_ai_response(response, github, file, file_diffs, reviewed_files, vars)


def handle_ai_response(response, github, file, file_diffs, vars):
    if not response or AiBot.is_no_issues_text(response):
        Log.print_green(f"No issues detected in {file}.")
        return

    existing_comments = github.get_comments()
    existing_comment_bodies = {comment['body'] for comment in existing_comments}

    latest_commit_id = github.get_latest_commit_id()

    diff_lines = file_diffs.split("\n")
    line_number = None
    diff_hunk = ""  # Biến để lưu diff_hunk hiện tại

    for diff in diff_lines:
        if diff.startswith("@@"):
            match = re.search(r"\+(\d+)", diff)
            if match:
                line_number = int(match.group(1))
                Log.print_yellow(f"Diff hunk start: {diff}, line_number: {line_number}")
                diff_hunk = diff  # Bắt đầu một diff_hunk mới
            continue

        if diff.startswith("+") and line_number:
            # Thêm dòng hiện tại vào diff_hunk
            diff_hunk += "\n" + diff
            # Tính position trong diff_hunk
            position = diff_hunk.count('\n')  # Số dòng trong diff_hunk
            comment_body = response.strip()

            if comment_body.strip() not in existing_comment_bodies:
                Log.print_yellow(f"Posting comment to line {line_number}: {comment_body.strip()}")
                try:
                    github.post_comment_to_line(
                        text=comment_body.strip(),
                        commit_id=latest_commit_id,
                        file_path=file,
                        line=line_number,
                        position=position,
                        diff_hunk=diff_hunk  # Gửi diff_hunk
                    )
                    Log.print_yellow(f"Posted review comment at line {line_number}: {comment_body.strip()}")
                except RepositoryError as e:
                    Log.print_red(f"Failed to post review comment: {e}")
            else:
                Log.print_yellow(f"Skipping comment: Comment already exists")
            line_number += 1
        else:
            # Nếu không phải là dòng bắt đầu bằng "+", hãy thêm vào diff_hunk hiện tại
            if diff_hunk:
                diff_hunk += "\n" + diff

if __name__ == "__main__":
    main()