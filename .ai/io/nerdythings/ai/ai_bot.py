from abc import ABC, abstractmethod
import re
from ai.line_comment import LineComment  # Đảm bảo import class LineComment

class AiBot(ABC):
    
    __no_response = "No critical issues found"
    __problems = "errors, security issues, performance bottlenecks, or bad practices"
    __chat_gpt_ask_long = """
        You are an AI code reviewer with expertise in multiple programming languages.
        Your goal is to analyze Git diffs and identify potential issues, focusing **exclusively** on the lines that have been changed.

        **Review Scope:**
        - **Strictly limited to the changes highlighted in the provided diffs.**  Do not analyze the surrounding code.
        - Focus on meaningful structural changes within the diff, ignoring formatting or comments that are outside the diff.
        - Provide clear explanations and actionable suggestions.
        - Categorize issues by severity: **Warning, Error, Critical**.

        **Output Format:**
        Each issue should follow the following Markdown format, resembling a commit log:
        
        **[Line {line_number}] - [{severity}] - [{type}] - {issue_description}**

        **Code:**
        ```diff
        {code}
        ```

        **Suggested Fix (if applicable):**
        ```diff
        {suggested_fix}
        ```

        **Important Notes:**
        *   The `line_number` refers to the line number in the **modified file**, not the diff output.
        *   `Code` and `Suggested Fix` are wrapped with ```diff to clearly show the code diffs and fixes.
        *   The review **MUST** be based solely on the provided `diffs`. If there are no issues within the `diffs`, then respond with "{no_response}".
    """

    @staticmethod
    def build_ask_text(code, diffs) -> str:
        """Xây dựng prompt cho AI, bao gồm code và diff."""

        diffs_with_line_numbers = "\n".join([f"[Line {d['line_number']}] {d['diff']}" for d in diffs])
        print(f"DEBUG: diffs type: {type(diffs)}, value: {diffs}")
        return AiBot.__chat_gpt_ask_long.format(
            no_response=AiBot.__no_response,
            diffs=diffs_with_line_numbers,
            code=code
        )

    @staticmethod
    def is_no_issues_text(source: str) -> bool:
        target = AiBot.__no_response.replace(" ", "")
        source_no_spaces = source.replace(" ", "")
        return source_no_spaces.startswith(target)
    
    @staticmethod
    def estimate_line_number_from_diffs(diffs):
        """Cố gắng lấy line_number từ diff nếu bị thiếu."""
        match = re.search(r"@@ -\d+,\d+ \+(\d+),\d+ @@", diffs)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def split_ai_response(input, diffs, total_lines_in_code) -> list[LineComment]:
        if not input:
            return []

        comments = []
        entries = re.split(r"\n\s*\n", input.strip())

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            match = re.match(r"\*\*\[Line\s*(\d+)\s*\]\s*-\s*\[(Warning|Error|Critical)\]\s*-\s*\[(.*?)\]\s*-\s*(.*)\*\*", entry)

            if match:
                line_number, severity, issue_type, description = match.groups()
                try:
                    line_number = int(line_number)
                    if line_number < 1 or line_number > total_lines_in_code:
                        raise ValueError(f"Invalid line number: {line_number}")
                except ValueError:
                    print(f"Warning: Could not determine line number, attempting fallback...")
                    line_number = AiBot.estimate_line_number_from_diffs(diffs)
                    if not line_number:
                        print(f"Error: Could not extract a valid line number, skipping comment.")
                        continue  # Bỏ qua nếu không có số dòng chính xác
                
                code_match = re.search(r"Code:\s*```diff\s*(.*?)\s*```", entry, re.DOTALL)
                code = code_match.group(1).strip() if code_match else ""

                fix_match = re.search(r"Suggested Fix \(if applicable\):\s*```diff\s*(.*?)\s*```", entry, re.DOTALL)
                suggested_fix = fix_match.group(1).strip() if fix_match else ""

                comment_text = f"""**[Line {line_number}] - [{severity}] - [{issue_type}] - {description.strip()}**

                    **Code:**
                    ```diff
                    {code}
                Suggested Fix (if applicable):
                {suggested_fix}
            ```"""

                comments.append(LineComment(line=line_number, text=comment_text))
            else:
                comments.append(LineComment(line=0, text=entry))

        return comments
