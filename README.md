Yang-search
=======

## Django version basics

**PROJECT STRUCTURE:**

├── LICENSE  
├── README.md  
├── search | django application dir   
│   ├── apps.py    
│   ├── models.py | defines database structure  
│   ├── templates  
│   │   └── search | all the html templates   
│   ├── templatetags  
│   │   └── search_extras.py | support functions for templates  
│   ├── tests.py  
│   ├── urls.py | Defines usable urls in search app  
│   └── views.py | Provides backend for html templates  
├── static | static files for the website  
├── staticfiles | static root for django  
└── yang | main django project settings  
    ├── settings.py | default django settings  
    ├── urls.py  
    └── wsgi.py  

**URL SCHEME**

/   
/show_node/        
/yang_tree/
/impact_analysis/
/module_details/

**DATABASE STRUCTURE:**

 * **table yindex**
 * module = CharField(max_length=255, blank=True, null=True)
 * revision = CharField(max_length=10, blank=True, null=True)
 * organization = CharField(max_length=255, blank=True, null=True)
 * path = TextField(blank=True, null=True)
 * statement = CharField(max_length=255, blank=True, null=True)
 * argument = CharField(max_length=255, blank=True, null=True)
 * description = TextField(blank=True, null=True)
 * properties = TextField(blank=True, null=True)
 
 
 * **table modules**
 * module = CharField(max_length=255, blank=True, null=True)
 * revision = CharField(max_length=10, blank=True, null=True)
 * yang_version = CharField(max_length=5, blank=True, null=True)
 * belongs_to = CharField(max_length=255, blank=True, null=True)
 * namespace = CharField(max_length=255, blank=True, null=True)
 * prefix = CharField(max_length=255, blank=True, null=True)
 * organization = CharField(max_length=255, blank=True, null=True)
 * maturity = CharField(max_length=255, blank=True, null=True)
 * compile_status = CharField(max_length=255, blank=True, null=True)
 * document = TextField(blank=True, null=True)
 * file_path = TextField(blank=True, null=True)

Migration of database was done with sequence of commands:  
`sqlite3 yang.db .dump > /$PATH/foo.dump`    
`sed -i '/BEGIN TRANSACTION/d' /$PATH/foo.dump`  
`sed -i '/PRAGMA foreign_keys=OFF/d' /$PATH/foo.dump`  
`sed -i -e 's/INSERT INTO "modules"/INSERT INTO modules(module,revision,yang_version,belongs_to,namespace,prefix,organization,maturity,compile_status,document,file_path)/g' /$PATH/foo.dump`  
`sed -i -e 's/INSERT INTO "yindex"/INSERT INTO yindex(module,revision,organization,path,statement,argument,description,properties)/g' /$PATH/foo.dump`  
Note: this command is just for speeding up the transmition, but might not be
viable for production.  
`sed -i '1s/^/SET autocommit=0;\n/' /$PATH/foo.dump`  
`mysql -u $DBUSER -p$DBPASSWORD $DBNAME < /$PATH/foo.dump`  

 * Python version currently is 3.5.5
 * Mysql version is 5.7.22

requirements.txt contains python libraries

uwsgi is running with command 
 *     uwsgi --chdir=$PATH_TO_DIR --module=yang.wsgi:application --env DJANGO_SETTINGS_MODULE=yang.settings --socket :$SOCKET --home=$PATH_TO_VENV --logto=$PATH_TO_LOG
