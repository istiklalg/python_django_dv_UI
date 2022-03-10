
"""
@author : istiklal
Database model for existing database structure
"""
import datetime
import decimal
import json
import logging
import math
import os
from statistics import mode

import jsonpickle
import requests
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, connection
from django.db.models import Manager, F
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import is_protected_type
from elasticsearch import Elasticsearch

from ATIBAreport.ElasticModels import es_host_list, es_port_number
from ATIBAreport.setting_files.passes import atibaApiService_PORT, atibaApiService_API_KEY

logger = logging.getLogger('models')
# es_host_list = ['127.0.0.1', '192.168.1.63', '192.168.1.92']
# host_list = ['127.0.0.1'] if os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.production" else ['192.168.1.92']


def check_environment_for_elastic():
    return os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.production" or os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.developing"


def mac_to_simplified(mac_address):
    return str.replace(f'{mac_address}', ':', '')


def simplified_to_mac(simplified_mac):
    return ':'.join(simplified_mac[i:i+2] for i in range(0, len(simplified_mac), 2))


class AiModels(models.Model):
    id = models.IntegerField(blank=True, null=True)
    modeltype = models.TextField(primary_key=True)
    model = models.BinaryField(blank=True, null=True)
    encodelogndx = models.BinaryField(blank=True, null=True)
    encodeparams = models.BinaryField(blank=True, null=True)
    aimetric = models.BinaryField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.modeltype

    class Meta:
        managed = False
        db_table = 'aimodels'
        ordering = ['-id']   # it used for reset_ai


class GeneralParameterDetail(models.Model):
    # shortCode = models.ForeignKey(GeneralParameters, to_field="kisakod", db_column="kisakod", db_index=False,
    #                               related_name="parameterDetail", on_delete=models.CASCADE)

    # verbose_name = "Parameter Code",
    kod = models.CharField(max_length=8)
    # verbose_name = "Parameter Short Code",
    kisakod = models.CharField(primary_key=True, max_length=10)
    # verbose_name = "Short ACK",
    kisaack = models.CharField(max_length=20, blank=True, null=True)
    # verbose_name = "ACK",
    ack = models.TextField(blank=True, null=True)
    # verbose_name = "Place in Queue",
    sira = models.IntegerField(blank=True, null=True)
    # verbose_name = "Is Active?",
    aktifpasif = models.BooleanField(blank=True, null=True)
    # verbose_name = "Min Value",
    minvalue = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    # verbose_name = "Max Value",
    maxvalue = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.kisaack

    class Meta:
        managed = False
        db_table = 'genelparametredetay'
        unique_together = (('kisakod', 'kod'),)
        ordering = ['kisakod', 'kod', 'aktifpasif']


