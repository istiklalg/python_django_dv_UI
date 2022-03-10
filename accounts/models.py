

"""
@author : istiklal
Database model for existing database structure
"""
import datetime
import json
import logging
import math
import subprocess
import jsonpickle
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import AbstractUser
from django.db.models import Manager, UniqueConstraint, Deferrable, Q
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils import timezone
from django.utils.encoding import is_protected_type

from ATIBAreport.project_common import atiba_decrypt
from inventories.models import GeneralParameterDetail

logger = logging.getLogger('models')


class User(AbstractUser):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(verbose_name="User Username", unique=True, max_length=20, db_column='kullanicikod')
    password = models.TextField(verbose_name="Password", db_column='sifre')
    first_name = models.CharField(verbose_name="Name", max_length=29, blank=True, null=True, db_column='ad')
    last_name = models.CharField(verbose_name="Surname", max_length=19, blank=True, null=True, db_column='soyad')
    fullname = models.CharField(verbose_name="Name and Surname", max_length=50, db_column='adsoyad')
    registry_number = models.CharField(verbose_name="User Registry Number", max_length=12, blank=True, null=True, db_column='sicilno')
    bolumkod = models.CharField(verbose_name="Department Code", max_length=5, blank=True, null=True)
    is_staff = models.BooleanField(verbose_name="is User Staff ?", default=True, db_column='yetki')
    is_active = models.BooleanField(verbose_name="User activity status", default=True, db_column='aktif')
    theme = models.CharField(max_length=30, blank=True, null=True, db_column='tema')
    is_superuser = models.BooleanField(verbose_name="Is Admin Level?", default=False, db_column='admin')
    date_joined = models.DateTimeField(db_column='olusturmatarih')
    last_login = models.DateTimeField(db_column='songiris')
    is_djangoUser = models.BooleanField(db_column='is_django', default=True)
    temsilci = models.BooleanField(blank=True, null=True)
    email = models.TextField(verbose_name="Email Address of User", db_column='emailaddr')
    localelang = models.CharField(max_length=5, blank=True, null=True)
    tammenu = models.BooleanField(default=True)
    dashboardstr = models.TextField(blank=True, null=True)
    dashudsgroupids = ArrayField(models.IntegerField(blank=True, null=True))
    dashudsseverities = ArrayField(models.BooleanField(blank=True, null=True))

    # objects = Manager()

    # def save(self):
    #     self.fullname = f"{self.first_name} {self.last_name}"
    #     self.save()

    def __str__(self):
        return self.username

    class Meta:
        managed = False
        db_table = 'kullanici'
        ordering = ['id']


