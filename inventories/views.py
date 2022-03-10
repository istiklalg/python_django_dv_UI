import _thread
import io
import locale
# import json
# import math
import tarfile
import tracemalloc

import django.apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin

from ATIBAreport.decorators import licence_required
from ATIBAreport.graph_generator import report_main_grid
from ATIBAreport.project_common import *
from ATIBAreport.reachjava import take_logs_from_elastic_with_java
from ATIBAreport.setting_files.basesettings import MEDIA_ROOT
from AgentRoot.models import *
# from accounts.models import User
from inventories.forms import AddDriver
from inventories.models import *

locale.setlocale(locale.LC_ALL, locale='tr_TR.utf8')

# we need it for GUI based errors like self.tk.call('image', 'delete', self.name) about tkinter process
# RuntimeError: main thread is not in main loop
matplotlib.use('Agg')

logger = logging.getLogger('views')
timer = logging.getLogger('timer')
memory_tracer = logging.getLogger('memorytracer')

globalBool = True
globalObjectList = []
globalObject = None
globalVariable = None


def template_message_show(key, message_type, message_content):
    """
    use to create template messages with message type and content, its useful for object_listing function notifications
    """
    if message_type == "info":
        template_message = messages.info(key, message_content)
    elif message_type == "warning":
        template_message = messages.warning(key, message_content)
    elif message_type == "error":
        template_message = messages.error(key, message_content)
    elif message_type == "success":
        template_message = messages.success(key, message_content)
    else:
        template_message = messages.error(key, message_content)

    return template_message


