import shelve
from peer_review_bot.config import shelve_name
from peer_review_bot.data_structures import DialogState


def set_user_state(user, state):
    with shelve.open(shelve_name) as storage:
        storage[str(user)] = state
    return True


def get_user_state(user):
    with shelve.open(shelve_name) as storage:
        return storage.get(str(user), DialogState(None))
