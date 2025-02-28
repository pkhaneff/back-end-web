import os
import re
import git
from git_utils import GitUtils
from ai.chat_gpt import ChatGPT
from log import Log
from ai.ai_bot import AiBot
from ai.prompts import SUMMARY_PROMPT
from env_vars import EnvVars
from repository.github import GitHub
from repository.repository import RepositoryError
import sys
import json

PR_SUMMARY_COMMENT_IDENTIFIER = "<!-- PR SUMMARY COMMENT -->"
PR_SUMMARY_FILES_IDENTIFIER = "<!-- PR SUMMARY FILES -->"
EXCLUDED_FOLDERS = {".ai/io/nerdythings", ".github/workflows"}

def main():
    vars = EnvVars()
    vars.check_vars()

    if os.getenv("GITHUB_EVENT_NAME") != "pull_request" or not vars.pull_number:
        Log.print_red("This action only runs on pull request events.")
        return

    github = GitHub(vars.token, vars.owner, vars.repo, vars.pull_number)
    ai = ChatGPT(vars.chat_gpt_token, vars.chat_gpt_model)

    changed_files = GitUtils.get_diff_files(head_ref=vars.head_ref, base_ref=vars.base_ref)
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

    for file in changed_files:
        process_file(file, ai, github, vars)

def generate_summary_table(all_files, file_summaries):
    """Creates a PR Summary table as a Markdown string."""
    table_header = "| Files | Change Summary |\n|---|---|"
    table_rows = []

    print(f"Debug: all_files = {all_files}")  # Debugging
    print(f"Debug: file_summaries = {file_summaries}")  # Debugging

    if len(all_files) != len(file_summaries):
        Log.print_red("Error: all_files and file_summaries have different lengths!")
        return "Error: Mismatched file and summary counts."

    for file, summary in zip(all_files, file_summaries):
        # Escape Markdown special characters
        file_escaped = file.replace("|", "\\|").replace("*", "\\*").replace("_", "\\_")
        summary_escaped = summary.replace("|", "\\|").replace("*", "\\*").replace("_", "\\_")

        row = f"| {file_escaped} | {summary_escaped} |"
        table_rows.append(row)
        print(f"Debug: Row = {row}") # Debugging each row
    return "\n".join([table_header] + table_rows)

def update_pr_summary(changed_files, ai, github):
    Log.print_green("Updating PR description...")

    pr_data = github.get_pull_request()
    current_body = pr_data.get("body") or ""

    existing_files = []
    match = re.search(f"{PR_SUMMARY_FILES_IDENTIFIER}(.*){PR_SUMMARY_FILES_IDENTIFIER}", current_body, re.DOTALL)
    if match:
        try:
            existing_files = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            Log.print_red("Error decoding existing files list. Resetting list.")
            existing_files = []

    all_files = list(set(changed_files + existing_files))

    file_summaries = []
    for file in all_files:
        try:
            with open(file, 'r', encoding="utf-8", errors="replace") as f:
                content = f.read()
                # Modify prompt to focus on business impact/purpose
                business_prompt = SUMMARY_PROMPT.replace(
                    "Hãy mô tả các thay đổi trong file sau đây theo phong cách ngắn gọn",
                    "Hãy tóm tắt mục đích kinh doanh hoặc tác động của các thay đổi trong file sau đây."
                )
                new_summary = ai.ai_request_summary(file_changes={file:content[:1000]}, prompt=business_prompt)
                file_summaries.append(new_summary)
        except FileNotFoundError:
            Log.print_yellow(f"File not found: {file}")
            file_summaries.append(f"File not found: {file}")
        except Exception as e:
            Log.print_red(f"Error processing file {file}: {e}")
            file_summaries.append(f"Error processing file {file}: {e}")

    print(f"all_files: {all_files}")
    print(f"file_summaries: {file_summaries}")
    summary_table = generate_summary_table(all_files, file_summaries)

    files_comment = f"{PR_SUMMARY_FILES_IDENTIFIER}{json.dumps(all_files)}{PR_SUMMARY_FILES_IDENTIFIER}"

    if PR_SUMMARY_COMMENT_IDENTIFIER in current_body:
        updated_body = re.sub(
            f"{PR_SUMMARY_COMMENT_IDENTIFIER}.*",
            f"{PR_SUMMARY_COMMENT_IDENTIFIER}\n## Summary by BAP_Review\n\n{summary_table}\n\n{files_comment}",
            current_body,
            flags=re.DOTALL
        )
    else:
        updated_body = f"{PR_SUMMARY_COMMENT_IDENTIFIER}\n## Summary by BAP_Review\n\n{summary_table}\n\n{files_comment}\n\n{current_body}"

    try:
        github.update_pull_request(updated_body)
        Log.print_yellow("PR description updated successfully!")
    except RepositoryError as e:
        Log.print_red(f"Failed to update PR description: {e}")