class GeneralParameters(models.Model):

    shortCode = models.ForeignKey(GeneralParameterDetail, to_field="kisakod", db_column="kisakod", db_index=False,
                                  related_name="parameter", on_delete=models.CASCADE)

    # verbose_name = "Short Code",
    # kisakod = models.CharField(primary_key=True, max_length=10)
    # verbose_name = "Explanation",
    aciklama = models.TextField(blank=True, null=True)
    # verbose_name = "Authorization Role",
    yetkirole = models.CharField(max_length=5, blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.aciklama

    class Meta:
        managed = False
        db_table = 'genelparametreler'


class DeviceMark(models.Model):

    id = models.IntegerField(primary_key=True)
    markname = models.TextField(null=True, blank=True)
    markfilename = models.TextField(null=True, blank=True)
    markversion = models.TextField(null=True, blank=True)
    marksubversion = models.IntegerField(null=True, blank=True)

    objects = Manager()

    def __str__(self):
        return str(self.markname)

    class Meta:
        managed = False
        db_table = 'devicemark'
        ordering = ['markname']


class DeviceVersionParse(models.Model):

    # verbose_name="Device Version Parser Name",
    versionparsename = models.TextField(blank=True, null=True)
    # verbose_name="Parser Start Definition",
    parsestartdef = models.TextField(blank=True, null=True)
    # verbose_name="Version Parse Length",
    parselength = models.IntegerField(blank=True, null=True)
    # verbose_name="Device Version Parser ID",
    versionoid = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.versionparsename

    class Meta:
        managed = False
        db_table = 'deviceversionparse'
        ordering = ['versionparsename']


class DeviceModel(models.Model):
    """
    This database table contains device model information like model name, device type, version, model code etc.
    """
    # verbose_name = "Device TradeMark(Brand) Info",
    brand = models.ForeignKey(DeviceMark, on_delete=models.CASCADE, related_name="models", db_index=False,
                              db_column='devicemarkid')
    # verbose_name = "Device Version Parse Info",
    versionParse = models.ForeignKey(DeviceVersionParse, related_name="models", on_delete=models.CASCADE,
                                     db_index=False, db_column="versionparseid")

    # foreignKey references;
    # devicemarkid = models.IntegerField(verbose_name="Device's Trademark(Brand) Id", null=True, blank=True)
    # versionparseid = models.IntegerField(verbose_name="Device's Version Parse ID", null=True, blank=True)

    # verbose_name = "Device Model Name",
    modelname = models.TextField(null=True, blank=True)
    # verbose_name = "Device Type Code",
    devicetypecode = models.TextField(null=True, blank=True)
    # verbose_name = "Device Definition Code",
    fielddefcode = models.IntegerField(null=True, blank=True)
    # verbose_name = "Device Model Code",
    modelcode = models.TextField(null=True, blank=True)
    # verbose_name = "Device Type",
    devicetype = models.TextField(null=True, blank=True)

    objects = Manager()

    def __str__(self):
        return self.modelname

    def get_versions(self):
        _version_list = []
        try:
            _version_list = [_.versioncode for _ in DeviceVersions.objects.filter(devicetype=self.devicetype)]
        except Exception as err:
            logger.exception(f"An error occurred trying to get version list for {self.devicetype}")
        return _version_list

    class Meta:
        managed = False
        db_table = 'devicemodel'
        ordering = ['modelname', 'devicetype']


class DeviceConfigProfile(models.Model):
    """
    This database table contains device configuration profile information
    """
    # verbose_name="Device Configuration Code",
    configcode = models.TextField(null=True, blank=True)
    # verbose_name="Device Configuration Name",
    configname = models.TextField(null=True, blank=True)
    # verbose_name="Device Configuration Text",
    configtxt = models.TextField(null=True, blank=True)

    objects = Manager()

    def __str__(self):
        return self.configname

    class Meta:
        managed = False
        db_table = 'deviceconfigprofile'
        ordering = ['configcode']


class VersionConfigs(models.Model):
    """
    This database table contains device version configuration profile information
    """
    # verbose_name="Version Configuration Code",
    configcode = models.TextField(null=True, blank=True)
    # verbose_name="Version Configuration Text",
    configtxt = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.configcode

    class Meta:
        managed = False
        db_table = 'versionconfigs'
        ordering = ['configcode']


class DeviceVersions(models.Model):

    # verbose_name = "Device Configuration",
    config = models.ForeignKey(VersionConfigs, on_delete=models.CASCADE,
                               related_name="deviceversion", db_index=False, db_column="configid")

    # foreignKey references;
    # configid = models.IntegerField(verbose_name="Device's Configuration Id", null=True, blank=True)

    # verbose_name="Device Version Code",
    versioncode = models.TextField(null=True, blank=True)
    # verbose_name = "Device's Parsed Version Name",
    parsedversionname = models.TextField(null=True, blank=True)
    # verbose_name = "Device Type",
    devicetype = models.TextField(null=True, blank=True)
    # verbose_name = "Parse Formula Code",
    parseformulcode = models.IntegerField(null=True, blank=True)

    objects = Manager()

    def __str__(self):
        return str(self.versioncode)

    class Meta:
        managed = False
        db_table = 'deviceversions'
        unique_together = (('versioncode', 'devicetype'),)
        ordering = ['versioncode', 'devicetype']


class DevLocationGroup(models.Model):
    """
    this database table keeps the location group information if exist
    """
    # verbose_name = 'Location Group Code',
    locationgroupcode = models.TextField(null=True, blank=True)
    # verbose_name = 'Location Group Name',
    locationgroupname = models.TextField(null=True, blank=True)

    objects = Manager()

    def __str__(self):
        return self.locationgroupname

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'devlocationgroup'
        ordering = ['locationgroupcode']


class DevLocations(models.Model):
    """
    This database table keeps location information of device if exist
    """
    locationGroup = models.ForeignKey(DevLocationGroup, verbose_name="Location Group", on_delete=models.CASCADE,
                                      related_name="locations", db_index=False, db_column="locationgroupid")

    # foreignKey references;
    # locationgroupid = models.IntegerField(verbose_name='Location Group ID', null=True, blank=True)

    # verbose_name = 'Location Code',
    locationcode = models.TextField(null=True, blank=True)
    locationname = models.TextField(verbose_name='Location Name', null=True, blank=True)

    objects = Manager()

    def __str__(self):
        return f"Location code : {self.locationcode} / name : {self.locationname}"

    def get_absolute_url(self):
        return reverse('inventories:location_detail', kwargs={'id': self.id})

    class Meta:
        managed = False
        db_table = 'devlocations'
        ordering = ['locationcode']


class DevicePasswordProfiles(models.Model):

    # verbose_name="Device Password Profile Code",
    passprofilecode = models.TextField(null=True, blank=True)
    # verbose_name="Device Password Profile Name",
    passprofilename = models.TextField(null=True, blank=True)
    # verbose_name="Device Password Community String",
    communitystring = models.TextField(null=True, blank=True)
    # verbose_name="Device SNMP V3 User",
    snmpv3user = models.TextField(null=True, blank=True)
    # verbose_name="Device SNMP V3 Authorization Pass",
    snmpv3authpass = models.TextField(null=True, blank=True)
    # verbose_name="Device SNMP V3 Authorization Protocol",
    snmpv3authprotocol = models.TextField(null=True, blank=True)
    # verbose_name="Device SNMP V3 Authorization Privacy Pass",
    snmpv3privacypass = models.TextField(null=True, blank=True)
    # verbose_name="Device SNMP V3 Authorization Privacy Protocol",
    snmpv3privacyprotocol = models.TextField(null=True, blank=True)
    # verbose_name="Device Telnet SSH User",
    telnetsshuser = models.TextField(null=True, blank=True)
    # verbose_name="Device Telnet SSH Password",
    telnetsshpass = models.TextField(null=True, blank=True)
    # verbose_name="Device Enable Password",
    enablepass = models.TextField(null=True, blank=True)

    objects = Manager()

    def __str__(self):
        return self.passprofilename

    class Meta:
        managed = False
        db_table = 'devicepasswordprofiles'
        ordering = ['passprofilecode']


class DeviceParserProfile(models.Model):

    parsername = models.TextField(null=True, blank=True)
    alternateparseid = models.IntegerField(null=True, blank=True)
    alternatecondition = models.TextField(blank=True, null=True)
    parsestatus = models.BooleanField(blank=True, null=True, default=True)

    tback = models.BooleanField(blank=True, null=True, default=False)  # True if traceback logs exists
    tbackdelim = models.TextField(blank=True, null=True)
    tbackdelimposition = models.IntegerField(null=True, blank=True)  # 0 for before & 1 for after
    delim = models.TextField(blank=True, null=True)
    delimposition = models.IntegerField(null=True, blank=True)  # 0 for before & 1 for after

    objects = Manager()

    def __str__(self):
        return self.parsername

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def get_alternative(self):
        """
        use to get alternative parser profile
        """
        if self.alternateparseid is not None:
            _alternative = DeviceParserProfile.objects.get(id=self.alternateparseid)
        else:
            _alternative = ""
        return _alternative

    def get_parser_rules(self):
        """
        use to get parser rules of current profile
        """
        try:
            _parser_rules = list(DeviceParserRules.objects.filter(parserProfile_id=self.id))
        except Exception as err:
            _parser_rules = []
        return _parser_rules

    class Meta:
        managed = False
        db_table = 'deviceparserprofile'
        ordering = ['-id']


class DeviceParserLogSeverity(models.Model):

    # verbose_name = "Parser Profile of Rules",
    parserProfile = models.ForeignKey(DeviceParserProfile, related_name="logSeverity", on_delete=models.CASCADE,
                                      db_index=False, db_column="parserprofileid")

    # foreignKey references;
    # parserprofileid = models.IntegerField(blank=True, null=True)

    # verbose_name = "Parser Log Code Severity",
    codeseverity = models.TextField(blank=True, null=True)
    # verbose_name = "Parser Log System Severity Code",
    systemseveritycode = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.systemseveritycode

    class Meta:
        managed = False
        db_table = 'deviceparserlogseverity'
        ordering = ['systemseveritycode']


class DeviceParserRules(models.Model):

    # verbose_name = "Parser Profile of Rules",
    parserProfile = models.ForeignKey(DeviceParserProfile, related_name="rules", on_delete=models.CASCADE,
                                      db_index=False, db_column="parserprofileid")

    # foreignKey references;
    # parserprofileid = models.IntegerField(blank=True, null=True)

    varname = models.TextField(blank=True, null=True)
    startpoint = models.TextField(blank=True, null=True)
    charcount = models.TextField(blank=True, null=True)
    vartype = models.TextField(blank=True, null=True)
    varformat = models.TextField(blank=True, null=True)
    staticval = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"{self.varname} start from : {self.startpoint} count of chars : {self.charcount} type : {self.vartype}"

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'deviceparserrules'
        unique_together = (('parserProfile_id', 'varname'),)
        ordering = ['id']


class DeviceProfileGroups(models.Model):

    # verbose_name = "Device Profile Location Group",
    locationGroup = models.ForeignKey(DevLocationGroup, on_delete=models.CASCADE, related_name="deviceProfile",
                                      db_index=False, db_column="locationgroupid")
    # verbose_name = "Device Profile Locations",
    location = models.ForeignKey(DevLocations, on_delete=models.CASCADE, related_name="deviceProfile", db_index=False,
                                 db_column="locationid")
    # verbose_name = "Device Profile Configuration Info",
    configProfile = models.ForeignKey(DeviceConfigProfile, on_delete=models.CASCADE, related_name="deviceProfile",
                                      db_index=False, db_column="confprofileid")
    # verbose_name = "Device Password Profile",
    passProfile = models.ForeignKey(DevicePasswordProfiles, on_delete=models.CASCADE, related_name="deviceProfile",
                                    db_index=False, db_column="passprofileid")
    # verbose_name = "Device Parser Profile",
    parserProfile = models.ForeignKey(DeviceParserProfile, on_delete=models.CASCADE, related_name="deviceProfile",
                                      db_index=False, db_column="parseprofileid")

    # foreignKey references;
    # passprofileid = models.IntegerField(verbose_name="Device Profile Location Group Pass Profile Id",
    #                                     null=True, blank=True)
    # locationgroupid = models.IntegerField(verbose_name="Device Profile Location Group Id", null=True, blank=True)
    # locationid = models.IntegerField(verbose_name="Device Profile Location Id", null=True, blank=True)
    # confprofileid = models.IntegerField(verbose_name="Device Profile Conf Profile Id", null=True, blank=True)
    # parseprofileid = models.IntegerField(verbose_name="Device Profile Parse Profile Id", null=True, blank=True)

    # verbose_name = "Device Profile Location Group Code",
    groupcode = models.TextField(null=True, blank=True)
    # verbose_name = "Device Profile Location Group Name",
    groupname = models.TextField(null=True, blank=True)
    # verbose_name = "Device Profile Parse Status",
    parsestatus = models.BooleanField(default=False, null=True, blank=True)

    objects = Manager()

    def __str__(self):
        return f"Device profile group - name : {self.groupname} / code : {self.groupcode}"

    class Meta:
        managed = False
        db_table = 'deviceprofilegroups'
        ordering = ['groupname', 'locationGroup_id']


class DeviceMac(models.Model):
    """
    This database table keeps mac addresses of devices with device model type and p, d, q values
    """
    #  verbose_name="Device Unique ID",
    uniqueid = models.TextField(primary_key=True, unique=True, blank=True)
    # verbose_name="Order P Value",
    orderpval = models.IntegerField(blank=True, null=True)
    # verbose_name="Order D Value",
    orderdval = models.IntegerField(blank=True, null=True)
    # verbose_name="Order Q Value",
    orderqval = models.IntegerField(blank=True, null=True)
    # verbose_name="Device Model Type",
    modeltype = models.IntegerField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.uniqueid

    def simplified_mac(self):
        return str.replace(f'{self.uniqueid}', ':', '')  # need to mac without ':' for log and anomaly tables

    class Meta:
        managed = False
        db_table = 'devicemac'
        ordering = ['uniqueid']


class DeviceTypeList(models.Model):
    """
    this database table keeps device types in system
    """
    # verbose_name = "Device's Type",
    devicetype = models.TextField(blank=True, null=True)
    # verbose_name = "Device's Type Code",
    devicetypecode = models.TextField(blank=True, null=True)
    # verbose_name = "Device's Up Version",
    upversion = models.TextField(blank=True, null=True)
    # verbose_name = "Device's Up Subversion",
    upsubversion = models.IntegerField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.devicetype

    class Meta:
        managed = False
        db_table = 'devicetypelist'
        ordering = ['devicetype', 'upversion', 'upsubversion']


class DeviceLogInterval(models.Model):

    # id = models.BigAutoField(primary_key=True)
    timeepoch = models.BigIntegerField(blank=True, null=True)
    intervalval = models.IntegerField(blank=True, null=True)
    uniqueid = models.TextField(blank=True, null=True)  # simlifiedMac if mac address
    timestart = models.DateTimeField(blank=True, null=True)
    logcount = models.IntegerField(blank=True, null=True)
    prediction = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    lowerbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    upperbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    modeltype = models.IntegerField(blank=True, null=True)
    deviceip = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return str(self.intervalval)

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def model_type_name(self):
        type_name = None
        if self.modeltype == 1:
            type_name = "Continuous"
        elif self.modeltype == 2:
            type_name = "Sparse"

        return type_name

    class Meta:
        managed = False
        db_table = 'deviceloginterval'
        unique_together = (('timeepoch', 'intervalval', 'uniqueid'),)
        ordering = ['id']


class EnterpriseSnmpIds(models.Model):

    # id = models.BigAutoField(primary_key=True)

    # verbose_name="Enterprise (Trade Mark) Brand Id",
    brandid = models.BigIntegerField(blank=True, null=True)
    # verbose_name="Enterprise Id",
    enterpriseid = models.IntegerField(unique=True, blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return str(self.enterpriseid)

    class Meta:
        managed = False
        db_table = 'enterprisesnmpids'
        ordering = ['enterpriseid']


class EnterpriseModelOIDs(models.Model):

    # verbose_name = "Enterprise Id",
    enterpriseid = models.ForeignKey(EnterpriseSnmpIds, to_field="enterpriseid", on_delete=models.CASCADE,
                                     related_name="modelOIDS", db_index=False, db_column="enterpriseid")

    # foreignKey references;
    # enterpriseid = models.TextField(verbose_name="Enterprise Id", blank=True, null=True)

    # verbose_name = "OID data",
    oid = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.oid

    class Meta:
        managed = False
        db_table = 'enterprisemodeloids'
        ordering = ['oid']


class Localization(models.Model):

    # id = models.BigAutoField(primary_key=True)

    # verbose_name = "Country Code",
    localekod = models.CharField(max_length=6, blank=True, null=True)
    # verbose_name = "Message Position Code",
    messagekod = models.CharField(max_length=50, blank=True, null=True)
    # verbose_name = "Message Text Content",
    messagelang = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.messagelang

    class Meta:
        managed = False
        db_table = 'localizasyon'
        ordering = ['localekod', 'messagelang']


class ServiceDevice(models.Model):

    # id = models.BigAutoField(primary_key=True)
    servicetype = models.CharField(verbose_name="Device Service Type", unique=True, max_length=6, blank=True, null=True)
    serveripaddress = models.TextField(verbose_name="Server Ip Address", unique=True, blank=True, null=True)
    domainname = models.TextField(verbose_name="Server Domain Name", blank=True, null=True)
    macaddress = models.TextField(verbose_name="Device MAC Address", blank=True, null=True)  # ?????????????????????
    # verbose_name = "Device Model Type",
    modeltype = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order P Value",
    orderpval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order D Value",
    orderdval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order Q Value",
    orderqval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Device Authorization Type",
    authtype = models.TextField(blank=True, null=True)
    servicestatus = models.CharField(verbose_name="Service Status", max_length=3, blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.servicetype

    class Meta:
        managed = False
        db_table = 'servicedevice'
        ordering = ['servicetype', 'serveripaddress', 'modeltype']


class ServiceDeviceDetails(models.Model):

    # verbose_name = "Service Device",
    serviceDevice = models.ForeignKey(ServiceDevice, related_name="details",
                                      on_delete=models.CASCADE, db_index=False, db_column="servicedeviceid")

    # foreignkey references;
    # servicedeviceid = models.BigIntegerField(blank=True, null=True)

    # verbose_name="User Information",
    raduser = models.TextField(blank=True, null=True)
    # verbose_name="User Pass Information",
    radpass = models.TextField(blank=True, null=True)
    # verbose_name="Auth Method",
    radmethod = models.TextField(blank=True, null=True)
    # verbose_name = "Device Model Type",
    modeltype = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order P Value",
    orderpval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order D Value",
    orderdval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order Q Value",
    orderqval = models.IntegerField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return str(self.modeltype)

    class Meta:
        managed = False
        db_table = 'servicedevicedetails'
        ordering = ['modeltype']


class NetworkParameters(models.Model):

    # verbose_name="Network Name",
    networkname = models.TextField(unique=True, blank=True, null=True)
    # verbose_name="Network IP Address",
    ipaddress = models.TextField(blank=True, null=True)
    # verbose_name="Sub Network Mask",
    subnetmask = models.IntegerField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.networkname

    def get_absolute_url(self):
        return reverse('inventories:network_detail', kwargs={'id': self.id})

    class Meta:
        managed = False
        db_table = 'networkparameters'
        ordering = ['-id', 'networkname', 'ipaddress']


class VirtualDeviceParameters(models.Model):

    # verbose_name = "Virtual Device Type",
    devicetype = models.TextField(blank=True, null=True)
    # verbose_name = "Virtual Device First OID Part",
    firstoidpart = models.TextField(blank=True, null=True)
    # verbose_name = "Virtual Device Last OID Part",
    lastoidpart = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.devicetype

    class Meta:
        managed = False
        db_table = 'virtualdeviceparams'
        ordering = ['devicetype', 'firstoidpart', 'lastoidpart']


class Logs(models.Model):
    # id = models.BigAutoField(primary_key=True)

    # verbose_name = "Socket Address (IP and PORT)",
    socketaddress = models.TextField(blank=True, null=True)
    # verbose_name = "Inet (IP) Address",
    inetaddress = models.TextField(blank=True, null=True)
    # verbose_name = "Log Data",
    logdata = models.TextField(blank=True, null=True)
    # verbose_name = "Port information",
    port = models.CharField(max_length=50, blank=True, null=True)
    # verbose_name = "Creation Date",
    olusturmatarih = models.DateTimeField(blank=True, null=True)
    # verbose_name = "Status",
    durum = models.BooleanField(blank=True, null=True)
    # verbose_name = "Log Id",
    logid = models.CharField(max_length=40, blank=True, null=True)
    # verbose_name = "Log Date Information",
    logdate = models.DateTimeField(blank=True, null=True)
    # verbose_name = "Name of Device",
    devicename = models.TextField(max_length=50, blank=True, null=True)
    # verbose_name = "Log Service Number",
    logserviceno = models.TextField(blank=True, null=True)
    # verbose_name = "Severity of Log",
    severity = models.CharField(max_length=40, blank=True, null=True)
    # verbose_name = "Log Event",
    logevent = models.TextField(blank=True, null=True)
    # verbose_name = "Log Number",
    logno = models.TextField(blank=True, null=True)
    # verbose_name = "Log Service",
    logservice = models.TextField(blank=True, null=True)
    # verbose_name = "Log Classification Group",
    classificationgroup = models.TextField(blank=True, null=True)
    # verbose_name = "Record Status",
    recstatus = models.SmallIntegerField(blank=True, null=True)
    # verbose_name = "Log JSON file",
    logjson = models.TextField(blank=True, null=True)  # field type is json in database.
    # verbose_name = "Recording Error",
    recerror = models.TextField(blank=True, null=True)
    # verbose_name = "Try JSON",
    tryjson = models.IntegerField(blank=True, null=True)
    mappedlogsource = models.TextField(blank=True, null=True)

    mline = models.IntegerField(null=True, blank=True, default=0)  # 0 for multiline False & 1 for multiline True

    objects = Manager()

    def __str__(self):
        return self.logdata

    def get_absolute_url(self):
        return reverse('inventories:log_detail', kwargs={'id': self.id})

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                elif type(value) is datetime.datetime:
                    data[field.name] = datetime.datetime.strftime(value, '%Y-%m-%d %H:%M:%S')
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def get_logsource(self):
        _logsurce = None
        if self.mappedlogsource:
            try:
                _logsurce = NetworkDevice.objects.get(uniqueid=self.mappedlogsource)
            except MultipleObjectsReturned:
                logger.warning(f"More than one log source found with uniqueid {self.mappedlogsource}")
            except ObjectDoesNotExist:
                logger.warning(f"No log source found with uniqueid {self.mappedlogsource}")
            except Exception as err:
                logger.warning(f"An error occurred with uniqueid {self.mappedlogsource}. ERROR IS : {err}")
        return _logsurce

    class Meta:
        managed = False
        db_table = 'loglar'
        ordering = ['-olusturmatarih', '-id']


class LogDefinitions(models.Model):

    definitioncode = models.IntegerField(verbose_name="Log Definition Unique Code", primary_key=True, unique=True)  # anomalies using it
    definitionname = models.TextField(verbose_name="Log Definition Name", blank=True, null=True)
    logcodeaccept = models.TextField(verbose_name="Log Accept Code", blank=True, null=True)
    shortcode = models.TextField(blank=True, null=True)
    logcodedelete = models.TextField(verbose_name="Log Delete Code", blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.definitionname

    def get_absolute_url(self):
        return reverse('logdefdetails_analysis', kwargs={'id': self.definitioncode})

    class Meta:
        managed = False
        db_table = 'logdefinitions'
        ordering = ['shortcode']


class LogDeviceGroup(models.Model):
    # id = models.BigAutoField(primary_key=True)

    # verbose_name = "Log Number",
    logno = models.TextField(blank=True, null=True)
    # verbose_name = "Device's MAC Address",
    uniqueid = models.TextField(blank=True, null=True)
    # verbose_name = "Model Type Id?",
    modeltype = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order D Value",
    orderdval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order P Value",
    orderpval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order Q Value",
    orderqval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Log Group Time Interval",
    loggroupinterval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Log Status is Active or Not",
    statusactive = models.BooleanField(blank=True, null=True)
    # verbose_name = "Count of Zeros"
    kdezero = models.TextField(blank=True, null=True)
    # verbose_name = "Count of Non Zeros"
    kdenonzero = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"form uniqueid : {self.uniqueid} log code : {self.logno}"

    class Meta:
        managed = False
        db_table = 'logdevicegroup'
        unique_together = (('logno', 'uniqueid'),)
        ordering = ['uniqueid']


class LogDefinitionDetails(models.Model):
    # id = models.BigAutoField(primary_key=True)s

    # foreignkey definitions;
    # logCode = models.ForeignKey(LogDefinitions, verbose_name="Log Code", related_name="definitionDetails",
    #                             on_delete=models.CASCADE,db_index=False,to_field="definitioncode",db_column="logcode")
    # verbose_name = "Log Definition Code Like ID",
    logDefCode = models.ForeignKey(LogDefinitions, db_index=False, related_name="definitionDetails",
                                   db_column="logdefcode", on_delete=models.CASCADE)

    # foreignkey references;
    # verbose_name = "Log Code",
    logcode = models.TextField(blank=True, null=True)
    # logdefcode = models.IntegerField(verbose_name="Log Definition Code Like ID", blank=True, null=True)  #anomalies will be table using it

    # verbose_name = "Log Structures",
    logstructs = models.TextField(blank=True, null=True)
    # verbose_name = "Logs ARR",
    logsarr = ArrayField(models.TextField(blank=True, null=True))
    # verbose_name = "Output Class Type",
    outclasstype = models.TextField(blank=True, null=True)
    # verbose_name = "Log Sub Definition Code",
    logsubdefcode = models.IntegerField(blank=True, null=True)
    # verbose_name = "Log Fields",
    logfields = ArrayField(models.TextField(blank=True, null=True))
    # verbose_name = "Is User Disabled?",
    userdisabled = models.BooleanField(blank=True, null=True, default=False)
    # verbose_name = "Log Protocol Relations",
    protocolrelation = ArrayField(models.TextField(blank=True, null=True))
    # verbose_name = "Log Deamon Relations",
    daemonrelation = models.TextField(blank=True, null=True)
    # verbose_name = "Is Parameters Valid?",
    paramsvalid = models.BooleanField(blank=True, null=True, default=False)
    # verbose_name = "Is System Log Defined?",
    systemlogdef = models.BooleanField(blank=True, null=True, default=False)
    # verbose_name = "Log Definitions",
    logdefs = ArrayField(models.TextField(blank=True, null=True))
    # verbose_name = "Is Auto Parameter Assigned?",
    autoparam = models.BooleanField(blank=True, null=True, default=False)

    objects = Manager()

    def __str__(self):
        return str(self.logstructs)

    def get_absolute_url(self):
        return reverse('logdefdetails_configure', kwargs={'id': self.id})

    def get_edit_url(self):
        return reverse('logdefdetails_edit', kwargs={'id': self.id})

    def get_logdefs(self):
        _defs_list = [json.loads(_) for _ in self.logdefs] if self.logdefs else []
        for _ in _defs_list:
            if "s" in _ and _["s"] == "":
                _["s"] = " "
        return _defs_list

    class Meta:
        managed = False
        db_table = 'logdefdetails'
        unique_together = (('logDefCode_id', 'logcode', 'logsubdefcode'),)
        ordering = ['-id', 'logcode', 'logsubdefcode']
        # constraints = ['logcode', 'logsubdefcode']
        # constraints = []


class LogCluster(models.Model):
    # id = models.BigAutoField(primary_key=True)

    # verbose_name = "Log Clustering Text",
    clustertext = models.TextField(blank=True, null=True)
    # verbose_name = "Added Logs",
    addedlogs = models.TextField(blank=True, null=True)
    # verbose_name = "Log Priority Information",
    logpriority = models.TextField(blank=True, null=True)
    # verbose_name = "Log Definition Number",
    logdefno = models.IntegerField(blank=True, null=True)
    # verbose_name = "Device or User Parse",
    devoruserparse = models.TextField(blank=True, null=True)
    # verbose_name = "Parser Formula Code",
    parseformulcode = models.IntegerField(blank=True, null=True)
    # verbose_name = "Added Log Counts",
    addedlognos = models.TextField(blank=True, null=True)
    # verbose_name = "SMLR Rate Number",
    smlrrates = models.TextField(blank=True, null=True)
    # verbose_name = "Parsed Word Count",
    wordcnt = models.IntegerField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.clustertext

    class Meta:
        managed = False
        db_table = 'logcluster'
        ordering = ['logpriority', 'logdefno', 'wordcnt']


class PParseFormulaCode(models.Model):

    id = models.IntegerField(primary_key=True, db_column='parseformulkod')
    parsername = models.TextField(blank=True, null=True, db_column='formulname')
    alternateparseid = models.IntegerField(blank=True, null=True)
    alternatecondition = models.TextField(blank=True, null=True)

    tback = models.BooleanField(blank=True, null=True, default=False)  # True if traceback logs exists
    tbackdelim = models.TextField(blank=True, null=True)
    tbackdelimposition = models.IntegerField(null=True, blank=True)
    delim = models.TextField(blank=True, null=True)  # if not null some logs can be multiline
    delimposition = models.IntegerField(null=True, blank=True)  # 0 for before & 1 for after

    objects = Manager()

    def __str__(self):
        return self.parsername

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def get_alternative(self):
        """
        use to get alternative parser formula
        """
        if self.alternateparseid is not None:
            _alternative = PParseFormulaCode.objects.get(id=self.alternateparseid)
        else:
            _alternative = ""
        return _alternative

    def get_parser_rules(self):
        """
        use to get parser rules of current formula
        """
        try:
            _parser_rules = list(LogRules.objects.filter(parserProfile_id=self.id))
        except Exception as err:
            _parser_rules = []
        return _parser_rules

    class Meta:
        managed = False
        db_table = 'pparseformulkod'
        ordering = ['-id']


class LogRules(models.Model):
    # id = models.BigAutoField(primary_key=True)

    parserProfile = models.ForeignKey(PParseFormulaCode, related_name="rules", on_delete=models.CASCADE,
                                      db_index=False, db_column="parseformulkod", to_field='id')
    # parseformulkod = models.IntegerField(blank=True, null=True)

    startpoint = models.TextField(blank=True, null=True, db_column='basla')
    charcount = models.TextField(blank=True, null=True, db_column='karaktersay')
    vartype = models.CharField(max_length=40, blank=True, null=True, db_column='tur')
    varformat = models.CharField(max_length=40, blank=True, null=True, db_column='format')
    varname = models.CharField(max_length=40, blank=True, null=True, db_column='degisken')
    staticval = models.CharField(max_length=40, blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"{self.varname}"

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'logkural'
        # unique_together = (('parseformulkod', 'degisken'),)
        # ordering = ['parseformulkod', 'degisken', 'tur']
        unique_together = (('parserProfile_id', 'varname'),)
        ordering = ['parserProfile_id', 'varname', 'vartype']


class LogInterval(models.Model):
    # id = models.BigAutoField(primary_key=True)
    logdevicegroupid = models.BigIntegerField(blank=True, null=True)
    timeepoch = models.BigIntegerField(blank=True, null=True)
    intervalval = models.IntegerField(blank=True, null=True)
    timestart = models.DateTimeField(blank=True, null=True)
    logcount = models.IntegerField(blank=True, null=True)
    prediction = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    lowerbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    upperbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    modeltype = models.IntegerField(blank=True, null=True)
    kdezero = models.TextField(blank=True, null=True)
    kdenonzero = models.TextField(blank=True, null=True)
    excessmedian = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    fqmedian = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return str(self.intervalval)

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def model_type_name(self):
        type_name = None
        if self.modeltype == 1:
            type_name = "Continuous"
        elif self.modeltype == 2:
            type_name = "Sparse"

        return type_name


    class Meta:
        managed = False
        db_table = 'loginterval'
        unique_together = (('timeepoch', 'intervalval', 'logdevicegroupid'),)
        ordering = ['timeepoch']


class LogDeviceParameters(models.Model):
    # id = models.BigAutoField(primary_key=True)

    uniqueid = models.TextField(blank=True, null=True)  # needs simplifiedMac
    parametername = models.TextField(blank=True, null=True)  # it's using another table, unique together wit devicemac
    modeltype = models.IntegerField(blank=True, null=True)
    orderdval = models.IntegerField(blank=True, null=True)
    orderpval = models.IntegerField(blank=True, null=True)
    orderqval = models.IntegerField(blank=True, null=True)
    loggroupinterval = models.IntegerField(blank=True, null=True)
    statusactive = models.BooleanField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.parametername

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'logdeviceparameter'
        unique_together = (('parametername', 'uniqueid'),)


class LogParameterValues(models.Model):
    # id = models.BigAutoField(primary_key=True)

    logdefcode = models.IntegerField(blank=True, null=True)
    logcode = models.TextField(blank=True, null=True)
    logsubdefcode = models.IntegerField(blank=True, null=True)
    logfieldsid = models.IntegerField(blank=True, null=True)
    paramvals = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.paramvals

    class Meta:
        managed = False
        db_table = 'logparamvals'
        unique_together = (('logdefcode', 'logcode', 'logsubdefcode', 'logfieldsid'),)
        ordering = ['logdefcode', 'logcode']


class LogSeverityTypes(models.Model):

    parseformulacode = models.IntegerField(blank=True, null=True)
    parsecodeseverity = models.TextField(blank=True, null=True)
    systemseveritycode = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.systemseveritycode

    class Meta:
        managed = False
        db_table = 'logseveritytypes'
        unique_together = (('parseformulacode', 'parsecodeseverity'),)
        ordering = ['parseformulacode', 'parsecodeseverity', 'systemseveritycode']


class ServiceLogInterval(models.Model):
    # id = models.BigAutoField(primary_key=True)
    timeepoch = models.BigIntegerField(blank=True, null=True)
    intervalval = models.IntegerField(blank=True, null=True)
    macaddress = models.TextField(blank=True, null=True)  # ????????????????????????????????????????????????
    timestart = models.DateTimeField(blank=True, null=True)
    servicetime = models.IntegerField(blank=True, null=True)
    prediction = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    lowerbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    upperbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    modeltype = models.IntegerField(blank=True, null=True)
    deviceip = models.TextField(blank=True, null=True)
    servauthtype = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return str(self.intervalval)

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'serviceloginterval'


class SystemLogFacilities(models.Model):
    """
    This table contains System Log Facility labels (facilityname), short names (facilitykeyword),
    showing status (status) in atibadash.
    If status false facility row in system configuration disappear, and all related show settings set as false
    """
    # verbose_name = "Facility Keyword Information",
    facilitykeyword = models.TextField(blank=True, null=True)
    # verbose_name = "Facility Name Information",
    facilityname = models.TextField(blank=True, null=True)
    # verbose_name = "Facility Status",
    status = models.BooleanField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"{self.facilityname} ({self.facilitykeyword}) "

    class Meta:
        managed = False
        db_table = 'syslogfacilities'
        ordering = ['id']


class Anomalies(models.Model):
    """
    Basic anomaly table of atiba
    """
    # id = models.BigAutoField(primary_key=True)
    uniqueid = models.CharField(max_length=40, blank=True, null=True)  # it was devicemacid before
    deviceip = models.CharField(max_length=40, blank=True, null=True)
    # deviceip column : networkdevice table deviceip column if anomalytype != 1201, 1301, if anomalytype ==1202
    # logdevicegroup table id column, if anomalytype ==1301 logdeviceparameter table id column
    # verbose_name = "Log Definition Code Like ID",
    logdefcode = models.IntegerField(blank=True, null=True)  # logdefdetails table logcode column NOT UNIQUE
    logcode = models.TextField(blank=True, null=True)  # logdefinitions table definitioncode column  # NOT UNIQUE
    anomalytype = models.IntegerField(blank=True, null=True)  # AnomalyAbnormalLogs using it
    credate = models.DateTimeField(blank=True, null=True)
    logdatestart = models.DateTimeField(blank=True, null=True)
    logdateend = models.DateTimeField(blank=True, null=True)
    logid = models.BigIntegerField(blank=True, null=True)
    status = models.CharField(verbose_name="Anomaly Status", max_length=3, blank=True, null=True)  # 000 open 001 closed
    logevent = models.TextField(blank=True, null=True)
    anomalycount = models.IntegerField(verbose_name="Count of Anomalies", blank=True, null=True)
    logids = ArrayField(models.IntegerField(blank=True, null=True))  # source : ElasticSearch
    prediction = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    lowerbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    upperbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    modeltype = models.IntegerField(blank=True, null=True)
    anomalyscore = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    servauthtype = models.TextField(blank=True, null=True)
    analyzedstatus = models.IntegerField(blank=True, null=True)
    # exact unique id of logsource to connect directly LogSources or NetworkDevice objects
    lsuniqueid = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"ID: {self.id} type : {self.anomalytype}, created at : {self.credate}, log code : {self.logcode}, " \
               f"COUNT : {self.anomalycount}, device ip : {self.deviceip}."

    def get_absolute_url(self):
        return reverse('AgentRoot:anomalies_detail_monitor', kwargs={'id': self.id})

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                elif type(value) is decimal.Decimal:
                    data[field.name] = float(value)
                elif type(value) is datetime.datetime:
                    data[field.name] = value.strftime("%Y/%m/%d %H:%M:%S.%f")
                elif type(value) is datetime.time:
                    data[field.name] = value.strftime("%H:%M:%S.%f")
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def get_type_definition(self):
        """
        provides you the type definition sentence of anomaly
        """
        try:
            _definition = GeneralParameterDetail.objects.filter(kisakod="ANMLTYPE").get(kod=self.anomalytype).kisaack
        except Exception as err:
            _definition = f"couldn't get any definition for : {self.anomalytype} because of {err}"
        return str(_definition)

    def get_device(self):
        """
        provides you the device that detected anomaly
        """
        _deviceUniqueID = self.lsuniqueid
        _device = LogSources()
        _device.uniqueid = "NO DEVICE"
        if _deviceUniqueID:
            try:
                _device = NetworkDevice.objects.get(uniqueid=_deviceUniqueID)
            except ObjectDoesNotExist:
                try:
                    _device = NetworkDevice.objects.get(sourcename=_deviceUniqueID)
                except Exception as err:
                    logger.warning(f"No Log Source record for anomaly with id {self.id} with lsuniqueid {_deviceUniqueID}")
            except Exception as err:
                logger.warning(f"No Log Source record for anomaly with id {self.id} with lsuniqueid {_deviceUniqueID}")
        else:
            if self.anomalytype in [1, 2, 3]:
                try:
                    _device = NetworkDevice.objects.get(uniqueid=self.uniqueid)
                except ObjectDoesNotExist:
                    _device = NetworkDevice.objects.get(deviceip=self.deviceip)
                except Exception as err:
                    _device = f"couldn't find device because {err}"
            elif self.anomalytype == 1101:
                try:
                    try:
                        _device = NetworkDevice.objects.get(
                            uniqueid=LogDeviceGroup.objects.get(id=self.uniqueid).uniqueid)
                    except ObjectDoesNotExist:
                        _device = NetworkDevice.objects.get(
                            uniqueid=simplified_to_mac(LogDeviceGroup.objects.get(id=self.uniqueid).uniqueid))
                except ObjectDoesNotExist:
                    try:
                        _device = NetworkDevice.objects.get(
                            uniqueid=LogDeviceParameters.objects.get(id=self.uniqueid).uniqueid)
                    except ObjectDoesNotExist:
                        _device = NetworkDevice.objects.get(
                            uniqueid=simplified_to_mac(LogDeviceParameters.objects.get(id=self.uniqueid).uniqueid))
                except Exception as err:
                    _device = f"couldn't find device because {err}"
            elif self.anomalytype in [1201, 1203, 1204]:
                try:
                    _device = NetworkDevice.objects.get(uniqueid=LogDeviceGroup.objects.get(id=self.uniqueid).uniqueid)
                except ObjectDoesNotExist:
                    _device = NetworkDevice.objects.get(
                        uniqueid=simplified_to_mac(LogDeviceGroup.objects.get(id=self.uniqueid).uniqueid))
                except Exception as err:
                    _device = f"couldn't find device because {err}"
            elif self.anomalytype in [1301, 1303, 1304, 1401]:
                try:
                    _device = NetworkDevice.objects.get(uniqueid=LogDeviceParameters.objects.get(id=self.uniqueid).uniqueid)
                except ObjectDoesNotExist:
                    _device = NetworkDevice.objects.get(
                        uniqueid=simplified_to_mac(LogDeviceParameters.objects.get(id=self.uniqueid).uniqueid))
                except Exception as err:
                    _device = f"couldn't find device because {err}"
        return _device

    def get_anomaly_detail_data(self):
        """
        This method provides data that you need for graph based on anomaly types.
        :returns:
        for anomalytype 1, 2 nothing because no need to graph //
        for anomalytype 1201, 1301 a list of tuples which contains (timestart, lowerbound, logcount, upperbound) //
        for anomalytype 1203, 1204, 1303, 1304 a list of tuples which contains (timestart, lıogcount, kde)
        """
        _data_list = []
        if self.anomalytype == 1:  # New Behaviour
            pass
        elif self.anomalytype == 2:  # Critical Alert
            pass
        elif self.anomalytype == 3:  # Inf. Anomaly Beh.
            _detail = list(DeviceLogInterval.objects.filter(uniqueid=mac_to_simplified(self.uniqueid)).filter(
                timestart__lt=(self.logdateend + datetime.timedelta(hours=0.5))).filter(
                timestart__gt=(self.logdatestart - datetime.timedelta(hours=1))).order_by('timeepoch'))
            _data_list = [(_.timestart, _.lowerbound, _.logcount, _.upperbound) for _ in _detail if
                          (_.lowerbound and _.upperbound)]
        elif self.anomalytype == 1101:  # UDM Anomaly
            pass
        elif self.anomalytype == 1201:  # Log Behaviour Anomaly modeltype = 1
            _detail = list(LogInterval.objects.filter(logdevicegroupid=self.uniqueid).filter(
                timestart__lt=(self.logdateend + datetime.timedelta(hours=0.5))).filter(
                timestart__gt=(self.logdatestart - datetime.timedelta(hours=1))).order_by('timeepoch'))
            _data_list = [(_.timestart, _.lowerbound, _.logcount, _.upperbound) for _ in _detail if
                          (_.lowerbound and _.upperbound)]
        elif self.anomalytype == 1203:  # Log Excess Anomaly modeltype = 2
            _detail = list(LogInterval.objects.filter(logdevicegroupid=self.uniqueid).filter(
                timestart__lt=(self.logdateend + datetime.timedelta(hours=0.5))).filter(
                timestart__gt=(self.logdatestart - datetime.timedelta(hours=1))).order_by('timeepoch'))
            _data_list = [(_.timestart, _.logcount, _.kdenonzero) for _ in _detail]
        elif self.anomalytype == 1204:  # Log Frequency Anomaly modeltype = 2
            _detail = list(LogInterval.objects.filter(logdevicegroupid=self.uniqueid).filter(
                timestart__lt=(self.logdateend + datetime.timedelta(hours=0.5))).filter(
                timestart__gt=(self.logdatestart - datetime.timedelta(hours=1))).order_by('timeepoch'))
            _data_list = [(_.timestart, _.logcount, _.kdezero) for _ in _detail]
        elif self.anomalytype == 1301:  # Parameter Behaviour Anomaly modeltype = 1
            _detail = list(ParameterInterval.objects.filter(parameterdevicegroupid=self.uniqueid).filter(
                timestart__lt=(self.logdateend + datetime.timedelta(hours=0.5))).filter(
                timestart__gt=(self.logdatestart - datetime.timedelta(hours=1))).order_by('timeepoch'))
            _data_list = [(_.timestart, _.lowerbound, _.logcount, _.upperbound) for _ in _detail if
                          (_.lowerbound and _.upperbound)]
        elif self.anomalytype == 1303:  # Parameter Excess Anomaly modeltype = 2
            _detail = list(ParameterInterval.objects.filter(parameterdevicegroupid=self.uniqueid).filter(
                timestart__lt=(self.logdateend + datetime.timedelta(hours=0.5))).filter(
                timestart__gt=(self.logdatestart - datetime.timedelta(hours=1))).order_by('timeepoch'))
            _data_list = [(_.timestart, _.logcount, _.kdenonzero) for _ in _detail]
        elif self.anomalytype == 1304:  # Parameter Frequency Anomaly modeltype = 2
            _detail = list(ParameterInterval.objects.filter(parameterdevicegroupid=self.uniqueid).filter(
                timestart__lt=(self.logdateend + datetime.timedelta(hours=0.5))).filter(
                timestart__gt=(self.logdatestart - datetime.timedelta(hours=1))).order_by('timeepoch'))
            _data_list = [(_.timestart, _.logcount, _.kdezero) for _ in _detail]
        elif self.anomalytype == 1401:  # Gauge parameter Anomaly modeltype = 1
            _detail = list(ParameterInterval.objects.filter(parameterdevicegroupid=self.uniqueid).filter(
                timestart__lt=(self.logdateend + datetime.timedelta(hours=0.5))).filter(
                timestart__gt=(self.logdatestart - datetime.timedelta(hours=1))).order_by('timeepoch'))
            _data_list = [(_.timestart, _.lowerbound, _.logcount, _.upperbound) for _ in _detail if
                          (_.lowerbound and _.upperbound)]
        else:
            pass
        logger.warning(f"Detail data for anomaly with id {self.id} : {_data_list}")
        return _data_list

    def get_simple_chart_data(self):
        _data_list = self.get_anomaly_detail_data()
        _currents = None
        _label = []
        _data = []
        if self.anomalytype in [1203, 1204, 1303, 1304]:
            for _ in _data_list:
                # _label.append(_[0].strftime("%d-%b-%H:%M"))
                _data.append(_[1])
                if _[0] == self.logdatestart:
                    # _currents = (_[0].strftime("%d-%b-%H:%M"), _[1])
                    _label.append("Alert")
                    _currents = ("Alert", _[1])
                else:
                    _label.append("-")
        elif self.anomalytype in [3, 1201, 1301, 1401]:
            for _ in _data_list:
                # _label.append(_[0].strftime("%d-%b-%H:%M"))
                _data.append(_[2])
                if _[0] == self.logdatestart:
                    # _currents = (_[0].strftime("%d-%b-%H:%M"), _[2])
                    _label.append("Alert")
                    _currents = ("Alert", _[2])
                else:
                    _label.append("-")
        # elif self.anomalytype in [1, 2, 1101]:
        else:
            _label = ["-"]*18
            _data = [0]*18
            _label[11] = "Alert"
            _data[11] = self.anomalycount if self.anomalycount else 1
            _currents = (_label[11], _data[11])
        return [_label, _data, _currents]

    def get_anomaly_kde(self):
        """
        provides you the gaussian kde function of the anomaly detected (it returns for anomaly type models 2)
        """
        _kde_query_result = []
        _kde_json_text = None
        _kde = ""
        if self.anomalytype == 1203:
            try:
                _kde_query_result = list(LogInterval.objects.filter(logdevicegroupid=self.uniqueid).filter(timestart=self.logdatestart))
                if _kde_query_result:
                    _kde_json_text = _kde_query_result[0].kdenonzero
                    _kde = jsonpickle.decode(_kde_json_text, keys=True) if _kde_json_text else "Distribution Function Not Determined"
                else:
                    _kde = "Interval data not found, data may have been corrupted"
            except Exception as err:
                _kde = f"Error : {err}"
        elif self.anomalytype == 1204:
            try:
                _kde_query_result = list(LogInterval.objects.filter(logdevicegroupid=self.uniqueid).filter(timestart=self.logdatestart))
                if _kde_query_result:
                    _kde_json_text = _kde_query_result[0].kdezero
                    _kde = jsonpickle.decode(_kde_json_text, keys=True) if _kde_json_text else "Distribution Function Not Determined"
                else:
                    _kde = "Interval data not found, data may have been corrupted"
            except Exception as err:
                _kde = f"Error : {err}"
        elif self.anomalytype == 1303:
            try:
                _kde_query_result = list(ParameterInterval.objects.filter(parameterdevicegroupid=self.uniqueid).filter(timestart=self.logdatestart))
                if _kde_query_result:
                    _kde_json_text = _kde_query_result[0].kdenonzero
                    _kde = jsonpickle.decode(_kde_json_text, keys=True) if _kde_json_text else "Distribution Function Not Determined"
                else:
                    _kde = "Interval data not found, data may have been corrupted"
            except Exception as err:
                _kde = f"Error : {err}"
        elif self.anomalytype == 1304:
            try:
                _kde_query_result = ParameterInterval.objects.filter(parameterdevicegroupid=self.uniqueid).filter(timestart=self.logdatestart)
                if _kde_query_result:
                    _kde_json_text = _kde_query_result[0].kdezero
                    _kde = jsonpickle.decode(_kde_json_text, keys=True) if _kde_json_text else "Distribution Function Not Determined"
                else:
                    _kde = "Interval data not found, data may have been corrupted"
            except Exception as err:
                _kde = f"Error : {err}"
        return _kde

    def get_anomaly_parameter(self):
        """
        provides you the parameter with the anomaly detected
        """
        _parameterName = ""
        if self.anomalytype in [1301, 1302, 1303, 1304, 1401]:
            try:
                _parameterName = LogDeviceParameters.objects.get(id=self.uniqueid).parametername
            except Exception as err:
                _parameter = f"Couldn't get parameter name because {err}"
        return _parameterName

    def get_anomaly_parameter_and_values(self):
        """
        provides you the parameter and values with the anomaly detected
        """
        _parameterName = ""
        _parameterValues = []
        if self.anomalytype in [1301, 1302, 1303, 1304, 1401]:
            try:
                anomaly_parameter = AnomalyParameters.objects.values("id", "uniqueid").filter(
                    logcode=self.logcode, anomalytype=self.anomalytype,
                    logstartdate__gte=(self.logdatestart - datetime.timedelta(seconds=1)),
                    logenddate__lte=(self.logdateend + datetime.timedelta(seconds=1)))
                # logger.debug(f"Anomaly Parameters object for anomaly id {self.id} is : {anomaly_parameter}")
                if anomaly_parameter:
                    _parameterValues = list(
                        AnomalyParametersDetails.objects.values_list("paramval", flat=True).filter(
                            anomaly_id=anomaly_parameter[0]["id"],
                            uniqueid=anomaly_parameter[0]["uniqueid"],
                            logdatestart__gte=(self.logdatestart - datetime.timedelta(seconds=1)),
                            logdateend__lte=(self.logdateend + datetime.timedelta(seconds=1)),
                            paramfield=self.logcode))
                    if not _parameterValues:
                        _parameterValues = ["There is no dominant parameter value causing this anomaly"]
                    # logger.debug(f"Anomaly Parameter Details for anomaly id {self.id} is : {_parameterValues}")
            except Exception as err:
                logger.warning(
                    f"An error occurred trying to get anomaly parameter for anomaly id {self.id}. ERROR IS : {err}")

        return self.logcode, _parameterValues

    def define_anomaly(self):
        _definition = None
        if self.anomalytype == 2:
            # critical alerts
            _definition = f"Critical alert for log code {self.logcode}"
        if self.anomalytype == 1:
            # new behaviour
            _definition = f"This log has been seen for the first time in last {SystemParameters.objects.all()[0].newbehaviortime} days"
        if self.anomalytype == 1201:
            # log behavior anomaly
            _lower = int(round(float(self.lowerbound)*100)/100) if float(self.lowerbound) > 0 else 0
            _upper = int(round(float(self.upperbound)*100)/100) if float(self.upperbound) > 0 else 0
            if _lower == _upper:
                _definition = f"Count of logs are out of expected {_lower}"
            else:
                _definition = f"Count of logs are out of expected ({_lower} , {_upper}) bounds"
        if self.anomalytype == 1203:
            # log excess anomaly
            _definition = f"Unexpected excess of counts for log code {self.logcode}"

        if self.anomalytype == 1204:
            # log frequency anomaly
            _definition = f"Unexpected frequency change for log code {self.logcode}"

        if self.anomalytype == 1301:
            # parameter behaviour anomaly
            _parameter = self.get_anomaly_parameter()
            _lower = int(round(float(self.lowerbound) * 100) / 100) if float(self.lowerbound) > 0 else 0
            _upper = int(round(float(self.upperbound) * 100) / 100) if float(self.upperbound) > 0 else 0
            if _lower == _upper:
                _definition = f"Count of logs with {_parameter} parameter are out of expected {_lower}"
            else:
                _definition = f"Count of logs with {_parameter} parameter are out of expected ({_lower} , {_upper}) bounds"
        if self.anomalytype == 1303:
            # parameter excess anomaly
            _definition = f"Unexpected excess of counts for logs with {self.get_anomaly_parameter()} parameter."

        if self.anomalytype == 1304:
            # parameter frequency anomaly
            _definition = f"Unexpected frequency change for logs with {self.get_anomaly_parameter()} parameter."

        if self.anomalytype == 1401:
            # gauge parameter anomaly
            _parameter = self.get_anomaly_parameter()
            _lower = int(round(float(self.lowerbound) * 100) / 100) if float(self.lowerbound) > 0 else 0
            _upper = int(round(float(self.upperbound) * 100) / 100) if float(self.upperbound) > 0 else 0
            if _lower == _upper:
                _definition = f"Value of gauge parameter {_parameter} is out of expected {_lower}"
            else:
                _definition = f"Value of gauge parameter {_parameter} is out of expected ({_lower} , {_upper}) bounds"

        if self.anomalytype == 1101:
            # user defined metric anomaly
            _definition = f"Anomaly about UDM."
        return _definition

    def get_anomaly_logs(self):
        """To get AnomalyLogs record for this anomaly, returns a list of AnomalyLogs objects"""
        _max_record_count = 25
        _anomaly_logs = []
        if self.anomalytype in [1301, 1302, 1303, 1304, 1401]:
            _source_uniqueid = LogDeviceParameters.objects.get(id=self.uniqueid).uniqueid
            try:
                anomaly_parameter = AnomalyParameters.objects.values("id", "uniqueid").filter(
                    logcode=self.logcode, anomalytype=self.anomalytype,
                    logstartdate__gte=(self.logdatestart - datetime.timedelta(seconds=1)),
                    logenddate__lte=(self.logdateend + datetime.timedelta(seconds=1)))
                logger.debug(f"Anomaly Parameters object for anomaly id {self.id} is : {anomaly_parameter}")
                if anomaly_parameter:
                    _anomaly_parameter_detail_ids = list(
                        AnomalyParametersDetails.objects.values_list("id", flat=True).filter(
                            anomaly_id=anomaly_parameter[0]["id"],
                            uniqueid=anomaly_parameter[0]["uniqueid"],
                            logdatestart__gte=(self.logdatestart - datetime.timedelta(seconds=1)),
                            logdateend__lte=(self.logdateend + datetime.timedelta(seconds=1)),
                            paramfield=self.logcode))
                    logger.debug(f"Parameter detail ids for anomaly id {self.id}: {_anomaly_parameter_detail_ids}")
                    _anomaly_logs = list(
                        AnomalyLogs.objects.filter(
                            logid__in=_anomaly_parameter_detail_ids,
                            logstartdate__gte=(self.logdatestart - datetime.timedelta(seconds=1)),
                            logenddate__lte=(self.logdateend + datetime.timedelta(seconds=1)),
                            uniqueid=_source_uniqueid))
            except Exception as err:
                logger.exception(
                    f"An error occurred trying to get anomalylogs for anomaly with id {id}. ERROR IS : {err}")
        else:
            try:
                _anomaly_logs_count = AnomalyLogs.objects.filter(
                    logstartdate__gte=(self.logdatestart - datetime.timedelta(seconds=1)),
                    logenddate__lte=(self.logdateend + datetime.timedelta(seconds=1)), logcode=self.logcode).count()
                if 0 < _anomaly_logs_count < 5:
                    _anomaly_logs = list(
                        AnomalyLogs.objects.filter(
                            logstartdate__gte=(self.logdatestart - datetime.timedelta(seconds=1)),
                            logenddate__lte=(self.logdateend + datetime.timedelta(seconds=1)),
                            logcode=self.logcode))
                elif _anomaly_logs_count > 5:
                    _anomaly_logs = list(
                        AnomalyLogs.objects.filter(
                            logstartdate__gte=(self.logdatestart - datetime.timedelta(seconds=1)),
                            logenddate__lte=(self.logdateend + datetime.timedelta(seconds=1)),
                            logcode=self.logcode)[:_max_record_count])
                logger.info(f"AnomalyLogs count for {self.get_type_definition()} with id {self.id} : {_anomaly_logs_count}")
            except Exception as err:
                logger.exception(
                    f"An error occurred trying to get anomalylogs for anomaly with id {id}. ERROR IS : {err}")
        return _anomaly_logs

    def get_sparsity_data(self):
        _behaviour_type = "Not suitable type for a behavioral model"
        _list_of_counts = []
        _list_of_labels = []
        if self.anomalytype in [1301, 1302, 1303, 1304, 1401]:
            _list_of_counts = list(ParameterInterval.objects.values_list('logcount', flat=True).filter(parameterdevicegroupid=self.uniqueid, timestart__lt=(self.logdateend + datetime.timedelta(seconds=0.5))).order_by('-timeepoch')[:1024])
            _list_of_labels = list(ParameterInterval.objects.values_list('timestart', flat=True).filter(parameterdevicegroupid=self.uniqueid, timestart__lt=(self.logdateend + datetime.timedelta(seconds=0.5))).order_by('-timeepoch')[:1024])

        elif self.anomalytype in [1201, 1202, 1203, 1204]:
            _list_of_counts = list(LogInterval.objects.values_list('logcount', flat=True).filter(logdevicegroupid=self.uniqueid, timestart__lt=(self.logdateend + datetime.timedelta(seconds=0.5))).order_by('-timeepoch')[:1024])
            _list_of_labels = list(LogInterval.objects.values_list('timestart', flat=True).filter(logdevicegroupid=self.uniqueid, timestart__lt=(self.logdateend + datetime.timedelta(seconds=0.5))).order_by('-timeepoch')[:1024])

        elif self.anomalytype in [1101, 1102, 1103, 1104]:
            pass
        elif self.anomalytype == 3:
            _list_of_counts = list(DeviceLogInterval.objects.values_list('logcount', flat=True).filter(uniqueid=mac_to_simplified(self.uniqueid), timestart__lt=(self.logdateend + datetime.timedelta(seconds=0.5))).order_by('-timeepoch')[:1024])
            _list_of_labels = list(DeviceLogInterval.objects.values_list('timestart', flat=True).filter(uniqueid=mac_to_simplified(self.uniqueid), timestart__lt=(self.logdateend + datetime.timedelta(seconds=0.5))).order_by('-timeepoch')[:1024])

        # if clauses for model type info;
        if 0 < len(_list_of_counts) < 1024:
            _behaviour_type = "lack of data for modeling"
        elif len(_list_of_counts) == 1024:
            try:
                _list_mode = mode(_list_of_counts)
            except Exception as err:
                _list_mode = _list_of_counts[0]
                logger.warning(f"Couldn't get mode of count list. WARNING IS : {err}")
            if _list_mode == 0:
                _mode_count = _list_of_counts.count(_list_mode)
                # _mode_percentage = (round((_mode_count*100/len(_list_of_counts))*100))/100
                _mode_percentage = _mode_count * 100 / len(_list_of_counts)
                _behaviour_type = "Sparse" if _mode_percentage > 60 else "Continuous"
                _behaviour_type += f" ({round(_mode_percentage*100)/100} of data is 0)"
            else:
                _mode_count = _list_of_counts.count(_list_mode)
                _mode_percentage = (round((_mode_count*100/len(_list_of_counts))*100))/100
                # _mode_percentage = _mode_count * 100 / len(_list_of_counts)
                _behaviour_type = f"Continuous ({_mode_percentage} of data is {_list_mode})"

        # _list_of_labels = [datetime.datetime.strftime(_, "%Y-%m-%d--%H:%M") for _ in _list_of_labels]
        _list_of_labels = [datetime.datetime.strftime(_, "%d-%b-%H:%M") for _ in _list_of_labels]
        _list_of_labels.reverse()
        _list_of_counts.reverse()
        return [_behaviour_type, _list_of_labels, _list_of_counts]

    class Meta:
        managed = False
        db_table = 'anomalies'
        unique_together = (('uniqueid', 'logdefcode', 'logcode'), ('uniqueid', 'logevent'),)
        ordering = ['-logdateend', '-id']


class AnomalyAbnormalLogs(models.Model):
    """
    When detected log behaviour anomaly it means has anomaly type 1201, the operation continues in this database table
    """

    # id = models.BigAutoField(primary_key=True)
    locationGroupID = models.ForeignKey(DevLocationGroup, db_column="locationgroupid", db_index=False,
                                        on_delete=models.CASCADE, related_name="anomalyAbnormal")
    # foreignkey references;
    # locationgroupid = models.IntegerField(blank=True, null=True)  # devlocationgroup table id column

    uniqueid = models.TextField(blank=True, null=True)  # it was devicemac before
    logcode = models.TextField(blank=True, null=True)  # logdefdetails table logcode column
    anomalytype = models.IntegerField(blank=True, null=True)  # anomalies table anomaytype column
    credate = models.DateTimeField(blank=True, null=True)
    logevents = ArrayField(models.TextField(blank=True, null=True))
    logcredate = models.DateTimeField(blank=True, null=True)
    logstartdate = models.DateTimeField(blank=True, null=True)
    logenddate = models.DateTimeField(blank=True, null=True)
    analyzedstatus = models.IntegerField(blank=True, null=True)
    logtimeseries = ArrayField(models.IntegerField(blank=True, null=True))
    dateseries = ArrayField(models.BigIntegerField(blank=True, null=True))
    intervalval = models.IntegerField(blank=True, null=True)
    anomaliesid = models.IntegerField(blank=True, null=True)  # id of anomalies table it means alert about it

    objects = Manager()

    def __str__(self):
        return f"created at {self.logcredate} it start {self.logstartdate} & end {self.logenddate}"

    def get_device(self):
        try:
            _device = NetworkDevice.objects.get(uniqueid=self.uniqueid)
        except ObjectDoesNotExist:
            _device = f"No log source with Unique id {self.uniqueid}, it may have been changed"
            logger.warning(f"No log source with Unique id {self.uniqueid}, uniqueid of this log source may have been changed");
        except Exception as err:
            _device = f"Couldn't find device because {err}"
        return _device

    class Meta:
        managed = False
        db_table = 'anomalyabnormallogs'
        ordering = ['-logcredate']


class AnomalyLogs(models.Model):
    """
    This database table contains almost all abnormal logs. It keeps them with a lot of information together. Most of
    modules use this table.
    """
    # id = models.BigAutoField(primary_key=True)

    # foreignkey definitions;
    locationGroupId = models.ForeignKey(DevLocationGroup, db_column="locationgroupid", on_delete=models.CASCADE,
                                        db_index=False, related_name="anomalyLogs")

    # foreignkey references;
    # verbose_name = "Device IP Address",
    deviceip = models.TextField(blank=True, null=True)  # networkdevice table deviceip column
    # locationgroupid = models.IntegerField(blank=True, null=True)  # devlocationgroup table id column

    uniqueid = models.TextField(blank=True, null=True)  # it was devicemac before
    logcode = models.TextField(blank=True, null=True)  # logdefdetails table logcode column
    logid = models.BigIntegerField(blank=True, null=True)  # elasticsearch id
    credate = models.DateTimeField(blank=True, null=True)
    anomalytype = models.IntegerField(blank=True, null=True)
    logevent = models.TextField(blank=True, null=True)
    logcredate = models.DateTimeField(blank=True, null=True)
    analyzedstatus = models.IntegerField(blank=True, null=True)
    logtimeseries = ArrayField(models.IntegerField(blank=True, null=True))
    dateseries = ArrayField(models.BigIntegerField(blank=True, null=True))
    logparams = ArrayField(models.TextField(blank=True, null=True))
    causetimeseries = ArrayField(models.IntegerField(blank=True, null=True))
    logstartdate = models.DateTimeField(blank=True, null=True)
    logenddate = models.DateTimeField(blank=True, null=True)
    logtimes = ArrayField(models.DateTimeField(blank=True, null=True))
    paramvariable = models.TextField(blank=True, null=True)
    paramvalue = models.TextField(blank=True, null=True)
    logdefs = ArrayField(models.TextField(blank=True, null=True))
    logeventstruct = models.TextField(blank=True, null=True)
    noresolve = models.IntegerField(blank=True, null=True)
    aioutput = models.BooleanField(blank=True, null=True)
    aistatus = models.IntegerField(blank=True, null=True)
    isshow = models.BooleanField(blank=True, null=True)
    ttr = models.DateTimeField(blank=True, null=True)
    aiconfidence = models.FloatField(blank=True, null=True)
    aimetricscore = models.FloatField(blank=True, null=True)
    componentids = ArrayField(models.IntegerField(blank=True, null=True))
    applicationids = ArrayField(models.IntegerField(blank=True, null=True))
    logids = ArrayField(models.IntegerField(blank=True, null=True))  # elasticsearch ids
    anomaliesid = models.IntegerField(blank=True, null=True)  # id of anomalies table it means alert about it

    objects = Manager()

    def __str__(self):
        return f"ID: {self.id} - EVENT: {self.logevent}"

    def get_anomaly_logs_url(self):
        return reverse('inventories:anomaly_logs', kwargs={'id': self.id})

    # def get_absolute_url(self):
    #     return reverse('inventories:anomaly_detail', kwargs={'id': self.id})

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                elif type(value) is datetime.datetime:
                    data[field.name] = value.strftime("%Y/%m/%d %H:%M:%S")
                elif type(value) is datetime.time:
                    data[field.name] = value.strftime("%H:%M:%S")
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def general_info(self):
        _params = self.paramvariable if self.paramvariable else "No parameters"
        _paramvals = self.paramvalue if self.paramvalue else "No values"
        _logs_count = len(list(self.logids)) if self.logids else 1

        _info = {
            'ID No': self.id,
            'Log Event': self.logevent,
            'Log Code': self.logcode,
            'Log Source': self.uniqueid,
            'IP Address': self.deviceip,
            'Parameters': _params,
            'Parameter Values': _paramvals,
            'Log Time Series': self.logtimeseries,
            'Creation Date': self.credate,
            'Log Creation Date': self.logcredate,
            # 'Count of Logs': _logs_count
        }

        return _info

    # we get devices from LogSources class;
    def get_device(self):
        try:
            # device = self.deviceMac.devices.all()[0]
            device = LogSources.objects.get(uniqueid=self.uniqueid)
        except MultipleObjectsReturned:
            device = list(LogSources.objects.filter(uniqueid=self.uniqueid))[0]
        except ObjectDoesNotExist:
            device = f"No log source with Unique id {self.uniqueid}, it may have been changed"
            logger.warning(
                f"No log source with Unique id {self.uniqueid}, uniqueid of this log source may have been changed")
        except Exception as err:
            device = f"Error: couldn't find device {err}"
        return device

    def get_log_code(self):
        _code = str(self.logcode)
        try:
            if _code.index("ATIBA") > -1:
                log_code = ""
            else:
                log_code = _code.replace("<", "").replace(">", "")
        except Exception:
            log_code = _code.replace("<", "").replace(">", "")
        return log_code

    def get_type_definition(self):
        try:
            _definition = GeneralParameterDetail.objects.filter(kisakod="ANMLTYPE").get(kod=self.anomalytype).kisaack
        except Exception as err:
            _definition = f"couldn't get any definition for : {self.anomalytype} because of {err}"
        return _definition

    def define_incident(self):
        _definition = None
        if self.anomalytype == 2:
            # critical alerts
            _definition = f"Critical alert for log code {self.logcode}"

        if self.anomalytype == 1:
            # new behaviour
            _definition = f"This log has been seen for the first time in last {SystemParameters.objects.all()[0].newbehaviortime} days"

        if self.anomalytype == 1201:
            # log behavior anomaly
            _definition = f"Count of logs are out of expected boundaries"

        if self.anomalytype == 1203:
            # log excess anomaly
            _definition = f"Unexpected excess of counts for log code {self.logcode}"

        if self.anomalytype == 1204:
            # log frequency anomaly
            _definition = f"Unexpected frequency change for log code {self.logcode}"

        if self.anomalytype == 1301:
            # parameter behaviour anomaly
            _definition = f"Count of logs with {self.paramvariable} parameter are out of expected boundaries"
        if self.anomalytype == 1303:
            # parameter excess anomaly
            _definition = f"Unexpected excess of counts for logs with {self.paramvariable} parameter."

        if self.anomalytype == 1304:
            # parameter frequency anomaly
            _definition = f"Unexpected frequency change for logs with {self.paramvariable} parameter."

        if self.anomalytype == 1101:
            # user defined metric anomaly
            _definition = f"Anomaly about UDM."
        return _definition

    def get_rc_graphs(self):
        """to get RootCauseGraphDetails which are containing it in node lists"""
        _rc_graphs = []
        try:
            _rc_graphs = list(RootCauseGraphsDetails.objects.filter(nodelist__contains=[self.id], analyzedstatus=2))
            logger.info(f"list from RootCauseGraphDetails for AnomalyLogs with id : {self.id} -> {_rc_graphs}")
        except Exception as err:
            logger.exception(
                f"An error occurred trying to find RootCauseGraphDetails for id {self.id}. ERROR IS : {err}")
        return _rc_graphs

    def get_its_anomaly(self):
        _anomaly = []
        if self.anomaliesid:
            _anomaly = [Anomalies.objects.get(id=self.anomaliesid)]
            logger.debug(f"anomalylogs id {self.id} anomalies id {self.anomaliesid} anomaly : {_anomaly}")
            return _anomaly
        _anomaly_type = self.anomalytype
        if _anomaly_type in [1301, 1302, 1303, 1304]:
            _anomaly = list(Anomalies.objects.filter(
                logcode=self.paramvariable,
                logdatestart__lte=(self.logstartdate + datetime.timedelta(seconds=1)),
                logdateend__gte=(self.logenddate - datetime.timedelta(seconds=1))))
        # elif _anomaly_type in [1201, 1202, 1203, 1204]:
        #     _anomaly = list(Anomalies.objects.filter(
        #         logcode=self.logcode,
        #         logdatestart__lte=(self.logstartdate + datetime.timedelta(seconds=1)),
        #         logdateend__gte=(self.logenddate - datetime.timedelta(seconds=1))))
        elif _anomaly_type == 2:
            _anomaly = list(Anomalies.objects.filter(
                logcode=self.logcode,
                logdateend__gte=(self.logstartdate - datetime.timedelta(seconds=1)),
                logdateend__lte=(self.logenddate + datetime.timedelta(seconds=1))))
        else:
            _anomaly = list(Anomalies.objects.filter(
                logcode=self.logcode,
                logdatestart__lte=(self.logstartdate + datetime.timedelta(seconds=1)),
                logdateend__gte=(self.logenddate - datetime.timedelta(seconds=1))))
        # try:
        #     _anomaly_count = Anomalies.objects.filter(
        #         logcode=self.logcode,
        #         logdatestart__lte=(self.logstartdate + datetime.timedelta(seconds=1)),
        #         logdateend__gte=(self.logenddate - datetime.timedelta(seconds=1))).count()
        #     if _anomaly_count > 0:
        #         _anomaly = list(Anomalies.objects.filter(
        #             logcode=self.logcode,
        #             logdatestart__lte=(self.logstartdate + datetime.timedelta(seconds=1)),
        #             logdateend__gte=(self.logenddate - datetime.timedelta(seconds=1))))
        #     logger.debug(f"FOUND {_anomaly_count} Anomalies : {_anomaly}")
        # except Exception as err:
        #     logger.exception(
        #         f"An error occurred trying to find Anomaly for this AnomalyLogs id: {self.id}. ERROR IS : {err}")
        logger.debug(f"For anomalylog id:{self.id}&type:{_anomaly_type} FOUND {len(_anomaly)} Anomalies : {_anomaly}")
        return _anomaly

    def alerts_are_open(self):
        _result = False
        _userdisabled_values = LogDefinitionDetails.objects.values_list(
            "userdisabled", flat=True).filter(logcode=self.logcode)
        logger.debug(f"_userdisabled_values for anomalylog with id {self.id} is : {_userdisabled_values}")
        if _userdisabled_values and False in _userdisabled_values:
            logger.debug(f"There is at least one False in list. It means that there is at least one alert not disabled")
            _result = True
        return _result

    class Meta:
        managed = False
        db_table = 'anomalylogs'
        ordering = ['-id']   # it used for reset_ai
        unique_together = (('logid', 'anomalytype', 'logcode'),
                           ('logid', 'anomalytype', 'logcode', 'paramvariable', 'paramvalue'),)


class AnomalyLogsDetails(models.Model):
    """
    this database table keeps logs with a relation between them. Holds logs by calculation of some scores and time
    based root-cause as Anomaly log and Sub anomaly Log
    """
    id = models.BigAutoField(primary_key=True)

    # foreignkey definitions;
    anomalyLog = models.ForeignKey(AnomalyLogs, db_column="alogid", on_delete=models.CASCADE, db_index=False,
                                   related_name="logDetails", verbose_name="First Related Anomaly Log ID")
    subAnomalyLog = models.ForeignKey(AnomalyLogs, db_column="subalogid", on_delete=models.CASCADE, db_index=False,
                                      related_name="subLogDetails", verbose_name="Second Related Anomaly Log ID")

    # foreignkey references;
    # alogid = models.BigIntegerField(blank=True, null=True)  # anomalylogs id
    # subalogid = models.BigIntegerField(blank=True, null=True)  # anomalylogs id

    # other columns;
    scoredeviceip = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    scorelocgroup = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    scoreeventsimilar = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    scoreparameters = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    scorecredate = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    scoretimeseries = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    subtimeseries = ArrayField(models.IntegerField(blank=True, null=True))
    scorelast = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    grangerpval = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    causeeffect = models.TextField(verbose_name="Cause Effect", blank=True, null=True)
    causetimeseries = ArrayField(models.IntegerField(blank=True, null=True))
    relatedparameters = ArrayField(models.TextField(blank=True, null=True))
    userfeedback = models.BooleanField(verbose_name="User Feedback information", blank=True, null=True)
    pastdecisions = models.BooleanField(blank=True, null=True)
    aioutput = models.BooleanField(blank=True, null=True)
    aistatus = models.IntegerField(blank=True, null=True)
    aiconfidence = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    f1score = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    graphstatus = models.IntegerField(blank=True, null=True)
    scorecomponent = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    scoreapplication = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    aioutputscore = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    userscorefeedback = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)

    objects = Manager()

    def __str__(self):
        if self.relatedparameters is None or self.relatedparameters == "":
            return "No Value"
        else:
            return f"{self.relatedparameters}"

    def get_absolute_url(self):
        return reverse('inventories:anomaly_detail', kwargs={'id': self.id})

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                elif type(value) is datetime.datetime:
                    data[field.name] = value.strftime("%Y/%m/%d %H:%M:%S")
                elif type(value) is datetime.time:
                    data[field.name] = value.strftime("%H:%M:%S")
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def get_relation_string(self):
        _str = "Similarity in"
        if self.scoredeviceip == 3:
            _str = _str + " ip address &"
        if self.scorecomponent == 3:
            _str = _str + " component &"
        if self.scoreapplication == 3:
            _str = _str + " application &"
        if self.scorelocgroup == 1:
            _str = _str + " location group &"
        if self.scoreeventsimilar > 6:
            _str = _str + " context &"
        if self.scoreparameters > 10:
            _str = _str + f" parameters ({self.relatedparameters}) &"
        if _str == "Similarity in":
            _str = _str + " nothing"
        # elif _str.endswith(" &"):
        else:
            _str = _str[:-2]
        return _str

    def get_relations_dict(self):
        _same_ip = True if self.scoredeviceip == 3 else False
        _same_comp = True if self.scorecomponent == 3 else False
        _same_app = True if self.scoreapplication == 3 else False
        _same_loc = True if self.scorelocgroup == 1 else False
        _common_params = False if self.scoreparameters == 0 else self.relatedparameters
        _dtw_similar = None
        # if self.scoretimeseries > 0:
        #     if (float(self.scoretimeseries) - 0.3125656) == 0 or (float(self.scoretimeseries) - 0.3125656) == 0.0:
        #         _dtw_similar = 0.000
        #         logger.warning(f"scoretimeseries for AnomalyLogsDetails with id {self.id} is equal to 0.3125656 !!")
        #     else:
        #         _dtw_similar = (round((11.42757*abs(math.log((9.642015/abs(float(self.scoretimeseries)-0.3125656)), 2)))*1000))/1000

        # self.intervalscore = 0.3125656 + 9.642015 / (math.pow(2, self.intervalscoretemp / 11.42757))  # reverse math of this for time similarity inervalscore is scorecredate

        _time_similar = (round(11.42757 * abs(math.log((9.642015 / ((float(self.scorecredate) / 0.6) - 0.3125656)), 2))) * 1000) / 1000 if (float(self.scorecredate) / 0.6) > 0.32 else "No Time Similarity"

        _context_similar = None
        if self.scoreeventsimilar < 3:
            _context_similar = "LOW"
        elif self.scoreeventsimilar < 7:
            _context_similar = "MEDIUM"
        else:
            _context_similar = "HIGH"
        _ai_score = self.aioutputscore

        _relations = {
            'Same IP': _same_ip,
            'Same Component': _same_comp,
            'Same Application': _same_app,
            'Same Location': _same_loc,
            'Common Parameters': _common_params,
            # 'Parameters': False if not _common_params else f"{self.relatedparameters}",
            'Time Similarity (in seconds)': _time_similar,
            'Contextual Similarity Level': _context_similar,
            'AI Score': _ai_score
        }

        return _relations

    class Meta:
        managed = False
        db_table = 'anomalylogsdetails'
        ordering = ['-id']   # it used for reset_ai


class AnomalyParameters(models.Model):

    # id = models.BigAutoField(primary_key=True)

    # foreignkey definitions;
    # logCode = models.ForeignKey(LogDeviceParameters, to_field="parametername", db_column="logcode", db_index=False,
    #                             on_delete=models.CASCADE, related_name="anomalyParameters", verbose_name="Log Code")

    # verbose_name = "Device MAC address"
    # deviceMac = models.ForeignKey(DeviceMac, to_field="macaddress", db_column="devicemac", db_index=False,
    #                               on_delete=models.CASCADE, related_name="anomalyParameters")

    # foreignkey references;
    # devicemac = models.TextField(blank=True, null=True)  # devicemac

    uniqueid = models.TextField(blank=True, null=True)  # it was devicemac before

    # verbose_name = "Log Code",
    logcode = models.TextField(blank=True, null=True)  # logdeviceparameter table parametername column
    # verbose_name = "Anomaly Type",
    anomalytype = models.IntegerField(blank=True, null=True)  # 1301

    # other columns;
    # verbose_name = "Creation Date",
    credate = models.DateTimeField(blank=True, null=True)
    # verbose_name = "Location Group ID",
    locationgroupid = models.IntegerField(blank=True, null=True)
    # verbose_name = "Log Events",
    logevents = ArrayField(models.TextField(blank=True, null=True))
    # verbose_name = "Log Creation Date",
    logcredate = models.DateTimeField(blank=True, null=True)
    # verbose_name = "First Log Date",
    logstartdate = models.DateTimeField(blank=True, null=True)
    # verbose_name = "LAst Log Date",
    logenddate = models.DateTimeField(blank=True, null=True)
    # verbose_name = "Analyzed Status",
    analyzedstatus = models.IntegerField(blank=True, null=True)
    # verbose_name = "Log Time Series",
    logtimeseries = ArrayField(models.IntegerField(blank=True, null=True))
    # verbose_name = "Date Series",
    dateseries = ArrayField(models.BigIntegerField(blank=True, null=True))
    # verbose_name = "Interval Value",
    intervalval = models.IntegerField(blank=True, null=True)
    anomaliesid = models.IntegerField(blank=True, null=True)  # id of anomalies table it means alert about it

    objects = Manager()

    def __str__(self):
        return f"ID:{self.id} for {self.anomalytype} anomaly found parameter {self.logcode} in logs of log source {self.uniqueid}"

    def get_device(self):
        try:
            _device = NetworkDevice.objects.get(uniqueid=self.uniqueid)
        except ObjectDoesNotExist:
            _device = f"No log source with Unique id {self.uniqueid}, it may have been changed"
            logger.warning(f"No log source with Unique id {self.uniqueid}, uniqueid of this log source may have been changed");
        except Exception as err:
            _device = f"Couldn't find device because {err}"
        return _device

    class Meta:
        managed = False
        db_table = 'anomalyparameters'
        unique_together = (('uniqueid', 'logcode'),)
        ordering = ['-logcredate']


class AnomalyParametersDetails(models.Model):

    # id = models.BigAutoField(primary_key=True)

    # foreignkey definitions;
    anomaly = models.ForeignKey(AnomalyParameters, db_column="anomalyid", db_index=False, on_delete=models.CASCADE,
                                related_name="anomalyDetails", verbose_name="Anomaly Parameters")
    # deviceIP = models.ForeignKey(NetworkDevice, db_column="deviceip", to_field="deviceip", db_index=False,
    #                              on_delete=models.CASCADE, related_name="anomalyDetails",
    #                              verbose_name="Network Device Information")
    # verbose_name = "Device MAC Address"
    # deviceMac = models.ForeignKey(DeviceMac, db_column="devicemacid", db_index=False, on_delete=models.CASCADE,
    #                               to_field="macaddress", related_name="anomalyDetails")

    # foreignkey references;
    # anomalyid = models.BigIntegerField(blank=True, null=True)  # anomalyparameter table id column
    # devicemacid = models.TextField(blank=True, null=True)  # devicemac

    uniqueid = models.TextField(blank=True, null=True)  # it was devicemacid before
    deviceip = models.TextField(verbose_name="Network Device IP", blank=True, null=True)  # deviceip

    # other columns;
    # verbose_name = "Parameter Values",
    paramval = models.TextField(blank=True, null=True)
    # verbose_name = "Creation Date",
    credate = models.DateTimeField(blank=True, null=True)
    # verbose_name = "Log Start Date",
    logdatestart = models.DateTimeField(blank=True, null=True)
    # verbose_name = "Log End Date",
    logdateend = models.DateTimeField(blank=True, null=True)
    # verbose_name = "Parameter Series",
    paramseries = ArrayField(models.IntegerField(blank=True, null=True))
    # verbose_name = "Analyzed Status",
    analyzedstatus = models.IntegerField(blank=True, null=True)
    # verbose_name = "Log Times",
    logtimes = ArrayField(models.DateTimeField(blank=True, null=True))
    # verbose_name = "Parameter Field",
    paramfield = models.TextField(blank=True, null=True)
    anomaliesid = models.IntegerField(blank=True, null=True)  # id of anomalies table it means alert about it

    objects = Manager()

    def __str__(self):
        return self.paramval

    def get_device(self):
        try:
            _device = NetworkDevice.objects.get(uniqueid=self.uniqueid)
        except ObjectDoesNotExist:
            _device = f"No log source with Unique id {self.uniqueid}, it may have been changed"
            logger.warning(f"No log source with Unique id {self.uniqueid}, uniqueid of this log source may have been changed");
        except Exception as err:
            _device = f"Couldn't find device because {err}"
        return _device

    class Meta:
        managed = False
        db_table = 'anomalyparametersdetails'
        ordering = ['-credate']


class Mib(models.Model):

    # id = models.BigAutoField(verbose_name="", primary_key=True)
    # , verbose_name = "Device Brand Information"
    brand = models.ForeignKey(DeviceMark, db_column="markaid", db_index=False, on_delete=models.CASCADE,
                              related_name="mib")
    # , verbose_name = "Device Brand Model Information"
    brandModel = models.ForeignKey(DeviceModel, db_column="modelid", db_index=False, on_delete=models.CASCADE,
                                   related_name="mib")
    # , verbose_name = "Device Version Information"
    version = models.ForeignKey(DeviceVersions, db_column="versionid", db_index=False, on_delete=models.CASCADE,
                                related_name="mib")

    # foreignkey references;
    # markaid = models.BigIntegerField(verbose_name="", blank=True, null=True)  # brand_id for values of this column
    # modelid = models.BigIntegerField(verbose_name="", blank=True, null=True)  # brandModel_id
    # versionid = models.IntegerField(verbose_name="", blank=True, null=True)  # version_id

    # other columns;
    # verbose_name = "",
    oib = models.CharField(max_length=40, blank=True, null=True)
    # verbose_name = "",
    oibaciklama = models.TextField(blank=True, null=True)
    # verbose_name = "",
    grup = models.CharField(max_length=10, blank=True, null=True)
    # verbose_name = "",
    durum = models.BooleanField(blank=True, null=True)
    # verbose_name = "",
    degisken = models.CharField(max_length=20, blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.oibaciklama

    class Meta:
        managed = False
        db_table = 'mib'


class NewBehaviors(models.Model):

    # id = models.BigAutoField(primary_key=True)
    # verbose_name = "Device MAC Address"
    # deviceMac = models.ForeignKey(DeviceMac, db_column="macaddress", to_field="macaddress", db_index=False,
    #                               on_delete=models.CASCADE, related_name="newBehaviors")
    # foreignkey references;
    # macaddress = models.CharField(max_length=40, blank=True, null=True)#devicemac

    uniqueid = models.CharField(max_length=40, blank=True, null=True)  #it was macaddress before

    # verbose_name = "Device IP Adress",
    deviceip = models.CharField(max_length=40, blank=True, null=True)  # deviceip
    # verbose_name = "Log Definition Code",
    logdefcode = models.IntegerField(blank=True, null=True)  # logdefinitions table definitioncode column
    # verbose_name = "Log Code",
    logcode = models.TextField(blank=True, null=True)  # logdefdetails table logcode table
    # verbose_name = "Date of Last Log",
    lastlogtime = models.DateTimeField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return str(self.lastlogtime)

    class Meta:
        managed = False
        db_table = 'newbehaviors'
        unique_together = (('uniqueid', 'logdefcode', 'logcode'),)


class ParameterInterval(models.Model):

    # id = models.BigAutoField(verbose_name="", primary_key=True)
    parameterdevicegroupid = models.BigIntegerField(verbose_name="", )  # logdeviceparameter table id column

    timeepoch = models.BigIntegerField(blank=True, null=True)
    intervalval = models.IntegerField(blank=True, null=True)
    timestart = models.DateTimeField(blank=True, null=True)
    logcount = models.IntegerField(blank=True, null=True)
    prediction = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    lowerbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    upperbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    modeltype = models.IntegerField(blank=True, null=True)
    kdezero = models.TextField(blank=True, null=True)
    kdenonzero = models.TextField(blank=True, null=True)
    excessmedian = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    fqmedian = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return str(self.intervalval)

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def model_type_name(self):
        type_name = None
        if self.modeltype == 1:
            type_name = "Continuous"
        elif self.modeltype == 2:
            type_name = "Sparse"

        return type_name

    class Meta:
        managed = False
        db_table = 'parameterinterval'
        unique_together = (('timeepoch', 'intervalval', 'parameterdevicegroupid'),)
        ordering = ['timeepoch']


class MailSettings(models.Model):
    """
    about sending mails to relevant peoples
    """
    touser = models.TextField(verbose_name="E-mail Recipient", blank=True, null=True)
    mailtype = models.TextField(verbose_name="Mail Protokol", blank=True, null=True)
    starttls = models.BooleanField(verbose_name="TLS ?", blank=True, null=True)
    mailport = models.IntegerField(verbose_name="Mail Port", blank=True, null=True)
    fromuser = models.TextField(verbose_name="E-mail Sender", blank=True, null=True)
    frompass = models.TextField(verbose_name="Sender Password", blank=True, null=True)
    auth = models.BooleanField(verbose_name="Is Authentication required", blank=True, null=True)
    mailserver = models.TextField(verbose_name="IP Address of Mail Server", blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"Mail from {self.fromuser} to {self.touser}"

    def get_absolute_url(self):
        return reverse('mailing_settings_edit', kwargs={'id': self.id})

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def get_details(self):
        _mailDetailsList = []
        try:
            _mailDetailsList = list(MailDetails.objects.filter(mailsetting=self.id))
        except Exception as err:
            logger.exception(
                f"An error occurred trying to get maildetails for mailsettings with id {self.id}. ERROR IS : {err}")
        return _mailDetailsList

    class Meta:
        managed = False
        db_table = 'mailsettings'
        ordering = ['id']


class MailDetails(models.Model):
    """
    Details about mail content
    """
    lstype = models.TextField(verbose_name="Type of Log Source", blank=True, null=True)
    lsvendor = models.TextField(verbose_name="Brand of Log Sources", blank=True, null=True)
    lsmodel = models.TextField(verbose_name="Model of Chosen Brand", blank=True, null=True)
    lsversion = models.TextField(verbose_name="Version of Chosen Model", blank=True, null=True)
    service = models.TextField(verbose_name="Service That You Want to be Informed", blank=True, null=True)
    application = models.TextField(verbose_name="Application That You Want to be Informed", blank=True, null=True)
    lslocation = models.TextField(verbose_name="Location That You Want to be Informed", blank=True, null=True)
    anomalylevel = models.TextField(verbose_name="Min Level of Information", blank=True, null=True, default="0")
    typetosend = models.TextField(verbose_name="Type of Occurrences You Want to be Informed", blank=True, null=True)
    mailsetting = models.IntegerField(verbose_name="Mail Settings You Want to Use for it (Chose recipient)",
                                      blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"Mail for {self.typetosend} notifications"

    def get_absolute_url(self):
        return reverse('mailing_details_edit', kwargs={'id': self.id})

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'maildetails'
        ordering = ['id']


class SystemParameters(models.Model):
    """
    atibaserver global parameters
    """
    # id = models.SmallAutoField(primary_key=True)

    # lifetime of the records in atibalogs named index of elasticsearch
    loglifetime = models.IntegerField(verbose_name="Storage Time of a Logs in ATIBA (DAYS)", blank=True, null=True,
                                      validators=[MaxValueValidator(365), MinValueValidator(8)], default=30)
    # the time interval in days required to decide whether the behavior is new;
    newbehaviortime = models.IntegerField(verbose_name="New Behaviour Time (DAYS)", blank=True, null=True, default=7)
    # timeseries interval values in minutes;
    timeseriesinterval = models.IntegerField(verbose_name="Interval of Time Series (MINUTES)", blank=True, null=True)
    dnsinterval = models.IntegerField(blank=True, null=True)
    dhcpinterval = models.IntegerField(blank=True, null=True)
    radiusinterval = models.IntegerField(blank=True, null=True)
    fromuser = models.TextField(blank=True, null=True)
    frompass = models.TextField(blank=True, null=True)
    pop3 = models.TextField(blank=True, null=True)
    emailtype = models.TextField(blank=True, null=True)
    sslport = models.IntegerField(blank=True, null=True)
    auth = models.BooleanField(blank=True, null=True)
    emailhost = models.TextField(blank=True, null=True)
    starttls = models.BooleanField(blank=True, null=True)
    smtpport = models.IntegerField(blank=True, null=True)
    devmacaddress = models.TextField(blank=True, null=True)
    snmpcontrollerinterval = models.IntegerField(blank=True, null=True)
    ssl = models.BooleanField(blank=True, null=True)
    fallback = models.BooleanField(blank=True, null=True)
    systemip = models.TextField(blank=True, null=True)
    atibaver = models.TextField(blank=True, null=True)
    atibasubver = models.IntegerField(blank=True, null=True)
    syslogpriorities = ArrayField(models.BooleanField(verbose_name="System Log Priorities", blank=True, null=True))
    # lifetime of the records in atibaloglar named index of elasticsearch
    errstatloglife = models.IntegerField(verbose_name="Un-parsed Log Lifetime in ATIBA (DAYS)", blank=True, null=True,
                                         default=7, validators=[MaxValueValidator(14), MinValueValidator(5)])
    # lifetime of AnomalyLogs records...
    alertlife = models.IntegerField(verbose_name="Alerts Lifetime in ATIBA (DAYS)", blank=True, null=True, default=30)
    corepointthreshold = models.DecimalField(verbose_name="AI-Correlation Point Threshold", max_digits=7,
                                             decimal_places=2, blank=True, null=True, default=8.00)
    corepiecethreshold = models.IntegerField(verbose_name="AI-Correlation Count Threshold", blank=True, null=True,
                                             default=2500)
    incpiecethreshold = models.IntegerField(verbose_name="AI-Incident Count Threshold", blank=True, null=True,
                                            default=2500)
    incidenttimeout = models.IntegerField(verbose_name="Max Interval That Incident Sets will remain Open (SECONDS)",
                                          blank=True, null=True, default=600)
    autoparamintervalchoices = [("Daily", "Work Per Day")]
    autoparaminterval = models.CharField(verbose_name="Parameter Analyst Process Period",
                                         choices=autoparamintervalchoices, default="Daily", blank=True, null=True,
                                         max_length=20)
    autoparamtime = models.TimeField(verbose_name="Parameter Analyst Exact Working Time", blank=True,
                                     null=True, default=datetime.time(3, 30, 00))
    clusterips = ArrayField(models.TextField(blank=True, null=True))
    # notifyemails = ArrayField(models.TextField(verbose_name="Email Addresses for Notifications", blank=True, null=True))

    objects = Manager()

    def __str__(self):
        return str(self.newbehaviortime)

    class Meta:
        managed = False
        db_table = 'systemparameters'

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                elif type(value) is decimal.Decimal:
                    data[field.name] = float(value)
                elif type(value) is datetime.datetime:
                    data[field.name] = value.strftime("%Y/%m/%d %H:%M:%S")
                elif type(value) is datetime.time:
                    data[field.name] = value.strftime("%H:%M:%S")
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def get_readable_syslogpriorities(self):
        _list = self.syslogpriorities
        _upper = math.floor(len(_list)/8)
        _a = []
        _counter = 0
        for i in range(0, _upper):
            _b = []
            for j in range(0, 8):
                _b.append(_list[_counter])
                _counter += 1
            _a.append(_b)
        return _a

    def set_syslogpriorities_from_readable(self, *args):
        _list = args[0]
        _a = _list[0]
        # logger.debug(f"before loop : {_a}")
        for i in range(1, len(_list)):
            _a.extend(_list[i])
        # logger.debug(f"after loop : {_a}")
        self.syslogpriorities = _a
        try:
            self.save()
            return True
        except Exception as err:
            logger.exception(f"An error occurred trying to save syslogpriorities and failed to save. ERROR IS : {err}")
            return False

    def coreAiStatus(self):
        """
        select case when (2500< ANY(array_agg(id))) then 0 when (2500>ANY(array_agg(id))) then 1 end from anomalylogsdetails
        select case when (%s< ANY(array_agg(id))) then 0 when (%s>ANY(array_agg(id))) then 1 end from anomalylogsdetails
        """
        _threshold = self.corepiecethreshold if self.corepiecethreshold else 2500
        _completed_string = "Initial training process of AI-correlation has been completed, we recommend giving feedback to further the training."
        _continue_string = "Initial training process of AI-correlation is ongoing, we advice that you give feedback at the end of this process."
        _condition = AnomalyLogsDetails.objects.count()
        if _condition:
            if _condition > _threshold:
                return ["green", _completed_string]
            else:
                return ["red", _continue_string]

    def incAiStatus(self):
        """
        select case when (2500< ANY(array_agg(id))) then 0 when (2500>ANY(array_agg(id))) then 1 end from anomalylogs
        select case when (%s< ANY(array_agg(id))) then 0 when (%s>ANY(array_agg(id))) then 1 end from anomalylogs
        """
        _threshold = self.incpiecethreshold if self.incpiecethreshold else 2500
        _completed_string = "Initial training process of AI-incident has been completed, we recommend giving feedback to further the training."
        _continue_string = "Initial training process of AI-incident is ongoing, we advice that you give feedback at the end of this process."
        _condition = AnomalyLogs.objects.count()
        if _condition:
            if _condition > _threshold:
                return ["green", _completed_string]
            else:
                return ["red", _continue_string]

    def notifyemails(self):
        _mailSettings = []
        try:
            _mailSettings = list(MailSettings.objects.all())
        except Exception as err:
            logger.exception(f"An error occurred trying to get mailsettings objects. ERROR IS : {err}")
        return _mailSettings


class SystemSeverities(models.Model):

    # verbose_name = "System Severity Code",
    severitycode = models.TextField(primary_key=True)  # primary key of table
    # verbose_name = "Severity Definition",
    severitydef = models.TextField(blank=True, null=True)
    # verbose_name = "Anomaly Value",
    anomalyvalue = models.IntegerField(blank=True, null=True)
    # verbose_name = "Severity Level",
    severitylevel = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.severitycode

    class Meta:
        managed = False
        db_table = 'systemseverities'


class UpdateStatus(models.Model):

    # id = models.BigAutoField(primary_key=True)

    brand = models.ForeignKey(DeviceMark, on_delete=models.CASCADE, related_name="updatestatus", db_index=False,
                              db_column='markid')
    # markid = models.IntegerField(blank=True, null=True)  # ForeignKey reference this column
    uploadtype = models.TextField(blank=True, null=True)
    upversion = models.TextField(blank=True, null=True)
    upsubversion = models.IntegerField(blank=True, null=True)
    cmdtitle = models.TextField(blank=True, null=True)
    cmd = models.TextField(blank=True, null=True)
    ifsuccess = models.BooleanField(blank=True, null=True)
    errorinfo = models.TextField(blank=True, null=True)
    versioncontent = models.TextField(blank=True, null=True)
    uploaddate = models.DateTimeField(blank=True, null=True, default=timezone.now)
    filename = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"{self.filename} -> type : {self.uploadtype}"

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'updatestatus'


class UserMetricGroup(models.Model):

    # id = models.BigAutoField(primary_key=True)

    # verbose_name = "Metric Definition Information",
    metricdefinition = models.TextField(blank=True, null=True)
    # verbose_name = "Recalculation Model?",
    recalcmodel = models.BooleanField(blank=True, null=True)
    # verbose_name = "Model Type",
    modeltype = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order D Value",
    orderdval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order P Value",
    orderpval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Order Q Value",
    orderqval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Metric Interval",
    metricinterval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Is Status Active?",
    statusactive = models.BooleanField(blank=True, null=True)
    # verbose_name = "Metric Value",
    metricval = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.metricdefinition

    class Meta:
        managed = False
        db_table = 'usermetricgroup'


class UserMetricDefinition(models.Model):

    # id = models.BigAutoField(primary_key=True)

    # foreignkey definitions;
    # verbose_name = "Device Location Group"
    locationGroup = models.ForeignKey(DevLocationGroup, db_column="locationgroupid", db_index=False,
                                      on_delete=models.CASCADE, related_name="userMetrics")
    # verbose_name = "Device Location Info"
    location = models.ForeignKey(DevLocations, db_column="locationid", db_index=False, on_delete=models.CASCADE,
                                 related_name="userMetrics")
    # verbose_name = "User Metric Group Information"
    userMetricGroup = models.ForeignKey(UserMetricGroup, db_column="usermetricgroupid", db_index=False,
                                        on_delete=models.CASCADE, related_name="userMetrics")
    # foreignkey references;
    # locationgroupid = models.IntegerField(blank=True, null=True)  # devicelocationgroup table id column
    # locationid = models.IntegerField(blank=True, null=True)  # devlocations table id column
    # usermetricgroupid = models.IntegerField(blank=True, null=True)  # usermetricgroup table id column

    # verbose_name = "Application Group Info",
    applicationgroup = models.IntegerField(blank=True, null=True)
    # verbose_name = "Application ID",
    applicationid = models.IntegerField(blank=True, null=True)
    # verbose_name = "Device MAC Address",
    devicemac = models.TextField(blank=True, null=True)  # device mac address
    # verbose_name = "Device Type",
    devicetype = models.TextField(blank=True, null=True)  # devicetypelist table devicetype column
    # verbose_name = "device Type Code",
    devicetypecode = models.TextField(blank=True, null=True)  # devicetypelist table devicetypecode column
    # verbose_name = "User Metric Definition Name",
    definitionname = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.definitionname

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'usermetricdefinition'


class UserMetricInterval(models.Model):

    # id = models.BigAutoField(primary_key=True)

    # foreignkey definitions;
    # verbose_name = "User Metric Group Information"
    userMetricGroup = models.ForeignKey(UserMetricGroup, db_column="usermetricgroupid", db_index=False,
                                        on_delete=models.CASCADE, related_name="metricInterval")

    # foreignkey references;
    # usermetricgroupid = models.IntegerField(blank=True, null=True)  # usermetricgroup table id column

    # verbose_name = "Time Epoch",
    timeepoch = models.BigIntegerField(blank=True, null=True)
    # verbose_name = "Interval Value",
    intervalval = models.IntegerField(blank=True, null=True)
    # verbose_name = "Exact Time of Start",
    timestart = models.DateTimeField(blank=True, null=True)
    # verbose_name = "Log Count",
    logcount = models.IntegerField(blank=True, null=True)
    # verbose_name = "Prediction",
    prediction = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    # verbose_name = "Lower Bound",
    lowerbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    # verbose_name = "Upper Bound",
    upperbound = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    # verbose_name = "Model Type",
    modeltype = models.IntegerField(blank=True, null=True)  # usermetricgroup table modeltype column

    objects = Manager()

    def __str__(self):
        return str(self.intervalval)

    class Meta:
        managed = False
        db_table = 'usermetricinterval'
        unique_together = (('timeepoch', 'intervalval', 'userMetricGroup_id'),)


# class RootCauseGraphs(models.Model):
#     # id = models.BigAutoField(primary_key=True)
#
#     # verbose_name = "Root Node of This Graph",
#     rootnode = models.BigIntegerField(blank=True, null=True)
#     # verbose_name = "Full Node List of Graph",
#     nodelist = ArrayField(models.BigIntegerField(blank=True, null=True))
#     # verbose_name = "Cause List of Root",
#     leaflist = ArrayField(models.BigIntegerField(blank=True, null=True))
#     # verbose_name = "Root - Cause Graph",
#     rcgraph = models.TextField(blank=True, null=True)
#     # verbose_name = "SinGraph ID",
#     idsingraph = ArrayField(models.BigIntegerField(blank=True, null=True))
#     # verbose_name = "Cause Nodes of Graph",
#     causenode = models.BigIntegerField(blank=True, null=True)
#     # verbose_name = "Status of Analysis",
#     analyzedstatus = models.IntegerField(blank=True, null=True)
#
#     objects = Manager()
#
#     def __str__(self):
#         return f"TREE FOR ROOT NODE : {str(self.rootnode)}"
#
#     def get_absolute_url(self):
#         return reverse('inventories:rc_graph_detail', kwargs={'id': self.id})
#
#     def rc_map(self):
#         return json.loads(json.dumps(self.rcgraph))
#
#     def get_root_log(self):
#         try:
#             log = AnomalyLogs.objects.get(id=self.rootnode)
#         except ObjectDoesNotExist:
#             log = f"Couldn't find matching object with id : {self.rootnode}"
#         return log
#
#     def get_cause_log(self):
#         try:
#             log = AnomalyLogs.objects.get(id=self.causenode)
#         except ObjectDoesNotExist:
#             log = f"Couldn't find matching object with id : {self.causenode}"
#         return log
#
#     def get_root_device(self):
#         rootLog = self.get_root_log()
#         try:
#             device = rootLog.deviceMac.devices.all()[0]
#         except Exception as err:
#             device = f"error : {err}"
#         return device
#
#     def get_cause_device(self):
#         causeLog = self.get_cause_log()
#         try:
#             device = causeLog.deviceMac.devices.all()[0]
#         except Exception as err:
#             device = f"error : {err}"
#         return device
#
#     class Meta:
#         managed = False
#         db_table = 'rcgraphs'
#         unique_together = (('rootnode', 'causenode'),)
#         ordering = ['-id']


class RootCauseGraphsDetails(models.Model):
    # id = models.BigAutoField(primary_key=True)

    rootlist = ArrayField(models.BigIntegerField(blank=True, null=True))
    nodelist = ArrayField(models.BigIntegerField(blank=True, null=True))
    leaflist = ArrayField(models.BigIntegerField(blank=True, null=True))
    rcgraph = models.TextField(blank=True, null=True)
    analyzedstatus = models.IntegerField(blank=True, null=True)
    graphupdatetime = models.DateTimeField(blank=True, null=True)
    graphpaths = models.TextField(blank=True, null=True)
    largegraph = models.TextField(blank=True, null=True)
    graphimage = models.ImageField(blank=True, null=True)
    incidentid = models.IntegerField(blank=True, null=True)
    giventotalfeed = models.BooleanField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"Causal Mapping for Incident(s) : {str(self.rootlist)}"

    def get_absolute_url(self):
        return reverse('inventories:rc_graph_detail', kwargs={'id': self.id})

    def get_analyse_url(self):
        return reverse('AgentRoot:diagnosis_analyse', kwargs={'id': self.id})

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                elif type(value) is datetime.datetime:
                    data[field.name] = value.strftime("%Y/%m/%d %H:%M:%S")
                elif type(value) is datetime.time:
                    data[field.name] = value.strftime("%H:%M:%S")
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def rc_map(self):
        return json.loads(json.dumps(self.rcgraph))

    def rc_paths(self):
        return json.loads(json.dumps(self.graphpaths))

    def incident_closedate(self):
        _result = None
        if self.incidentid:
            try:
                _result = Incidents.objects.values_list("closedate", flat=True).filter(id=self.incidentid)[0]
            except Exception as err:
                _result = "No Info"
                logger.exception(f"An error occurred trying to get incident isopen value. ERROR IS : {err}")
        else:
            _result = "Not Have an Incident Set"
        return _result

    def get_root_logs(self):
        _rootList = list(self.rootlist)
        _rootList.sort(reverse=True)
        _rootLogs = []
        for root in _rootList:
            try:
                _log = AnomalyLogs.objects.get(id=root)
            except ObjectDoesNotExist:
                _log = f"Couldn't find matching Anomaly Log with id : {root}"
            _rootLogs.append(_log)
        return _rootLogs

    def get_leaf_logs(self):
        _leafList = list(self.leaflist)
        _leafList.sort()
        _leafLogs = []
        for _leaf in _leafList:
            try:
                _log = AnomalyLogs.objects.get(id=_leaf)
            except ObjectDoesNotExist:
                _log = f"Couldn't find matching Anomaly Log with id : {_leaf}"
            _leafLogs.append(_log)
        return _leafLogs

    def get_node_loglist(self):
        _nodeList = list(self.nodelist)
        _nodeList.sort(reverse=True)
        _nodeLogs = []
        for _node in _nodeList:
            try:
                _log = AnomalyLogs.objects.get(id=_node)
            except ObjectDoesNotExist:
                _log = f"Couldn't find matching Anomaly Log with id : {_node}"
            _nodeLogs.append(_log)
        return _nodeLogs

    def get_log_times_chart_data(self):
        """to get list of json objects to use bubble chart"""
        _node_list = list(self.nodelist)
        _node_list.sort(reverse=True)
        _node_date_list = []
        _date_list = []
        for node in _node_list:
            _anomaly_log = AnomalyLogs.objects.only("anomalytype").get(id=node)
            logger.debug(f"Anomaly type is {_anomaly_log.anomalytype} for node {node}")
            if _anomaly_log.anomalytype == 1:
                _node_dates = [AnomalyLogs.objects.values_list("credate", flat=True).filter(id=node)]
            else:
                _node_dates = AnomalyLogs.objects.values_list("logtimes", flat=True).filter(id=node)
            # _column_name = "credate" if 1 in AnomalyLogs.objects.values_list("anomalytype", flat=True).filter(id=node) else "logtimes"
            # _node_dates = AnomalyLogs.objects.values_list(_column_name, flat=True).filter(id=node)
            # _node_dates = AnomalyLogs.objects.values_list("logtimes", flat=True).filter(id=node)
            if _node_dates and _node_dates[0] is not None:
                # _date_list += [_.strftime("%Y/%m/%d-%H:%M:%S.%f") for _ in _node_dates[0]]
                _date_list += [_.strftime("%d-%b-%H:%M:%S.%f") for _ in _node_dates[0]]
                # _node_date_list += [(node, _.strftime("%Y/%m/%d-%H:%M:%S.%f")) for _ in _node_dates[0]]
                _node_date_list += [(node, _.strftime("%d-%b-%H:%M:%S.%f")) for _ in _node_dates[0]]
        _date_list = list(set(_date_list))
        _date_list.sort()
        _date_list = _date_list[-50:] if len(_date_list) > 50 else _date_list
        _results = []
        for _date in _date_list:
            for node, node_date in _node_date_list:
                if node_date == _date:
                    _results.append(node)
        logger.debug(f"_result is : {_results}")
        return [_node_list, _date_list, _results]

    def get_root_devices(self):
        _rootLogs = self.get_root_logs()
        try:
            _devices = [_rootLog.get_device() for _rootLog in _rootLogs]
        except Exception as err:
            _devices = [f"error : {err}"]
        return list(set(_devices))

    def get_cause_devices(self):
        _causeLogs = self.get_leaf_logs()
        try:
            _devices = [_causeLog.get_device() for _causeLog in _causeLogs]
        except Exception as err:
            _devices = [f"error : {err}"]
        return _devices

    def get_anomaly_types(self):
        _roots = self.get_root_logs()
        _anomaly_types = []
        for _root in _roots:
            if isinstance(_root, AnomalyLogs):
                try:
                    _explanation = _root.get_type_definition()
                except Exception as err:
                    _explanation = f"Couldn't find any matching explanation for {_root.id} log because {err}"
                _anomaly_types.append(_explanation)
            else:
                logger.error(f"Couldn't find any matching explanation for log because : {_root}")
        return list(set(_anomaly_types))

    def get_paths(self):
        """
        provides you paths from incidents to root-causes
        """
        _paths = []
        try:
            _paths = json.loads(str(self.graphpaths))
        except Exception as err:
            logger.error(f"RootCauseGraphsDetail class get_paths method encountered an error : {err}")
            _paths = []
        return _paths

    def get_incident_set(self):
        _incident_set = None
        try:
            _incident_set = Incidents.objects.get(id=self.incidentid)
        except ObjectDoesNotExist:
            logger.warning(f"There is no incident set with id {self.incidentid}")
        except Exception as err:
            logger.exception(f"An error occurred trying to get incident set with id {self.incidentid}. ERROR IS {err}")
        return _incident_set

    class Meta:
        managed = False
        db_table = 'rcgraphsdetails'
        ordering = ['-id']


class ScanParameters(models.Model):
    paramsname = models.TextField(blank=True, null=True)
    communitystring = models.TextField(blank=True, null=True)
    snmpv3user = models.TextField(blank=True, null=True)
    snmpv3authpass = models.TextField(blank=True, null=True)
    snmpv3authprotocol = models.TextField(blank=True, null=True)
    snmpv3privacypass = models.TextField(blank=True, null=True)
    snmpv3privacyprotocol = models.TextField(blank=True, null=True)
    snmpversion = models.TextField(blank=True, null=True)
    # oid = models.TextField(blank=True, null=True)
    versionoid = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.paramsname

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'scanparameters'
        ordering = ['id']


class IngestionProfileType(models.Model):

    id = models.BigIntegerField(primary_key=True)
    profiletype = models.TextField(blank=True, null=True, db_column="ingestiontype")

    objects = Manager()

    def __str__(self):
        return self.profiletype

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data
    
    def get_profiles(self):
        _profiles = []
        try:
            _profiles = list(IngestionProfile.objects.filter(ingestionprofiletypeid=self.id))
        except Exception as err:
            logger.warning(f"Couldn't get profiles for profile type {self.profiletype}. ERROR IS : {err}")
        return _profiles

    class Meta:
        managed = False
        db_table = 'ingestionprofiletype'
        ordering = ['id']


class IngestionProfile(models.Model):

    ingestionprofilename = models.TextField(blank=True, null=True)
    ingestionprofiletypeid = models.BigIntegerField(blank=True, null=True)
    ingestionport = models.IntegerField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return self.ingestionprofilename

    # def get_delete_url(self):
    #     return reverse('delete_profile', kwargs={'id': self.id, 'type': 'ingestionprofile'})

    def is_in_use(self):
        return LogSources.objects.filter(ingestionprofile=self.id).count() > 0

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data
    
    def get_profile_type(self):
        _profile_type = ""
        if self.ingestionprofiletypeid:
            try:
                _profile_type = IngestionProfileType.objects.get(id=self.ingestionprofiletypeid)
            except ObjectDoesNotExist:
                _profile_type = f"ingestionprofiletype dosn't exist for id : {self.ingestionprofiletypeid}"
        return _profile_type

    class Meta:
        managed = False
        db_table = 'ingestionprofile'
        ordering = ['id']


class MonitorProfile(models.Model):

    id = models.IntegerField(primary_key=True)
    monitorprofilename = models.TextField(blank=True, null=True)
    monitorprofiletype = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"{self.monitorprofilename} - type : {self.monitorprofiletype}"

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def get_profile_details(self):
        _monitor_profile_details_list = []
        try:
            _monitor_profile_details_list = list(MonitorProfileDetails.objects.filter(monitorProfile_id=self.id))
        except Exception as err:
            logger.warning(f"No monitorprofdetails for monitorprofile which id : {self.id}. ERROR IS : {err}")
        return _monitor_profile_details_list

    class Meta:
        managed = False
        db_table = 'monitorprofile'
        ordering = ['id']


class MonitorProfileDetails(models.Model):

    monitorProfile = models.ForeignKey(MonitorProfile, db_column="monitorprofileid", db_index=False,
                                       related_name="profileDetails", on_delete=models.CASCADE)
    # monitorprofileid = models.TextField(blank=True, null=True)
    paramsname = models.TextField(blank=True, null=True)
    querytosend = models.TextField(blank=True, null=True)
    responsetoreceive = models.TextField(blank=True, null=True)
    responsetodown = models.TextField(blank=True, null=True)
    communitystring = models.TextField(blank=True, null=True)
    snmpv3user = models.TextField(blank=True, null=True)
    snmpv3authpass = models.TextField(blank=True, null=True)
    snmpv3authprotocol = models.TextField(blank=True, null=True)
    snmpv3privacypass = models.TextField(blank=True, null=True)
    snmpv3privacyprotocol = models.TextField(blank=True, null=True)
    snmpversion = models.TextField(blank=True, null=True)

    httpmethod = models.TextField(blank=True, null=True)
    httpurl = models.TextField(blank=True, null=True)
    httpuri = models.TextField(blank=True, null=True)
    httpsecure = models.BooleanField(blank=True, null=True)
    httpport = models.IntegerField(blank=True, null=True)
    username = models.TextField(blank=True, null=True)
    userpass = models.TextField(blank=True, null=True)
    dbasename = models.TextField(blank=True, null=True)

    objects = Manager()

    class Meta:
        managed = False
        db_table = 'monitorprofdetails'

    def __str__(self):
        return f"Name : {self.paramsname} (Send : {self.querytosend} & Wait : {self.responsetoreceive} & Down : {self.responsetodown})"

    def get_edit_url(self):
        return reverse('edit_monitor_profile', kwargs={'id': self.id})

    def get_delete_url(self):
        return reverse('delete_profile', kwargs={'id': self.id, 'type': 'monitorprofiledetails'})

    def is_in_use(self):
        return LogSources.objects.filter(monitorprofile=self.id).count() > 0

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            # stolen from Serializer :D
            value = field.value_from_object(self)
            # Protected types (i.e., primitives like None, numbers, dates, and Decimals) are passed through as is.
            # All other values are converted to string first.
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        # Collect ids of M2M related items
        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data


class NetworkDevice(models.Model):
    """
    Now it connects to db table logsources
    This database table keeps a lot of information about devices in system like brand, model, type, mac address, device
    name, status, ip more and more...
    """
    brand = models.ForeignKey(DeviceMark, verbose_name="Device TradeMark(Brand) Info", on_delete=models.CASCADE,
                              related_name="devices", db_index=False, db_column='markid')
    brandModel = models.ForeignKey(DeviceModel, verbose_name="Device Model Info", on_delete=models.CASCADE,
                                   related_name="devices", db_index=False, db_column='modelid')
    version = models.ForeignKey(DeviceVersions, verbose_name="Device Version Info", on_delete=models.CASCADE,
                                related_name="devices", db_index=False, db_column="deviceverid")
    monitorProfile = models.ForeignKey(MonitorProfileDetails, on_delete=models.CASCADE, related_name='devices',
                                       db_column='monitorprofile')
    locationProfile = models.ForeignKey(DevLocations, on_delete=models.CASCADE, related_name='devices',
                                        db_column='locationprofile')
    parserProfile = models.ForeignKey(DeviceParserProfile, on_delete=models.CASCADE, related_name='devices',
                                      db_column='parserprofile')

    # macAddress = models.ForeignKey(DeviceMac, to_field="macaddress", on_delete=models.CASCADE, related_name="devices",
    #                                db_index=False, db_column="macaddress")

    # foreignKey references;
    # markid = models.IntegerField(verbose_name="Device Brand Id", null=True, blank=True)
    # modelid = models.IntegerField(verbose_name="Device Model Id", null=True, blank=True)
    # deviceverid = models.IntegerField(verbose_name="Device Verify Id", null=True, blank=True)

    uniqueid = models.TextField(unique=True, blank=True, null=True)
    uniqueidtype = models.TextField(blank=True, null=True)
    deviceip = models.TextField(null=True, blank=True, db_column='ipaddress')
    devicename = models.TextField(blank=True, null=True, db_column='sourcename')

    macaddress = models.TextField(blank=True, null=True)
    hostname = models.TextField(blank=True, null=True)
    customname = models.TextField(blank=True, null=True)
    logsourceselection = models.TextField(blank=True, null=True)

    manualyadded = models.BooleanField(null=True, blank=True, db_column='manuallyadded')
    creationdate = models.DateTimeField(null=True, blank=True)
    updatedate = models.DateTimeField(null=True, blank=True)
    devstatus = models.TextField(blank=True, null=True, db_column='status')
    devicenote = models.TextField(null=True, blank=True)
    snmpstatus = models.BooleanField(null=True, blank=True)
    scanstatus = models.IntegerField(null=True, blank=True)
    modeltype = models.IntegerField(null=True, blank=True, db_column='devicetype')
    connectedmac = models.TextField(null=True, blank=True)
    virtualdeviceip = models.TextField(null=True, blank=True)

    objects = Manager()

    def __str__(self):
        return f"Name of log source {self.devicename}"

    def fields_of(self):
        return [str(i.verbose_name) for i in self._meta.fields]

    def get_absolute_url(self):
        return reverse('inventories:device_detail', kwargs={'id': self.id})

    def get_logs_for_source_url(self):
        return reverse('inventories:logs_for_source', kwargs={'id': self.id})

    def simplified_mac(self):
        if self.uniqueidtype != "macaddress":
            return self.uniqueid
        return mac_to_simplified(self.uniqueid)

    def get_connected_devices(self):
        """
        this method helps to find devices which connected to this device
        :returns: a the list of devices connected to this device
        """
        _connected_devices = None
        if (self.uniqueid is not None) and self.uniqueid != "":
            try:
                _connected_devices = list(NetworkDevice.objects.filter(connectedmac=self.uniqueid))
            except Exception as err:
                logger.warning(f"NetworkDevice.get_connected_devices encountered an error : {err}")
        return _connected_devices

    def mean_scan_status(self):
        _result = "LOGGING"
        if self.scanstatus in [1, 2]:
            _result = "IN STAGING"
        elif self.scanstatus == 9:
            _result = "IN HISTORY"
        return _result

    def get_unparsed_log_count(self):
        if self.uniqueid is not None:
            try:
                _count = Logs.objects.filter(mappedlogsource=self.uniqueid).count()
            except Exception as err:
                _count = 0
        else:
            _count = 0
        return _count

    class Meta:
        managed = False
        db_table = 'logsources'
        # unique_together = (('deviceip', 'macAddress_id'),)
        ordering = ['id']


class LogSources(models.Model):
    # table primary key
    # id = models.BigAutoField(primary_key=True)
    sourcename = models.TextField(blank=True, null=True)
    # log source unique identifier
    uniqueid = models.TextField(unique=True, blank=True, null=True)
    ipaddress = models.TextField(blank=True, null=True)
    macaddress = models.TextField(blank=True, null=True)
    hostname = models.TextField(blank=True, null=True)
    customname = models.TextField(blank=True, null=True)
    connectedmac = models.TextField(blank=True, null=True)
    devicetype = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    errorstatus = models.TextField(blank=True, null=True)
    uniqueidtype = models.TextField(blank=True, null=True)
    monitorprofile = models.IntegerField(blank=True, null=True)
    parserprofile = models.IntegerField(blank=True, null=True)
    locationprofile = models.IntegerField(blank=True, null=True)
    ingestionprofile = models.IntegerField(blank=True, null=True)

    markid = models.BigIntegerField(blank=True, null=True)
    modelid = models.BigIntegerField(blank=True, null=True)
    deviceverid = models.IntegerField(blank=True, null=True)
    creationdate = models.DateTimeField(blank=True, null=True)
    updatedate = models.DateTimeField(blank=True, null=True)
    virtualdeviceip = models.TextField(blank=True, null=True)
    devicenote = models.TextField(blank=True, null=True)
    snmpstatus = models.BooleanField(default=True)
    """
    scan status shows us log source status information about logging, its resource, editable etc;
    null    :   ?
    0       :   active logging log sources
    1       :   in staging & logging
    2       :   log source is added by auto scan service (in staging & NOT logging)
    3       :   log source is sent to staging manually by user to edit (in staging & logging)
    4       :   it's not in use for now !!!!
    5       :   log source is just added manually from UI (in staging & NOT logging)
    9       :   in history (NOT logging)
    """
    scanstatus = models.SmallIntegerField(blank=True, null=True, default=0)
    manuallyadded = models.BooleanField(default=True)  # all log sources added from here is manually added
    logsourceselection = models.TextField(blank=True, null=True)

    syslogtag = models.TextField(blank=True, default="")
    taglocation = models.TextField(blank=True, default="")
    facility = models.TextField(blank=True, null=True)

    sysuptime = models.TextField(blank=True, null=True)
    syscontact = models.TextField(blank=True, null=True)
    syslocation = models.TextField(blank=True, null=True)
    sysservices = models.TextField(blank=True, null=True)
    componentids = ArrayField(models.IntegerField(unique=True, blank=True, null=True))

    licenseused = ArrayField(models.IntegerField(blank=True, null=True))

    objects = Manager()

    def __str__(self):
        return f"{self.sourcename} named {self.logsourceselection}"

    def get_absolute_url(self):
        return reverse('edit_log_source', kwargs={'id': self.id})

    def get_logs_for_source_url(self):
        return reverse('inventories:logs_for_source', kwargs={'id': self.id})

    def get_ingestion_profile(self):
        if self.ingestionprofile is None or self.ingestionprofile == 0:
            _ingestion_profile = f"No valid ingestion profile"
        else:
            try:
                _ingestion_profile = IngestionProfile.objects.get(id=self.ingestionprofile)
            except ObjectDoesNotExist:
                _ingestion_profile = f"No valid ingestion profile for {self.ingestionprofile}"
            except Exception as err:
                _ingestion_profile = f"Couldn't find ingestion profile because {err}"
        return _ingestion_profile

    def get_monitor_profile(self):
        if self.monitorprofile is None or self.monitorprofile == 0:
            _monitor_profile = f"No valid monitor profile"
        else:
            try:
                _monitor_profile = MonitorProfileDetails.objects.get(id=self.monitorprofile)
            except ObjectDoesNotExist:
                _monitor_profile = f"No valid monitor profile for {self.ingestionprofile}"
            except Exception as err:
                _monitor_profile = f"Couldn't find monitor profile because {err}"
        return _monitor_profile

    def get_component_in(self):
        # if len(list(Components.objects.filter(logsources__contains=[self.id]))) > 1 or len(list(Components.objects.filter(logsources__contains=[self.id]))) == 0:
        #     _component = ""
        # else:
        #     _component = list(Components.objects.filter(logsources__contains=[self.id]))[0]
        # return _component
        # if self.componentids:
        #     _components = [Components.objects.get(id=_) for _ in self.componentids]
        # else:
        #     _components = []
        return [Components.objects.get(id=_) for _ in self.componentids] if self.componentids else []

    def get_application_in(self):
        # _result = self.get_component_in()
        # if _result != "":
        #     _result = _result.get_application_in()
        # return _result
        _result = []
        if self.componentids:
            for id in self.componentids:
                _result += Components.objects.get(id=id).get_application_in()
        return list(set(_result))

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def brand(self):
        _result = ""
        try:
            _result = DeviceMark.objects.get(id=self.markid)
        except Exception as err:
            # _result = f"Couldn't get brand info : {err}"
            _result = "-"
        return _result

    def brandModel(self):
        _result = ""
        try:
            _result = DeviceModel.objects.get(id=self.modelid)
        except Exception as err:
            # _result = f"Couldn't get model info : {err}"
            _result = "-"
        return _result

    def version(self):
        _result = ""
        try:
            _result = DeviceVersions.objects.get(id=self.deviceverid)
        except Exception as err:
            # _result = f"Couldn't get version info : {err}"
            _result = "-"
        return _result

    def mean_scan_status(self):
        """
        returns a meaningful sentence about the condition of log source is in staging, historical or normal collecting
        logs
        """
        _result = "LOGGING"
        if self.scanstatus in [1, 3]:
            _result = "IN STAGING - LOGGING"
        elif self.scanstatus == 2:
            _result = "IN STAGING - WAITING (New Auto-Scan)"
        elif self.scanstatus == 5:
            _result = "IN STAGING - WAITING (New Manually)"
        elif self.scanstatus == 9:
            _result = "IN HISTORY"
        return _result

    def isEditable(self):
        """
        checks if device in staging or history in this case return True, else False
        """
        _result = False
        # _result = True  # this line for test
        if self.scanstatus in [1, 2, 3, 5, 9]:
            _result = True
        return _result

    def isFirstEdit(self):
        """
        checks if device is added by ScanDeviceService in this case return True, else False
        """
        _result = False
        if self.scanstatus in [2]:
            _result = True
        return _result

    def get_unparsed_log_count(self):
        # from ATIBAreport.ElasticModels import es_host_list, es_port_number
        if self.uniqueid is not None and check_environment_for_elastic():
            # elastic_connection = Elasticsearch(host_list, scheme='http', port=9200, sniff_on_start=True,
            #                                    request_timeout=2)

            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number, sniff_on_start=True,
                                               request_timeout=2)

            try:
                # _body = '{"size":0,"query":{"bool":{"must":[{"term":{"mappedlogsource":{"value":"%s","boost":1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"_id":{"order":"desc"}}]}' % self.uniqueid
                # _body = json.loads(_body)
                # search = elastic_connection.search(index="atibaloglar", body=_body)
                # _count = int(search["hits"]["total"]["value"])
                _body = '{"query":{"bool":{"must":[{"term":{"mappedlogsource":{"value":"%s","boost":1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"_id":{"order":"desc"}}]}' % self.uniqueid
                _body = json.loads(_body)
                search = elastic_connection.search(index="atibaloglar", body=_body)
                _count = int(search["count"])
            except Exception as err:
                logger.warning(f"Couldn't get unparsed log count for {self.uniqueid}. Because {err}")
                _count = 0
        else:
            _count = self.get_queued_log_count()
        return _count

    def get_queued_log_count(self):
        if self.uniqueid is not None:
            try:
                _count = Logs.objects.filter(mappedlogsource=self.uniqueid).count()
            except Exception as err:
                _count = 0
        else:
            _count = 0
        return _count

    class Meta:
        managed = False
        db_table = 'logsources'
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['ipaddress', 'syslogtag'], name="syslogtag_control")]


class Components(models.Model):
    # id = models.BigAutoField(primary_key=True)
    componentname = models.TextField(blank=True, null=True)
    applicationids = ArrayField(models.IntegerField(unique=True, blank=True, null=True))

    objects = Manager()

    def __str__(self):
        return f"{self.componentname} named log source collection"

    def get_absolute_url(self):
        return reverse('edit_component', kwargs={'id': self.id})

    def get_log_sources(self):
        # _log_sources = []
        # if len(self.logsources) > 0:
        #     for _ in self.logsources:
        #         try:
        #             _log_sources.append(LogSources.objects.get(id=_))
        #         except Exception as err:
        #             logger.error(f"An error occurred trying to get {self.id} component log sources as : {err}")
        #             continue
        # return _log_sources
        return [_ for _ in LogSources.objects.all() if _.componentids and self.id in _.componentids]

    def get_application_in(self):
        # if len(list(Applications.objects.filter(componentids__contains=[self.id]))) > 1 or len(list(Applications.objects.filter(componentids__contains=[self.id]))) == 0:
        #     _application = ""
        # else:
        #     _application = list(Applications.objects.filter(componentids__contains=[self.id]))[0]
        # return _application
        return [Applications.objects.get(id=_) for _ in self.applicationids] if self.applicationids else []

    def add_sources(self, source_ids):
        _updt = 0
        if len(source_ids) > 0:
            for _id in source_ids:
                _source = LogSources.objects.get(id=_id)
                if _source.componentids:
                    _source.componentids.append(self.id)
                else:
                    _source.componentids = [self.id]
                _source.save()
                _updt += 1
        return _updt

    def remove_sources(self, source_ids):
        _updt = 0
        if len(source_ids) > 0:
            for _id in source_ids:
                _source = LogSources.objects.get(id=_id)
                if _source.componentids:
                    if len(_source.componentids) > 1:
                        _source.componentids.remove(self.id)
                    else:
                        _source.componentids = None
                _source.save()
                _updt += 1
        return _updt

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'components'
        ordering = ['-id']


class Applications(models.Model):
    # id = models.BigAutoField(primary_key=True)
    appname = models.TextField(blank=True, null=True)
    # componentids = ArrayField(models.IntegerField(unique=True, blank=True, null=True))

    objects = Manager()

    def __str__(self):
        return f"{self.appname} named component collection"

    def get_absolute_url(self):
        return reverse('edit_application', kwargs={'id': self.id})

    def get_components(self):
        # _components = []
        # if len(self.componentids) > 0:
        #     for _ in self.componentids:
        #         try:
        #             _components.append(Components.objects.get(id=_))
        #         except Exception as err:
        #             logger.error(f"An error occurred trying to get {self.id} application components as : {err}")
        #             continue
        # return _components
        return [_ for _ in Components.objects.all() if _.applicationids and self.id in _.applicationids]

    def add_components(self, component_ids):
        _updt = 0
        if len(component_ids) > 0:
            for _id in component_ids:
                _component = Components.objects.get(id=_id)
                if _component.applicationids:
                    _component.applicationids.append(self.id)
                else:
                    _component.applicationids = [self.id]
                _component.save()
                _updt += 1
        return _updt

    def remove_components(self, component_ids):
        _updt = 0
        if len(component_ids) > 0:
            for _id in component_ids:
                _component = Components.objects.get(id=_id)
                if _component.applicationids:
                    if len(_component.applicationids) > 1:
                        _component.applicationids.remove(self.id)
                    else:
                        _component.applicationids = None
                _component.save()
                _updt += 1
        return _updt

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'applications'
        ordering = ['-id']


class AnomaliesTemp(models.Model):
    credate = models.DateTimeField(blank=True, null=True)
    uniqueid = models.TextField(blank=True, null=True)
    logdefcode = models.IntegerField(blank=True, null=True)
    logcode = models.TextField(blank=True, null=True)
    logid = models.BigIntegerField(blank=True, null=True)
    deviceip = models.TextField(blank=True, null=True)

    object = Manager()

    def __str__(self):
        return f"AnomaliesTemp object for logcode {self.logcode}"

    class Meta:
        managed = False
        db_table = 'anomaliestemp'


class ParameterTypes(models.Model):

    parametertype = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    object = Manager()

    def __str__(self):
        # return f"ID: {self.id} TYPE: {self.parametertype} DESCRIPTION: {self.description}"
        return f"{self.parametertype} ({self.description})"

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'parametertypes'


class ParamVariables(models.Model):

    kod = models.CharField(verbose_name="Unique Variable Name (use lower case and don't use whitespaces !)",
                           blank=True, null=True, max_length=100)
    kodnote = models.CharField(verbose_name="Parameter Name", blank=True, null=True, max_length=100)
    valacceptreg = models.TextField(verbose_name="Regex to Confirm Variable", blank=True, null=True, default=None)
    isvalid = models.BooleanField(verbose_name="Is It a Valid Parameter", blank=True, null=True, default=True)
    codeorder = models.IntegerField(verbose_name="Order of Code", blank=True, null=True)
    paramtype = models.CharField(verbose_name="Group of Parameter Type", blank=True, null=True, max_length=100,
                                 default="0")
    hidevalue = models.BooleanField(verbose_name="Will this information be masked?",
                                    blank=True, null=True, default=False)  # it will use for mask values
    paramgroup = models.CharField(
        verbose_name="Unique Variable Name of Parameter Group (use lower case and don't use whitespaces !)",
        blank=True, null=True, max_length=100)
    correlationstatus = models.BooleanField(verbose_name="Will this information be used in correlation?",
                                            blank=True, null=True, default=None)
    # parametertypeid = models.IntegerField(verbose_name="Type of Parameter", blank=True, null=True, default=7)
    parametertypeid = models.ForeignKey(ParameterTypes, verbose_name="Type of Parameter", null=True,
                                        default=7, db_column='parametertypeid', on_delete=models.CASCADE)

    objects = Manager()

    def __str__(self):
        return f"{self.paramtype} / {self.kod}"

    def get_absolute_url(self):
        return reverse('edit_parameter_variable', kwargs={'id': self.id})

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'paramvariables'


class ApplicationVersion(models.Model):
    appname = models.TextField(unique=True)
    appversion = models.TextField(blank=True, null=True)
    appsubversion = models.TextField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"{self.appname} / {self.appversion}.{self.appsubversion}"

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'applicationversion'
        ordering = ['-id']


class AIParameters(models.Model):
    id = models.IntegerField()
    dummycode = models.TextField(primary_key=True)
    algorithmname = models.TextField(blank=True, null=True)
    val = models.IntegerField(blank=True, null=True)
    anomalycode = models.IntegerField(blank=True, null=True)
    pastsettings = ArrayField(models.IntegerField(blank=True, null=True))

    objects = Manager()

    def __str__(self):
        return f"Sensitivity for {self.algorithmname} ( value : {self.val}, changes in past : {self.pastsettings})"

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'aiparameters'
        ordering = ["anomalycode"]


class Incidents(models.Model):
    """
    this table carry anomalies in an incidents set
    """
    # id = models.IntegerField(primary_key=True)
    anomalies = ArrayField(models.IntegerField(blank=True, null=True))
    creationdate = models.DateTimeField(blank=True, null=True)
    lastupdatetime = models.DateTimeField(blank=True, null=True)
    closedate = models.DateTimeField(blank=True, null=True)
    isopen = models.BooleanField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        _condition = "Open" if self.isopen else "Closed"
        _string = f"generated at {self.lastupdatetime}" if self.isopen else f"solved at {self.closedate}"
        return f"{_condition} Incident Set ({_string}) :  {self.anomalies}"

    def get_summary(self):
        if self.isopen:
            _date = datetime.datetime.strftime(self.lastupdatetime, "%d/%m/%Y %H:%M:%S")
            _string = f"Open Incident Set. Generated {_date}"
        else:
            _date = datetime.datetime.strftime(self.closedate, "%d/%m/%Y %H:%M:%S")
            _string = f"Closed Incident Set. Closed {_date}"
        return _string

    def get_absolute_url(self):
        return reverse('diagnoses_for_incidentset', kwargs={'id': self.id})

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    def get_incident_logs(self):
        _icidentList = []
        _idList = self.anomalies
        _idList.sort(reverse=True)
        for incident in _idList:
            try:
                _log = AnomalyLogs.objects.get(id=incident)
            except ObjectDoesNotExist:
                _log = f"Couldn't find matching Anomaly Log with id : {incident}"
            _icidentList.append(_log)
        return _icidentList

    def get_rcgraphs(self):
        _rcgraphs = []
        try:
            _rcgraphs = list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2).filter(incidentid=self.id))
        except Exception as err:
            logger.exception(
                f"An error occurred trying to get rcgraphdetails for incident set with id {self.id}. ERROR IS : {err}")
        return _rcgraphs

    def get_root_devices(self):
        _devices = []
        if self.get_rcgraphs():
            for _ in self.get_rcgraphs():
                _devices += _.get_root_devices()
        return list(set(_devices))

    class Meta:
        managed = False
        db_table = 'incidents'
        ordering = ["-id"]


class AtibaHA(models.Model):
    """
    this table carry cluster structure information
    """
    # id = models.IntegerField(primary_key=True)
    ipaddress = models.TextField(verbose_name="HA IP Address", blank=True, null=True)
    uniqueid = models.TextField(verbose_name="HA Unique ID", blank=True, null=True)
    nodeid = models.TextField(verbose_name="Node ID", blank=True, null=True)
    elasticstatus = models.IntegerField(verbose_name="Status of ElasticSearch", blank=True, null=True)
    pgstatus = models.IntegerField(verbose_name="Status of PostgreSQL", blank=True, null=True)
    loggerstatus = models.IntegerField(verbose_name="Status of Logger Service", blank=True, null=True)
    hastate = models.IntegerField(verbose_name="HA State", blank=True, null=True, default=0)
    hamodel = models.IntegerField(verbose_name="HA Model", blank=True, null=True, default=1)
    vrid = models.IntegerField(verbose_name="Virtual Router ID", blank=True, null=True)
    vrrppriority = models.IntegerField(verbose_name="Virtual Router Priority", blank=True, null=True)
    vrip = models.TextField(verbose_name="Virtual Router IP", blank=True, null=True)
    interfacename = models.TextField(verbose_name="HA Interface Name", blank=True, null=True)
    advertint = models.IntegerField(verbose_name="", blank=True, null=True)
    vrrpauthtype = models.TextField(verbose_name="Virtual Router Authentication Type", blank=True, null=True)
    vrrpauthpass = models.TextField(verbose_name="Virtual Router Authentication Password", blank=True, null=True)
    loggerweight = models.IntegerField(verbose_name="", blank=True, null=True)
    loggerchecktimeout = models.IntegerField(verbose_name="", blank=True, null=True)
    loggerretry = models.IntegerField(verbose_name="", blank=True, null=True)
    loggerdelay = models.IntegerField(verbose_name="", blank=True, null=True)
    cpuusage = ArrayField(models.DecimalField(verbose_name="Server CPU Usage", max_digits=10, decimal_places=5,
                                              blank=True, null=True))
    ramusage = ArrayField(models.DecimalField(verbose_name="Server Ram Usage", max_digits=10, decimal_places=5,
                                              blank=True, null=True))
    diskusage = ArrayField(models.DecimalField(verbose_name="Server Disk Usage", max_digits=10, decimal_places=5,
                                               blank=True, null=True))
    updatetime = models.DateTimeField(verbose_name="Last Update", blank=True, null=True)
    usagecheckinterval = models.IntegerField(verbose_name="Usage Info Check Interval", blank=True, null=True,
                                             default=30)

    objects = Manager()

    def __str__(self):
        _status = "Master" if self.hastate == 1 else "Slave"
        return f"{_status} node with {self.interfacename} ip {self.ipaddress}"

    def is_master(self):
        return True if self.hastate == 1 else False

    def is_api_alive(self):
        _result = None
        _response_json = None
        _api_port = atibaApiService_PORT
        _api_key = atibaApiService_API_KEY
        try:
            response = requests.get(f"http://{self.ipaddress}:{_api_port}/health_check?api_key={_api_key}",
                                    timeout=0.2)
            # response = requests.get(f"http://localhost:{_api_port}/health_check?api_key={_api_key}",timeout=0.2)
            _response_json = response.json()
            logger.info(f"Api health response for {self.ipaddress} : {_response_json}")
            _result = True
        except Exception as err:
            logger.error(f"An error occurred trying to check api health on IP {self.ipaddress}. ERROR IS : {err}")
            _result = False
        return _result

    def get_absolute_url(self):
        return reverse('cluster_node_settings', kwargs={'id': self.id})

    def get_remove_url(self):
        return reverse('cluster_remove_slave', kwargs={'id': self.id})

    def get_add_slave_url(self):
        return reverse('cluster_add_slave', kwargs={'id': self.id})

    def get_make_slave_url(self):
        return reverse('cluster_make_it_slave', kwargs={'id': self.id})

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        managed = False
        db_table = 'atibaha'
        ordering = ["id"]


# """Calling a database function"""
class LogParseTestResult(models.Model):
    """
    object for take and carry the results of function on it. Use it for row queries to call logparsetest function
    """
    id = models.IntegerField(primary_key=True)
    rtext = models.TextField(blank=True, null=True)
    rlogdate = models.DateTimeField(blank=True, null=True)
    rstatuskod = models.IntegerField(blank=True, null=True)

    # results = LogParseTestFunction.as_manager()
    objects = Manager()

    def __str__(self):
        return f"id : {self.id} / rtext : {self.rtext} / rlogdate : {self.rlogdate} / rstatuscode : {self.rstatuskod}"

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        # db_table = 'logparsetest()'
        managed = False


# """Calling a database function"""
class AnomalyScoreDetection(models.Model):
    """
    object for take and carry the results of function on it. Use it for row queries to call logparsetest function
    """
    id = models.IntegerField(primary_key=True)
    anomalyscoredetection = models.DecimalField(max_digits=14, decimal_places=10, blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"id : {self.id} / anomaly Score : {self.anomalyscoredetection}"

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data

    class Meta:
        # db_table = 'anomalyscoretest()'
        managed = False


# """ Generating an object like usual log objects """
class ErrorLogsFromElastic:
    """
    This class defines an object for elasticsearch atibaloglar index records. It's not about the PSQL database
    operations, all about elasticsearch.
    """
    def __init__(self, _id, hit_object=None, dictionary=None, *args, **kwargs):
        if hit_object:
            _obj = hit_object
            self.id = _obj.id if hasattr(_obj, "id") else None
            self.severity = int(_obj.severity) if hasattr(_obj, "severity") else None
            self.classificationgroup = _obj.classificationgroup if hasattr(_obj, "classificationgroup") else None
            self.mappedlogsource = _obj.mappedlogsource if hasattr(_obj, "mappedlogsource") else None
            self.socketaddress = _obj.socketaddress if hasattr(_obj, "socketaddress") else None
            self.recstatus = int(_obj.recstatus) if hasattr(_obj, "recstatus") else None
            self.port = int(_obj.port) if hasattr(_obj, "port") else None
            self.logdata = _obj.logdata if hasattr(_obj, "logdata") else None
            self.recerror = _obj.recerror if hasattr(_obj, "recerror") else None
            self.inetaddress = _obj.inetaddress if hasattr(_obj, "inetaddress") else None
            self.tryjson = int(_obj.tryjson) if hasattr(_obj, "tryjson") else None
            try:
                self.olusturmatarih = datetime.datetime.strptime(
                    _obj.olusturmatarih, "%Y-%m-%d %H:%M:%S.%f") if hasattr(_obj, "olusturmatarih") else None
            except Exception:
                self.olusturmatarih = datetime.datetime.strptime(
                    _obj.olusturmatarih, "%Y-%m-%d %H:%M:%S") if hasattr(_obj, "olusturmatarih") else None
            try:
                self.logdate = datetime.datetime.strptime(
                    _obj.logdate, "%Y-%m-%d %H:%M:%S.%f") if hasattr(_obj, "logdate") else None
            except Exception:
                self.logdate = datetime.datetime.strptime(
                    _obj.logdate, "%Y-%m-%d %H:%M:%S") if hasattr(_obj, "logdate") else None

        elif dictionary:
            _obj = dictionary
            # self.id = int(_obj['_id'])
            self.id = int(_id)
            self.severity = int(_obj['severity']) if "severity" in _obj.keys() else None
            self.classificationgroup = _obj['classificationgroup'] if "classificationgroup" in _obj else None
            self.mappedlogsource = _obj['mappedlogsource'] if "mappedlogsource" in _obj else None
            self.socketaddress = _obj['socketaddress'] if "socketaddress" in _obj else None
            self.recstatus = int(_obj['recstatus']) if "recstatus" in _obj else None
            self.port = int(_obj['port']) if "port" in _obj else None
            self.logdata = _obj['logdata'] if "logdata" in _obj else None
            self.recerror = _obj['recerror'] if "recerror" in _obj else None
            self.inetaddress = _obj['inetaddress'] if "inetaddress" in _obj else None
            self.tryjson = int(_obj['tryjson']) if "tryjson" in _obj else None
            self.olusturmatarih = datetime.datetime.strptime(
                _obj['olusturmatarih'], "%Y-%m-%d %H:%M:%S.%f") if "olusturmatarih" in _obj else None
            try:
                self.logdate = datetime.datetime.strptime(
                    _obj['logdate'], "%Y-%m-%d %H:%M:%S.%f") if "logdate" in _obj else None
            except Exception:
                self.logdate = datetime.datetime.strptime(
                    _obj['logdate'], "%Y-%m-%d %H:%M:%S") if "logdate" in _obj else None

    def __str__(self):
        return f"Un-parsed log from source {self.mappedlogsource} elastic id : {self.id}"

    def get_absolute_url(self):
        return reverse('inventories:log_detail', kwargs={'id': self.id})

    def get_logsource(self):
        _logsurce = None
        if self.mappedlogsource:
            try:
                _logsurce = NetworkDevice.objects.get(uniqueid=self.mappedlogsource)
            except MultipleObjectsReturned:
                logger.warning(f"More than one log source found with uniqueid {self.mappedlogsource}")
            except ObjectDoesNotExist:
                logger.warning(f"No log source found with uniqueid {self.mappedlogsource}")
            except Exception as err:
                logger.error(f"An error occurred with uniqueid {self.mappedlogsource}. ERROR IS : {err}")
        return _logsurce

    def get_json(self):
        """
        to use objects in template with javascript;
        """
        data = {}
        for field in self._meta.local_fields:
            value = field.value_from_object(self)
            if is_protected_type(value):
                if value is None:
                    data[field.name] = ""
                elif type(value) is bool:
                    data[field.name] = "true" if value else "false"
                else:
                    data[field.name] = value
            else:
                data[field.name] = field.value_to_string(self)

        for field in self._meta.get_fields():
            if field.is_relation and field.many_to_many:
                data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]

        return data


# Drawing custom interval charts
class IntervalDataChart:
    """
    to draw custom interval charts ... I'll write a method update to update objects attribute values
    """
    labellist = []
    upperbound = []
    lowerbound = []
    count = []
    paramorcode = ""
    uniqueid = None
    startdate = None
    enddate = None

    def __init__(self, startdate=None, enddate=None, paramorcode="", uniqueid=None):
        _detail = []
        self.enddate = enddate if enddate else datetime.datetime.now()
        self.startdate = startdate if startdate else self.enddate - datetime.timedelta(days=1)
        self.paramorcode = paramorcode if paramorcode else ""
        if uniqueid:
            self.uniqueid = uniqueid
            if (paramorcode.startswith("<") and paramorcode.endswith(">")) or paramorcode.startswith("ATIBA"):
                logger.debug(f"Getting loginterval table for log code : {paramorcode}")
                _device_group_id = LogDeviceGroup.objects.filter(uniqueid=self.uniqueid, logno=self.paramorcode)[0].id
                logger.debug(f"  _device_group_id : {_device_group_id}")
                logger.debug(f"  startdate : {self.startdate}")
                logger.debug(f"  enddate : {self.enddate}")
                # .filter(timestart__lte=self.enddate).filter(timestart__gte=self.startdate)
                _detail = list(LogInterval.objects.filter(
                    logdevicegroupid=_device_group_id,
                    timestart__lt=(self.enddate + datetime.timedelta(hours=0.5)),
                    timestart__gt=(self.startdate - datetime.timedelta(hours=1))).order_by('timeepoch'))
            else:
                logger.debug(f"Getting parameterinterval table for parameter : {paramorcode}")
                _detail = list(ParameterInterval.objects.filter(
                    parameterdevicegroupid__in=LogDeviceParameters.objects.values_list("id", flat=True).filter(
                        uniqueid=self.uniqueid, parametername=self.paramorcode)).filter(
                    timestart__lt=(self.enddate + datetime.timedelta(hours=0.5))).filter(
                    timestart__gt=(self.startdate - datetime.timedelta(hours=1))).order_by('timeepoch'))
            # logger.debug(f"IntervalDataChart object constructor _detail list : {_detail}")
            for _ in _detail:
                if _.upperbound and _.lowerbound:
                    self.upperbound.append(float(_.upperbound))
                    self.lowerbound.append(float(_.lowerbound))
                    self.count.append(float(_.logcount))
                    # self.labellist.append(datetime.datetime.strftime(_.timestart, "%Y/%m/%d %H:%M:%S.%f"))
                    # self.labellist.append(_.timestart.strftime("%Y/%m/%d %H:%M:%S.%f"))
                    self.labellist.append(_.timestart.strftime("%Y/%m/%d %H:%M"))


    # def get_json(self):
    #     """
    #     to use objects in template with javascript;
    #     """
    #     data = {}
    #     for field in self._meta.local_fields:
    #         values = field.value_from_object(self)
    #         if len(values) > 0:
    #             for value in values:
    #                 if is_protected_type(value):
    #                     if value is None:
    #                         value = ""
    #                     elif type(value) is bool:
    #                         value = "true" if value else "false"
    #                     elif type(value) is decimal.Decimal:
    #                         value = float(value)
    #                     elif type(value) is datetime.datetime:
    #                         value = value.strftime("%Y/%m/%d %H:%M:%S.%f")
    #                     elif type(value) is datetime.time:
    #                         value = value.strftime("%H:%M:%S.%f")
    #                     # else:
    #                     #     data[field.name] = value
    #                 else:
    #                     data[field.name] = field.value_to_string(self)
    #             data[field.name] = values
    #
    #     for field in self._meta.get_fields():
    #         if field.is_relation and field.many_to_many:
    #             data[field.name] = [str(o.id) for o in getattr(self, field.name).all()]
    #
    #     return data
