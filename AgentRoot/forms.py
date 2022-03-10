from ATIBAreport.project_common import check_special_chars
from inventories.models import SystemParameters, ParamVariables, MailSettings, MailDetails, DeviceMark, DeviceModel, \
    DeviceVersions, DeviceTypeList, Components, Applications, DevLocations
from crispy_forms.bootstrap import StrictButton
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Field, HTML


class SystemParameterSettingsForm1(forms.ModelForm):
    class Meta:
        model = SystemParameters
        fields = (
            'loglifetime',
            'errstatloglife',
            'alertlife',
            'newbehaviortime',
            'timeseriesinterval',
            'corepointthreshold',
            'corepiecethreshold',
            'incpiecethreshold',
            'incidenttimeout',
            'autoparaminterval',
            'autoparamtime',
        )

    def __init__(self, *args, **kwargs):
        super(SystemParameterSettingsForm1, self).__init__(*args, **kwargs)
        self.fields['loglifetime'].required = True
        self.fields['errstatloglife'].required = True
        self.fields['alertlife'].required = True
        self.fields['newbehaviortime'].required = True
        self.fields['timeseriesinterval'].required = True
        self.fields['corepointthreshold'].required = True
        self.fields['corepiecethreshold'].required = True
        self.fields['incpiecethreshold'].required = True
        self.fields['incidenttimeout'].required = True
        self.fields['autoparaminterval'].required = True
        self.fields['autoparamtime'].required = True
        self.helper = FormHelper()
        self.helper.form_name = 'systemParamSettingsForm1'
        self.helper.form_id = 'changeParamsForm1'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'POST'
        self.helper.form_action = 'submit'
        self.helper.label_class = 'col-md-6'
        self.helper.field_class = 'col-md-6'
        self.helper.layout = Layout(
            Fieldset('LIFETIMES IN ATIBA',
                     Field('loglifetime', style='font-size:9pt;'),
                     Field('errstatloglife', style='font-size:9pt;'),
                     Field('alertlife', style='font-size:9pt;'),
                     Field('newbehaviortime', style='font-size:9pt;'),
                     Field('timeseriesinterval', style='font-size:9pt;'),
                     Field('incidenttimeout', style='font-size:9pt;'),
                     ),
            Fieldset('SCHEDULED SERVICES',
                     Field('autoparaminterval', style='font-size:9pt;'),
                     Field('autoparamtime', style='font-size:9pt;',
                           pattern="^(?:(?:([01]?\d|2[0-3]):)?([0-5]?\d):)?([0-5]?\d)$"),
                     ),
            Fieldset('AI STATIC THRESHOLDS',
                     Field('corepointthreshold', style='font-size:9pt;'),
                     Field('corepiecethreshold', style='font-size:9pt;'),
                     Field('incpiecethreshold', style='font-size:9pt;'),
                     ),
            StrictButton('SAVE', css_class='btn-outline-info btn-sm', type='submit'),
        )

    def clean_loglifetime(self):
        loglifetime = self.cleaned_data.get('loglifetime')
        if not 7 < loglifetime < 366:
            raise forms.ValidationError('Value must be in range [8, 365]')
        return loglifetime

    def clean_errstatloglife(self):
        errstatloglife = self.cleaned_data.get('errstatloglife')
        if not 4 < errstatloglife < 15:
            raise forms.ValidationError('Value must be in range [5, 14]')
        return errstatloglife

    def clean_alertlife(self):
        loglifetime = self.cleaned_data.get('loglifetime')
        alertlife = self.cleaned_data.get('alertlife')
        if loglifetime:
            if not 5 < alertlife <= loglifetime:
                raise forms.ValidationError(f'Value must be in range [6, {loglifetime}]')
        else:
            if not 5 < alertlife <= 365:
                raise forms.ValidationError(f'Value must be in range [6, 365]')
        return alertlife

    def clean_newbehaviortime(self):
        alertlife = self.cleaned_data.get('alertlife')
        loglifetime = self.cleaned_data.get('loglifetime')
        newbehaviortime = self.cleaned_data.get('newbehaviortime')

        if alertlife:
            if not 5 < newbehaviortime <= alertlife:
                raise forms.ValidationError(f'Value must be in range [6, {alertlife - 1}]')
        elif loglifetime:
            if not 5 < newbehaviortime <= loglifetime:
                raise forms.ValidationError(f'Value must be in range [6, {loglifetime - 1}]')
        else:
            if not 5 < newbehaviortime <= 365:
                raise forms.ValidationError(f'Value must be in range [6, 365]')
        return newbehaviortime

    def clean_incidenttimeout(self):
        incidenttimeout = self.cleaned_data.get('incidenttimeout')
        if incidenttimeout > 1800:
            raise forms.ValidationError(f'Value must be in range [1, 1800] as seconds')
        return incidenttimeout


