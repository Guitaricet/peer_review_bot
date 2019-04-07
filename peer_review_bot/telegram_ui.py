import os
import sys
import logging
import traceback
from datetime import datetime

import telebot
from peer_review_bot import config, utils, datautils
from peer_review_bot.dbutils import TasksDB
from peer_review_bot.data_structures import User, Document, DialogState


# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
telebot.logger.setLevel(logging.INFO)
logger = telebot.logger

fileHandler = logging.FileHandler('telegram.log')
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
logger.addHandler(consoleHandler)


# -- bot starts here
bot = telebot.TeleBot(config.token)
if config.use_proxy:
    telebot.apihelper.proxy = {'https': config.proxy}

# we use telegram id as state tracker idenficicator
# this is a good idea


@bot.message_handler(commands=['start'])
def register(message):
    bot.send_message(message.chat.id, 'Hi!')
    # TODO: move db logic to db
    try:
        TasksDB.get_user_info(User.from_telegram(message.from_user))
        bot.send_message(message.chat.id, config.registered_error)
    except RuntimeError:
        # TODO: this is bad idea, use if (?)
        bot.send_message(message.chat.id, config.registration_message)
        datautils.set_user_state(message.from_user.id, DialogState('registration'))
        return
    bot.send_message(message.chat.id, config.help_message)


@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, config.help_message)


@bot.message_handler(commands=['info'])
def info(message):
    """Debug message"""
    user_tgid = message.from_user.id
    state = datautils.get_user_state(user_tgid)
    info = {'state': state}

    try:
        user_info = TasksDB.get_user_info(User.from_telegram(message.from_user))
    except RuntimeError as e:
        logger.error(f'Chat_id: {message.chat.id}, error: {e}')
        logger.error(traceback.format_exc())
        bot.send_message(message.chat.id, e)
        return
    if user_info is not None:
        info.update(user_info)
    bot.send_message(message.chat.id, repr(info))


@bot.message_handler(commands=['sudo'], func=lambda x: os.environ.get('PRB_STAGE') == 'test')
def sudo(message):
    _, tg_user_id, command_str = message.text.split(' ')
    message.from_user.id = int(tg_user_id)
    command = f'{command_str}(message)'
    exec(command)


@bot.message_handler(commands=['send_task'])
def send_task(message):
    """Set user state to sending_task with workshop, task"""
    if message.text == '/send_task':
        bot.send_message(message.chat.id, config.send_task_help_message, parse_mode='markdown')
        return

    res = utils.check_workshop_task_from(message, bot, logger)
    if res is None:
        return

    workshop, task = res
    deadline = config.deadlines.get(workshop)

    if deadline is None:
        bot.send_message(message.chat.id, 'No specified deadline for this workshop. Ask admin.')
        return

    has_sent_previous = TasksDB.check_task_order(User.from_telegram(message.from_user), workshop, task)
    if not has_sent_previous:
        bot.send_message(message.chat.id, config.order_error)
        return

    n_late = utils.late_days(deadline)
    if n_late is None:
        bot.send_message(message.chat.id, config.deadline_message.format(max_late=config.max_late))
        return

    datautils.set_user_state(message.from_user.id, DialogState('sending_task', workshop, task, n_late))
    answer = config.send_task_message.format(workshop=workshop, task=task)

    if n_late > 0:
        answer += '\n' + f'*{n_late} late days* will be used'
    bot.send_message(message.chat.id, answer, parse_mode='markdown')


@bot.message_handler(commands=['get_gradable'])
def get_gradable(message):
    try:
        gradable = TasksDB.get_gradable(
            User.from_telegram(message.from_user)
        )
    except (ValueError, RuntimeError) as e:
        bot.send_message(message.chat.id, e)
        bot.send_message(message.chat.id, 'Probably, you are not registered')
        return
    if not gradable:
        bot.send_message(message.chat.id, 'No gradable tasks for now')
        return

    repr_gradable = utils.format_gradable(gradable)
    bot.send_message(message.chat.id, repr_gradable)


@bot.message_handler(commands=['get_graders'])
def get_graders(message):
    try:
        graders = TasksDB.get_graders(
            User.from_telegram(message.from_user)
        )
    except (ValueError, RuntimeError) as e:
        bot.send_message(message.chat.id, e)
        bot.send_message(message.chat.id, 'Probably, you are not registered')
        return
    if not graders:
        bot.send_message(message.chat.id, 'No graders for your tasks')
        return

    repr_graders = utils.format_gradable(graders)
    bot.send_message(message.chat.id, repr_graders)


@bot.message_handler(commands=['get_task'])
def get_task(message):
    """Get a task to grade
    syntax: /get_task @username 1.4
    """
    user = User.from_telegram(message.from_user)

    # 1. parse the message
    # standard try-except-except for parsing handling
    try:
        graded_tg_username, workshop, task = utils.parse_get_task_message(message.text)
    except (ValueError, UnboundLocalError):
        logger.warning(f'Chat_id: {message.chat.id}, user: {message.from_user.username}'
                       f', #wrong_format: {message.text}')
        bot.send_message(message.chat.id, config.wrong_format_error)
        bot.send_message(message.chat.id, config.get_task_format_message, parse_mode='markdown')
        return
    except Exception:
        bot.send_message(message.chat.id, config.just_error)
        return

    # 2. check that user can get this task
    # 3. get this task
    graded = User(tg_username=graded_tg_username)
    try:
        file_id = TasksDB.get_task(user, graded, workshop, task)
    except RuntimeError as e:
        bot.send_message(message.chat.id, e)
        return
    except Exception as e:
        logger.error(f'Chat_id: {message.chat.id}, user: {message.from_user.username}'
                     f', error: {e}, traceback: {traceback.format_exc()}')
        bot.send_message(message.chat.id, config.just_error)
        return

    bot.send_document(message.chat.id, file_id)


