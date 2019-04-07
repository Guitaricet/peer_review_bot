from random import sample
from dataclasses import asdict
from pymongo import MongoClient

from peer_review_bot import config
from peer_review_bot.data_structures import Task


class TasksDB:
    _client = MongoClient(config.dbhost)
    _db = _client.peer_review_db

    @classmethod
    def register_new_user(cls, user):
        res = cls._db.user.insert_one(asdict(user))
        return res

    @classmethod
    def get_user_info(cls, user):
        if user.tg_id is not None:
            info = cls._db.user.find_one({'tg_id': user.tg_id})
        elif user.tg_username is not None:
            info = cls._db.user.find_one({'tg_username': user.tg_username})
        elif user.username is not None:
            info = cls._db.user.find_one({'username': user.username})
        else:
            raise ValueError('User without id or tg_id')

        if info is None:
            raise RuntimeError(f'No such user in db. User: {user}')
        
        cls.maybe_update_user_info(user, info)

        return info

    @classmethod
    def maybe_update_user_info(cls, user, info):
        if info['tg_username'] == user.tg_username:
            return

        cls._db.user.update_one(
            {'tg_id': user.tg_id},
            {'$set': {'tg_username': user.tg_username}}
        )

    @classmethod
    def use_late_days(cls, user, n_late):
        user = cls.get_user_info(user)
        late_days = user.get('late_days', config.default_late_days) or config.default_late_days
        assert late_days is not None
        assert n_late is not None
        if late_days < n_late:
            raise ValueError(f'Not enough late days. {late_days} available')

        cls._db.user.update_one({'_id': user.get('_id')},
                                {'$set': {'late_days': late_days - n_late}})
        return late_days - n_late

    @classmethod
    def add_task(cls, user, workshop_number, task_number, document, force=False):
        """Add task solution document to db
        - user: User object
        - workshop_number: int
        - task_number: int
        - document: Document object
        - force: bool, load even if exists
        """
        user_info = cls.get_user_info(user)
        user_id = user_info.get('_id')
        if user_id is None:
            raise RuntimeError(f'No user {repr(user)}')

        res = cls._db.task.find_one({'user_id': user_id,
                                     'workshop_number': workshop_number,
                                     'task_number': task_number})

        if res is not None and not force:
            raise RuntimeError('Error. The task has already been uploaded')

        task = Task(user_id=user_id,
                    workshop_number=workshop_number,
                    task_number=task_number,
                    file_info=document)

        res = cls._db.task.insert_one(asdict(task))
        return res

    @classmethod
    def add_graders(cls, user, workshop_number, task_number):
        # TODO: make more data-safe, without a lot of graders
        user_info = cls.get_user_info(user)
        user_id = user_info.get('_id')
        if user_id is None:
            raise RuntimeError(f'#add_graders No user {repr(user)}')

        # get upto 3 people who have less than 3 graders
        to_grade = cls._db.task.find({'user_id': {'$ne': user_id},
                                      'workshop_number': workshop_number,
                                      'task_number': task_number,
                                      '$where': f'this.graders.length < {config.n_graders}'})
        to_grade = list(to_grade)
        to_grade = sample(to_grade, min(config.n_graders, len(to_grade)))

        gradable = []
        for task in to_grade:
            gradable.append(task.get('user_id'))
            cls._db.task.update_one({'_id': task.get('_id')},
                                    {'$push': {'graders': user_id}})

        # assign the scoring to 3 people, who have less than 3 graders
        to_be_graded_by = cls._db.task.find({'user_id': {'$ne': user_id},
                                             'workshop_number': workshop_number,
                                             'task_number': task_number,
                                             '$where': f'this.graders.length + this.scores.length < {config.n_graders}'})

        # sample upto 3 people to grade
        to_be_graded_by = list(to_be_graded_by)
        to_be_graded_by = sample(to_be_graded_by, min(config.n_graders, len(to_be_graded_by)))

        graders = [task['user_id'] for task in to_be_graded_by]
        cls._db.task.update_one({'user_id': user_id, 'workshop_number': workshop_number, 'task_number': task_number},
                                {'$push': {'graders': {'$each': graders}}})

        # return list of peple the user need to score
        gradable_info = cls._db.user.find({'_id': {'$in': gradable}})
        gradable_tg_names = [u['tg_username'] for u in gradable_info]
        return gradable_tg_names

    @classmethod
    def add_score(cls, grader, graded, workshop_number, task_number, score):
        # TODO: refactor, guarantee some field
        grader_info = cls.get_user_info(grader)
        graded_info = cls.get_user_info(graded)
        if graded is None:
            raise ValueError('Wrong telegram username. User not found.')

        task = cls._db.task.find_one({'user_id': graded_info.get('_id'),
                                      'workshop_number': workshop_number,
                                      'task_number': task_number})

        if grader_info.get('_id') not in task['graders']:
            raise RuntimeError('Error. You should not grade this task')

        res = cls._db.task.update_one({'_id': task.get('_id')},
                                      {'$push': {'scores': score}})
        cls._db.task.update_one({'_id': task.get('_id')},
                                {'$pull': {'graders': grader_info.get('_id')}})
        cls._db.user.update_one({'_id': grader_info.get('_id')},
                                {'$push': {
                                    'scored_tasks': {
                                        'workshop_number': workshop_number,
                                        'task_number': task_number,
                                        'score': score,
                                        'user': graded_info.get('_id')}}})
        return res

    @classmethod
    def get_scores(cls, user):
        user_info = cls.get_user_info(user)
        tasks = cls._db.task.find({'user_id': user_info.get('_id')})

        res = []
        for task in tasks:
            scores = task['scores']
            if not scores:
                continue

            n_scores = len(scores)
            score = round(sum(scores) / n_scores, 1)
            if n_scores < 2:
                score = config.not_scored_yet_message.format(n=config.n_graders - n_scores)

            res.append({
                'workshop_number': task['workshop_number'],
                'task_number': task['task_number'],
                'score': score
            })
        return res

    @classmethod
    def get_gradable(cls, user):
        """
        returns: list(dict)

        [{'workshop_number': int, 'task_number': int, 'tg_username': str},]
        """
        user_info = cls.get_user_info(user)
        tasks = cls._db.task.find({'graders': user_info.get('_id')})

        res = []
        for task in tasks:
            tg_username = cls._db.user.find_one({'_id': task['user_id']})['tg_username']
            res.append({'workshop_number': task['workshop_number'],
                        'task_number': task['task_number'],
                        'tg_username': tg_username})
        return res

    @classmethod
    def get_graders(cls, user):
        """
        returns: list(dict)

        [{'workshop_number': int, 'task_number': int, 'tg_username': str},]
        """
        user_info = cls.get_user_info(user)

        tasks = cls._db.task.find({'user_id': user_info.get('_id'), 'graders.0': {'$exists': 1}})
        res = []
        for task in tasks:
            graders = task['graders']
            for grader in graders:
                tg_username = cls._db.user.find_one({'_id': grader})['tg_username']
                res.append({'workshop_number': task['workshop_number'],
                            'task_number': task['task_number'],
                            'tg_username': tg_username})
        return res

    @classmethod
    def check_task_order(cls, user, workshop_number, task_number):
        """Check that user has sent the previous task"""
        if task_number == 1:
            return True

        user_info = cls.get_user_info(user)

        res = cls._db.task.find_one({'user_id': user_info.get('_id'),
                                     'workshop_number': workshop_number,
                                     'task_number': task_number - 1})
        return res is not None

    @classmethod
    def get_task(cls, grader, graded, workshop_number, task_number):
        """Get a file for scoring
        - grader: User object
        - graded: User objec
        - workshop_number: int
        - task_number: int
        """
        # TODO: incapsulate this function
        grader_info = cls.get_user_info(grader)
        graded_info = cls.get_user_info(graded)
        if graded is None:
            raise ValueError('Wrong telegram username. User not found.')

        task = cls._db.task.find_one({'user_id': graded_info.get('_id'),
                                      'workshop_number': workshop_number,
                                      'task_number': task_number})

        if grader_info.get('_id') not in task['graders']:
            raise RuntimeError('Error. You should not grade this task')

        try:
            file_id = task['file_info']['file_id']
        except Exception:
            raise RuntimeError('Database error. Ask admins.')

        return file_id
