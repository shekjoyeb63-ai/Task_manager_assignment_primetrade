from Tables import Task, sessionLocal
from flask import g

def get_db():
    if "db" not in g:
        g.db = sessionLocal()
    return g.db

class TaskManager:
    def __init__(self) -> None:
        pass

    def create_task(self, title, description, priority, due_date, owner_id):
        try:
            db = get_db()
            new_task = Task(
                title=title,
                description=description,
                status="pending",
                priority=priority,
                due_date=due_date,
                owner_id=owner_id
            )
            db.add(new_task)
            db.commit()
            return {"message": "Task created successfully", "task": new_task.to_dict()}, 201
        except Exception as e:
            return {"message": f"Error: {str(e)}"}, 500

    def get_all_tasks(self):
        try:
            db = get_db()
            tasks = db.query(Task).all()
            return [t.to_dict() for t in tasks], 200
        except Exception as e:
            return {"message": f"Error: {str(e)}"}, 500

    def get_my_tasks(self, owner_id):
        try:
            db = get_db()
            tasks = db.query(Task).filter(Task.owner_id == owner_id).all()
            return [t.to_dict() for t in tasks], 200
        except Exception as e:
            return {"message": f"Error: {str(e)}"}, 500

    def get_task_by_id(self, task_id):
        try:
            db = get_db()
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                return task.to_dict(), 200
            return {"message": "Task not found"}, 404
        except Exception as e:
            return {"message": f"Error: {str(e)}"}, 500

    def update_task(self, task_id, owner_id, is_admin, title, description, status, priority, due_date):
        try:
            db = get_db()
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return {"message": "Task not found"}, 404
            if not is_admin and task.owner_id != owner_id:
                return {"message": "Unauthorized"}, 401
            if title is not None:
                task.title = title
            if description is not None:
                task.description = description
            if status is not None:
                task.status = status
            if priority is not None:
                task.priority = priority
            if due_date is not None:
                task.due_date = due_date
            db.commit()
            return {"message": "Task updated successfully", "task": task.to_dict()}, 200
        except Exception as e:
            return {"message": f"Error: {str(e)}"}, 500

    def delete_task(self, task_id, owner_id, is_admin):
        try:
            db = get_db()
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return {"message": "Task not found"}, 404
            if not is_admin and task.owner_id != owner_id:
                return {"message": "Unauthorized"}, 401
            db.delete(task)
            db.commit()
            return {"message": "Task deleted successfully"}, 200
        except Exception as e:
            return {"message": f"Error: {str(e)}"}, 500

    def filter_tasks(self, owner_id, is_admin, status, priority):
        try:
            db = get_db()
            query = db.query(Task)
            if not is_admin:
                query = query.filter(Task.owner_id == owner_id)
            if status:
                query = query.filter(Task.status == status)
            if priority:
                query = query.filter(Task.priority == priority)
            tasks = query.all()
            return [t.to_dict() for t in tasks], 200
        except Exception as e:
            return {"message": f"Error: {str(e)}"}, 500
