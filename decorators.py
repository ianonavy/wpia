from flask import g, redirect, url_for
from functools import wraps

from models import Course, Assignment, Submission, Presentation


def get_current_course(kwargs):
    course = None
    if 'course_id' in kwargs:
        course = Course.query.get(kwargs.get('course_id'))
    elif 'assignment_id' in kwargs:
        course = Assignment.query.get(kwargs.get('assignment_id')).course
    elif 'submission_id' in kwargs:
        course = Submission.query.get(kwargs.get('submission_id')).assignment.course
    elif 'presentation_id' in kwargs:
        course = Presentation.query.get(kwargs.get('presentation_id')).course
    return course



def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if g.user.is_admin():
            return f(*args, **kwargs)
        else:
            return redirect(url_for('home'))
    return wrapper


def instructor_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        course = get_current_course(kwargs)
        if g.user.is_instructor_for(course):
            return f(*args, **kwargs)
        else:
            return redirect(url_for('home'))
    return wrapper


def course_membership_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        course = get_current_course(kwargs)
        if g.user.is_part_of(course):
            return f(*args, **kwargs)
        else:
            return redirect(url_for('home'))
    return wrapper