@licence_required
@login_required
def networks(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    systemNetworks = object_listing(NetworkParameters)
    networkList = systemNetworks["list"]
    template_message_show(request, systemNetworks["type"], systemNetworks["message"])

    paginator = Paginator(networkList, 20)
    page = request.GET.get('page')
    try:
        networkList = paginator.page(page)
    except PageNotAnInteger:
        networkList = paginator.page(1)
    except EmptyPage:
        networkList = paginator.page(paginator.num_pages)

    context = {
        'route': 'general',
        'networkList': networkList,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/networks.html', context)


@licence_required
@login_required
def network_detail(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    try:
        systemNetwork = NetworkParameters.objects.get(id=id)
    except ObjectDoesNotExist:
        return redirect('home')
    context = {
        'route': 'detail',
        'systemNetwork': systemNetwork,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/networks.html', context)


@licence_required
@login_required
def network_devices(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    try:
        deviceList = list(
            NetworkDevice.objects.filter(connectedmac=None).exclude(brand_id=None).exclude(brandModel_id=None).exclude(
                brand_id=0).exclude(brandModel_id=0))
        unsupportedDeviceList = list(
            NetworkDevice.objects.filter(brand_id=None).filter(connectedmac=None)) + list(
            NetworkDevice.objects.filter(brand_id=0).filter(connectedmac=None)) + list(
            NetworkDevice.objects.filter(brandModel_id=0).filter(connectedmac=None)) + list(
            NetworkDevice.objects.filter(brandModel_id=None).filter(connectedmac=None))
        unsupportedDeviceList = list(set(unsupportedDeviceList))
        template_message_show(request, "success", f"Successfully finished for {NetworkDevice.objects.count()} devices")
    except Exception as err:
        deviceList = []
        unsupportedDeviceList = []
        template_message_show(request, "error", f"Error occurred while getting devices : {err}")

    supported_count = len(deviceList) + len([d for device in deviceList for d in device.get_connected_devices()])
    unsupported_count = len(unsupportedDeviceList) + len(
        [d for device in unsupportedDeviceList for d in device.get_connected_devices()])

    paginator_1 = Paginator(deviceList, 20)
    s_page = request.GET.get('s_page')
    try:
        deviceList = paginator_1.page(s_page)
    except PageNotAnInteger:
        deviceList = paginator_1.page(1)
    except EmptyPage:
        deviceList = paginator_1.page(paginator_1.num_pages)

    paginator_2 = Paginator(unsupportedDeviceList, 20)
    u_page = request.GET.get('u_page')
    try:
        unsupportedDeviceList = paginator_2.page(u_page)
    except PageNotAnInteger:
        unsupportedDeviceList = paginator_2.page(1)
    except EmptyPage:
        unsupportedDeviceList = paginator_2.page(paginator_2.num_pages)

    if s_page:
        supported_style = "display:block;"
        unsupported_style = "display:none;"
    elif u_page:
        supported_style = "display:none;"
        unsupported_style = "display:block;"
    else:
        supported_style = ""
        unsupported_style = "display:none;"

    context = {
        'route': 'general', 'supported_count': supported_count, 'unsupported_count': unsupported_count,
        'deviceList': deviceList, 'unsupportedDeviceList': unsupportedDeviceList,
        'supported_style': supported_style, 'unsupported_style': unsupported_style,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/devices.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def device_detail(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    global globalObject
    if globalObject:
        if isinstance(globalObject, NetworkDevice) and globalObject.id == id:
            device = globalObject
        else:
            try:
                device = NetworkDevice.objects.get(id=id)
                globalObject = device
            except ObjectDoesNotExist:
                return redirect('AgentRoot:general_monitor')
    else:
        try:
            device = NetworkDevice.objects.get(id=id)
            globalObject = device
        except ObjectDoesNotExist:
            return redirect('AgentRoot:general_monitor')

    # logger.debug(f"{mac_to_simplified(device.macAddress_id)}")

    context = {
        'route': 'detail',
        'device': device,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/devices.html', context)


@licence_required
@login_required
def locations(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    systemLocations = object_listing(DevLocations)
    locationList = systemLocations["list"]
    template_message_show(request, systemLocations["type"], systemLocations["message"])

    paginator = Paginator(locationList, 20)
    page = request.GET.get('page')
    try:
        locationList = paginator.page(page)
    except PageNotAnInteger:
        locationList = paginator.page(1)
    except EmptyPage:
        locationList = paginator.page(paginator.num_pages)

    context = {
        'route': 'general',
        'locationList': locationList,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/locations.html', context)


@licence_required
@login_required
def location_detail(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    global globalObject
    if globalObject:
        if isinstance(globalObject, DevLocations) and globalObject.id == id:
            location = globalObject
        else:
            try:
                location = DevLocations.objects.get(id=id)
                globalObject = location
            except ObjectDoesNotExist:
                return redirect('home')
    else:
        try:
            location = DevLocations.objects.get(id=id)
            globalObject = location
        except ObjectDoesNotExist:
            return redirect('home')

    context = {
        'route': 'detail',
        'location': location
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/locations.html', context)


@licence_required
@login_required
@csrf_exempt
def logs(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'general'
    _updt = (0, 0)
    global globalBool
    # for environment where can connect elasticsearch
    if check_environment_for_elastic():
        elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number, sniff_on_start=True,
                                           request_timeout=2)
        if request.method == "POST":
            """
            'inetaddress': ['192.168.1.249'], 
            'mappedlogsource': ['']
            """
            _inetaddress = request.POST.get('inetaddress') if check_existence(request.POST.get('inetaddress')) else None
            _mappedlogsource = request.POST.get('mappedlogsource') if check_existence(request.POST.get('mappedlogsource')) else None
            logger.info(f"Values for update request : _inetaddress -> {_inetaddress} _mappedlogsource -> {_mappedlogsource}")
            if _mappedlogsource:
                try:
                    _updt = take_logs_from_elastic_with_java("mappedlogsource", str(_mappedlogsource))
                    logger.info(f"In logs view. Process is over with {_updt[0]} log update - in {_updt[1]} seconds")
                    if _updt[2]:
                        # _updt[2] carries the error threw from function exception
                        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                        return JsonResponse({'command': 0, 'updated': _updt[0], 'duration': _updt[1],
                                             'error': _updt[2]}, status=200)
                    else:
                        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                        return JsonResponse({'command': 1, 'updated': _updt[0], 'duration': _updt[1]}, status=200)
                except Exception as err:
                    logger.exception(
                        f"An error occurred trying to call take_logs_from_elastic_with_java function. ERROR IS : {err}")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'updated': _updt[0], 'error': str(err)}, status=200)
            elif _inetaddress:
                try:
                    _updt = take_logs_from_elastic_with_java("inetaddress", str(_inetaddress))
                    logger.info(f"In logs view. Process is over with {_updt[0]} log update - in {_updt[1]} seconds")
                    if _updt[2]:
                        # _updt[2] carries the error threw from function exception
                        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                        return JsonResponse({'command': 0, 'updated': _updt[0], 'duration': _updt[1],
                                             'error': _updt[2]}, status=200)
                    else:
                        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                        return JsonResponse({'command': 1, 'updated': _updt[0], 'duration': _updt[1]}, status=200)
                except Exception as err:
                    logger.exception(
                        f"An error occurred trying to call take_logs_from_elastic_with_java function. ERROR IS : {err}")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'updated': _updt[0], 'error': str(err)}, status=200)
        try:
            # _body = '{"size": 10000, "query": {"match_all": {}} }'
            # _body = json.loads(_body)
            search = elastic_connection.count(index="atibaloglar", body={"query": {"match_all": {}}})
            logCount = int(search["count"])
            search = elastic_connection.search(index="atibaloglar", body={"size": 10000, "query": {"match_all": {}}})
            # logCount = int(search["hits"]["total"]["value"])

            if logCount > 0 and len(search["hits"]["hits"]) > 0:
                logger.debug(f'Sample of elasticsearch search result : {search["hits"]["hits"][0]["_source"]}')
            else:
                logger.warning(
                    f'Elasticsearch search results weird, count:{logCount} & length:{len(search["hits"]["hits"])}')
            logList = [ErrorLogsFromElastic(hit['_id'], dictionary=hit["_source"]) for hit in search["hits"]["hits"]]
            template_message_show(request, "success", f"Successfully get {logCount} logs")
        except Exception as err:
            logger.exception(f"An error occurred while trying to get logs. ERROR IS : {err}")
            template_message_show(request, "error", f"Failed to get logs! {err}")
            logList = []
    # for environment where no elastic connection
    else:
        if request.method == "POST":
            """
            'inetaddress': ['192.168.1.249'], 
            'mappedlogsource': ['']
            """
            _inetaddress = request.POST.get('inetaddress') if check_existence(request.POST.get('inetaddress')) else None
            _mappedlogsource = request.POST.get('mappedlogsource') if check_existence(request.POST.get('mappedlogsource')) else None
            logger.info(
                f"Values for update request : _inetaddress -> {_inetaddress} _mappedlogsource -> {_mappedlogsource}")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return JsonResponse({'command': 0, 'updated': 0,
                                 'duration': (datetime.datetime.now() - time_triggered).total_seconds(),
                                 'error': "No elastic connection!!"}, status=200)
        try:
            logList = list(Logs.objects.exclude(recerror__isnull=True))
            template_message_show(request, "success", f"Successfully get {len(logList)} logs")
        except Exception as err:
            logger.exception(f"An error occurred while trying to get logs (1). ERROR IS : {err}")
            template_message_show(request, "warning", f"Failed to get in first attempt! {err}")
            logList = []

    ipList = list(set([_.inetaddress for _ in logList]))
    uniqueidList = list(set([_.mappedlogsource for _ in logList if _.mappedlogsource]))

    # logger.debug(f"{request.GET}")
    """
    'filterIP': ['192.168.1.249']
    'filterID': ['KutayEvAP']
    """
    filter_ip = request.GET.get('filterIP') if check_existence(request.GET.get('filterIP')) else None
    filter_uniqueid = request.GET.get('filterID') if check_existence(request.GET.get('filterID')) else None
    sortby = request.GET.get('sort') if check_existence(request.GET.get('sort')) else None
    page = request.GET.get('page') if check_existence(request.GET.get('page')) else None

    if sortby:
        if not page:
            globalBool = not globalBool
        try:
            logList.sort(key=lambda x: getattr(x, sortby), reverse=globalBool)
        except TypeError:
            logList.sort(key=lambda x: getattr(x, sortby) if getattr(x, sortby) else "", reverse=globalBool)
        except Exception as err:
            logger.error(f"An error occurred while trying to sort list. ERROR IS : {err}")
            template_message_show(request, "warning", f"Sorting error {err}")
    if filter_ip:
        logList = list(filter(lambda x: x.inetaddress == filter_ip, logList))

    if filter_uniqueid:
        logList = list(filter(lambda x: x.mappedlogsource == filter_uniqueid, logList))

    filterIpList = list(set([_.inetaddress for _ in logList]))
    filterUniqueidList = list(set([_.mappedlogsource for _ in logList if _.mappedlogsource]))

    template_message_show(request, "success", f"{len(logList)} logs listing")

    paginator = Paginator(logList, record_per_page)
    try:
        logList = paginator.page(page)
    except PageNotAnInteger:
        logList = paginator.page(1)
    except EmptyPage:
        logList = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'caption': 'UNPARSED LOGS',
        'logList': logList, 'ipList': ipList, 'uniqueidList': uniqueidList,
        'filterIpList': filterIpList, 'filterUniqueidList': filterUniqueidList,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/logs.html', context)


@licence_required
@login_required
@csrf_exempt
def logs_for_source(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "source"
    _updt = (0, 0)
    global globalBool
    _source = LogSources.objects.get(id=id)
    caption = f"UNPARSED LOGS FOR {_source.uniqueid}"
    # for environment which has elastic connection;
    if check_environment_for_elastic():
        if request.method == "POST":
            if check_existence(request.POST.get('mappedlogsource')):
                try:
                    _updt = take_logs_from_elastic_with_java("mappedlogsource", request.POST.get('mappedlogsource'))
                    logger.info(
                        f"In log_for_source view. Process is over with {_updt[0]} log update - in {_updt[1]} seconds")
                    if _updt[0]:
                        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                        return JsonResponse({'command': 1, 'updated': _updt[0], 'duration': _updt[1]}, status=200)
                    else:
                        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                        return JsonResponse({'command': 0, 'updated': 0, 'error': _updt[2]}, status=200)
                except Exception as err:
                    logger.exception(
                        f"An error occurred trying to call take_logs_from_elastic_with_java function. ERROR IS : {err}")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'updated': 0, 'error': str(err)}, status=200)
        try:
            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number, sniff_on_start=True,
                                               request_timeout=2)
            _body = '{"query":{"bool":{"must":[{"term":{"mappedlogsource":{"value":"%s","boost":1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"_id":{"order":"desc"}}]}' % _source.uniqueid
            _body = json.loads(_body)
            search = elastic_connection.count(index="atibaloglar", body=_body)
            logCount = int(search["count"])
            _body = '{"size":5000,"query":{"bool":{"must":[{"term":{"mappedlogsource":{"value":"%s","boost":1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"_id":{"order":"desc"}}]}' % _source.uniqueid
            _body = json.loads(_body)
            search = elastic_connection.search(index="atibaloglar", body=_body)
            logList = [ErrorLogsFromElastic(hit['_id'], dictionary=hit["_source"]) for hit in search["hits"]["hits"]]
        except Exception as err:
            logList = []
            logger.exception(
                f"An error occurred trying to get logs from elastic for {_source.uniqueid}. ERROR IS : {err}")
            template_message_show(request, "error",
                                  f"Failed to get logs in queue from elastic for {_source.uniqueid}, because {err}")
    # for environment that no elastic connection;
    else:
        if request.method == "POST":
            logger.debug(f"In inventories.logs_for_source view request for retry : {request.POST}")
            """
            # 'retryParse': ['UNIQUEID']
            'mappedlogsource': ['UNIQUEID']
            """
            if check_existence(request.POST.get('mappedlogsource')):
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return JsonResponse({'command': 0, 'updated': 0,
                                     'duration': (datetime.datetime.now() - time_triggered).total_seconds(),
                                     'error': "No elastic connection!!"}, status=200)
        try:
            logList = list(Logs.objects.filter(mappedlogsource=_source.uniqueid))
            template_message_show(request, "success", f"Successfully get {len(logList)} logs")
        except Exception as err:
            logger.exception(f"An error occurred in first attempt to get logs. ERROR IS : {err}")
            template_message_show(request, "warning",
                                  f"Failed to get logs in queue for {_source.uniqueid} because {err}")
            logList = []

    sortby = request.GET.get('sort') if check_existence(request.GET.get('sort')) else None
    page = request.GET.get('page') if check_existence(request.GET.get('page')) else None

    if sortby:
        if not page:
            globalBool = not globalBool
        try:
            logList.sort(key=lambda x: getattr(x, sortby), reverse=globalBool)
        except TypeError:
            logList.sort(key=lambda x: getattr(x, sortby) if getattr(x, sortby) else "", reverse=globalBool)
        except Exception as err:
            logger.exception(f"An error occurred while trying to sort list. ERROR IS : {err}")
            template_message_show(request, "warning", f"Sorting error {err}")

    paginator = Paginator(logList, record_per_page)
    try:
        logList = paginator.page(page)
    except PageNotAnInteger:
        logList = paginator.page(1)
    except EmptyPage:
        logList = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'caption': caption, 'logSource': _source,
        'logList': logList, 'ipList': [], 'uniqueidList': [],
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/logs.html', context)


@licence_required
@login_required
def log_detail(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'detail'
    if check_environment_for_elastic():
        try:
            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number, sniff_on_start=True,
                                               request_timeout=2)
            _body = '{"size":1,"query":{"bool":{"must":[{"term":{"_id":{"value": %s,"boost":1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"_id":{"order":"desc"}}]}' % id
            _body = json.loads(_body)
            search = elastic_connection.search(index="atibaloglar", body=_body)
            if len(search["hits"]["hits"]) > 0:
                log = ErrorLogsFromElastic(search["hits"]["hits"][0]['_id'], dictionary=search["hits"]["hits"][0]["_source"])
            else:
                logger.warning(f"There is no log with id {id} in elastic")
                template_message_show(request, "info", f"Log with id {id} is no longer available")
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return redirect('inventories:logs')
        except Exception as err:
            logger.exception(f"An error occurred while trying to get object with id {id}. ERROR IS : {err}")
            template_message_show(request, "error", f"Failed to get log with id {id} !! because {err}")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('inventories:logs')
    else:
        try:
            log = Logs.objects.get(id=id)
        except ObjectDoesNotExist:
            logger.warning(f"Log doesn't exist no more. id : {id}")
            template_message_show(request, "info", f"Log doesn't exist, it may parsed successfully")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('inventories:logs')
        except Exception as err:
            logger.exception(f"An error occurred while trying to get object with id {id}. ERROR IS : {err}")
            template_message_show(request, "error", f"Failed to get log with id {id} !!")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('inventories:logs')

    context = {
        'route': route, 'caption': 'UNPARSED LOG DETAILS',
        'log': log,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/logs.html', context)


@licence_required
@login_required
def anomalies(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    systemAnomalyLogs = object_listing(AnomalyLogsDetails, limit=20000)
    anomalyList = systemAnomalyLogs["list"]
    template_message_show(request, systemAnomalyLogs["type"], systemAnomalyLogs["message"])

    paginator = Paginator(anomalyList, 20)
    page = request.GET.get('page')
    try:
        anomalyList = paginator.page(page)
    except PageNotAnInteger:
        anomalyList = paginator.page(1)
    except EmptyPage:
        anomalyList = paginator.page(paginator.num_pages)

    context = {
        'route': 'general',
        'anomalyList': anomalyList,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/anomalies.html', context)


@licence_required
@login_required
def anomaly_detail(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    try:
        anomaly = AnomalyLogsDetails.objects.get(id=id)
    except ObjectDoesNotExist:
        return redirect('home')

    device = anomaly.anomalyLog.get_device()

    alog = anomaly.anomalyLog
    subalog = anomaly.subAnomalyLog
    # logger.debug(f"In Anomaly Detail Screen got : ALOG : {log1} - SUBALOG {log2}")

    log1code = alog.logcode
    log1 = LogDefinitionDetails.objects.filter(logcode=log1code)
    log2code = subalog.logcode
    log2 = LogDefinitionDetails.objects.filter(logcode=log2code)
    logger.info(f"In Anomaly Detail Screen got : ALOG : {log1} - SUBALOG {log2}")

    context = {
        'route': 'detail',
        'anomaly': anomaly, 'device': device, 'alog': alog, 'subalog': subalog,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/anomalies.html', context)


@licence_required
@login_required
def anomaly_logs(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    try:
        log = AnomalyLogs.objects.get(id=id)
    except ObjectDoesNotExist:
        return redirect('home')
    logcode = log.logcode
    logList = LogDefinitionDetails.objects.filter(logcode=logcode)

    context = {
        'route': 'general', 'caption': 'RELATED LOGS FOR ANOMALY',
        'logList': logList,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/logs.html', context)


@licence_required
@login_required
def system_users(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    # systemUsers = object_listing(User)
    # systemUserList = systemUsers["list"]
    # template_message_show(request, systemUsers["type"], systemUsers["message"])
    #
    # paginator = Paginator(systemUserList, 20)
    # page = request.GET.get('page')
    # try:
    #     systemUserList = paginator.page(page)
    # except PageNotAnInteger:
    #     systemUserList = paginator.page(1)
    # except EmptyPage:
    #     systemUserList = paginator.page(paginator.num_pages)

    context = {
        'route': 'general',
        # 'systemUserList': systemUserList,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/users.html', context)


@licence_required
@login_required
def system_user_detail(request):
    """ Not used view """
    pass


@licence_required
@login_required
@xframe_options_sameorigin
def rc_graph_list(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    global globalObjectList
    if globalObjectList:
        if not isinstance(globalObjectList[0], RootCauseGraphsDetails):
            try:
                rcMapList = list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2))
            except Exception as err:
                rcMapList = []
                logger.exception(f"An error occurred while trying to get RootCauseGraphDetails. ERROR IS : {err}")
            globalObjectList = rcMapList
        else:
            if len(globalObjectList) != RootCauseGraphsDetails.objects.filter(analyzedstatus=2).count():
                try:
                    rcMapList = list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2))
                except Exception as err:
                    rcMapList = []
                    logger.exception(f"An error occurred while trying to get RootCauseGraphDetails. ERROR IS : {err}")
                globalObjectList = rcMapList
            else:
                rcMapList = globalObjectList
    else:
        try:
            rcMapList = list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2))
        except Exception as err:
            rcMapList = []
            logger.exception(f"An error occurred while trying to get RootCauseGraphDetails. ERROR IS : {err}")
        globalObjectList = rcMapList

    # sourceList = list(LogSources.objects.values_list("uniqueid", flat=True))
    # incidentTypes = list(GeneralParameterDetail.objects.values_list("kisaack", flat=True).filter(kisakod="ANMLTYPE"))
    # for rc in rcMapList:
    #     sourceList += rc.get_root_devices()
    #     incidentTypes += rc.get_anomaly_types()
    # sourceList = list(set(sourceList))
    # incidentTypes = list(set(incidentTypes))
    # logger.debug(f"{len(sourceList)} SOURCES : {sourceList}")
    # logger.debug(f"{len(incidentTypes)} ANOMALY TYPES : {incidentTypes}")

    paginator = Paginator(rcMapList, record_per_page)
    page = request.GET.get('page')
    try:
        rcMapList = paginator.page(page)
        if int(page) > 1:
            template_message_show(request, "success", f"Successfully get next {len(rcMapList)} record")
        else:
            template_message_show(request, "success", f"Successfully get {len(rcMapList)} record")
    except PageNotAnInteger:
        rcMapList = paginator.page(1)
        template_message_show(request, "success", f"Successfully get {len(rcMapList)} record")
    except EmptyPage:
        rcMapList = paginator.page(paginator.num_pages)

    context = {
        'route': 'general', 'caption': 'INCIDENTS',
        'rcMapList': rcMapList,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/rc_graphs.html', context)


@licence_required
@login_required
@csrf_exempt
@xframe_options_sameorigin
def rc_graph_detail(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    # logger.debug(f"csrf cookie is : {request.META['CSRF_COOKIE']}")

    dataWarning = None

    if request.method == 'POST':
        if request.is_ajax():
            # logger.debug(f"Re-draw request : {request.POST}")
            if request.POST.get("action") == "re_draw":
                logger.info(f"Re-draw requested for {id}")
                _response = create_rc_picture(rc_id=id, re_draw=True)
                if _response == "FINISH":
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 1, "result": "Graph has been successfully redrawn"}, status=200)
                else:
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, "result": "Failed to draw again"}, status=200)
    else:
        if list(RootCauseGraphsDetails.objects.values_list('graphimage', flat=True).filter(id=id))[0] is None:
            rc_picture_proccess = create_rc_picture(rc_id=id)
            if rc_picture_proccess == "BUSY":
                logger.warning(f"create_rc_picture(rc_id={id}) called and returned {rc_picture_proccess}")
            else:
                logger.info(f"create_rc_picture(rc_id={id}) called and returned {rc_picture_proccess}")
    # _thread.start_new_thread(create_rc_picture, ())

    global globalObject
    if globalObject:
        if isinstance(globalObject, RootCauseGraphsDetails) and globalObject.id == id:
            _rcMap = globalObject
        else:
            try:
                _rcMap = RootCauseGraphsDetails.objects.get(id=id)
                globalObject = _rcMap
            except ObjectDoesNotExist:
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return redirect('AgentRoot:rc_flowing')
    else:
        try:
            _rcMap = RootCauseGraphsDetails.objects.get(id=id)
            globalObject = _rcMap
        except ObjectDoesNotExist:
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('AgentRoot:rc_flowing')

    analysisCase = "Analysis Completed" if _rcMap.analyzedstatus == 2 else "The analysis continues"

    _root_devices = list(set(_rcMap.get_root_devices()))

    rc_leafList = [get_anomaly_log_detail(leaf) for leaf in _rcMap.leaflist]
    rc_nodeList = [get_anomaly_log_detail(node) for node in _rcMap.nodelist]

    code_list = list(set([_.logcode for _ in rc_leafList]))

    # Collecting logs by arranging them by anomaly type in here;
    definition_and_incident = []
    root_logs = _rcMap.get_root_logs()
    logger.debug(f"ROOT LOGS LIST : {root_logs}")
    definitions = list(set(_.get_type_definition() for _ in root_logs if isinstance(_, AnomalyLogs)))
    dataWarning = "possible data corruption detected" if not definitions else None
    for anomalyType in definitions:
        _logs = []
        for _ in root_logs:
            if not isinstance(_, AnomalyLogs):
                dataWarning = "possible data corruption detected"
                logger.warning(f"Possible data corruption detected : {_}")
                continue
            if _.get_type_definition() == anomalyType:
                _logs.append(_)
        if not anomalyType.endswith("s") and len(_logs) > 1:
            anomalyType = anomalyType[:-1]+"ies" if anomalyType.endswith("Anomaly") else anomalyType+"s"
        definition_and_incident.append((anomalyType, _logs))
    logger.debug(f"DEFINITIONS & ANOMALYLOGS COLLECTION : {definition_and_incident}")

    # paths = json.loads(_rcMap.graphpaths)
    paths = _rcMap.get_paths()

    # root_leaves = root_and_leaves(_rcMap.rootlist, json.loads(_rcMap.graphpaths), _rcMap.leaflist)
    root_leaves = root_and_leaves(_rcMap.rootlist, paths, _rcMap.leaflist)
    if len(root_leaves) == 0:
        analysisCase = "The analysis is still ongoing ..."

    if request.method == 'POST':
        _changed = False
        _form_response = request.POST
        # logger.debug(f"{_form_response}")
        # logger.debug(f"{_form_response.getlist('correction_feedbacks')}")
        if 'correction_feedbacks' in _form_response.keys():
            # logger.debug("correction_feedbacks form sent (rc_graph_detail view)")
            _correction_form = _form_response.getlist('correction_feedbacks')
            _changed = update_anomalylogsdetails_userfeedback(json.loads(_rcMap.graphpaths), _correction_form)
            logger.info(f"Is anything changed for correction feedbacks ? : {_changed}")

        elif 'alert_managements' in _form_response.keys():
            # logger.debug("alert_managements form sent (rc_graph_detail view)")
            _changed = update_anomalylogs_isshow(_form_response.getlist('alert_managements'))
            logger.info(f"Is anything changed for alert managements ? : {_changed}")

        if _changed:
            root_leaves = root_and_leaves(_rcMap.rootlist, json.loads(_rcMap.graphpaths), _rcMap.leaflist)
            template_message_show(request, 'success', 'Changes saved successfully')

    context = {
        'route': 'detail', 'caption': 'ROOT - CAUSE MAPPING', 'code_list': code_list, 'root_leaves': root_leaves,
        'rcMap': _rcMap, 'leafList': rc_leafList, 'nodeList': rc_nodeList, 'root_devices': _root_devices,
        'paths': paths, 'analysisCase': analysisCase, 'definition_and_incident': definition_and_incident,
        'dataWarning': dataWarning,
    }
    # memory usage logging with memory_tracer
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/rc_graphs.html', context)


@licence_required
@login_required
@csrf_exempt
def add_device_driver(request):
    """
    to load, expand and execute vendor based driver files in tar format.
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()

    global globalObject, globalVariable

    if not isinstance(globalObject, django.core.files.uploadedfile.InMemoryUploadedFile):
        globalObject, globalVariable = None, None

    logger.debug(f"globalObject -> {globalObject} type is {type(globalObject)}")
    logger.debug(f"globalVariable -> {globalVariable} type is {type(globalVariable)}")
    folder = f"{MEDIA_ROOT}/DRIVERS/DEVICE"  # this is our root folder for device drivers !!
    logger.debug(f"IS {folder} EXIST : {os.path.exists(folder)}")
    if not os.path.exists(folder):
        os.makedirs(folder)
        logger.info(f"{folder} folder doesn't exist, now it's created.")

    _objectsList = UpdateStatus.objects.filter(filename__isnull=False)
    updateds = [(_obj.filename, _obj.ifsuccess, _obj.errorinfo, _obj.brand.markname,
                 _obj.uploaddate) for _obj in _objectsList]
    logger.debug(f"Updateds list is : {updateds}")

    # sub_folders = list(UpdateStatus.objects.filter(filename__isnull=False).values_list('filename', flat=True))
    sub_folders = [name for name in os.listdir(folder) if os.path.isdir(os.path.join(folder, name))]

    # updateds = []
    # for name in sub_folders:
    #     try:
    #         _obj = UpdateStatus.objects.get(filename=name)
    #         updateds.append((name, _obj.ifsuccess, _obj.errorinfo, _obj.brand.markname, _obj.uploaddate))
    #     except ObjectDoesNotExist:
    #         updateds.append((name, False, "", "", ""))
    #     except Exception as err:
    #         logger.exception(
    #             f"An error occurred trying to get updatestatus record with filename {name}. ERROR IS : {err}")
    #         continue

    logger.debug(f"Loaded device drivers : {sub_folders}")
    route = "file load"
    _dir_name = None
    _device_mark_id = None
    _device_mark_ver_subver = None
    _existing_device_mark = None
    _new_device_mark = None

    if globalObject and globalVariable:
        _dir_name = str(globalObject).replace('.gz', '').replace('.tar', '')

    form = AddDriver(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            logger.debug(f"REQUEST : {request.POST}")
            logger.debug(f"VALID FORM REQUEST FILES : {request.FILES}")
            _file = request.FILES['driver_file']

            if not globalObject or str(globalObject) != str(_file):
                globalObject = _file
                logger.info(f"New globalObject : {globalObject}")
                _dir_name = str(globalObject).replace('.gz', '').replace('.tar', '')
                if _dir_name in sub_folders:
                    with open(f"{folder}/{_dir_name}/version.txt", 'r', encoding='utf-8') as f:
                        row = f.read()
                        globalVariable = json.loads(row)
                        logger.info(f"New globalVariable is version row : {row}")

                    #
                    _device_mark_id = int(globalVariable["definitioncode"])
                    try:
                        _existing_device_mark = DeviceMark.objects.get(id=_device_mark_id)
                    except ObjectDoesNotExist:
                        try:
                            DeviceMark.objects.create(id=_device_mark_id,
                                                      markname=globalVariable["definitionname"],
                                                      markfilename=globalVariable["filename"],
                                                      markversion=str(globalVariable["defversion"]),
                                                      marksubversion=int(globalVariable["defsubversion"]))
                        except Exception as err:
                            logger.exception(f"An error occurred trying to create devicemark row with id {_device_mark_id}. ERROR IS : {err}")
                    except Exception as err:
                        logger.exception(f"An error occurred trying to get devicemark row for id {_device_mark_id}. ERROR IS : {err}")

                    if _existing_device_mark:
                        if _existing_device_mark.markversion and _existing_device_mark.markversion:
                            _existing_version = _existing_device_mark.markversion + "." + str(_existing_device_mark.markversion)
                            _new_version = globalVariable["defversion"] + "." + str(globalVariable["defsubversion"])
                            if _existing_version == _new_version:
                                logger.info(f"Existing devicemark version is {_existing_version} same with new {_new_version} version.")
                                template_message_show(request, 'info', f"{_dir_name} driver already installed before")
                            else:
                                DeviceMark.objects.filter(id=_device_mark_id).update(
                                    markfilename=globalVariable["filename"],
                                    markversion=str(globalVariable["defversion"]),
                                    marksubversion=int(globalVariable["defsubversion"])
                                )
                                template_message_show(request,
                                                      'info',
                                                      f"{_dir_name} driver already installed and updated some old records")
                        else:
                            DeviceMark.objects.filter(id=_device_mark_id).update(
                                markfilename=globalVariable["filename"],
                                markversion=str(globalVariable["defversion"]),
                                marksubversion=int(globalVariable["defsubversion"])
                            )
                            template_message_show(request,
                                                  'info',
                                                  f"{_dir_name} driver already installed and updated some old records")
                    # template_message_show(request, 'info', f"{_dir_name} driver already installed before")
                elif str(globalObject).endswith("tar.gz"):
                    with tarfile.open(fileobj=globalObject, mode="r:gz") as driver:
                        # """Open tar.gz file read and extract it"""
                        logger.debug(f"Extracting tar.gz file...")
                        try:
                            driver.getmember('version.txt')
                        except KeyError:
                            logger.warning(f"No version information in {globalObject}")
                            template_message_show(request, 'warning', f"No version information in {globalObject}")
                        logger.debug(f"Content of file : {driver.getmember('version.txt')}")
                        logger.info(f"{MEDIA_ROOT}\\DRIVERS\\DEVICE\\{_dir_name}")
                        driver.extractall(path=f"{folder}/{_dir_name}")
                    with open(f"{folder}/{_dir_name}/version.txt", 'r', encoding='utf-8') as f:
                        # """Open version file read it"""
                        # for row in f:
                        row = f.read()
                        globalVariable = json.loads(row)
                        logger.info(f"New globalVariable is version row : {row}")
                    try:
                        if globalVariable["tarType"] == 'device':
                            template_message_show(request, 'success', f'{globalObject} file successfully loaded')
                        elif _dir_name != globalVariable['filename']:
                            template_message_show(request,
                                                  'warning',
                                                  f"Compressed file name and file name doesn't match !!")
                        else:
                            logger.warning(f"Not a device type driver {globalObject}. Removing extracted files")
                            try:
                                os.rmdir(f"{folder}/{_dir_name}")
                            except Exception as err:
                                logger.exception(
                                    f"An error occurred trying to remove folder {_dir_name}. ERROR IS : {err}")
                            template_message_show(request, 'warning', f"Not a device type driver {globalObject}")
                    except Exception as err:
                        logger.exception(
                            f"An error occurred trying to get tarType from file {globalObject}. ERROR IS : {err}")
                elif str(globalObject).endswith("tar"):
                    with tarfile.open(fileobj=globalObject, mode="r:") as driver:
                        # """Open tar file read and extract it"""
                        logger.debug(f"Extracting tar file...")
                        # _dir_name = str(globalObject).replace('.tar', '')
                        try:
                            driver.getmember('version.txt')
                        except KeyError:
                            logger.warning(f"No version information in {globalObject}")
                            template_message_show(request, 'warning', f"No version information in {globalObject}")
                        logger.info(f"{MEDIA_ROOT}\\DRIVERS\\DEVICE\\{_dir_name}")
                        driver.extractall(path=f"{folder}/{_dir_name}")
                    with open(f"{folder}/{_dir_name}/version.txt", 'r', encoding='utf-8') as f:
                        # """Open version file read it"""
                        # for row in f:
                        row = f.read()
                        globalVariable = json.loads(row)
                        logger.info(f"New globalVariable is version row : {row}")
                    try:
                        if globalVariable["tarType"] == 'device':
                            template_message_show(request, 'success', f'{globalObject} file successfully loaded')
                        elif _dir_name != globalVariable['filename']:
                            template_message_show(request, 'warning',
                                                  f"Compressed file name and file name doesn't match !!")
                        else:
                            logger.warning(f"Not a device type driver {globalObject}. Removing extracted files")
                            try:
                                os.rmdir(f"{folder}/{_dir_name}")
                            except Exception as err:
                                logger.exception(
                                    f"An error occurred trying to remove folder {_dir_name}. ERROR IS : {err}")
                            template_message_show(request, 'warning', f"Not a device type driver {globalObject}")
                    except Exception as err:
                        logger.exception(
                                f"An error occurred trying to get tarType from file {globalObject}. ERROR IS : {err}")
                else:
                    logger.warning(f"{globalObject} file is not tar or tar.gz file")
            else:
                _dir_name = str(globalObject).replace('.gz', '').replace('.tar', '')
                template_message_show(request, 'warning', f'{globalObject} file already loaded')
                logger.debug(f"Existing globalObject : {globalObject}")
        else:
            logger.debug(f"NOT VALID FORM : {request.FILES}")

    if request.is_ajax():
        logger.debug(f"Ajax request : {request.POST}")
        sql_query_file = None
        # sql_query_file_path = None
        _installed = None
        if request.POST.get('action') == "resetGlobals":
            globalObject, globalVariable = None, None
            return JsonResponse({'command': 1, 'action': 'resetGlobals', 'result': 'Ok'}, status=200)
        if request.POST.get('action') == "installLoaded":
            if globalObject and globalVariable:
                logger.debug(f"files in driver : {globalVariable['files']} & type {type(globalVariable['files'])}")
                _dir_name = str(globalObject).replace('.gz', '').replace('.tar', '')
                # _dir_name = globalVariable['filename']
                if _dir_name != globalVariable['filename']:
                    logger.warning(
                        f"Name of compressed file {_dir_name} and file name {globalVariable['filename']}. Not a valid!")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'action': 'installLoaded', 'result': 'Not valid driver file ! '}, status=200)
                for _ in globalVariable['files']:
                    if str(_['filename']).endswith(".sql"):
                        sql_query_file = _['filename']
                        break
                logger.debug(f"SQL Query File : {sql_query_file}")
                logger.info(f"SQL Query File path : {MEDIA_ROOT}\\DRIVERS\\DEVICE\\{_dir_name}\\{sql_query_file}")
                sql_query_file_path = f"{folder}/{_dir_name}/{sql_query_file}"
                try:
                    _installed = UpdateStatus.objects.get(filename=globalVariable['filename'])
                    # if we get the record successfully then the code will be continued to execution of if _installed
                    # row lying below the exceptions
                except ObjectDoesNotExist:
                    # if there is no record we are looking for...
                    _ifsuccess, _errorinfo, _dur = execute_sql_file(sql_query_file_path, database_name='atibadb')
                    _errorinfo = _errorinfo if not _errorinfo else str(_errorinfo)  # to string if not None

                    _id = UpdateStatus.objects.create(uploadtype=globalVariable['tarType'],
                                                      upversion=str(globalVariable['defversion']),
                                                      upsubversion=int(globalVariable['defsubversion']),
                                                      ifsuccess=_ifsuccess,
                                                      errorinfo=_errorinfo,
                                                      brand_id=int(globalVariable['definitioncode']),
                                                      filename=globalVariable['filename'],
                                                      versioncontent=json.dumps(globalVariable))

                    if _ifsuccess:
                        _device_mark_id = int(globalVariable["definitioncode"])
                        try:
                            _existing_device_mark = DeviceMark.objects.get(id=_device_mark_id)
                        except ObjectDoesNotExist:
                            logger.warning(f"There is no vendor information loaded, now vendor information is loading")
                            try:
                                DeviceMark.objects.create(id=_device_mark_id,
                                                          markname=globalVariable["definitionname"],
                                                          markfilename=globalVariable["filename"],
                                                          markversion=str(globalVariable["defversion"]),
                                                          marksubversion=int(globalVariable["defsubversion"]))
                                logger.info(f"Devicemark row for {_existing_device_mark.markname} successfully added")
                            except Exception as err:
                                logger.exception(
                                    f"An error occurred trying to create devicemark row with id {_device_mark_id}. ERROR IS : {err}")
                        except Exception as err:
                            logger.exception(
                                f"An error occurred trying to get devicemark row for id {_device_mark_id}. ERROR IS : {err}")

                        if _existing_device_mark:
                            if _existing_device_mark.markversion and _existing_device_mark.markversion:
                                if _existing_device_mark.markname.lower() == globalVariable["definitionname"].lower():
                                    _existing_version = _existing_device_mark.markversion + "." + str(_existing_device_mark.markversion)
                                    _new_version = globalVariable["defversion"] + "." + str(globalVariable["defsubversion"])
                                    if _existing_version == _new_version:
                                        logger.info(f"Existing devicemark version is {_existing_version} same with new {_new_version} version.")
                                    # elif _existing_version > _new_version:
                                    #     logger.info(f"Existing devicemark version is {_existing_version} older from new {_new_version} version.")
                                    else:
                                        DeviceMark.objects.filter(id=_device_mark_id).update(
                                            markfilename=globalVariable["filename"],
                                            markversion=str(globalVariable["defversion"]),
                                            marksubversion=int(globalVariable["defsubversion"])
                                        )
                                        logger.info(f"Devicemark row for {_existing_device_mark.markname} successfully updated to {_new_version}")
                                else:
                                    logger.error(
                                        f"Vendor row with id {_device_mark_id} is {_existing_device_mark.markname} row, not {globalVariable['definitionname']} row!!")
                            else:
                                DeviceMark.objects.filter(id=_device_mark_id).update(
                                    markfilename=globalVariable["filename"],
                                    markversion=str(globalVariable["defversion"]),
                                    marksubversion=int(globalVariable["defsubversion"])
                                )
                                logger.info(f"Devicemark row for {_existing_device_mark.markname} successfully updated to {_new_version}")

                        logger.debug(f"Installed successfully in {_dur}. id : {_id}")
                        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                        # command : 2 means page need to be reloaded...
                        return JsonResponse({'command': 2, 'action': 'installLoaded',
                                             'result': f'Installed successfully in {_dur}'}, status=200)
                    elif _errorinfo:
                        logger.debug(f"Installed with error. id : {_id}")
                        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                        # command : 2 means page need to be reloaded...
                        return JsonResponse(
                            {'command': 2, 'action': 'installLoaded',
                             'result': f'Installed some parts but an error occurred. {str(_errorinfo)}'}, status=200)
                    else:
                        logger.debug(f"Something happened unexpected while installing device driver !!")
                        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                        return JsonResponse({'command': 0, 'action': 'installLoaded',
                                             'result': 'Something happened unexpected while installing device driver'},
                                            status=200)
                except MultipleObjectsReturned:
                    # if there is more than one record we are looking for...
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'action': 'installLoaded',
                                         'result': 'Already Installed more than one !!'}, status=200)
                except Exception as err:
                    # Other unexpected db exceptions...
                    logger.exception(f"An error occurred trying to check if installed before. ERROR IS : {str(err)}")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'action': 'installLoaded',
                                         'result': f'Installation check error {str(err)}'}, status=200)

                # if we get the _installed UpdateStatus object successfully without any exceptions

                if _installed:
                    # check and decide what we will do for this record...
                    if _installed.ifsuccess:
                        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                        return JsonResponse({'command': 1, 'action': 'installLoaded',
                                             'result': 'Already installed before with success'}, status=200)
                    else:
                        # Using this function for SQL Execution...............execute_sql_file().......................
                        _ifsuccess, _errorinfo, _dur = execute_sql_file(sql_query_file_path, database_name='atibadb')

                        _installed.ifsuccess = _ifsuccess
                        _installed.errorinfo = _errorinfo if not _errorinfo else str(_errorinfo)  # to str if not None
                        _installed.versioncontent = json.dumps(globalVariable)
                        _installed.uploaddate = datetime.datetime.now()
                        _installed.save()
                        if _ifsuccess:
                            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                            # command : 2 means page need to be reloaded...
                            return JsonResponse({'command': 2, 'action': 'installLoaded',
                                                 'result': f'This time successfully installed in {_dur}'},
                                                status=200)
                        elif not _ifsuccess and _errorinfo:
                            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                            # command : 2 means page need to be reloaded...
                            return JsonResponse({'command': 2, 'action': 'installLoaded',
                                                 'result': f'Installed in {_dur} with error {str(_errorinfo)}'},
                                                status=200)
                        else:
                            logger.warning(
                                f"Unexpected condition on install process. success:{_ifsuccess} - error:{_errorinfo}")
                            return JsonResponse({'command': 0, 'action': 'installLoaded',
                                                 'result': f'Unexpected error {_ifsuccess},{str(_errorinfo)}'},
                                                status=200)
            else:
                logger.info(f"{globalObject} is already installed before")
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return JsonResponse({'command': 0, 'action': 'installLoaded',
                                     'result': 'Already Installed'}, status=200)

    filterVendor = request.GET.get('filterVendor') if check_existence(request.GET.get('filterVendor')) else None
    vendorList = []
    logger.debug(f"filterVendor : {filterVendor}")
    if filterVendor:
        loadedList = list(DeviceModel.objects.defer(
            "fielddefcode", "modelcode", "versionParse_id").filter(brand_id=filterVendor))
        vendorList = [loadedList[0].brand]
    else:
        try:
            loadedList = list(DeviceModel.objects.defer("fielddefcode", "modelcode", "versionParse_id").all())
        except Exception as err:
            loadedList = []
            logger.exception(f"An error occurred trying to get loaded models. ERROR IS : {err}")
            template_message_show(request, "warning", f"Data corruption detected. {err}")
        vendorIDS = list(set(DeviceModel.objects.values_list('brand_id', flat=True).distinct()))
        logger.debug(f"Vendor ids are {vendorIDS}")
        # logger.debug(f"Vendor ids count {len(vendorIDS)}")
        # vendorList = [DeviceMark.objects.get(id=_) for _ in vendorIDS if _ > 0]
        for _ in vendorIDS:
            if _ > 0:
                try:
                    vendorList.append(DeviceMark.objects.get(id=_))
                except ObjectDoesNotExist:
                    logger.warning(f"No devicemark with id {_}")
                    continue
                except Exception as err:
                    logger.exception(f"An error occurred trying to get devicemark for id {_}. ERROR IS : {err}")
                    continue

    logger.debug(f"Count of loadedList is {len(loadedList)}")

    paginator = Paginator(loadedList, record_per_page)
    page = request.GET.get('page')
    try:
        loadedList = paginator.page(page)
    except PageNotAnInteger:
        loadedList = paginator.page(1)
    except EmptyPage:
        loadedList = paginator.page(paginator.num_pages)

    if _dir_name is None:
        logger.debug("If there is a loaded file then unexpectedly _dir_name variable left blank somehow !!")

    context = {
        'route': route, 'form': form, 'loadedList': loadedList, 'vendorList': vendorList, 'loadedFile': globalObject,
        'versionInfo': globalVariable, 'loadedDrivers': updateds, 'loadedDirectory': _dir_name,
    }

    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/driver.html', context)


@licence_required
@login_required
def module_home(request):
    time_triggered = datetime.datetime.now()
    # logger.debug(f"{inventories.models}")
    modelList = []
    modelNameList = [("Make your choices", "")]
    i = 0
    for model in django.apps.apps.get_models():

        modelList.append(model)
        name = model.__name__
        if name == "LogEntry" or name == "Permission" or name == "Group" or name == "ReportBase" or \
                name == "User" or name == "ContentType" or name == "Session":
            continue
        try:
            liste = [(str(i.name), str(i.verbose_name)) for i in model._meta.fields
                     if (i.verbose_name != "" and i.verbose_name != i.name) and i.name != "id"]
            modelNameList.append((name, liste))
            # logger.debug(f"**{i} - {name} models fields : {liste}")
        except Exception as err:
            logger.exception(f"{err}")

        count = model.objects.all().count()
        # logger.debug("{} rows: {}".format(name, count))
        i += 1

    # logger.debug(modelNameList)

    # devices = object_listing(NetworkDevice)
    # deviceList = devices["list"]

    # logger.debug(25 * "---")

    # device = deviceList[0]
    # logger.debug(device.verbose_name("devicename"))
    # fieldList = device.__dict__.keys()
    # fieldList = device._meta.fields
    # # fieldList = device.fields_of
    # logger.debug(type(fieldList))
    # for i in fieldList:
    #     logger.debug(i.verbose_name)

    # fieldList = [str(i.verbose_name) for i in device._meta.fields]
    # logger.debug(fieldList)

    context = {
        'route': 'general',
        'caption': 'DATA YOU HAVE FOR REPORT',
        'modelNameList': modelNameList,
    }
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/module.html', context)


@licence_required
@login_required
@csrf_exempt
def module_report(request):
    time_triggered = datetime.datetime.now()
    operation_result = "No operation executed"
    notice = ""
    # logger.debug(f"{args}")
    # logger.debug(f"{kwargs}")
    form_values_raw = request.POST
    # logger.debug(form_values_raw)
    class_field_list = form_values_raw.lists()
    # logger.debug(f"{class_field_list}")
    format_definitions = {}
    for i in class_field_list:
        x, y = i[0], i[1]
        if x == "csrfmiddlewaretoken" or x == "class_names":
            continue
        else:
            # format_definitions["class_name"] = x
            columns = []
            # logger.debug(f"y is : {y}")
            for b in y:
                columns.append(b)
                # logger.debug(f"columns list : {columns}")
                # format_definitions.append((x, y))
                # logger.debug(format_definitions, " as a list")
                # logger.debug(f"{x} - class : {y}")
            format_definitions[x] = columns
    if len(format_definitions) > 0:
        format_definitions = json.dumps(format_definitions)
        # logger.debug(f"JSON DUMP : {format_definitions}")
        # y = json.loads(format_definitions)
        # logger.debug(f"JSON LOAD : {y}")
        # logger.debug(f"JSON LOAD : {y[0][1]}")
        try:
            exist = ReportBase.objects.get(report_format=format_definitions)
            format_definitions = exist.report_format
            operation_result = f"Your choices are already exist as a report format with name : {exist.report_name}"
            # exist.name_change("reloaded")
            # exist.save()
            logger.info(f"Found an equivalent in database, its ID : {exist.id}")
        except ObjectDoesNotExist:
            logger.warning(f"There is no equivalent in database, creating new record for this definition")
            report_instance = ReportBase()
            report_instance.report_format = format_definitions
            report_instance.save()
            operation_result = "Saved Successfully"
            notice = "NEW"
        except Exception as err:
            operation_result = f"Operation failed for some errors like : {err}"
            logger.exception(f"An Error has occurred when saving report definitions : {err}")
    else:
        operation_result = "No operation executed, because you chose nothing.."

    reportList = ReportBase.objects.all()
    # values_dict = MultiValueDict(form_values)
    # logger.debug(f"{values_dict}")
    #
    # for k in form_values.keys():
    #     logger.debug(f"{k} : {form_values.__getitem__()}")

    context = {
        'route': 'creation', 'caption': 'SAVED REPORTS', 'notice': notice,
        'content_title': 'Saved your choices as below',
        'form_values': form_values_raw, 'format_definitions': format_definitions, 'text': operation_result,
        'reportList': reportList,
    }
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/module_report.html', context)


@licence_required
@login_required
def delete_report_type(request, id):
    time_triggered = datetime.datetime.now()
    try:
        report = ReportBase.objects.get(id=id)
        report.delete()
        template_message_show(request, "info", "Report type record deleted successfully...")
    except ObjectDoesNotExist:
        logger.warning(f"there is no object with id : {id} - couldn't deleted")
        template_message_show(request, "error", "An error occurred when trying to delete report type record")
    except Exception as err:
        logger.exception(f"An Error occurred while trying to get report with id : {id} & ERROR IS : {err}")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return redirect('inventories:report_list')


@licence_required
@login_required
def report_list(request):
    time_triggered = datetime.datetime.now()
    reportList = []
    try:
        reports = object_listing(ReportBase)
        reportList = reports["list"]
        template_message_show(request, reports["type"], reports["message"])
    except ObjectDoesNotExist:
        logger.warning(f"there is no object error")
    except Exception as err:
        logger.warning(f"An Error occurred when trying to get reports & ERROR IS : {err}")

    context = {
        'route': 'general', 'caption': 'REPORTS CREATED BEFORE',
        'content_title': 'See reports that saved before',
        'reportList': reportList,
    }
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/module_report.html', context)


@licence_required
@login_required
def report_detail(request, id):
    time_triggered = datetime.datetime.now()
    report = None
    try:
        report = ReportBase.objects.get(id=id)
        report_format = json.loads(report.report_format)
        # logger.debug(report.report_format)
        # logger.debug(report_format)
    except ObjectDoesNotExist:
        report_format = []
        logger.warning(f"there is no object with id : {id}")
    except Exception as err:
        report_format = []
        logger.exception(f"An Error occurred when trying to get report with id : {id} & ERROR IS : {err}")

    # logger.debug(len(report_format))
    # logger.debug(report_format.items())

    object_dict = {}
    try:
        for key, value in report_format.items():
            # logger.debug(f"tuple is : {key} and {value}")
            # module = importlib.import_module(key)
            # module = globals()[key]
            # logger.debug(module)
            object_dict[key] = {}
            object_dict[key]["object_list"] = object_listing(globals()[key])["list"]
            object_dict[key]["attr_list"] = []
            for v in value:
                object_dict[key]["attr_list"].append(v)
    except Exception as err:
        logger.exception(f"Error on report_detail : {err}")

    # logger.debug(f"object_dict dict is : {object_dict}")
    generated_html = report_main_grid(object_dict)

    context = {
        'route': 'detail', 'caption': 'REPORT DETAILS',
        'content_title': 'See report details',
        'report': report, 'report_format': report_format, 'object_dict': object_dict, 'generated_html': generated_html,
    }
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'inventories/module_report.html', context)
