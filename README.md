Iowa - Deploy and scale your web apps in real time 
==================================================

As a developer, when I deploy/scale a web app in my own servers **I want to do
it on a fast, funny and seamless way**, without having to *edit files* or *make
ssh connections* each time. Imagine it on several servers. It's simply annoying.

I always was amazed how easy and fun was deploy/scale with some PaaS services
as *Heroku*. This is an attempt to create an open-source system able to
do most of those common tasks following the same philosophy, just using
**the command line**.

Iowa, for this job, uses **Fabric**, **uWSGI** (Emperor mode) and **NGINX**, so it's mainly
for python web apps. Said that, don't think it's a big deal to export it using different
WSGI HTTP Servers as Unicorn (ruby) or Gunicorn (python) for example.

In a nutshell
-------------

```
	# Run uWSGI in emperor mode. Just do it the first time.
	fab run_uwsgi

	# Push your app.
	fab push:example

	# Deploy it.
	fab deploy:example

	# Scale it!
	fab scale:example,workers=5

```
> Please notice that in order to let **iowa** know about your system's credentials and app's paths,
  you should change the default settings in the **fabfile.py** and **config.ini** files.
  
Adding a new web app
--------------------

1.- Make sure the fabfile.py and config.ini files have proper credentials/paths.

2.- Add a new .ini file in the apps/ folder.

```
	fabfile.py
	config.ini
	apps/
		new_app.ini
```
*.Ini example:*

```
	[uwsgi]
	chdir = /var/www/%n
	pythonpath = /var/www/%n
	master = true
	workers = 1
	socket = /var/www/sockets/%n.sock
	module = hello_world
```
> Keep in mind that, in order to let uWSGI's emperor recognizes that .ini file (a new vassal), your should
  leave the **[uwsgi]** section at the top. If you have questions about the syntax and
  attributes, just check the [uWSGI doc](http://uwsgi-docs.readthedocs.org/en/latest/Options.html "uWSGI doc").

3.- Add a new location in the listeners/ folder.

```
	fabfile.py
	config.ini
	listeners/
		server
		locations/
			new_app
```

*new_app example:*

```
	location /example {
    	include uwsgi_params;
    	uwsgi_pass unix:/var/www/sockets/example.sock;
	}
```
> Note that you should specify this precise socket pattern (#####/sockets/blabla.sock), cause Iowa
  will create a sockets/ folder for this purpose.
  
4.- Create a symbolic link to sites-enabled/ in your nginx remote folder (Just need to do it for the 
    first application)
    
```
	ln -s /var/www/listeners/server /etc/nginx/sites-enabled/server
```
> Change the paths in case you have a different files structure.
  
4.- Run the above commands in the specified order (fab push....)

5.- Go to http://<server_host>/example and watch your work!

6.- Let's scale it again, It's fun!
```
	fab scale:example, workers=7 
```

Contributing
------------

If you'd like to contribute, just Fork the repository, create a branch with your changes and send a pull request. 
Don't forget appending your name to AUTHORS ;)


*Sunday, 20th January, 2013*
