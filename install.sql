/*
Copyright 2018 Cisco and its affiliates

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

CREATE TABLE `modules` (
	  `id` int(11) NOT NULL AUTO_INCREMENT,
	  `module` varchar(255) DEFAULT NULL,
	  `revision` varchar(10) DEFAULT NULL,
	  `yang_version` varchar(5) DEFAULT NULL,
	  `belongs_to` varchar(255) DEFAULT NULL,
	  `namespace` varchar(255) DEFAULT NULL,
	  `prefix` varchar(255) DEFAULT NULL,
	  `organization` varchar(255) DEFAULT NULL,
	  `maturity` varchar(255) DEFAULT NULL,
	  `compile_status` varchar(255) DEFAULT NULL,
	  `document` longtext,
	  `file_path` longtext,
	  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8 ;

CREATE TABLE `yindex` (
	  `id` int(11) NOT NULL AUTO_INCREMENT,
	  `module` varchar(255) DEFAULT NULL,
	  `revision` varchar(10) DEFAULT NULL,
	  `organization` varchar(255) DEFAULT NULL,
	  `path` longtext,
	  `statement` varchar(255) DEFAULT NULL,
	  `argument` varchar(255) DEFAULT NULL,
	  `description` longtext,
	  `properties` longtext,
	  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8 ;

