from flask import current_app, request
from flask_jwt_extended import jwt_required

from core.scheduler import InvalidTriggerArgs
from server.returncodes import *
from server.security import roles_accepted_for_resources


def get_scheduler_status():
    from server.context import running_context

    @jwt_required
    @roles_accepted_for_resources('scheduler')
    def __func():
        return {"status": running_context.controller.scheduler.scheduler.state}, SUCCESS
    return __func()


def update_scheduler_status(status):
    from server.context import running_context

    @jwt_required
    @roles_accepted_for_resources('scheduler')
    def __func():
        updated_status = running_context.controller.scheduler.scheduler.state
        if status == "start":
            updated_status = running_context.controller.scheduler.start()
            current_app.logger.info('Scheduler started. Status {0}'.format(updated_status))
        elif status == "stop":
            updated_status = running_context.controller.scheduler.stop()
            current_app.logger.info('Scheduler stopped. Status {0}'.format(updated_status))
        elif status == "pause":
            updated_status = running_context.controller.scheduler.pause()
            current_app.logger.info('Scheduler paused. Status {0}'.format(updated_status))
        elif status == "resume":
            updated_status = running_context.controller.scheduler.resume()
            current_app.logger.info('Scheduler resumed. Status {0}'.format(updated_status))
        return {"status": updated_status}, SUCCESS

    return __func()


def read_all_scheduled_tasks():
    from server.context import running_context

    @jwt_required
    @roles_accepted_for_resources('scheduler')
    def __func():
        return [task.as_json() for task in running_context.ScheduledTask.query.all()], SUCCESS
    return __func()


def create_scheduled_task():
    from server.context import running_context

    @jwt_required
    @roles_accepted_for_resources('scheduler')
    def __func():
        data = request.get_json()
        task = running_context.ScheduledTask.query.filter_by(name=data['name']).first()
        if task is None:
            try:
                task = running_context.ScheduledTask(**data)
            except InvalidTriggerArgs:
                return {'error': 'invalid scheduler arguments'}, 400
            else:
                running_context.db.session.add(task)
                running_context.db.session.commit()
                return task.as_json(), OBJECT_CREATED
        else:
            return {'error': 'Could not create object. Object with given name already exists'}, OBJECT_EXISTS_ERROR
    return __func()


def read_scheduled_task(scheduled_task_id):
    from server.context import running_context

    @jwt_required
    @roles_accepted_for_resources('scheduler')
    def __func():
        task = running_context.ScheduledTask.query.filter_by(id=scheduled_task_id).first()
        if task is not None:
            return task.as_json(), SUCCESS
        else:
            return {'error': 'Could not read object. Object does not exist'}, OBJECT_DNE_ERROR

    return __func()


def update_scheduled_task():
    from server.context import running_context

    @jwt_required
    @roles_accepted_for_resources('scheduler')
    def __func():
        data = request.get_json()
        task = running_context.ScheduledTask.query.filter_by(id=data['id']).first()
        if task is not None:
            if 'name' in data:
                same_name = running_context.ScheduledTask.query.filter_by(name=data['name']).first()
                if same_name is not None and same_name.id != data['id']:
                    return {'error': 'Task with that name already exists.'}, OBJECT_EXISTS_ERROR
            try:
                task.update(data)
            except InvalidTriggerArgs:
                return {'error': 'invalid scheduler arguments'}, 400
            else:
                running_context.db.session.commit()
                return task.as_json(), SUCCESS
        else:
            return {'error': 'Could not update object. Object does not exist.'}, OBJECT_DNE_ERROR

    return __func()


def delete_scheduled_task(scheduled_task_id):
    from server.context import running_context

    @jwt_required
    @roles_accepted_for_resources('scheduler')
    def __func():
        task = running_context.ScheduledTask.query.filter_by(id=scheduled_task_id).first()
        if task is not None:
            running_context.db.session.delete(task)
            running_context.db.session.commit()
            return {}, SUCCESS
        else:
            return {'error': 'Could not delete object. Object does not exist'}, OBJECT_DNE_ERROR

    return __func()


def control_scheduled_task(scheduled_task_id, action):
    from server.context import running_context

    @jwt_required
    @roles_accepted_for_resources('scheduler')
    def __func():
        task = running_context.ScheduledTask.query.filter_by(id=scheduled_task_id).first()
        if task is not None:
            if action == 'start':
                task.start()
                running_context.db.session.commit()
                return {}, SUCCESS
            elif action == 'stop':
                task.stop()
                running_context.db.session.commit()
                return {}, SUCCESS
        else:
            return {'error': 'Could not read object. Object does not exist'}, OBJECT_DNE_ERROR

    return __func()