class AtibaLicense(models.Model):

    licenseStringJava = models.TextField(blank=True, null=True, db_column="licstr")
    licenseStringPython = models.TextField(blank=True, null=True, db_column="pylicstr")
    isExpired = models.BooleanField(blank=True, null=True, db_column="isexpired")
    democount = models.IntegerField(blank=True, null=True, default=0)
    lictype = models.TextField(blank=True, null=True)
    expirationdate = models.DateField(blank=True, null=True)
    productcodes = ArrayField(models.TextField(blank=True, null=True))
    failoverdate = models.DateField(blank=True, null=True)

    objects = Manager()

    def __str__(self):
        return f"{self.lictype} license with id {self.id}"

    class Meta:
        managed = False
        db_table = 'atibalic'
        ordering = ['-id']

    def get_license_json(self):
        if self.licenseStringPython is not None and self.licenseStringPython != "":
            return json.loads(atiba_decrypt(self.licenseStringPython))["atiba-license"]
        else:
            return None

    def get_license_owner(self):
        if self.licenseStringPython is not None and self.licenseStringPython != "":
            return json.loads(atiba_decrypt(self.licenseStringPython))["atiba-license"]["customer_name"]
        else:
            return None

    def get_license_type(self):
        if self.licenseStringPython is not None and self.licenseStringPython != "":
            return json.loads(atiba_decrypt(self.licenseStringPython))["atiba-license"]["license_type"]
        else:
            return None

    def is_license_valid(self):
        _system_unique_string = ""
        try:
            _system_unique_bytes = subprocess.check_output(['sh', '/usr/local/bin/getmacaddr.sh'])
            _system_unique_string = _system_unique_bytes.decode("utf-8").replace("\n", "")
        except Exception as err:
            logger.error(f"An error occurred trying to get system hw_mac_address. ERROR IS {err}")
        if _system_unique_string != "":
            _licence_unique_string = json.loads(atiba_decrypt(self.licenseStringPython))["atiba-license"]["hw_mac_address"]
            if _system_unique_string == _licence_unique_string:
                return True
            else:
                logger.warning("License is not allowed for this location")
                return False
        else:
            logger.warning("Couldn't get system hw_mac_address")
            return False

    def is_converted_python(self):
        return True if self.licenseStringPython and self.licenseStringPython != "" else False

    def get_license_expiration(self):
        if self.licenseStringPython is not None and self.licenseStringPython != "":
            try:
                _expiration = json.loads(atiba_decrypt(self.licenseStringPython))["atiba-license"]["exp_date"]
            except Exception as err:
                _expiration = ""
            if _expiration != "":
                # return datetime.datetime.strptime(
                #     json.loads(atiba_decrypt(self.licenseStringPython))["atiba-license"]["exp_date"], "%d-%m-%Y")
                return datetime.datetime.strptime(_expiration, "%d-%m-%Y")
        else:
            return None

    def get_order(self):
        if self.licenseStringPython is not None and self.licenseStringPython != "":
            try:
                _order = json.loads(atiba_decrypt(self.licenseStringPython))["atiba-license"]["customer_po"]
            except Exception as err:
                _order = ""
            if _order != "":
                return _order
        else:
            return None

    def get_product_list(self):
        _list = []
        if self.licenseStringPython is not None and self.licenseStringPython != "":
            try:
                _list = (json.loads(atiba_decrypt(self.licenseStringPython))["atiba-license"]["product_sku"])
            except Exception as err:
                _list = [{"licname": "None", "licdevtype": "None", "liccount": 0}]
        return _list


class AtibaLicenseDetails(models.Model):
    # license id
    atibaLic = models.ForeignKey(AtibaLicense, verbose_name="License", related_name="licdetails",
                                 db_column="atibalicid", on_delete=models.CASCADE)
    # unique identifier string of machine
    atibaid = models.TextField(verbose_name="Unique identifier of system hardware")
    licname = models.TextField(verbose_name="ATIBA product code")
    # device sira column value for licdevtype in license. It's comes from GeneralParameterDetail table
    # kısakod = 'CIHAZTUR', ack = given kod in license
    lictypeid = models.IntegerField(verbose_name="License device type order no")
    # liccount in license
    liccount = models.IntegerField(verbose_name="License device type count limit")
    # usedcount = models.IntegerField(verbose_name="Device type count in use")

    objects = Manager()

    def __str__(self):
        return f"According to {self.atibaLic} for {self.lictypeid} type limit {self.liccount}"

    class Meta:
        managed = False
        db_table = 'atibalicdetails'
        ordering = ['atibaLic_id', '-id']


# class LicenseControl:
#
#     def __init__(self, values_tuple, *args, **kwargs):
#         self.gpdsira = values_tuple[0]
#         self.gpdkod = values_tuple[1]
#         self.amountinuse = values_tuple[2] if values_tuple[2] else 0
#         self.amountlimit = values_tuple[3] if values_tuple[3] else 0
#         if self.gpdkod in ["STORAGE", "ACCPNT"]:
#             self.isExceeded = self.amountinuse > self.amountlimit*1.1
#         else:
#             self.isExceeded = self.amountinuse > self.amountlimit
#         self.status = f"License exceed for {self.gpdkod} !" if self.isExceeded else f"{self.gpdkod} in license limits"
#
#     def __str__(self):
#         return f"{self.status} (limit : {self.amountlimit}, inuse : {self.amountinuse})"


