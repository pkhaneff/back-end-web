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

        **Review Guidelines:**
        - **Syntax Errors**: Compilation/runtime failures introduced by the change.
        - **Logical Errors**: Incorrect conditions, infinite loops, unexpected behavior caused by the change.
        - **Security Vulnerabilities**: Security problems directly caused by the change.
        - **Performance Bottlenecks**: Performance degradation as a result of the change.

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
        *   Titles and instructions are formatted for readability.
        *   The review **MUST** be based solely on the provided `diffs`. If there are no issues within the `diffs`, then respond with "{no_response}".
    """

    @staticmethod
    def get_context_lines(code, line_number, context=2):
        """
        Lấy một số dòng xung quanh dòng thay đổi để cung cấp ngữ cảnh cho AI.  (Không còn dùng nữa, vì giờ chỉ tập trung vào diff.)
        """
        lines = code.split("\n")
        start = max(line_number - context - 1, 0) 
        end = min(line_number + context, len(lines))
        return "\n".join(lines[start:end])

    @abstractmethod
    def ai_request_diffs(self, code, diffs) -> str:
        pass

    @staticmethod
    def build_ask_text(code, diffs) -> str:
        """Xây dựng prompt cho AI, bao gồm code và diff."""

        if not diffs:
            return "" 
        if isinstance(diffs, str): 
            line_number_match = re.search(r"^\+\+\+ b/.*\n@@ -\d+,\d+ \+(\d+),?", diffs, re.MULTILINE)
            line_number = int(line_number_match.group(1)) if line_number_match else "N/A"

            severity = "Warning"
            issue_type = "General Issue"
            issue_description = "Potential issue in the changed code."
            suggested_fix = ""
            code_to_review = diffs
        else: 
            line_number = diffs[0].get("line_number", "N/A") if isinstance(diffs, list) else diffs.get("line_number", "N/A")
            severity = diffs[0].get("severity", "Warning") if isinstance(diffs, list) else diffs.get("severity", "Warning")
            issue_type = diffs[0].get("type", "General Issue") if isinstance(diffs, list) else diffs.get("type", "General Issue")
            issue_description = diffs[0].get("issue_description", "No description") if isinstance(diffs, list) else diffs.get("issue_description", "No description")
            suggested_fix = diffs[0].get("suggested_fix", "") if isinstance(diffs, list) else diffs.get("suggested_fix", "")
            code_to_review = diffs[0].get("code", "") if isinstance(diffs, list) else diffs.get("code", "")

        return AiBot.__chat_gpt_ask_long.format(
            problems=AiBot.__problems,
            no_response=AiBot.__no_response,
            diffs=code_to_review, 
            code=code,
            line_number=line_number,
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
    
    @staticmethod
    def extract_offset_from_hunk(diffs):
        """Trích xuất số dòng bắt đầu từ hunk diff"""
        match = re.search(r"@@ -\d+,\d+ \+(\d+),?", diffs)
        if match:
            return int(match.group(1))  
        return None  

    @staticmethod
    def split_ai_response(input, diffs, total_lines_in_code) -> list[LineComment]:
        """Chia AI response thành danh sách comment kèm vị trí dòng chính xác"""
        if not input:
            return []

        offset = AiBot.extract_offset_from_hunk(diffs)
        if offset is None:
            print("Warning: Không tìm thấy offset từ hunk!")
            return []

        comments = []
        entries = re.split(r"###", input.strip())

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            match = re.match(r"\s*\[Line\s*(\d+)\s*\]\s*-\s*\[(Warning|Error|Critical)\]\s*-\s*\[(.*?)\]\s*-\s*(.*)", entry)
            if match:
                line_number, severity, issue_type, description = match.groups()
                try:
                    line_number = int(line_number)
                except ValueError:
                    print(f"Warning: Không thể parse line number: {line_number}")
                    continue 

                # Điều chỉnh line_number dựa trên offset
                adjusted_line = offset + (line_number - 1)
                if adjusted_line < 1 or adjusted_line > total_lines_in_code:
                    print(f"Warning: Line number out of range: {adjusted_line}")
                    continue

                code_match = re.search(r"Code:\s*```diff\s*(.*?)\s*```", entry, re.DOTALL)
                code = code_match.group(1).strip() if code_match else ""

                fix_match = re.search(r"Suggested Fix\s*```diff\s*(.*?)\s*```", entry, re.DOTALL)
                suggested_fix = fix_match.group(1).strip() if fix_match else ""

                comment_text = f"**[Line {adjusted_line}] - [{severity}] - [{issue_type}] - {description.strip()}**\n\n"
                if code:
                    comment_text += f"**Code:**\n```diff\n{code}\n```\n\n"
                if suggested_fix:
                    comment_text += f"**Suggested Fix:**\n```diff\n{suggested_fix}\n```\n"

                comments.append(LineComment(line=adjusted_line, text=comment_text))
            else:
                comments.append(LineComment(line=0, text=entry))

        return comments