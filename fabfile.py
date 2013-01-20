import os
from ConfigParser import SafeConfigParser

from fabric.api import run, local, env, cd
from fabric.contrib.files import exists
from fabric.operations import put, get, sudo

# Config.
env.user = 'ubuntu'
env.key_filename = 'controller.pem'
env.roledefs = {
    'dev': ['107.21.240.103'],
    'staging': ['*'],
    'production': ['*']
}

# Default role will be dev.
env.roles = ['dev']


def _load_config(config='config.ini'):
    """
    Load configuration.
    """

    config = SafeConfigParser()
    config.read('config.ini')

    return config


def deploy(app=None, config='config.ini'):
    """
    Deploy a specific app into several remote hosts.
    :param app: The app to deploy.
    :param config: Configuration file.
    """

    parser = _load_config(config)

    # Local paths.
    local_apps_ini_path = parser.get('iowa', 'local_apps_ini_path')
    local_listeners_path = parser.get('iowa', 'local_listeners_path')

    # Remote paths.
    remote_projects_path = parser.get('iowa', 'remote_projects_path')
    remote_apps_ini_path = parser.get('iowa', 'remote_apps_ini_path')
    remote_listeners_path = parser.get('iowa', 'remote_listeners_path')

    if not app:
        print "Please specify an app"
    elif not os.path.exists(local_apps_ini_path):
        print "The app folder doesn't exist in your local"
    elif not os.path.exists(local_listeners_path):
        print "The listeners folder doesn't exist in your local"
    elif not os.path.exists(os.path.join(local_apps_ini_path, app + '.ini')):
        print "%s.ini seems unrecheable (%s)" \
            % (app, os.path.join(local_apps_ini_path, app + '.ini'))
    elif not os.path.exists(os.path.join(local_apps_ini_path, app + '.ini')):
        print "%s seems unrecheable (%s)" \
            % (app, os.path.join(local_listeners_path, app + '.ini'))
    else:
        print "Updating %s .ini file and listeners..." % app
        with cd(remote_projects_path):
            run('mkdir -p apps')
            put(os.path.join(local_apps_ini_path, app + '.ini'),
                os.path.join(remote_apps_ini_path, app + '.ini'))
            run('mkdir -p listeners')
            run('mkdir -p listeners/locations')
            put(os.path.join(local_listeners_path, 'server'),
                os.path.join(remote_listeners_path,'server'))
            put(os.path.join(local_listeners_path,'locations', app),
                os.path.join(remote_listeners_path,'locations'))
            run('mkdir -p logs && cd logs && touch %s.log' % app)
        print "Done."

    # Fetch generated logs.
    _fetch_log(app=app)


def push(app=None, config='config.ini'):
    """
    Push the latest app's source code into several remote
    hosts.
    :param app: The app to push into the hosts.
    :param config: Configuration file.
    """

    parser = _load_config(config)

    # Local paths.
    local_projects_path = parser.get('iowa', 'local_projects_path')
    # Remote paths.
    remote_projects_path = parser.get('iowa', 'remote_projects_path')

    if not os.path.exists(os.path.join(local_projects_path, app)):
        print "%s not found in you local" % app
    else:
        print "Pushing %s source code..." % app
        with cd(remote_projects_path):
            put('%s' % os.path.join(local_projects_path, app),
                '%s' % remote_projects_path)
        print "Done."


def instruct_server(server_action=None):
    """
    Execute some actions with the server.
    :param action: The action to execute.
    """

    if server_action == 'start':
        print "Starting server..."
        sudo('nginx')
    elif server_action == 'reload':
        print "Reloading server..."
        sudo('nginx -s reload')
    else:
        print "Unknown server action"


def run_uwsgi(server_action=None, config='config.ini'):
    """
    Run uwsgi with 'emperor mode' in the hosts.
    :param server_action: Should also start/reload the server
                          afterwards?.
    :param config: Configuration file.
    """

    parser = _load_config(config)

    # Remote paths.
    remote_projects_path = parser.get('iowa', 'remote_projects_path')
    remote_apps_ini_path = parser.get('iowa', 'remote_apps_ini_path')
    remote_logs_path = parser.get('iowa', 'remote_logs_path')

    # Make sure log and socket folders exist.
    with cd(remote_projects_path):
        run('mkdir -p logs && cd logs && touch uwsgi.log')
        run('mkdir -p sockets')

    # Run uWSGI in emperor mode.
    run('uwsgi --master --emperor %s --daemonize %s'
        ' --die-on-term --uid www-data --gid www-data'
        % (os.path.join(remote_projects_path, remote_apps_ini_path),
           os.path.join(remote_logs_path, 'uwsgi.log')))



def scale(app=None, workers=None, config='config.ini'):
    """
    Scale a specific app into several remote hosts.
    :param app: The app to scale.
    :param workers: The desired number of workers.
    :param config: Configuration file.
    """

    parser = _load_config(config)

    # Local paths.
    local_projects_path = parser.get('iowa', 'local_projects_path')
    local_apps_ini_path = parser.get('iowa', 'local_apps_ini_path')

    if not os.path.exists(os.path.join(local_projects_path, app)):
        print "%s not found in you local" % app
    elif not workers:
        print "Please specify the number of workers"
    else:
        app_parser = SafeConfigParser()
        file_path = os.path.join(local_apps_ini_path, app + '.ini')
        app_parser.read(file_path)

        current_workers = app_parser.get('uwsgi', 'workers')
        app_parser.set('uwsgi', 'workers', workers)
        print "Scaling %s from %s to %s workers..." \
            % (app, current_workers, workers)

        with open(file_path, 'w') as configfile:    # save
            app_parser.write(configfile)
        print "Done."

        # Deploy changes.
        deploy(app=app, config=config)


def _fetch_log(app=None, config='config.ini'):
    """
    Fetch the latest logs.
    :param app: The target app.
    :param config: Configuration file.
    """

    parser = _load_config(config)

    # Remote paths.
    remote_projects_path = parser.get('iowa', 'remote_projects_path')

    print "Fetching generated log..."
    role = _get_current_role()
    local('mkdir -p logs')
    with cd(remote_projects_path):
        get('logs/%s.log' % app, 'logs/%s.%s.log' % (role, app))
        get('logs/uwsgi.log', 'logs/%s.uwsgi.log' % role)


def _get_current_role():
    """
    Helper method which returns the current role.
    """

    for role in env.roledefs.keys():
        if env.host_string in env.roledefs[role]:
            return role
    return None
