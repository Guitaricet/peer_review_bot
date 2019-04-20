import os
from datetime import datetime

# Telegram-related
use_proxy = True
token = os.environ['PRB_TOKEN']
proxy = os.environ.get('PRB_PROXY')

# Data-related
shelve_name = 'user_states.shelve'
dbhost = 'mongo'

# Logic-related:
n_graders = 2
logto = 132238726
max_late = 3
default_late_days = 12

# Messages etc.
registration_message = "Please, enter your nickname (the one you use for this class' quizzes)"
registered_message = 'You have been successfuly registered. Type /help to see all commands.'
help_message = ('List of commands:\n'
                '/start - registration in the bot (regiser again, if you did it before 3.3.19,\n'
                '/send_task - send a file of a completed task,\n'
                '/get_gradable - get a list of gradable pairs user-task,\n'
                '/get_task - get a task of a user to grade it,\n'
                '/grade - send a scaled to [0, 10] score of the task.')
send_task_message = ("You want to send task *{task}* of workshop *{workshop}*. "
                     "Just drop one file here (or a .zip, if there are multiple files). To cancel, type /cancel")
send_task_help_message = 'Use the following syntax to send the task: `/send_task 1.4` where 1.4 is the task number'
task_sent_message = ("Task {task} of the workshop {workshop} has been sent")
not_scored_yet_message = 'Not scored yet, {n} more student(s) should score it'
score_not_available_message = 'Score others work first ({n} more)'

list_of_people_to_grade_message = 'Check solutions of the following people: {graded}'
grade_format_message = ('To grade task use the following format: `/grade @username 1.1 10` where 1.1 '
                        'is workshop\_number.task\_number and 10 is your grade on the scale \[0, 10]')
get_task_format_message = 'To get the task use the following syntax: `/get_task @username 1.1` where 1.1 is task number'
deadline_message = 'This task cannot be sent anymore. Deadline was more than {max_late} days ago.'

task_accepted = 'Solution of the task {workshop}.{task} is uploaded'
success_message = 'Success!'

wrong_format_error = 'Wrong format.'
registered_error = ('You have already registered and have a username. '
                    'Type /help for the list of commands')
order_error = 'You cannot send this task, because you have not sent the prevous one. Tasks should be sent in order'
not_implemented_error = 'NotImplementedError'
just_error = 'An error has occured. Write to admins.'

# Deadlines
# yes, this may be not the best idea. But let's try

deadlines = {
    1: datetime(2019, 3, 8),
    2: datetime(2019, 3, 23),
    3: datetime(2019, 4, 18),
    4: datetime(2019, 4, 27),
}
