from abc import abstractmethod
import re
from ai.line_comment import LineComment

class AiBot:

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

        **Review Guidelines:**
        - **Syntax Errors**: Compilation/runtime failures introduced by the change.
        - **Logical Errors**: Incorrect conditions, infinite loops, unexpected behavior caused by the change.
        - **Security Vulnerabilities**: Security problems directly caused by the change.
        - **Performance Bottlenecks**: Performance degradation as a result of the change.

        **Output Format:**
        Each issue should follow the following Markdown format, resembling a commit log:

        **[ERROR] - [{severity}] - [{type}] - {issue_description}**

        **Code:**
        ```diff
        {code}
        ```

        **Suggested Fix (if applicable):**
        ```diff
        {suggested_fix}
        ```

        **Important Notes:**
        *   The review **MUST** be based solely on the provided `diffs`. If there are no issues within the `diffs`, then respond with "{no_response}".
    """

    

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
            suggested_fix = ""
        else:
            code_to_review = diffs[0].get("code", "") if isinstance(diffs, list) else diffs.get("code", "")
            severity = diffs[0].get("severity", "Warning") if isinstance(diffs, list) else diffs.get("severity", "Warning")
            issue_type = diffs[0].get("type", "General Issue") if isinstance(diffs, list) else diffs.get("type", "General Issue")
            issue_description = diffs[0].get("issue_description", "No description") if isinstance(diffs, list) else diffs.get("issue_description", "No description")
            suggested_fix = diffs[0].get("suggested_fix", "") if isinstance(diffs, list) else diffs.get("suggested_fix", "")

        return AiBot.__chat_gpt_ask_long.format(
            problems=AiBot.__problems,
            no_response=AiBot.__no_response,
            diffs=code_to_review,
            code=code,
            severity=severity,
            type=issue_type,
            issue_description=issue_description,
            suggested_fix=suggested_fix
        )

    @staticmethod
    def is_no_issues_text(source: str) -> bool:
        target = AiBot.__no_response.replace(" ", "")
        source_no_spaces = source.replace(" ", "")
        return source_no_spaces.startswith(target)
    
    @abstractmethod
    def ai_request_diffs(self, code, diffs) -> str:
        pass

    @staticmethod
    def split_ai_response(input, diffs) -> list[LineComment]:
        """Chia AI response thành danh sách comment, mỗi comment chứa 1 lỗi."""
        if not input:
            return []

        comments = []
        # Regex để tìm từng lỗi
        error_regex = re.compile(
            r"\*\*\[(Error|Warning|Critical)\] - \[(.*?)\] - \[(.*?)\] - (.*?)", re.DOTALL
        )
        # Tìm tất cả các lỗi trong input
        error_matches = error_regex.finditer(input)

        for match in error_matches:
            severity = match.group(1)
            issue_type = match.group(2)
            description = match.group(3)
            full_error = match.group(0)  # Lấy toàn bộ thông tin lỗi

            # Tìm code và suggested fix cho lỗi hiện tại
            code_match = re.search(r"Code:\s*```diff\s*(.*?)\s*```", full_error, re.DOTALL)
            code = code_match.group(1).strip() if code_match else ""

            fix_match = re.search(r"Suggested Fix:\s*```diff\s*(.*?)\s*```", full_error, re.DOTALL)
            suggested_fix = fix_match.group(1).strip() if fix_match else ""

            # Tạo comment
            comment_text = f"**[{severity}] - [{issue_type}] - {description.strip()}**\n\n"
            comment_text += f"**Code:**\n```diff\n{code}\n```\n\n"
            if suggested_fix:
                comment_text += f"**Suggested Fix:**\n```diff\n{suggested_fix}\n```\n"

            comments.append(LineComment(line="", text=comment_text))

        return comments