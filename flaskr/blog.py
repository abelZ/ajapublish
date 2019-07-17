from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('blog', __name__)


@bp.route('/')
def index():
    db = get_db()
    # posts = db.execute(
        # 'SELECT p.id, title, body, created, author_id, username'
        # ' FROM post p JOIN user u ON p.author_id = u.id'
        # ' ORDER BY created DESC'
    # ).fetchall()
    instances = db.execute(
        'SELECT p.id, process_id, author_id, created, parameter, title, status'
        ' FROM instance p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    return render_template('blog/index.html', instances=instances)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        error = ''
        if int(request.form['duration']) < 0:
            error = 'duration is not valid, need >= 0'
        elif not ('port1' in request.form or 'port2' in request.form or 'port3' in request.form or 'port4' in request.form):
            error = 'at least 1 port should be selected'
        elif not 'format' in request.form:
            error = 'format must be set'
        elif not 'input_file' in request.form:
            error = 'input file must be set'
        elif not request.form['title']:
            error = 'you must input the title'
        else:
            used_ports = []
            db = get_db()
            instances = db.execute(
                'SELECT p.id, ports'
                ' FROM instance p ORDER BY created DESC'
                ).fetchall()
            for ins in instances:
                used_ports.extend(ins['ports'].split(','))
            
            ports = []
            for i in range(1, 5, 1):
                if 'port%d' % i in request.form:
                    if str(i) in used_ports:
                        error = 'port %d already in use' % i
                        break
                    ports.append(str(i))

        if error:
            flash(error)
        else:
            cmdline = 'AjaPublish.exe -ports %s ' % ','.join(ports)
            if 'bits' in request.form:
                cmdline += '-bits %s ' % request.form['bits']
            if 'duration' in request.form:
                cmdline += '-duration %s ' % request.form['duration']
            if 'mute_audio' in request.form:
                cmdline += '-mute '
            if 'interlaced' in request.form:
                cmdline += '-interlaced '
            if request.form['format'] != 'origin':
                cmdline += '-format %s ' % request.form['format']
            cmdline += '-file %s' % request.form['input_file']
            db = get_db()
            db.execute(
                'INSERT INTO instance (process_id, author_id, parameter, title, ports, status)'
                ' VALUES (?, ?, ?, ?, ?, ?)',
                (99, g.user['id'], cmdline, request.form['title'], ','.join(ports), 'on')
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')


def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, process_id, author_id, created, parameter, title, status'
        ' FROM instance p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))

@bp.route('/<int:id>/start', methods=('GET',))
@login_required
def start(id):
    post = get_post(id)
    new_status = ''
    if post['status'] == 'on':
        new_status = 'off'
    else:
        new_status = 'on'

    db = get_db()
    db.execute(
        'update instance set status = ?'
        ' where id = ?',
        (new_status, id)
    )
    db.commit()
    return redirect(url_for('blog.index'))


@bp.route('/<int:id>/stop', methods=('GET',))
@login_required
def stop(id):
    post = get_post(id)
    new_status = ''
    if post['status'] == 'on':
        new_status = 'off'
    else:
        new_status = 'on'

    db = get_db()
    db.execute(
        'update instance set status = ?'
        ' where id = ?',
        (new_status, id)
    )
    db.commit()
    return redirect(url_for('blog.index'))
