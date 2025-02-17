import os
import json
import requests
from log import Log
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)

class EnvVars:
    def __init__(self):
        self.event_name = os.getenv('GITHUB_EVENT_NAME')
        self.event_path = os.getenv('GITHUB_EVENT_PATH')
        self.chat_gpt_token = os.getenv('CHATGPT_KEY')
        self.chat_gpt_model = os.getenv('CHATGPT_MODEL')

        if not self.event_path:
            raise ValueError("GITHUB_EVENT_PATH is not set. Make sure this variable is defined.")

        with open(self.event_path, 'r') as f:
            self.event_payload = json.load(f)

        if self.event_name == 'pull_request':
            self.handle_pull_request_event()
        elif self.event_name == 'push':
            self.handle_push_event()
        else:
            raise ValueError(f"Unsupported event type: {self.event_name}")

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

    def handle_pull_request_event(self):
        pr = self.event_payload['pull_request']
        self.owner = pr['base']['repo']['owner']['login']
        self.repo = pr['base']['repo']['name']
        self.token = os.getenv('GITHUB_TOKEN')
        self.pull_number = str(pr['number'])

        if self.event_payload['action'] in ['opened', 'reopened']:
            self.base_ref = pr['base']['ref']
            self.head_ref = pr['head']['sha']
        else:
            self.base_ref = self.event_payload['before']
            self.head_ref = self.event_payload['after']

    def handle_push_event(self):
        self.owner = os.getenv('GITHUB_REPOSITORY_OWNER')
        self.repo = os.getenv('GITHUB_REPOSITORY').split('/')[-1]
        self.token = os.getenv('GITHUB_TOKEN')
        self.base_ref = self.event_payload['before']
        self.head_ref = self.event_payload['after']
        self.pull_number = None

    def check_vars(self):
        required_vars = ["CHATGPT_KEY", "CHATGPT_MODEL", "GITHUB_TOKEN"]

        if self.event_name == "pull_request":
            pass
        elif self.event_name == "push":
            if not self.owner or not self.repo:
                raise ValueError("REPO_OWNER and GITHUB_REPOSITORY must be set for push events.")

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            missing_vars_str = ", ".join(missing_vars)
            raise ValueError(f"The following environment variables are missing or empty: {missing_vars_str}")