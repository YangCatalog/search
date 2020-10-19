
bind = "unix:/var/run/yang/yang-search.sock"
#umask = os.umask('007')

workers = 5

max_requests = 1000
timeout = 300
keep_alive = 2

user = 'yang'
group = 'yang'

preload = True

accesslog = '/var/yang/logs/uwsgi/yang-search-access.log'
errorlog = '/var/yang/logs/uwsgi/yang-search-error.log'
loglevel = 'debug'
#change log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'