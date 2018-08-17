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
