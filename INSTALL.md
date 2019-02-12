#Installation*

##Database

There is no more any SQL database involved in YANG search but rather elasticsearch which must be installed.

##Tree information

/var/yang/ytrees should contain one .json file per YANG module (with the tree information).

##Pyang plugins

YANG search relies on some `pyang` specific plugins which are in `search/scripts/pyang_plugin/`. Those files must be copied/linked as plugins in the `pyang` plugins directory which is usually something such as `/usr/local/lib/python*/dist-packages/pyang/plugins/`. 

##Cron

There are no specific cron jobs.

##Django

Django must be installed (including the Django table in the same database as the yang-search tables).

Ensure that your webserver:
* will serve https://example.org/yang-search/static to the `static/*` files
* will serve https://example.org/yang-search/ via the port of UWSGI

For example:
```
       location /yang-search/static {
            alias /home/yang/yang-search/search/static;
        }

        location /yang-search/ {
            include uwsgi_params;
            uwsgi_pass unix:/var/run/yang/yang-search.sock ;
            uwsgi_read_timeout 300;
        }
```

##UWSGI

UWSGI can be run as an indepedent process or via the `emperor`mechanism.

uwsgi can be run manually with command:
 `uwsgi --chdir=$PATH_TO_DIR --module=yang.wsgi:application --env DJANGO_SETTINGS_MODULE=yang.settings --socket :$SOCKET --home=$PATH_TO_VENV --logto=$PATH_TO_LOG`

Alternatively, the django server can be run as a `vassal` of the `uwsgi emperor` by putting the `yang-search.uwsgi.ini-dist` (renamed into a .ini extension) into the vassals directory (or creating a symbolic).
The `yang-search.uswgi.ini-dist` needs to be customized to the directory installation of course
