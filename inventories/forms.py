import logging

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from crispy_forms.bootstrap import StrictButton

logger = logging.getLogger('views')


class ReportModulePrepare(forms.Form):
    pass


class AddDriver(forms.Form):
    driver_file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super(AddDriver, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_name = 'driverLoad'
        self.helper.form_id = 'driverLoad'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'POST'
        self.helper.enctype = "multipart/form-data"
        # self.helper.form_action = ''
        # self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-12'
        self.helper.layout = Layout(
            Field('driver_file', style="font-size:9pt;z-index:3;"),
            StrictButton('&#x271A; LOAD', css_class='btn btn-sm btn-outline-info col-md-12', type='submit',
                         style="font-size:9pt;"),
        )

    def clean(self):
        _file = self.cleaned_data.get('driver_file')
        logger.debug(f"file : {_file}")
        # logger.debug(f"file name split : {str(_file).endswith('tar.gz')}")
        file_name_parts = str(_file).split(".")
        logger.debug(f"file name split : {file_name_parts}")
        # file_extension = None
        # if len(file_name_parts) == 2:
        #     file_extension = file_name_parts[-1]
        # elif len(file_name_parts) > 2:
        #     file_extension = file_name_parts[-2]+"."+file_name_parts[-1]
        # if file_extension and file_extension == "tar.gz":
        #     logger.debug(f"extension : {file_extension}")
        if str(_file).endswith('tar.gz') or str(_file).endswith('tar'):
            logger.debug(f"Valid file : {str(_file)}")
        elif str(_file) != "None":
            logger.warning(f"Trying to add {str(_file)} Not valid driver file!!")
            raise forms.ValidationError('Not a valid driver file')
        else:
            raise forms.ValidationError('Not a valid driver file')
        return _file
