from abc import ABC, abstractmethod
from typing import List

class RepositoryError(Exception):
    pass

class Repository(ABC):

    @abstractmethod
    def get_comments(self) -> List[dict]:
        pass

    @abstractmethod
    def post_comment_general(self, text: str) -> dict:
        pass

    @abstractmethod
    def get_latest_commit_id(self) -> str:
        pass

    @abstractmethod
    def get_pull_request(self) -> dict:
        pass

    @abstractmethod
    def update_pull_request(self, new_body: str) -> dict:
        pass