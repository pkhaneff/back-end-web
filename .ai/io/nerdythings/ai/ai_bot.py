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

        return AiBot.__chat_gpt_ask_long.format(
            no_response=AiBot.__no_response,
            diffs=diffs,
            code=code
        )

    @staticmethod
    def is_no_issues_text(source: str) -> bool:
        target = AiBot.__no_response.replace(" ", "")
        source_no_spaces = source.replace(" ", "")
        return source_no_spaces.startswith(target)
    
    @staticmethod
    def split_ai_response(input, total_lines_in_code) -> list[LineComment]:
        if not input:
            return []

        comments = []
        # Tách các entry bằng dấu xuống dòng kép và khoảng trắng thừa
        entries = re.split(r"\n\s*\n", input.strip())

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            # Tìm kiếm các thông tin cần thiết từ mỗi entry
            match = re.match(r"\*\*\[Line\s*(\d+)\s*\]\s*-\s*\[(Warning|Error|Critical)\]\s*-\s*\[(.*?)\]\s*-\s*(.*)\*\*", entry)

            if match:
                line_number, severity, issue_type, description = match.groups()
                try:
                    line_number = int(line_number)
                except ValueError:
                    print(f"Warning: Could not parse line number: {line_number}")
                    continue  # Bỏ qua entry nếu không parse được line number

                if line_number < 1 or line_number > total_lines_in_code:
                    print(f"Warning: Line number out of range: {line_number}")
                    continue
                
                # Tìm kiếm code và suggested fix
                code_match = re.search(r"Code:\s*```diff\s*(.*?)\s*```", entry, re.DOTALL)
                code = code_match.group(1).strip() if code_match else ""

                fix_match = re.search(r"Suggested Fix \(if applicable\):\s*```diff\s*(.*?)\s*```", entry, re.DOTALL)
                suggested_fix = fix_match.group(1).strip() if fix_match else ""

                # Tạo comment với đầy đủ thông tin (giữ nguyên format yêu cầu)
                comment_text = f"""**[Line {line_number}] - [{severity}] - [{issue_type}] - {description.strip()}**

                    **Code:**
                    ```diff
                    {code}
                Suggested Fix (if applicable):
                {suggested_fix}
            ```"""

                comments.append(LineComment(line=line_number, text=comment_text))
            else:
                # Nếu không khớp format chuẩn, coi như là 1 comment tự do
                comments.append(LineComment(line=0, text=entry))

        return comments