from subprocess import PIPE
import shlex
import psutil
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort
import foxutils.path
import foxutils.process

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('blog', __name__)


@bp.route('/')
def index():
    database = get_db()
    # posts = db.execute(
        # 'SELECT p.id, title, body, created, author_id, username'
        # ' FROM post p JOIN user u ON p.author_id = u.id'
        # ' ORDER BY created DESC'
    # ).fetchall()
    instances = database.execute(
        'SELECT p.id, process_id, author_id, created, parameter, title, status'
        ' FROM instance p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    active_pids = []
    for ins in instances:
        pid = int(ins['process_id'])
        if foxutils.process.pid_match_name(pid, 'AjaPublish.exe'):
            active_pids.append(pid)

    return render_template('blog/index.html', instances=instances, pids=active_pids)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    video_files = foxutils.path.listfiles(current_app.config['VIDEO_DIR'], ['.mp4', '.ts'])
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
            database = get_db()
            instances = database.execute(
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
                    ports.append(str(i-1))

        if error:
            flash(error)
        else:
            cmdline = '%s/AjaPublish.exe -ports %s ' % (current_app.config['EXECUTE_DIR'], ','.join(ports))
            if 'bits' in request.form:
                cmdline += '-bit %s ' % request.form['bits']
            if 'duration' in request.form:
                cmdline += '-dur %s ' % request.form['duration']
            if 'mute_audio' in request.form:
                cmdline += '-muteAudio '
            if 'interlaced' in request.form:
                cmdline += '-interlaced '
            if request.form['format'] != 'origin':
                cmdline += '-format %s ' % request.form['format']
            cmdline += '-file %s' % request.form['input_file']

            try:
                aja_process = psutil.Popen(shlex.split(cmdline, posix=False))
            except Exception as except_all:
                flash('failed! %s' % str(except_all))
                return render_template('blog/create.html')
            database = get_db()
            database.execute(
                'INSERT INTO instance (process_id, author_id, parameter, title, ports, status)'
                ' VALUES (?, ?, ?, ?, ?, ?)',
                (aja_process.pid, g.user['id'], cmdline, request.form['title'], ','.join(ports), 'on')
            )
            database.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html', videos=video_files)


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
            database = get_db()
            database.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            database.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    database = get_db()
    database.execute('DELETE FROM instance WHERE id = ?', (id,))
    database.commit()
    return redirect(url_for('blog.index'))

@bp.route('/<int:id>/start', methods=('GET',))
@login_required
def start(id):
    post = get_post(id)
    pid = int(post['process_id'])
    cmdline = post['parameter']
    if not foxutils.process.pid_match_name(pid, 'AjaPublish.exe'):
        try:
            process = psutil.Popen(shlex.split(cmdline, posix=False))
            database = get_db()
            database.execute(
                'update instance set process_id = ?'
                ' where id = ?',
                (process.pid, id)
            )
            database.commit()
        except Exception as except_all:
            flash('failed! %s' % str(except_all))

    return redirect(url_for('blog.index'))


@bp.route('/<int:id>/stop', methods=('GET',))
@login_required
def stop(id):
    post = get_post(id)
    pid = int(post['process_id'])
    if foxutils.process.pid_match_name(pid, 'AjaPublish.exe'):
        try:
            psutil.Process(pid).kill()
            database = get_db()
            database.execute(
                'update instance set process_id = ?'
                ' where id = ?',
                (-1, id)
            )
            database.commit()
        except Exception as except_all:
            flash('failed! %s' % str(except_all))

    return redirect(url_for('blog.index'))