# class SystemUsersRole(models.Model):
#
#     # verbose_name = "System User"
#     userID = models.ForeignKey(User, db_column="kullaniciid", db_index=False, on_delete=models.CASCADE, related_name="userRole")
#
#     # kullaniciid = models.BigIntegerField(verbose_name="", primary_key=True)  # use systemUser_id for column values
#
#     # verbose_name = "System User User Role ID",
#     roleid = models.BigIntegerField(blank=True, null=True)
#
#     objects = Manager()
#
#     def __str__(self):
#         return str(self.roleid)
#
#     class Meta:
#         managed = False
#         db_table = 'kullanicirol'
#         unique_together = (('userID_id', 'roleid'),)
#
#
# class MailDefinition(models.Model):
#
#     # id = models.BigAutoField(verbose_name="", primary_key=True)
#
#     # verbose_name = "Mail Definition Flag",
#     definition = models.TextField(blank=True, null=True)
#     # verbose_name = "Subject Field of Mail",
#     tosubject = models.TextField(blank=True, null=True)
#     # verbose_name = "Types of Detected Anomalies",
#     anomalytypes = models.TextField(blank=True, null=True)
#
#     objects = Manager()
#
#     def __str__(self):
#         return self.definition
#
#     class Meta:
#         managed = False
#         db_table = 'maildefinition'
#
#
# class MailingList(models.Model):
#
#     # id = models.BigAutoField(verbose_name="", primary_key=True)
#
#     # verbose_name = "Mail Definition ID Key"
#     mail = models.ForeignKey(MailDefinition, db_column="mailid", db_index=False, on_delete=models.CASCADE,
#                              related_name="mailingList")
#
#     # foreignkey references; use mail_id for values of this column;
#     # mailid = models.BigIntegerField(verbose_name="Mail Primary ID Key", blank=True, null=True)
#
#     # verbose_name = "Receiver for Mailing",
#     touser = models.TextField(blank=True, null=True)
#     # verbose_name = "Subject of Mail",
#     tosubject = models.TextField(blank=True, null=True)
#     # verbose_name = "Creation Date of Mail",
#     creationdate = models.DateTimeField(blank=True, null=True)
#     # verbose_name = "Sending Date of Mail",
#     senddate = models.DateTimeField(blank=True, null=True)
#     # verbose_name = "Content of Mail",
#     tocontent = models.TextField(blank=True, null=True)
#
#     objects = Manager()
#
#     def __str__(self):
#         return self.tosubject
#
#     class Meta:
#         managed = False
#         db_table = 'maillist'
#
#
# class MailUsers(models.Model):
#
#     # id = models.BigAutoField(verbose_name="", primary_key=True)
#
#     # verbose_name = "Mail Definition ID Key"
#     mail = models.ForeignKey(MailDefinition, db_column="mailid", db_index=False, on_delete=models.CASCADE,
#                              related_name="mailUsers")
#     # foreignkey references;  use mail_id for values of this column;
#     # mailid = models.BigIntegerField(verbose_name="Mail Primary ID Key", blank=True, null=True)
#
#     # verbose_name = "System User Descriptions",
#     userdesc = models.TextField(blank=True, null=True)
#
#     objects = Manager()
#
#     def __str__(self):
#         return self.userdesc
#
#     class Meta:
#         managed = False
#         db_table = 'mailusers'
#
#
# class Menus(models.Model):
#
#     # id = models.BigAutoField(verbose_name="", primary_key=True)
#
#     # verbose_name = "Name of Menu",
#     menuname = models.CharField(max_length=50, blank=True, null=True)
#     # verbose_name = "Hints of Menu Types",
#     menutip = models.CharField(max_length=2, blank=True, null=True)
#     # verbose_name = "Menu Form ID",
#     formid = models.BigIntegerField(blank=True, null=True)
#     # verbose_name = "Upper Menu Hint Number",
#     ustmenu = models.BigIntegerField(blank=True, null=True)
#     # verbose_name = "Place in Queue",
#     sira = models.IntegerField(blank=True, null=True)
#     # verbose_name = "Menu Selection Links",
#     link = models.CharField(max_length=20, blank=True, null=True)
#
#     objects = Manager()
#
#     def __str__(self):
#         return self.menuname
#
#     class Meta:
#         managed = False
#         db_table = 'menuler'
