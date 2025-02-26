import os
import json
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)

class EnvVars:
    def __init__(self):
        self.chat_gpt_token = os.getenv('CHATGPT_KEY')
        self.chat_gpt_model = os.getenv('CHATGPT_MODEL')
        self.token = os.getenv('GITHUB_TOKEN')
        
        self.owner = os.getenv('GITHUB_REPOSITORY_OWNER')
        self.repo = os.getenv('GITHUB_REPOSITORY').split('/')[-1]
        self.pull_number = os.getenv('GITHUB_PR_NUMBER')
        self.base_ref = os.getenv('GITHUB_BASE_REF')
        self.head_ref = os.getenv('GITHUB_HEAD_REF')
        
        print(f"DEBUG: CHATGPT_KEY={self.chat_gpt_token}, CHATGPT_MODEL={self.chat_gpt_model}")
        self.target_extensions = os.getenv('TARGET_EXTENSIONS', 'kt,java,py,js,ts,swift,c,cpp').split(',')

        self.commit_id = self.head_ref

        self.env_vars = {
            "owner": self.owner,
            "repo": self.repo,
            "token": self.token,
            "base_ref": self.base_ref,
            "head_ref": self.head_ref,
            "pull_number": self.pull_number,
            "chat_gpt_token": self.chat_gpt_token,
            "chat_gpt_model": self.chat_gpt_model,
            "commit_id": self.commit_id,
        }

        self.check_vars()

    def check_vars(self):
        required_vars = ["CHATGPT_KEY", "CHATGPT_MODEL", "GITHUB_TOKEN", "GITHUB_REPOSITORY_OWNER", "GITHUB_REPOSITORY", "GITHUB_PR_NUMBER", "GITHUB_BASE_REF", "GITHUB_HEAD_REF"]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            missing_vars_str = ", ".join(missing_vars)
            raise ValueError(f"The following environment variables are missing or empty: {missing_vars_str}")
