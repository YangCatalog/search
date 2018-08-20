# Copyright 2018 Cisco and its afficiliates
# 
# Authors Joe Clarke jclarke@cisco.com and Tomás Markovic <Tomas.Markovic@pantheon.tech> for the Python version
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

from django.db import models


class yindex(models.Model):
    module = models.CharField(max_length=255, blank=True, null=True)
    revision = models.CharField(max_length=10, blank=True, null=True)
    organization = models.CharField(max_length=255, blank=True, null=True)
    path = models.TextField(blank=True, null=True)
    statement = models.CharField(max_length=255, blank=True, null=True)
    argument = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    properties = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'yindex'


class modules(models.Model):
    module = models.CharField(max_length=255, blank=True, null=True)
    revision = models.CharField(max_length=10, blank=True, null=True)
    yang_version = models.CharField(max_length=5, blank=True, null=True)
    belongs_to = models.CharField(max_length=255, blank=True, null=True)
    namespace = models.CharField(max_length=255, blank=True, null=True)
    prefix = models.CharField(max_length=255, blank=True, null=True)
    organization = models.CharField(max_length=255, blank=True, null=True)
    maturity = models.CharField(max_length=255, blank=True, null=True)
    compile_status = models.CharField(max_length=255, blank=True, null=True)
    document = models.TextField(blank=True, null=True)
    file_path = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'modules'
