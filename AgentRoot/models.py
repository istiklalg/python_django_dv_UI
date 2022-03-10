
"""
@author : istiklal
Database models for newly creating report types
"""
import logging

from django.db import models
from django.db.models import Manager
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger('models')


class ReportBase(models.Model):
    """
    database to save reporting style
    """
    user = models.IntegerField(verbose_name="User ID that select this report type", blank=True, null=True)
    user_group = models.IntegerField(verbose_name="Group ID for licence over user groups", blank=True, null=True)
    report_name = models.TextField(verbose_name="Name that given by user", null=True, blank=True)
    report_format = models.TextField(verbose_name="List formatted report details", blank=True, null=True)
    report_type = models.TextField(verbose_name="List formatted report type details", blank=True, null=True)
    visual_format = models.TextField(verbose_name="Text formatted visual format details", blank=True, null=True)
    home_page = models.BooleanField(verbose_name="Do you want to see this on your home page?", default=False)
    mailing_interval = models.IntegerField(verbose_name="Email sending interval by days, if null ve don't send email",
                                           blank=True, null=True)
    creation_date = models.DateTimeField(verbose_name="Exact date & time report's creation",
                                         default=timezone.now)

    objects = Manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.report_name is None or self.report_name == "":
            self.report_name = f"report_{self.user}_{self.user_group}_{self.creation_date}"

    def __str__(self):
        return self.report_format

    def get_absolute_url(self):
        return reverse('inventories:report_detail', kwargs={'id': self.id})

    def get_delete_url(self):
        return reverse('inventories:delete_report_type', kwargs={'id': self.id})

    def name_change(self, name):
        self.report_name = name

    class Meta:
        ordering = ["-id", "user_group", "user", "home_page"]
        unique_together = (('user', 'report_format'),)


