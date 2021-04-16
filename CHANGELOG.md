## Yang Search Release Notes

* ##### vm.m.p - 2021-MM-DD

* ##### v3.2.0 - 2021-04-15

  * Logs format modified - added filename information [#89](https://github.com/YangCatalog/search/issues/89)
  * Python base image bumped to version 3.9 [deployment #66](https://github.com/YangCatalog/deployment/issues/66)
  * Elasticsearch start control

* ##### v3.1.0 - 2021-18-03

  * No changes - released with other [deployment submodules](https://github.com/YangCatalog/deployment)

* ##### v3.0.1 - 2021-02-26

  * rsyslog and systemd added to Docker image build [deployment #48](https://github.com/YangCatalog/deployment/issues/48)

* ##### v3.0.0 - 2021-02-10

  * Explicitly set version of Python base image to 3.8
  * Update Dockerfile
  * Moved to Gunicorn from Uwsgi [deployment #39](https://github.com/YangCatalog/deployment/issues/39)
  * Switch to elasticsearch in AWS [deployment #38](https://github.com/YangCatalog/deployment/issues/38)
  * Update pyang [deployment #36]( https://github.com/YangCatalog/deployment/issues/36)
  * Various major/minor bug fixes and improvements

* ##### v2.0.0 - 2020-08-14

  * Fix alerts
  * Add health check endpoint
  * Update indexing script to be more resistant against edge case
  * Update Dockerfile
  * Update json_tree plugin script[#67](https://github.com/YangCatalog/search/issues/67)
  * Load more parameters from config file
  * Various major/minor bug fixes and improvements

* ##### v1.1.0 - 2020-07-16

  * Update indexing script to parse huge files[#75](https://github.com/YangCatalog/search/issues/75)
  * Fixes with pyang update
  * Update pyang
  * Update Dockerfile
  * Various major/minor bug fixes and improvements

* ##### v1.0.1 - 2020-07-03

  * Various major/minor bug fixes and improvements

* ##### v1.0.0 - 2020-06-23

  * Initial submitted version
