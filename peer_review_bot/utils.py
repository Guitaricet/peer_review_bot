from datetime import datetime
from collections import defaultdict
from peer_review_bot import config


def parse_task_number(message_text):
    """3.4 --> 3, 4"""
    workshop, task = message_text.strip('\n').strip(' ').split('.')
    workshop, task = int(workshop), int(task)
    return workshop, task


def parse_grade_message(message_text):
    """/grade_task @username 1.4 10"""
    _, username, task_str, score = message_text.strip('\n').strip(' ').split(' ')
    username = username.strip('@')
    workshop, task = parse_task_number(task_str)
    score = int(score)
    if not (0 <= score <= 10):
        raise ValueError('Score is not an integer between 0 and 10')
    return {'tg_username': username, 'workshop_number': workshop, 'task_number': task, 'score': score}


def parse_send_task(message_text):
    workshop, task = message_text.strip('\n').strip(' ').split(' ')[1].split('.')
    workshop, task = int(workshop), int(task)
    return workshop, task


def parse_get_task_message(message_text):
    """/get_task @username 1.4"""
    _, username, task_str = message_text.strip('\n').strip(' ').split(' ')
    username = username.strip('@')
    workshop, task = parse_task_number(task_str)
    return username, workshop, task


def parse_send_task_message(message_text):
    """/send_task 1.4 -> workshop, task"""
    _, task_str = message_text.strip('\n').strip(' ').split(' ')
    workshop, task = parse_task_number(task_str)
    return workshop, task


def late_days(deadline):
    delta = (datetime.now() - deadline).days
    if delta <= 0:
        return 0
    if 0 < delta <= config.max_late:
        return delta
    return None


def format_gradable(gradable):
    """
    [{'workshop_number': int, 'task_number': int, 'tg_username': str},]

    workshop 1:
        task 1: @tg_username1, @tg_username2, ...
        task 2: @tg_username3, ...
    workshop 2:
        task 1: @tg_username4
    ...
    """
    workshops = defaultdict(lambda: defaultdict(list))
    for line in gradable:
        w, t = line['workshop_number'], line['task_number']
        tg_username = line['tg_username']
        if tg_username is None:
            tg_username = '???'
        else:
            tg_username = '@' + tg_username
        workshops[w][t].append(tg_username)

    res = ''
    workshop_numbers = sorted(list(workshops.keys()))
    for w in workshop_numbers:
        res += f'Workshop {w}:\n'
        tasks = workshops[w]

        task_numbers = sorted(list(tasks.keys()))
        for t in task_numbers:
            graders_str = ', '.join(tasks[t])
            res += f'\ttask {t}: {graders_str}\n'

        res += '\n'
    return res


def format_scores(scores):
    """
    [{'workshop_number': int, 'task_number': int, 'score': str or float},]

    workshop 1:
        task 1: 9.5
        task 2: not scored yet, need 2 more
    workshop 2:
        task 1: 8
    ...
    """
    workshops = defaultdict(dict)
    for line in scores:
        w, t = line['workshop_number'], line['task_number']
        workshops[w][t] = line['score']

    res = ''
    workshop_numbers = sorted(list(workshops.keys()))
    for w in workshop_numbers:
        res += f'Workshop {w}:\n'
        tasks = workshops[w]

        task_numbers = sorted(list(tasks.keys()))
        for t in task_numbers:
            res += f'\ttask {t}: {tasks[t]}\n'

        res += '\n'
    return res


def check_workshop_task_from(message, bot, logger=None):
    try:
        workshop, task = parse_send_task_message(message.text)
    except (ValueError, UnboundLocalError):
        if logger:
            logger.warning(f'Chat_id: {message.chat.id}, user: {message.from_user.username}'
                           f', #wrong_format: {message.text}')
        bot.send_message(message.chat.id, config.wrong_format_error)
        return
    except Exception as e:
        if logger:
            logger.error(f'Chat_id: {message.chat.id}, user: {message.from_user.username}'
                         f', error: {e}')
        bot.send_message(message.chat.id, e)
        return

    if workshop > len(config.deadlines):
        bot.send_message(message.chat.id, config.wrong_format_error)
        bot.send_message(message.chat.id, 'this workshop has not started yet')
        return

    # TODO: hardcode
    if task > 7:
        bot.send_message(message.chat.id, config.wrong_format_error)
        bot.send_message(message.chat.id, 'are you sure this task exists? Contact admins')
        return

    return workshop, task


if __name__ == "__main__":
    res = parse_task_number(' 3.4 ')
    assert 3, 4 == res

    res = parse_grade_message('/grade_task @username 1.4 10')
    assert res['tg_username'] == 'username', res
    assert res['workshop_number'] == 1, res
    assert res['task_number'] == 4, res
    assert res['score'] == 10, res

    print('Format scores result:')
    print(format_scores([
        {'workshop_number': 1, 'task_number': 1, 'score': 7.5},
        {'workshop_number': 1, 'task_number': 2, 'score': 'No'},
        {'workshop_number': 2, 'task_number': 3, 'score': 9}
    ]))

    print('Format gradable result:')
    print(format_gradable([
        {'workshop_number': 1, 'task_number': 1, 'tg_username': 'user1'},
        {'workshop_number': 1, 'task_number': 1, 'tg_username': 'No'},
        {'workshop_number': 2, 'task_number': 3, 'tg_username': 'User3'}
    ]))
