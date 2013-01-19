import os
from ConfigParser import SafeConfigParser

from fabric.api import local, run, env, cd
from fabric.contrib.files import exists
from fabric.operations import put, sudo

# Config.
env.user = 'ubuntu'
env.hosts = ['107.21.240.103']
env.key_filename = 'controller.pem'

projects = ['iowa', 'cluster']
projects_path = '/home/ubuntu/www/'
ini_folder = 'apps'
listeners_folder = 'listeners'
server_config_folder = 'server'
logs_path = '/home/ubuntu/www/logs'


def deploy(app=None, should_push=False, server_action=None):
    """
    Deploy a specific app into several remote hosts.
    :param app: The app to deploy.
    :param push: Should also update the app's source code?.
    :param server_action: Should also start/reload the server
                          afterwards?.
    """
    if not app:
        print "Please specify an app"
    elif not os.path.exists(ini_folder):
        print "The app folder doesn't exist in your local"
    elif not os.path.exists(listeners_folder):
        print "The listeners folder doesn't exist in your local"
    elif not os.path.exists(os.path.join(ini_folder, app +'.ini')):
        print "%s.ini seems unrecheable (%s)" % (app, os.path.join(ini_folder, app +'.ini'))
    elif not os.path.exists(os.path.join(ini_folder, app +'.ini')):
        print "%s seems unrecheable (%s)" % (app, os.path.join(listeners_folder, app +'.ini'))
    else:
        print "Deploying %s to the remote hosts" % app
        with cd(os.path.join(projects_path)):
            put(os.path.join(ini_folder, app +'.ini'), os.path.join(ini_folder, app +'.ini'))
            put(os.path.join(listeners_folder, app), os.path.join(listeners_folder, app +'.ini'))
            if not exists('logs'):
                run('mkdir logs')
            run('cd logs && touch %s.log' % app)
            
    # Upload the latest code.
    if should_push:
        push(app)
    
    if server_action:
        _make_server(server_action)
        
def push(app=None):
    """
    Push the latest app's source code into several remote
    hosts.
    :param app: The app to push into the hosts.
    """
    if not os.path.exists(app):
        print "%s not found in you local" % app
    else:
        print "Pushing %s source code" % app
        with cd(projects_path):
            put('%s' % app, '%s' % projects_path)
    
def _make_server(action=None):
    """
    Execute some actions with the server.
    :param action: The action to execute.
    """
    
    if action == 'start':
        print "Starting server..."
        sudo('nginx')
    elif action == 'reload':
        print "Reloading server..."
        sudo('nginx -s reload')
    else:
        print "Unknown server action"
            
def run_uwsgi(server_action=None):
    """
    Run uwsgi with 'emperor mode' in the hosts.
    :param server_action: Should also start/reload the server
                          afterwards?.
    """
    # Make sure log folder exists.
    with cd(os.path.join(projects_path)):
        if not exists('logs'):
            run('mkdir logs')
        run('cd logs && touch uwsgi.log')

    if server_action:
        _make_server(server_action)
        
    run('uwsgi --master --emperor %s --daemonize %s'
        ' --die-on-term --uid www-data --gid www-data'
        % (os.path.join(projects_path, ini_folder), os.path.join(logs_path, 'uwsgi.log')))
    
def scale(app=None, workers=None):
    """
    Scale a specific app into several remote hosts.
    :param app: The app to scale.
    :param workers: The desired number of workers.
    """
    if not os.path.exists(app):
        print "%s not found in you local" % app
    elif not workers:
        print "Please specify the number of workers"
    else:
        parser = SafeConfigParser()
        file_path = os.path.join(ini_folder, app +'.ini')
        parser.read(file_path)

        current_workers = parser.get('uwsgi', 'workers')
        parser.set('uwsgi', 'workers', workers)
        print "Scaling %s from %s to %s workers..." % (app, current_workers, workers)

        with open(file_path, 'w') as configfile:    # save
            parser.write(configfile)
        
        deploy(app)
    
    
