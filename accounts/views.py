
"""
@author:istiklal
"""

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from ATIBAreport.project_common import get_system_hw_macaddress, calculate_permanent_license
from accounts.models import *
from inventories.views import template_message_show
from accounts.forms import *

logger = logging.getLogger('views')
timer = logging.getLogger('timer')

# @csrf_exempt
# def accounts_register(request):
#     users = User.objects.all()
#     logger.debug(f"{users}")
#     route = 'REGISTER'
#     form = RegisterForm(request.POST or None)
#     if form.is_valid():
#         _user = form.save(commit=False)
#         _password = form.cleaned_data.get("password1")
#         _user.set_password(_password)
#         if len(users) == 0:
#             _user.is_superuser = True
#         _user.date_joined = datetime.now()
#         _user.fullname = f"{_user.first_name} {_user.last_name}"
#         _user.save()
#         _new_user = authenticate(username=_user.username, password=_password)
#         login(request, _new_user)
#         return redirect('home')
#     context = {
#         'form': form, 'route': route,
#     }
#     return render(request, 'accounts/register_and_login.html', context)


@csrf_exempt
def accounts_login(request):
    time_triggered = datetime.datetime.now()
    route = "LOGIN"
    # logger.debug(f"before login request : {request.META}")
    if request.user.is_authenticated:
        logger.info(f'Hello  {request.user}')
        return redirect('home')

    form = LoginForm(request.POST or None)
    if form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        login(request, user)
        logger.info(f'**** Hello again : {user} -- {request.user}')
        # logger.debug(f'after login request : {request.META}')
        # return redirect('home')
        return redirect('check_license')

    context = {'form': form, 'route': route}
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'accounts/register_and_login.html', context)


@login_required
@csrf_exempt
def accounts_change_password(request):
    time_triggered = datetime.datetime.now()
    route = "CHANGE PASSWORD"
    _user = request.user

    form = PasswordChangeForm(request.POST or None, initial={"username": _user.username})
    if form.is_valid():
        _username = form.cleaned_data.get("username")
        if _username != _user.username:
            # raise forms.ValidationError('You can not change User Name !')
            template_message_show(request, 'warning', 'You can not change username here !')
            return render(request, 'accounts/forms.html', {'form': form, 'route': route})
        _password = form.cleaned_data.get("newpassword1")
        _user.set_password(_password)
        _user.save()
        template_message_show(request, 'success', 'Successfully changed your password')
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'accounts/forms.html', {'form': form, 'route': route})


@csrf_exempt
def accounts_logout(request):
    time_triggered = datetime.datetime.now()
    logger.info(f'See you again : {request.user.username}')
    logout(request)
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return redirect('accounts:accounts_login')


@login_required
@csrf_exempt
def add_license(request, exceed=None):
    time_triggered = datetime.datetime.now()
    route = "NEW LICENSE"
    systemIdentifier = get_system_hw_macaddress() if get_system_hw_macaddress() != "" else "No system identifier"
    form = AddLicenseForm(request.POST or None, initial={"identifier": systemIdentifier})

    if form.is_valid():
        # logger.debug(f"{form}")
        # logger.debug(f"{request.POST}")
        """
        'identifier': ['']
        'licstring': ['']
        """
        new_lic = AtibaLicense()
        new_lic.licenseStringPython = request.POST.get('licstring')
        _license_dict = json.loads(atiba_decrypt(new_lic.licenseStringPython))["atiba-license"]
        logger.debug(f"License Dict : {_license_dict}")
        _hw_mac_address = _license_dict["hw_mac_address"]
        # if json.loads(atiba_decrypt(new_lic.licenseStringPython))["atiba-license"]["license_type"] == "temporary":
        new_lic.lictype = _license_dict["license_type"]
        new_lic.productcodes = _license_dict["product_codes"] if "product_codes" in _license_dict else None
        if _license_dict["license_type"] == "temporary":
            # new_lic.lictype = "temporary"
            new_lic.expirationdate = datetime.datetime.strptime(_license_dict["exp_date"], "%d-%m-%Y")
            new_lic.isExpired = False
        try:
            new_lic.save()
            template_message_show(request, 'success', 'New License activated successfully')
        except Exception as err:
            logger.exception(f"An error occurred while trying to save new license. ERROR IS : {err}")
            template_message_show(request, 'error', 'Failed to activate new license')
        if new_lic.id:
            _product_sku_list = _license_dict["product_sku"]
            logger.debug(f"Product SKU : {_product_sku_list}")
            for product in _product_sku_list:
                logger.debug(f"Product : {product}")
                _device_kod = product["licdevtype"]
                logger.debug(f"Dev Type : {_device_kod}")
                _device_siralist = list(GeneralParameterDetail.objects.values_list("sira", flat=True).filter(kisakod="CIHAZTUR", ack=f"{_device_kod}"))
                logger.debug(f"Query result for sira {_device_siralist}")
                _device_sira = _device_siralist[0] if _device_siralist else None
                _device_liccount = int(product["liccount"])
                AtibaLicenseDetails.objects.create(atibaLic_id=new_lic.id, atibaid=_hw_mac_address, licname=product["licname"], lictypeid=int(_device_sira), liccount=_device_liccount)
                logger.debug(f"Lic detail created ... ")

    licenseList = AtibaLicense.objects.all()

    """
        Permanent license control and warnings
    """
    newsList = []

    if exceed:
        logger.warning(f"Exceed !! {exceed}")
        _exceed_sentence = "You need to add license. For now you can reduce active log sources by sending them to" \
                           " history. But this will be a temporary solution. "
        _exceed_sentence += " <a href='/log_source/'> Log Sources </a>"
        newsList = exceed["details"]
        newsList.insert(0, ("danger", _exceed_sentence))
    else:
        _active_temporary_license_list = list(AtibaLicense.objects.exclude(isExpired=True).filter(lictype="temporary"))
        if not _active_temporary_license_list:
            _exceed, _exceed_list = calculate_permanent_license()
            if _exceed:
                logger.warning(f"Exceed !! {_exceed_list}")
                _exceed_sentence = "As a temporary solution you can reduce active log sources by sending them to " \
                                   "history. But we suggest you add license. "
                _exceed_sentence += " <a href='/accounts/license/'> Add License </a>"
                newsList = _exceed_list
                newsList.insert(0, ("danger", _exceed_sentence))
    """
        End of permanent license control and warnings
    """

    context = {
        'route': route, 'form': form, 'licenseList': licenseList, 'newsList': newsList,
    }
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'accounts/forms.html', context)
