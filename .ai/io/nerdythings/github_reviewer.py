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

    for file in changed_files:
        process_file(file, ai, github, vars)


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


def process_file(file, ai, github, vars):
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

    # Split diffs into individual chunks/changes
    individual_diffs = Git.split_diff_into_chunks(file_diffs)

    for diff_chunk in individual_diffs:
        Log.print_green(f"AI analyzing changes in {file}...")
        response = ai.ai_request_diffs(code=file_content, diffs=diff_chunk)  # review each change.

        # Process AI response and post comment immediately
        if response and not AiBot.is_no_issues_text(response):
            comments = AiBot.split_ai_response(response, diff_chunk)
            existing_comments = github.get_comments()
            existing_comment_bodies = {c['body'] for c in existing_comments}
            for comment in comments:  # Process each comment separately
                if comment.text:

                    comment_text = comment.text.strip()
                    if comment_text not in existing_comment_bodies:
                        Log.print_yellow(f"Posting general comment:\n{comment_text}")
                        try:
                            github.post_comment_general(
                                text=comment_text  # Full comment content
                            )
                        except RepositoryError as e:
                            Log.print_red(f"Failed to post review comment: {e}")
                        except Exception as e:
                            Log.print_red(f"Unexpected error: {e}")
                    else:
                        Log.print_yellow(f"Skipping comment: Comment already exists")
                else:
                    Log.print_yellow(f"Skipping comment because no content.")

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