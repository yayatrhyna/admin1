import os

from functools import wraps
from flask import redirect, url_for, abort
from flask_login import current_user

OPERATORS = [
    ('=', '='), 
    (':=', ':='),
    ('==', '=='),
    ('+=', '+='),
    ('!=', '!='),
    ('>', '>'),
    ('>=', '>='),
    ('<', '<'),
    ('<=', '<='),
    ('=~', '=~'),
    ('!~', '!~'),
    ('=*', '=*'),
    ('!*', '!*')
]

def read_vendors(dict_folder_path):
    if not os.path.exists(dict_folder_path):
        return None

    vendors = []
    for file in os.listdir(dict_folder_path):
        if file.startswith('dictionary'):
            filename_parts = file.split('.')[1:]
            
            vendor = '-'.join([fp.capitalize() for fp in filename_parts])
            if vendor == 'Freeradius':
                continue

            vendors.append(('.'.join(filename_parts), vendor))
    vendors = sorted(vendors, key=lambda v: v[1])
    vendors.append(('others', 'Others'))
    return list(filter(lambda v: v[1] != '', vendors))

def read_dictionary(dict_path):
    if not os.path.isfile(dict_path):
        return None

    with open(dict_path, 'r') as dictionary_file:
        lines = dictionary_file.readlines()
        filename = dict_path.split('/')[-1]
        filename_parts = filename.split('.')[1:]
        vendor = '-'.join([fp.capitalize() for fp in filename_parts])

        attributes = []
        values = []

        for line in lines:
            # filter values
            line = line.replace('\n', '')
            line_list = line.split('\t')
            line_list = list(filter(lambda s: s != '', line_list))

            if len(line_list):
                if line_list[0] == 'ATTRIBUTE':
                    attribute = {
                        'name': line_list[1],
                        'number': line_list[2] if len(line_list) > 2 else None,
                        'type': line_list[3] if len(line_list) > 3 else None,
                        'options': line_list[4] if len(line_list) > 4 else None
                    }
                    attributes.append(attribute)
                elif line_list[0] == 'VALUE':
                    attribute_exists = [a for a in attributes if a['name'] == line_list[1]]
                    if not len(attribute_exists):
                        attribute = {
                            'name': line_list[1],
                            'number': None,
                            'type': None,
                            'options': None
                        }
                        attributes.append(attribute)
                    
                    value = {
                        'attribute': line_list[1],
                        'name': line_list[2],
                        'number': line_list[3] if len(line_list) > 3 else None
                    }
                    values.append(value)

        return {'vendor': vendor, 'attributes': attributes, 'values': values}


def has_access():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            if not current_user.has_access:
                return abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def running_on_docker():
    with open('/proc/self/cgroup', 'r') as procfile:
        for line in procfile:
            fields = line.strip().split('/')
            if fields[1] == 'docker':
                return True

    return False
