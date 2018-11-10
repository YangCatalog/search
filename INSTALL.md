*Installation*

**SQL Database**

Create a database in MySQL with read/write access for a user and execute the install.sql file (you can safely remove it after).

Be sure that /etc/yangcatalog.conf has the right information about MySQL database and credentials as well as the secret token for the metadata update.

**Tree information**

/var/yang/ytrees should contain one .json file per YANG module (with the tree information).

**Cron**

There are no specific cron jobs.

**Django**

Django must be installed (including the Django table in the same database as the yang-search tables).

Ensure that your webserver:
* will serve https://example.org/yang-search/static to the `static/*` files
* will serve https://example.org/yang-search/ via the port of UWSGI

For example:
```
       location /yang-search/static {
            alias /var/www/html/yang-search/static;
        }

        location /yang-search/ {
            include uwsgi_params;
            uwsgi_pass unix:/var/run/yang/yang-search.sock ;
            uwsgi_read_timeout 300;
        }
```

**UWSGI**

UWSGI can be run as an indepedant process or via the `emperor`mechanism.

uwsgi can be run manually with command:
 `uwsgi --chdir=$PATH_TO_DIR --module=yang.wsgi:application --env DJANGO_SETTINGS_MODULE=yang.settings --socket :$SOCKET --home=$PATH_TO_VENV --logto=$PATH_TO_LOG`

Alternatively, the django server can be run as a `vassal` of the `uwsgi emperor` by putting the yang-search.uwsgi.ini into the vassals directory (or creating a symbolic).
The yang-search.uswgi.ini needs to be customized to the directory installation of course