def process_file(file, ai, github, vars):
    Log.print_green(f"Reviewing file: {file}")
    try:
        with open(file, 'r', encoding="utf-8", errors="replace") as f:
            file_content = f.read()
    except FileNotFoundError:
        Log.print_yellow(f"File not found: {file}")
        return

    file_diffs = GitUtils.get_diff_in_file(head_ref=vars.head_ref, base_ref=vars.base_ref, file_path=file)
    if not file_diffs:
        Log.print_red(f"No diffs found for: {file}")
        return

    individual_diffs = GitUtils.split_diff_into_chunks(file_diffs)

    for diff_chunk in individual_diffs:
        Log.print_yellow(f"base_ref: {vars.base_ref}, head_ref: {vars.head_ref}, file: {file}")
        try:
            repo = git.Repo(vars.repo_path)
            try:
                repo.git.rev_parse('--verify', 'main')
                base_branch = 'main'
            except git.exc.GitCommandError:
                base_branch = vars.base_ref

            Log.print_yellow(f"DEBUG: base_ref = {vars.base_ref}, base_branch = {base_branch}")
            diff = repo.git.diff(base_branch, vars.head_ref, '--', file)


            line_numbers = "..."
            changed_lines = diff
        except Exception as e:
            Log.print_red(f"Error while parsing diff chunk: {e}")
            Log.print_red(f"Exception details: {type(e).__name__}, {e}")
            line_numbers = "N/A"
            changed_lines = "N/A"

        diff_data = {
            "code": diff_chunk,
            "severity": "Warning",
            "type": "General",
            "issue_description": "Potential issue",
            "line_numbers": line_numbers,
            "changed_lines": changed_lines,
            "explanation": "",
        }
        Log.print_yellow(f"Diff data being sent to AI: {diff_data}")

        try:
            response = ai.ai_request_diffs(code=file_content, diffs=diff_data)
        except Exception as e:
            Log.print_red(f"Error during AI request: {e}")
            continue

        if response and not AiBot.is_no_issues_text(response):
            comments = AiBot.split_ai_response(response, diff_chunk, file_path=file)
            existing_comments = github.get_comments()
            existing_comment_bodies = {c['body'] for c in existing_comments}
            for comment in comments:
                if comment.text:

                    comment_text = comment.text.strip()
                    if comment_text not in existing_comment_bodies:
                        Log.print_yellow(f"Posting general comment:\n{comment_text}")
                        try:
                            github.post_comment_general(
                                text=comment_text
                            )
                        except RepositoryError as e:
                            Log.print_red(f"Failed to post review comment: {e}")
                        except Exception as e:
                            Log.print_red(f"Unexpected error: {e}")
                    else:
                        Log.print_yellow(f"Skipping comment: Comment already exists")
                else:
                    Log.print_yellow(f"Skipping comment because no content.")
        else:
            Log.print_green(f"No critical issues found in diff chunk, skipping comments.")
            continue


def parse_ai_suggestions(response):
    if not response:
        return []

    suggestions = []
    for suggestion_text in response.split("\n\n"):
        suggestion_text = suggestion_text.strip()
        if suggestion_text:
            suggestions.append({"text": suggestion_text})
    return suggestions
if __name__ == "__main__":
    main()