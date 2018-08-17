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