class ParamVariablesForm(forms.ModelForm):
    class Meta:
        model = ParamVariables
        fields = (
            'kod',
            'kodnote',
            'valacceptreg',
            'isvalid',
            'codeorder',
            'paramtype',  # Group of parameter type
            # 'hidevalue',
            'paramgroup',
            # 'correlationstatus',
            'parametertypeid'  # parameter type
        )

    def __init__(self, *args, **kwargs):
        super(ParamVariablesForm, self).__init__(*args, **kwargs)
        self.fields['kod'].required = True
        self.fields['kodnote'].required = True
        # self.fields['valacceptreg'].required = True
        # self.fields['isvalid'].required = True
        self.fields['codeorder'].required = True
        self.fields['paramtype'].required = True
        # self.fields['hidevalue'].required = True
        self.fields['paramgroup'].required = True
        # self.fields['correlationstatus'].required = True
        self.helper = FormHelper()
        self.helper.form_name = 'paramVariablesForm'
        self.helper.form_id = 'paramVariablesForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'POST'
        self.helper.form_action = 'submit'
        self.helper.label_class = 'col-md-6'
        self.helper.field_class = 'col-md-6'
        self.helper.layout = Layout(
            Fieldset('Variable Form',
                     Field('kod', style="font-size:9pt;"),
                     Field('kodnote', style="font-size:9pt;"),
                     Field('valacceptreg', style="font-size:9pt;", rows=3),
                     Field('isvalid', style="font-size:9pt;"),
                     Field('codeorder', style="font-size:9pt;"),
                     Field('paramtype', style="font-size:9pt;", list="paramtype_choices"),  # group of parameter type
                     Field('parametertypeid', style="font-size:9pt;", list="paramtype_choices"),  # type of parameter
                     # Field('hidevalue', style="font-size:9pt;"),
                     Field('paramgroup', style="font-size:9pt;"),
                     # Field('correlationstatus', style="font-size:9pt;")
                     ),
            StrictButton('SAVE', css_class='btn-outline-info btn-sm', type='submit', style="float:right;"),
        )

    def clean_kod(self):
        kod = self.cleaned_data.get('kod')
        _kodList = list(ParamVariables.objects.values_list('kod', flat=True))
        if self.instance.id:
            _kodList.remove(self.instance.kod)

        if kod in _kodList:
            raise forms.ValidationError(f'This variable is in not unique !!')

        if check_special_chars(kod):
            raise forms.ValidationError(f'Do not use special chars in here !!')

        if not kod.islower():
            raise forms.ValidationError(f'Do not use upper case of chars in here !!')
        return kod

    def clean_paramgroup(self):
        paramgroup = self.cleaned_data.get('paramgroup')
        if check_special_chars(paramgroup):
            raise forms.ValidationError(f'Do not use special chars in here !!')
        if not paramgroup.islower():
            raise forms.ValidationError(f'Do not use upper case of chars in here !!')
        return paramgroup

    def clean_kodnote(self):
        kodnote = self.cleaned_data.get('kodnote')
        if check_special_chars(kodnote, list_of_exceptions=[" "]):
            raise forms.ValidationError(f'Do not use special chars in here !!')
        return kodnote


