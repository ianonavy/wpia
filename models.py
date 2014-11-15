import datetime

from flask import g
from flask.ext.login import UserMixin

from db import db
from utils import ldap_fetch
import config


class SaveMixin(object):

    def save(self):
        db.session.add(self)
        db.session.commit()


class DisplayAtMixin(object):

    display_at = db.Column(db.DateTime, nullable=False)

    def is_visible_to_students(self):
        return self.display_at <= datetime.datetime.now()




student_course_maps = db.Table(
    'student_course_maps',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'))
)

instructor_course_maps = db.Table(
    'instructor_course_maps',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'))
)


class User(db.Model, SaveMixin, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    submissions = db.relationship('Submission', backref='user')
    courses = db.relationship(
        'Course', secondary=student_course_maps,
        backref=db.backref('students', lazy='dynamic'))
    taught_courses = db.relationship(
        'Course', secondary=instructor_course_maps,
        backref=db.backref('instructors', lazy='dynamic'))

    def __init__(self, uid=None, name=None, passwd=None):
        ldapres = ldap_fetch(uid=uid, name=name, passwd=passwd)
        if ldapres is not None:
            self.name = ldapres['name']
            self.username = ldapres['uid']
            self.email = ldapres['mail']
            self.id = ldapres['id']

    def get_upcoming_assignments(self):
        assignments = []
        for course in self.courses:
            assignments += course.get_upcoming_assignments()
        return assignments

    def has_permission_to_read(self, setname, filename):
        # TODO: dry this up
        ret = True
        if setname == 'submissions':
            subs = Submission.query.filter(
                Submission.filename == filename).all()
            for sub in subs:
                course = sub.assignment.course
                is_instructor = self.is_instructor_for(course)
                ret = ret and self.is_part_of(course)
                ret = ret and (sub.user_id == self.id or is_instructor)
        elif setname == 'presentations':
            presentations = Presentation.query.filter(
                Presentation.filename == filename).all()
            for p in presentations:
                course = p.course
                ret = ret and self.is_part_of(course)
                if self.is_taking(course):
                    ret = ret and p.is_visible_to_students()
        elif setname == 'syllabi':
            courses = Course.query.filter(
                Course.syllabus_filename == filename).all()
            for course in courses:
                ret = ret and self.is_part_of(course)
        elif setname == 'assignments':
            assignments = Assignment.query.filter(
                Assignment.description_filename == filename).all()
            for a in assignments:
                course = a.course
                ret = ret and self.is_part_of(course)
        else:
            ret = False
        return ret


    def is_part_of(self, course):
        return self.is_instructor_for(course) or self.is_taking(course)

    def is_taking(self, course):
        return course in self.courses

    def is_instructor_for(self, course):
        return course in self.taught_courses

    def is_admin(self):
        return self.username in config.ADMIN_USERNAMES

    def __repr__(self):
        return '<User %r>' % self.username


class Course(db.Model, SaveMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    syllabus_filename = db.Column(db.String)
    assignments = db.relationship('Assignment', backref='course')
    presentations = db.relationship('Presentation', backref='course')

    def get_upcoming_assignments(self):
        return self.get_visible_assignments()

    def add_assignment(self, assignment):
        assignment.course = self

    def add_presentation(self, presentation):
        presentation.course = self

    def add_students(self, users):
        for user in users:
            self.students.append(user)
        self.save()

    def get_visible_presentations(self):
        return Presentation.query.filter(
            Presentation.course_id == self.id,
            Presentation.display_at <= datetime.datetime.now()).all()

    def get_visible_assignments(self):
        return Assignment.query.filter(
            Assignment.course_id == self.id,
            Assignment.display_at <= datetime.datetime.now()).all()

    def remove_students(self, users):
        for user in users:
            self.students.remove(user)
        self.save()

    def add_instructors(self, users):
        for user in users:
            self.instructors.append(user)
        self.save()

    def remove_instructors(self, users):
        for user in users:
            self.instructors.remove(user)
        self.save()


class Assignment(db.Model, SaveMixin, DisplayAtMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    due_at = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(1000))
    description_filename = db.Column(db.String)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    submissions = db.relationship('Submission', backref='assignment')

    def has_submission_from_user(self, user):
        return len(self.get_submissions_from_user(user)) > 0

    def get_submissions_from_user(self, user):
        # TODO: make SQL more efficient with session.query
        return filter(lambda sub: sub.user_id == user.id, self.submissions)

    def my_submissions(self):
        return self.get_submissions_from_user(g.user)


class Presentation(db.Model, SaveMixin, DisplayAtMixin):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    name = db.Column(db.String(120), nullable=False)
    filename = db.Column(db.String, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)


class Submission(db.Model, SaveMixin):
    id = db.Column(db.Integer, primary_key=True)
    submitted_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    is_official = db.Column(db.Boolean, nullable=False)
    filename = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)

    def is_late(self):
        return self.submitted_at > self.assignment.due_at

    def officialize(self):
        other_submissions = self.assignment.my_submissions()
        for other in other_submissions:
            other.is_official = False
        self.is_official = True
        self.save()

    def __repr__(self):
        return '%r' % self.filename
