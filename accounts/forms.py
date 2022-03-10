import json
import logging
import datetime

from django import forms
# from django.contrib import auth
from django.contrib.auth import authenticate

from ATIBAreport.project_common import atiba_decrypt
from accounts.models import User, AtibaLicense
from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field

logger = logging.getLogger('views')


class RegisterForm(forms.ModelForm):
    username = forms.CharField(max_length=20, label='User Name')
    first_name = forms.CharField(max_length=50, label='First Name')
    last_name = forms.CharField(max_length=50, label='Last Name')
    email = forms.EmailField(max_length=50, label='E-mail Address')
    password1 = forms.CharField(max_length=50, label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(max_length=50, label='Password verification', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'password1', 'password2',
        ]

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match !')
        return password2

    def clean_username(self):
        _username = self.cleaned_data.get('username')
        _usernames = [_.username for _ in User.objects.all()]

        if _username in _usernames:
            raise forms.ValidationError('{} username is already used, please choose another username'.format(_username))
        return _username

    def clean_email(self):
        _email = self.cleaned_data.get('email')
        _emails = [_.email for _ in User.objects.all()]
        if _email in _emails:
            raise forms.ValidationError('{} email address being used'.format(_email))
        return _email


class LoginForm(forms.Form):
    username = forms.CharField(max_length=20, label='USER NAME')
    password = forms.CharField(max_length=50, label='PASSWORD', widget=forms.PasswordInput)

    def clean(self):
        _username = self.cleaned_data.get('username')
        _password = self.cleaned_data.get('password')
        if _username and _password:
            _user = authenticate(username=_username, password=_password)
            if not _user:
                raise forms.ValidationError('Username or password is wrong !')
        return super(LoginForm, self).clean()


class PasswordChangeForm(forms.Form):
    username = forms.CharField(max_length=20, label='User Name')
    oldpassword = forms.CharField(max_length=50, label='Current Password', widget=forms.PasswordInput)
    newpassword1 = forms.CharField(max_length=50, label='New Password', widget=forms.PasswordInput)
    newpassword2 = forms.CharField(max_length=50, label='New Password verification', widget=forms.PasswordInput)

    def clean_oldpassword(self):
        _username = self.cleaned_data.get('username')
        _current_password = self.cleaned_data.get('oldpassword')
        if _username and _current_password:
            _user = authenticate(username=_username, password=_current_password)
            if not _user:
                raise forms.ValidationError('Check your current password !')
        elif not _username or not _current_password:
            raise forms.ValidationError('Write your current password !')
        return _current_password

    def clean_newpassword2(self):
        password1 = self.cleaned_data.get('newpassword1')
        password2 = self.cleaned_data.get('newpassword2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('New passwords do not match !')
        return password2


class AddLicenseForm(forms.Form):
    identifier = forms.CharField(max_length=120, label="Your Identifier Key")
    licstring = forms.CharField(label="Your License Key", widget=forms.Textarea(attrs={"rows": 5, "cols": 20}))

    def __init__(self, *args, **kwargs):
        super(AddLicenseForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_name = 'licenseAdd'
        self.helper.form_id = 'licenseAdd'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'POST'
        self.helper.form_action = 'submit'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.layout = Layout(
            Field('identifier', style="font-size:9pt;", autocomplete='off'),
            Field('licstring', style="font-size:9pt;", autocomplete='off', rows=3),
            StrictButton('&#x271A; ADD {{route}}', css_class='btn btn-sm btn-outline-info', type='submit',
                         style="font-size:9pt;"),
        )

    def clean(self):
        licstring = self.cleaned_data.get('licstring')
        identifier = self.cleaned_data.get('identifier')
        licstring_list = AtibaLicense.objects.values_list(
            "licenseStringPython", flat=True).filter(licenseStringPython__isnull=False)
        logger.debug(f"List of active license string : {licstring_list}")
        _license_dict = None
        _expiration_date = None
        _customer_po = None
        _customer_name = None
        _license_type = None
        _product_codes = []
        # logger.debug("in clean function")
        try:
            _license_dict = json.loads(atiba_decrypt(licstring))["atiba-license"]
            _identifier_in_license = _license_dict["hw_mac_address"] if "hw_mac_address" in _license_dict else None
            _customer_po = _license_dict["customer_po"] if "customer_po" in _license_dict else None
            _customer_name = _license_dict["customer_name"] if "customer_name" in _license_dict else None
            _license_type = _license_dict["license_type"] if "license_type" in _license_dict else None
            _product_codes = _license_dict["product_codes"] if "product_codes" in _license_dict else []
        except Exception as err:
            logger.warning(f"License key is not valid. {err}")
            raise forms.ValidationError('License key is not valid')

        if licstring in licstring_list:
            logger.warning(f"{licstring} license key is already in use")
            raise forms.ValidationError('License key is already in use')

        if not _customer_name or not _customer_name.strip():
            logger.critical(f"License customer info is not valid !! CONTENT : '{_customer_name}'")
            raise forms.ValidationError("License key has not valid customer information")

        if _customer_po:
            _customer_po_parts = _customer_po.split("-")
            try:
                _poDate = datetime.datetime.strptime(_customer_po_parts[1], "%Y%m%d")
                # if _poDate > datetime.datetime.now() or len(_customer_po_parts[1]) != 2 or len(_customer_po_parts) != 3:
                #     raise forms.ValidationError('License key order code is not valid')
            except Exception as err:
                logger.critical(f"Purchase order date is not valid !! CONTENT : {_customer_po_parts[1]} ERROR : {err}")
                raise forms.ValidationError('License key order code is not valid')
        else:
            raise forms.ValidationError('License key has not valid order code')

        try:
            _expiration_date = datetime.datetime.strptime(_license_dict["exp_date"], "%d-%m-%Y")
        except Exception as err:
            logger.error(f"Couldn't take expiration, because : {err}")

        if _license_type == "temporary":
            if not _expiration_date:
                raise forms.ValidationError('Expiration date is missing for demo license !!')
            _active_temporary_licenses = list(AtibaLicense.objects.values_list("productcodes", flat=True).filter(
                lictype="temporary", isExpired=False))
            if _product_codes and _product_codes in _active_temporary_licenses:
                raise forms.ValidationError('You already have a temporary license for this product')

        if _expiration_date and (_expiration_date - datetime.datetime.now()).days <= 0:
            raise forms.ValidationError('License key has expired')

        if identifier != _identifier_in_license:
            raise forms.ValidationError('License key is not yours')

        return licstring
