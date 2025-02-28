from abc import ABC, abstractmethod
import re
from log import Log
from ai.line_comment import LineComment
from ai.prompts import CHAT_GPT_ASK_LONG, PROBLEMS, NO_RESPONSE


class AiBot(ABC):

    __no_response =  NO_RESPONSE
    __problems = PROBLEMS
    __chat_gpt_ask_long = CHAT_GPT_ASK_LONG 

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
            line_numbers = "N/A"
            changed_lines = "N/A"
            explanation = ""
            suggested_fix = ""
        else:
            code_to_review = diffs[0].get("code", "") if isinstance(diffs, list) else diffs.get("code", "")
            severity = diffs[0].get("severity", "Warning") if isinstance(diffs, list) else diffs.get("severity", "Warning")
            issue_type = diffs[0].get("type", "General Issue") if isinstance(diffs, list) else diffs.get("type", "General Issue")
            issue_description = diffs[0].get("issue_description", "No description") if isinstance(diffs, list) else diffs.get("issue_description", "No description")
            line_numbers = diffs[0].get("line_numbers", "N/A") if isinstance(diffs, list) else diffs.get("line_numbers", "N/A")
            changed_lines = diffs[0].get("changed_lines", "N/A") if isinstance(diffs, list) else diffs.get("changed_lines", "N/A")
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
            line_numbers=line_numbers,
            changed_lines=changed_lines,
            explanation=explanation,
            suggested_fix=suggested_fix
        )

    @staticmethod
    def is_no_issues_text(source: str) -> bool:
        target = AiBot.__no_response.replace(" ", "")
        source_no_spaces = source.replace(" ", "")
        return source_no_spaces.startswith(target)

    @staticmethod
    def split_ai_response(input, diffs, file_path="") -> list[LineComment]:
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

            match = re.match(r"\s*\[:x:ERROR\]\s*-\s*\[(:warning:Warning|:x:Error|:bangbang:Critical)\]\s*-\s*\[(.*?)\]\s*-\s*(.*)", entry)
            if match:
                severity, issue_type, description = match.groups()

                lines_match = re.search(r"Lines:\s*```\s*([\s\S]*?)\s*```", entry)
                lines_info = lines_match.group(1).strip() if lines_match else ""

                fix_match = re.search(r":white_check_mark: Suggested Fix \(if applicable\):\s*```diff\s*(.*?)\s*```", entry, re.DOTALL)
                suggested_fix = fix_match.group(1).strip() if fix_match else ""

                comment_text += f"**[ERROR] - [{severity}] - [{issue_type}] - {description.strip()}**\n\n"
                if lines_info:
                    comment_text += f"**:point_right:Lines:**\n```\n{lines_info}\n```\n\n"

                if suggested_fix:
                    comment_text += f"**Suggested Fix:**\n```diff\n{suggested_fix}\n```\n"

            else:
                comment_text += entry

            if i > 0:
                comment_text = separator + comment_text

            comments.append(LineComment(line="", text=comment_text))

        return comments