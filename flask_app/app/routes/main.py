import os.path
import subprocess

from app import app, db, cache
from flask import render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import event

from app.models.auth import User, Group
from app.models.radius import (
    RadGroupCheck, RadGroupReply, RadUserGroup,
    RadCheck, Nas
)

from app.utils import read_dictionary, running_on_docker

@app.before_first_request
def setup():
    # create admin user
    if not User.query.count():
        app.logger.info('No users found. Creating new admin user.')
        admin = User(
            username='admin', password='freeradius@admin',
            name='Administrative User', has_access=True
        )
        admin.hash_password()
        db.session.add(admin)

        db.session.add(RadCheck(
            username='admin',
            attribute='Cleartext-Password',
            op=':=',
            value='freeradius@admin'
        ))
        db.session.commit()

    # create default users groups
    if not Group.query.count():
        app.logger.info('No groups found. Creating default user group.')
        db.session.add(Group(name='user', description='Default user group'))

        # create default parameters for groups
        db.session.add(RadUserGroup(
            username='admin', groupname='user', priority=1
        ))
        db.session.commit()

@app.route('/_filter_attributes')
@cache.cached(timeout=1800, query_string=True)
@login_required
def _filter_attributes():
    dict_path = app.config.get('DICTIONARIES_PATH')
    vendor = request.args.get('vendor')
    if not vendor or vendor == 'others':
        return jsonify([('Custom', 'Custom')])

    dict_data = read_dictionary(
        os.path.join(dict_path, 'dictionary.' + vendor)
    )
    attributes = [(d['name'], d['name']) for d in dict_data['attributes']]
    attributes = sorted(attributes, key=lambda a: a[1])
    attributes.append(('Custom', 'Custom'))

    return jsonify(attributes) if dict_data else jsonify([])

@app.route('/_filter_values')
@cache.cached(timeout=1800, query_string=True)
@login_required
def _filter_values():
    dict_path = app.config.get('DICTIONARIES_PATH')
    vendor = request.args.get('vendor')
    attribute = request.args.get('attribute')
    
    dict_data = read_dictionary(
        os.path.join(dict_path, 'dictionary.' + vendor)
    )
    if dict_data:
        values = [(d['name'], d['name']) for d in dict_data['values'] 
                                        if d['attribute'] == attribute]
    else:
        values = []

    return jsonify(sorted(values, key=lambda v: v[1]))
    
@event.listens_for(Nas, 'after_insert')
def on_insert_nas(mapper, connection, target):
    ### The Freeradius server must be restarted every time you add a
    ### new NAS record. If you are using docker, you may need to
    ### configure a restart policy, such as a cronjob or similar.
    if not running_on_docker():
        subprocess.run(["systemctl", "restart", "freeradius.service"])
