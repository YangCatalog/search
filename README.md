Yang-search
=======

## Django version basics

### PROJECT STRUCTURE
```
├── LICENSE  
├── README.md  
├── scripts | database handling, importing the new modules intot the DB
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
```

### URL SCHEME

* /  =>   the home page
* /show_node/        
* /yang_tree/
* /impact_analysis/
	- modtags= comma-separated list of modules to display (without the .yang file extension)
	- orgtags = comma-separated list of organization do display (ieee, ietf, bbf, ...)
	- recursion = integer
	- show_rfcs = if present, then show ratified standard
	- show_subm = if present, then show submodules
	- show_dir = direction ('both', 'dependencies', 'dependents')
* /module_details/
	- module = the module name, the .yang or .yin extensions are ignored
* /metadata_update/ => called when a module is created or deleted, check signature, then save the changes in JSON files (to be picked up by a cronjob later)

### Dependancies

_requirements.txt contains Python libraries_
