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
OWNER_COMMENT_IDENTIFIER = "<!-- OWNER COMMENT -->"
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

    file_summaries = update_pr_summary(changed_files, ai, github)

    for file in changed_files:
        process_file(file, ai, github, vars)

    #Generate and post the owner comment
    owner_comment = generate_owner_comment(changed_files, github, vars)
    if owner_comment:
      post_or_update_owner_comment(github, owner_comment)



def generate_summary_table(file_summaries):
    """Creates a PR Summary table as a Markdown string."""
    table_header = "| <div style='width:40%'>Files</div> | <div style='width:60%'>Business Summary</div> |\n|---------------------|-------------------------------------|"
    table_rows = []

    for file, summary in file_summaries.items():
        file_escaped = str(file).replace("|", "|").replace("*", "*").replace("_", "_").replace("\n", "<br>")
        summary_escaped = str(summary).replace("|", "|").replace("*", "*").replace("_", "_").replace("\n", "<br>")
        
        summary_escaped = re.sub(r"^\s*[-•]\s*", "", summary_escaped, flags=re.MULTILINE)

        row = f"| {file_escaped} | {summary_escaped} |"
        table_rows.append(row)

    if not table_rows:
        return "No summaries available."

    return "\n".join([table_header] + table_rows)


def update_pr_summary(changed_files, ai, github):
    Log.print_green("Updating PR description...")

    pr_data = github.get_pull_request()
    current_body = pr_data.get("body") or ""

    # Extract existing summaries from the PR body
    existing_summaries = {}
    summary_table_match = re.search(f"{PR_SUMMARY_COMMENT_IDENTIFIER}.*?\n(.*?)(\n{PR_SUMMARY_FILES_IDENTIFIER}|\n{OWNER_COMMENT_IDENTIFIER}|\n\n)", current_body, re.DOTALL)
    if summary_table_match:
        summary_table_markdown = summary_table_match.group(1).strip()
        # Parse the markdown table to extract existing summaries
        existing_summaries = parse_summary_table(summary_table_markdown) # Function to parse is created below
    else:
        Log.print_yellow("No existing summary table found.")

    file_summaries = existing_summaries.copy()  # Start with existing summaries

    # Generate summaries for new/modified files
    for file in changed_files:
        try:
            with open(file, 'r', encoding="utf-8", errors="replace") as f:
                content = f.read()
                new_summary = ai.ai_request_summary(file_changes={file:content[:1500]}, summary_prompt=SUMMARY_PROMPT)
                file_summaries[file] = new_summary
        except FileNotFoundError:
            Log.print_yellow(f"File not found: {file}")
            file_summaries[file] = f"File not found: {file}"
        except Exception as e:
            Log.print_red(f"Error processing file {file}: {e}")
            file_summaries[file] = f"Error processing file {file}: {e}"

    summary_table = generate_summary_table(file_summaries)
    files_comment = "" #Empty this out since we removed the files storing


    if PR_SUMMARY_COMMENT_IDENTIFIER in current_body:
        updated_body = re.sub(
            f"{PR_SUMMARY_COMMENT_IDENTIFIER}.*",
            f"{PR_SUMMARY_COMMENT_IDENTIFIER}\n## Summary by BAP_Review\n\n{summary_table}\n{files_comment}",
            current_body,
            flags=re.DOTALL
        )
    else:
        updated_body = f"{PR_SUMMARY_COMMENT_IDENTIFIER}\n## Summary by BAP_Review\n\n{summary_table}\n{files_comment}\n\n{current_body}"

    try:
        github.update_pull_request(updated_body)
        Log.print_yellow("PR description updated successfully!")
    except RepositoryError as e:
        Log.print_red(f"Failed to update PR description: {e}")

    return file_summaries #Returning for the owner comment

def parse_summary_table(markdown_table):
    """Parses the summary table from markdown to extract existing summaries."""
    file_summaries = {}
    rows = markdown_table.strip().split('\n')

    # Check if there is a header row and a separator row:
    if len(rows) < 3:
        return file_summaries

    # Check if it is a valid markdown table
    if not rows[1].startswith("|---"):
        return file_summaries

    #Skip the header and separator row
    for row in rows[2:]:
        parts = row.split('|')
        if len(parts) != 3:  # Expecting | File | Summary |
            continue

        file_name = parts[1].strip()
        summary = parts[2].strip()

        # Unescape markdown characters:
        file_name = file_name.replace("\\|", "|").replace("\\*", "*").replace("\\_", "_").replace("<br>", "\n")
        summary = summary.replace("\\|", "|").replace("\\*", "*").replace("\\_", "_").replace("<br>", "\n")

        file_summaries[file_name] = summary

    return file_summaries

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

def generate_owner_comment(changed_files, github, vars):
    """Generates the owner's comment with dropdowns for each changed file."""

    comment = f"{OWNER_COMMENT_IDENTIFIER}\n## Owner's Review Notes\n"
    comment += "<details>\n"
    comment += "  <summary><b>List Change History</b></summary>\n\n"

    for file in changed_files:
        try:
            repo = git.Repo(vars.repo_path)
            try:
                repo.git.rev_parse('--verify', 'main')
                base_branch = 'main'
            except git.exc.GitCommandError:
                base_branch = vars.base_ref

            diff = repo.git.diff(base_branch, vars.head_ref, '--', file)

            comment += "  <details>\n"
            comment += f"    <summary><b>{file}</b></summary>\n\n"

            comment += "    <ul>\n"
            for line in diff.splitlines():
                comment += f"      <li><code>{line}</code></li>\n"
            comment += "    </ul>\n\n"

            comment += "    **Impact:** (Summary of impact needs to be manually added here)\n\n" #Manually added because you need domain knowledge to do so

            comment += "  </details>\n\n"

        except Exception as e:
            Log.print_red(f"Error generating diff for owner comment: {e}")
            comment += f"  <details>\n"
            comment += f"    <summary><b>{file}</b> - Error generating diff</summary>\n\n"
            comment += f"    Error: {e}\n\n"
            comment += "  </details>\n\n"

    comment += "</details>\n"
    return comment

def post_or_update_owner_comment(github, comment):
    """Posts a new comment or updates an existing one."""
    existing_comments = github.get_comments()
    owner_comment_exists = False

    for existing_comment in existing_comments:
        if OWNER_COMMENT_IDENTIFIER in existing_comment['body']:
            Log.print_yellow("Updating existing owner comment...")
            try:
                github.update_comment(existing_comment['id'], comment)
                Log.print_green("Owner comment updated successfully!")
            except RepositoryError as e:
                Log.print_red(f"Failed to update owner comment: {e}")
            owner_comment_exists = True
            break

    if not owner_comment_exists:
        Log.print_yellow("Posting new owner comment...")
        try:
            github.post_comment_general(comment)
            Log.print_green("Owner comment posted successfully!")
        except RepositoryError as e:
            Log.print_red(f"Failed to post owner comment: {e}")



if __name__ == "__main__":
    main()