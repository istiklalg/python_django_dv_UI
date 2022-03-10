"""
@author: istiklal
"""
import _thread
import datetime
import json
import locale
import socket
import tracemalloc
# import requests
# from base64 import b64encode
# import dill
# import jsonpickle
# import numpy as np
# from bokeh.embed import components
# from bokeh.plotting import figure, show, output_file
from statistics import mode

import requests
from elasticsearch_dsl import Search
from scipy.stats import gaussian_kde
from django.core import serializers
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Count, Func, Max
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from ATIBAreport.ElasticModels import LogFromElastic, AggregationElastic
from ATIBAreport.decorators import licence_required
from ATIBAreport.graph_generator import hitsListForTest, help_psqlDateTimeFormats, help_psqlStringOps, \
    check_services_result_samples
from ATIBAreport.project_common import *
from ATIBAreport.reachjava import *
from ATIBAreport.setting_files.passes import postgresql_conn_string_prod, postgresql_conn_string_dev, \
    atibaApiService_API_KEY, atibaApiService_PORT
from AgentRoot.forms import *
from accounts.models import *
from inventories.models import *
from inventories.views import template_message_show

locale.setlocale(locale.LC_ALL, locale='tr_TR.utf8')
logger = logging.getLogger('views')
timer = logging.getLogger('timer')
memory_tracer = logging.getLogger('memorytracer')
# logger.setLevel(logging.INFO)

# signal = Signal(providing_args=['signal_data'])
postgresql_conn_string = postgresql_conn_string_prod if check_environment_for_elastic() else postgresql_conn_string_dev
globalBool = True
globalList = []
globalElasticLogList = []
globalAggregation = None

# Home page views in here


@xframe_options_sameorigin
def loading_view(request):
    logger.debug(f"Loading screen appeared..")
    return render(request, "loading.html", {'route': 'atiba_loading'})


@xframe_options_sameorigin
def not_found_view(request):
    logger.debug(f"Not Found screen appeared..")
    return render(request, "loading.html", {'route': 'not_found'})


@login_required
def check_license(request):
    time_triggered = datetime.datetime.now()
    route = ""
    _updt = 0
    _today = datetime.datetime.now()
    is_expired = True
    active_lics = []
    licenseCount = AtibaLicense.objects.count()
    logger.info(f"We got total {licenseCount} license")
    if licenseCount > 0:
        licenseList = AtibaLicense.objects.all()
        for lic in licenseList:
            if not lic.is_converted_python():
                try:
                    _lic_json_string = decode_with_java(lic.licenseStringJava)
                    if _lic_json_string and _lic_json_string != "":
                        _lic_json = json.loads(_lic_json_string)
                        logger.info(f"Got license which is not pythonized : ({_lic_json})")
                        _expiration = datetime.datetime.strptime(_lic_json["atiba-license"]["exp_date"], "%d-%m-%Y")
                        lic.licenseStringPython = atiba_encrypt(json.dumps(_lic_json))
                        try:
                            if _expiration and (_expiration - _today).days > 0:
                                is_expired = False
                                lic.isExpired = False
                                active_lics.append(lic)
                            else:
                                lic.isExpired = True

                            lic.save()

                        except Exception as err:
                            logger.exception(f"An error occurred trying to save lic. ERROR IS : {err}")
                except Exception as err:
                    logger.exception(
                        f"An error occurred in check_license view trying to decode_with_java. ERROR IS : {err}")

            else:
                if lic.lictype is None:
                    _updt += AtibaLicense.objects.filter(id=lic.id).update(lictype=lic.get_license_type())

                if lic.lictype == 'permanent':
                    is_expired = False
                    active_lics.append(lic)

                _expiration = lic.get_license_expiration()
                if _expiration and (_expiration - _today).days > 0:
                    if lic.isExpired is None:
                        _updt += AtibaLicense.objects.filter(id=lic.id).update(isExpired=False)
                    is_expired = lic.isExpired if lic.isExpired else False
                    active_lics.append(lic)

                if check_environment_for_production() and not lic.is_license_valid():
                    if lic.failoverdate:
                        # it means that master is down on this date, and machine running on back-up node. Let the
                        # license work for 15 days
                        _failing_days = (time_triggered.date() - lic.failoverdate).days
                        if _failing_days < 15:
                            logger.critical(f"SYSTEM IS WORKING ON A SLAVE NODE FOR {_failing_days} DAYS, "
                                            f"IMMEDIATELY RETURN TO MASTER NODE !!")
                            template_message_show(request,
                                                  "error",
                                                  f"System is working in recovery mode for {_failing_days} days")
                        else:
                            logger.warning(f"SYSTEM DO NOT MATCH LICENSE : {lic.id}")
                            _updt += AtibaLicense.objects.filter(id=lic.id).update(isExpired=True)

        logger.info(f"lic update count is : {_updt}")
        logger.info(f"active license count is : {len(active_lics)}")
        # logger.debug(f"is_expired is : {is_expired}")

        if len(active_lics) > 0 and not is_expired:
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('home')
        else:
            # send to new license form
            route = "LICENSE EXPIRED"
            logger.warning("LICENSE EXPIRED")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('accounts:add_license')
    else:
        # send to new license form
        route = "NO LICENSE"
        logger.warning("NO LICENSE")
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return redirect('accounts:add_license')

    # context = {
    #     'route': route,
    # }

    # return render(request, 'accounts/register_and_login.html', {'route': route})


def error_pages(request, **kwargs):
    if kwargs:
        logger.debug(f"we got parameters : {kwargs}")
    route = None
    warning = None
    myLogList = []

    context = {
        "route": route, "warning": warning, "myLogList": myLogList,
    }
    return render(request, 'errors.html', context)


@licence_required
@xframe_options_sameorigin
def home_view(request):
    time_triggered = datetime.datetime.now()
    _today = datetime.date.today()
    startDate = _today-datetime.timedelta(days=6)
    startDateString = startDate.strftime("%Y-%m-%d")
    endDate = _today
    endDateString = _today.strftime("%Y-%m-%d")
    logger.info(f"TODAY : {_today}")
    logger.info(f"USER IS : {request.user}")
    # _usersCount = User.objects.filter(is_djangoUser=True).count()

    if check_psql_is_recovery():
        return redirect('cluster')

    # GREETING PAGE CONTROL
    try:
        referer = request.META['HTTP_REFERER']
        logger.debug(f"Request from internal guest : {referer} in port {request.META['SERVER_PORT']}")
    except Exception as err:
        logger.warning(f"Request from external guest : {err} in port {request.META['SERVER_PORT']}")
        timer.debug(f"{(datetime.datetime.now()-time_triggered).total_seconds()}")
        return render(request, 'greeting.html')

    # CHECKING PSQL, ELASTIC CONNECTIONS AND HEALTH INFO
    elastic_health = check_elastic_health()
    psql_health = check_psql_health()
    if not elastic_health or not psql_health:
        errorDay = datetime.date.today()
        myLogList = read_your_own_logs(end_date=errorDay, start_date=errorDay)[0]
        myLogList = [_ for _ in myLogList if _.startswith("[ERROR") or _.startswith("[WARNING")]
        myLogList.reverse()
        if not elastic_health and not psql_health:
            cause = "database"
            explanation = f"Errors in both Postgresql and Elacticsearch connection"
            # return redirect('error_pages')
            return render(request, 'errors.html', {"route": cause, "warning": explanation, "myLogList": myLogList})

        elif not psql_health:
            cause = "database"
            explanation = f"Errors in Postgresql connection"
            # return redirect('error_pages')
            return render(request, 'errors.html', {"route": cause, "warning": explanation, "myLogList": myLogList})

        elif not elastic_health:
            cause = "database"
            explanation = f"There are problems in Elacticsearch connection"
            # return redirect('error_pages')
            return render(request, 'errors.html', {"route": cause, "warning": explanation, "myLogList": myLogList})

    # USER LOGIN CONTROL
    # if _usersCount == 0 and not request.user.is_authenticated:
    #     return redirect('accounts:accounts_register')
    if not request.user.is_authenticated:
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return redirect('accounts:accounts_login')

    # CHECKING PSQL IS IN RECOVERY MODE OR NOT. IF RESULT IS TRUE THEN WE ARE IN SLAVE NODE !!!
    isPSQLrecovery = check_psql_is_recovery()
    if isPSQLrecovery:
        logger.warning(f"PSQL is in recovery mode. Probably you are working on slave node. ETH0IP : {es_host_list[0]}")
        template_message_show(request, 'warning',
                              f'You are not in master node, manage backup cluster position. IP : {es_host_list[0]}')
        return redirect('cluster')

    # START TRACING MEMORY ALLOCATION BECAUSE NO MORE REDIRECTIONS BELOW, SAFE NOW FOR THIS
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()

    # Locations part
    locationCount = DevLocations.objects.count()
    location_chart_values = [locationCount]
    location_chart_labels = ["Count"]
    logger.debug(f"Dev Locations table total count : {locationCount}")

    # Sources part
    deviceTotalCount = LogSources.objects.count()
    deviceGreenCount = LogSources.objects.filter(status="A").count()
    deviceRedCount = LogSources.objects.filter(status="P").count()
    deviceOrangeCount = LogSources.objects.exclude(status="A").exclude(status="P").count()
    device_chart_values = [deviceGreenCount, deviceRedCount, deviceOrangeCount]
    device_chart_labels = ["Active", "Passive", "Unknown"]
    logger.debug(f"Devices total count : {deviceTotalCount}")

    # Sources by brand part
    # sources = LogSources.objects.all()
    # brandids = list(set([_.markid for _ in sources]))
    brandids = list(
        set(
            list(LogSources.objects.values_list('markid', flat=True).exclude(markid__isnull=True).exclude(markid=0))))
    sources_chart_labels = []
    sources_chart_values = []
    for brandid in brandids:
        if not brandid and brandid == 0:
            continue
        try:
            sources_chart_labels.append(DeviceMark.objects.get(id=brandid).markname)
            sources_chart_values.append(LogSources.objects.filter(markid=brandid).count())
        except Exception as err:
            logger.error(
                f"An error occurred trying to get brand info from devicemark table with id {brandid}. ERROR IS : {err}")
            template_message_show(
                request, "error",
                "Some drivers are missing, please install updated log sources drivers or contact to your reseller")
    sources_chart_labels.append("Unknown")
    sources_chart_values.append(
        LogSources.objects.filter(Q(markid=0) | Q(markid__isnull=True)).filter(connectedmac__isnull=True).count())
    logger.info(f"Brand list for sources : {sources_chart_labels}")
    logger.info(f"Brand counts for sources : {sources_chart_values}")

    # Unparsed logs part
    try:
        logTotalCount = Logs.objects.count()
        logsInQueue = Logs.objects.filter(recstatus=0).count()
        logsUnmapped = Logs.objects.filter(recstatus__in=[1, 2]).filter(mappedlogsource__isnull=True).count()
        logsMapped = Logs.objects.filter(recstatus__in=[1, 2]).exclude(mappedlogsource__isnull=True).count()
    except Exception as err:
        logger.exception(f"An error occurred while trying to count loglar table. ERROR IS : {err}")
        logTotalCount = 0
        logsInQueue = 0
        logsUnmapped = 0
        logsMapped = 0
    if check_environment_for_elastic():
        try:
            elastic_connection = Elasticsearch(es_host_list,
                                               scheme='http',
                                               port=es_port_number, sniff_on_start=True, request_timeout=2)
            _body = '{"query": {"bool": {"must":[{"term":{"mappedlogsource":{"value": "null","boost":1.0}}}],"adjust_pure_negative":true,"boost":1.0}}}'
            _body = json.loads(_body)
            search = elastic_connection.count(index="atibaloglar", body=_body)
            inElasticUnmapped = int(search["count"])
            logsUnmapped += inElasticUnmapped
            # GET / atibaloglar / _count
            # {"query": {"match_all": {}}}
            # {
            #     "count": 196067,
            #     "_shards": {
            #         "total": 10,
            #         "successful": 10,
            #         "skipped": 0,
            #         "failed": 0
            #     }
            # }
            # _body = '{"size":0, "query": {"match_all": {}} }'
            # _body = json.loads(_body)
            # search = elastic_connection.search(index="atibaloglar", body=_body)
            # logsMapped += (int(search["hits"]["total"]["value"]) - inElasticUnmapped)
            _body = '{"query": {"match_all": {}} }'
            _body = json.loads(_body)
            search = elastic_connection.count(index="atibaloglar", body=_body)
            logsMapped += (int(search["count"]) - inElasticUnmapped)
        except Exception as err:
            logger.exception(f"An error occurred trying to connect elasticsearch for log counts : {err}")
            template_message_show(request, "error", f"ELASTIC CONNECTION FAILED : {err}")

    log_chart_values = [logsInQueue, logsUnmapped, logsMapped]
    log_chart_labels = ["Queue", "Unmapped", "Mapped"]
    totalUnparsedLogs = logsInQueue+logsUnmapped+logsMapped
    logger.info(f"Total Unparsed Log Count is {totalUnparsedLogs}. {logTotalCount} of that in PSQL loglar table.")

    # All Logs and 7 days histogram parts
    elasticLogCount = 0
    # FOR ENVIRONMENT THAT ELASTIC RUN --------------------------------------------------------------------------
    if check_environment_for_elastic():
        weeklyLogs_chart_labels = []
        weeklyLogs_chart_values = []
        try:
            elastic_connection = Elasticsearch(es_host_list,
                                               scheme='http',
                                               port=es_port_number, sniff_on_start=True, request_timeout=2)
            _body = '{"size": 0, "query":{"bool":{"must":[{"range": {"credate": {"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}}], "adjust_pure_negative": true, "boost": 1.0}},"aggregations":{"sonuc":{"date_histogram":{"field":"credate","interval":"1d","offset":0,"format":"yyyy-MM-dd","order":{"_key":"asc"},"keyed":false,"min_doc_count":0,"extended_bounds" : { "min" : "%s","max":"%s"}}}}}' % (startDateString, endDateString, startDateString, endDateString)
            _body = json.loads(_body)
            search = elastic_connection.search(index="atibalogs", body=_body)
            elastic_aggregation = AggregationElastic(dictionary=search["aggregations"], aggregation_name="sonuc")
            for x, y in elastic_aggregation.kvtupples:
                if x == "key_as_string":
                    weeklyLogs_chart_labels.append(y)
                if x == "doc_count":
                    weeklyLogs_chart_values.append(y)
        except Exception as err:
            logger.exception(f"An error occurred trying to connect elasticsearch for logs histogram : {err}")
            template_message_show(request, "error", f"ELASTIC CONNECTION FAILED : {err}")
            weeklyLogs_chart_labels = [startDateString, endDateString]
            weeklyLogs_chart_values = [0, 0]
        finally:
            logger.info(f"Logs in Elastic weekly total : {sum(weeklyLogs_chart_values)}")

        try:
            elastic_connection = Elasticsearch(es_host_list,
                                               scheme='http',
                                               port=es_port_number, sniff_on_start=True, request_timeout=2)
            search = elastic_connection.count(index="atibalogs", body={"query": {"match_all": {}}})
            elasticLogCount = int(search["count"])
        except Exception as err:
            elasticLogCount = 0
            logger.exception(f"An error occurred trying to connect elasticsearch for logs doughnut : {err}")
            template_message_show(request, "error", f"ELASTIC CONNECTION FAILED : {err}")
        finally:
            logger.info(f"Logs in Elastic total count : {elasticLogCount}")
            LogsElastic_chart_values = [elasticLogCount, totalUnparsedLogs]
            LogsElastic_chart_labels = ["Parsed", "Un-Parsed"]
    else:
        # FOR LOCAL WITH NO ELASTIC -----------------------------------------------------------------------------
        weeklyLogs_chart_labels = [startDateString, endDateString]
        weeklyLogs_chart_values = [500, 1200]
        LogsElastic_chart_values = [elasticLogCount, totalUnparsedLogs]
        LogsElastic_chart_labels = ["Parsed", "Un-Parsed"]
        logger.warning(f"NO ELASTIC CONNECTION total count : {elasticLogCount}")
        logger.info(f"Logs in Elastic weekly total : {sum(weeklyLogs_chart_values)}")
        logger.info(f"Logs in Elastic total count : {elasticLogCount}")

    # Incident & Root-Cause part
    rcTotalCount = RootCauseGraphsDetails.objects.count()
    rc_chart_values = [rcTotalCount]
    rc_chart_labels = ["Count"]
    logger.info(f"Root Cause Graphs total count : {rcTotalCount}")

    # Alerts part
    # res = Anomalies.objects.all().values('anomalytype').annotate(total=Count('anomalytype')).order_by('total')
    res = Anomalies.objects.all().values('anomalytype').annotate(total=Count('anomalytype')).order_by('anomalytype')
    logger.debug(f"{res}")
    alerts_chart_labels = [GeneralParameterDetail.objects.filter(kisakod="ANMLTYPE").get(
        kod=int(x['anomalytype'])).kisaack for x in res]
    alerts_chart_values = [int(x['total']) for x in res]

    # incident detection info for all data
    alertCount = Anomalies.objects.exclude(analyzedstatus=9).count()
    incidentCount = len(set(RootCauseGraphsDetails.objects.values_list("incidentid", flat=True).exclude(incidentid__isnull=True)))
    incidentOccurrence = round((incidentCount*100/alertCount)*1000)/1000 if alertCount else 100
    incidentPercentage = round((incidentCount*100/elasticLogCount)*1000)/1000 if elasticLogCount else 100

    # incidentSentence = f"{incidentCount} incidents detected overall {elasticLogCount} logs. Incident occurrence percentage is {incidentPercentage}% for the given environment."
    # newsList = [
    #     (get_percentage_pri(incidentPercentage), incidentSentence),
    # ]

    overViewData = [
        ("TOTAL EVENTS", elasticLogCount),
        ("TOTAL ALERTS", alertCount),
        ("TOTAL INCIDENTS", incidentCount),
        ("INCIDENT OCCURRENCE", f"{incidentOccurrence} %"),
        ("NOISE REDUCTION", f"{100-incidentPercentage} %")
    ]

    context = {
        'log_chart_values': log_chart_values, 'log_chart_labels': log_chart_labels,
        'rc_chart_values': rc_chart_values, 'rc_chart_labels': rc_chart_labels,
        'device_chart_values': device_chart_values, 'device_chart_labels': device_chart_labels,
        'sources_chart_values': sources_chart_values, 'sources_chart_labels': sources_chart_labels,
        'location_chart_values': location_chart_values, 'location_chart_labels': location_chart_labels,
        'LogsElastic_chart_values': LogsElastic_chart_values, 'LogsElastic_chart_labels': LogsElastic_chart_labels,
        'weeklyLogs_chart_values': weeklyLogs_chart_values, 'weeklyLogs_chart_labels': weeklyLogs_chart_labels,
        'alerts_chart_values': alerts_chart_values, 'alerts_chart_labels': alerts_chart_labels,
        'overViewData': overViewData,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'home.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def search_from_nav(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()

    route = "OK"
    keyWord = None
    _anomaly_log_ids, _alerts, _incidents, _logs = [], [], [], []

    if request.method == 'POST':
        # logger.debug(f"Post request is : {request.POST}")
        keyWord = request.POST.get('key_word') if check_existence(request.POST.get('key_word')) else None
        if keyWord:
            _anomaly_log_ids = list(AnomalyLogs.objects.values_list("id", "anomaliesid", "logids").filter(
                Q(logevent__icontains=keyWord)))
            # logger.debug(f"AnomalyLogs id list : {_anomaly_log_ids}")
            logger.info(f"{len(_anomaly_log_ids)} AnomalyLogs found contain '{keyWord}'")

            # GETTING INCIDENTS AND ALERTS;
            for _ in _anomaly_log_ids:
                try:
                    _incidents += list(RootCauseGraphsDetails.objects.exclude(incidentid__isnull=True).filter(
                        nodelist__contains=[_[0]], analyzedstatus=2))
                    _alerts += list(Anomalies.objects.exclude(analyzedstatus=9).filter(id=_[1])) if _[1] else []
                    _logs += _[2] if _[2] else []
                except Exception as err:
                    logger.exception(f"An error occurred trying to get search result for '{keyWord}'. ERROR IS : {err}")
            _incidents = list(set(_incidents))
            _alerts = list(set(_alerts))
            _logs = list(set(_logs))
            # _incidents = [_.get_incident_set for _ in _incidents]
            _incidents.sort(key=lambda x: x.id, reverse=True)
            _alerts.sort(key=lambda x: x.id, reverse=True)
            # _logs.sort(key=lambda x: x.id, reverse=True)
            _logs.sort(reverse=True)
            logger.info(f"{len(_incidents)} RootCauseGraphsDetails found related with '{keyWord}' somehow")
            logger.info(f"{len(_alerts)} Anomalies found related with '{keyWord}' somehow")
            logger.info(f"{len(_logs)} LogsFromElastic found possibly containing '{keyWord}'")
            # logger.debug(f"Elastic log ids : {_logs}")
            # _logs = []
        else:
            keyWord = "No value to search"
    else:
        route = "ERROR"
        keyWord = "You came here directly with url, this is not a correct way to search. Use the search tool " \
                  "in the navigation"

    context = {
        'route': route, 'keyWord': keyWord, 'alertList': _alerts, 'incidentList': _incidents, 'logList': _logs,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'search.html', context)


@licence_required
# @login_required
@xframe_options_sameorigin
@csrf_exempt
def rc_flowing(request):
    """
    Now it's deprecated, but there are some links to call this view and it's working...
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    if not request.user.is_authenticated:
        route = 'timeout'
    else:
        route = 'general'

    def recall_rc_list(_limit=10):
        return list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2)[:_limit])

    #
    rc_without_image = list(RootCauseGraphsDetails.objects.values_list('id', flat=True).filter(graphimage__isnull=True))
    if rc_without_image:
        logger.info(f"There are {len(rc_without_image)} RootCauseGraphDetails without graph image")
        _thread.start_new_thread(create_rc_picture, ())

    networkDevices = NetworkDevice.objects.all()
    _newCount = 0
    rcTotalCount = RootCauseGraphsDetails.objects.count()
    # logger.info(f"we have request, is it from machine? - {request.is_ajax()}")
    if request.is_ajax():
        logger.info(f"Flowing, update check..")
        _first_id = int(request.POST.get('first_id'))
        _count = int(request.POST.get('count'))
        if rcTotalCount > _count:
            # logger.info(f"there is new records in database")
            rcList = recall_rc_list(_limit=50)
            # _sortedRcList = filter_rc_list(rcList)  # function is deprecated !!
            # _old_first_index = _sortedRcList.index(RootCauseGraphsDetails.objects.get(id=_first_id))
            _old_first_index = rcList.index(RootCauseGraphsDetails.objects.get(id=_first_id))
            if _old_first_index > 0:
                _newCount = _old_first_index + 1
                logger.info(f"refreshing page for new record count {_newCount}")
                context1 = {
                    'rcList': rcList, 'rcTotalCount': str(rcTotalCount), 'newCount': _newCount, 'command': 1
                }
                # top_stats = tracemalloc.take_snapshot().statistics('lineno')
                # total_size, unit = take_memory_usage(top_stats)
                # logger.info(f"Memory allocation  {total_size} {unit}")
                # memory_tracer.info(f"{total_size}")
                # tracemalloc.stop()
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return JsonResponse({'command': 1, 'newCount': _newCount}, status=200)
            else:
                logger.info(f"No new record to show")
                # top_stats = tracemalloc.take_snapshot().statistics('lineno')
                # total_size, unit = take_memory_usage(top_stats)
                # logger.info(f"Memory allocation  {total_size} {unit}")
                # memory_tracer.info(f"{total_size}")
                # tracemalloc.stop()
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return JsonResponse({'command': 0}, status=200)
        else:
            logger.info(f"No new row in database")
            # top_stats = tracemalloc.take_snapshot().statistics('lineno')
            # total_size, unit = take_memory_usage(top_stats)
            # logger.info(f"Memory allocation  {total_size} {unit}")
            # memory_tracer.info(f"{total_size}")
            # tracemalloc.stop()
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return JsonResponse({'command': 0}, status=200)
    else:
        rcList = recall_rc_list(_limit=30)
        context = {
            'route': route, 'rcList': rcList, 'rcTotalCount': str(rcTotalCount), 'newCount': _newCount,
            'networkDevices': networkDevices,
        }
        try:
            top_stats = tracemalloc.take_snapshot().statistics('lineno')
            total_size, unit = take_memory_usage(top_stats)
            logger.info(f"Memory allocation  {total_size} {unit}")
            memory_tracer.info(f"{total_size}")
            tracemalloc.stop()
        except:
            logger.debug("tracemalloc stopped before somehow")
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return render(request, 'flowing.html', context)


global_rcd_count, global_anomaly_count = 0, 0


@licence_required
# @login_required
@xframe_options_sameorigin
@csrf_exempt
def incidents_home(request):
    time_triggered = datetime.datetime.now()
    global global_rcd_count, global_anomaly_count

    if not request.user.is_authenticated:
        route = 'timeout'
    else:
        route = 'general'

    # Preparing the directed network graph images for rcgraphsdetails objects
    rc_without_image = list(RootCauseGraphsDetails.objects.values_list('id', flat=True).filter(graphimage__isnull=True))
    if rc_without_image:
        logger.info(f"There are {len(rc_without_image)} RootCauseGraphDetails without graph image")
        _thread.start_new_thread(create_rc_picture, ())

    if request.is_ajax():
        # logger.debug(f"Ajax request details : {request.POST}")
        logger.info(f"Detections, update check..")
        if request.POST.get("action") == "check_for_new":
            current_rcd_count = RootCauseGraphsDetails.objects.count()
            current_anomaly_count = Anomalies.objects.count()
            if current_rcd_count > global_rcd_count or current_anomaly_count > global_anomaly_count:
                logger.info(f"New record detected. Incidents {current_rcd_count - global_rcd_count}, Alerts {current_anomaly_count - global_anomaly_count}")
                global_rcd_count, global_anomaly_count = current_rcd_count, current_anomaly_count
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return JsonResponse({'command': 1}, status=200)
            else:
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return JsonResponse({'command': 0}, status=200)
        else:
            logger.info(f"Request is not for new record check")
    else:
        global_rcd_count = RootCauseGraphsDetails.objects.count()
        global_anomaly_count = Anomalies.objects.count()

    sources = list(LogSources.objects.exclude(scanstatus=9).filter(connectedmac__isnull=True))

    # open_alerts_by_source = list(Anomalies.objects.values(
    #     "lsuniqueid").exclude(analyzedstatus=9).filter(status="000").annotate(
    #     total=Count("id", distinct=True), recent=Max("id")).order_by("lsuniqueid"))
    # closed_alerts_by_source = list(Anomalies.objects.values(
    #     "lsuniqueid").exclude(analyzedstatus=9).filter(status="001").annotate(
    #     total=Count("id", distinct=True), recent=Max("id")).order_by("lsuniqueid"))

    alerts_by_source = list(Anomalies.objects.values(
        "lsuniqueid", "status").exclude(analyzedstatus=9).annotate(
        total=Count("id", distinct=True), recent=Max("id")).order_by("lsuniqueid"))

    # qq = """
    # with rcgdtabopen as (select array_agg(distinct(rcgd.id)) as rcgdid, rcgd.incidentid from rcgraphsdetails rcgd join
    # incidents i on rcgd.rootlist && i.anomalies where i.isopen group by rcgd.incidentid),
    # rcgdtabclose as (select array_agg(distinct(rcgd.id)) as rcgdid, rcgd.incidentid from rcgraphsdetails rcgd join
    # incidents i on rcgd.rootlist && i.anomalies where not i.isopen group by rcgd.incidentid)
    # select al.uniqueid, array_agg(distinct(rcgdtabopen.incidentid)), array_agg(distinct(rcgdtabclose.incidentid)) from
    # anomalylogs al left join rcgdtabopen  on al.id = ANY(rcgdtabopen.rcgdid) left join rcgdtabclose  on
    # al.id = ANY(rcgdtabclose.rcgdid) group by al.uniqueid
    # """

    # qq = "CREATE AGGREGATE array_concat_agg(anyarray) (SFUNC = array_cat, STYPE = anyarray);"

    qq = """
    with rcgdtabopen as (select array_concat_agg(distinct(rcgd.rootlist)) as rcgdid, rcgd.incidentid from 
    rcgraphsdetails rcgd join incidents i on rcgd.rootlist && i.anomalies where i.isopen group by rcgd.incidentid),
    rcgdtabclose as (select array_concat_agg(distinct(rcgd.rootlist)) as rcgdid, rcgd.incidentid from 
    rcgraphsdetails rcgd join incidents i on rcgd.rootlist && i.anomalies where not i.isopen group by rcgd.incidentid) 
    select al.uniqueid, array_agg(distinct(rcgdtabopen.incidentid)),array_agg(distinct(rcgdtabclose.incidentid)) 
    from anomalylogs al left join rcgdtabopen  on al.id = ANY(rcgdtabopen.rcgdid) left join rcgdtabclose  on 
    al.id = ANY(rcgdtabclose.rcgdid) group by al.uniqueid
    """
    conn = psycopg2.connect(postgresql_conn_string)
    cur = conn.cursor()
    cur.execute(qq)
    incs_by_source = cur.fetchall()
    cur.close()
    logger.debug(f"Incident ids by log sources : {type(incs_by_source)} : {incs_by_source}")
    logger.debug(f"Alerts by log sources : {type(alerts_by_source)} : {alerts_by_source}")

    incident_list = source_incident_alert_organizer(sources, incs_by_source, alerts_by_source)

    context = {
        'route': route, 'incident_list': incident_list,
    }
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/incidents_home.html', context)


@licence_required
@login_required
@csrf_exempt
def incidents_monitor(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "general"

    if request.POST:
        logger.debug(f"POST request incident set open|close : {request.POST}")
        _i_id = request.POST.get('change_status')
        try:
            _incident = Incidents.objects.get(id=int(_i_id))
            # if _incident.isopen and _incident.closedate is None:
            #     _incident.closedate = datetime.datetime.now()
            _incident.closedate = datetime.datetime.now() if _incident.isopen else None
            _incident.isopen = not _incident.isopen
            _incident.save()
            template_message_show(request, 'success', 'Status changed successfully')
        except Exception as err:
            logger.exception(f"An error occurred trying to change incident status : {err}")

    # incident_list = list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2))

    incident_list = Incidents.objects.all()

    uniqueid_q = request.GET.get("uniqueid_q")
    status_q = request.GET.get("status_q")
    if uniqueid_q:
        incident_list = list(filter(lambda x: uniqueid_q in [a.uniqueid for a in x.get_root_devices()], incident_list))
    if status_q:
        if "Closed".lower().find(status_q.lower()) >= 0 or "Kapalı".lower().find(status_q.lower()) >= 0:
            incident_list = list(filter(lambda x: not x.isopen, incident_list))
        elif "Open".lower().find(status_q.lower()) >= 0 or "Açık".lower().find(status_q.lower()) >= 0:
            incident_list = list(filter(lambda x: x.isopen, incident_list))

    paginator = Paginator(incident_list, record_per_page)
    page = request.GET.get('page')
    try:
        incident_list = paginator.page(page)
    except PageNotAnInteger:
        incident_list = paginator.page(1)
    except EmptyPage:
        incident_list = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'incident_list': incident_list,
    }
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/incidents.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def diagnoses_for_incidentset(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "inincident"

    # incident_list = list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2))

    rc_list = list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2).filter(incidentid=id))
    if not rc_list:
        # it means no rc graph matching with given arguments analyzedstatus and incidentid
        context = {
            'route': route, 'rc_list': rc_list, 'setID': id,
            'dataWarning': "Probably analyse not completed yet or causal mapping didn't generated ..."
        }
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return render(request, 'AgentRoot/incidents.html', context)

    paginator = Paginator(rc_list, record_per_page)
    page = request.GET.get('page')
    try:
        rc_list = paginator.page(page)
    except PageNotAnInteger:
        rc_list = paginator.page(1)
    except EmptyPage:
        rc_list = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'rc_list': rc_list, 'setID': id,
    }
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/incidents.html', context)


