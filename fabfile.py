import os
from ConfigParser import SafeConfigParser

from fabric.api import run, local, env, cd, hide
from fabric.contrib.files import exists
from fabric.operations import put, get, sudo

from conf.yaml_reader import YamlReader

# Config.
env.user = 'ubuntu'
env.key_filename = '~/.ssh/controller.pem'
env.roledefs = {
    'dev': ['107.21.240.103'],
    'staging': ['*'],
    'production': ['*']
}

# Default role will be dev.
env.roles = ['dev']


def _load_config(path='conf/config.ini'):
    """
    Load configuration.
    """

    config = SafeConfigParser()
    config.read(path)

    return config


def deploy(app=None, config='conf/config.ini'):
    """
    Deploy a specific app into several remote hosts.
    :param app: The app to deploy.
    :param config: Configuration file.
    """
    
    if os.path.exists(config):
        parser = _load_config(config)
    else:
        print "Are you in the right path?"
        sys.exit(1)

    # Local paths.
    local_servers_path = parser.get('iowa', 'local_servers_path')
    local_projects_path = parser.get('iowa', 'local_projects_path')

    # Remote paths.
    remote_servers_path = parser.get('iowa', 'remote_servers_path')
    remote_projects_path = parser.get('iowa', 'remote_projects_path')

    if not app:
        print "Please specify an app"
    elif not os.path.exists(os.path.join(local_projects_path, app)):
        print "The app folder doesn't exist in your local"
    elif not os.path.exists(local_servers_path):
        print "The servers folder doesn't exist in your local"
    elif not os.path.exists(os.path.join(local_projects_path, app, app + '.ini')):
        print "%s.ini seems unreachable (%s)" \
            % (app, os.path.join(local_projects_path, app, app + '.ini'))
    elif not os.path.exists(os.path.join(local_servers_path, app)):
        print "%s seems unreachable (%s)" \
            % (app, os.path.join(local_servers_path, app + '.ini'))
    else:
        print "Updating server..."
        with cd(remote_projects_path), hide('everything'):
            run('mkdir -p servers')
            put(os.path.join(local_servers_path, app),
                remote_servers_path)
            run('mkdir -p logs && cd logs && touch %s.%s.log' % (_get_current_role(), app))
            
            push(app=app)
            instruct_server(server_action='reload')


def push(app=None, config='conf/config.ini'):
    """
    Push the latest app's source code into several remote
    hosts.
    :param app: The app to push into the hosts.
    :param config: Configuration file.
    """

    if os.path.exists(config):
        parser = _load_config(config)
    else:
        print "Are you in the right path?"
        sys.exit(1)

    # Local paths.
    local_projects_path = parser.get('iowa', 'local_projects_path')
    # Remote paths.
    remote_projects_path = parser.get('iowa', 'remote_projects_path')

    if not os.path.exists(os.path.join(local_projects_path, app)):
        print "%s not found in you local" % app
    else:
        print "Pushing %s source code..." % app
        with cd(remote_projects_path):
            run('mkdir -p %s' % app)
            put('%s' % os.path.join(local_projects_path, app),
                '%s' % remote_projects_path)


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


def scale(app=None, process=None, workers=None, config='conf/config.ini'):
    """
    Scale a specific app into several remote hosts.
    :param app: The targeted app.
    :param process: The process to scale.
    :param workers: The desired number of workers.
    :param config: Configuration file.
    """

    if os.path.exists(config):
        parser = _load_config(config)
    else:
        print "Are you in the right path?"
        sys.exit(1)

    # Local paths.
    local_projects_path = parser.get('iowa', 'local_projects_path')
    
    # Remote paths.
    remote_projects_path = parser.get('iowa', 'remote_projects_path')

    if not os.path.exists(os.path.join(local_projects_path, app)):
        print "%s not found in you local" % app
    elif not process:
        print "Please specify the process type"
    elif not workers:
        print "Please specify the number of workers"
    else:
        # Read the .ini.
        file_path = os.path.join(local_projects_path, app, app + '.ini')
        uwsgi_ini = SafeConfigParser()
        uwsgi_ini.read(file_path)
        
        # Read the Procfile.
        procfile = YamlReader(os.path.join(local_projects_path, app))
        declared_processes = procfile.get_processes()

        if not process in declared_processes:
            print "Unknown %s process" % process
        else:
            # Write the new configuration in the app's .ini file.
            uwsgi_ini.set('uwsgi', 'workers', workers)
            with open(file_path, 'w') as configfile:
                uwsgi_ini.write(configfile)
            with hide('everything'):
                if int(workers) > 0:
                    # Scaling... and updating remote .ini file.
                    print "Scaling %s:%s to %s workers..." \
                        % (app, process, workers)
                    put(file_path, os.path.join(remote_projects_path, app, app + '.ini'))
                    with cd(os.path.join(remote_projects_path, app)):
                        run('%s' % declared_processes[process])
                else:
                    # Scaling to 0 workers. The app will be stopped.
                    print "Stopping %s:%s ..." % (app, process)
                    run('kill -INT `cat /tmp/%s.pid`' % app)


def _get_current_role():
    """
    Helper method which returns the current role.
    """

    for role in env.roledefs.keys():
        if env.host_string in env.roledefs[role]:
            return role
    return None
