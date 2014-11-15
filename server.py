from flask import render_template, request, redirect, url_for, g, Blueprint, \
    abort, current_app, send_from_directory
from flask.ext.login import LoginManager, login_user, \
    login_required, logout_user, current_user
from dateutil.parser import parse

from models import User, Course, Assignment, Submission, Presentation
from uploads import submissions, presentations, syllabi, assignment_descs
from db import app, db
from forms import LoginForm
from decorators import admin_required, instructor_required, \
    course_membership_required


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'



@login_manager.user_loader
def load_user(userid):
    return User(uid=userid)


@app.before_request
def before_request():
    g.user = current_user
    if current_user.is_authenticated():
        user = User.query.get(current_user.id)
        if user:
            g.user = user




@app.route('/')
@login_required
def home():
    return render_template('index.html')


@app.route('/login', methods=["GET", "POST"])
def login():
    if current_user.is_authenticated():
        return redirect(url_for('home'))
    form = LoginForm(request.form)
    next_url = request.args.get('next', None)
    if request.method == 'POST' and form.validate():
        user = User.query.filter(User.username == form.username.data).first()
        if not user:
            user = User(name=form.username.data, passwd=form.password.data)
        if user.username and user.email:
            user.save()
            login_user(user)
            return redirect(next_url or url_for("home"))
    return render_template('login.html')


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))



@app.route('/courses')
@login_required
def list_courses():
    return render_template('course/list.html', courses=Course.query.all())


@app.route('/courses/new', methods=["GET", "POST"])
@login_required
@admin_required
def new_course():
    if request.method == "POST":
        name = request.form.get('name', None)
        syllabus = request.files.get('syllabus', None)
        if name and syllabus:
            filename = syllabi.save(syllabus)
            course = Course(name=name, syllabus_filename=filename)
            db.session.add(course)
            db.session.commit()
            return redirect(url_for('list_courses'))
    return render_template('course/new.html')


@app.route('/courses/<course_id>')
@login_required
def view_course(course_id):
    return render_template(
        'course/view.html',
        course=Course.query.get(course_id))


@app.route('/courses/<course_id>/edit', methods=["POST"])
@login_required
@instructor_required
def edit_course(course_id):
    course = Course.query.get(course_id)
    name = request.form.get('name', None)
    syllabus = request.files.get('syllabus', None)
    if name:
        course.name = name
    if syllabus:
        filename = syllabi.save(syllabus)
        course.syllabus_filename = filename
    course.save()
    return redirect(url_for('view_course', course_id=course_id))


@app.route('/courses/<course_id>/syllabus')
@login_required
@course_membership_required
def get_course_syllabus(course_id):
    course = Course.query.get(course_id)
    if not course.syllabus_filename:
        return redirect(url_for('view_course', course_id=course_id))
    return redirect(syllabi.url(course.syllabus_filename))


@app.route('/courses/<course_id>/add_students', methods=["POST"])
@login_required
@instructor_required
def course_add_students(course_id):
    course = Course.query.get(course_id)
    usernames = request.form.get('usernames', '').split('\n')
    users = User.query.filter(User.username.in_(usernames)).all()
    course.add_students(users)
    course.save()
    return redirect(url_for('view_course', course_id=course_id))


@app.route('/courses/<course_id>/remove_students', methods=["POST"])
@instructor_required
def course_remove_students(course_id):
    course = Course.query.get(course_id)
    usernames = request.form.get('usernames', '').split('\n')
    users = User.query.filter(User.username.in_(usernames)).all()
    course.remove_students(users)
    course.save()
    return redirect(url_for('view_course', course_id=course_id))


@app.route('/courses/<course_id>/add_instructors', methods=["POST"])
@login_required
@admin_required
def course_add_instructors(course_id):
    course = Course.query.get(course_id)
    usernames = request.form.get('usernames', '').split('\n')
    users = User.query.filter(User.username.in_(usernames)).all()
    course.add_instructors(users)
    course.save()
    return redirect(url_for('view_course', course_id=course_id))


@app.route('/courses/<course_id>/remove_instructors', methods=["POST"])
@login_required
@admin_required
def course_remove_instructors(course_id):
    course = Course.query.get(course_id)
    usernames = request.form.get('usernames', '').split('\n')
    users = User.query.filter(User.username.in_(usernames)).all()
    course.remove_instructors(users)
    course.save()
    return redirect(url_for('view_course', course_id=course_id))


@app.route('/courses/<course_id>/assignments')
@login_required
@course_membership_required
def list_assignments(course_id):
    course = Course.query.get(course_id)
    return render_template('assignment/list.html', course=course)


@app.route('/courses/<course_id>/assignments/new', methods=["GET", "POST"])
@login_required
@instructor_required
def new_assignment(course_id):
    course = Course.query.get(course_id)
    if request.method == "POST":
        name = request.form.get('name', None)
        description = request.form.get('description', None)
        due_at = request.form.get('due-at', None)
        display_at = request.form.get('display-at', None)
        file_ = request.files.get('file', None)
        if name and due_at and display_at:
            assignment = Assignment(name=name, description=description)
            assignment.due_at = parse(due_at)
            assignment.display_at = parse(display_at)
            if file_:
                filename = assignment_descs.save(file_)
                assignment.description_filename = filename
            course.add_assignment(assignment)
            assignment.save()
            return redirect(url_for('list_assignments', course_id=course_id))
    return render_template('assignment/new.html', course=course)


