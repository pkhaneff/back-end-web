import os
from git import Git
from ai.chat_gpt import ChatGPT
from log import Log
from ai.ai_bot import AiBot
from env_vars import EnvVars
from repository.github import GitHub
from repository.repository import RepositoryError

PR_SUMMARY_COMMENT_IDENTIFIER = "<!-- PR_SUMMARY_COMMENT -->"

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

    Log.print_yellow(f"Changed files: {changed_files}")

    update_pr_summary(changed_files, ai, github)

    # Set to track files that have been reviewed
    reviewed_files = set()

    for file in changed_files:
        process_file(file, ai, github, vars, reviewed_files)

def update_pr_summary(changed_files, ai, github):
    """
    Cập nhật/tạo comment PR summary. Nếu có comment cũ, chỉ sửa lại nó.
    """
    Log.print_green("Updating PR summary...")

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

    full_context = "\n\n".join(file_contents)
    new_summary = ai.ai_request_summary(code=full_context)

    pr_summary_comment_body = f"{PR_SUMMARY_COMMENT_IDENTIFIER}\n## PR Summary\n\n{new_summary}"

    existing_comments = github.get_comments()
    comment_id_to_update = None

    for comment in existing_comments:
        if PR_SUMMARY_COMMENT_IDENTIFIER in comment['body']:
            comment_id_to_update = comment['id']
            break

    try:
        if comment_id_to_update:
            Log.print_yellow(f"Updating existing PR summary comment (ID: {comment_id_to_update})...")
            github.update_comment(comment_id_to_update, pr_summary_comment_body)
        else:
            Log.print_yellow("Creating new PR summary comment...")
            github.post_comment_general(pr_summary_comment_body)

    except RepositoryError as e:
        Log.print_red(f"Failed to update/create PR summary comment: {e}")
    except Exception as e:
        Log.print_red(f"An unexpected error occurred during comment update/creation: {e}")


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

    handle_ai_response(response, github, file, file_diffs, reviewed_files)

def handle_ai_response(response, github, file, file_diffs, reviewed_files):
    if not response or AiBot.is_no_issues_text(response):
        Log.print_green(f"No issues detected in {file}.")
        reviewed_files.add(file)  
        return

    suggestions = parse_ai_suggestions(response)
    if not suggestions:
        Log.print_red(f"Failed to parse AI suggestions for {file}.")
        return

    comment_body = f"### AI Review for {file}\n\n"
    for suggestion in suggestions:
        comment_body += f"- {suggestion.strip()}\n"

    try:
        existing_comments = github.get_comments()
        comment_already_posted = False
        for comment in existing_comments:
            if comment['body'] == comment_body:
                comment_already_posted = True
                break

        if not comment_already_posted:
            github.post_comment_general(comment_body)
            Log.print_yellow(f"Posted review for {file}")
        else:
            Log.print_green(f"Review for {file} already posted, skipping.")

    except RepositoryError as e:
        Log.print_red(f"Failed to post review for {file}: {e}")

    reviewed_files.add(file)

def parse_ai_suggestions(response):
    return response.split("\n\n") if response else []

if __name__ == "__main__":
    main()