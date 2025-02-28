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
        - Categorize issues by severity: **:warning: Warning, :x: Error, :bangbang: Critical**.

        **Review Guidelines:**
        - **Syntax Errors**: Compilation/runtime failures introduced by the change.
        - **Logical Errors**: Incorrect conditions, infinite loops, unexpected behavior caused by the change.
        - **Security Vulnerabilities**: Security problems directly caused by the change.
        - **Performance Bottlenecks**: Performance degradation as a result of the change.

        **Output Format:**
        Each issue should follow the following Markdown format, resembling a commit log:

        **[ERROR] - [{severity}] - [{type}] - {issue_description}**

        **:interrobang: Explanation:**
        {explanation}

        **Code:**
        ```diff
        {code}
        ```

        ** :white_check_mark: Suggested Fix (if applicable):**
        ```diff
        {suggested_fix}
        ```

        **Important Notes:**
        *   The review **MUST** be based solely on the provided `diffs`. If there are no issues within the `diffs`, then respond with "{no_response}".
    """

    @abstractmethod
    def ai_request_diffs(self, code, diffs) -> str:
        pass

    @staticmethod
    def build_ask_text(code, diffs) -> str:
        """Xây dựng prompt cho AI, bao gồm code và diff."""

        if not diffs:
            return ""

        if isinstance(diffs, str):
            code_to_review = diffs
            severity = "Warning"
            issue_type = "General Issue"
            issue_description = "Potential issue in the changed code."
            explanation = ""  # Thêm explanation
            suggested_fix = ""
        else:
            code_to_review = diffs[0].get("code", "") if isinstance(diffs, list) else diffs.get("code", "")
            severity = diffs[0].get("severity", "Warning") if isinstance(diffs, list) else diffs.get("severity", "Warning")
            issue_type = diffs[0].get("type", "General Issue") if isinstance(diffs, list) else diffs.get("type", "General Issue")
            issue_description = diffs[0].get("issue_description", "No description") if isinstance(diffs, list) else diffs.get("issue_description", "No description")
            explanation = diffs[0].get("explanation", "") if isinstance(diffs, list) else diffs.get("explanation", "")
            suggested_fix = diffs[0].get("suggested_fix", "") if isinstance(diffs, list) else diffs.get("suggested_fix", "")

        return AiBot.__chat_gpt_ask_long.format(
            problems=AiBot.__problems,
            no_response=AiBot.__no_response,
            diffs=code_to_review,
            code=code,
            severity=severity,
            type=issue_type,
            issue_description=issue_description,
            explanation=explanation, # Truyền explanation vào prompt
            suggested_fix=suggested_fix
        )

    @staticmethod
    def is_no_issues_text(source: str) -> bool:
        target = AiBot.__no_response.replace(" ", "")
        source_no_spaces = source.replace(" ", "")
        return source_no_spaces.startswith(target)

    @staticmethod
    def split_ai_response(input, diffs, file_path="") -> list[LineComment]:
        """
        Chia AI response thành danh sách comment, mỗi comment chứa diff (code thay đổi)
        gây ra lỗi và thông tin về lỗi đó. Thêm file_path vào đầu mỗi comment và gạch ngang phân tách.
        """
        if not input:
            return []

        comments = []
        entries = re.split(r"###", input.strip())
        separator = "---\n"

        for i, entry in enumerate(entries):
            entry = entry.strip()
            if not entry:
                continue

            comment_text = f"**File:** {file_path}\n\n"

            match = re.match(r"\s*\[ERROR\]\s*-\s*\[(Warning|Error|Critical)\]\s*-\s*\[(.*?)\]\s*-\s*(.*)", entry)
            if match:
                severity, issue_type, description = match.groups()

                explanation_match = re.search(r"Explanation:\s*(.*?)\s*Code:", entry, re.DOTALL) # Tìm explanation trước Code
                explanation = explanation_match.group(1).strip() if explanation_match else ""

                code_match = re.search(r"Code:\s*```diff\s*(.*?)\s*```", entry, re.DOTALL)
                code = code_match.group(1).strip() if code_match else ""

                fix_match = re.search(r":white_check_mark: Suggested Fix \(if applicable\):\s*```diff\s*(.*?)\s*```", entry, re.DOTALL)
                suggested_fix = fix_match.group(1).strip() if fix_match else ""

                comment_text += f"**[ERROR] - [{severity}] - [{issue_type}] - {description.strip()}**\n\n"
                if explanation:
                   comment_text += f"**Explanation:**\n{explanation}\n\n" # Thêm explanation vào comment
                comment_text += f"**Code:**\n```diff\n{code}\n```\n\n"
                if suggested_fix:
                    comment_text += f"**Suggested Fix:**\n```diff\n{suggested_fix}\n```\n"

            else:
                comment_text += entry

            if i > 0:
                comment_text = separator + comment_text

            comments.append(LineComment(line="", text=comment_text))

        return comments