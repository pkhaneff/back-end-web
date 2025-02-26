from abc import ABC, abstractmethod
import re
from ai.line_comment import LineComment

class AiBot(ABC):
    
    __no_response = "No critical issues found"
    __problems = "errors, security issues, performance bottlenecks, or bad practices"
    __chat_gpt_ask_long = """
        You are an AI code reviewer with expertise in multiple programming languages.
        Your goal is to analyze Git diffs and identify potential issues.

        **Review Scope:**
        - Focus on meaningful structural changes, ignoring formatting or comments.
        - Provide clear explanations and actionable suggestions.
        - Categorize issues by severity: **Warning, Error, Critical**.

        **Review Guidelines:**
        - **Syntax Errors**: Compilation/runtime failures.
        - **Logical Errors**: Incorrect conditions, infinite loops, unexpected behavior.

        **Output Format:**
        Each issue should follow the following Markdown format, resembling a commit log:
        
        **[Line {line_number}] - [{severity}] - [{type}] - {issue_description}**

        **Code:**
        diff
        {code}

        Suggested Fix (nếu có):
        {suggested_fix}
         Ví dụ:
        ### ⚠️ [Warning] [Logical Error] - Incorrect function name used for saving newComment.

        **Code:**
        ```diff
        - await newComment.saved()
        + await newComment.save()

        **Suggested Fix:**
        Sửa lại phương thức `.saved()` thành `.save()` để tránh lỗi.            
                
        **Note:**
        *   `Code` and `Suggested Fix` are wrapped with ```diff to show code diffs and fixes.
        *   Titles and instructions are formatted for readability.

        **Reason for modification:**
        *   Removed complex Markdown like bullet points for easy copying.
        *   Used simple titles to differentiate sections.
        *   Kept code blocks to easily identify diffs and fixes.
    """

    @staticmethod
    def get_context_lines(code, line_number, context=2):
        """
        Lấy một số dòng xung quanh dòng thay đổi để cung cấp ngữ cảnh cho AI.
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
        if isinstance(diffs, list) and diffs:
            line_number = diffs[0].get("line_number", "N/A")
            severity = diffs[0].get("severity", "Warning")
            issue_type = diffs[0].get("type", "General Issue") 
            issue_description = diffs[0].get("issue_description", "No description")
            suggested_fix = diffs[0].get("suggested_fix", "")
        elif isinstance(diffs, dict):
            line_number = diffs.get("line_number", "N/A")
            severity = diffs.get("severity", "Warning")
            issue_type = diffs.get("type", "General Issue") 
            issue_description = diffs.get("issue_description", "No description")
            suggested_fix = diffs.get("suggested_fix", "")
        else:
            line_number = "N/A"
            severity = "Warning"
            issue_type = "General Issue"
            issue_description = "No description"
            suggested_fix = ""

        return AiBot.__chat_gpt_ask_long.format(
            problems=AiBot.__problems,
            no_response=AiBot.__no_response,
            diffs=diffs,
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
    def split_ai_response(input, total_lines_in_code) -> list[LineComment]:
        if not input:
            return []

        comments = []
        # Tách các entry bằng dấu ###
        entries = re.split(r"###", input.strip())

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            # Tìm kiếm các thông tin cần thiết từ mỗi entry
            match = re.match(r"\s*\[Line\s*(\d+)\s*\]\s*-\s*\[(Warning|Error|Critical)\]\s*-\s*\[(.*?)\]\s*-\s*(.*)", entry)

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

                fix_match = re.search(r"Suggested Fix \(nếu có\):\s*```diff\s*(.*?)\s*```", entry, re.DOTALL)
                suggested_fix = fix_match.group(1).strip() if fix_match else ""

                # Tạo comment với đầy đủ thông tin
                comment_text = f"### [{severity}] [{issue_type}]\n\n{description.strip()}\n\n"
                if code:
                    comment_text += f"**Code:**\n```diff\n{code}\n```\n\n"
                if suggested_fix:
                    comment_text += f"**Suggested Fix:**\n```diff\n{suggested_fix}\n```\n"

                comments.append(LineComment(line=line_number, text=comment_text))
            else:
                # Nếu không khớp format chuẩn, coi như là 1 comment tự do
                comments.append(LineComment(line=0, text=entry))

        return comments