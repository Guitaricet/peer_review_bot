from dataclasses import dataclass


@dataclass
class Document:
    file_id: str
    file_name: str
    file_size: int
    mime_type: str

    @classmethod
    def from_telegram(cls, document):
        return cls(document.file_id,
                   document.file_name,
                   document.file_size,
                   document.mime_type)


@dataclass
class User:
    """User info"""
    # id: int = None  # id form mongo
    tg_id: int = None
    tg_username: str = None
    username: str = None
    first_name: str = None
    last_name: str = None
    late_days: int = None
    scored_tasks: list = None

    @classmethod
    def from_telegram(cls, user):
        return cls(user.id,
                   user.username,
                   None,
                   user.first_name,
                   user.last_name)

    @classmethod
    def from_dict(cls, dict_):
        return cls(dict_['tg_id'],
                   dict_['tg_username'],
                   dict_['username'],
                   dict_['first_name'],
                   dict_['last_name'])


@dataclass
class Task:
    """Pair user-task"""
    user_id: int
    workshop_number: int
    task_number: int
    file_info: Document
    scores: list = tuple()
    graders: list = tuple()


@dataclass
class DialogState:
    action: str
    workshop: int = None
    task: int = None
    n_late: int = None