class AddNodeForm(forms.Form):
    newnodes = forms.CharField(label="New Node(s) eth0 IPs", max_length=100)

    class Meta:
        fields = 'newnodes'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['newnodes'].required = True
        # self.validators = [self.clean_newnodes]
        self.helper = FormHelper()
        self.helper.form_name = 'addNodeForm'
        self.helper.form_id = 'addNodeForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'POST'
        self.helper.form_action = ''
        self.helper.label_class = 'col-md-4'
        self.helper.field_class = 'col-md-8'
        self.helper.layout = Layout(
            Fieldset(
                "ADD NEW BACKUP NODE(S)",
                Field('newnodes', style="font-size:9pt;"),
                HTML("<small style='color:red;'>NOTE THAT : You can add more than one IP by separating them with "
                     "commas</small>"),
            ),
            HTML("<br />"),
            StrictButton('START PROCESS', css_class='btn-outline-info btn-sm', type='submit'),
        )

    def clean_newnodes(self):
        newnodes = self.cleaned_data.get('newnodes')
        # print(f" --------------------------- {newnodes}")
        newnodes = newnodes.replace(" ", "")
        new_ips = newnodes.split(",")
        # print(f" --------------------------- {new_ips}")
        for ip in new_ips:
            ip_parts = ip.split(".")
            if len(ip_parts) != 4:
                # print(f" --------------------------- {ip_parts} - {len(ip_parts)}")
                raise forms.ValidationError(f'Invalid ip address. Ip address should consist of 4 parts')
            else:
                for part in ip_parts:
                    if len(part) > 3:
                        # print(f" --------------------------- {part} - {len(part)}")
                        raise forms.ValidationError(f'Invalid ip address. Each part must be less than 4')
                    else:
                        try:
                            int(part)
                        except Exception as err:
                            # print(f" --------------------------- {err}")
                            raise forms.ValidationError(f'Invalid char usage in ip address')
                        if int(part) > 255:
                            # print(f" --------------------------- {part}")
                            raise forms.ValidationError(f"Invalid ip address part. It' greater than 255")
        return newnodes


class MailSettingsForm(forms.ModelForm):

    class Meta:
        model = MailSettings
        fields = (
            'touser',
            'mailtype',
            'starttls',
            'mailport',
            'fromuser',
            'frompass',
            'auth',
            'mailserver',
        )
        widgets = {
            'touser': forms.TextInput(),
            'mailtype': forms.Select(choices=[("SMTP", "SMTP"), ("POP3", "POP3")]),
            'fromuser': forms.TextInput(),
            'frompass': forms.TextInput(attrs={"type": "password"}),
            # 'mailserver': forms.GenericIPAddressField(attrs={"prptocol": "both"}),
            'mailserver': forms.TextInput()
        }

    def __init__(self, *args, **kwargs):
        super(MailSettingsForm, self).__init__(*args, **kwargs)
        self.fields['touser'].required = True
        self.fields['mailtype'].required = True
        self.fields['starttls'].required = True
        self.fields['mailport'].required = True
        self.fields['fromuser'].required = True
        self.fields['frompass'].required = True
        self.fields['auth'].required = True
        self.fields['mailserver'].required = True
        self.helper = FormHelper()
        self.helper.form_name = 'mailSettingsForm'
        self.helper.form_id = 'mailSettingsForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'POST'
        # self.helper.form_action = 'submit'
        self.helper.label_class = 'col-md-6'
        self.helper.field_class = 'col-md-6'
        self.helper.layout = Layout(
            Fieldset("Settings of Sending E-mail",
                     Field('touser', style='font-size:9pt;', rows=1),
                     Field('mailtype', style='font-size:9pt;', rows=1),
                     Field('starttls', style='font-size:9pt;'),
                     Field('mailport', style='font-size:9pt;'),
                     Field('fromuser', style='font-size:9pt;', rows=1),
                     Field('frompass', style='font-size:9pt;', rows=1),
                     Field('auth', style='font-size:9pt;'),
                     Field('mailserver', style='font-size:9pt;', rows=1),
                     ),
            StrictButton('SAVE', css_class='btn-outline-info btn-sm', type='submit'),
        )


