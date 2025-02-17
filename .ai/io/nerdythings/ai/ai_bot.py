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
        - **Security Issues**: SQL injection, XSS, hardcoded secrets, unvalidated inputs.  
        - **Performance Bottlenecks**: Unoptimized loops, redundant computations.  
        - **Best Practices Violations**: Not following language-specific best practices.  
        + - **Best Practices Violations**: Only report issues on unchanged or newly introduced code. 
        **Output Format:**  
        - Each issue should follow this format:
        ```markdown
        ⚠️ [Severity] - [Type] - Issue description and fix suggestion.  
        Suggested Fix:
        ```diff
        - new code
        + old code
        ```
        
        ```
        - If no issues are found, return exactly:  
        `{no_response}`.  
        **Git Diffs (Only structural changes considered):**  
        ```diff
        {diffs}
        ```
        ========= {code} ========= Answer in Markdown
    """


    @abstractmethod
    def ai_request_diffs(self, code, diffs) -> str:
        pass

    @staticmethod
    def build_ask_text(code, diffs) -> str:
        return AiBot.__chat_gpt_ask_long.format(
            problems=AiBot.__problems,
            no_response=AiBot.__no_response,
            diffs=diffs,
            code=code,
        )

    @staticmethod
    def is_no_issues_text(source: str) -> bool:
        target = AiBot.__no_response.replace(" ", "")
        source_no_spaces = source.replace(" ", "")
        return source_no_spaces.startswith(target)
    
    @staticmethod
    def split_ai_response(input) -> list[LineComment]:
        if not input:
            return []

        lines = input.strip().split("\n")
        models = []

        for full_text in lines:
            full_text = full_text.strip()
            if not full_text:
                continue

            match = re.match(r"(⚠️|❌)\s*\[(.*?)\]\s*\[(.*?)\]\s*(.*)", full_text)
            if match and all(match.groups()):
                severity_icon, severity, issue_type, description = match.groups()
                clean_description = description.capitalize().strip()
                if not clean_description.endswith("."):
                    clean_description += "."
                models.append(LineComment(line=0, text=f"{severity_icon} [{severity}] [{issue_type}] {clean_description}"))
            elif full_text.strip():  
                models.append(LineComment(line=0, text=full_text))

        return models