@bot.message_handler(commands=['get_scores'])
def get_scores(message):
    """Get scores of all tasks for given user"""
    user = User.from_telegram(message.from_user)
    try:
        scores = TasksDB.get_scores(user)
    except Exception as e:
        logger.error(f'Chat_id: {message.chat.id}, user: {message.from_user.username}'
                     f', error: {e}, , traceback: {traceback.format_exc()}')
        bot.send_message(message.chat.id, config.just_error)
        return

    if not scores:
        bot.send_message(message.chat.id, 'No scores available for now')
        return

    repr_scores = utils.format_scores(scores)
    bot.send_message(message.chat.id, repr_scores)


@bot.message_handler(commands=['late_days'])
def get_late_days(message):
    """Return to user number of late days left"""
    user_info = TasksDB.get_user_info(User.from_telegram(message.from_user))
    n_days = user_info.get('late_days', config.default_late_days)
    if n_days is None:
        n_days = config.default_late_days
    bot.send_message(message.chat.id, f'You have *{n_days}* late days left.', parse_mode='markdown')


@bot.message_handler(commands=['grade'])
def grade(message):
    try:
        score_dict = utils.parse_grade_message(message.text)
    except (ValueError, UnboundLocalError):
        bot.send_message(message.chat.id, config.grade_format_message, parse_mode='markdown')
        return
    except Exception as e:
        logger.error(f'Chat_id: {message.chat.id}, user: {message.from_user.username}'
                     f', error: {e}')
        bot.send_message(message.chat.id, e)
        return

    # TODO: user should have initialization from db(?)
    # lazy init if the param is unavailable
    user = User.from_telegram(message.from_user)
    graded = User(tg_username=score_dict['tg_username'])
    try:
        TasksDB.add_score(user,
                          graded,
                          score_dict['workshop_number'],
                          score_dict['task_number'],
                          score_dict['score'])
    except (ValueError, RuntimeError) as e:
        bot.send_message(message.chat.id, repr(e))
        return
    except Exception as e:
        bot.send_message(message.chat.id, config.just_error)
        logger.error(f'Chat_id: {message.chat.id}, user: {message.from_user.username}'
                     f', error: {e}')
        bot.send_message(config.logto, e)
        return

    bot.send_message(message.chat.id, config.success_message)


@bot.message_handler(commands=['cancel'])
def cancel(message):
    datautils.set_user_state(message.from_user.id, DialogState(None))


@bot.message_handler(content_types=['text'])
def answer(message):
    # TODO: change ifs to lambda filters
    tg_user = message.from_user
    state = datautils.get_user_state(tg_user.id)

    if state.action == 'registration':
        user = User.from_telegram(tg_user)
        if user.tg_username is None:
            bot.send_message(
                message.chat.id,
                'Please, create a telegram username and call /start again')
            datautils.set_user_state(user.tg_id, DialogState(None))
            return

        user.username = message.text

        TasksDB.register_new_user(user)
        datautils.set_user_state(user.tg_id, DialogState(None))
        bot.send_message(message.chat.id, config.registered_message)
        return


@bot.message_handler(content_types=['document'])
def recieve_task(message):
    # extract workshop number and task number
    state = datautils.get_user_state(message.from_user.id)
    if state.action == 'sending_task':
        workshop, task = state.workshop, state.task
    else:
        bot.send_message(message.chat.id, config.wrong_format_error)
        bot.send_message(message.chat.id, config.send_task_help_message)
        return

    # write to db
    document = Document.from_telegram(message.document)
    user = User.from_telegram(message.from_user)
    try:
        res = TasksDB.add_task(user, workshop, task, document)
    except RuntimeError as e:
        logger.error(f'Chat_id: {message.chat.id}, user: {message.from_user.username}'
                     f', #runtime_error: {e}')
        bot.send_message(message.chat.id, str(e))
        return

    if not res.acknowledged:
        bot.send_message(message.chat.id, config.just_error)
        return

    if state.n_late > 0:
        try:
            days_left = TasksDB.use_late_days(user, state.n_late)
        except ValueError as e:
            bot.send_message(message.chat.id, e)
            return
        bot.send_message(message.chat.id,
                         f'You have spent *{state.n_late}* late days. *{days_left}* left',
                         parse_mode='markdown')

    bot.send_message(message.chat.id, config.task_accepted.format(workshop=workshop, task=task))
    datautils.set_user_state(message.from_user.id, DialogState(None))

    # add and find scorers
    graded = TasksDB.add_graders(user, workshop, task)
    if graded:
        bot.send_message(message.chat.id, config.list_of_people_to_grade_message.format(graded=graded))
        return
    bot.send_message(message.chat.id, 'No users to grade for now. Type /get_gradable later')


def init_telegram_ui():
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f'Bot has crashed, error: {e}')
        logger.error(traceback.format_exc())

        print(e)
        traceback.print_exc()
        bot.send_message(config.logto, traceback.format_exc())
        raise e