class MailDetailsForm(forms.ModelForm):

    class Meta:
        model = MailDetails
        fields = (
            'lstype',
            'lsvendor',
            'lsmodel',
            'lsversion',
            'service',
            'application',
            'lslocation',
            'anomalylevel',
            'typetosend',
            'mailsetting',
        )
        widgets = {
            # 'lstype': forms.Select(choices=[(None, "--")]+list(DeviceTypeList.objects.values_list("devicetypecode", "devicetype"))),
            'lstype': forms.Select(choices=[(None, "--")]+list(set(DeviceTypeList.objects.values_list("devicetypecode", "devicetypecode")))),
            'lsvendor': forms.Select(choices=[(None, "--")]+list(DeviceMark.objects.values_list("markname", "markname"))),
            'lsmodel': forms.Select(choices=[(None, "--")]+list(DeviceModel.objects.values_list("modelname", "modelname"))),
            'lsversion': forms.Select(choices=[(None, "--")]+list(set(DeviceVersions.objects.values_list("versioncode", "versioncode")))),
            'service': forms.Select(choices=[(None, "--")]+list(Components.objects.values_list("componentname", "componentname"))),
            'application': forms.Select(choices=[(None, "--")]+list(Applications.objects.values_list("appname", "appname"))),
            'lslocation': forms.Select(choices=[(None, "--")]+list(DevLocations.objects.values_list("locationname", "locationname"))),
            # 'anomalylevel': forms.Select(choices=[("0", "--")]),
            'anomalylevel': forms.TextInput(attrs={"type": "number", "value": "0"}),
            'typetosend': forms.Select(choices=[("", "--"), ("ALERT", "ALERT"), ("INCIDENT", "INCIDENT")]),
            'mailsetting': forms.Select(choices=list(MailSettings.objects.values_list("id", "touser"))),
            # 'mailsetting': forms.Select(choices=[("ID", "STRING"), ("SMTP", "SMTP"), ("POP3", "POP3")]),
            # 'touser': forms.TextInput(),
            # 'mailtype': forms.Select(choices=[("SMTP", "SMTP"), ("POP3", "POP3")]),
            # 'fromuser': forms.TextInput(),
            # 'frompass': forms.TextInput(attrs={"type": "password"}),
            # # 'mailserver': forms.GenericIPAddressField(attrs={"prptocol": "both"}),
            # 'mailserver': forms.TextInput()
        }

    def __init__(self, *args, **kwargs):
        super(MailDetailsForm, self).__init__(*args, **kwargs)
        # self.fields['lstype'].required = True
        # self.fields['lsvendor'].required = True
        # self.fields['lsmodel'].required = True
        # self.fields['lsversion'].required = True
        # self.fields['service'].required = True
        # self.fields['application'].required = True
        # self.fields['lslocation'].required = True
        # self.fields['anomalylevel'].required = True
        # self.fields['typetosend'].required = True
        self.fields['mailsetting'].required = True
        self.helper = FormHelper()
        self.helper.form_name = 'mailDetailsForm'
        self.helper.form_id = 'mailDetailsForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'POST'
        self.helper.label_class = 'col-md-6'
        self.helper.field_class = 'col-md-6'
        self.helper.layout = Layout(
            Fieldset("Details of Sending E-mail",
                     Field('lstype', style='font-size:9pt;'),
                     Field('lsvendor', style='font-size:9pt;'),
                     Field('lsmodel', style='font-size:9pt;'),
                     Field('lsversion', style='font-size:9pt;'),
                     Field('service', style='font-size:9pt;'),
                     Field('application', style='font-size:9pt;'),
                     Field('lslocation', style='font-size:9pt;'),
                     Field('anomalylevel', style='font-size:9pt;'),
                     Field('typetosend', style='font-size:9pt;'),
                     Field('mailsetting', style='font-size:9pt;'),
                     ),
            StrictButton('SAVE', css_class='btn-outline-info btn-sm', type='submit'),
        )