globalRcList = []  # its just for diagnosis_monitor view function
globalResultSentence = ""
globalRcListLength = None


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def diagnosis_monitor(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "detail"
    rc_list = []
    result_sentence = None
    global globalRcList, globalResultSentence, globalRcListLength

    selection_choices = list(set(AnomalyLogs.objects.values_list("paramvariable", flat=True).filter(
        paramvariable__isnull=False)))

    # incident_list = list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2))

    if request.method == "POST":
        logger.debug(f"Post request details : {request.POST}")
        _param_name = request.POST.get("parameter_name") if check_existence(
            request.POST.get("parameter_name")) else None
        _param_value = request.POST.get("parameter_value") if check_existence(
            request.POST.get("parameter_value")) else None
        _reset_search = request.POST.get("reset_search") if check_existence(request.POST.get("reset_search")) else None

        if not _reset_search:
            _anomalylogs_idlist = list(AnomalyLogs.objects.values_list(
                "id", flat=True).filter(paramvariable=_param_name).filter(
                Q(paramvalue__icontains=_param_value))) if _param_name and _param_value else []

            _anomalylogs_idlist += list(AnomalyLogs.objects.values_list(
                "id", flat=True).filter(paramvariable__isnull=True).filter(
                Q(logevent__icontains=_param_value))) if _param_value else []

            logger.info(f"{len(_anomalylogs_idlist)} anomalylogs id list for {_param_name} = {_param_value} : {_anomalylogs_idlist}")

            # rc_list = list(RootCauseGraphsDetails.objects.filter(nodelist__in=[_anomalylogs_idlist],
            #                                                      analyzedstatus=2)) if _anomalylogs_idlist else []

            if _anomalylogs_idlist:
                for _ in _anomalylogs_idlist:
                    rc_list += list(RootCauseGraphsDetails.objects.filter(nodelist__contains=[_], analyzedstatus=2))
                rc_list = list(set(rc_list))
                rc_list.sort(key=lambda x: x.id, reverse=True)

            result_sentence = f"Found {len(rc_list)} Root Cause Graphs for {_param_name if _param_name else 'All'} related with {_param_value}"
            logger.info(result_sentence)
            globalResultSentence = result_sentence
            globalRcList = rc_list
            globalRcListLength = len(rc_list)
        else:
            # reset search button pressed.
            rc_list = list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2))
            globalResultSentence = ""
            globalRcList = rc_list
            globalRcListLength = len(rc_list)

    else:
        # if there is a new record ??
        if not globalRcList:
            rc_list = list(RootCauseGraphsDetails.objects.filter(analyzedstatus=2))
            globalResultSentence = ""
            globalRcList = rc_list
            globalRcListLength = len(rc_list)
        else:
            rc_list = globalRcList
            result_sentence = globalResultSentence
            globalRcListLength = len(rc_list)

    paginator = Paginator(rc_list, record_per_page)
    page = request.GET.get('page')
    try:
        rc_list = paginator.page(page)
    except PageNotAnInteger:
        rc_list = paginator.page(1)
    except EmptyPage:
        rc_list = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'rc_list': rc_list, 'selection_choices': selection_choices, 'result_sentence': result_sentence,
    }
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/incidents.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def diagnosis_analyse(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "general"

    _rcMap = None
    try:
        _rcMap = RootCauseGraphsDetails.objects.get(id=id)
    except Exception as err:
        # current_rc is None in here and it's pointing to possible data corruption
        logger.exception(f"An error occurred trying to get rcgraphdetails record with id {id}. ERROR IS : {err}")
        context = {
            'route': route, '_rcMap': _rcMap,
        }
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return render(request, 'AgentRoot/incidents_analyse.html', context)

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
            _changed = False
            _form_response = request.POST
            logger.debug(f"Form response is : {_form_response}")
            # logger.debug(f"{_form_response.getlist('correction_feedbacks')}")
            logger.debug(f"{_form_response.get('_disable_alers_for_logcode')}")

            if '_disable_alers_for_logcode' in _form_response.keys() and _form_response.get(
                    '_disable_alers_for_logcode') != "None":
                _disable_alers_for_logcode = _form_response.get('_disable_alers_for_logcode')
                logger.info(f"Closing Alerts for logcode {_disable_alers_for_logcode}")
                try:
                    _updated = LogDefinitionDetails.objects.filter(
                        logcode=_disable_alers_for_logcode).update(userdisabled=True)
                    logger.info(f"Updated {_updated} rows of logdefdetails to userdisabled True")
                except Exception as err:
                    logger.exception(f"An error occurred trying to update logdefdetails for logcode {_disable_alers_for_logcode} to userdisabled True. ERROR IS : {err}")

            if 'rc_total_feedback' in _form_response.keys() and _form_response.get('rc_total_feedback') != "None":
                if _rcMap.giventotalfeed is None:
                    # _total_feed = _form_response.get('rc_total_feedback')
                    _total_feed = True if _form_response.get('rc_total_feedback') == "True" else False
                    logger.critical(f"Diagnosis with id {id} is totally {_total_feed}")
                    _incident_set_id = _rcMap.incidentid
                    _factor = 1.1 if _total_feed else 0.95

                    qq = f"""
                        update anomalylogsdetails set userfeedback = {_total_feed}, aistatus = 2, 
                        userscorefeedback = aioutputscore*{_factor} where id in (select ald.id from anomalylogsdetails ald 
                        join incidents i on (ald.alogid = ANY(i.anomalies) or ald.subalogid = ANY(i.anomalies)) 
                        where i.id = {_incident_set_id} and ald.causeeffect is not null)
                    """
                    logger.info(f"anomalylogsdetails update query : {qq}")
                    try:
                        conn = psycopg2.connect(postgresql_conn_string)
                        cur = conn.cursor()
                        cur.execute(qq)
                        # update_results = cur.fetchall()
                        conn.commit()
                        cur.close()
                        logger.info(f"anomalylogsdetails updated for given {_total_feed} feedback")
                        RootCauseGraphsDetails.objects.filter(id=id).update(giventotalfeed=_total_feed)
                        _rcMap.giventotalfeed = _total_feed
                        # _rcMap.save()
                        template_message_show(request, "success", f"Total feedback saved successfully")
                    except Exception as err:
                        logger.exception(f"An error occurred trying to update total feedback on pgsql ERROR IS : {err}")
                        template_message_show(request, "error", f"An error occurred ERROR IS : {err}")

                    # _graph_paths = json.loads(_rcMap.graphpaths)
                    # # logger.debug(f"Graph paths json to feed : {type(_graph_paths)} - {_graph_paths}")
                    # logger.info(f"Total feed started ..")
                    # for _ in _graph_paths:
                    #     _feed_list = []
                    #     for x in _.values():
                    #         _feed_string = ""
                    #         for i in range(len(x)):
                    #             if i > 0:
                    #                 _feed_string = f"{x[i]}-{_total_feed}-{x[0]}-{x[-1]}"
                    #             if _feed_string:
                    #                 _feed_list.append(_feed_string)
                    #     _changed = update_anomalylogsdetails_userfeedback(_graph_paths, _feed_list)
                    #     logger.info(f"List to total feed {_feed_list} is operated. Are there any changes : {_changed}")
                    # logger.info(f"Total feed completed .. ")
                else:
                    template_message_show(request, "info", f"There is a total feedback given before as {_rcMap.giventotalfeed}")

            if 'close_incident' in _form_response.keys() and _rcMap.incidentid:
                try:
                    Incidents.objects.filter(id=_rcMap.incidentid).update(isopen=False, closedate=time_triggered)
                    logger.info(f"Incident (id:{_rcMap.incidentid}) for rcgraphdetails (id:{id}) is closed successfully.")
                except Exception as err:
                    logger.exception(f"An error occurred trying to close incident with id {_rcMap.incidentid}. ERROR IS : {err}")

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
                # root_leaves = root_and_leaves(_rcMap.rootlist, json.loads(_rcMap.graphpaths), _rcMap.leaflist)
                template_message_show(request, 'success', 'Changes saved successfully')
    else:
        if list(RootCauseGraphsDetails.objects.values_list('graphimage', flat=True).filter(id=id))[0] is None:
            rc_picture_proccess = create_rc_picture(rc_id=id)
            if rc_picture_proccess == "BUSY":
                logger.warning(f"create_rc_picture(rc_id={id}) called and returned {rc_picture_proccess}")
            else:
                logger.info(f"create_rc_picture(rc_id={id}) called and returned {rc_picture_proccess}")

    analysisCase = "Analysis Completed" if _rcMap.analyzedstatus == 2 else "The analysis continues"

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
            anomalyType = anomalyType[:-1] + "ies" if anomalyType.endswith("Anomaly") else anomalyType + "s"
        definition_and_incident.append((anomalyType, _logs))
    logger.debug(f"DEFINITIONS & ANOMALYLOGS COLLECTION : {definition_and_incident}")

    # paths = json.loads(_rcMap.graphpaths)
    paths = _rcMap.get_paths()

    # root_leaves = root_and_leaves(_rcMap.rootlist, json.loads(_rcMap.graphpaths), _rcMap.leaflist)
    root_leaves = root_and_leaves(_rcMap.rootlist, paths, _rcMap.leaflist)
    if len(root_leaves) == 0:
        analysisCase = "The analysis is still ongoing ..."

    context = {
        'route': route, '_rcMap': _rcMap, 'code_list': code_list, 'root_leaves': root_leaves,
        'givenTotalFeed': _rcMap.giventotalfeed,
        'rcMap': _rcMap, 'leafList': rc_leafList, 'nodeList': rc_nodeList,
        'paths': paths, 'analysisCase': analysisCase, 'definition_and_incident': definition_and_incident,
        'dataWarning': dataWarning,
    }
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/incidents_analyse.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def system_configurations(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    _restart_atiba_logger = False
    sp_count = SystemParameters.objects.count()
    sp_list = SystemParameters.objects.all()
    sp = sp_list[0]

    current_autoparaminterval = sp.autoparaminterval
    current_autoparamtime = sp.autoparamtime
    current_log_lifetime = sp.loglifetime

    query = request.GET.get('log_q')
    if query:
        # .exclude(logsubdefcode=999) exclusion canceled to able to disable alerts with 999 structure
        ldd_log_list = LogDefinitionDetails.objects.filter(Q(outclasstype__icontains=query) |
                                                           Q(logcode__icontains=query) |
                                                           Q(logstructs__icontains=query) |
                                                           Q(logsarr__icontains=query) |
                                                           Q(logfields__icontains=query) |
                                                           Q(userdisabled__icontains=query)).distinct()
    else:
        ldd_log_list = []

    form1 = SystemParameterSettingsForm1(request.POST or None, instance=sp)

    if request.method == 'POST':
        logger.debug(f"request.POST is : {request.POST}")

        # add notify_email
        # if check_existence(request.POST.get('notify_email')):
        #     _new_email = request.POST.get('notify_email')
        #     _email_list = sp.notifyemails if sp.notifyemails else []
        #
        #     _email_list.append(_new_email)
        #     sp.notifyemails = _email_list
        #     try:
        #         sp.save()
        #         template_message_show(request, "success", f"New e-mail added to notify emails successfully")
        #     except Exception as err:
        #         logger.error(f"An error occurred trying to add e-mail to notify e-mails. ERROR IS : {err}")
        #         template_message_show(request, "error", f"Fail to add new notification email, ERROR : {err}")

        # delete_email
        # if check_existence(request.POST.get('delete_email')):
        #     _delete_it = request.POST.get('delete_email')
        #     _email_list = sp.notifyemails if sp.notifyemails else []
        #     _email_list.remove(_delete_it)
        #     sp.notifyemails = _email_list if _email_list else None
        #     try:
        #         sp.save()
        #         template_message_show(request, "success", f"{_delete_it} removed from notify emails successfully")
        #     except Exception as err:
        #         logger.error(f"An error occurred trying to remove {_delete_it} from notify e-mails. ERROR IS : {err}")
        #         template_message_show(request, "error", f"Fail to remove {_delete_it}, ERROR : {err}")

        if check_existence(request.POST.get('reset_ai')):
            logger.info(f"reset_ai for : {request.POST.get('reset_ai')}")
            try:
                reset_ai(request.POST.get('reset_ai'))
                template_message_show(request, 'success', f"Successfully reset {request.POST.get('reset_ai')} AI")
            except Exception as err:
                logger.exception(f"An error occurred in system_configurations view trying to reset_ai for {request.POST.get('reset_ai')}. ERROR IS : {err}")
                template_message_show(request, 'error', f"Failed to reset AI for {request.POST.get('reset_ai')}")

        if check_existence(request.POST.get('reboot')):
            if int(request.POST.get('reboot')) == 1:
                _reboot_result = reboot_system()
                if not _reboot_result:
                    template_message_show(request, 'error', 'Failed to reboot system')

        if len(request.POST.getlist('disableAlertCheckboxes')) > 0:
            chosen_ids = [int(_.replace(".", "")) for _ in request.POST.getlist('disableAlertCheckboxes')]
            _operation_count = 0
            for _ldd in ldd_log_list:
                if _ldd.id in chosen_ids and _ldd.userdisabled is False:
                    _ldd.userdisabled = True
                    _ldd.save()
                    _operation_count += 1
                elif _ldd.id not in chosen_ids and _ldd.userdisabled is True:
                    _ldd.userdisabled = False
                    _ldd.save()
                    _operation_count += 1
            template_message_show(request, message_type='success',
                                  message_content=f'{_operation_count} record updated successfully for alerts')

        if len(request.POST.getlist('priorityCheckboxes')) > 0:
            form_data = request.POST.getlist('priorityCheckboxes')
            # logger.debug(f"Form checkboxes data : {form_data}")
            tuple_list = []
            for tpl in form_data:
                _string = tpl.replace("(", "").replace(",", "").replace(")", "")
                _second = _string[-1]
                if len(_string) == 2:
                    _first = _string[0]
                elif len(_string) == 3:
                    _first = _string[0]+_string[1]
                tuple_list.append((int(_first), int(_second)))
            # logger.debug(f"tuple_list : {tuple_list}")
            readable_list = sp.get_readable_syslogpriorities()
            # logger.debug(f"readable_list : {readable_list}")
            if len(readable_list) > 0:
                for i in range(0, len(readable_list)):
                    for j in range(0, 8):
                        if (i, j) in tuple_list:
                            if not readable_list[i][j]:
                                _restart_atiba_logger = _restart_atiba_logger or True
                                readable_list[i][j] = True
                            else:
                                continue
                        else:
                            if readable_list[i][j]:
                                _restart_atiba_logger = _restart_atiba_logger or True
                                readable_list[i][j] = False
                            else:
                                continue
            # logger.debug(f"Anything changed? {_restart_atiba_logger}")
            if _restart_atiba_logger:
                isSaved = sp.set_syslogpriorities_from_readable(readable_list)
                if isSaved:
                    template_message_show(request,
                                          message_type='success',
                                          message_content='Changes on priorities saved successfully')
                    if check_environment_for_production():
                        logger.info(f"Changes saved for syslogpriorities and now iamatiba-logger being restart")
                        try:
                            # subprocess.call('systemctl restart iamatiba-logger')
                            if subprocess.call('systemctl stop iamatiba-logger', shell=True) == 0:
                                # time.sleep(1)
                                subprocess.call('systemctl start iamatiba-logger', shell=True)
                        except Exception as err:
                            logger.exception(f"An error occurred while running the commands to stop and start iamatiba-logger. ERROR IS : {err}")
                    else:
                        logger.warning(f"Changes saved for syslogpriorities but iamatiba-logger not being restart because we are not in production environment")
                else:
                    template_message_show(request,
                                          message_type='error', message_content='Failed to save changes on priorities')
            else:
                template_message_show(request, message_type='info', message_content='No change on priorities')

        if form1.is_valid():
            # logger.debug(f"form1 is valid : {form1}")

            if int(form1.cleaned_data.get('loglifetime')) != current_log_lifetime:
                logger.debug(
                    f"Current loglifetime {current_log_lifetime}, new value is {form1.cleaned_data.get('loglifetime')}")
                # change elasticsearch ilm life cycle policy delete option with new log lifetime value
                """
                -- put_lifecycle(policy, body=None, params=None, headers=None)
                """
                _body = {
                    "policy": {
                        "phases": {
                            "hot": {
                                "actions": {
                                    "rollover": {
                                        "max_primary_shard_size": "40GB",
                                        "max_age": "7d"
                                    }
                                }
                            },
                            "delete": {
                                "min_age": f"{int(form1.cleaned_data.get('loglifetime'))}d",
                                "actions": {
                                    "delete": {}
                                }
                            }
                        }
                    }
                }
                logger.debug(f"Body for elastic policy update : {_body}")
                try:
                    elastic_connection = Elasticsearch(es_host_list,
                                                       scheme='http',
                                                       port=es_port_number, sniff_on_start=True, request_timeout=2)
                    es_put_result = elastic_connection.ilm.put_lifecycle("atibalogs_policy", body=_body)
                    logger.info(f"Result of elasticsearch policy change : {es_put_result}")
                except Exception as err:
                    logger.exception(f"An error occurred trying to change delete policy in elastic. ERROR IS : {err}")

            try:
                # sp.loglifetime = form1.cleaned_data.get('loglifetime')
                # sp.newbehaviortime = form1.cleaned_data.get('newbehaviortime')
                # sp.timeseriesinterval = form1.cleaned_data.get('timeseriesinterval')
                sp.save()
                logger.info(f"System preferences saved successfully")
                template_message_show(request, message_type='success',
                                      message_content='User preferences saved successfully')
            except Exception as err:
                logger.exception(f"An error occurred trying to save system preferences. ERROR IS {err}")
                template_message_show(request, message_type='error', message_content=f'Some errors occurred ! {err}')

            if sp.autoparaminterval != current_autoparaminterval or sp.autoparamtime != current_autoparamtime:
                logger.info(f"autoparaminterval from {current_autoparaminterval} to {sp.autoparaminterval}")
                logger.info(f"autoparamtime from {current_autoparamtime} to {sp.autoparamtime}")
                logger.info(f"Parameter Analyst Service will be restarted")
                restart_iamatiba_service('iamatiba-loganalyze')
                # service_restart = restart_iamatiba_service('iamatiba-loganalyze')
                # if service_restart["code"] == 999:
                #     logger.error(f"restart iamatiba-loganalyze failed...")
                # else:
                #     logger.info(f"iamatiba-loganalyze restarted successfully..")
        else:
            # logger.debug(f"form1 is not valid : {form1}")
            pass

        # form1 = SystemParameterSettingsForm1(instance=sp)
        # else:
        #     template_message_show(request, 'error', 'Values are not in the proper range')

    _x = sp.get_readable_syslogpriorities()
    _y = [(sysLogPriorityLabels[_], _x[_]) for _ in range(0, len(_x))]  # Sys Log Priority Labels can be taken from db

    ldd_count = LogDefinitionDetails.objects.count()
    ldd_count_1 = LogDefinitionDetails.objects.filter(outclasstype="Information").count()
    ldd_count_2 = LogDefinitionDetails.objects.filter(outclasstype="Error").count()
    ldd_count_3 = LogDefinitionDetails.objects.filter(outclasstype="Warning").count()
    ldd_count_4 = LogDefinitionDetails.objects.filter(outclasstype="Debug").count()
    ldd_count_5 = LogDefinitionDetails.objects.filter(outclasstype="Critical").count()
    ldd_count_7 = LogDefinitionDetails.objects.filter(outclasstype="Notice").count()
    ldd_count_6 = (ldd_count-ldd_count_1-ldd_count_2-ldd_count_3-ldd_count_4-ldd_count_5-ldd_count_7)

    ldd_chart_values = [ldd_count_1, ldd_count_2, ldd_count_3, ldd_count_4, ldd_count_5, ldd_count_6, ldd_count_7]
    ldd_chart_labels = ["Information", "Error", "Warning", "Debug", "Critical", "None", "Notice"]

    # ldd_user_dis_1 = LogDefinitionDetails.objects.filter(userdisabled=True).exclude(logsubdefcode=999).count()
    # ldd_user_dis_2 = LogDefinitionDetails.objects.filter(userdisabled=False).exclude(logsubdefcode=999).count()
    ldd_user_dis_1 = LogDefinitionDetails.objects.filter(userdisabled=True).count()
    ldd_user_dis_2 = LogDefinitionDetails.objects.filter(userdisabled=False).count()

    ldd_user_dis_values = [ldd_user_dis_2, ldd_user_dis_1]
    ldd_user_dis_labels = ["Enabled", "Disabled"]

    licenseList = AtibaLicense.objects.all()

    context = {
        'sp_count': sp_count, 'sp_list': sp_list, 'sp': sp, 'form1': form1, 'priorities': _y,
        'sysLogPriorityLabels': sysLogPriorityLabels,
        'ldd_chart_values': ldd_chart_values, 'ldd_chart_labels': ldd_chart_labels,
        'ldd_user_dis_values': ldd_user_dis_values, 'ldd_user_dis_labels': ldd_user_dis_labels,
        'ldd_log_list': ldd_log_list, 'licenseList': licenseList,
    }
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'sysconf.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def ai_sensitivity(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    _algorithms = AIParameters.objects.all()
    _algorithm_ids = [_.id for _ in _algorithms]
    if request.method == 'POST':
        logger.debug(f"POST REQUEST DETAILS : {request.POST}")
        _changed = 0
        for _ in _algorithms:
            logger.debug(f"POST REQUEST DETAILS : {request.POST.get(str(_.id))}")
            _new_val = int(request.POST.get(str(_.id)))
            if _new_val != 0 and _.val != _new_val:
                logger.info(f"Sensitivity changed for {_.algorithmname} : From {_.val} to {_new_val}")
                _.val = _new_val
                _.pastsettings = [_new_val] if not _.pastsettings else _.pastsettings + [_new_val]
                try:
                    _.save()
                    _changed += 1
                    template_message_show(request, "success", f"Changes saved successfully for {_.algorithmname}")
                except Exception as err:
                    template_message_show(request, "error", f"Failed to save for {_.algorithmname}, because {err}")

        if _changed == 0:
            template_message_show(request, "info", "No changes to save.")
        else:
            template_message_show(request, "info", f"Total {_changed} changes saved.")

    context = {
        'algorithms': _algorithms,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except Exception as err:
        logger.warning(f"An error occurred in memory tracer system. ERROR IS : {err}")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'ai_sensitivity.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def mailing_settings(request, id=0):
    """
    URL : /system_configurations/mailing_settings/
    mailing settings and forms.
    two postgresql table will be used in here mailsettings, maildetails.
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    #
    if id == 0:
        route = "add"
        _mail_settings_form = MailSettingsForm(request.POST or None)
        # if request.method == "POST":
        #     if _mail_settings_form.is_valid():
        #         _mail_settings_form.save()
    else:
        route = "edit"
        _mailSetting = MailSettings.objects.get(id=id)
        _mail_settings_form = MailSettingsForm(request.POST or None, instance=_mailSetting)
        # if request.method == "POST":
        #     if _mail_settings_form.is_valid():
        #         _mail_settings_form.save()

    if request.method == "POST":
        if _mail_settings_form.is_valid():
            try:
                _mail_settings_form.save()
                template_message_show(request, "success", f"Saved successfully")
            except Exception as err:
                logger.exception(f"An error occurred trying to save mail settings. ERROR IS : {err}")
                template_message_show(request, "error", f"Failed to save. ERROR : {err}")

    #
    context = {
        'route': route, 'form': _mail_settings_form,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except Exception as err:
        logger.warning(f"An error occurred in memory tracer system. ERROR IS : {err}")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'mailing_forms.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def mailing_details(request, id=0):
    """
    URL : /system_configurations/mailing_settings/
    mailing settings and forms.
    two postgresql table will be used in here mailsettings, maildetails.
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    #
    # ...
    _listOfSettings = list(MailSettings.objects.values_list('id', 'touser'))
    logger.debug(f"List of Settings -> {_listOfSettings}")
    # ...
    if id == 0:
        route = "add"
        _mail_details_form = MailDetailsForm(request.POST or None)
        # if request.method == "POST":
        #     if _mail_details_form.is_valid():
        #         _mail_details_form.save()

    else:
        route = "edit"
        _mailDetails = MailDetails.objects.get(id=id)
        _mail_details_form = MailDetailsForm(request.POST or None, instance=_mailDetails)
        # if request.method == "POST":
        #     if _mail_details_form.is_valid():
        #         _mail_details_form.save()

    if request.method == "POST":
        if _mail_details_form.is_valid():
            try:
                _mail_details_form.save()
                template_message_show(request, "success", f"Saved successfully")
            except Exception as err:
                logger.exception(f"An error occurred trying to save mail details. ERROR IS : {err}")
                template_message_show(request, "error", f"Failed to save. ERROR : {err}")


    #
    context = {
        'route': route, 'form': _mail_details_form,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except Exception as err:
        logger.warning(f"An error occurred in memory tracer system. ERROR IS : {err}")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'mailing_forms.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def general_monitor(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    if request.POST:
        _a_id = request.POST.get('change_status')
        try:
            _anomaly = Anomalies.objects.get(id=int(_a_id))
            if _anomaly.status == '000':
                _anomaly.status = '001'
            elif _anomaly.status == '001':
                _anomaly.status = '000'
            _anomaly.save()
            template_message_show(request, 'success', 'Status changed successfully')
        except Exception as err:
            logger.exception(f"An error occurred trying to change anomaly status : {err}")

    _caption = ""
    _default_limit = 250
    _count_by_page = 20
    if len(request.GET) > 0:
        _aList = []
        limit_q = request.GET.get("limit_q")
        anomaly_q = request.GET.get("anomaly_q")
        device_q = request.GET.get("device_q")
        location_q = request.GET.get("location_q")
        ip_q = request.GET.get("ip_q")
        uniqueid_q = request.GET.get("uniqueid_q")
        start_q = request.GET.get("start_q")
        end_q = request.GET.get("end_q")
        count_q = request.GET.get("count_q")
        code_q = request.GET.get("code_q")
        status_q = request.GET.get("status_q")

        if start_q or end_q:
            if start_q:
                _aList += list(
                    Anomalies.objects.filter(Q(logdatestart__icontains=start_q)).exclude(analyzedstatus=9).distinct())
            if end_q:
                _aList += list(
                    Anomalies.objects.filter(Q(logdateend__icontains=end_q)).exclude(analyzedstatus=9).distinct())
            _aList = set(_aList)
        else:
            _aList = set(list(Anomalies.objects.exclude(analyzedstatus=9)))

        if anomaly_q:
            _related_types = GeneralParameterDetail.objects.values_list(
                "kod", flat=True).filter(kisakod="ANMLTYPE").filter(Q(kisaack__icontains=anomaly_q))
            _related_types = list(map(int, _related_types))
            _aList = _aList.intersection(
                list(Anomalies.objects.filter(anomalytype__in=_related_types).exclude(analyzedstatus=9).distinct()))

        if device_q:  # search on device type -- not yet for anomaly types 1201 and 1301
            _models_id_list = DeviceModel.objects.values_list("id", flat=True).filter(Q(devicetype__icontains=device_q))

            _devices_uniqueid_list = list(
                LogSources.objects.values_list("uniqueid", flat=True).filter(modelid__in=_models_id_list))
            _devices_uniqueid_list += list(
                LogDeviceGroup.objects.values_list("id", flat=True).filter(uniqueid__in=_devices_uniqueid_list))
            _devices_uniqueid_list += list(
                LogDeviceParameters.objects.values_list("id", flat=True).filter(uniqueid__in=_devices_uniqueid_list))

            _dev_alist = list(Anomalies.objects.filter(uniqueid__in=_devices_uniqueid_list).exclude(analyzedstatus=9))
            _aList = _aList.intersection(_dev_alist)

        if location_q:  # couldn't test because table is empty
            _locations_id_list = list(
                DevLocations.objects.values_list("id", flat=True).filter(Q(locationname__icontains=location_q)))
            _dev_profile_group_id_list = list(
                DeviceProfileGroups.objects.values_list("id", flat=True).filter(location_id__in=_locations_id_list))
            _dev_uniqueid_list = list(
                LogSources.objects.values_list(
                    "uniqueid", flat=True).filter(locationprofile__in=_dev_profile_group_id_list))
            _dev_uniqueid_list += list(
                LogDeviceGroup.objects.values_list("id", flat=True).filter(uniqueid__in=_dev_uniqueid_list))
            _dev_uniqueid_list += list(
                LogDeviceParameters.objects.values_list("id", flat=True).filter(uniqueid__in=_dev_uniqueid_list))

            _loc_alist = list(Anomalies.objects.filter(uniqueid__in=_dev_uniqueid_list).exclude(analyzedstatus=9))
            _aList = _aList.intersection(_loc_alist)

        if ip_q:
            _aList = _aList.intersection(
                list(Anomalies.objects.filter(
                    Q(deviceip__icontains=ip_q) | Q(uniqueid__icontains=ip_q)).exclude(analyzedstatus=9).distinct()))

        if uniqueid_q:
            _aList = _aList.intersection(list(Anomalies.objects.filter(Q(lsuniqueid__icontains=uniqueid_q)).exclude(
                analyzedstatus=9)))

        if count_q and count_q != "":
            _aList = _aList.intersection(
                list(Anomalies.objects.filter(anomalycount__gte=int(count_q)).exclude(analyzedstatus=9)))
        if code_q:
            _aList = _aList.intersection(
                list(Anomalies.objects.filter(
                    Q(logcode__icontains=code_q) | Q(logevent__icontains=code_q)).exclude(analyzedstatus=9).distinct()))
        if status_q:
            if "Closed".lower().find(status_q.lower()) >= 0 or "Kapalı".lower().find(status_q.lower()) >= 0:
                _aList = _aList.intersection(
                    list(Anomalies.objects.filter(status="001").exclude(analyzedstatus=9).distinct()))
            elif "Open".lower().find(status_q.lower()) >= 0 or "Açık".lower().find(status_q.lower()) >= 0:
                _aList = _aList.intersection(
                    list(Anomalies.objects.filter(status="000").exclude(analyzedstatus=9).distinct()))

        if ((not limit_q) and (not anomaly_q) and (not device_q) and (not location_q) and (not ip_q) and (
                not start_q) and (not end_q) and (not count_q) and (not code_q) and (not status_q) and (
                not uniqueid_q)) and request.GET.get("page") != "":
            _aList = list(Anomalies.objects.exclude(analyzedstatus=9))

        if ((not anomaly_q) and (not device_q) and (not location_q) and (not ip_q) and (not start_q) and (
                not end_q) and (not count_q) and (not code_q) and (not status_q) and (not uniqueid_q)) and (
                limit_q is not None and limit_q != ""):
            _aList = list(Anomalies.objects.exclude(analyzedstatus=9)[:int(limit_q)])

        _anomaliesList = sorted(list(set(_aList)), key=lambda _a: _a.id, reverse=True)

        if limit_q:
            _anomaliesList = _anomaliesList[:int(limit_q)]

        paginator = Paginator(_anomaliesList, _count_by_page)
        page = request.GET.get('page')
        try:
            _anomaliesList = paginator.page(page)
            if len(_anomaliesList) < _count_by_page:
                _caption = f"{(int(page) - 1) * _count_by_page + len(_anomaliesList)} of last {len(list(set(_aList)))} records "
            else:
                _caption = f"{int(page) * _count_by_page} of last {len(list(set(_aList)))} records "
        except PageNotAnInteger:
            _anomaliesList = paginator.page(1)
            if len(_anomaliesList) < _count_by_page:
                _caption = f"{len(_anomaliesList)} of last {len(list(set(_aList)))} records"
            else:
                _caption = f"{_count_by_page} of last {len(list(set(_aList)))} records"
        except EmptyPage:
            _anomaliesList = paginator.page(paginator.num_pages)
            _caption = f"{len(list(set(_aList)))} of the last {len(list(set(_aList)))} records "
        template_message_show(request, 'success', f'Successfully got {_caption}')
    else:
        _anomaliesList = list(Anomalies.objects.exclude(analyzedstatus=9))
        _total_anomalies = len(_anomaliesList)
        paginator = Paginator(_anomaliesList, _count_by_page)
        page = request.GET.get('page')
        try:
            _anomaliesList = paginator.page(page)
            if len(_anomaliesList) < _count_by_page:
                _caption = f"{(int(page)-1) * _count_by_page + len(_anomaliesList)} of last {_total_anomalies} records"
            else:
                _caption = f"{int(page) * _count_by_page} of last {_total_anomalies} records "
        except PageNotAnInteger:
            _anomaliesList = paginator.page(1)
            if len(_anomaliesList) < _count_by_page:
                _caption = f"{len(_anomaliesList)} of last {_total_anomalies} records "
            else:
                _caption = f"{_count_by_page} of last {_total_anomalies} records "
        except EmptyPage:
            _anomaliesList = paginator.page(paginator.num_pages)
            _caption = f"{_total_anomalies} of the last {_total_anomalies} records "
        template_message_show(request, 'success', f'Successfully got {_caption}')

    context = {
        'route': 'general', 'anomaliesList': _anomaliesList, 'caption': _caption,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/monitor.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
def anomalies_detail_monitor(request, id):
    """
    to see alert details from the monitoring page;
    """
    # feedback operations starts with Ajax request and end with its own return, we don't need to continue to view ------
    if request.is_ajax():
        #  start operation;
        # logger.debug(f"request : {request.POST}")
        """
        'action': ['sendSingleFeedBack'],
        'aldID': ['20919'],
        'feedbackValue': ['True']
        """
        _id_of_ald = request.POST.get("aldID")
        _value_of_feedback = True if request.POST.get("feedbackValue") == "True" else False
        logger.info(f"Now {_value_of_feedback} is given for anomalylogdetails with id {_id_of_ald}")
        try:
            if _value_of_feedback:
                AnomalyLogsDetails.objects.filter(
                    id=_id_of_ald).update(userfeedback=_value_of_feedback, aistatus=1,
                                          userscorefeedback=F("aioutputscore")*1.1)
            else:
                AnomalyLogsDetails.objects.filter(
                    id=_id_of_ald).update(userfeedback=_value_of_feedback, aistatus=2,
                                          userscorefeedback=F("aioutputscore")*0.95)
            return JsonResponse(
                {"command": 0, "result": f"{_value_of_feedback} value given for {_id_of_ald} successfully."},
                status=200)
        except Exception as err:
            logger.exception(
                f"An error occurred trying to give {_value_of_feedback} feedback to {_id_of_ald}.ERROR IS : {err}")
            return JsonResponse({'command': 1, 'result': f"{err}"}, status=200)

    # Normal view operations are lying below ---------------------------------------------------------------------------
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    try:
        _anomaly = Anomalies.objects.get(id=id)
    except ObjectDoesNotExist:
        return redirect('AgentRoot:not_found_view')
    dataWarning = None
    lastFiveMinWarning = None
    kde_exception = ""
    graph_data = []
    _labels = []
    _logids = []
    elasticLogs = []
    _body = None

    if _anomaly.anomalytype in [1, 2]:
        if _anomaly.anomalytype == 1:
            # for new behaviours
            _logids = [_anomaly.logid]
        elif _anomaly.anomalytype == 2:
            # for critical alerts
            _logids = _anomaly.logids

        if check_environment_for_elastic():
            try:
                elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                                   sniff_on_start=True, request_timeout=2)
                _body = '{"size": 20, "query": {"terms" : {"id" : %s}}, "sort":[{"id":{"order":"desc"}}]}' % _logids
                logger.debug(f"{_body}")
                _body = json.loads(f"{_body}")
                search = elastic_connection.search(index="atibalogs", body=_body)
                elasticLogs = [LogFromElastic(dictionary=hit["_source"]) for hit in search["hits"]["hits"]]
            except Exception as err:
                logger.exception(
                    f"An error occurred trying to get logs from elastic with query {_body}. ERROR IS : {err}")
        else:
            logger.warning("No Elasticsearch connection !")

    elif _anomaly.anomalytype in [3, 1201, 1301, 1401]:
        graph_data = _anomaly.get_anomaly_detail_data()
        _labels, _line_up, _line_middle, _line_down = [], [], [], []
        for t, x, y, z in graph_data:
            # _str_date = f"{t.year}-{t.month}-{t.day}-{t.hour}:{t.minute}:{t.second}"
            _str_date = t.strftime("%d-%b-%H:%M")
            _labels.append(_str_date)
            _line_up.append(float(z))
            _line_middle.append(float(y))
            _line_down.append(float(x))

        graph_data = [_line_up, _line_middle, _line_down]  # list of data lists to draw graph

    elif _anomaly.anomalytype in [1203, 1204, 1303, 1304]:
        graph_data = _anomaly.get_anomaly_detail_data()
        dataWarning = "possible data corruption detected" if not graph_data else None
        logger.debug(f"TO DRAW CHART - > _anomaly.get_anomaly_detail_data RETURNED FOR ID {id} : {graph_data}")
        _labels, _line_count, _line_gaussian = [], [], []
        for t, x, y in graph_data:
            # _str_date = f"{t.year}-{t.month}-{t.day}-{t.hour}:{t.minute}:{t.second}"
            _str_date = t.strftime("%d-%b-%H:%M")
            _labels.append(_str_date)
            _line_count.append(float(x))
        max_of_counts = max(_line_count) if _line_count else 5
        _axises = np.linspace(0, max_of_counts, (math.ceil(len(_line_count)*1.1)+1))
        axes_x = [round(float(num), 3) for num in list(_axises)]

        _kde = _anomaly.get_anomaly_kde()
        logger.debug(f"KDE FOR ID {id} : {_kde}")
        if _kde:
            if type(_kde) is gaussian_kde:
                axes_y = [float(round(float(num), 3)) for num in list(_kde([_axises]))]
                pass
            elif type(_kde) is str:
                axes_y = []
                logger.error(f"Possibly KDE empty or interval data doesn't exist : / {_kde} / in type of {type(_kde)}")
                kde_exception = f"{_kde}"
            else:
                # _gs_kde = gaussian_kde(_line_count, bw_method=0.15)
                # axes_y = [float(round(float(num), 3)) for num in list(_gs_kde([_axises]))]
                axes_y = []
                logger.error(f"KDE Function Type Error : / {_kde} / in type of {type(_kde)}")
                kde_exception = "Possibly Distribution Function Not Determined"
        else:
            # _gs_kde = gaussian_kde(_line_count, bw_method=0.15)
            # axes_y = [float(round(float(num), 3)) for num in list(_gs_kde([_axises]))]
            axes_y = []
            logger.warning(f"Couldn't Get KDE Function and we got : / {_kde} / in type of {type(_kde)}")
            kde_exception = "KDE Function not determined"

        _line_gaussian = [axes_x, axes_y]
        graph_data = [_line_count, axes_x, axes_y]  # list of data lists to draw graph

    # if duration between logdatestart and logdateend more than 5 minutes somehow than we need to ad a warning for it
    intervalWarning = None
    lastFiveMinStart = None  # it will use for critical alerts that has wider interval
    _start_end_date_difference = (_anomaly.logdateend - _anomaly.logdatestart).total_seconds()
    if _start_end_date_difference > 5*60:
        lastFiveMinStart = (_anomaly.logdateend - datetime.timedelta(minutes=5))
        intervalWarning = f"Time interval wider then usual. ({round((_start_end_date_difference/60)*100)/100} minutes)"

    logdatestart_string = datetime.datetime.strftime(_anomaly.logdatestart, '%Y-%m-%d %H:%M:%S.%f')[:-3]
    logdateend_string = datetime.datetime.strftime(_anomaly.logdateend, '%Y-%m-%d %H:%M:%S.%f')[:-3]
    elasticLogsInInterval = []
    # anomaly_logs = []
    anomaly_logs_details = []
    rc_graphs = []
    rc_graph_paths = []

    # _body = '{"size": 5000, "query": {"bool": {"must": [{"range": {"credate": {"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}}, {"bool": {"must": [{"term": {"uniqueid": {"value": "%s", "boost": 1.0}}},{"exists": {"field": "%s"}}], "adjust_pure_negative": true, "boost": 1.0}}], "adjust_pure_negative": true, "boost": 1.0}}}'  % (logdatestart_string, logdateend_string, _anomaly.get_device().uniqueid, _anomaly.logcode)
    # _body = json.loads(_body)
    # logger.debug(f"Logs About Alert query body for id {_anomaly.id} type {_anomaly.anomalytype} --> {_body}")

    # get logs from elasticsearch index atibalogs in 5 seconds time interval with this logcode
    if check_environment_for_elastic():
        try:
            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number, sniff_on_start=True,
                                               request_timeout=2)
            if _anomaly.anomalytype in [1301, 1302, 1303, 1304, 1401]:
                # _body = '{"size":5000,"query":{"bool":{"must":[{"range":{"credate":{"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}}, {"bool": {"must": [{"term": {"uniqueid": {"value": "%s", "boost": 1.0}}},{"exists": {"field": "parameters.%s"}}], "adjust_pure_negative": true, "boost": 1.0}}], "adjust_pure_negative": true, "boost": 1.0}}}'  % (logdatestart_string, logdateend_string, _anomaly.get_device().uniqueid, _anomaly.logcode)
                _body = '{"size":5000,"query":{"bool":{"must":[{"range":{"credate":{"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "uuuu-MM-dd HH:mm:ss.SSSSSSZ||uuuu-MM-dd HH:mm:ss.SSSSSS||uuuu-MM-dd HH:mm:ss.SSSZ||uuuu-MM-dd HH:mm:ss.SSS||uuuu-MM-dd HH:mm:ss||uuuu-MM-dd||epoch_millis", "boost": 1.0}}}, {"bool": {"must": [{"term": {"uniqueid": {"value": "%s", "boost": 1.0}}},{"exists": {"field": "parameters.%s"}}], "adjust_pure_negative": true, "boost": 1.0}}], "adjust_pure_negative": true, "boost": 1.0}}}'  % (logdatestart_string, logdateend_string, _anomaly.get_device().uniqueid, _anomaly.logcode)
            else:
                # _body = '{"size":5000,"query":{"bool":{"must":[{"range":{"credate":{"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}},{"bool":{"must":[{"term": {"logndx": {"value": "%s", "boost": 1.0}}}], "adjust_pure_negative": true, "boost": 1.0}}], "adjust_pure_negative": true, "boost": 1.0}}}' % (logdatestart_string, logdateend_string, _anomaly.logcode)
                _body = '{"size":5000,"query":{"bool":{"must":[{"range":{"credate":{"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "uuuu-MM-dd HH:mm:ss.SSSSSSZ||uuuu-MM-dd HH:mm:ss.SSSSSS||uuuu-MM-dd HH:mm:ss.SSSZ||uuuu-MM-dd HH:mm:ss.SSS||uuuu-MM-dd HH:mm:ss||uuuu-MM-dd||epoch_millis", "boost": 1.0}}},{"bool":{"must":[{"term": {"logndx": {"value": "%s", "boost": 1.0}}}], "adjust_pure_negative": true, "boost": 1.0}}], "adjust_pure_negative": true, "boost": 1.0}}}' % (logdatestart_string, logdateend_string, _anomaly.logcode)
            _body = json.loads(_body)
            logger.info(f"Logs About Alert query body for id {_anomaly.id} type {_anomaly.anomalytype} --> {_body}")
            search = elastic_connection.search(index="atibalogs", body=_body)
            elasticLogsInInterval = [LogFromElastic(dictionary=hit["_source"]) for hit in search["hits"]["hits"]]
        except Exception as err:
            logger.exception(f"An error occurred trying to get logs from elastic with query {_body}. ERROR IS : {err}")
            template_message_show(request, "error", f"Logs couldn't get from elastic. Because {err}")
    else:
        logger.warning("No Elasticsearch connection !")
        template_message_show(request, "warning", f"No elastic connection on this environment")
        elasticLogsInInterval = [LogFromElastic(dictionary=x['_source']) for x in hitsListForTest]

    anomaly_logs = _anomaly.get_anomaly_logs()

    if anomaly_logs:
        anomaly_logs_ids = [_.id for _ in anomaly_logs]
        # get anomalylogsdetails for anomalylogs if in alogid or subalogid
        try:
            anomaly_logs_details = [list(AnomalyLogsDetails.objects.filter(
                anomalyLog_id__in=anomaly_logs_ids).order_by('-aioutputscore')),
                                    list(AnomalyLogsDetails.objects.filter(
                                        subAnomalyLog_id__in=anomaly_logs_ids).order_by('-aioutputscore'))]
            if not anomaly_logs_details[0] and not anomaly_logs_details[1]:
                anomaly_logs_details = []
            logger.info(f"list from anomalylogsdetails for {anomaly_logs_ids} -> {anomaly_logs_details}")
        except Exception as err:
            logger.exception(
                f"While getting anomalylogsdetails for anomalylogs with ids {anomaly_logs_ids}. ERROR IS : {err}")
            template_message_show(request, "error", f"AnomalyLogsDetails couldn't get. Because {err}")

        # get rcgraphsdetails for anomalylogs if its in nodelist
        _anomaly_log_last_five_minute = []
        for _ in anomaly_logs:
            # for critical alerts check if anomaly log exists in last 5 min interval
            if lastFiveMinStart:
                if lastFiveMinStart <= _.credate <= _anomaly.logdateend:
                    _anomaly_log_last_five_minute.append(_)
            rc_graphs += _.get_rc_graphs()
            for rc in _.get_rc_graphs():
                for rcItem in rc.get_paths():
                    for k, v in rcItem.items():
                        logger.debug(f"rcItem -> {k} : {v} {type(v)}")
                        if isinstance(v, list):
                            if _.id in v:
                                _path = [AnomalyLogs.objects.get(id=int(i)) for i in v]
                                rc_graph_paths.append((_, rc, _path))
                        else:
                            logger.debug(f"v is not list {type(v)}")
        logger.debug(f"rc_graph_paths list is : {rc_graph_paths}")

        # for critical alerts check if any causal relation for anomaly logs in last five minutes
        _anomaly_logs_details_last_five_minute = []
        if lastFiveMinStart:
            try:
                _anomaly_logs_details_last_five_minute = [
                    list(AnomalyLogsDetails.objects.filter(
                        anomalyLog_id__in=_anomaly_log_last_five_minute).order_by('-aioutputscore')),
                    list(AnomalyLogsDetails.objects.filter(
                        subAnomalyLog_id__in=_anomaly_log_last_five_minute).order_by('-aioutputscore'))
                ]
                if not _anomaly_logs_details_last_five_minute[0] and not _anomaly_logs_details_last_five_minute[1]:
                    _anomaly_logs_details_last_five_minute = []
                logger.info(
                    f"list from anomalylogsdetails for last 5 minutes -> {_anomaly_logs_details_last_five_minute}")
            except Exception as err:
                logger.exception(
                    f"While getting anomalylogsdetails for last 5 minutes. ERROR IS : {err}")
        if lastFiveMinStart and not _anomaly_logs_details_last_five_minute:
            lastFiveMinWarning = f"There is no causal relation for current alert which is generated in interval [{lastFiveMinStart.strftime('%y-%m-%d %H:%M:%S')} , {(_anomaly.logdateend).strftime('%y-%m-%d %H:%M:%S')}]. Older relations are below in descending order of AI Score"

    _list_of_interval = []
    _alarms = []
    if _anomaly.anomalytype in [1201, 1202, 1203, 1204]:
        _list_of_interval = list(LogInterval.objects.filter(logdevicegroupid=_anomaly.uniqueid,
                                                            timestart__lt=_anomaly.logdateend).order_by("-id")[:10])
        logger.debug(f"INTERVAL COUNT : {len(_list_of_interval)}")
        _alarms = list(Anomalies.objects.filter(logdateend=_anomaly.logdateend,
                                                anomalytype__in=[1201, 1202, 1203, 1204]).exclude(id=_anomaly.id))
        logger.debug(f"DIFFERENT ANOMALIES COUNT : {len(_alarms)}")
    elif _anomaly.anomalytype in [1301, 1302, 1303, 1304, 1401]:
        _list_of_interval = list(ParameterInterval.objects.filter(
            parameterdevicegroupid=_anomaly.uniqueid, timestart__lt=_anomaly.logdateend).order_by("-id")[:10])
        logger.debug(f"INTERVAL COUNT : {len(_list_of_interval)}")
        _alarms = list(Anomalies.objects.filter(logdateend=_anomaly.logdateend,
                                                anomalytype__in=[1301, 1302, 1303, 1304, 1401]).exclude(id=_anomaly.id))
        logger.debug(f"DIFFERENT ANOMALIES COUNT : {len(_alarms)}")
    elif _anomaly.anomalytype in [1101, 1, 2, 3]:
        _alarms = list(Anomalies.objects.filter(logdateend=_anomaly.logdateend,
                                                anomalytype=_anomaly.anomalytype).exclude(id=_anomaly.id))
        logger.debug(f"DIFFERENT ANOMALIES COUNT : {len(_alarms)}")
    # logger.debug(f"SPARSITY DATA : {_anomaly.get_sparsity_data()}")
    # if _anomaly.anomalytype in [1201, 1202, 1203, 1204]:
    #     _beh_type = ""
    #     _list_of_counts = list(LogInterval.objects.values_list('logcount', flat=True).filter(logdevicegroupid=_anomaly.uniqueid, timestart__lt=(_anomaly.logdateend + datetime.timedelta(seconds=0.5))).order_by('timeepoch')[:1024])
    #     _list_of_labels = list(LogInterval.objects.values_list('timestart', flat=True).filter(logdevicegroupid=_anomaly.uniqueid, timestart__lt=(_anomaly.logdateend + datetime.timedelta(seconds=0.5))).order_by('timeepoch')[:1024])
    #     _list_mode = mode(_list_of_counts)
    #     _mode_count = _list_of_counts.count(_list_mode)
    #     logger.debug(f"MODE OF COUNT LIST : {_list_mode}")
    #     logger.debug(f"COUNT OF MODE : {_mode_count}")
    #     logger.debug(f"PERCENTAGE OF MODE : {_mode_count*100/len(_list_of_counts)}")
    #     logger.debug(f"SPARSITY DATA : {len(_list_of_counts)}")
    #     # logger.debug(f"SPARSITY DATA : {[_list_of_labels, _list_of_counts]}")

    # calling the anomalyScoreTest function in postgresql
    # _anomalyScore = None
    # if not _anomaly.anomalyscore or _anomaly.anomalyscore > 10:
    #     if _anomaly.anomalytype in [1201, 1301, 3]:
    #         _anomalyScore = serializers.serialize('json', AnomalyScoreDetection.objects.raw(
    #             'SELECT 1 as id, anomalyscoredetection FROM anomalyscoredetection(%s,%s,%s,%s)',
    #             [_anomaly.lowerbound, _anomaly.prediction, _anomaly.upperbound, _anomaly.anomalycount]), fields=(
    #             'id', 'anomalyscoredetection'))
    #         _anomalyScore = float(json.loads(_anomalyScore)[0]['fields']['anomalyscoredetection'])
    #         logger.debug(f"ANOMALY SCORE : {_anomalyScore}")
    #     # elif _anomaly.anomalytype in [1203, 1303]:
    #     #     _anomalyScore = serializers.serialize('json', AnomalyScoreDetection.objects.raw(
    #     #         'SELECT 1 as id, anomalyscoredetection FROM anomalyscoredetection(%s,%s,%s)',
    #     #         [_anomaly.prediction, _anomaly.excessmedian, _anomaly.anomalycount]), fields=(
    #     #         'id', 'anomalyscoredetection'))
    #     #     _anomalyScore = float(json.loads(_anomalyScore)[0]['fields']['anomalyscoredetection'])
    #     #     logger.debug(f"ANOMALY SCORE : {_anomalyScore}")
    #     # elif _anomaly.anomalytype in [1204, 1304]:
    #     #     _anomalyScore = serializers.serialize('json', AnomalyScoreDetection.objects.raw(
    #     #         'SELECT 1 as id, anomalyscoredetection FROM anomalyscoredetection(%s,%s,%s)',
    #     #         [_anomaly.prediction, _anomaly.fqmedian, _anomaly.anomalycount]), fields=(
    #     #         'id', 'anomalyscoredetection'))
    #     #     _anomalyScore = float(json.loads(_anomalyScore)[0]['fields']['anomalyscoredetection'])
    #     #     logger.debug(f"ANOMALY SCORE : {_anomalyScore}")
    #     else:
    #         _anomalyScore = f"No score evaluated. IN DB {_anomaly.anomalyscore}"
    # else:
    #     _anomalyScore = _anomaly.anomalyscore
    #     logger.debug(f"ANOMALY SCORE FROM DB : {_anomalyScore}")

    # to draw small count line graphs
    # try:
    #     simple_chart = _anomaly.get_simple_chart_data()
    #     logger.debug(f"SIMPLE CHART DATA : {simple_chart}")
    # except Exception as err:
    #     logger.exception(f"ERROR IS : {err}")

    # paginating elasticLogsInInterval list
    paginator = Paginator(elasticLogsInInterval, record_per_page)
    page = request.GET.get('l_page')
    try:
        elasticLogsInInterval = paginator.page(page)
    except PageNotAnInteger:
        elasticLogsInInterval = paginator.page(1)
    except EmptyPage:
        elasticLogsInInterval = paginator.page(paginator.num_pages)

    sample_labels = ["5min" for _ in range(14)]

    context = {
        'route': 'general', 'type': _anomaly.get_type_definition(), 'graph_data': list(graph_data), 'anomaly': _anomaly,
        'label_list': _labels, 'kde_exception': kde_exception, 'elasticLogs': elasticLogs,
        'intervalWarning': intervalWarning, 'anomaly_logs': anomaly_logs, 'rc_graphs': rc_graphs,
        'rc_graph_paths': rc_graph_paths,
        'anomaly_logs_details': anomaly_logs_details, 'elasticLogsInInterval': elasticLogsInInterval,
        'sample_labels': sample_labels, 'list_of_interval': _list_of_interval, 'alarms': _alarms,
        'dataWarning': dataWarning, 'lastFiveMinWarning': lastFiveMinWarning,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/anomaly.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def log_monitoring(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    global globalElasticLogList, globalAggregation
    logSource, logCode, parameters, parameterValues = None, None, None, None
    route = "general"

    _today = datetime.datetime.now()
    _today_string = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
    _today_html = datetime.datetime.strftime(timezone.now(), '%Y-%m-%dT%H:%M')
    _yesterday = datetime.datetime.now() - datetime.timedelta(hours=24)
    _yesterday_string = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(hours=24),
                                                   '%Y-%m-%d %H:%M:%S')
    _yesterday_html = datetime.datetime.strftime(datetime.datetime.now()-datetime.timedelta(hours=24), '%Y-%m-%dT%H:%M')

    if request.method == "POST":
        # logger.debug(f"{request.POST}")
        """
        'startDate': ['2021-02-01T20:15'], 
        'endDate': ['2021-02-04T20:15'], 
        'logSource': ['186472c82788'], 
        'logCode': ['<341005>'], 
        'parameters': ['hostname'], 
        'parameterValues': ['localhost']
        """
        if request.is_ajax():
            """
            'startDate': ['2021-02-01T20:15'], 
            'endDate': ['2021-02-04T20:15'], 
            'logSource': ['186472c82788'], 
            'logCode': ['<341005>'], 
            'parameters': ['hostname'], 
            'parameterValues': ['localhost']
            """
            startDate = datetime.datetime.strptime(request.POST.get('startDate'), '%Y-%m-%dT%H:%M') if check_existence(
                request.POST.get('startDate')) else None
            startDateString = date_picker_string(request.POST.get('startDate')) if check_existence(
                request.POST.get('startDate')) else None  # to use in elasticsearch query
            endDate = datetime.datetime.strptime(request.POST.get('endDate'), '%Y-%m-%dT%H:%M') if check_existence(
                request.POST.get('startDate')) else None
            endDateString = date_picker_string(request.POST.get('endDate')) if check_existence(
                request.POST.get('endDate')) else None  # to use in elasticsearch query

            logSource = request.POST.get('logSource') if check_existence(request.POST.get('logSource')) else None
            logCode = request.POST.get('logCode') if check_existence(request.POST.get('logCode')) else None
            parameters = request.POST.get('parameters') if check_existence(request.POST.get('parameters')) else None
            parameterValues = request.POST.get('parameterValues') if check_existence(
                request.POST.get('parameterValues')) else None
            logger.debug(f"Variables from Ajax are : {startDateString}, {endDateString}, {logSource}, {logCode}, {parameters}, {parameterValues}")
            """
            return JsonResponse({'command': 1, 'testResult': parseTestObj.get_json(), 'rtext': rtext}, status=200)
                except Exception as err:
                    logger.error(f"An error occurred in add_parser_profile view trying to excecute logparsetest in db. ERROR IS : {err}")
                    return JsonResponse({'command': 0, 'warning': 'Failed, check field values'}, status=200)
            """
            if check_environment_for_elastic():
                uniqueIdList, logCodeList, parametersList = [], [], []
                parameterValuesList, parameterKeyValueTupples = [], []
                elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                                   sniff_on_start=True, request_timeout=2)
                elastic_log_list = []
                if startDate:
                    _body = '{"size":0,"query":{"bool":{"must":[{"range": {"credate": {"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"id":{"order":"desc"}}],"aggregations":{"byEvent":{"terms":{"field":"uniqueid","size":100,"min_doc_count":1,"show_term_doc_count_error":false,"order":[{"_count":"desc"},{"_key":"asc"}]}}}}' % (startDateString, endDateString)
                    _body = json.loads(_body)
                    search = elastic_connection.search(index="atibalogs", body=_body)
                    _buckets = search["aggregations"]["byEvent"]["buckets"]
                    # logger.debug(f"in if startDate :  {_buckets}")
                    uniqueIdList = [_["key"] for _ in _buckets]

                if logSource:
                    _body = '{"size":0,"query":{"bool":{"must":[{"range": {"credate": {"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}},{"match":{"uniqueid":{"query":"%s","boost":1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"id":{"order":"desc"}}],"aggregations":{"byEvent":{"terms":{"field":"logndx","size":100,"min_doc_count":1,"show_term_doc_count_error":false,"order":[{"_count":"desc"},{"_key":"asc"}]}}}}' % (startDateString, endDateString, logSource)
                    _body = json.loads(_body)
                    search = elastic_connection.search(index="atibalogs", body=_body)
                    _buckets = search["aggregations"]["byEvent"]["buckets"]
                    # logger.debug(f"in if logSource :  {_buckets}")
                    logCodeList = [_["key"] for _ in _buckets]
                    logCodeList.sort()

                if logCode:
                    # parametersList = [_.parametername for _ in LogDeviceParameters.objects.all()]
                    parametersList = list(LogDeviceParameters.objects.values_list('parametername', flat=True))
                    # _body = '{"query":{"bool":{"must":[{"range": {"credate": {"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}},{"bool":{"must":[{"term": {"uniqueid": {"value": "%s", "boost": 1.0}}}, {"term": {"logndx": {"value": "%s", "boost": 1.0}}}], "adjust_pure_negative": true, "boost": 1.0}}], "adjust_pure_negative": true, "boost": 1.0}},"aggregations":{"byEvent":{"terms":{"field":"parameters.macaddress.keyword","size":100,"min_doc_count":1,"show_term_doc_count_error":false,"order":[{"_count":"desc"},{"_key":"asc"}]}}}}' % (startDateString, endDateString, logSource, logCode)
                    # _body = json.loads(_body)
                    # search = elastic_connection.search(index="atibalogs", body=_body)
                    # # _buckets = json.loads(search["hits"]["hits"])
                    # _buckets = search["hits"]["hits"]
                    # # logger.debug(f"in if logCode : {_buckets}")
                    # for hit in _buckets:
                    #     if hit["_source"]["parameters"]:
                    #         parameters_dict = json.loads(hit["_source"]["parameters"])
                    #         # for k, v in hit["_source"]["parameters"].items():
                    #         for k, v in parameters_dict.items():
                    #             parametersList.append(k)
                    #             parameterValuesList.append(v[0])
                    #             parameterKeyValueTupples.append((k, v))
                    #     else:
                    #         logger.warning("No parameters part in search response")
                if parameters:
                    _body = '{"query":{"bool":{"must":[{"range": {"credate": {"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}},{"bool":{"must":[{"term": {"uniqueid": {"value": "%s", "boost": 1.0}}}, {"term": {"logndx": {"value": "%s", "boost": 1.0}}}], "adjust_pure_negative": true, "boost": 1.0}}], "adjust_pure_negative": true, "boost": 1.0}},"aggregations":{"byEvent":{"terms":{"field":"parameters.%s.keyword","size":100,"min_doc_count":1,"show_term_doc_count_error":false,"order":[{"_count":"desc"},{"_key":"asc"}]}}}}' % (startDateString, endDateString, logSource, logCode, parameters)
                    _body = json.loads(_body)
                    search = elastic_connection.search(index="atibalogs", body=_body)
                    _buckets = search["aggregations"]["byEvent"]["buckets"]
                    if _buckets and len(_buckets) > 0:
                        parameterValuesList = [_["key"] for _ in _buckets]
                    # parameterValuesList = [y for x, y in parameterKeyValueTupples if x == parameters]
                # if parameterValues:
                #     pass
                logger.debug(f"uniqueIdList : {uniqueIdList}")
                logger.debug(f"logCodeList : {logCodeList}")
                logger.debug(f"parametersList : {parametersList}")
                logger.debug(f"parameterValuesList : {parameterValues}")
                # memory usage logging with memory_tracer
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return JsonResponse({'command': 1,
                                     'uniqueIdList': uniqueIdList,
                                     'logCodeList': logCodeList,
                                     'parametersList': parametersList,
                                     'parameterValuesList': list(set(parameterValuesList))
                                     }, status=200)
            else:
                elastic_log_list = [LogFromElastic(dictionary=x['_source']) for x in hitsListForTest]
                if startDate:
                    if endDate:
                        elastic_log_list = [_ for _ in elastic_log_list if startDate <= _.credate <= endDate]
                    else:
                        elastic_log_list = [_ for _ in elastic_log_list if startDate <= _.credate <= _today]

                if logSource:
                    elastic_log_list = [_ for _ in elastic_log_list if _.uniqueid == logSource]
                if logCode:
                    elastic_log_list = [_ for _ in elastic_log_list if _.logcode == logCode]
                if parameters:
                    pass
                if parameterValues:
                    pass
                # memory usage logging with memory_tracer
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return JsonResponse({'command': 1,
                                     'uniqueIdList': list(set([_.uniqueid for _ in elastic_log_list])),
                                     'logCodeList': list(set([_.logcode for _ in elastic_log_list])),
                                     'parametersList': ['hostname', 'username'],
                                     'parameterValuesList': ['localhost', 'istiklal']
                                     }, status=200)

        else:
            """
            'startDate': ['2021-02-01T20:15'], 
            'endDate': ['2021-02-04T20:15'], 
            'logSource': ['186472c82788'], 
            'logCode': ['<341005>'], 
            'parameters': ['hostname'], 
            'parameterValues': ['localhost']
            """
            startDate = datetime.datetime.strptime(request.POST.get('startDate'), '%Y-%m-%dT%H:%M') if check_existence(
                request.POST.get('startDate')) else None
            startDateString = date_picker_string(request.POST.get('startDate')) if check_existence(
                request.POST.get('startDate')) else None  # to use in elasticsearch query
            endDate = datetime.datetime.strptime(request.POST.get('endDate'), '%Y-%m-%dT%H:%M') if check_existence(
                request.POST.get('endDate')) else None
            endDateString = date_picker_string(request.POST.get('endDate')) if check_existence(
                request.POST.get('endDate')) else None  # to use in elasticsearch query

            logSource = request.POST.get('logSource') if check_existence(request.POST.get('logSource')) else None
            logCode = request.POST.get('logCode') if check_existence(request.POST.get('logCode')) else None
            parameters = request.POST.get('parameters') if check_existence(request.POST.get('parameters')) else None
            parameterValues = request.POST.get('parameterValues') if check_existence(
                request.POST.get('parameterValues')) else None

            if check_environment_for_elastic():
                elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                                   sniff_on_start=True, request_timeout=2)

                dateRangeQuery = '{"range": {"credate": {"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}}' % (
                    startDateString, endDateString)
                uniqueIdQuery = '{"term": {"uniqueid": {"value": "%s", "boost": 1.0}}}' % logSource if check_existence(logSource) else None
                logCodeQuery = '{"term": {"logndx": {"value": "%s", "boost": 1.0}}}' % logCode if check_existence(logCode) else None
                parametersQuery = '{"term": {"parameters.%s.keyword": {"value": "%s", "boost": 1.0}}}' % (parameters, parameterValues) if check_existence(parameters) and check_existence(parameterValues) else None
                listOfQueries = list(filter(None, [uniqueIdQuery, logCodeQuery, parametersQuery]))
                stringQuery = ""
                for i in range(len(listOfQueries)):
                    if i == 0:
                        stringQuery += listOfQueries[i]
                    stringQuery += ", " + listOfQueries[i]
                listOfQueries = "[" + stringQuery + "]"
                # _aggregation_sonuc = '"aggregations":{"sonuc":{"date_histogram":{"field":"credate","interval":"1h","offset":0,"order":{"_key":"asc"},"keyed":false,"min_doc_count":0,"extended_bounds" : { "min" : "2021-03-23 11:00:00","max":"2021-03-23 16:05:00"}}}'
                # _body = '{"size":5000, "query":{"bool":{"must":[{"range": {"credate": {"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"id":{"order":"desc"}}], %s}}' % (dateRangeQuery, listOfQueries, _aggregation_sonuc)
                _body = '{"size": 5000, "query":{"bool":{"must":[%s,{"bool":{"must":%s, "adjust_pure_negative": true, "boost": 1.0}}], "adjust_pure_negative": true, "boost": 1.0}},"aggregations":{"sonuc":{"date_histogram":{"field":"credate","interval":"1h","offset":0,"order":{"_key":"asc"},"keyed":false,"min_doc_count":0,"extended_bounds" : { "min" : "%s","max":"%s"}}}}}' % (dateRangeQuery, listOfQueries, startDateString, endDateString)
                # logger.debug(f"Query BODY : {_body}")
                # _body = '{"query":{"bool":{"must":[{"range": {"credate": {"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}},{"bool":{"must":[{"term": {"uniqueid": {"value": "%s", "boost": 1.0}}}, {"term": {"logndx": {"value": "%s", "boost": 1.0}}},{"term": {"parameters.%s.keyword": {"value": "%s", "boost": 1.0}}}], "adjust_pure_negative": true, "boost": 1.0}}], "adjust_pure_negative": true, "boost": 1.0}},"aggregations":{"sonuc":{"date_histogram":{"field":"credate","interval":"1h","offset":0,"order":{"_key":"asc"},"keyed":false,"min_doc_count":0,"extended_bounds" : { "min" : "2021-03-23 11:00:00","max":"2021-03-23 16:05:00"}}}}}}' % (startDateString, endDateString, logSource, logCode, parameters, parameterValues)
                _body = json.loads(_body)
                # logger.debug(f"Query JSON : {_body}")
                search = elastic_connection.search(index="atibalogs", body=_body)
                # response = search.execute()
                # elastic_log_list = [LogFromElastic(hit_object=hit) for hit in response.hits]
                elastic_log_list = [LogFromElastic(dictionary=hit["_source"]) for hit in search["hits"]["hits"]]

                # adding logCodeCount and LogCodeUniqueIds to LogFromElastic object with new aggregation query
                _aggregation_logCodeCounts_uniqueids = '"aggregations":{"logCodeCounts":{"terms":{"field":"logndx","size":100,"min_doc_count":1,"show_term_doc_count_error":false,"order":[{"_count":"desc"},{"_key":"asc"}]}, "aggregations":{"uniqueids":{"terms":{"field":"uniqueid", "size":100,"min_doc_count":1,"show_term_doc_count_error":false,"order":[{"_count":"desc"},{"_key":"asc"}]}}}}'
                _body2 = '{"size":0,"query": {"match_all": {}},"sort":[{"id":{"order":"desc"}}], %s}}' % _aggregation_logCodeCounts_uniqueids
                # logger.debug(f"body for logCodeCounts : {_body2}")
                _body2 = json.loads(_body2)
                search2 = elastic_connection.search(index="atibalogs", body=_body2)
                # logger.debug(f'aggregation result for logCodeCounts : {search2["aggregations"]["logCodeCounts"]["buckets"]}')
                for bucket in search2["aggregations"]["logCodeCounts"]["buckets"]:
                    _uniqueids = [_["key"] for _ in bucket["uniqueids"]["buckets"]]
                    _countsForUniquesids = [_["doc_count"] for _ in bucket["uniqueids"]["buckets"]]
                    _list = [_ for _ in elastic_log_list if _.logcode == bucket["key"]]
                    if len(_list) > 0:
                        for el in _list:
                            el.logCodeCount = bucket["doc_count"]
                            el.logCodeUniqueids = _uniqueids
                            el.logCodeUniqueidCounts = _countsForUniquesids
                        else:
                            continue
                globalElasticLogList = elastic_log_list
                # elastic_aggregation = AggregationElastic(aggregation_object=response.aggregations, aggregation_name="sonuc")
                elastic_aggregation = AggregationElastic(dictionary=search["aggregations"], aggregation_name="sonuc")
                globalAggregation = elastic_aggregation
                _yesterday_html = request.POST.get('startDate')
                _today_html = request.POST.get('endDate')
            else:
                elastic_log_list = [LogFromElastic(dictionary=x['_source']) for x in hitsListForTest]
                elastic_log_list = [_ for _ in elastic_log_list if startDate <= _.credate <= endDate]
                elastic_log_list = [_ for _ in elastic_log_list if _.uniqueid == logSource] if logSource else elastic_log_list
                elastic_log_list = [_ for _ in elastic_log_list if _.logcode == logCode] if logCode else elastic_log_list
                _yesterday_html = request.POST.get('startDate')
                _today_html = request.POST.get('endDate')
                logger.debug(f"globalElasticList length : {len(globalElasticLogList)}")
                globalElasticLogList = elastic_log_list
    else:
        if check_environment_for_elastic():
            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                               sniff_on_start=True, request_timeout=2)
            _body = '{"size":5000, "query":{"bool":{"must":[{"range": {"credate": {"from": "%s", "to": "%s", "include_lower": true, "include_upper": false, "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis", "boost": 1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"id":{"order":"desc"}}],"aggregations":{"sonuc":{"date_histogram":{"field":"credate","interval":"1h","offset":0,"order":{"_key":"asc"},"keyed":false,"min_doc_count":0,"extended_bounds" : { "min" : "%s","max":"%s"}}}}}' % (_yesterday_string, _today_string, _yesterday_string, _today_string)
            _body = json.loads(_body)
            search = elastic_connection.search(index="atibalogs", body=_body)
            # response = search.execute()
            # elastic_log_list = [LogFromElastic(hit_object=hit) for hit in response.hits]
            elastic_log_list = [LogFromElastic(dictionary=hit["_source"]) for hit in search["hits"]["hits"]]

            # elastic_aggregation = AggregationElastic(aggregation_object=response.aggregations, aggregation_name="sonuc")
            elastic_aggregation = AggregationElastic(dictionary=search["aggregations"], aggregation_name="sonuc")
            globalAggregation = elastic_aggregation

            # adding logCodeCount and LogCodeUniqueIds to LogFromElastic object with new aggregation query
            _aggregation_logCodeCounts_uniqueids = '"aggregations":{"logCodeCounts":{"terms":{"field":"logndx","size":100,"min_doc_count":1,"show_term_doc_count_error":false,"order":[{"_count":"desc"},{"_key":"asc"}]}, "aggregations":{"uniqueids":{"terms":{"field":"uniqueid", "size":100,"min_doc_count":1,"show_term_doc_count_error":false,"order":[{"_count":"desc"},{"_key":"asc"}]}}}}'
            _body2 = '{"size":0,"query": {"match_all": {}},"sort":[{"id":{"order":"desc"}}], %s}}' % _aggregation_logCodeCounts_uniqueids
            # logger.debug(f"body for logCodeCounts : {_body2}")
            _body2 = json.loads(_body2)
            search2 = elastic_connection.search(index="atibalogs", body=_body2)
            # logger.debug(f'aggregation result for logCodeCounts : {search2["aggregations"]["logCodeCounts"]["buckets"]}')
            for bucket in search2["aggregations"]["logCodeCounts"]["buckets"]:
                _uniqueids = [_["key"] for _ in bucket["uniqueids"]["buckets"]]
                _countsForUniquesids = [_["doc_count"] for _ in bucket["uniqueids"]["buckets"]]
                _list = [_ for _ in elastic_log_list if _.logcode == bucket["key"]]
                if len(_list) > 0:
                    for el in _list:
                        el.logCodeCount = bucket["doc_count"]
                        el.logCodeUniqueids = _uniqueids
                        el.logCodeUniqueidCounts = _countsForUniquesids
                    else:
                        continue
            globalElasticLogList = elastic_log_list
        else:
            elastic_log_list = [LogFromElastic(dictionary=x['_source']) for x in hitsListForTest]
            elastic_log_list = [_ for _ in elastic_log_list if _yesterday <= _.credate <= _today]
            logger.warning("No Elastic connection")
            logger.debug(f"globalElasticList length : {len(globalElasticLogList)}")
            globalElasticLogList = elastic_log_list

    context = {
        'route': route, 'today': _today_html, 'yesterday': _yesterday_html, 'logSource': logSource, 'logCode': logCode,
        'parameters': parameters, 'parameterValues': parameterValues
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/log_monitoring.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def log_monitoring_all(request, elastic_log_list=None, elastic_aggregation=None):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    global globalElasticLogList, globalBool, globalAggregation
    # record_per_page = 20
    route = "general"
    all_logs_chart_labels = []
    all_logs_chart_values = []
    sortby = request.GET.get("sort") if check_existence(request.GET.get("sort")) else None
    page = request.GET.get('page') if check_existence(request.GET.get('page')) else None
    filterby = []
    # logger.debug(f"{request.GET}")
    for k, v in request.GET.items():
        if k in ['ipaddress', 'uniqueid', 'logcode'] and v != "":
            filterby.append((k, v))
    searchEvent = request.GET.get('searchEvent') if check_existence(request.GET.get('searchEvent')) else None

    _today = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
    _yesterday = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(hours=24), '%Y-%m-%d %H:%M:%S')

    # logger.debug(f"{elastic_log_list}")
    if not elastic_log_list:
        elastic_log_list = globalElasticLogList
    if not elastic_aggregation:
        elastic_aggregation = globalAggregation
    if len(elastic_log_list) > 0:
        if not elastic_aggregation:
            elastic_log_list.sort(key=lambda x: x.credate, reverse=True)
            first_date = elastic_log_list[0].credate.replace(microsecond=0, second=0, minute=0)  # getting exact time like 13:00:00 to create time intervals for one hours
            hours_diff = abs(int((elastic_log_list[-1].credate-elastic_log_list[0].credate).total_seconds()/3600))  # absolute value of datetime difference
            hours_count = hours_diff if hours_diff <= 96 else 96
            template_message_show(request, 'info',
                                  f'Chart was generated for piece of {hours_count} hours. It can be max 96 hours')
            # logger.debug(f"{elastic_log_list[0].credate} to {elastic_log_list[-1].credate}")
            # logger.debug(f"difference : {(elastic_log_list[-1].credate-elastic_log_list[0].credate)}")
            # logger.debug(f"first hour : {elastic_log_list[0].credate.hour}")
            # logger.debug(f"difference in hours : {hours_count}")
            # logger.debug(f"first_date in hours : {first_date}")

            for i in range(0, hours_count+1):
                _first = first_date - datetime.timedelta(hours=i)
                _last = first_date - datetime.timedelta(hours=(i+1))
                all_logs_chart_labels.append(f"{_first.day}-{datetime.datetime.strftime(_first, '%b')} - H:{_first.hour}")
                _filter = filter(lambda x: _first >= x.credate > _last, elastic_log_list)  # for descending order
                # _filter = filter(lambda x: _first <= x.credate < _last, elastic_log_list)  # for ascending order
                filtered = list(_filter)
                all_logs_chart_values.append(len(filtered))

            # if sortby:
            #     globalBool = not globalBool
            #     logger.debug(f"{getattr(elastic_log_list[0], sortby)}")
            #     elastic_log_list.sort(key=lambda x: getattr(x, sortby), reverse=globalBool)
        else:
            for x, y in elastic_aggregation.kvtupples:
                if x == "key_as_string":
                    all_logs_chart_labels.append(y)
                if x == "doc_count":
                    all_logs_chart_values.append(y)
            # template_message_show(request, 'info', f'Chart was generated for piece of {len(elastic_aggregation.kvtupples)} hours.')
    else:
        # elastic_log_list = []
        template_message_show(request, "warning", f"List is empty between {_yesterday} and {_today}")

    if len(filterby) > 0:
        logger.debug(f"filter operations for : {filterby}")
        for x in filterby:
            elastic_log_list = [_ for _ in elastic_log_list if getattr(_, x[0]) == x[1]]
    else:
        elastic_log_list = globalElasticLogList

    filterIpList = []
    filterUniqueidList = []
    filterLogCodeList = []
    for _ in elastic_log_list:
        if _.ipaddress not in filterIpList:
            filterIpList.append(_.ipaddress)
        if _.uniqueid not in filterUniqueidList:
            filterUniqueidList.append(_.uniqueid)
        if _.logcode not in filterLogCodeList:
            filterLogCodeList.append(_.logcode)

    if searchEvent:
        elastic_log_list = [_ for _ in elastic_log_list if searchEvent.lower() in _.logevent.lower()]

    if sortby:
        if not page:
            globalBool = not globalBool
        try:
            elastic_log_list.sort(key=lambda x: getattr(x, sortby), reverse=globalBool)
        except TypeError:
            elastic_log_list.sort(key=lambda x: getattr(x, sortby) if getattr(x, sortby) else "", reverse=globalBool)
        except Exception as err:
            logger.exception(f"An error occurred in inventories.logs view trying to sort list. ERROR IS : {err}")
            template_message_show(request, "warning", f"Sorting error {err}")

    paginator = Paginator(elastic_log_list, record_per_page)
    try:
        elastic_log_list = paginator.page(page)
    except PageNotAnInteger:
        elastic_log_list = paginator.page(1)
    except EmptyPage:
        elastic_log_list = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'elasticLogList': elastic_log_list,
        'all_logs_chart_labels': all_logs_chart_labels, 'all_logs_chart_values': all_logs_chart_values,
        'filterIpList': filterIpList, 'filterUniqueidList': filterUniqueidList, 'filterLogCodeList': filterLogCodeList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/log_monitoring_all.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
def all_logs(request):
    """
    this view is deprecated !!!
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    # record_per_page = 20
    filtered_count = ""
    totalPages = 1

    try:
        deviceList = NetworkDevice.objects.all()
    except Exception as err:
        deviceList = []
        logger.exception(f"An error occurred in all_logs view trying to get device list : {err}")

    _today = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
    _yesterday = datetime.datetime.strftime(datetime.datetime.now()-datetime.timedelta(hours=24), '%Y-%m-%d %H:%M:%S')
    _interval_in_hours = round(((datetime.datetime.strptime(_today, '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(_yesterday, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600), 2)

    today = datetime.datetime.strftime(timezone.now(), '%Y-%m-%dT%H:%M')  # html values
    yesterday = datetime.datetime.strftime(datetime.datetime.now()-datetime.timedelta(hours=24), '%Y-%m-%dT%H:%M')  # html values
    # _start = 0
    # _end = 1000
    caption = record_per_page
    # if len(request.GET) > 0:
    #     logger.debug(f"{request.GET}")
    #     limit_q = request.GET.get('limit_q')
    #     fromDate_q = date_picker_string(request.GET.get('fromDate_q')) if not request.GET.get(
    #         'fromDate_q') or request.GET.get('fromDate_q') != "" else _yesterday
    #     toDate_q = date_picker_string(request.GET.get('toDate_q')) if not request.GET.get(
    #         'toDate_q') or request.GET.get('toDate_q') != "" else _today
    #     device_q = request.GET.get('device_q')
    #     event_q = request.GET.get('event_q')
    #     page_q = request.GET.get('page_q')
    #     _interval_in_hours = round(((timezone.datetime.strptime(toDate_q,
    #                                                             '%Y-%m-%d %H:%M:%S') - timezone.datetime.strptime(
    #         fromDate_q, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600), 2)
    #     if device_q and device_q != "":
    #         if device_q.find(".") == -1:
    #             logger.debug(f"we got simplified_mac : {device_q}")
    #         else:
    #             logger.debug(f"we got deviceip : {device_q}")
    #
    #     if event_q and event_q != "":
    #         logger.debug(f"search it in log._source : {event_q}")
    #
    #     if fromDate_q and fromDate_q != "":
    #         logger.debug(f"Today inside IF : {toDate_q}")
    logList = []
    totalCount = 0
    logger.debug(f"{request.GET}")
    if len(request.GET) > 0:
        # fromDate_q = & toDate_q = & device_q = A & limit_q = & event_q = & page_q
        limit_q = request.GET.get('limit_q')

        fromDate_q = date_picker_string(request.GET.get('fromDate_q')) if request.GET.get('fromDate_q') and request.GET.get('fromDate_q') != "" else _yesterday
        toDate_q = date_picker_string(request.GET.get('toDate_q')) if request.GET.get('toDate_q') and request.GET.get('toDate_q') != "" else _today

        _interval_in_hours = round(((datetime.datetime.strptime(toDate_q, '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(fromDate_q, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600), 2)
        device_q = request.GET.get('device_q')
        event_q = request.GET.get('event_q')
        page_q = request.GET.get('page_q')

        if check_environment_for_elastic():
            try:
                elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                                   sniff_on_start=True, request_timeout=5)
                search_object = Search(using=elastic_connection, index="atibalogs")
                search = search_object.sort("-credate")

                if device_q and device_q != "":
                    if device_q.find(".") == -1:
                        search = search.query("term", **{"uniqueid": {"value": device_q}})

                if event_q and event_q != "":
                    logger.debug(f"search it in log._source : {event_q}")
                    search = search.query(Q(query=event_q, fields=['body']))

                if fromDate_q and fromDate_q != "":
                    logger.debug(f"Today inside IF : {toDate_q}")
                    search = search.query()

                if limit_q and limit_q != "":
                    limit_q = int(limit_q)
                    search = search[:limit_q]
                    filtered_count = limit_q
                    totalPages = math.ceil(limit_q / record_per_page)
                    if page_q and page_q != "":
                        page_q = int(page_q)
                        _start = (page_q - 1) * record_per_page
                        _end = _start + record_per_page
                        search = search[_start:_end] if _end < limit_q else search[_start:limit_q]
                        caption = ((page_q - 1) * record_per_page) + record_per_page

                if (page_q and page_q != "") and not (limit_q and limit_q != "") and not (
                        event_q and event_q != "") and not (device_q and device_q != ""):
                    page_q = int(page_q)
                    _start = (page_q - 1) * record_per_page
                    _end = _start + record_per_page
                    search = search[_start:_end]
                    caption = ((page_q - 1) * record_per_page) + record_per_page

                # search = search.query()
                response = search.execute()
                totalCount = response.hits.total
                if (page_q and page_q != "") and not (limit_q and limit_q != ""):
                    totalPages = math.ceil(totalCount / record_per_page)
                logList = response.hits

            except Exception as err:
                logger.exception(f"An error occurred in all_logs view trying to connect elasticsearch : {err}")

        else:
            logger.warning(f"No Elasticsearch Connection in Environment")

    else:
        if os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.production" or os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.developing":
            try:
                elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                                   sniff_on_start=True, request_timeout=5)
                search_object = Search(using=elastic_connection, index="atibalogs")
                search = search_object.sort("-id")
                search = search[:1000]
                # filtered_count = 1000
                search = search.query()
                response = search.execute()
                totalCount = response.hits.total
                logList = response.hits[0:20]
                totalPages = math.ceil(totalCount / record_per_page)
            except Exception as err:
                logger.exception(f"An error occurred trying to connect elasticsearch : {err}")
        elif os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.development":
            logger.warning(f"No Elasticsearch Connection in Environment")

    if request.GET.get('page_q') and int(request.GET.get('page_q')) == totalPages:
        caption = ((int(request.GET.get('page_q')) - 1) * record_per_page) + len(logList)

    all_logs_chart_labels = ["day 1", "day 2", "day 3", "day 4", "day 5", "day 5", "day 5", "day 5", "day 5", "day 6",
                             "day 7", "day 8", "day 9", "day 10", "day 11", "day 12", "day 13"]
    all_logs_chart_values = [25, 35, 43, 12, 5, 6, 9, 55, 23, 35, 43, 12, 5, 6, 9, 55, 23]

    context = {
        'route': 'general', 'totalCount': totalCount, 'totalPages': totalPages, 'totalPagesString': str(totalPages),
        'today': today, 'yesterday': yesterday, 'interval_in_hours': _interval_in_hours,
        'logList': logList, 'deviceList': deviceList,
        'caption': caption,
        'filtered_count': filtered_count,
        'all_logs_chart_labels': all_logs_chart_labels,
        'all_logs_chart_values': all_logs_chart_values,

        # 'time_interval_form': time_interval_form,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/elastic_logs.html', context)


# @licence_required
@login_required
@csrf_exempt
def log_sources(request, exceed=None):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    # record_per_page = 20

    if request.method == 'POST':
        logger.debug(f"{request.POST}")
        if check_existence(request.POST.get("sendToHistory")):
            try:
                LogSources.objects.filter(id=int(request.POST.get("sendToHistory"))).update(scanstatus=9, status='P', updatedate=datetime.datetime.now())
                template_message_show(request, 'success', "Successfully sent to history")
            except Exception as err:
                logger.exception(f"An error occurred in log_sources view when trying to sent log source in history")
                template_message_show(request, 'error', "Fail to send history")

        if check_existence(request.POST.get("sendToStaging")):
            try:
                LogSources.objects.filter(id=int(request.POST.get("sendToStaging"))).update(scanstatus=3, updatedate=datetime.datetime.now())
                template_message_show(request, 'success', "Successfully sent to staging area")
            except Exception as err:
                logger.exception(f"An error occurred in log_sources view when trying to sent log source to staging area")
                template_message_show(request, 'error', "Fail to send history")

        if (request.POST.get('component_name') and request.POST.getlist('id_list')) and (
                request.POST.get('component_name') != "" and len(request.POST.getlist('id_list')) > 0):

            try:
                if Components.objects.get(componentname=request.POST.get('component_name')):
                    template_message_show(request, 'warning',
                                          f'You got a component with {request.POST.get("component_name")} name !!')
                    # memory usage logging with memory_tracer
                    top_stats = tracemalloc.take_snapshot().statistics('lineno')
                    total_size, unit = take_memory_usage(top_stats)
                    logger.info(f"Memory allocation  {total_size} {unit}")
                    memory_tracer.info(f"{total_size}")
                    tracemalloc.stop()
                    return redirect('log_sources')
            except Exception:
                logger.warning(f"Ok, no record with this component name {request.POST.get('component_name')}")

            component = Components()
            component.componentname = request.POST.get('component_name')
            try:
                component.save()
                ids_of_sources = [int(_) for _ in request.POST.getlist('id_list')]
                for _id in ids_of_sources:
                    _source = LogSources.objects.get(id=_id)
                    _comps = _source.componentids if _source.componentids else []
                    _comps.append(component.id)
                    _source.componentids = list(set(_comps))
                    try:
                        _source.save()
                    except Exception as err:
                        logger.exception(f"An error occurred while trying to add component id to log source id : {_source.id}")
                template_message_show(request, 'success', f'Successfully saved component : {component.componentname}')
            except Exception as err:
                logger.exception(f'An error occurred while trying to save component ERROR IS : {err}')
                template_message_show(request, 'error', 'Failed to save component')
        if (request.POST.get('application_name') and request.POST.getlist('component_ids')) and (
                request.POST.get('application_name') != "" and len(request.POST.getlist('component_ids')) > 0):

            try:
                if Applications.objects.get(appname=request.POST.get('application_name')):
                    template_message_show(request, 'warning',
                                          f'You got a application with {request.POST.get("application_name")} name !!')
                    # memory usage logging with memory_tracer
                    top_stats = tracemalloc.take_snapshot().statistics('lineno')
                    total_size, unit = take_memory_usage(top_stats)
                    logger.info(f"Memory allocation  {total_size} {unit}")
                    memory_tracer.info(f"{total_size}")
                    tracemalloc.stop()
                    return redirect('log_sources')
            except Exception:
                logger.warning(f"Ok, no record with this application name {request.POST.get('application_name')}")

            _application = Applications()
            _application.appname = request.POST.get('application_name')
            # _application.componentids = [int(_) for _ in request.POST.getlist('component_ids')]
            try:
                _application.save()
                ids_of_components = [int(_) for _ in request.POST.getlist('component_ids')]
                for id in ids_of_components:
                    _component = Components.objects.get(id=id)
                    _apps = _component.applicationids if _component.applicationids else []
                    _apps.append(_application.id)
                    _component.applicationids = list(set(_apps))
                    try:
                        _component.save()
                    except Exception as err:
                        logger.exception(f"An error occurred while trying to add application id to component. ERROR IS {err}")
                template_message_show(request, 'success', f'Successfully saved application {_application.appname}')
            except Exception as err:
                logger.exception(f'An error occurred when trying to save application ERROR IS : {err}')
                template_message_show(request, 'error', f'An error occurred when trying to save application as {err}')

    # logger.debug(f"Count of saved log sources : {LogSources.objects.count()}")

    # logSources = LogSources.objects.all()  # log source list for creating component
    # logSources = list(LogSources.objects.filter(scanstatus__in=[0])) + list(LogSources.objects.filter(scanstatus__isnull=True))  # log source list for creating component
    logSources = list(LogSources.objects.filter(connectedmac__isnull=True).filter(Q(scanstatus__in=[0]) | Q(scanstatus__isnull=True)).distinct())  # log source list for creating component
    stagingSourcesList = list(LogSources.objects.filter(scanstatus__in=[1, 2, 3, 5]).exclude(connectedmac__isnull=False))
    historySourcesList = list(LogSources.objects.filter(scanstatus=9).exclude(connectedmac__isnull=False))
    componentList = Components.objects.all()
    applicationList = Applications.objects.all()
    profileList = []

    q = request.GET.get('q')
    if q:
        logSourcesList = LogSources.objects.exclude(scanstatus=1).exclude(scanstatus=2).exclude(scanstatus=9).exclude(connectedmac__isnull=False).filter(
            Q(sourcename__icontains=q) | Q(ipaddress__icontains=q) | Q(macaddress__icontains=q) | Q(
                hostname__icontains=q) | Q(customname__icontains=q) | Q(devicetype__icontains=q)).distinct()
    else:
        # logSourcesList = list(LogSources.objects.filter(scanstatus__in=[0, None]))
        logSourcesList = list(LogSources.objects.filter(Q(scanstatus__in=[0]) | Q(scanstatus__isnull=True)).exclude(connectedmac__isnull=False))

    paginator = Paginator(logSourcesList, record_per_page)
    page = request.GET.get('page')
    try:
        logSourcesList = paginator.page(page)
    except PageNotAnInteger:
        logSourcesList = paginator.page(1)
    except EmptyPage:
        logSourcesList = paginator.page(paginator.num_pages)

    """
        Permanent license control and warnings
    """
    newsList = []

    if exceed:
        logger.warning(f"Exceed !! {exceed}")
        _exceed_sentence = "As a temporary solution you can reduce active log sources by sending them to " \
                           "history. But we suggest you add license. "
        _exceed_sentence += " <a href='/accounts/license/'> Add License </a>"
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
        'route': 'general', 'logSourcesList': logSourcesList, 'logSources': logSources, 'componentList': componentList,
        'applicationList': applicationList, 'profileList': profileList, 'stagingSourcesList': stagingSourcesList,
        'historySourcesList': historySourcesList, 'newsList': newsList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/log_sources.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
def add_log_sources(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'general'
    # customNameList = [_.customname for _ in LogSources.objects.all() if _.customname]
    customNameList = list(LogSources.objects.values_list('customname', flat=True).exclude(customname__isnull=True))

    context = {
        'route': route, 'customNameList': customNameList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_log_sources.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_networkdevice(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'networkdevice'
    _record_status = False
    identifierList = []
    markList = []
    modelList = []
    versionList = []
    customNameList = list(LogSources.objects.values_list('customname', flat=True).exclude(customname__isnull=True))
    # if a uniqueid left from the past including any uppercase chars convert them to lower case
    customNameList = [_.lower() for _ in customNameList]
    # ipsOfNetworkDevices = [_.ipaddress for _ in list(LogSources.objects.filter(logsourceselection="networkdevice"))]
    ipsOfNetworkDevices = list(LogSources.objects.values_list('ipaddress', flat=True).filter(
        logsourceselection="networkdevice"))
    # we need monitor profile database table to get id values to give it template
    monitorProfileList = MonitorProfile.objects.all()
    parserProfileList = [{'name': _.parsername, 'value': _.id} for _ in DeviceParserProfile.objects.all()]
    locationProfileList = [{'name': _.locationname, 'value': _.id} for _ in DevLocations.objects.all()]
    ingestionProfileList = [{'name': _.ingestionprofilename, 'value': _.id} for _ in IngestionProfile.objects.all()]
    snmpProfileList = []
    snmpVersionList = [{'name': 'No Snmp', 'value': '0'},
                       {'name': 'V3', 'value': 'v3'},
                       {'name': 'V2c', 'value': 'v2c'}]
    v3AuthProtocolList = [{'name': 'No Snmp', 'value': '0'},
                          {'name': 'MD5', 'value': 'MD5'},
                          {'name': 'SHA', 'value': 'SHA'}]
    v3PrivacyProtocolList = [{'name': 'No Snmp', 'value': '0'},
                             {'name': 'DES', 'value': 'DES'},
                             {'name': 'AES', 'value': 'AES'}]
    deviceTypeList = [{'name': _.devicetype, 'value': _.devicetypecode} for _ in DeviceTypeList.objects.all()]

    # logger.debug(f"{request.GET}")
    if len(request.GET) > 0:
        # if request.GET.get('adding') == "networkdevice" or request.GET.get('adding') == "nginx" or request.GET.get('adding') == "postgresql":
        #     route = request.GET.get('adding')

        if request.GET.get('device_add_method') == 'scan':
            # snmpProfileList = MonitorProfileDetails.objects.all()  # we need object lis in html
            # identifierList = [{'name': 'Mac Address', 'value': 'macaddress'},
            #                   {'name': 'IP Address', 'value': 'ipaddress'},
            #                   {'name': 'Host Name', 'value': 'hostname'}]
            identifierList = [{'name': 'Custom Name', 'value': 'customname'}]
            monitorProfileList = list(MonitorProfile.objects.filter(monitorprofiletype="SNMP"))
            snmpProfileList = list(MonitorProfileDetails.objects.exclude(snmpversion=None))  # bu liste monitor profile id si yukarıdaki listede olanlardan oluşturulacak
            snmpVersionList = [{'name': 'V3', 'value': 'v3'}, {'name': 'V2c', 'value': 'v2c'}]
            v3AuthProtocolList = [{'name': 'MD5', 'value': 'MD5'}, {'name': 'SHA', 'value': 'SHA'}]
            v3PrivacyProtocolList = [{'name': 'DES', 'value': 'DES'}, {'name': 'AES', 'value': 'AES'}]
            route = request.GET.get('device_add_method')
            if request.method == 'POST':
                _record_status = True  # in exceptions can trace the status to see recording result

                network_parameter = NetworkParameters()
                # "2021-02-10 15:20:44".strptime('%Y-%m-%d %H:%M:%S')
                network_parameter.networkname = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_source = LogSources()
                log_source.logsourceselection = 'networkdevice'
                log_source.ipaddress = edit_ip_address_from_string(request.POST.get('ip_address'))
                network_parameter.ipaddress = edit_ip_address_from_string(request.POST.get('ip_address'))
                network_parameter.subnetmask = request.POST.get('ip_mask')
                log_source.uniqueidtype = request.POST.get('unique_identifier')
                log_source.devicetype = request.POST.get('device_type')
                log_source.parserprofile = int(request.POST.get('parser_profile')) if request.POST.get('parser_profile') and request.POST.get('parser_profile') != "new" else None
                log_source.locationprofile = int(request.POST.get('location_profile')) if request.POST.get('location_profile') and request.POST.get('location_profile') != "new" else None
                log_source.ingestionprofile = int(request.POST.get('ingestion_profile')) if request.POST.get('ingestion_profile') and request.POST.get('ingestion_profile') != "new" else None
                log_source.manuallyadded = False

                # request.POST.get('snmp_profile') value is id ScanParameters object id

                if request.POST.get('snmp_profile') == "0":  # if user didn't chose an existing snmp parameters
                    # scan_parameters = ScanParameters()
                    monitor_profile_details = MonitorProfileDetails()
                    monitor_profile_details.monitorProfile_id = int(request.POST.get('monitor_profile'))
                    monitor_profile_details.paramsname = request.POST.get('snmp_profile_name')
                    monitor_profile_details.querytosend = request.POST.get('oid')
                    monitor_profile_details.snmpversion = request.POST.get('snmp_version')
                    try:
                        monitor_profile_details.communitystring = encode_with_java(request.POST.get('community_string'))
                    except Exception as err:
                        _record_status = False
                        logger.exception(f"Couldn't save scan parameters comm_str because of : {err}")
                        template_message_show(request, "error", f"Couldn't save scan parameters because of : {err}")
                    if request.POST.get('snmp_version') == "v3" or request.POST.get('snmp_version') == "V3":
                        monitor_profile_details.snmpv3user = request.POST.get('v3_user_name')
                        monitor_profile_details.snmpv3authprotocol = request.POST.get('v3_auth_protocol')
                        monitor_profile_details.snmpv3privacyprotocol = request.POST.get('v3_privacy_protocol')
                        try:
                            monitor_profile_details.snmpv3authpass = encode_with_java(request.POST.get('v3_auth_password'))
                            monitor_profile_details.snmpv3privacypass = encode_with_java(request.POST.get('v3_privacy_password'))
                        except Exception as err:
                            _record_status = False
                            logger.exception(f"Couldn't save scan v3 parameters because of : {err}")
                            template_message_show(request, "error",
                                                  f"Couldn't save scan v3 parameters because of : {err}")

                    monitor_profile_details.save()
                    _mpdid = monitor_profile_details.id
                else:
                    _mpdid = request.POST.get('snmp_profile')

                log_source.monitorprofile = _mpdid
                log_source.creationdate = datetime.datetime.now()
                log_source.updatedate = datetime.datetime.now()

                # log_source.save()
                network_parameter.save()
                _java_result = ""
                try:
                    _java_result = scan_device_with_java(network_parameter.id, _mpdid, log_source.uniqueidtype)
                except Exception as err:
                    logger.exception(f"An error occurred while trying to call scan_device_with_java. ERROR IS : {err}")
                    template_message_show(request, "error", f"Auto scan encountered an error {err}")
                if _java_result == "" or _java_result == "NOTOK":
                    logger.error("An error occurred in scan_device_with_java runtime !!")
                    template_message_show(request, "error", f"An error occurred in java auto scan runtime")
                else:
                    template_message_show(request, "success", "networkdevice (SNMP source) saved successfully")
                # memory usage logging with memory_tracer
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return redirect('add_log_sources')

            # add_network_device_with_scanning(request)
        elif request.GET.get('device_add_method') == 'manual':
            identifierList = [{'name': 'Mac Address', 'value': 'macaddress'},
                              {'name': 'IP Address', 'value': 'ipaddress'},
                              {'name': 'Host Name', 'value': 'hostname'},
                              {'name': 'Custom Name', 'value': 'customname'}]
            route = request.GET.get('device_add_method')
            snmpProfileList = MonitorProfileDetails.objects.all()  # we need object lis in html
            markList = [{'name': _.markname, 'value': _.id} for _ in DeviceMark.objects.all()]
            modelList = [{'name': _.modelname, 'value': _.id, 'markid': _.brand_id, 'devicetype': _.devicetype}
                         for _ in DeviceModel.objects.all()]
            versionList = [{'name': _.versioncode, 'value': _.id, 'devicetype': _.devicetype} for _ in DeviceVersions.objects.all()]
            if request.method == 'POST':
                _record_status = True  # in exceptions can trace the status to see recording result
                log_source = LogSources()
                log_source.logsourceselection = 'networkdevice'

                # if request.GET.get('adding') != "networkdevice" and (request.POST.get('before_tag') and request.POST.get('tag') and request.POST.get('after_tag')):
                #     log_source.taglocation = f"(?<={request.POST.get('before_tag')})(.*)(?={request.POST.get('after_tag')})"
                #     log_source.syslogtag = request.POST.get('tag')
                #     log_source.snmpstatus = False

                if request.POST.get('monitor_profile') == "0" and request.POST.get('snmp_profile') == "0":
                    monitor_profile = MonitorProfile()
                    monitor_profile.monitorprofilename = request.POST.get('monitor_profile_name')
                    monitor_profile.monitorprofiletype = request.POST.get('monitor_profile_type')
                    monitor_profile.save()

                    monitor_profile_detail = MonitorProfileDetails()
                    monitor_profile_detail.monitorProfile_id = monitor_profile.id
                    monitor_profile_detail.paramsname = request.POST.get('snmp_profile_name')
                    monitor_profile_detail.querytosend = request.POST.get('oid')
                    monitor_profile_detail.responsetoreceive = request.POST.get('response_receive')
                    monitor_profile_detail.responsetodown = request.POST.get('response_down')
                    if request.POST.get('monitor_profile_type') == "SNMP":
                        try:
                            monitor_profile_detail.communitystring = encode_with_java(request.POST.get('community_string'))
                            monitor_profile_detail.snmpv3user = request.POST.get('v3_user_name') if request.POST.get('v3_user_name') else None
                            monitor_profile_detail.snmpv3authprotocol = request.POST.get('v3_auth_protocol') if request.POST.get('v3_auth_protocol') else None
                            monitor_profile_detail.snmpv3authpass = encode_with_java(request.POST.get('v3_auth_password')) if request.POST.get('v3_auth_password') else None
                            monitor_profile_detail.snmpv3privacyprotocol = request.POST.get('v3_privacy_protocol') if request.POST.get('v3_privacy_protocol') else None
                            monitor_profile_detail.snmpv3privacypass = encode_with_java(request.POST.get('v3_privacy_password')) if request.POST.get('v3_privacy_password') else None
                            monitor_profile_detail.snmpversion = request.POST.get('snmp_version')
                        except Exception as err:
                            _record_status = False
                            logger.exception(f"Couldn't save monitor profile details because of : {err}")
                            template_message_show(request, "error",
                                                  f"Couldn't save monitor profile details because of : {err}")

                    monitor_profile_detail.save()

                    log_source.monitorprofile = monitor_profile_detail.id
                elif request.POST.get('monitor_profile') != "0" and request.POST.get('snmp_profile') == "0":
                    try:
                        monitor_profile = MonitorProfile.objects.get(id=int(request.POST.get('monitor_profile')))
                        # if request.POST.get(
                        #         'monitor_profile_name') != monitor_profile.monitorprofilename or request.POST.get(
                        #         'monitor_profile_type') != monitor_profile.monitorprofiletype:
                        #     monitor_profile.monitorprofilename = request.POST.get('monitor_profile_name')
                        #     monitor_profile.monitorprofiletype = request.POST.get('monitor_profile_type')
                        #     monitor_profile.save()

                        monitor_profile_detail = MonitorProfileDetails()
                        monitor_profile_detail.monitorProfile_id = monitor_profile.id
                        monitor_profile_detail.paramsname = request.POST.get('snmp_profile_name')
                        monitor_profile_detail.querytosend = request.POST.get('oid')
                        monitor_profile_detail.responsetoreceive = request.POST.get('response_receive') if request.POST.get('response_receive') else None
                        monitor_profile_detail.responsetodown = request.POST.get('response_down') if request.POST.get('response_down') else None

                        monitor_profile_detail.snmpv3user = request.POST.get('v3_user_name') if request.POST.get(
                            'v3_user_name') else None
                        monitor_profile_detail.snmpv3authprotocol = request.POST.get(
                            'v3_auth_protocol') if request.POST.get('v3_auth_protocol') else None
                        monitor_profile_detail.snmpv3privacyprotocol = request.POST.get(
                            'v3_privacy_protocol') if request.POST.get('v3_privacy_protocol') else None
                        monitor_profile_detail.snmpversion = request.POST.get('snmp_version')
                        try:
                            monitor_profile_detail.communitystring = encode_with_java(request.POST.get('community_string'))
                            monitor_profile_detail.snmpv3authpass = encode_with_java(request.POST.get('v3_auth_password')) if request.POST.get('v3_auth_password') else None
                            monitor_profile_detail.snmpv3privacypass = encode_with_java(request.POST.get('v3_privacy_password')) if request.POST.get('v3_privacy_password') else None
                        except Exception as err:
                            _record_status = False
                            logger.exception(f"Couldn't save monitor profile details because of : {err}")
                            template_message_show(request, "error",
                                                  f"Couldn't save monitor profile details because of : {err}")

                        monitor_profile_detail.save()

                        log_source.monitorprofile = monitor_profile_detail.id
                    except Exception as err:
                        logger.exception(f"no monitorprofdetails found for id = {request.POST.get('snmp_profile')} - Error : {err}")
                elif request.POST.get('monitor_profile') != "0" and request.POST.get('snmp_profile') != "0":
                    try:
                        monitor_profile = MonitorProfile.objects.get(id=int(request.POST.get('monitor_profile')))
                        monitor_profile_detail = MonitorProfileDetails.objects.get(id=int(request.POST.get('snmp_profile')))
                        if monitor_profile_detail.monitorProfile_id != monitor_profile.id:
                            new_monitor_profile_detail = MonitorProfileDetails()
                            new_monitor_profile_detail = monitor_profile_detail
                            new_monitor_profile_detail.monitorProfile_id = monitor_profile.id
                            new_monitor_profile_detail.save()
                            log_source.monitorprofile = new_monitor_profile_detail.id
                        else:
                            log_source.monitorprofile = monitor_profile_detail.id

                    except Exception as err:
                        logger.exception(f"no monitorprofdetails found for id = {request.POST.get('snmp_profile')} - Error : {err}")

                log_source.ipaddress = edit_ip_address_from_string(request.POST.get('ip_address'))
                log_source.uniqueidtype = request.POST.get('unique_identifier') if request.POST.get('unique_identifier') and request.POST.get('unique_identifier') != "" else "macaddress"
                if request.POST.get('unique_identifier') and request.POST.get('unique_identifier') == "customname":
                    if check_existence(request.POST.get('custom_name')):
                        log_source.customname = (request.POST.get('custom_name')).lower()
                        log_source.uniqueid = (request.POST.get('custom_name')).lower()
                else:
                    log_source.uniqueid = getattr(log_source, log_source.uniqueidtype) if getattr(log_source, log_source.uniqueidtype) else None

                log_source.sourcename = request.POST.get('log_source_name') if request.POST.get('log_source_name') and request.POST.get('log_source_name') != "" else None

                log_source.parserprofile = int(request.POST.get('parser_profile')) if request.POST.get('parser_profile') and request.POST.get('parser_profile') != "0" else None
                log_source.locationprofile = int(request.POST.get('location_profile')) if request.POST.get('location_profile') and request.POST.get('location_profile') != "0" else None
                log_source.ingestionprofile = int(request.POST.get('ingestion_profile')) if request.POST.get('ingestion_profile') and request.POST.get('ingestion_profile') != "0" else None

                log_source.markid = request.POST.get('markid')
                log_source.modelid = request.POST.get('modelid')
                # log_source.devicetype = request.POST.get('device_type')
                log_source.devicetype = DeviceModel.objects.get(
                    id=int(request.POST.get("modelid"))).devicetype if check_existence(
                    request.POST.get("modelid")) and int(
                    request.POST.get("modelid")) != log_source.modelid else None
                log_source.deviceverid = request.POST.get('deviceverid')

                log_source.scanstatus = 5  # adding to staging area in first add operation with 5 and not logging
                log_source.creationdate = datetime.datetime.now()
                log_source.updatedate = datetime.datetime.now()

                # log_source.save()
                # template_message_show(request, "success", f"{request.GET.get('adding')} saved successfully")

                try:
                    log_source.save()
                    template_message_show(request, "success", "networkdevice (SNMP source) saved successfully")
                except psycopg2.errors.UniqueViolation:
                    template_message_show(
                        request,
                        "error",
                        "networkdevice (SNMP source) failed to save because of uniqueid already exist")
                except Exception as err:
                    logger.exception(
                        f"An error occurred when trying to add new log source by manually ERROR IS : {err}")

    context = {
        'route': route,
        'identifierList': identifierList,
        'monitorProfileList': monitorProfileList,
        'parserProfileList': parserProfileList,
        'locationProfileList': locationProfileList,
        'ingestionProfileList': ingestionProfileList,
        'snmpProfileList': snmpProfileList,
        'snmpVersionList': snmpVersionList,
        'v3AuthProtocolList': v3AuthProtocolList,
        'v3PrivacyProtocolList': v3PrivacyProtocolList,
        'deviceTypeList': deviceTypeList,
        'markList': markList,
        'modelList': modelList,
        'versionList': versionList,
        'customNameList': customNameList,
        'ipsOfNetworkDevices': ipsOfNetworkDevices,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_log_sources.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_nginx(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'nginx'
    # -----------------------------------------------------------------------------------------------------
    identifierList = [{'name': 'Custom Name', 'value': 'customname'}]
    customNameList = list(LogSources.objects.values_list('customname', flat=True).exclude(customname__isnull=True))
    # if a uniqueid left from the past including any uppercase chars convert them to lower case
    customNameList = [_.lower() for _ in customNameList]
    monitorProfileList = list(MonitorProfile.objects.filter(monitorprofiletype="HTTP"))
    # monitorProfileList = list(MonitorProfile.objects.filter(Q(monitorprofiletype__icontains="HTTP")))
    # logger.debug(f"{monitorProfileList}")

    # to control ip an tag unique together in this view!!
    ipAndTaglist = [(_.ipaddress, _.syslogtag) for _ in LogSources.objects.all()]
    ipAndTaglistForJS = []
    for _ in LogSources.objects.all():
        _ip = _.ipaddress
        _tag = _.syslogtag if _.syslogtag else ""
        ipAndTaglistForJS.append({"ipaddress": _ip, "syslogtag": _tag})

    if len(monitorProfileList) > 0:
        monitorProfileDetailList = monitorProfileList[0].get_profile_details()
    else:
        monitorProfileDetailList = []
    parserProfileList = [{'name': _.parsername, 'value': _.id} for _ in DeviceParserProfile.objects.all()]
    locationProfileList = [{'name': _.locationname, 'value': _.id} for _ in DevLocations.objects.all()]
    ingestionProfileList = [{'name': _.ingestionprofilename, 'value': _.id} for _ in IngestionProfile.objects.all()]

    # deviceTypeList = [{'name': _.devicetype, 'value': _.devicetypecode} for _ in DeviceTypeList.objects.all()]

    if request.method == "POST":
        logger.debug(f"{request.POST}")
        """
        'ip_address': [''], *
        'unique_identifier': ['customname'], *
        'custom_name': [''], *
        'log_source_name': [''], *
        'monitor_profile_details': ['0'], *
        'parser_profile': ['0'], *
        'location_profile': ['0'], *
        'ingestion_profile': ['0'], *
        'before_tag': [''], *
        'taglocation': ['']
        'tag': [''], *
        'after_tag': [''] *
        
        # these are monitorprofiledetails parts
        # 'httpurl': [''], 
        # 'httpuri': [''], 
        # 'httpsecure': ['on'], we can see this value only if the box is checked 
        # 'httpmethod': ['GET'], 
        # 'httpport': [''], 
        # 'request_to_send': [''], 
        # 'response_to_receive': [''], 
        # 'response_to_down': [''], 
        """
        nginx_source = LogSources()
        nginx_source.logsourceselection = route
        nginx_source.markid = 1903002
        nginx_source.modelid = 1903002
        nginx_source.deviceverid = 1903002
        nginx_source.monitorprofile = int(request.POST.get('monitor_profile_details')) if check_existence(
            request.POST.get('monitor_profile_details')) and request.POST.get('monitor_profile_details') != "0" else None
        nginx_source.ipaddress = edit_ip_address_from_string(request.POST.get('ip_address'))
        nginx_source.uniqueidtype = request.POST.get('unique_identifier')
        nginx_source.customname = (request.POST.get('custom_name')).lower()
        nginx_source.uniqueid = (request.POST.get('custom_name')).lower()
        nginx_source.sourcename = request.POST.get('log_source_name')
        nginx_source.parserprofile = int(request.POST.get('parser_profile')) if request.POST.get(
            'parser_profile') and request.POST.get('parser_profile') != "0" else None
        nginx_source.locationprofile = int(request.POST.get('location_profile')) if request.POST.get(
            'location_profile') and request.POST.get('location_profile') != "0" else None
        nginx_source.ingestionprofile = int(request.POST.get('ingestion_profile')) if request.POST.get(
            'ingestion_profile') and request.POST.get('ingestion_profile') != "0" else None

        nginx_source.creationdate = datetime.datetime.now()
        nginx_source.updatedate = datetime.datetime.now()
        nginx_source.manuallyadded = True
        nginx_source.snmpstatus = False
        nginx_source.scanstatus = 5  # adding to staging area in first add operation with 5 and not logging
        # if request.POST.get('before_tag') and request.POST.get('tag') and request.POST.get('after_tag'):
        #     nginx_source.taglocation = f"(?<={request.POST.get('before_tag')})(.*)(?={request.POST.get('after_tag')})"
        #     nginx_source.syslogtag = request.POST.get('tag')

        nginx_source.syslogtag = request.POST.get('tag') if check_existence(request.POST.get('tag')) else None
        nginx_source.taglocation = request.POST.get('taglocation') if check_existence(request.POST.get('taglocation')) else None

        if (nginx_source.ipaddress, nginx_source.syslogtag) in ipAndTaglist:
            warning = "There is another log source with same ip & tag"
            logger.info(f"{warning}")
            context = {
                'route': route, 'customNameList': customNameList, 'ipAndTaglist': ipAndTaglistForJS,
                'monitorProfileDetailList': monitorProfileDetailList, 'warning': warning,
                'parserProfileList': parserProfileList,
                'ingestionProfileList': ingestionProfileList,
                'identifierList': identifierList,
                'locationProfileList': locationProfileList,
            }
            # memory usage logging with memory_tracer
            try:
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return render(request, 'AgentRoot/add_log_sources.html', context)

        try:
            nginx_source.save()
            template_message_show(request, "success", f"{route} saved successfully")
            # memory usage logging with memory_tracer
            try:
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('add_log_sources')
        except psycopg2.errors.UniqueViolation:
            template_message_show(request, "error",
                                  f"{route} failed to save because of uniqueid already exist")
        except Exception as err:
            logger.exception(f"An error occurred when trying to add new log source by manually ERROR IS : {err}")

    # -----------------------------------------------------------------------------------------------------
    context = {
        'route': route, 'customNameList': customNameList, 'ipAndTaglist': ipAndTaglistForJS,
        'monitorProfileDetailList': monitorProfileDetailList,
        'parserProfileList': parserProfileList,
        'ingestionProfileList': ingestionProfileList,
        'identifierList': identifierList,
        'locationProfileList': locationProfileList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_log_sources.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_postgresql(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'postgresql'
    # warning = ""
    identifierList = [{'name': 'Custom Name', 'value': 'customname'}]
    customNameList = list(LogSources.objects.values_list('customname', flat=True).exclude(customname__isnull=True))
    # if a uniqueid left from the past including any uppercase chars convert them to lower case
    customNameList = [_.lower() for _ in customNameList]
    monitorProfileList = list(MonitorProfile.objects.filter(Q(monitorprofiletype__icontains="POSTGRESQL")))

    # to control ip an tag unique together in this view!!
    ipAndTaglist = [(_.ipaddress, _.syslogtag) for _ in LogSources.objects.all()]
    ipAndTaglistForJS = []
    for _ in LogSources.objects.all():
        _ip = _.ipaddress
        _tag = _.syslogtag if _.syslogtag else ""
        ipAndTaglistForJS.append({"ipaddress": _ip, "syslogtag": _tag})
    # logger.debug(f"{monitorProfileList}")
    if len(monitorProfileList) > 0:
        monitorProfileDetailList = monitorProfileList[0].get_profile_details()
    else:
        monitorProfileDetailList = []
    parserProfileList = [{'name': _.parsername, 'value': _.id} for _ in DeviceParserProfile.objects.all()]
    locationProfileList = [{'name': _.locationname, 'value': _.id} for _ in DevLocations.objects.all()]
    ingestionProfileList = [{'name': _.ingestionprofilename, 'value': _.id} for _ in IngestionProfile.objects.all()]

    # deviceTypeList = [{'name': _.devicetype, 'value': _.devicetypecode} for _ in DeviceTypeList.objects.all()]

    if request.method == "POST":
        logger.debug(f"{request.POST}")
        """
        'ip_address': [''], *
        'unique_identifier': ['customname'], *
        'custom_name': [''], *
        'log_source_name': [''], *
        'monitor_profile_details': ['0'], *
        'parser_profile': ['0'], *
        'location_profile': ['0'], *
        'ingestion_profile': ['0'], *
        'before_tag': [''], 'tag': [''], 'after_tag': ['']  *
        
        # these are monitorprofiledetails parts
        # 'dbusername': ['istiklal'], 
        # 'dbname': [''], 
        # 'dbpass': ['Zek'], 
        # 'dbport': [''], 
        # 'query_to_send': [''], 
        # 'response_to_receive': [''], 
        # 'response_to_down': [''], 
        """
        postgresql_source = LogSources()
        postgresql_source.logsourceselection = route
        postgresql_source.markid = 1903001
        postgresql_source.modelid = 1903001
        postgresql_source.deviceverid = 1903001
        postgresql_source.monitorprofile = int(request.POST.get('monitor_profile_details')) if check_existence(
            request.POST.get('monitor_profile_details')) and request.POST.get('monitor_profile_details') != "0" else None
        postgresql_source.ipaddress = edit_ip_address_from_string(request.POST.get('ip_address'))
        postgresql_source.uniqueidtype = request.POST.get('unique_identifier')
        postgresql_source.customname = (request.POST.get('custom_name')).lower()
        postgresql_source.uniqueid = (request.POST.get('custom_name')).lower()
        postgresql_source.sourcename = request.POST.get('log_source_name')
        postgresql_source.parserprofile = int(request.POST.get('parser_profile')) if request.POST.get('parser_profile') and request.POST.get('parser_profile') != "0" else None
        postgresql_source.locationprofile = int(request.POST.get('location_profile')) if request.POST.get('location_profile') and request.POST.get('location_profile') != "0" else None
        postgresql_source.ingestionprofile = int(request.POST.get('ingestion_profile')) if request.POST.get('ingestion_profile') and request.POST.get('ingestion_profile') != "0" else None

        postgresql_source.creationdate = datetime.datetime.now()
        postgresql_source.updatedate = datetime.datetime.now()
        postgresql_source.manuallyadded = True
        postgresql_source.snmpstatus = False
        postgresql_source.scanstatus = 5  # adding to staging area in first add operation with 5 and not logging

        postgresql_source.syslogtag = request.POST.get('tag') if check_existence(request.POST.get('tag')) else None
        postgresql_source.taglocation = request.POST.get('taglocation') if check_existence(request.POST.get('taglocation')) else None

        if (postgresql_source.ipaddress, postgresql_source.syslogtag) in ipAndTaglist:
            warning = "There is another log source with same ip & tag"
            logger.info(warning)
            context = {
                'route': route, 'customNameList': customNameList, 'ipAndTaglist': ipAndTaglistForJS,
                'monitorProfileDetailList': monitorProfileDetailList, 'warning': warning,
                'parserProfileList': parserProfileList,
                'ingestionProfileList': ingestionProfileList,
                'identifierList': identifierList,
                'locationProfileList': locationProfileList,
            }
            # memory usage logging with memory_tracer
            try:
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return render(request, 'AgentRoot/add_log_sources.html', context)

        try:
            postgresql_source.save()
            template_message_show(request, "success", f"{route} saved successfully")
            # memory usage logging with memory_tracer
            try:
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('add_log_sources')
        except psycopg2.errors.UniqueViolation:
            template_message_show(request, "error", f"{route} failed to save because of uniqueid already exist")
        except Exception as err:
            logger.exception(f"An error occurred when trying to add new log source by manually ERROR IS : {err}")

    context = {
        'route': route, 'customNameList': customNameList, 'ipAndTaglist': ipAndTaglistForJS,
        'monitorProfileDetailList': monitorProfileDetailList,
        'parserProfileList': parserProfileList,
        'ingestionProfileList': ingestionProfileList,
        'identifierList': identifierList,
        'locationProfileList': locationProfileList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_log_sources.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_microsoftserver(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'microsoftserver'
    identifierList = [{'name': 'Custom Name', 'value': 'customname'}]
    customNameList = list(LogSources.objects.values_list('customname', flat=True).exclude(customname__isnull=True))
    # if a uniqueid left from the past including any uppercase chars convert them to lower case
    customNameList = [_.lower() for _ in customNameList]
    monitorProfileList = list(MonitorProfile.objects.filter(Q(monitorprofiletype__icontains="MICROSOFT") | Q(monitorprofiletype__icontains="ICMP")))
    vendorName = "MICROSOFT"
    # markid ?
    microsoftMarkId = 0
    try:
        microsoftMarkRows = DeviceMark.objects.filter(markname=vendorName)
        if microsoftMarkRows:
            microsoftMarkId = microsoftMarkRows[0].id
            logger.debug(f"devicemark id for {vendorName} is : {microsoftMarkId}")
        else:
            logger.warning(f"There is no record in devicemark for vendor {vendorName}.")
            exceptionalWarn = f"Probably you need to load log source driver for {vendorName}"
            try:
                # memory usage logging with memory_tracer
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return render(request, 'exceptions.html', {'route': route, 'warning': exceptionalWarn})
    except Exception as err:
        logger.exception(f"An error occurred trying to get devicemark for vendor {vendorName}. ERROR IS : {err}")
        exceptionalWarn = f"Some exceptional cases occurred for {vendorName}"
        try:
            # memory usage logging with memory_tracer
            top_stats = tracemalloc.take_snapshot().statistics('lineno')
            total_size, unit = take_memory_usage(top_stats)
            logger.info(f"Memory allocation  {total_size} {unit}")
            memory_tracer.info(f"{total_size}")
            tracemalloc.stop()
        except:
            logger.debug("tracemalloc stopped before somehow")
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return render(request, 'exceptions.html', {'route': route, 'warning': exceptionalWarn})
    # microsoftMarkId = 1904001

    modelList = [{'name': _.modelname, 'value': _.id, 'devicetype': _.devicetype} for _ in DeviceModel.objects.filter(brand_id=microsoftMarkId)]
    versionList = [{'name': _.versioncode, 'value': _.id, 'devicetype': _.devicetype} for _ in DeviceVersions.objects.filter(Q(devicetype__icontains="Server"))]
    # deviceTypeList = [{'name': _.devicetype, 'value': _.devicetypecode} for _ in DeviceTypeList.objects.all()]

    # to control ip an tag unique together in this view!!
    ipAndTaglist = [(_.ipaddress, _.syslogtag) for _ in LogSources.objects.all()]
    ipAndTaglistForJS = []
    for _ in LogSources.objects.all():
        _ip = _.ipaddress
        _tag = _.syslogtag if _.syslogtag else ""
        ipAndTaglistForJS.append({"ipaddress": _ip, "syslogtag": _tag})
    # logger.debug(f"{monitorProfileList}")
    if len(monitorProfileList) > 0:
        monitorProfileDetailList = monitorProfileList[0].get_profile_details()
    else:
        monitorProfileDetailList = []
    parserProfileList = [{'name': _.parsername, 'value': _.id} for _ in DeviceParserProfile.objects.all()]
    locationProfileList = [{'name': _.locationname, 'value': _.id} for _ in DevLocations.objects.all()]
    ingestionProfileList = [{'name': _.ingestionprofilename, 'value': _.id} for _ in IngestionProfile.objects.all()]

    if request.method == "POST":
        logger.debug(f"{request.POST}")
        """
        'ip_address': [''], *
        'unique_identifier': ['customname'], *
        'custom_name': [''], *
        'log_source_name': [''], *
        'monitor_profile_details': ['0'], *
        'parser_profile': ['0'], *
        'location_profile': ['0'], *
        'ingestion_profile': ['0'], *
        'before_tag': [''], 'tag': [''], 'after_tag': ['']  *
        'vendor': []
        'modelid': [1],
        'deviceverid': [2],

        ????????????????????????????????????????????
        # these are monitorprofiledetails parts
        # 'dbusername': ['istiklal'], 
        # 'dbname': [''], 
        # 'dbpass': ['Zek'], 
        # 'dbport': [''], 
        # 'query_to_send': [''], 
        # 'response_to_receive': [''], 
        # 'response_to_down': [''], 
        """

        microsoft_source = LogSources()
        microsoft_source.logsourceselection = route
        microsoft_source.devicetype = "Microsoft Server"
        microsoft_source.markid = microsoftMarkId
        # microsoft_source.modelid = int(request.POST.get('modelid')) if request.POST.get('modelid') and request.POST.get('modelid') != "0" else None
        microsoft_source.modelid = int(request.POST.get('modelid')) if request.POST.get('modelid') else None
        # microsoft_source.deviceverid = int(request.POST.get('deviceverid')) if request.POST.get('deviceverid') and request.POST.get('deviceverid') != "0" else None
        microsoft_source.deviceverid = int(request.POST.get('deviceverid')) if request.POST.get('deviceverid') else None
        microsoft_source.monitorprofile = int(request.POST.get('monitor_profile_details')) if check_existence(
            request.POST.get('monitor_profile_details')) and request.POST.get(
            'monitor_profile_details') != "0" else None
        microsoft_source.ipaddress = edit_ip_address_from_string(request.POST.get('ip_address'))
        microsoft_source.uniqueidtype = request.POST.get('unique_identifier')
        microsoft_source.customname = (request.POST.get('custom_name')).lower()
        microsoft_source.uniqueid = (request.POST.get('custom_name')).lower()
        microsoft_source.sourcename = request.POST.get('log_source_name')
        microsoft_source.parserprofile = int(request.POST.get('parser_profile')) if request.POST.get(
            'parser_profile') and request.POST.get('parser_profile') != "0" else None
        microsoft_source.locationprofile = int(request.POST.get('location_profile')) if request.POST.get(
            'location_profile') and request.POST.get('location_profile') != "0" else None
        microsoft_source.ingestionprofile = int(request.POST.get('ingestion_profile')) if request.POST.get(
            'ingestion_profile') and request.POST.get('ingestion_profile') != "0" else None
        microsoft_source.creationdate = datetime.datetime.now()
        microsoft_source.updatedate = datetime.datetime.now()
        microsoft_source.manuallyadded = True
        microsoft_source.snmpstatus = False
        microsoft_source.status = "A"
        microsoft_source.scanstatus = 5  # adding to staging area in first add operation with 5 and not logging

        microsoft_source.syslogtag = request.POST.get('tag') if check_existence(request.POST.get('tag')) else None
        microsoft_source.taglocation = request.POST.get('taglocation') if check_existence(
            request.POST.get('taglocation')) else None

        if (microsoft_source.ipaddress, microsoft_source.syslogtag) in ipAndTaglist:
            warning = "There is another log source with same ip & tag"
            logger.info(warning)
            context = {
                'route': route, 'customNameList': customNameList, 'ipAndTaglist': ipAndTaglistForJS,
                'monitorProfileDetailList': monitorProfileDetailList, 'warning': warning,
                'parserProfileList': parserProfileList, 'monitorProfileList': monitorProfileList,
                'ingestionProfileList': ingestionProfileList,
                'identifierList': identifierList,
                'locationProfileList': locationProfileList,
                'vendorName': vendorName, 'modelList': modelList, 'versionList': versionList,
            }
            # memory usage logging with memory_tracer
            try:
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return render(request, 'AgentRoot/add_log_sources.html', context)

        try:
            microsoft_source.save()
            template_message_show(request, "success", f"{route} saved successfully")
            # memory usage logging with memory_tracer
            try:
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('add_log_sources')
        except psycopg2.errors.UniqueViolation:
            template_message_show(request, "error", f"{route} failed to save because of uniqueid already exist")
        except Exception as err:
            logger.exception(f"An error occurred when trying to add new log source by manually ERROR IS : {err}")

    context = {
        'route': route,
        'customNameList': customNameList, 'ipAndTaglist': ipAndTaglistForJS,
        'monitorProfileDetailList': monitorProfileDetailList, 'monitorProfileList': monitorProfileList,
        'parserProfileList': parserProfileList,
        'ingestionProfileList': ingestionProfileList,
        'identifierList': identifierList,
        'locationProfileList': locationProfileList,
        'vendorName': vendorName, 'modelList': modelList, 'versionList': versionList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_log_sources.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_linuxserver(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'linuxserver'
    identifierList = [{'name': 'Custom Name', 'value': 'customname'}]
    customNameList = list(LogSources.objects.values_list('customname', flat=True).exclude(customname__isnull=True))
    # if a uniqueid left from the past including any uppercase chars convert them to lower case
    customNameList = [_.lower() for _ in customNameList]
    monitorProfileList = list(MonitorProfile.objects.filter(Q(monitorprofiletype__icontains="LINUX") | Q(monitorprofiletype__icontains="ICMP")))

    # markid ?
    # linuxMarkId = 1905001
    linuxMarkId = 0
    vendorName = "LINUX"
    try:
        linuxMarkRows = DeviceMark.objects.filter(markname=vendorName)
        if linuxMarkRows:
            linuxMarkId = linuxMarkRows[0].id
            logger.debug(f"devicemark id for {vendorName} is : {linuxMarkId}")
        else:
            logger.warning(f"There is no record in devicemark for vendor {vendorName}.")
            exceptionalWarn = f"Probably you need to load log source driver for {vendorName}"
            try:
                # memory usage logging with memory_tracer
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return render(request, 'exceptions.html', {'route': route, 'warning': exceptionalWarn})
    except Exception as err:
        logger.exception(f"An error occurred trying to get devicemark for vendor {vendorName}. ERROR IS : {err}")
        exceptionalWarn = f"Some exceptional cases occurred for {vendorName}"
        try:
            # memory usage logging with memory_tracer
            top_stats = tracemalloc.take_snapshot().statistics('lineno')
            total_size, unit = take_memory_usage(top_stats)
            logger.info(f"Memory allocation  {total_size} {unit}")
            memory_tracer.info(f"{total_size}")
            tracemalloc.stop()
        except:
            logger.debug("tracemalloc stopped before somehow")
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return render(request, 'exceptions.html', {'route': route, 'warning': exceptionalWarn})

    modelList = [{'name': _.modelname, 'value': _.id, 'devicetype': _.devicetype} for _ in DeviceModel.objects.filter(brand_id=linuxMarkId)]
    versionList = [{'name': _.versioncode, 'value': _.id, 'devicetype': _.devicetype} for _ in DeviceVersions.objects.filter(Q(devicetype__icontains="Server"))]
    # deviceTypeList = [{'name': _.devicetype, 'value': _.devicetypecode} for _ in DeviceTypeList.objects.all()]

    # to control ip an tag unique together in this view!!
    ipAndTaglist = [(_.ipaddress, _.syslogtag) for _ in LogSources.objects.all()]
    ipAndTaglistForJS = []
    for _ in LogSources.objects.all():
        _ip = _.ipaddress
        _tag = _.syslogtag if _.syslogtag else ""
        ipAndTaglistForJS.append({"ipaddress": _ip, "syslogtag": _tag})
    # logger.debug(f"{monitorProfileList}")
    if len(monitorProfileList) > 0:
        monitorProfileDetailList = monitorProfileList[0].get_profile_details()
    else:
        monitorProfileDetailList = []
    parserProfileList = [{'name': _.parsername, 'value': _.id} for _ in DeviceParserProfile.objects.all()]
    locationProfileList = [{'name': _.locationname, 'value': _.id} for _ in DevLocations.objects.all()]
    ingestionProfileList = [{'name': _.ingestionprofilename, 'value': _.id} for _ in IngestionProfile.objects.all()]

    if request.method == "POST":
        logger.debug(f"{request.POST}")
        """
        'ip_address': [''], *
        'unique_identifier': ['customname'], *
        'custom_name': [''], *
        'log_source_name': [''], *
        'monitor_profile_details': ['0'], *
        'parser_profile': ['0'], *
        'location_profile': ['0'], *
        'ingestion_profile': ['0'], *
        'before_tag': [''], 'tag': [''], 'after_tag': ['']  *
        'vendor': []
        'modelid': [1],
        'deviceverid': [2],
        'devicetype': [2],

        ????????????????????????????????????????????
        # these are monitorprofiledetails parts
        # 'dbusername': ['istiklal'], 
        # 'dbname': [''], 
        # 'dbpass': ['Zek'], 
        # 'dbport': [''], 
        # 'query_to_send': [''], 
        # 'response_to_receive': [''], 
        # 'response_to_down': [''], 
        """

        linux_source = LogSources()
        linux_source.logsourceselection = route
        linux_source.devicetype = "Linux Server"
        linux_source.markid = linuxMarkId  # ?????????????????????????
        # linux_source.modelid = int(request.POST.get('modelid')) if request.POST.get('modelid') and request.POST.get('modelid') != "0" else None
        linux_source.modelid = int(request.POST.get('modelid')) if request.POST.get('modelid') else None
        # linux_source.deviceverid = int(request.POST.get('deviceverid')) if request.POST.get('deviceverid') and request.POST.get('deviceverid') != "0" else None
        linux_source.deviceverid = int(request.POST.get('deviceverid')) if request.POST.get('deviceverid') else None
        linux_source.monitorprofile = int(request.POST.get('monitor_profile_details')) if check_existence(
            request.POST.get('monitor_profile_details')) and request.POST.get(
            'monitor_profile_details') != "0" else None
        linux_source.ipaddress = edit_ip_address_from_string(request.POST.get('ip_address'))
        linux_source.uniqueidtype = request.POST.get('unique_identifier')
        linux_source.customname = (request.POST.get('custom_name')).lower()
        linux_source.uniqueid = (request.POST.get('custom_name')).lower()
        linux_source.sourcename = request.POST.get('log_source_name')
        linux_source.parserprofile = int(request.POST.get('parser_profile')) if request.POST.get(
            'parser_profile') and request.POST.get('parser_profile') != "0" else None
        linux_source.locationprofile = int(request.POST.get('location_profile')) if request.POST.get(
            'location_profile') and request.POST.get('location_profile') != "0" else None
        linux_source.ingestionprofile = int(request.POST.get('ingestion_profile')) if request.POST.get(
            'ingestion_profile') and request.POST.get('ingestion_profile') != "0" else None
        linux_source.creationdate = datetime.datetime.now()
        linux_source.updatedate = datetime.datetime.now()
        linux_source.manuallyadded = True
        linux_source.snmpstatus = False
        linux_source.status = "A"
        linux_source.scanstatus = 5  # adding to staging area in first add operation with 5 and not logging

        linux_source.syslogtag = request.POST.get('tag') if check_existence(request.POST.get('tag')) else None
        linux_source.taglocation = request.POST.get('taglocation') if check_existence(
            request.POST.get('taglocation')) else None

        if (linux_source.ipaddress, linux_source.syslogtag) in ipAndTaglist:
            warning = "There is another log source with same ip & tag"
            logger.info(warning)
            context = {
                'route': route, 'customNameList': customNameList, 'ipAndTaglist': ipAndTaglistForJS,
                'monitorProfileDetailList': monitorProfileDetailList, 'warning': warning,
                'parserProfileList': parserProfileList, 'monitorProfileList': monitorProfileList,
                'ingestionProfileList': ingestionProfileList,
                'identifierList': identifierList,
                'locationProfileList': locationProfileList,
                'vendorName': vendorName, 'modelList': modelList, 'versionList': versionList,
            }
            # memory usage logging with memory_tracer
            try:
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return render(request, 'AgentRoot/add_log_sources.html', context)

        try:
            linux_source.save()
            template_message_show(request, "success", f"{route} saved successfully")
            # memory usage logging with memory_tracer
            try:
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('add_log_sources')
        except psycopg2.errors.UniqueViolation:
            template_message_show(request, "error", f"{route} failed to save because of uniqueid already exist")
        except Exception as err:
            logger.exception(f"An error occurred when trying to add new log source by manually ERROR IS : {err}")

    context = {
        'route': route,
        'customNameList': customNameList, 'ipAndTaglist': ipAndTaglistForJS,
        'monitorProfileDetailList': monitorProfileDetailList, 'monitorProfileList': monitorProfileList,
        'parserProfileList': parserProfileList,
        'ingestionProfileList': ingestionProfileList,
        'identifierList': identifierList,
        'locationProfileList': locationProfileList,
        'vendorName': vendorName, 'modelList': modelList, 'versionList': versionList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_log_sources.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_elastic(request):
    """
    This function will be work like nginx, because elasticsearch is communicate with http like nginx
    writen on 15/10/2021
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'elasticsearch'
    # -----------------------------------------------------------------------------------------------------
    identifierList = [{'name': 'Custom Name', 'value': 'customname'}]
    customNameList = list(LogSources.objects.values_list('customname', flat=True).exclude(customname__isnull=True))
    # if a uniqueid left from the past including any uppercase chars convert them to lower case
    customNameList = [_.lower() for _ in customNameList]
    monitorProfileList = list(MonitorProfile.objects.filter(monitorprofiletype="HTTP"))

    # to control ip an tag unique together in this view!!
    ipAndTaglist = [(_.ipaddress, _.syslogtag) for _ in LogSources.objects.all()]
    ipAndTaglistForJS = []
    for _ in LogSources.objects.all():
        _ip = _.ipaddress
        _tag = _.syslogtag if _.syslogtag else ""
        ipAndTaglistForJS.append({"ipaddress": _ip, "syslogtag": _tag})

    if len(monitorProfileList) > 0:
        monitorProfileDetailList = monitorProfileList[0].get_profile_details()
    else:
        monitorProfileDetailList = []
    parserProfileList = [{'name': _.parsername, 'value': _.id} for _ in DeviceParserProfile.objects.all()]
    locationProfileList = [{'name': _.locationname, 'value': _.id} for _ in DevLocations.objects.all()]
    ingestionProfileList = [{'name': _.ingestionprofilename, 'value': _.id} for _ in IngestionProfile.objects.all()]

    if request.method == "POST":
        logger.debug(f"{request.POST}")
        """
        'ip_address': [''], *
        'unique_identifier': ['customname'], *
        'custom_name': [''], *
        'log_source_name': [''], *
        'monitor_profile_details': ['0'], *
        'parser_profile': ['0'], *
        'location_profile': ['0'], *
        'ingestion_profile': ['0'], *
        'syslog_tag': [''], *
        'taglocation': [''] *

        # these are monitorprofiledetails parts
        # 'httpurl': [''], 
        # 'httpuri': [''], 
        # 'httpsecure': ['on'], we can see this value only if the box is checked 
        # 'httpmethod': ['GET'], 
        # 'httpport': [''], 
        # 'request_to_send': [''], 
        # 'response_to_receive': [''], 
        # 'response_to_down': [''], 
        """
        elastic_source = LogSources()
        elastic_source.logsourceselection = route
        elastic_source.markid = 1903003
        elastic_source.modelid = 1903003
        elastic_source.deviceverid = 1903003
        elastic_source.monitorprofile = int(request.POST.get('monitor_profile_details')) if check_existence(
            request.POST.get('monitor_profile_details')) and request.POST.get(
            'monitor_profile_details') != "0" else None
        elastic_source.ipaddress = edit_ip_address_from_string(request.POST.get('ip_address'))
        elastic_source.uniqueidtype = request.POST.get('unique_identifier')
        elastic_source.customname = (request.POST.get('custom_name')).lower()
        elastic_source.uniqueid = (request.POST.get('custom_name')).lower()
        elastic_source.sourcename = request.POST.get('log_source_name')
        elastic_source.parserprofile = int(request.POST.get('parser_profile')) if request.POST.get(
            'parser_profile') and request.POST.get('parser_profile') != "0" else None
        elastic_source.locationprofile = int(request.POST.get('location_profile')) if request.POST.get(
            'location_profile') and request.POST.get('location_profile') != "0" else None
        elastic_source.ingestionprofile = int(request.POST.get('ingestion_profile')) if request.POST.get(
            'ingestion_profile') and request.POST.get('ingestion_profile') != "0" else None
        elastic_source.creationdate = datetime.datetime.now()
        elastic_source.updatedate = datetime.datetime.now()
        elastic_source.manuallyadded = True
        elastic_source.snmpstatus = False
        elastic_source.scanstatus = 5  # adding to staging area in first add operation with 5 and not logging
        elastic_source.syslogtag = request.POST.get('tag') if check_existence(request.POST.get('tag')) else None
        elastic_source.taglocation = request.POST.get('taglocation') if check_existence(
            request.POST.get('taglocation')) else None

        if (elastic_source.ipaddress, elastic_source.syslogtag) in ipAndTaglist:
            warning = "There is another log source with same ip & tag"
            logger.info(f"{warning}")
            context = {
                'route': route, 'customNameList': customNameList, 'ipAndTaglist': ipAndTaglistForJS,
                'monitorProfileDetailList': monitorProfileDetailList, 'warning': warning,
                'parserProfileList': parserProfileList,
                'ingestionProfileList': ingestionProfileList,
                'identifierList': identifierList,
                'locationProfileList': locationProfileList,
            }
            # memory usage logging with memory_tracer
            try:
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return render(request, 'AgentRoot/add_log_sources.html', context)

        try:
            elastic_source.save()
            template_message_show(request, "success", f"{route} saved successfully")
            # memory usage logging with memory_tracer
            try:
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect('add_log_sources')
        except psycopg2.errors.UniqueViolation:
            template_message_show(request, "error",
                                  f"{route} failed to save because of uniqueid already exist")
        except Exception as err:
            logger.exception(f"An error occurred when trying to add new log source by manually ERROR IS : {err}")

    # -----------------------------------------------------------------------------------------------------
    context = {
        'route': route,
        'customNameList': customNameList, 'ipAndTaglist': ipAndTaglistForJS,
        'monitorProfileDetailList': monitorProfileDetailList,
        'parserProfileList': parserProfileList,
        'ingestionProfileList': ingestionProfileList,
        'identifierList': identifierList,
        'locationProfileList': locationProfileList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_log_sources.html', context)


# @licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def edit_log_source(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'logsource'
    warning = ""
    uniqueidList = list(LogSources.objects.values_list('uniqueid', flat=True).exclude(id=id))
    # if a uniqueid left from the past including any uppercase chars convert them to lower case
    uniqueidList = [_.lower() for _ in uniqueidList]
    # to control ip an tag unique together in this view. it's important to right mapping!!
    ipAndTaglist = [(_.ipaddress, _.syslogtag) for _ in list(LogSources.objects.exclude(id=id))]
    ipAndTaglistForJS = []
    for _ in list(LogSources.objects.exclude(id=id)):
        _ip = _.ipaddress
        _tag = _.syslogtag if _.syslogtag else ""
        ipAndTaglistForJS.append({"ipaddress": _ip, "syslogtag": _tag})
    # ipsOfNetworkDevices = [_.ipaddress for _ in list(LogSources.objects.filter(logsourceselection="networkdevice").exclude(id=id).exclude(scanstatus=9))]
    ipsOfNetworkDevices = list(LogSources.objects.values_list('ipaddress', flat=True).filter(logsourceselection="networkdevice").exclude(id=id).exclude(scanstatus=9))
    try:
        log_source = LogSources.objects.get(id=id)
        if log_source.uniqueid is None or getattr(log_source, log_source.uniqueidtype) != log_source.uniqueid:
            warning = f"{log_source.uniqueidtype} data is different from unique identifier data"
            if log_source.uniqueid is None:
                warning = f"Unique identifier can not be empty to start collecting logs !"
                log_source.uniqueid = getattr(log_source, log_source.uniqueidtype) if getattr(log_source, log_source.uniqueidtype) else None
    except ObjectDoesNotExist:
        try:
            # memory usage logging with memory_tracer
            top_stats = tracemalloc.take_snapshot().statistics('lineno')
            total_size, unit = take_memory_usage(top_stats)
            logger.info(f"Memory allocation  {total_size} {unit}")
            memory_tracer.info(f"{total_size}")
            tracemalloc.stop()
        except:
            logger.debug("tracemalloc stopped before somehow")
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return redirect('log_sources')

    _current_scanstatus = log_source.scanstatus

    monitorProfileList, deviceTypeList, markList, modelList, versionList = [], [], [], [], []

    if log_source.isEditable():

        if log_source.logsourceselection == "networkdevice":
            monitorProfileList = list(MonitorProfileDetails.objects.filter(
                monitorProfile_id=MonitorProfile.objects.get(monitorprofiletype="SNMP")))
            # deviceTypeList = list(set([_.devicetypecode for _ in DeviceTypeList.objects.all()]))
            # deviceTypeList = list(set(list(DeviceTypeList.objects.values_list('devicetypecode', flat=True))))
            markList = [{'name': _.markname, 'value': _.id} for _ in DeviceMark.objects.all()]
            modelList = [{'name': _.modelname, 'value': _.id, 'markid': _.brand_id, 'devicetype': _.devicetype}
                         for _ in DeviceModel.objects.all()]
            versionList = [{'name': _.versioncode, 'value': _.id, 'devicetype': _.devicetype} for _ in
                           DeviceVersions.objects.all()]

        elif log_source.logsourceselection == "nginx":
            monitorProfileList = list(MonitorProfileDetails.objects.filter(
                monitorProfile_id=MonitorProfile.objects.get(monitorprofiletype="HTTP")))

        elif log_source.logsourceselection == "postgresql":
            monitorProfileList = list(MonitorProfileDetails.objects.filter(
                monitorProfile_id=MonitorProfile.objects.get(monitorprofiletype="POSTGRESQL")))

        elif log_source.logsourceselection == "microsoftserver":
            monitorProfileList = list(MonitorProfileDetails.objects.filter(
                monitorProfile_id=MonitorProfile.objects.get(monitorprofiletype="ICMP")))
            # deviceTypeList = list(set([_.devicetypecode for _ in DeviceTypeList.objects.all()]))
            # deviceTypeList = list(set(list(DeviceTypeList.objects.values_list('devicetypecode', flat=True))))
            markList = [{'name': _.markname, 'value': _.id}
                        for _ in DeviceMark.objects.all() if _.id == log_source.markid]
            modelList = [{'name': _.modelname, 'value': _.id, 'markid': _.brand_id, 'devicetype': _.devicetype}
                         for _ in DeviceModel.objects.all() if _.brand_id == log_source.markid]
            versionList = [{'name': _.versioncode, 'value': _.id, 'devicetype': _.devicetype} for _ in
                           DeviceVersions.objects.all()]

        elif log_source.logsourceselection == "linuxserver":
            monitorProfileList = list(MonitorProfileDetails.objects.filter(
                monitorProfile_id=MonitorProfile.objects.get(monitorprofiletype="ICMP")))
            # deviceTypeList = list(set([_.devicetypecode for _ in DeviceTypeList.objects.all()]))
            # deviceTypeList = list(set(list(DeviceTypeList.objects.values_list('devicetypecode', flat=True))))
            markList = [{'name': _.markname, 'value': _.id}
                        for _ in DeviceMark.objects.all() if _.id == log_source.markid]
            modelList = [{'name': _.modelname, 'value': _.id, 'markid': _.brand_id, 'devicetype': _.devicetype}
                         for _ in DeviceModel.objects.all() if _.brand_id == log_source.markid]
            versionList = [{'name': _.versioncode, 'value': _.id, 'devicetype': _.devicetype} for _ in
                           DeviceVersions.objects.all()]

        else:
            monitorProfileList = MonitorProfile.objects.all()

    else:
        route = 'noedit'

    # if log_source.syslogtag or log_source.taglocation:
    #     _str = log_source.taglocation if log_source.taglocation and log_source.taglocation != "" else "(?<=)(.*)(?=)"
    #     # log_source.taglocation = f"(?<={request.POST.get('before_tag')})(.*)(?={request.POST.get('after_tag')})"
    #     before_tag = _str[_str.index("=")+1:_str.index(")")]
    #     after_tag = _str[_str.index("?=")+2:len(_str)-1]
    # else:
    #     before_tag, after_tag = "", ""

    parserProfileList = [{'name': _.parsername, 'value': _.id} for _ in DeviceParserProfile.objects.all()]
    locationProfileList = [{'name': _.locationname, 'value': _.id} for _ in DevLocations.objects.all()]
    ingestionProfileList = [{'name': _.ingestionprofilename, 'value': _.id} for _ in IngestionProfile.objects.all()]

    if request.method == "POST":
        logger.debug(f"{request.POST}")
        """
        {'ipaddress': ['192.168.1.60'], *
        'monitorprofile': ['1'], *
        'parserprofile': ['0'], *
        'locationprofile': ['0'], *
        'ingestionprofile': ['0'], *
        'markid': ['2'], *
        'devicetype': ['SWITCH'], *
        'modelid': ['48'], *
        'deviceverid': ['24'], *
        'taglocation': ['']
        'syslogtag': [''], 
        'scanstatus': ['']}>
        """

        # logger.info(f"log source scanstatus changed as {request.POST.get('scanstatus')}")
        # log_source.scanstatus = 0 if check_existence(request.POST.get("scanstatus")) else log_source.scanstatus
        _uniqueid = (request.POST.get("uniqueid")).lower() if check_existence(request.POST.get("uniqueid")) else None
        # if request.POST.get("scanstatus"):
        #     _updt = LogSources.objects.filter(id=id).update(scanstatus=0)
        #     if _updt != 0:
        #         logger.debug(f"{_updt} record updated")

        if log_source.logsourceselection == "networkdevice":
            if check_existence(request.POST.get("ipaddress")):
                if edit_ip_address_from_string(request.POST.get("ipaddress")) in ipsOfNetworkDevices:
                    warning = f"There is another network device on {edit_ip_address_from_string(request.POST.get('ipaddress'))} ip address !!"
                    logger.info(warning)
                    context = {
                        'route': route, 'warning': warning, 'source': log_source,
                        'markList': markList, 'modelList': modelList,
                        'versionList': versionList,
                        'monitorProfileList': monitorProfileList,
                        'parserProfileList': parserProfileList, 'locationProfileList': locationProfileList,
                        'ingestionProfileList': ingestionProfileList, 'uniqueidList': uniqueidList,
                        'ipsOfNetworkDevices': ipsOfNetworkDevices,
                    }
                    try:
                        # memory usage logging with memory_tracer
                        top_stats = tracemalloc.take_snapshot().statistics('lineno')
                        total_size, unit = take_memory_usage(top_stats)
                        logger.info(f"Memory allocation  {total_size} {unit}")
                        memory_tracer.info(f"{total_size}")
                        tracemalloc.stop()
                    except:
                        logger.debug("tracemalloc stopped before somehow")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return render(request, 'AgentRoot/edit.html', context)
            elif log_source.ipaddress in ipsOfNetworkDevices:
                if edit_ip_address_from_string(request.POST.get("ipaddress")) in ipsOfNetworkDevices:
                    warning = f"There is another network device on {edit_ip_address_from_string(request.POST.get('ipaddress'))} ip address !!"
                    logger.info(warning)
                    context = {
                        'route': route, 'warning': warning, 'source': log_source,
                        'markList': markList, 'modelList': modelList,
                        'versionList': versionList,
                        'monitorProfileList': monitorProfileList,
                        'parserProfileList': parserProfileList, 'locationProfileList': locationProfileList,
                        'ingestionProfileList': ingestionProfileList, 'uniqueidList': uniqueidList,
                        'ipsOfNetworkDevices': ipsOfNetworkDevices,
                    }
                    try:
                        # memory usage logging with memory_tracer
                        top_stats = tracemalloc.take_snapshot().statistics('lineno')
                        total_size, unit = take_memory_usage(top_stats)
                        logger.info(f"Memory allocation  {total_size} {unit}")
                        memory_tracer.info(f"{total_size}")
                        tracemalloc.stop()
                    except:
                        logger.debug("tracemalloc stopped before somehow")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return render(request, 'AgentRoot/edit.html', context)

        if log_source.logsourceselection == "networkdevice" and (int(request.POST.get("markid")) == 0 or
                                                                 int(request.POST.get("modelid")) == 0 or
                                                                 int(request.POST.get("deviceverid")) == 0):
            warning = "You have to chose brand, model and verison. If the appropriate information for your device is " \
                      "not in lists, please contact us to install the driver for this version"
            logger.info(warning)
            context = {
                'route': route, 'warning': warning, 'source': log_source,
                'markList': markList, 'modelList': modelList,
                'versionList': versionList,
                'monitorProfileList': monitorProfileList,
                'parserProfileList': parserProfileList, 'locationProfileList': locationProfileList,
                'ingestionProfileList': ingestionProfileList, 'uniqueidList': uniqueidList,
                'ipsOfNetworkDevices': ipsOfNetworkDevices,
            }
            try:
                # memory usage logging with memory_tracer
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return render(request, 'AgentRoot/edit.html', context)

        if log_source.scanstatus in [2, "2"]:

            if _uniqueid is None or _uniqueid in uniqueidList or check_special_chars(_uniqueid):
                if _uniqueid is None and log_source.uniqueid is None:
                    warning = f"Unique identifier can not be empty !"
                    logger.info(warning)
                elif _uniqueid is not None and _uniqueid in uniqueidList:
                    warning = f"Unique identifier can not be same with another to start collecting logs !"
                    logger.info(warning)
                elif _uniqueid is not None and check_special_chars(_uniqueid):
                    warning = f"Unique identifier can not contain special chars !"
                    logger.info(warning)
                context = {
                    'route': route, 'warning': warning, 'source': log_source,
                    'markList': markList, 'modelList': modelList,
                    'versionList': versionList,
                    'monitorProfileList': monitorProfileList,
                    'parserProfileList': parserProfileList, 'locationProfileList': locationProfileList,
                    'ingestionProfileList': ingestionProfileList, 'uniqueidList': uniqueidList,
                    'ipsOfNetworkDevices': ipsOfNetworkDevices,
                }
                try:
                    # memory usage logging with memory_tracer
                    top_stats = tracemalloc.take_snapshot().statistics('lineno')
                    total_size, unit = take_memory_usage(top_stats)
                    logger.info(f"Memory allocation  {total_size} {unit}")
                    memory_tracer.info(f"{total_size}")
                    tracemalloc.stop()
                except:
                    logger.debug("tracemalloc stopped before somehow")
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return render(request, 'AgentRoot/edit.html', context)

        elif log_source.scanstatus in [1, 3] and log_source.uniqueidtype != "ipaddress":

            if not check_existence(request.POST.get("ipaddress")):
                warning = "You can not pass ip address field blank !!"
                logger.info(warning)
                context = {
                    'route': route, 'warning': warning, 'source': log_source,
                    'markList': markList, 'modelList': modelList,
                    'versionList': versionList,
                    'monitorProfileList': monitorProfileList,
                    'parserProfileList': parserProfileList, 'locationProfileList': locationProfileList,
                    'ingestionProfileList': ingestionProfileList, 'uniqueidList': uniqueidList,
                    'ipsOfNetworkDevices': ipsOfNetworkDevices,
                }
                try:
                    # memory usage logging with memory_tracer
                    top_stats = tracemalloc.take_snapshot().statistics('lineno')
                    total_size, unit = take_memory_usage(top_stats)
                    logger.info(f"Memory allocation  {total_size} {unit}")
                    memory_tracer.info(f"{total_size}")
                    tracemalloc.stop()
                except:
                    logger.debug("tracemalloc stopped before somehow")
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return render(request, 'AgentRoot/edit.html', context)

        logger.info(f"log source scanstatus changed as {request.POST.get('scanstatus')}")

        log_source.scanstatus = 0 if check_existence(request.POST.get("scanstatus")) else log_source.scanstatus

        log_source.uniqueid = _uniqueid if check_existence(_uniqueid) and _uniqueid != log_source.uniqueid else log_source.uniqueid
        # log_source.customname = log_source.uniqueid if log_source.uniqueidtype == "customname" else log_source.customname
        setattr(log_source, log_source.uniqueidtype, log_source.uniqueid)
        log_source.ipaddress = edit_ip_address_from_string(request.POST.get("ipaddress")) if check_existence(request.POST.get("ipaddress")) else log_source.ipaddress
        log_source.monitorprofile = int(request.POST.get("monitorprofile")) if int(request.POST.get("monitorprofile")) != log_source.monitorprofile else log_source.monitorprofile
        log_source.parserprofile = int(request.POST.get("parserprofile")) if int(request.POST.get("parserprofile")) != log_source.parserprofile else log_source.parserprofile
        log_source.locationprofile = int(request.POST.get("locationprofile")) if int(request.POST.get("locationprofile")) != log_source.locationprofile else log_source.locationprofile
        log_source.ingestionprofile = int(request.POST.get("ingestionprofile")) if int(request.POST.get("ingestionprofile")) != log_source.ingestionprofile else log_source.ingestionprofile
        # log_source.devicetype = request.POST.get("devicetype") if request.POST.get("devicetype") != log_source.devicetype else log_source.devicetype
        log_source.devicetype = DeviceModel.objects.get(id=int(request.POST.get("modelid"))).devicetype if check_existence(request.POST.get("modelid")) and int(request.POST.get("modelid")) != log_source.modelid else log_source.devicetype
        log_source.markid = int(request.POST.get("markid")) if check_existence(request.POST.get("markid")) and int(request.POST.get("markid")) != log_source.markid else log_source.markid
        log_source.modelid = int(request.POST.get("modelid")) if check_existence(request.POST.get("modelid")) and int(request.POST.get("modelid")) != log_source.modelid else log_source.modelid
        log_source.deviceverid = int(request.POST.get("deviceverid")) if check_existence(request.POST.get("deviceverid")) and int(request.POST.get("deviceverid")) != log_source.deviceverid else log_source.deviceverid
        log_source.updatedate = datetime.datetime.now()
        # log_source.manuallyadded = True

        if check_existence(request.POST.get("tag")):
            log_source.syslogtag = request.POST.get("tag") if request.POST.get("tag") != log_source.syslogtag else log_source.syslogtag
            log_source.taglocation = request.POST.get("taglocation") if request.POST.get("taglocation") != log_source.taglocation else log_source.taglocation
        else:
            log_source.syslogtag = None
            log_source.taglocation = None

        # log_source.syslogtag = request.POST.get("tag") if check_existence(request.POST.get("tag")) and request.POST.get("tag") != log_source.syslogtag else log_source.syslogtag
        # log_source.taglocation = request.POST.get("taglocation") if check_existence(request.POST.get("taglocation")) and request.POST.get("taglocation") != log_source.taglocation else log_source.taglocation

        if (log_source.ipaddress, log_source.syslogtag) in ipAndTaglist:
            warning = "There is another log source with same ip & tag"
            logger.info(warning)
            context = {
                'route': route, 'warning': warning, 'source': log_source,
                'markList': markList, 'modelList': modelList,
                'versionList': versionList,
                'monitorProfileList': monitorProfileList,
                'parserProfileList': parserProfileList, 'locationProfileList': locationProfileList,
                'ingestionProfileList': ingestionProfileList, 'uniqueidList': uniqueidList,
                'ipsOfNetworkDevices': ipsOfNetworkDevices,
            }
            try:
                # memory usage logging with memory_tracer
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
            except:
                logger.debug("tracemalloc stopped before somehow")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return render(request, 'AgentRoot/edit.html', context)

        try:
            log_source.save()
            if check_existence(request.POST.get("scanstatus")) and _current_scanstatus == log_source.scanstatus:
                template_message_show(
                    request,
                    'error',
                    'Could not be activated because your license for this log source has been exceeded.')
                template_message_show(request, 'success', 'Other changes successfully saved')
                logger.info(f"Could not be activated because license for this log source has been exceeded id : {id}")
            else:
                template_message_show(request, 'success', 'Successfully edited')
                logger.info(f"Successfully edited id : {id}")
        except Exception as err:
            logger.exception(f"An error occurred in edit_log_source view while trying to save. ERROR IS : {err}")
            template_message_show(request, 'error', "Changes couldn't be saved !")

    context = {
        'route': route, 'warning': warning, 'source': log_source, 'ipAndTaglist': ipAndTaglistForJS,
        'markList': markList, 'modelList': modelList, 'versionList': versionList,
        'monitorProfileList': monitorProfileList,
        'parserProfileList': parserProfileList, 'locationProfileList': locationProfileList,
        'ingestionProfileList': ingestionProfileList, 'uniqueidList': uniqueidList,
        'ipsOfNetworkDevices': ipsOfNetworkDevices,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/edit.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def edit_component(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'component'
    warning = None
    component = None
    logSources = []
    componentNames = []
    try:
        component = Components.objects.get(id=id)
        logSources = list(LogSources.objects.filter(connectedmac__isnull=True).filter(Q(scanstatus__in=[0]) | Q(scanstatus__isnull=True)).distinct())
        componentNames = list(Components.objects.values_list('componentname', flat=True).exclude(id=id))
    except ObjectDoesNotExist:
        logger.warning(f"No Component with id : {id}")
    except Exception as err:
        logger.exception(f"An error occurred trying to get component with id {id}. ERROR IS : {err}")

    if component:
        if request.method == 'POST':
            """
            
            """
            sourceIds = [int(_) for _ in request.POST.getlist('id_list')]
            logger.debug(f"{request.POST}")
            if request.POST.get('component_name') != component.componentname:
                if request.POST.get('component_name') in componentNames:
                    warning = f"Component name '{request.POST.get('component_name')}' is already in use"
                else:
                    component.componentname = request.POST.get('component_name')
                    try:
                        component.save()
                        logger.debug(f"Component name changed")
                        template_message_show(request, "success", f"Component name successfully changed")
                    except Exception as err:
                        template_message_show(request, "error", f"Failed to save component name. {err}")
            else:
                template_message_show(request, "info", "Nothing changed in component name")
                logger.debug(f"Nothing changed in component name")

            existingIds = [_.id for _ in component.get_log_sources()]
            addedIds = list(set(sourceIds).difference(set(existingIds)))
            extractedIds = list(set(existingIds).difference(set(sourceIds)))
            logger.debug(f"{component.componentname} added log sources : {addedIds}")
            logger.debug(f"{component.componentname} extracted log sources : {extractedIds}")
            _updt = 0
            if addedIds:
                try:
                    _updt += component.add_sources(addedIds)
                    logger.debug(f"{len(addedIds)} Sources added")
                    template_message_show(request, "success", f"{len(addedIds)} Sources added")
                except Exception as err:
                    logger.exception(f"Failed to add {component.id} to componentids. ERROR IS : {err}")
                    template_message_show(request, "error", f"Failed to add log sources to component. {err}")
            if extractedIds:
                try:
                    _updt += component.remove_sources(extractedIds)
                    logger.debug(f"{len(extractedIds)} Sources extracted")
                    template_message_show(request, "success", f"{len(extractedIds)} Sources extracted")
                except Exception as err:
                    logger.exception(f"Failed to remove {component.id} from componentids. ERROR IS : {err}")
                    template_message_show(request, "error", f"Failed to remove log sources from component. {err}")
            logger.debug(f"Total updated log sources count : {_updt}")

    # logger.debug(f"Name list : {list(Components.objects.values_list('componentname', flat=True).exclude(id=id))}")

    context = {
        'route': route, 'component': component, 'logSources': logSources, 'componentNames': componentNames,
        'warning': warning,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/edit.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def edit_application(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'application'
    application = None
    warning = None
    applicationNames = []
    componentList = []
    try:
        application = Applications.objects.get(id=id)
        # applicationNames = [_.appname for _ in Applications.objects.exclude(id=id)]
        applicationNames = list(Applications.objects.values_list('appname', flat=True).exclude(id=id))
        componentList = Components.objects.all()
    except ObjectDoesNotExist:
        logger.warning(f"Couldn't find application with id {id}")
    except Exception as err:
        logger.exception(f"An error occurred while trying to get application with id {id}. ERROR IS : {err}")

    if application:
        if request.method == 'POST':
            """
            'application_name'
            'component_ids'
            """
            logger.debug(f"{request.POST}")
            componentIds = [int(_) for _ in request.POST.getlist('component_ids')]
            if request.POST.get('application_name') != application.appname:
                if request.POST.get('application_name') in applicationNames:
                    warning = f"Application name '{request.POST.get('application_name')}' is already in use"
                else:
                    application.appname = request.POST.get('application_name')
                    try:
                        application.save()
                        logger.debug(f"Application name changed")
                        template_message_show(request, "success", f"Application name successfully changed")
                    except Exception as err:
                        template_message_show(request, "error", f"Failed to save application name. {err}")
            else:
                template_message_show(request, "info", "Nothing changed in application name")
                logger.debug(f"Nothing changed in application name")
            existingIds = [_.id for _ in application.get_components()]
            addedIds = list(set(componentIds).difference(set(existingIds)))
            extractedIds = list(set(existingIds).difference(set(componentIds)))
            logger.debug(f"{application.appname} added log sources : {addedIds}")
            logger.debug(f"{application.appname} extracted log sources : {extractedIds}")
            _updt = 0
            if addedIds:
                try:
                    _updt += application.add_components(addedIds)
                    logger.debug(f"{len(addedIds)} Components added")
                    template_message_show(request, "success", f"{len(addedIds)} Components added")
                except Exception as err:
                    logger.exception(f"Failed to add {application.id} to applicationids. ERROR IS : {err}")
                    template_message_show(request, "error", f"Failed to add component to application. {err}")
            if extractedIds:
                try:
                    _updt += application.remove_components(extractedIds)
                    logger.debug(f"{len(extractedIds)} Components extracted")
                    template_message_show(request, "success", f"{len(extractedIds)} Components extracted")
                except Exception as err:
                    logger.exception(f"Failed to remove {application.id} from applicationids. ERROR IS : {err}")
                    template_message_show(request, "error", f"Failed to remove component from application. {err}")
            logger.debug(f"Total updated components count : {_updt}")

    context = {
        'route': route, 'application': application, 'applicationNames': applicationNames,
        'componentList': componentList, 'warning': warning,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/edit.html', context)


@licence_required
@login_required
@csrf_exempt
def profiles(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "general"
    monitorProfileList = MonitorProfileDetails.objects.all()
    locationProfileList = DevLocations.objects.all()
    ingestionProfileList = IngestionProfile.objects.all()
    customParserList = DeviceParserProfile.objects.all()
    installedParserList = PParseFormulaCode.objects.all()

    ingestionProfileTypeCount = IngestionProfileType.objects.count()

    context = {
        'route': route,
        'monitorProfileList': monitorProfileList,
        'locationProfileList': locationProfileList,
        'ingestionProfileList': ingestionProfileList,
        'customParserList': customParserList,
        'installedParserList': installedParserList,
        'ingestionProfileTypeCount': ingestionProfileTypeCount,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/profiles.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def delete_profile(request, id, type):
    """
    working for monitor profiles for now !!
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    logger.debug(f"id : {id}  type : {type}")
    if type == "monitorprofiledetails":
        _profile = MonitorProfileDetails.objects.get(id=id)
        logger.debug(f"IS IN USE : {_profile.is_in_use()}")
        if not _profile.is_in_use():
            try:
                _profile.delete()
                template_message_show(request, "success", "Profile successfully deleted")
            except Exception as err:
                logger.exception(f"An error occurred in delete_profile view trying to delete {type} profile id {id}. ERROR IS : {err}")
                template_message_show(request, "error", "Failed to delete profile")
        else:
            logger.warning("Trying to delete a profile in use")
            template_message_show(request, "warning", "Profile is in use !!")
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return redirect('profiles')


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_monitor_profile(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "monitor"
    pageTitle = "New"
    purpose = "add"
    warning = ""

    # mpdNameList = [_.paramsname for _ in MonitorProfileDetails.objects.all()]
    mpdNameList = list(MonitorProfileDetails.objects.values_list('paramsname', flat=True))
    monitorProfileList = [{"value": _.id, "name": _.monitorprofiletype} for _ in MonitorProfile.objects.all()]

    if request.method == "POST":
        save_status = True
        new_monitor_profile_details = MonitorProfileDetails()

        new_monitor_profile_details.paramsname = request.POST.get("paramsname") if request.POST.get("paramsname") and request.POST.get("paramsname") != "" else None
        new_monitor_profile_details.monitorProfile_id = int(request.POST.get("monitorprofileid")) if request.POST.get("monitorprofileid") and request.POST.get("monitorprofileid") != "" else None

        try:
            _monitor_profile_type = MonitorProfile.objects.get(id=int(request.POST.get("monitorprofileid"))).monitorprofiletype
        except Exception as err:
            logger.exception(f"An exception occurred in add_monitor-profile view when trying to get MonitorProfile with id = {request.POST.get('monitorprofileid')} ERROR IS : {err}")
            _monitor_profile_type = ""
            save_status = False

        if _monitor_profile_type != "" and _monitor_profile_type == "SNMP":
            if not check_existence(request.POST.get("communitystring")):
                warning = "You can not pass Community String field blank when Monitor Profile Type SNMP !!"
                context = {
                    'route': route, 'warning': warning,
                    'monitorProfileList': monitorProfileList,
                    'mpdNameList': mpdNameList,
                }
                # memory usage logging with memory_tracer
                top_stats = tracemalloc.take_snapshot().statistics('lineno')
                total_size, unit = take_memory_usage(top_stats)
                logger.info(f"Memory allocation  {total_size} {unit}")
                memory_tracer.info(f"{total_size}")
                tracemalloc.stop()
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return render(request, 'AgentRoot/add_profile.html', context)
            new_monitor_profile_details.snmpversion = request.POST.get("snmpversion") if request.POST.get("snmpversion") and request.POST.get("snmpversion") != "" else None
            if check_existence(request.POST.get("snmpversion")) and request.POST.get("snmpversion") == "v3":
                if not check_existence(request.POST.get("snmpv3user")) or not check_existence(request.POST.get("snmpv3authpass")) or not check_existence(request.POST.get("snmpv3privacypass")):
                    warning = "You can not pass V3 Areas blank when SNMP Version selected v3 !!"
                    context = {
                        'route': route, 'warning': warning,
                        'monitorProfileList': monitorProfileList,
                        'mpdNameList': mpdNameList,
                    }
                    # memory usage logging with memory_tracer
                    top_stats = tracemalloc.take_snapshot().statistics('lineno')
                    total_size, unit = take_memory_usage(top_stats)
                    logger.info(f"Memory allocation  {total_size} {unit}")
                    memory_tracer.info(f"{total_size}")
                    tracemalloc.stop()
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return render(request, 'AgentRoot/add_profile.html', context)
            new_monitor_profile_details.snmpv3user = request.POST.get("snmpv3user") if request.POST.get("snmpv3user") and request.POST.get("snmpv3user") != "" else None
            new_monitor_profile_details.snmpv3authprotocol = request.POST.get("snmpv3authprotocol") if request.POST.get("snmpv3authprotocol") and request.POST.get("snmpv3authprotocol") != "" else None
            new_monitor_profile_details.snmpv3privacyprotocol = request.POST.get("snmpv3privacyprotocol") if request.POST.get("snmpv3privacyprotocol") and request.POST.get("snmpv3privacyprotocol") != "" else None
            try:
                # we use encode_with_java() for SNMP profile because java codes decodes this terms
                new_monitor_profile_details.communitystring = encode_with_java(request.POST.get("communitystring")) if request.POST.get("communitystring") and request.POST.get("communitystring") != "" else None
                new_monitor_profile_details.snmpv3authpass = encode_with_java(request.POST.get("snmpv3authpass")) if request.POST.get("snmpv3authpass") and request.POST.get("snmpv3authpass") != "" else None
                new_monitor_profile_details.snmpv3privacypass = encode_with_java(request.POST.get("snmpv3privacypass")) if request.POST.get("snmpv3privacypass") and request.POST.get("snmpv3privacypass") != "" else None
            except Exception as err:
                logger.exception(f"An error occurred in add_monitor_profile view while trying to reach java ERROR IS : {err}")
                save_status = False
        if _monitor_profile_type != "" and _monitor_profile_type in ["HTTP", "HTTPS"]:
            new_monitor_profile_details.httpmethod = request.POST.get("httpmethod") if request.POST.get("httpmethod") and request.POST.get("httpmethod") != "" else None
            new_monitor_profile_details.httpsecure = bool(int(request.POST.get("httpsecure"))) if request.POST.get("httpsecure") and request.POST.get("httpsecure") != "" else None
            new_monitor_profile_details.httpport = int(request.POST.get("httpport")) if request.POST.get("httpport") and request.POST.get("httpport") != "" else None
            new_monitor_profile_details.httpurl = request.POST.get("httpurl") if request.POST.get("httpurl") and request.POST.get("httpurl") != "" else None
            new_monitor_profile_details.httpuri = request.POST.get("httpuri") if request.POST.get("httpuri") and request.POST.get("httpuri") != "" else None

        if _monitor_profile_type != "" and _monitor_profile_type in ["SQL", "PSQL", "POSTGRESQL"]:
            new_monitor_profile_details.username = request.POST.get("username") if request.POST.get("username") and request.POST.get("username") != "" else None
            new_monitor_profile_details.dbasename = request.POST.get("dbasename") if request.POST.get("dbasename") and request.POST.get("dbasename") != "" else None
            new_monitor_profile_details.httpport = request.POST.get("dbaseport") if request.POST.get("dbaseport") and request.POST.get("dbaseport") != "" else None
            # we use atiba_encrypt() because it will be decoded in python codes
            new_monitor_profile_details.userpass = atiba_encrypt(request.POST.get("userpass")) if request.POST.get("userpass") and request.POST.get("userpass") != "" else None
        # if _monitor_profile_type is ICMP we don't need any if clause

        new_monitor_profile_details.querytosend = request.POST.get("querytosend") if request.POST.get("querytosend") and request.POST.get("querytosend") != "" else None
        new_monitor_profile_details.responsetoreceive = request.POST.get("responsetoreceive") if request.POST.get("responsetoreceive") and request.POST.get("responsetoreceive") != "" else None
        new_monitor_profile_details.responsetodown = request.POST.get("responsetodown") if request.POST.get("responsetodown") and request.POST.get("responsetodown") != "" else None

        if save_status:
            new_monitor_profile_details.save()
            template_message_show(request, 'success', 'Monitor profile is successfully saved')
        else:
            template_message_show(request, "error", "Monitor profile couldn't be saved")

    context = {
        'route': route, 'purpose': purpose, 'warning': warning, 'monitorProfileList': monitorProfileList,
        'mpdNameList': mpdNameList, 'pageTitle': pageTitle,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_profile.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def edit_monitor_profile(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "monitor"
    purpose = "edit"
    try:
        selectedMPD = MonitorProfileDetails.objects.get(id=id)
        mpdNameList = [_.paramsname for _ in MonitorProfileDetails.objects.all() if _.paramsname != selectedMPD.paramsname]
        monitorProfileList = [{"value": _.id, "name": _.monitorprofiletype} for _ in MonitorProfile.objects.all()]
        selectedMP = selectedMPD.monitorProfile
    except Exception as err:
        logger.exception(f"An error occurred while trying to get MonitorProfileDetails object. ERROR IS : {err}")
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return render(request, 'AgentRoot/add_profile.html', {'route': ""})
    pageTitle = f"Edit {selectedMPD.paramsname} Named "

    if request.method == "POST":
        logger.debug(f"{request.POST}")
        """
        'paramsname': ['digerNginx'], *
        'monitorprofileid': ['3'], *
        'communitystring': [''], *
        'snmpv3user': [''], *
        'snmpv3authpass': [''], *
        'snmpv3authprotocol': [''], *
        'snmpv3privacypass': [''], *
        'snmpv3privacyprotocol': [''], *
        'httpmethod': ['POST'], *
        'httpsecure': ['0'], *
        'httpport': ['8443'], *
        'httpurl': ['ht://www.camentasystem.com'], *
        'httpuri': ['/121'], *
        'username': [''], *
        'dbasename': [''], *
        'userpass': [''], *
        'dbaseport': [''], *
        'querytosend': [''], *
        'responsetoreceive': [''], *
        'responsetodown': [''] *
        """
        selectedMPD.paramsname = request.POST.get('paramsname') if check_existence(request.POST.get('paramsname')) and request.POST.get('paramsname') != selectedMPD.paramsname else selectedMPD.paramsname
        selectedMPD.monitorProfile_id = int(request.POST.get('monitorprofileid')) if check_existence(request.POST.get('monitorprofileid')) and int(request.POST.get('monitorprofileid')) != selectedMPD.monitorProfile_id else selectedMPD.monitorProfile_id
        try:
            selectedMPD.communitystring = encode_with_java(request.POST.get('communitystring')) if check_existence(request.POST.get('communitystring')) and request.POST.get('communitystring') != selectedMPD.communitystring else selectedMPD.communitystring
            selectedMPD.snmpv3authpass = encode_with_java(request.POST.get('snmpv3authpass')) if check_existence(request.POST.get('snmpv3authpass')) and request.POST.get('snmpv3authpass') != selectedMPD.snmpv3authpass else selectedMPD.snmpv3authpass
            selectedMPD.snmpv3privacypass = encode_with_java(request.POST.get('snmpv3privacypass')) if check_existence(request.POST.get('snmpv3privacypass')) and request.POST.get('snmpv3privacypass') != selectedMPD.snmpv3privacypass else selectedMPD.snmpv3privacypass
        except Exception as err:
            logger.exception(f"An error occurred while trying to call encode_with_java for mpdid = {id}. ERROR IS : {err}")
        selectedMPD.snmpv3user = request.POST.get('snmpv3user') if check_existence(request.POST.get('snmpv3user')) and request.POST.get('snmpv3user') != selectedMPD.snmpv3user else selectedMPD.snmpv3user
        selectedMPD.snmpv3authprotocol = request.POST.get('snmpv3authprotocol') if check_existence(request.POST.get('snmpv3authprotocol')) and request.POST.get('snmpv3authprotocol') != selectedMPD.snmpv3authprotocol else selectedMPD.snmpv3authprotocol
        selectedMPD.snmpv3privacyprotocol = request.POST.get('snmpv3privacyprotocol') if check_existence(request.POST.get('snmpv3privacyprotocol')) and request.POST.get('snmpv3privacyprotocol') != selectedMPD.snmpv3privacyprotocol else selectedMPD.snmpv3privacyprotocol
        selectedMPD.httpmethod = request.POST.get('httpmethod') if check_existence(request.POST.get('httpmethod')) and request.POST.get('httpmethod') != selectedMPD.httpmethod else selectedMPD.httpmethod
        selectedMPD.httpsecure = bool(int(request.POST.get('httpsecure'))) if check_existence(request.POST.get('httpsecure')) and bool(int(request.POST.get('httpsecure'))) != selectedMPD.httpsecure else selectedMPD.httpsecure
        if selectedMP.monitorprofiletype in ["POSTGRESQL", "SQL"]:
            selectedMPD.httpport = int(request.POST.get('dbaseport')) if check_existence(request.POST.get('dbaseport')) and int(request.POST.get('dbaseport')) != selectedMPD.httpport else selectedMPD.httpport
        else:
            selectedMPD.httpport = int(request.POST.get('httpport')) if check_existence(request.POST.get('httpport')) and int(request.POST.get('httpport')) != selectedMPD.httpport else selectedMPD.httpport
        selectedMPD.httpurl = request.POST.get('httpurl') if check_existence(request.POST.get('httpurl')) and request.POST.get('httpurl') != selectedMPD.httpurl else selectedMPD.httpurl
        selectedMPD.username = request.POST.get('username') if check_existence(request.POST.get('username')) and request.POST.get('username') != selectedMPD.username else selectedMPD.username
        selectedMPD.dbasename = request.POST.get('dbasename') if check_existence(request.POST.get('dbasename')) and request.POST.get('dbasename') != selectedMPD.dbasename else selectedMPD.dbasename
        selectedMPD.userpass = atiba_encrypt(request.POST.get('userpass')) if check_existence(request.POST.get('userpass')) and request.POST.get('userpass') != selectedMPD.userpass else selectedMPD.userpass
        selectedMPD.querytosend = request.POST.get('querytosend') if check_existence(request.POST.get('querytosend')) and request.POST.get('querytosend') != selectedMPD.querytosend else selectedMPD.querytosend
        selectedMPD.responsetoreceive = request.POST.get('responsetoreceive') if check_existence(request.POST.get('responsetoreceive')) and request.POST.get('responsetoreceive') != selectedMPD.responsetoreceive else selectedMPD.responsetoreceive
        selectedMPD.responsetodown = request.POST.get('responsetodown') if check_existence(request.POST.get('responsetodown')) and request.POST.get('responsetodown') != selectedMPD.responsetodown else selectedMPD.responsetodown
        try:
            selectedMPD.save()
            template_message_show(request, "success", "Successfully updated profile")
        except Exception as err:
            logger.exception(f"An error occurred in edit_monitor_profile view trying to save changes for mpdid={id}. ERROR IS : {err}")
            template_message_show(request, "error", "Failed to save updates")

    # logger.debug(f"{vars(selectedMPD)}")
    # for feature in vars(selectedMPD):
    #     logger.debug(f"{feature} : {getattr(selectedMPD, feature)}")

    context = {
        'route': route, 'purpose': purpose, 'selectedMPD': selectedMPD, 'selectedMP': selectedMP,
        'pageTitle': pageTitle, 'mpdNameList': mpdNameList, 'monitorProfileList': monitorProfileList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_profile.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_location_profile(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "location"
    if request.method == "POST":
        if request.POST.get("locationgroupid") == "0":
            location_group = DevLocationGroup()
            location_group.locationgroupname = request.POST.get("locationgroupname")
            location_group.locationgroupcode = request.POST.get("locationgroupcode")
            location_group.save()
            groupID = location_group.id
        else:
            groupID = int(request.POST.get("locationgroupid"))

        location = DevLocations()
        location.locationGroup_id = groupID
        location.locationname = request.POST.get("locationname")
        location.locationcode = request.POST.get("locationcode")
        try:
            location.save()
            template_message_show(request, 'success', 'Location profile successfully saved')
        except Exception as err:
            logger.exception(f"An error occurred while trying to save location ERROR IS : {err}")
            template_message_show(request, 'error', f'Location profile save failed because {err}')

    locationGroupList = DevLocationGroup.objects.all()

    context = {
        'route': route, 'locationGroupList': locationGroupList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_profile.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_ingestion_profile(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "ingestion"
    profileTypeList = IngestionProfileType.objects.all()
    if request.method == "POST":
        # logger.debug(f"{request.POST}")
        ingestion_profile = IngestionProfile()
        ingestion_profile.ingestionprofilename = request.POST.get("ingestionprofilename")
        ingestion_profile.ingestionprofiletypeid = int(request.POST.get("ingestionprofiletype"))
        ingestion_profile.ingestionport = int(request.POST.get("ingestionport"))
        try:
            ingestion_profile.save()
            template_message_show(request, 'success', 'Ingestion Profile successfully saved')
        except Exception as err:
            logger.exception(f"An error occurred in add_ingestion_profile view when trying to save ingestion ERROR IS : {err}")
            template_message_show(request, 'error', f'Ingestion profile save failed because {err}')

    ingestionNameList = [_.ingestionprofilename for _ in IngestionProfile.objects.all()]

    context = {
        'route': route, 'ingestionNameList': ingestionNameList, 'profileTypeList': profileTypeList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/add_profile.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_parser_profile(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "general"
    parserProfileId = 0
    versionParserList = PParseFormulaCode.objects.all()
    customParserList = DeviceParserProfile.objects.all()
    # rawLogCount = Logs.objects.filter(recstatus=2).count()
    # rawLogList = Logs.objects.raw('SELECT id, inetaddress, logdata, logevent, mappedlogsource From loglar WHERE recstatus=2')
    if check_environment_for_elastic():
        try:
            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                               sniff_on_start=True, request_timeout=2)
            _body = '{"size":10000, "query": {"match_all": {}} }'
            _body = json.loads(_body)
            search = elastic_connection.search(index="atibaloglar", body=_body)
            # rawLogCount = int(search["hits"]["total"]["value"])
            # rawLogList = [ErrorLogsFromElastic(hit['_id'], dictionary=hit["_source"]) for hit in search["hits"]["hits"]]
            # ipList = list(set([f"{hit['_source']['inetaddress']}-{hit['_source']['mappedlogsource'] if hit['_source']['mappedlogsource'] else ''}" for hit in search["hits"]["hits"]]))
            ipList = []
            for hit in search["hits"]["hits"]:
                try:
                    ipList.append(f"{hit['_source']['inetaddress']}-{hit['_source']['mappedlogsource'] if hit['_source']['mappedlogsource'] else ''}")
                except KeyError:
                    logger.warning(f"No mappedlogsource key for inetaddress {hit['_source']['inetaddress']}")
                    ipList.append(f"{hit['_source']['inetaddress']}-''")
            ipList = list(set(ipList))
        except Exception as err:
            logger.exception(f"An error occurred while trying to get un-parsed logs from elastic. ERROR IS : {err}")
            ipList = ["NoIpaddres-NoUniqueId"]
    else:
        rawLogList = []
        try:
            # rawLogCount = Logs.objects.filter(recstatus=2).count()
            rawLogList = list(Logs.objects.filter(recstatus=2).defer('olusturmatarih', 'logdate'))
        except Exception as err:
            logger.exception(f"An error occurred while trying to get Logs objects. ERROR IS : {err}")
            try:
                rawLogList = Logs.objects.raw('SELECT id, inetaddress, logdata, logevent, mappedlogsource From loglar WHERE recstatus=2')
            except Exception as err:
                logger.exception(f"Second error occurred while trying to get Logs objects, empty list sent interface. ERROR IS : {err}")
        finally:
            ipList = list(set([f"{_.inetaddress}-{_.mappedlogsource if _.mappedlogsource else ''}" for _ in rawLogList]))
    # logger.debug(f"In add_parser_profile view Raw Log Count : {len(rawLogList)}")
    # if (len(rawLogList) == 0 and rawLogCount > 0) or (len(rawLogList) < rawLogCount):
    #     logger.debug(f"add_parser_profile view encountered an error trying to get raw logs. List length is {len(rawLogList)} where count is {rawLogCount}")
    #     template_message_show(request, "warning", f"Failed to get {rawLogCount} raw logs")
    # ipList = list(set([f"{_.inetaddress}-{_.mappedlogsource if _.mappedlogsource else ''}" for _ in rawLogList]))

    if request.method == "GET":
        logger.debug(f"{request.GET}")

    elif request.method == "POST":
        save_status = False
        logger.debug(f"is request from ajax? {request.is_ajax()}")
        """
        GELEN POST QUERY SET :
        BURASI DEVICE PARSER PROFILE
        'ipaddress': ['192.168.1.249'], 
        'uniqueid': [''],
        'parsername': ['Yeniparser'], 
        'alternateparseid': ['Yeniparser'], seçilmemişse 0
        'alternatecondition': ['regex']
        'save_or_update': ['0'] 0 for save new, parser profile id for update
        
        BURASI DEVICE PARSER RULES
        'logidstart': ["instr($1,'<',1,1)+1"], 
        'logidcount': ["instr($1,'>',-1,1)-(instr($1,'<',1,1)+1)"], 
        
        'logdatestart': ["instr($1,'>',1,1)+1"], 
        'logdatecount': ['23'], 
        'logdateformat': ['YYYY-MM-DD HH:MM:SS'],
        
        'logservicestart': ["instr($1,' ',1,6)+1"], 
        'logservicecount': ["instr($1,' ',-1,8)-(instr($1,' ',1,6)+1)"], 
        
        'logservicenostart': ["instr($1,' ',1,5)+1"], 
        'logservicenocount': ["instr($1,' ',-1,10)-(instr($1,' ',1,5)+1)"], 
        
        'lognostart': ["instr($1,'0',1,7)+1"], 
        'lognocount': ["instr($1,' ',-1,8)-(instr($1,'0',1,7)+1)"], 
        
        'logeventstart': ["instr($1,' ',1,8)+1"], 
        'logeventcount': ["instr($1,'',-1,1)-(instr($1,' ',1,8)+1)"]}
         
        POSTGRE DE PARSER TESTİ İÇİN KULLANILACAK FONKSİYON:
        seielct * from logparsetest(
            plogdata text,
            pdegisken text,
            pstart text,
            pkaraktersay text,
            ptype text,
            pformat text)
            
        select * from logparsetest(
            plogdata text,
            pdegisken text,
            pstart text,
            pkaraktersay text,
            ptype text,
            pformat text,
            pstaticval text)
        """

        if request.is_ajax():
            logger.info(f"request for : {request.POST.get('action')}")
            if request.POST.get("action") == "test":
                plogdata = request.POST.get("plogdata")
                pdegisken = request.POST.get("pdegisken") if request.POST.get("pdegisken") else ""
                pstart = request.POST.get("pstart")
                pkaraktersay = request.POST.get("pkaraktersay")
                ptype = request.POST.get("ptype")
                pformat = request.POST.get("pformat") if request.POST.get("pformat") != "Regular Expression" else ""

                if not check_existence(plogdata) or not check_existence(pstart) or not check_existence(pkaraktersay):
                    logger.warning("You have to give required variables for function")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'warning': 'Fields are empty'}, status=200)

                if ptype == 'date' and (pformat is None or pformat == ""):
                    logger.warning("You have to give right format for date and time")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'warning': 'Please give right format'}, status=200)

                try:
                    testResult = serializers.serialize('json', LogParseTestResult.objects.raw('SELECT 1 as id, rtext, rlogdate, rstatuskod FROM logparsetest(%s,%s,%s,%s,%s,%s)', [plogdata, pdegisken, pstart, pkaraktersay, ptype, pformat]), fields=('id', 'rtext', 'rlogdate', 'rstatuskod'))
                    testResult = json.loads(testResult)[0]
                    logger.debug(f"{type(testResult)}")
                    logger.debug(f"{testResult}")
                    logger.debug(f"{testResult['fields']['rtext']}")
                    rtext = testResult['fields']['rtext']
                    parseTestObj = LogParseTestResult()
                    parseTestObj.id = testResult['pk']
                    parseTestObj.rtext = testResult['fields']['rtext']
                    parseTestObj.rlogdate = testResult['fields']['rlogdate']
                    parseTestObj.rstatuskod = testResult['fields']['rstatuskod']
                    logger.debug(f"{parseTestObj}")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 1, 'testResult': parseTestObj.get_json(), 'rtext': rtext}, status=200)
                except Exception as err:
                    logger.exception(f"An error occurred while trying to excecute logparsetest in db. ERROR IS : {err}")
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'warning': 'Failed, check field values', 'err': str(err)}, status=200)
            elif request.POST.get("action") == "getCustomRules" or request.POST.get("action") == "getInstalledRules":
                parserID = int(request.POST.get("parserID"))
                try:
                    if request.POST.get("action") == "getCustomRules":
                        selectedProfile = DeviceParserProfile.objects.get(id=parserID)
                    # elif request.POST.get("action") == "getInstalledRules":  # there is no alternative different from getInstalledRules for now
                    else:
                        selectedProfile = PParseFormulaCode.objects.get(id=parserID)
                    alternativeProfile = selectedProfile.get_alternative().get_json() if selectedProfile.get_alternative() != "" else None
                    parserRules = [x.get_json() for x in selectedProfile.get_parser_rules()]
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 1, 'selectedProfile': selectedProfile.get_json(), 'parserRules': parserRules, 'alternativeProfile': alternativeProfile}, status=200)
                except ObjectDoesNotExist or MultipleObjectsReturned:
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'warning': 'Parser Selection Error'}, status=200)
            elif request.POST.get("action") == "get_rawLogList":
                # logger.debug(f"{request.POST}")
                _ip = request.POST.get("ip") if check_existence(request.POST.get("ip")) else None
                _uid = request.POST.get("uniqueid") if check_existence(request.POST.get("uniqueid")) else None
                if check_existence(_uid):
                    if check_environment_for_elastic():
                        try:
                            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                                               sniff_on_start=True, request_timeout=2)
                            _body = '{"size":100,"query":{"bool":{"must":[{"term":{"mappedlogsource":{"value":"%s","boost":1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"_id":{"order":"desc"}}]}' % _uid
                            logger.debug(f"{_body}")
                            _body = json.loads(f"{_body}")
                            search = elastic_connection.search(index="atibaloglar", body=_body)
                            # elastic_log_list = [ErrorLogsFromElastic(hit['_id'], dictionary=hit["_source"]) for hit in search["hits"]["hits"]]
                            rawLogList = [hit["_source"]["logdata"] for hit in search["hits"]["hits"]]
                        except Exception as err:
                            logger.exception(f"An error occurred while trying to get raw logs from elastic. ERROR IS : {err}")
                            rawLogList = []
                            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                            return JsonResponse({'command': 0, 'error': str(err)}, status=200)
                    else:
                        try:
                            rawLogList = list(Logs.objects.filter(recstatus=2).filter(mappedlogsource=_uid).only('logdata')[:100])
                            rawLogList = [_.logdata for _ in rawLogList]
                        except Exception as err:
                            logger.exception(f"An error occurred while trying to get Logs objects. ERROR IS : {err}")
                            try:
                                _qry = f"SELECT id, logdata FROM loglar WHERE mappedlogsource='{_uid}' ORDER BY id DESC LIMIT 100"
                                rawLogList = list(Logs.objects.raw(_qry))
                                rawLogList = [_.logdata for _ in rawLogList]
                            except Exception as err:
                                logger.exception(f"Second error occurred while trying to get Logs objects. ERROR IS : {err}")
                                try:
                                    _qry = f"SELECT id, logdata FROM loglar WHERE mappedlogsource='{_uid}' ORDER BY id DESC LIMIT 100"
                                    conn = psycopg2.connect(postgresql_conn_string)
                                    cur = conn.cursor()
                                    cur.execute(_qry)
                                    rawLogList = cur.fetchall()
                                    cur.close()
                                    rawLogList = [y for x, y in rawLogList]
                                except Exception as err:
                                    logger.exception(f"Third error occurred while trying to get Logs objects, empty list sent interface. ERROR IS : {err}")
                                    rawLogList = []
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 1, 'rawLogList': rawLogList}, status=200)
                elif check_existence(_ip):
                    if check_environment_for_elastic():
                        try:
                            # _aggr = '"aggregations":{"sonuc":{"terms":{"field":"inetaddress", "size":100,"min_doc_count":1,"show_term_doc_count_error":false,"order":[{"_count":"desc"},{"_key":"asc"}]}}}'
                            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                                               sniff_on_start=True, request_timeout=2)
                            _body = '{"size":100,"query":{"bool":{"must":[{"term":{"inetaddress":{"value":"%s","boost":1.0}}}],"adjust_pure_negative":true,"boost":1.0}},"sort":[{"_id":{"order":"desc"}}]}' % _ip
                            logger.debug(f"{_body}")
                            _body = json.loads(f"{_body}")
                            search = elastic_connection.search(index="atibaloglar", body=_body)
                            # elastic_log_list = [ErrorLogsFromElastic(hit['_id'], dictionary=hit["_source"]) for hit in search["hits"]["hits"]]
                            rawLogList = [hit["_source"]["logdata"] for hit in search["hits"]["hits"]]
                        except Exception as err:
                            logger.exception(f"An error occurred while trying to get raw logs from elastic. ERROR IS : {err}")
                            rawLogList = []
                            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                            return JsonResponse({'command': 0, 'error': str(err)}, status=200)
                    else:
                        try:
                            rawLogList = list(Logs.objects.filter(recstatus=2).filter(inetaddress=_ip).only('logdata')[:100])
                            rawLogList = [_.logdata for _ in rawLogList]
                        except Exception as err:
                            logger.exception(f"An error occurred while trying to get Logs objects. ERROR IS : {err}")
                            try:
                                _qry = f"SELECT id, logdata FROM loglar WHERE inetaddress='{_ip}' ORDER BY id DESC LIMIT 100"
                                rawLogList = list(Logs.objects.raw(_qry))
                                rawLogList = [_.logdata for _ in rawLogList]
                            except Exception as err:
                                logger.exception(f"Second error occurred while trying to get Logs objects. ERROR IS : {err}")
                                try:
                                    _qry = f"SELECT id, logdata FROM loglar WHERE inetaddress='{_ip}' ORDER BY id DESC LIMIT 100"
                                    conn = psycopg2.connect(postgresql_conn_string)
                                    cur = conn.cursor()
                                    cur.execute(_qry)
                                    rawLogList = cur.fetchall()
                                    cur.close()
                                    rawLogList = [y for x, y in rawLogList]
                                except Exception as err:
                                    logger.exception(f"Third error occurred while trying to get Logs objects, empty list sent interface. ERROR IS : {err}")
                                    rawLogList = []
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 1, 'rawLogList': rawLogList}, status=200)
                else:
                    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                    return JsonResponse({'command': 0, 'error': 'No ip or unique id given !'}, status=200)
        else:
            logger.debug(f"not ajax it's form : {request.POST}")  # request is not ajax
            """
                'multiline_log': ['on'], 
                'delimposition': ['1'], 
                'delim': ['mlt'], 
                'traceback_log': ['on'], 
                'tbackdelimposition': ['0'], 
                'tbackdelim': ['trb']
            """
            # logger.debug(f"multiline_log : {request.POST.get('multiline_log')}")
            # logger.debug(f"delimposition : {request.POST.get('delimposition')}")
            # logger.debug(f"delim : {request.POST.get('delim')}")
            # logger.debug(f"traceback_log: {request.POST.get('traceback_log')}")
            # logger.debug(f"tbackdelimposition : {request.POST.get('tbackdelimposition')}")
            # logger.debug(f"tbackdelim : {request.POST.get('tbackdelim')}")

            _ip_address = request.POST.get("ipaddress")
            # _full_log_data = request.POST.get("fulllogdata")
            if check_existence(request.POST.get("save_or_update")) and request.POST.get("save_or_update") == "0":
                device_parser_profile = DeviceParserProfile()
                device_parser_profile.parsername = request.POST.get("parsername") if check_existence(request.POST.get("parsername")) else datetime.datetime.now().strftime('%d_%m_%YT%H:%M:%S')
                device_parser_profile.alternateparseid = int(request.POST.get("alternateparseid")) if check_existence(request.POST.get("alternateparseid")) and request.POST.get("alternateparseid") != "0" else None
                device_parser_profile.alternatecondition = request.POST.get("alternatecondition") if check_existence(request.POST.get("alternatecondition")) else None
                device_parser_profile.parsestatus = True
                if check_existence(request.POST.get('multiline_log')) and request.POST.get('multiline_log') == "on":
                    device_parser_profile.delimposition = int(request.POST.get('delimposition')) if check_existence(request.POST.get('delimposition')) else None
                    device_parser_profile.delim = request.POST.get('delim') if check_existence(request.POST.get('delim')) else None
                if check_existence(request.POST.get('traceback_log')) and request.POST.get('traceback_log') == "on":
                    device_parser_profile.tback = True
                    device_parser_profile.tbackdelim = request.POST.get('tbackdelim') if check_existence(request.POST.get('tbackdelim')) else None
                    device_parser_profile.tbackdelimposition = int(request.POST.get('tbackdelimposition')) if check_existence(request.POST.get('tbackdelimposition')) else None
                
                try:
                    device_parser_profile.save()
                    parserProfileId = device_parser_profile.id
                    save_status = True
                    template_message_show(request, "success", "Parser profile successfully saved")
                except Exception as err:
                    logger.exception(f"An error occurred while trying to save deviceparserprofile ERROR IS : {err}")
                    template_message_show(request, "error", f"Failed to save parser profile because {err}")

                variable_names = ["logid", "logdate", "logservice", "logserviceno", "logno", "logevent"]
                if parserProfileId != 0:
                    for name in variable_names:
                        if check_existence(request.POST.get(f"{name}start")) and check_existence(request.POST.get(f"{name}count")):
                            device_parser_rules = DeviceParserRules()
                            device_parser_rules.parserProfile_id = parserProfileId
                            device_parser_rules.varname = name
                            device_parser_rules.startpoint = request.POST.get(f"{name}start")
                            device_parser_rules.charcount = request.POST.get(f"{name}count")
                            if name == "logdate":
                                device_parser_rules.vartype = "date"
                                device_parser_rules.varformat = request.POST.get(f"{name}format") if check_existence(request.POST.get(f"{name}format")) else None
                            else:
                                device_parser_rules.vartype = "string"
                            try:
                                device_parser_rules.save()
                                save_status = save_status and True
                                template_message_show(request, "success", f"{name} parser rule successfully saved")
                            except Exception as err:
                                save_status = save_status and False
                                logger.exception(f"An error occurred while trying to save deviceparserrule for {name}. ERROR IS : {err}")
                                template_message_show(request, "error", f"Failed to save parser rule {name} because {err}")
                                continue
                            logger.debug(f'{request.POST.get(f"{name}start")} {request.POST.get(f"{name}count")}')
                        else:
                            if name == "logno":
                                device_parser_rules = DeviceParserRules()
                                device_parser_rules.parserProfile_id = parserProfileId
                                device_parser_rules.varname = name
                                device_parser_rules.startpoint = None
                                device_parser_rules.charcount = None
                                device_parser_rules.vartype = "string"
                                device_parser_rules.staticval = "<undef>"
                                try:
                                    device_parser_rules.save()
                                    save_status = save_status and True
                                    template_message_show(request, "success", f"{name} parser rule successfully saved")
                                except Exception as err:
                                    save_status = save_status and False
                                    logger.exception(f"An error occurred while trying to save deviceparserrule for {name}. ERROR IS : {err}")
                                    template_message_show(request, "error", f"Failed to save parser rule {name} because {err}")
                                    continue
                                logger.info(f"{name}start empty {name}count empty that's why {name}static is {device_parser_rules.staticval}")
            elif check_existence(request.POST.get("save_or_update")) and request.POST.get("save_or_update") != "0":
                profile_to_update_id = int(request.POST.get("save_or_update"))
                profile_to_update = DeviceParserProfile.objects.get(id=profile_to_update_id)
                profile_to_update.parsername = request.POST.get("parsername") if check_existence(request.POST.get("parsername")) and request.POST.get("parsername") != profile_to_update.parsername else profile_to_update.parsername
                profile_to_update.alternateparseid = int(request.POST.get("alternateparseid")) if request.POST.get("alternateparseid") != "0" and int(request.POST.get("alternateparseid")) != profile_to_update.alternateparseid else profile_to_update.alternateparseid
                profile_to_update.alternatecondition = request.POST.get("alternatecondition") if check_existence(request.POST.get("alternatecondition")) and request.POST.get("alternatecondition") != profile_to_update.alternatecondition else profile_to_update.alternatecondition
                profile_to_update.parsestatus = True

                if check_existence(request.POST.get('multiline_log')) and request.POST.get('multiline_log') == "on":
                    profile_to_update.delimposition = int(request.POST.get('delimposition')) if check_existence(request.POST.get('delimposition')) else None
                    profile_to_update.delim = request.POST.get('delim') if check_existence(request.POST.get('delim')) else None
                else:

                    profile_to_update.delimposition, profile_to_update.delim = None, None

                if check_existence(request.POST.get('traceback_log')) and request.POST.get('traceback_log') == "on":
                    profile_to_update.tback = True
                    profile_to_update.tbackdelim = request.POST.get('tbackdelim') if check_existence(request.POST.get('tbackdelim')) else None
                    profile_to_update.tbackdelimposition = int(request.POST.get('tbackdelimposition')) if check_existence(request.POST.get('tbackdelimposition')) else None
                else:
                    profile_to_update.tback = False
                    profile_to_update.tbackdelim, profile_to_update.tbackdelimposition = None, None

                try:
                    profile_to_update.save()
                    template_message_show(request, "success", "Parser profile successfully updated")
                except Exception as err:
                    logger.exception(f"An error occurred while trying to update existing parser profile. ERROR IS : {err}")
                    template_message_show(request, "error", f"Failed to update. Because {err}")
                rules_list = profile_to_update.get_parser_rules()
                logger.debug(f"{rules_list}")
                variable_names = ["logid", "logdate", "logservice", "logserviceno", "logno", "logevent"]
                for name in variable_names:
                    count_updated = 0
                    if check_existence(request.POST.get(f"{name}start")) and check_existence(request.POST.get(f"{name}count")):
                        if name == "logdate":
                            count_updated = DeviceParserRules.objects.filter(parserProfile_id=profile_to_update_id).filter(varname=name).update(startpoint=request.POST.get(f"{name}start"), charcount=request.POST.get(f"{name}count"), varformat=request.POST.get(f"{name}format"))
                        else:
                            count_updated = DeviceParserRules.objects.filter(parserProfile_id=profile_to_update_id).filter(varname=name).update(startpoint=request.POST.get(f"{name}start"), charcount=request.POST.get(f"{name}count"))
                        if count_updated == 0:
                            new_rule = DeviceParserRules()
                            new_rule.parserProfile_id = profile_to_update_id
                            new_rule.varname = name
                            new_rule.startpoint = request.POST.get(f"{name}start")
                            new_rule.charcount = request.POST.get(f"{name}count")
                            if name == "logdate":
                                new_rule.vartype = "date"
                                new_rule.varformat = request.POST.get(f"{name}format") if check_existence(
                                    request.POST.get(f"{name}format")) else None
                            else:
                                new_rule.vartype = "string"
                            try:
                                new_rule.save()
                            except Exception as err:
                                logger.exception(f"An error occurred while trying to save new deviceparserrule for parserprofileid : {profile_to_update_id} ERROR IS : {err}")
                                continue
                    else:
                        if name == "logno":
                            DeviceParserRules.objects.filter(parserProfile_id=profile_to_update_id).filter(varname=name).update(startpoint=None, charcount=None, staticval="<undef>")
                        else:
                            if name != "logdate":
                                DeviceParserRules.objects.filter(parserProfile_id=profile_to_update_id).filter(varname=name).update(startpoint=request.POST.get(f"{name}start"), charcount=request.POST.get(f"{name}count"))
            else:
                logger.warning("save or update value is None or Empty Value received !!")

    template_message_show(request, 'warning', 'Chose log event first')

    context = {
        'route': route, 'ipList': ipList, 'customParserList': customParserList,
        'versionParserList': versionParserList,
        # "rawLogList": rawLogList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return render(request, 'AgentRoot/add_parser_profile.html', context)
    except Exception as err:
        try:
            logger.exception(f"An error occurred while trying to render add_parser_profile.html. ERROR IS : {err}")
            template_message_show(request, "error", f"Failed to render parser profile form. {err}")
            # memory usage logging with memory_tracer
            top_stats = tracemalloc.take_snapshot().statistics('lineno')
            total_size, unit = take_memory_usage(top_stats)
            logger.info(f"Memory allocation  {total_size} {unit}")
            memory_tracer.info(f"{total_size}")
            tracemalloc.stop()
        except:
            logger.debug("tracemalloc stopped before somehow")
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return redirect('profiles')


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def parameter_variables(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    global globalBool
    route = "general"

    page = request.GET.get('page')
    order_by = request.GET.get("order_by")
    name_q = request.GET.get("name_q")
    type_q = request.GET.get("type_q")
    code_q = request.GET.get("code_q")

    allParams = list(ParamVariables.objects.all())

    paramsList = set(allParams)

    if name_q:
        paramsList = paramsList.intersection(set(list(ParamVariables.objects.filter(Q(kodnote__icontains=name_q)))))
    if type_q:
        paramsList = paramsList.intersection(set(list(ParamVariables.objects.filter(Q(paramtype__icontains=type_q)))))
    if code_q:
        paramsList = paramsList.intersection(set(list(ParamVariables.objects.filter(Q(kod__icontains=code_q)))))

    paramsList = list(paramsList)
    record_count = len(paramsList)

    if order_by:
        if not page:
            globalBool = not globalBool
        if order_by == "parametertypeid_id":
            paramsList.sort(key=lambda x: getattr(x, order_by) if hasattr(x, order_by) and getattr(x, order_by) else 0,
                            reverse=globalBool)
        else:
            paramsList.sort(key=lambda x: getattr(x, order_by) if hasattr(x, order_by) and getattr(x, order_by) else "",
                            reverse=globalBool)
    else:
        paramsList.sort(key=lambda x: x.paramtype)

    paginator = Paginator(paramsList, record_per_page)
    try:
        paramsList = paginator.page(page)
    except PageNotAnInteger:
        paramsList = paginator.page(1)
    except EmptyPage:
        paramsList = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'paramsList': paramsList, 'record_count': record_count,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'paramvars.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def edit_parameter_variable(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "edit"

    paramTypes = list(set(ParamVariables.objects.values_list("paramtype", flat=True).all()))
    logger.debug(f"type list : {paramTypes}")

    paramvars = ParamVariables.objects.get(id=id)
    form = ParamVariablesForm(request.POST or None, instance=paramvars)

    if request.method == "POST":
        logger.debug(f"{request.POST}")
        if form.is_valid():
            try:
                paramvars.save()
                template_message_show(request, "success", f"Parameter variable updated successfully.")
                return redirect("parameter_variables")
            except Exception as err:
                logger.exception(f"An error occurred trying to save new parameter variable. ERROR IS {err}")
                template_message_show(request, "error", f"New parameter variable failed to save because : {err}")

    context = {
        'route': route, 'form': form, 'paramTypes': paramTypes,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'paramvars.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def add_parameter_variable(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "add"

    paramTypes = list(set(ParamVariables.objects.values_list("paramtype", flat=True).all()))
    logger.debug(f"type list : {paramTypes}")

    try:
        latest_code_order = ParamVariables.objects.values_list("codeorder", flat=True).order_by("-codeorder")[1]
        logger.debug(f"latest codeorder : {latest_code_order}")
    except Exception as err:
        logger.warning(f"Latest codeorder before 999 couldn't get from database. {err}")
        try:
            latest_code_order = ParamVariables.objects.values_list("id", flat=True).order_by("-id")[0]
            logger.debug(f"latest id for codeorder : {latest_code_order}")
        except Exception as err:
            logger.warning(f"Latest id couldn't get from database. {err}")
            latest_code_order = 0

    new_pv = ParamVariables()
    new_pv.codeorder = latest_code_order + 1

    form = ParamVariablesForm(request.POST or None, instance=new_pv)

    if request.method == "POST":
        logger.debug(f"request.POST : {request.POST}")
        logger.debug(f"is form valid ? : {form.is_valid()}")
        if form.is_valid():
            try:
                new_pv.valacceptreg = new_pv.valacceptreg if check_existence(new_pv.valacceptreg) else None
                new_pv.save()
                logger.debug(f"New parameter variable valacceptreg : {new_pv.valacceptreg}")
                template_message_show(request, "success",
                                      f"New parameter variable saved successfully with id {new_pv.id}.")
                return redirect("parameter_variables")
            except Exception as err:
                logger.exception(f"An error occurred trying to save new parameter variable. ERROR IS {err}")
                template_message_show(request, "error", f"New parameter variable failed to save because : {err}")

    context = {
        'route': route, 'form': form, 'paramTypes': paramTypes,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'paramvars.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def logdefinitions_analysis(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "LOG DEFINITIONS"
    lodDefinitionList = LogDefinitions.objects.all()
    logDefinitionsId = 0
    if request.method == "POST":
        logger.debug(f"Data inside request : {request.POST}")
        if check_existence(request.POST.get('analyse_parameters')):
            logDefinitionsId = int(request.POST.get('analyse_parameters'))
            logger.debug("Java analyse parameters will be called here in new thread !! from logdefinitions_analysis view")
            _thread.start_new_thread(analyse_parameters_with_java, (logDefinitionsId,))
            # analyse_parameters_with_java(logDefinitionsId)
            # _result = analyse_parameters_with_java(logDefinitionsId)
            # logger.info(f"analyse_parameters_with_java result is : {_result}")
            logger.info(f"Called function analyse_parameters_with_java in new thread.")
        else:
            template_message_show(request, "warning", "You must select a definition before pressing the Analyse Parameters")

    paginator = Paginator(lodDefinitionList, 10)
    page = request.GET.get('page')
    try:
        lodDefinitionList = paginator.page(page)
    except PageNotAnInteger:
        lodDefinitionList = paginator.page(1)
    except EmptyPage:
        lodDefinitionList = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'lodDefinitionList': lodDefinitionList, 'logDefinitionsId': logDefinitionsId,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/logdefinitions_analysis.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def logdefdetails_analysis(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    global globalBool
    route = "detail"
    logdefinition = LogDefinitions.objects.get(definitioncode=id)
    systemSeverityList = [_.severitydef for _ in SystemSeverities.objects.all()]

    if request.method == 'POST':
        logger.debug(f"{request.POST}")
        """
        'new_subdef': ['4260']  --> value is : logdefdetails.id
        'delete_subdef': ['4517']
        """
        new_subdef = int(request.POST.get('new_subdef')) if check_existence(request.POST.get('new_subdef')) else None
        delete_subdef = int(request.POST.get('delete_subdef')) if check_existence(request.POST.get('delete_subdef')) else None

        if request.POST.get('new_subdef') == "" or request.POST.get('delete_subdef') == "":
            # it means buttons are pressed without selecting any row, we saw that kind of idiots !!
            logger.info(f"Pressed Delete Sub Definition or Create New Sub Definition button without selecting a row")
            template_message_show(request, "warning", f"Please select a row first !")

        if new_subdef:
            _new_ldd = LogDefinitionDetails.objects.get(id=new_subdef)
            _new_ldd.id = None
            _new_ldd.autoparam = False
            _new_ldd.paramsvalid = False
            _new_ldd.systemlogdef = False
            _subdefcodelist = [_.logsubdefcode for _ in list(LogDefinitionDetails.objects.filter(
                logcode=_new_ldd.logcode).exclude(logsubdefcode=999))]
            _new_ldd.logsubdefcode = 1 if len(_subdefcodelist) == 0 else max(_subdefcodelist)+1
            _new_ldd.save()
            template_message_show(request, "success", "Successfully added a new log parameter definition same as your selection, please don't forget to edit and validate")

        if delete_subdef:
            _ldd_to_delete = LogDefinitionDetails.objects.get(id=delete_subdef)
            if not _ldd_to_delete.paramsvalid and not _ldd_to_delete.systemlogdef:
                _ldd_to_delete.delete()
                template_message_show(request, "success", "Selected log parameter definition successfully deleted")
            else:
                template_message_show(request, "warning", "You Can't delete a validated log parameter definition")

    logdefdetailList = list(LogDefinitionDetails.objects.filter(logDefCode_id=id))
    page = None
    # if request.method == 'GET':
    # logger.debug(f"{request.GET}")
    """
    'change_severity_for': ['<501093>'], 
    'change_severity_to': ['Information'],
    'current_severity': ['Debug'],
    'logcode_q': ['25'], 
    'structs_q': ['']
    """
    logcode_q = request.GET.get('logcode_q')
    structs_q = request.GET.get('structs_q')
    order_by = request.GET.get('order_by') if check_existence(request.GET.get('order_by')) else None
    page = request.GET.get('page') if check_existence(request.GET.get('page')) else None
    change_severity_for = int(request.GET.get('change_severity_for')) if request.GET.get('change_severity_for') else None
    change_severity_to = request.GET.get('change_severity_to')

    if logcode_q and not structs_q:
        logdefdetailList = list(LogDefinitionDetails.objects.filter(logDefCode_id=id).filter(
            Q(logcode__icontains=logcode_q)))

    if not logcode_q and structs_q:
        logdefdetailList = list(LogDefinitionDetails.objects.filter(logDefCode_id=id).filter(
            Q(logstructs__icontains=structs_q)))

    if logcode_q and structs_q:
        logdefdetailList = list(
            LogDefinitionDetails.objects.filter(logDefCode_id=id).filter(
                Q(logcode__icontains=logcode_q)).filter(Q(logstructs__icontains=structs_q)))

    if order_by:
        if not page:
            globalBool = not globalBool
        try:
            logdefdetailList.sort(key=lambda x: getattr(x, order_by) if hasattr(x, order_by) else "",
                                  reverse=globalBool)
        except TypeError:
            logdefdetailList.sort(key=lambda x: getattr(x, order_by) if getattr(x, order_by) else "",
                                  reverse=globalBool)
        except Exception as err:
            logger.error(f"An error occurred while trying to sort list. ERROR IS : {err}")
            template_message_show(request, "warning", f"Sorting error {err}")
    if request.method == 'GET':
        if change_severity_for and change_severity_to:
            # ldd_to_change_severity = (LogDefinitionDetails.objects.filter(logcode=change_severity_for).filter(logsubdefcode=999))[0]
            ldd_to_change_severity = LogDefinitionDetails.objects.get(id=change_severity_for)
            current_severity = ldd_to_change_severity.outclasstype
            sub_def_code = ldd_to_change_severity.logsubdefcode
            logger.info(f"logdefinitions row outclasstype changed for logdefdetails id {change_severity_for} from {current_severity} to {change_severity_to}")
            # change_severity_with_java(change_severity_for, current_severity, change_severity_to)  # function changed as a void function...
            # _thread.start_new_thread(change_severity_with_java, (change_severity_for, current_severity, change_severity_to, ))  # function changed as a void function...
            _thread.start_new_thread(change_severity_with_java, (change_severity_for, current_severity, change_severity_to, sub_def_code, ))  # function changed as a void function...
            logger.info(f"Called change_severity_with_java in new thread.")
            template_message_show(request, 'success', f'Priority change operation started successfully -> for {change_severity_for} from {current_severity} to {change_severity_to}')
            # _resultChangeSeverity = change_severity_with_java(change_severity_for, current_severity, change_severity_to)
            # if _resultChangeSeverity:
            #     logger.info(f"Called change_severity_with_java. Result : {_resultChangeSeverity}")
            #     template_message_show(request, 'success', f'Priorities successfully changed for {change_severity_for} from {current_severity} to {change_severity_to}')
            # else:
            #     logger.exception(f"Failed to run change_severity_with_java")
            #     template_message_show(request, 'error', f'Failed to change priority for {change_severity_for} from {current_severity} to {change_severity_to}.')
        elif change_severity_for and not change_severity_to:
            template_message_show(request, 'info', f'No changes to make difference')

    paginator = Paginator(logdefdetailList, 15)

    try:
        logdefdetailList = paginator.page(page)
    except PageNotAnInteger:
        logdefdetailList = paginator.page(1)
    except EmptyPage:
        logdefdetailList = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'logdefinition': logdefinition, 'logdefdetailList': logdefdetailList,
        'systemSeverityList': systemSeverityList,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/logdefdetails_analysis.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def logdefdetails_configure(request, id):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "LOG DEFINITION DETAILS"
    logDefinitionsId = 0  # i need it for javascript
    try:
        logDefDetail = LogDefinitionDetails.objects.get(id=id)
    except ObjectDoesNotExist:
        # exceptionalWarn = f"Possible data corruption"
        logger.warning(f"logdefdetails object that you trying to get with id : {id} couldn't found")
        exceptionalWarn = f"No valid data were found,  may data be fragmented or missing"
        return render(request, 'exceptions.html', {'route': route, 'warning': exceptionalWarn})

    # FOR ENVIRONMENT THAT ELASTIC RUN ---------------------------------------------------------------------------
    if check_environment_for_elastic():
        try:
            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                               sniff_on_start=True, request_timeout=5)
            search_object = Search(using=elastic_connection, index="atibalogs")
            search = search_object[:100].sort("-credate")
            search = search.query("term", **{"logndx": {"value": logDefDetail.logcode}})
            response = search.execute()
            logsFromElastic = [LogFromElastic(hit_object=hit) for hit in response.hits]
        except Exception as err:
            logsFromElastic = []
            logger.exception(f"An error occurred while trying to connect elasticsearch : {err}")
            template_message_show(request, "error", f"Failed to get logs with logcode {logDefDetail.logcode}")
    # FOR LOCAL WITH NO ELASTIC ----------------------------------------------------------------------------------
    else:
        logsFromElastic = []

    if request.method == 'POST':
        # logger.debug(request.POST)
        """
        'reparse_all': ['<404090>']  --> reparse for log code
        'reparse_selected': ['']  --> reparse for log in elasticsearch where id is this (logndx)
        'analyse_parameter': ['']  --> call java function analyzeparameter with logdefdetails id
        'paramsvalid': ['1']  --> value is 1 it means paramsvalid column value update to true 
                               if value is 0 then update to false
        """
        reparse_all = request.POST.get('reparse_all') if check_existence(request.POST.get('reparse_all')) else None
        reparse_selected = int(request.POST.get('reparse_selected')) if check_existence(request.POST.get('reparse_selected')) else None
        analyse_parameter = int(request.POST.get('analyse_parameter')) if check_existence(request.POST.get('analyse_parameter')) else None
        paramsvalid = bool(int(request.POST.get('paramsvalid'))) if check_existence(request.POST.get('paramsvalid')) else None

        if reparse_all:
            logger.info(f"reparse_all : {reparse_all}")
            _thread.start_new_thread(reparse_all_with_java, (reparse_all, 3, ))
            # reparse_all_with_java(reparse_all, 3)
            # _resultReparse = reparse_all_with_java(reparse_all, 3)
            # logger.info(f"Called reparse_all_with_java. Result : {_resultReparse}")
            logger.info(f"Called reparse_all_with_java in new thread.")

        if reparse_selected:
            logger.info(f"reparse_selected : {reparse_selected}")
            _thread.start_new_thread(reparse_selected_with_java, (reparse_selected, 4, ))
            # reparse_selected_with_java(reparse_selected, 4)
            # _resultReparseSelected = reparse_selected_with_java(reparse_selected, 4)
            # logger.info(f"Called reparse_selected_with_java. Result : {_resultReparseSelected}")
            logger.info(f"Called reparse_selected_with_java in new thread.")

        if analyse_parameter:
            logger.info(f"analyse_parameter : {analyse_parameter}")
            # analyze_parameter_with_java(analyse_parameter, logDefDetail.logcode)
            _thread.start_new_thread(analyze_parameter_with_java, (analyse_parameter, logDefDetail.logcode, ))
            # _resultAnalyseParameter = analyze_parameter_with_java(analyse_parameter, logDefDetail.logcode)
            # logger.info(f"Called analyze_parameter_with_java. Result : {_resultAnalyseParameter}")
            logger.info(f"Called analyze_parameter_with_java in new thread.")

        if paramsvalid is not None:
            logger.info(f"paramsvalid : {paramsvalid}")
            logDefDetail.paramsvalid = paramsvalid
            if paramsvalid:
                # logger.info(f"paramsvalid : {paramsvalid}")
                # logDefDetail.paramsvalid = paramsvalid
                _thread.start_new_thread(logdefValidate_with_java, (id, ))
                # logdefValidate_with_java(id)
                # _resultLogDefValidate = logdefValidate_with_java(id)
                # logger.info(f"Called logdefValidate_with_java. Result : {_resultLogDefValidate}")
                logger.info(f"Called logdefValidate_with_java.")
            try:
                logDefDetail.save()
                # LogDefinitionDetails.objects.filter(id=id).update(paramsvalid=paramsvalid)
                template_message_show(request, "success", "Successfully updated as valid")
            except Exception as err:
                logger.exception(f"An error occurred while trying to update validation. ERROR IS : {err}")
                template_message_show(request, "error", f"Failed to update as valid because {err}")

    paginator = Paginator(logsFromElastic, 15)
    page = request.GET.get('page')
    try:
        logsFromElastic = paginator.page(page)
    except PageNotAnInteger:
        logsFromElastic = paginator.page(1)
    except EmptyPage:
        logsFromElastic = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'logDefinitionsId': logDefinitionsId, 'logDefDetail': logDefDetail,
        'logsFromElastic': logsFromElastic,
    }
    try:
        # memory usage logging with memory_tracer
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/logdefinitions_analysis.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def logdefdetails_edit(request, id):
    """
    this view function is not in use !!!!
    log definition view. It will be changed, because moveup, movedown, add and delete operations wilbe solved in javascript...
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    global globalList
    route = "Configure Parameters"
    logDefDetail = LogDefinitionDetails.objects.get(id=id)
    logDefsList = logDefDetail.get_logdefs()
    logger.debug(f"logDefsList : {logDefsList}")
    logDefsList = logDefsList if logDefsList else [{"d": "generic"}, {"s": "string"}]
    logger.debug(f"logDefsList : {logDefsList}")
    ParamVariableList = ParamVariables.objects.all()
    paramTypeList = list(set([_.paramtype for _ in ParamVariableList]))
    variableList = [(paramType, [(_.kodnote, _.kod) for _ in ParamVariableList if _.paramtype == paramType]) for paramType in paramTypeList]
    reconstructedLogStructs = ""

    if request.method == 'GET':
        if len(globalList) == 0:
            globalList = logDefsList
        else:
            logDefsList = globalList
        logger.debug(f"{request.GET}")
        # logger.debug(f"{globalList}")
        """
        'down': ['form_row_2']
        'up': ['form_row_2']
        --> these are coming with up and down : 'key': ['s'], 'value': ['Learning client username:']
        'add': ['form_row_2']
        'delete': ['form_row_3']
        'structure': [''] ??
        """
        if check_existence(request.GET.get('up')):
            _current_index = int(request.GET.get('up').split("_")[2])-1
            _new_index = _current_index-1 if _current_index > 0 else 0
            _selected_element = globalList.pop(_current_index).copy()
            _selected_element[request.GET.get('key')] = request.GET.get('value')
            globalList.insert(_new_index, _selected_element)
            # logger.debug(f"current globalList {globalList}")
            # structList = request.GET.get('structure').split(",") if check_existence(request.GET.get('structure')) and request.GET.get('structure').split(",") != globalList else globalList
            logger.debug(f"current globalList after move up {globalList}")
            logDefsList = globalList
            reconstructedLogStructs = reconstruct_log_definition(logDefsList)

        elif check_existence(request.GET.get('down')):
            _current_index = int(request.GET.get('down').split("_")[2]) - 1
            _new_index = _current_index + 1 if _current_index < len(globalList) else len(globalList)
            _selected_element = globalList.pop(_current_index).copy()
            _selected_element[request.GET.get('key')] = request.GET.get('value')
            globalList.insert(_new_index, _selected_element)
            logger.debug(f"current globalList after move down {globalList}")
            logDefsList = globalList
            reconstructedLogStructs = reconstruct_log_definition(logDefsList)

        elif check_existence(request.GET.get('add')):
            _current_index = int(request.GET.get('add').split("_")[2]) - 1
            # globalList.insert(0, globalList[_current_index])
            _selected_element = globalList[_current_index]
            _selected_element[request.GET.get('key')] = request.GET.get('value')
            globalList.insert(_current_index + 1, _selected_element)
            logger.debug(f"current globalList after add {globalList}")
            logDefsList = globalList
            reconstructedLogStructs = reconstruct_log_definition(logDefsList)

        elif check_existence(request.GET.get('delete')):
            _current_index = int(request.GET.get('delete').split("_")[2]) - 1
            del globalList[_current_index]
            logger.debug(f"current globalList after delete element {globalList}")
            logDefsList = globalList
            reconstructedLogStructs = reconstruct_log_definition(logDefsList)

        else:
            logDefsList = logDefDetail.get_logdefs()
            logDefsList = logDefsList if logDefsList else [{"d": "generic"}, {"s": "string"}]
            globalList = []

    if request.method == 'POST':
        logger.debug(f"{request.POST}")
        """
        'd': ['funcname', 'macaddress', 'hostname'],
        's': ['client', 'hostname updated to '], 
        'new_logdefs': ["{'d':'funcname'},{'s':'client'},{'d':'macaddress'},
                            {'s':'hostname updated to '},{'d':'hostname'}"]
        """
        new_logfields = request.POST.getlist("d")
        new_logsarr = request.POST.getlist("s")
        new_logdefs_dict_list = json.loads(f'[{request.POST.get("new_logdefs")}]')
        new_logdefs = [json.dumps(_, indent=4) for _ in new_logdefs_dict_list]
        # logger.debug(f"NEW LOGDEFS : {new_logdefs}")
        new_logstructs = reconstruct_log_definition(new_logdefs_dict_list if new_logdefs_dict_list else [])
        # logger.debug(f"NEW LOGSTRUCTS : {new_logstructs}")

        logDefDetail.logfields = new_logfields
        logDefDetail.logsarr = new_logsarr
        logDefDetail.logdefs = new_logdefs
        logDefDetail.logstructs = new_logstructs
        try:
            logDefDetail.save()
            template_message_show(request, "success", "Changes saved successfully")
        except Exception as err:
            logger.exception(f"An error occurred while trying to update update logdefdetail. ERROR IS : {err}")
            template_message_show(request, "error", f"Failed to update changes because {err}")

        logDefDetail = LogDefinitionDetails.objects.get(id=id)
        logDefsList = logDefDetail.get_logdefs()

        globalList = []

    # log event sample list from elasticsearch
    # FOR ENVIRONMENT THAT ELASTIC RUN -------------------------------------------------------------------------
    if check_environment_for_elastic():
        logEventSamples = []
        try:
            logCode = logDefDetail.logcode
            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number,
                                               sniff_on_start=True, request_timeout=2)
            _body = '{"size": 0, "query": {"bool": {"must": [{"match": {"logndx": {"query": "%s", "boost": 1.0}}}], "adjust_pure_negative": true, "boost": 1.0}}, "sort": [{"id": {"order": "desc"}}], "aggregations": {"byEvent": {"terms": {"field": "event", "size": 10, "min_doc_count": 1, "show_term_doc_count_error": false, "order": [{"_count": "desc"}, {"_key": "asc"}]}}}}' % logCode
            _body = json.loads(_body)
            search = elastic_connection.search(index="atibalogs", body=_body)
            logEventSamples = search["aggregations"]["byEvent"]["buckets"]
            logger.debug(f"Log event samples are :  {logEventSamples}")
            logEventSamples = [x["key"] for x in logEventSamples]
        except Exception as err:
            logger.error(f"An error occurred while trying to connect elasticsearch for log event samples : {err}")
    # FOR LOCAL WITH NO ELASTIC ---------------------------------------------------------------------------------
    else:
        logEventSamples = [_["_source"]["event"] for _ in hitsListForTest]

    paginator = Paginator(logEventSamples, 15)
    page = request.GET.get('page')
    try:
        logEventSamples = paginator.page(page)
    except PageNotAnInteger:
        logEventSamples = paginator.page(1)
    except EmptyPage:
        logEventSamples = paginator.page(paginator.num_pages)

    context = {
        'route': route, 'logDefDetail': logDefDetail, 'logEventSamples': logEventSamples, 'variableList': variableList,
        'logDefsList': logDefsList, 'reconstructedLogStructs': reconstructedLogStructs,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/logdefdetails_edit.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def logdefdetails_edit2(request, id):
    """
    logdefinitions edit with drag and drop
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()

    route = "Configure Parameters"
    logDefDetail = LogDefinitionDetails.objects.get(id=id)
    logDefsList = logDefDetail.get_logdefs()
    # logger.debug(f"logDefsList : {logDefsList}")
    logDefsList = logDefsList if logDefsList else [{"d": "generic"}, {"s": "string"}]
    # logger.debug(f"logDefsList : {logDefsList}")
    ParamVariableList = ParamVariables.objects.all()
    paramTypeList = list(set([_.paramtype for _ in ParamVariableList]))
    variableList = [(paramType, [(_.kodnote, _.kod) for _ in ParamVariableList if _.paramtype == paramType]) for
                    paramType in paramTypeList]

    reconstructedLogStructs = ""

    if request.method == 'POST' and not request.is_ajax():
        logger.debug(f"{request.POST}")
        """
        'd': ['funcname', 'macaddress', 'hostname'],
        's': ['client', 'hostname updated to '], 
        'new_logdefs': ["{'d':'funcname'},{'s':'client'},{'d':'macaddress'},
                            {'s':'hostname updated to '},{'d':'hostname'}"]
        """
        new_logfields = request.POST.getlist("d")
        new_logsarr = request.POST.getlist("s")
        new_logdefs_dict_list = json.loads(f'[{request.POST.get("new_logdefs")}]')
        new_logdefs = [json.dumps(_, indent=4) for _ in new_logdefs_dict_list]
        logger.debug(f"NEW LOGDEFS for id {id}: {new_logdefs}")
        new_logstructs = reconstruct_log_definition(new_logdefs_dict_list if new_logdefs_dict_list else [])
        logger.debug(f"NEW LOGSTRUCTS for id {id} : {new_logstructs}")

        logDefDetail.logfields = new_logfields
        logDefDetail.logsarr = new_logsarr
        logDefDetail.logdefs = new_logdefs
        logDefDetail.logstructs = new_logstructs
        try:
            logDefDetail.save()
            template_message_show(request, "success", "Changes saved successfully")
        except Exception as err:
            logger.exception(f"An error occurred while trying to update update logdefdetail. ERROR IS : {err}")
            template_message_show(request, "error", f"Failed to update changes because {err}")

        logDefDetail = LogDefinitionDetails.objects.get(id=id)
        logDefsList = logDefDetail.get_logdefs()

    # log event sample list from elasticsearch
    # FOR ENVIRONMENT THAT ELASTIC RUN -------------------------------------------------------------------------
    if check_environment_for_elastic():
        logEventSamples = []
        try:
            logCode = logDefDetail.logcode
            elastic_connection = Elasticsearch(es_host_list, scheme='http', port=es_port_number, sniff_on_start=True,
                                               request_timeout=2)
            _body = '{"size": 0, "query": {"bool": {"must": [{"match": {"logndx": {"query": "%s", "boost": 1.0}}}], "adjust_pure_negative": true, "boost": 1.0}}, "sort": [{"id": {"order": "desc"}}], "aggregations": {"byEvent": {"terms": {"field": "event.keyword", "size": 10, "min_doc_count": 1, "show_term_doc_count_error": false, "order": [{"_count": "desc"}, {"_key": "asc"}]}}}}' % logCode
            _body = json.loads(_body)
            search = elastic_connection.search(index="atibalogs", body=_body)
            logEventSamples = search["aggregations"]["byEvent"]["buckets"]
            logger.debug(f"Log event samples are :  {logEventSamples}")
            logEventSamples = [x["key"] for x in logEventSamples]
        except Exception as err:
            logger.error(f"An error occurred while trying to connect elasticsearch for log event samples : {err}")
    # FOR LOCAL WITH NO ELASTIC ---------------------------------------------------------------------------------
    else:
        logEventSamples = [_["_source"]["event"] for _ in hitsListForTest]

    linePerPage = 5
    totalSample = len(logEventSamples)
    totalPages = math.ceil(totalSample/linePerPage)
    logger.debug(f"{totalSample} record {totalPages} page for {linePerPage} record on each page")

    if request.is_ajax():
        logger.debug(f"Ajax request : {request.POST}")
        action = request.POST.get('action')
        if action == "page":
            direction = request.POST.get('direction')
            currentPage = int(request.POST.get('currentPage'))
            slicingOperator = currentPage - 1 if 1 <= currentPage <= totalPages else 0
            if direction == "prev":

                logEventSample = logEventSamples[(slicingOperator - 1)*linePerPage:slicingOperator*linePerPage]
                currentPage -= 1 if 1 < currentPage <= totalPages else 0
                try:
                    top_stats = tracemalloc.take_snapshot().statistics('lineno')
                    total_size, unit = take_memory_usage(top_stats)
                    logger.info(f"Memory allocation  {total_size} {unit}")
                    memory_tracer.info(f"{total_size}")
                    tracemalloc.stop()
                except:
                    logger.debug("tracemalloc stopped before somehow")
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return JsonResponse({'command': 1, 'logEventSample': logEventSample, 'currentPage': currentPage},
                                    status=200)
            elif direction == "next":

                logEventSample = logEventSamples[currentPage*linePerPage:(currentPage + 1)*linePerPage]
                currentPage += 1 if 1 <= currentPage < totalPages else 0
                try:
                    top_stats = tracemalloc.take_snapshot().statistics('lineno')
                    total_size, unit = take_memory_usage(top_stats)
                    logger.info(f"Memory allocation  {total_size} {unit}")
                    memory_tracer.info(f"{total_size}")
                    tracemalloc.stop()
                except:
                    logger.debug("tracemalloc stopped before somehow")
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return JsonResponse({'command': 1, 'logEventSample': logEventSample, 'currentPage': currentPage},
                                    status=200)
    else:
        logEventSample = logEventSamples[:linePerPage]

    context = {
        'route': route, 'logDefDetail': logDefDetail,
        # 'logEventSamples': logEventSamples,
        'logEventSamples': logEventSample,
        'totalPages': totalPages,
        'variableList': variableList,
        'logDefsList': logDefsList, 'reconstructedLogStructs': reconstructedLogStructs,
    }

    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/logdefdetails_edit2.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def check_interval_tables(request):
    """

    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "general"

    if request.is_ajax():
        logger.debug(f"requast : {request.POST}")
        pass
    else:
        pass

    start_date = (datetime.datetime.now() - datetime.timedelta(days=150))
    end_date = datetime.datetime.now()
    param_or_code = "<304008>"
    src_unique_id = "evap"
    interval_obj = IntervalDataChart(enddate=end_date, startdate=start_date,
                                     paramorcode=param_or_code, uniqueid=src_unique_id)
    # interval_obj = IntervalDataChart()
    logger.debug(f"Interval Object start date : {interval_obj.startdate} - end date : {interval_obj.enddate}")
    # chart_values = [[120, 130, 270, 150, 245], [100, 100, 200, 175, 200], [50, 70, 140, 100, 165]]
    chart_values = [interval_obj.upperbound, interval_obj.count, interval_obj.lowerbound]
    # chart_labels = ["5 min"]*len(chart_values[0])
    chart_labels = interval_obj.labellist
    # logger.debug(f" -> values : {chart_values}")
    # logger.debug(f" -> label list : {chart_labels}")

    context = {
        'route': route, "chart_labels": chart_labels, "graph_data": chart_values,
        "start_date": start_date, "end_date": end_date, "param_or_code": param_or_code, "src_unque_id": src_unique_id
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/check_interval_tables.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def monitoring_atiba(request):
    """
    to monitor ui render times and memory allocations
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = 'general'
    # threadID = _thread.start_new_thread(timeout_test, (30, ))

    # -> Alarms for anomalies chart
    res = Anomalies.objects.all().values('anomalytype').annotate(total=Count('anomalytype')).order_by('total')
    # logger.debug(f"{res}")
    anomaly_labels = [GeneralParameterDetail.objects.filter(kisakod="ANMLTYPE").get(kod=int(x['anomalytype'])).kisaack for x in res]
    anomaly_values = [int(x['total']) for x in res]
    totalAlarm = sum(anomaly_values)
    # logger.debug(f"Anomaly chart labels and values : {anomaly_labels} , {anomaly_values}")
    # -> for view function duration chart
    view_list, home_charts_json, charts_jsons, charts_tuples = get_ui_charts_data('Log/ATIBAreportTimer.log', days_from_now=10)
    todaysTotalTime = (round(sum(read_timer_logs('Log/ATIBAreportTimer.log', days_from_now=0)[2])*100)/100)
    logger.debug(f"read timer logs returned : {todaysTotalTime}")
    # -> for view function memory usage chart
    m_view_list, m_home_charts_json, m_charts_jsons, m_charts_tuples = get_ui_charts_data('Log/ATIBAreportMemoryTracer.log', days_from_now=10)
    todaysTotalMemory = (round(sum(read_timer_logs('Log/ATIBAreportMemoryTracer.log', days_from_now=0)[2]) * 100) / 100)

    # rename_old_log_file("Log", "sacma", "txt")

    context = {
        'route': route,
        'anomaly_values': anomaly_values, 'anomaly_labels': anomaly_labels,
        'views_list': set(view_list), 'chart_tuples': charts_tuples,
        'chart_jsons': charts_jsons, 'home_chart_json': home_charts_json,
        'm_views_list': set(m_view_list), 'm_chart_tuples': m_charts_tuples,
        'm_chart_jsons': m_charts_jsons, 'm_home_chart_json': m_home_charts_json,
        'totalAlarm': totalAlarm, 'todaysTotalTime': todaysTotalTime, 'todaysTotalMemory': todaysTotalMemory,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        # logger.debug(f"{top_stats[:20]}")
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/monitoring_atiba.html', context)


globalStartDate, globalEndDate, globalLogFile = None, None, None


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def monitoring_atiba_uilogs(request):
    """
    To inspect detail information from my own ui logs
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    global globalBool, globalStartDate, globalEndDate, globalLogFile

    _service_list = iamatiba_service_list
    _priList = ["DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL", "ALERT", "EMERGENCY"]
    _priTupleList = []
    _pri_filter = request.GET.get("pri_filter") if check_existence(
        request.GET.get("pri_filter")) and request.GET.get("pri_filter") in _priList else None
    _sort_by = request.GET.get("sort_by") if check_existence(
        request.GET.get("sort_by")) and 0 <= int(request.GET.get("sort_by")) < 8 else None
    page = request.GET.get('page')

    _today = datetime.date.today()
    if request.method == "POST":
        logger.debug(f"form : {request.POST}")
        globalLogFile = request.POST.get("log_file")
        globalEndDate = datetime.datetime.strptime(request.POST.get('end_date'), "%Y-%m-%d").date()
        globalStartDate = datetime.datetime.strptime(request.POST.get('start_date'), "%Y-%m-%d").date()
    else:
        if not globalEndDate and not globalStartDate:
            globalEndDate = _today
            globalStartDate = globalEndDate - datetime.timedelta(days=1)

    serviceName = next(filter(lambda x: x["log_file"] == globalLogFile, _service_list),
                       None) if globalLogFile else None
    serviceName = serviceName["name"] if serviceName else "UI Server"

    my_logs, parsed_logs, _success = read_your_own_logs(end_date=globalEndDate, start_date=globalStartDate,
                                                        file_with_path=globalLogFile)
    if _success:
        if not my_logs:
            template_message_show(request, "info", "Successfully read file, but it appears empty between these days")
        elif not parsed_logs:
            template_message_show(request, "error", "Successfully read file, but none of them could be parsed")
        elif len(my_logs) > len(parsed_logs):
            template_message_show(request, "warning", f"Successfully read file, but {len(parsed_logs)} of "
                                                      f"{len(my_logs)} could parsed")
    else:
        template_message_show(request, "error", "Failed to read file. You can find out what happened in UI Server logs")

    my_logs.reverse()
    parsed_logs.reverse()

    totalCount = len(parsed_logs)

    for _ in _priList:
        counts = 0
        counts += len(list(filter(lambda x: x[0] == _, parsed_logs)))
        # logger.debug(f"{_} logs count : {counts}")
        _priTupleList.append((_, counts))
    # logger.debug(f"_priList with counts {_priTupleList}")

    if _pri_filter:
        parsed_logs = list(filter(lambda x: x[0] == _pri_filter, parsed_logs))

    if _sort_by:

        globalBool = not globalBool if not page else globalBool
        parsed_logs.sort(key=lambda x: x[int(_sort_by)], reverse=globalBool)

    paginator = Paginator(parsed_logs, record_per_page)
    # page = request.GET.get('page')
    try:
        parsed_logs = paginator.page(page)
    except PageNotAnInteger:
        parsed_logs = paginator.page(1)
    except EmptyPage:
        parsed_logs = paginator.page(paginator.num_pages)

    context = {
        'my_logs': my_logs, 'parsed_logs': parsed_logs, 'startDate': globalStartDate, 'endDate': globalEndDate,
        'totalCount': totalCount, 'serviceList': _service_list, 'logFile': globalLogFile, 'serviceName': serviceName,
        'priList': _priTupleList,
        # 'priList': _priList,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        # logger.debug(f"{top_stats[:20]}")
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/monitoring_atiba_logs.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def maintenance(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()

    route = "maintenance"

    context = {
        "route": route,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/maintenance.html', context)


# @licence_required
# @login_required
@xframe_options_sameorigin
@csrf_exempt
def iamatiba_services(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()

    _service_list = iamatiba_service_list
    route = "services"

    if request.is_ajax():
        logger.debug(f"request : {request.POST}")
        _action = request.POST.get('action')
        if _action == "serviceCheck":
            _serviceName = request.POST.get('name')
            _service_check_result = check_service_status(_serviceName)
            logger.debug(f"Service Check Result is : {_service_check_result}")
            return JsonResponse({"command": 0, "result": json.loads(json.dumps(_service_check_result))}, status=200)
        elif _action == "serviceStart":
            _serviceName = request.POST.get('name')
            _service_start_result = start_iamatiba_service(_serviceName)
            logger.debug(f"Service Start Result is : {_service_start_result}")
            return JsonResponse({"command": 0, "result": json.loads(json.dumps(_service_start_result))}, status=200)
        elif _action == "serviceRestart":
            _serviceName = request.POST.get('name')
            _service_restart_result = restart_iamatiba_service(_serviceName)
            logger.debug(f"Service Restart Result is : {_service_restart_result}")
            return JsonResponse({"command": 0, "result": json.loads(json.dumps(_service_restart_result))}, status=200)
        elif _action == "serviceStop":
            _serviceName = request.POST.get('name')
            _service_stop_result = stop_iamatiba_service(_serviceName)
            logger.debug(f"Service Stop Result is : {_service_stop_result}")
            return JsonResponse({"command": 0, "result": json.loads(json.dumps(_service_stop_result))}, status=200)

    context = {
        "route": route, "service_list": _service_list,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/maintenance.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def cluster(request):
    """
    To see the cluster structure, master node, now which one is active and their health status.
    In order to collect these data we use an http backend service which get the request and send a response in form
    of a list of json. Every json consist of data about a node
    """
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    route = "Status"
    inSlaveNode = check_psql_is_recovery()

    _nodeList = AtibaHA.objects.all()
    _nodeCount = len(_nodeList)
    _vrip_check_set = set(list(list(AtibaHA.objects.values_list("vrip", flat=True))))

    _vrip = _nodeList[0].vrip if _nodeList else None
    _vrip = _vrip if len(_vrip_check_set) < 2 else "There is more than one Virtual Router IP the db !!"

    # _service_address = f"http://{es_host_list[0]}:port_number_of service"
    # _response = requests.get(_service_address)
    # logger.debug(f"Response of service at {_service_address} : {_response}")

    # _api_port = atibaApiService_PORT
    # _api_key = atibaApiService_API_KEY
    #
    # response = requests.get(f"http://localhost:{_api_port}/health_check?api_key={_api_key}")
    # response_json = response.json()
    # logger.warning(f"Api health response is : {response_json} in type of {type(response_json)}")
    # logger.warning(f"response code : {response_json.get('code')}")

    context = {
        "route": route, 'inSlaveNode': inSlaveNode, 'vrip': _vrip, 'nodeList': _nodeList, 'nodeCount': _nodeCount,
    }
    try:
        top_stats = tracemalloc.take_snapshot().statistics('lineno')
        total_size, unit = take_memory_usage(top_stats)
        logger.info(f"Memory allocation  {total_size} {unit}")
        memory_tracer.info(f"{total_size}")
        tracemalloc.stop()
    except:
        logger.debug("tracemalloc stopped before somehow")
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/cluster.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def cluster_node_settings(request, id):
    """
    To node settings.
    """
    time_triggered = datetime.datetime.now()
    route = "Node Settings"
    # node resource usage graph operations;
    _node = AtibaHA.objects.get(id=id)
    _cpuUsage = _node.cpuusage if _node.cpuusage else []
    _ramUsage = _node.ramusage if _node.ramusage else []
    _diskUsage = _node.diskusage if _node.diskusage else []
    _list_length = max(len(_cpuUsage), len(_ramUsage), len(_diskUsage))
    _chart_labels = ["-"] * _list_length
    _chart_values = [
        [float(_) for _ in _cpuUsage],
        [float(_) for _ in _ramUsage],
        [float(_) for _ in _diskUsage]
    ]

    if request.method == "POST":
        logger.debug(f"in settings of node {_node.nodeid} form values : {request.POST}")
        _check_interval = request.POST.get('check_interval') if check_existence(request.POST.get('check_interval')) else None
        # _node.usagecheckinterval = _check_interval if _node.usagecheckinterval != _check_interval else _node.usagecheckinterval
        _node.usagecheckinterval = _check_interval

        try:
            _node.save()
            template_message_show(request, "success", f"Changes saved successfully")
        except Exception as err:
            logger.error(f"An error occurred trying to save changes for {_node.nodeid}. ERROR IS : {err}")
            template_message_show(request, "error", f"An Error occurred, ERROR IS : {err}")

    context = {
        'route': route, 'node': _node,
        'chart_labels': _chart_labels, 'chart_values': _chart_values,
    }
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/cluster.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def cluster_add_slave(request, id):
    """
    To add a slave part of existing cluster structure from the master node.

    """
    time_triggered = datetime.datetime.now()
    route = "Add Slave"

    _node = AtibaHA.objects.get(id=id)
    _master_ip = _node.ipaddress
    _vr_ip = _node.vrip
    _existing_nodes = list(AtibaHA.objects.values_list("ipaddress", flat=True))
    # if you are adding nodes to working single node machine,
    # you need to add 1 as value of elasticsearch ilm policy number of replicas, else pass this step.
    # To check if it is needed, ilm operations will make if api process finish successfully;
    _elastic_ilm_needed = True if len(_existing_nodes) == 1 else False

    _nodes_without_master = [_ for _ in _existing_nodes if _ != _master_ip]
    logger.debug(f"Existing IPs list : {_existing_nodes}")
    logger.debug(f"Not master IPs list : {_nodes_without_master}")

    _form = AddNodeForm(request.POST or None)

    if request.method == "POST":
        """
        POST method content : <QueryDict: {
                'csrfmiddlewaretoken': ['3oEd07Co1cuaZua5xXtLaM8Iy6UOgPb9obJSYuPoCv3pCSyh2FDhds8DtM3whxnB'], 
                'newnodes': ['192.168.10.1, 192.168.10.12']
        }>
        
        request.POST.get('newnodes') = '192.168.10.1, 192.168.10.12'
        """
        logger.debug(f"POST method content : {request.POST}")
        # logger.debug(f"new nodes : {request.POST.get('newnodes')}")
        logger.debug(f"Is Form Valid ? : {_form.is_valid()}")
        if _form.is_valid():
            # _new_nodes = request.POST.get('newnodes')
            _new_nodes = _form.cleaned_data.get('newnodes')
            _new_nodes = _new_nodes.replace(" ", "")
            _new_node_ips = _new_nodes.split(",")
            logger.debug(f"new node ips : {_new_node_ips}")

            if len(_existing_nodes) == 1 and len(_new_node_ips) < 2:
                template_message_show(request, "warning", f"Atiba Cluster needs at least 3 nodes to work ! Add 2 node")
                context = {
                    'route': route, 'node': _node, 'existing_backups': _nodes_without_master,
                    'form': _form
                }
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return render(request, 'AgentRoot/cluster.html', context)

            # NOTE THAT : if your system currently work with single node and when you add two new node and make it
            #             cluster, then you have to change number of replicas from 0 to 1 in elasticsearch ilm policy,
            #             off course you have to change number of replicas form 1 to 0 if remove all nodes and make
            #             single node system.....

            # sending a request to atibaApiService
            # we keep api_key in api_port in passes.py file
            _api_port = atibaApiService_PORT
            # _api_key = atiba_encrypt("ISTIKLAL")  # key "S3V0SGFzQ2Vua0t1ckZhdGw2atM1Tgun1bwCEECThOs=", that api expect to see
            _api_key = atibaApiService_API_KEY

            # _vr_ip = ""  # this value is lying on my database
            # _master_ip = '192.168.250.11'  # this value is lying on my database
            # _node_ip = '192.168.250.12'  # this value will be given in the loop, to send http request to each node ip
            # _nodes_without_master = ['127.0.0.1', '192.168.250.12']  # these are lying on my database
            # _new_node_ips = ['192.168.250.13', '192.168.250.14']  # this will be come from form !!
            _all_nodes = [_master_ip] + _nodes_without_master + _new_node_ips
            # logger.debug(f"all nodes list : {_all_nodes}")
            # node-1 (it's master Node) and node-2 (it's right after the master) must be like [ master, data ],
            # all the others like [ master, voting_only, data ]. It will be given from python..
            _first_two_ips = _all_nodes[:2]
            _first_three_ips = _all_nodes[:3]

            _api_process_loop_errors = []
            for _node_ip in _all_nodes:
                _pri_number = 150 - _all_nodes.index(_node_ip) * 10
                dictObject = {
                    'vrip': _vr_ip,
                    'myIP': _node_ip,
                    'nodeID': 'node-'+_node_ip.replace(".", ""),
                    'isMaster': _node_ip == _master_ip,
                    'priorityNumber': _pri_number,
                    'masterIP': _master_ip,
                    'nodeListWithoutMaster': _nodes_without_master,
                    'newNodesList': _new_node_ips,
                    'allNodesList': _all_nodes,
                    'roles': f"{'[ master, data ]' if _node_ip in _first_two_ips else '[ master, voting_only, data ]'}",
                    'isPostgreActive': f"{_node_ip in _first_three_ips}",
                    'removeNode': ""
                }
                logger.debug(f"nodes request object : {dictObject}")

                if check_environment_for_production():
                    # for production
                    response = None
                    try:
                        response = requests.post(f"http://{_node_ip}:{_api_port}/cluster/add_node?api_key={_api_key}",
                                                 headers={'Content-type': 'application/json', 'Accept': 'text/plain'},
                                                 data=json.dumps(dictObject))
                    except Exception as err:
                        _api_process_loop_errors.append(_node_ip)
                        logger.exception(
                            f"An error occurred trying to send request api on {_node_ip}:{_api_port}. ERROR IS : {err}")
                    if response:
                        logger.info(f"We got response from api : {response}")
                    # we are doing anything with response on production environment for now ...
                else:
                    # for development
                    logger.warning(f"Working on development environment, request will be sent to localhost")
                    response = None
                    try:
                        response = requests.post(f"http://localhost:{_api_port}/cluster/add_node?api_key={_api_key}",
                                                 headers={'Content-type': 'application/json', 'Accept': 'text/plain'},
                                                 data=json.dumps(dictObject))
                    except Exception as err:
                        _api_process_loop_errors.append(_node_ip)
                        logger.exception(
                            f"An error occurred trying to send request api on localhost:{_api_port}. ERROR IS : {err}")
                    logger.debug(f"response from api : {response if response else 'no response'}")
                    logger.debug(f"json response from api : {response.json() if response else 'no response'}")
            if not _api_process_loop_errors:  # if list is empty;
                for _ in _new_node_ips:
                    AtibaHA.objects.create(ipaddress=_, nodeid=f'node-{_.replace(".", "")}',
                                           vrip=_vr_ip, interfacename="eth0", pgstatus=(_ in _first_three_ips))
                # v---------------------------------------------------------------ELASTIC ILM-------------------------v
                if _elastic_ilm_needed:
                    # if single node -> "number_of_replicas": 0, if cluster -> "number_of_replicas": 1,
                    _log_lifetime = list(SystemParameters.objects.all())[0].loglifetime if SystemParameters.objects.count() > 0 else 7
                    logger.info(f"elasticsearch number of replicas will be changed to 1.")
                    _body = {
                        "policy": {
                            "phases": {
                                "cold": {
                                    "min_age": "7d",
                                    "actions": {
                                        "freeze": {},
                                        "allocate": {
                                            "number_of_replicas": 1,
                                            "include": {},
                                            "exclude": {},
                                            "require": {
                                                "temp": "cold"
                                            }
                                        }
                                    }
                                },
                                "hot": {
                                    "actions": {
                                        "rollover": {
                                            "max_primary_shard_size": "40GB",
                                            "max_age": "7d"
                                        }
                                    }
                                },
                                "delete": {
                                    "min_age": f"{_log_lifetime}d",
                                    "actions": {
                                        "delete": {}
                                    }
                                }
                            }
                        }
                    }
                    logger.debug(f"Body for elastic policy update : {_body}")
                    try:
                        elastic_connection = Elasticsearch(es_host_list,
                                                           scheme='http',
                                                           port=es_port_number, sniff_on_start=True, request_timeout=2)
                        es_put_result = elastic_connection.ilm.put_lifecycle("atibalogs_policy", body=_body)
                        logger.info(f"Result of elasticsearch policy change : {es_put_result}")
                    except Exception as err:
                        logger.exception(
                            f"An error occurred trying to change number_of_replica policy in elastic. ERROR IS : {err}")
                # ^---------------------------------------------------------------ELASTIC ILM-------------------------^
                template_message_show(request, "success", f"Successfully added nodes on IP : {_new_node_ips}")
                timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
                return redirect("cluster")
            else:
                logger.error(f"Some errors occurred in api on : {_api_process_loop_errors}")
                template_message_show(request, "error", f"Some errors occurred in api on : {_api_process_loop_errors}")

    context = {
        'route': route, 'node': _node, 'existing_backups': _nodes_without_master,
        'form': _form
    }
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/cluster.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def cluster_make_it_slave(request, id):
    """
    To make a single node be a slave part of a cluster structure.
    In this view we will make some changes to more than one configuration or yaml files save them all on this server
    and then reboot the server for the changes to work. But we also have to make some changes on the master node with
    the cluster_add_slave view
    """
    time_triggered = datetime.datetime.now()
    route = "Make Slave"

    _node = AtibaHA.objects.get(id=id)

    context = {
        'route': route, 'node': _node,
    }
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'AgentRoot/cluster.html', context)


@licence_required
@login_required
@xframe_options_sameorigin
@csrf_exempt
def cluster_remove_slave(request, id):
    """
    To remove a slave from the existing cluster structure.
    """
    time_triggered = datetime.datetime.now()
    route = "Remove Slave"

    _node = AtibaHA.objects.get(id=id)
    _nodeList = AtibaHA.objects.all()
    _nodeCount = len(_nodeList)
    if _nodeCount < 4:
        # if you try to remove a node using url from address bar on browser, i'll block it in here
        template_message_show(
            request,
            "warning",
            f"Atiba Cluster needs at least 3 nodes, you got {_nodeCount}, remove operation is not allowed in this case")
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return redirect("cluster")

    # if request.is_ajax():
    #     _removal_node_id = int(request.POST.get('node_id'))
    #
    #     return JsonResponse({'command': 1}, status=200)

    _removal_node = None
    try:
        _removal_node = AtibaHA.objects.get(id=id)
    except Exception as err:
        logger.exception(f"An error occurred trying to get node with id {id}. ERROR IS : {err}")

    _node_objects_list = list(AtibaHA.objects.all())
    _master_node = None
    for _ in _node_objects_list:
        if _.is_master():
            _master_node = _
            break
    if _removal_node and _master_node:  # we got master node and removal node both;
        _vr_ip = _master_node.vrip
        _master_ip = _master_node.ipaddress
        _removal_node_ip = _removal_node.ipaddress
        _existing_nodes = list(AtibaHA.objects.values_list("ipaddress", flat=True))
        # we don't want removal_node_ip in ip lists, that's why exclude this with master_ip like below;
        _nodes_without_master = [_ for _ in _existing_nodes if _ != _master_ip and _ != _removal_node_ip]
        _new_node_ips = []
        logger.debug(f"Existing IPs list : {_existing_nodes}")
        logger.debug(f"Not master IPs list : {_nodes_without_master}")
        logger.debug(f"Removing IP : {_removal_node_ip}")

        _api_port = atibaApiService_PORT
        _api_key = atibaApiService_API_KEY

        _all_nodes = [_master_ip] + _nodes_without_master + _new_node_ips

        _first_two_ips = _all_nodes[:2]
        _first_three_ips = _all_nodes[:3]

        _api_process_loop_errors = []
        for _node_ip in _all_nodes:
            _pri_number = 150 - _all_nodes.index(_node_ip) * 10
            dictObject = {
                'vrip': _vr_ip,
                'myIP': _node_ip,
                'nodeID': 'node-' + _node_ip.replace(".", ""),
                'isMaster': _node_ip == _master_ip,
                'priorityNumber': _pri_number,
                'masterIP': _master_ip,
                'nodeListWithoutMaster': _nodes_without_master,
                'newNodesList': _new_node_ips,
                'allNodesList': _all_nodes,
                'roles': f"{'[ master, data ]' if _node_ip in _first_two_ips else '[ master, voting_only, data ]'}",
                'isPostgreActive': f"{_node_ip in _first_three_ips}",
                'removeNode': _removal_node_ip
            }
            logger.debug(f"nodes request object : {dictObject}")

            if check_environment_for_production():
                # for production
                response = None
                try:
                    response = requests.post(f"http://{_node_ip}:{_api_port}/cluster/remove_node?api_key={_api_key}",
                                             headers={'Content-type': 'application/json', 'Accept': 'text/plain'},
                                             data=json.dumps(dictObject))
                except Exception as err:
                    logger.exception(
                        f"An error occurred trying to send request api on {_node_ip}:{_api_port}. ERROR IS : {err}")
                    _api_process_loop_errors.append(_node_ip)
                if response:
                    logger.info(f"We got response from api : {response}")
                # we are doing anything with response on production environment for now ...
            else:
                # for development
                logger.warning(f"Working on development environment, request will be sent to localhost")
                response = None
                try:
                    response = requests.post(f"http://localhost:{_api_port}/cluster/remove_node?api_key={_api_key}",
                                             headers={'Content-type': 'application/json', 'Accept': 'text/plain'},
                                             data=json.dumps(dictObject))
                except Exception as err:
                    logger.exception(
                        f"An error occurred trying to send request api on localhost:{_api_port}. ERROR IS : {err}")
                    _api_process_loop_errors.append(_node_ip)
                logger.debug(f"response from api : {response if response else 'no response'}")
                logger.debug(f"json response from api : {response.json() if response else 'no response'}")
        if not _api_process_loop_errors:  # if list is empty;
            _removal_node.delete()
            template_message_show(
                request,
                "success",
                f"Node successfully removed from cluster (id : {id}, ip : {_removal_node_ip})")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect("cluster")
        else:
            logger.error(f"Some errors occurred in api on : {_api_process_loop_errors}")
            template_message_show(
                request,
                "error",
                f"Some errors occurred in api on : {_api_process_loop_errors} trying to remove {_removal_node_ip}")
            timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
            return redirect("cluster")
    else:  # we couldn't get master node and removal node information from postgresql;
        template_message_show(
            request,
            "warning",
            f"No master node or removing non existing node (id:{id}). There may be lock of info in the database")
        timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
        return redirect("cluster")

    # context = {
    #     'route': route, 'node': _node,
    # }
    # timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    # return render(request, 'AgentRoot/cluster.html', context)


@xframe_options_sameorigin
def help_pages(request):
    time_triggered = datetime.datetime.now()
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()
    # logger.debug(f"Tracemalloc is trcing ? : {tracemalloc.is_tracing()}")
    # if subprocess.call("python --version", shell=True) == 0:
    #     x = subprocess.call("python --version", shell=True)
    #     logger.debug(f"Python version command {x}")
    #     t = subprocess.check_output("python --version", shell=True)
    #     t = t.decode("utf-8").replace("\n", "")
    #     logger.debug(f"Python version is : {t}")
    #     template_message_show(request, "success", f"You are using {t}")
    #     y = subprocess.check_call("dir", shell=True)
    #     logger.debug(f"y is {y}")
    #     if subprocess.call("cd ATIBA_REPORT", shell=True) == 0:
    #         logger.debug("z is ok")
    #         template_message_show(request, "info", "z worked")
    #     else:
    #         logger.debug("z didn't work")
    #         template_message_show(request, "error", "z didn't work")

    # sql_query_file_path = f"{MEDIA_ROOT}/deneme.sql"
    # _ifsuccess, _errorinfo, _dur = execute_sql_file(sql_query_file_path, database_name='atibadb')

    template_message_show(request, 'info', "Welcome to help pages")
    context = {
        'help_psqlDateTimeFormats': help_psqlDateTimeFormats,
        'help_psqlStringOps': help_psqlStringOps,
    }
    top_stats = tracemalloc.take_snapshot().statistics('lineno')
    total_size, unit = take_memory_usage(top_stats)
    logger.info(f"Memory allocation  {total_size} {unit}")
    memory_tracer.info(f"{total_size}")
    tracemalloc.stop()
    timer.debug(f"{(datetime.datetime.now() - time_triggered).total_seconds()}")
    return render(request, 'helpPages/helpPages.html', context)