@app.route('/assignments/<assignment_id>')
@login_required
@course_membership_required
def view_assignment(assignment_id):
    assignment = Assignment.query.get(assignment_id)
    if assignment.description_filename:
        url = assignment_descs.url(assignment.description_filename)
    else:
        url = None
    return render_template(
        'assignment/view.html',
        submissions=submissions,
        course=assignment.course,
        assignment=assignment,
        url=url)


@app.route('/assignments/<assignment_id>/edit', methods=["GET", "POST"])
@login_required
@instructor_required
def edit_assignment(assignment_id):
    assignment = Assignment.query.get(assignment_id)
    if request.method == "POST":
        name = request.form.get('name', None)
        due_at = request.form.get('due-at', None)
        display_at = request.form.get('display-at', None)
        file_ = request.files.get('file', None)
        if name:
            assignment.name = name
        if due_at:
            assignment.due_at = parse(due_at)
        if display_at:
            assignment.display_at = parse(display_at)
        if file_:
            assignment.filename = assignments.save(file_)
        assignment.save()
        return redirect(
            url_for('list_assignments', course_id=assignment.course_id))
    return render_template('assignment/edit.html', assignment=assignment)


@app.route('/assignments/<assignment_id>/delete', methods=["GET"])
@login_required
@instructor_required
def delete_assignment(assignment_id):
    assignment = Assignment.query.get(assignment_id)
    db.session.delete(assignment)
    db.session.commit()
    return redirect(
        url_for('list_assignments', course_id=assignment.course_id))


@app.route('/assignments/<assignment_id>/submissions/new', methods=["POST"])
@login_required
@course_membership_required
def new_submission(assignment_id):
    assignment = Assignment.query.get(assignment_id)
    if request.method == 'POST' and 'file' in request.files:
        filename = submissions.save(request.files['file'])
        rec = Submission(
            filename=filename,
            is_official=False,
            assignment_id=assignment_id,
            user_id=g.user.id)
        rec.save()
        rec.officialize()
    return redirect(url_for('view_assignment', assignment_id=assignment_id))


@app.route('/submissions/<submission_id>/officialize')
@login_required
@course_membership_required
def officialize_submission(submission_id):
    submission = Submission.query.get(submission_id)
    if submission.user == g.user:
        submission.officialize()
        return redirect(
            url_for('view_assignment', assignment_id=submission.assignment_id))
    else:
        abort(403)


@app.route('/courses/<course_id>/presentations')
@login_required
@course_membership_required
def list_presentations(course_id):
    course = Course.query.get(course_id)
    return render_template(
        'presentation/list.html', course=course, presentations=presentations)


@app.route('/courses/<course_id>/presentations/new', methods=["GET", "POST"])
@login_required
@instructor_required
@course_membership_required
def new_presentation(course_id):
    course = Course.query.get(course_id)
    if request.method == "POST":
        name = request.form.get('name', None)
        display_at = request.form.get('display-at', None)
        file_ = request.files.get('file', None)
        if name and display_at and file_:
            filename = presentations.save(file_)
            presentation = Presentation(
                name=name, filename=filename, course_id=course.id)
            presentation.display_at = parse(display_at)
            course.add_presentation(presentation)
            db.session.add(presentation)
            db.session.commit()
            return redirect(url_for('list_presentations', course_id=course_id))
    return render_template('presentation/new.html', course=course)


@app.route('/presentations/<presentation_id>/edit', methods=["GET", "POST"])
@login_required
@instructor_required
def edit_presentation(presentation_id):
    presentation = Presentation.query.get(presentation_id)
    if request.method == "POST":
        name = request.form.get('name', None)
        display_at = request.form.get('display-at', None)
        file_ = request.files.get('file', None)
        if name:
            presentation.name = name
        if display_at:
            presentation.display_at = parse(display_at)
        if file_:
            presentation.filename = presentations.save(file_)
        presentation.save()
        return redirect(
            url_for('list_presentations', course_id=presentation.course_id))
    return render_template('presentation/edit.html', presentation=presentation)


@app.route('/presentations/<presentation_id>/delete', methods=["GET"])
@login_required
@instructor_required
def delete_presentation(presentation_id):
    presentation = Presentation.query.get(presentation_id)
    db.session.delete(presentation)
    db.session.commit()
    return redirect(
        url_for('list_presentations', course_id=presentation.course_id))


uploads = Blueprint('uploads', __name__, url_prefix='/uploads')

@uploads.route('/<setname>/<path:filename>')
@login_required
def show(setname, filename):
    config = current_app.upload_set_config.get(setname)
    if config is None:
        abort(404)
    if g.user.has_permission_to_read(setname, filename):
        return send_from_directory(config.destination, filename)
    else:
        abort(403)
app.register_blueprint(uploads)


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, ssl_context='adhoc')
