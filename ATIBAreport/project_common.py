"""
@author: istiklal
"""
import base64
import datetime
import json
import logging
import os
import platform
import string
import subprocess
import time
import psycopg2
import numpy as np
import io
import networkx as nx
import matplotlib
from itertools import groupby
import matplotlib.pyplot as plt
from Cryptodome.Cipher import AES
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.utils import timezone
from elasticsearch import Elasticsearch

from ATIBAreport.setting_files.basesettings import MEDIA_ROOT
from ATIBAreport.setting_files.passes import encription_key, postgresql_conn_string_prod, postgresql_conn_string_dev
# from accounts.models import LicenseControl
from inventories.models import AnomalyLogs, AnomalyLogsDetails, AiModels, RootCauseGraphsDetails, Incidents, Anomalies
from ATIBAreport.ElasticModels import es_host_list, es_port_number

logger = logging.getLogger('commons')

# we need it for GUI based errors like self.tk.call('image', 'delete', self.name) about tkinter process
# RuntimeError: main thread is not in main loop
matplotlib.use('Agg')

# Preparing general common functions for all python files;

log_files_list = [("Log", "ATIBAreportMemoryTracer", "log"), ("Log", "ATIBAreportTimer", "log")]
record_per_page = 20
sysLogPriorityLabels = [
    "Kernel Messages (kern)",
    "User Level Messages (user)",
    "Mail System (mail)",
    "System Daemons (daemon)",
    "Security Messages (auth)",
    "Syslog Messages (syslog)",
    "Line Printer Subsystem (lpr)",
    "Network News Subsystem (news)",
    "UUCP Subsystem (uucp)",
    "Clock Daemon (cron)",
    "Security Messages (authpriv)",
    "FTP Daemon (ftp)",
    "NTP Subsystem (ntp)",
    "Security Log Audit (security)",
    "Console Log Alert (console)",
    "Scheduling Logs (clock)",
    "Local Facilities0 (local0)",
    "Local Facilities1 (local1)",
    "Local Facilities2 (local2)",
    "Local Facilities3 (local3)",
    "Local Facilities4 (local4)",
    "Local Facilities5 (local5)",
    "Local Facilities6 (local6)",
    "Local Facilities7 (local7)"
]


def object_listing(db_class, first=0, limit=0):
    """
    it provides u an object getter with null point exception handler and also provide visual message contents about
    process results to use it in template messages.

    :param db_class : Database class information to get rows as objects
    :param first : if u need to specific rows, then u can give the first number of row to get from
    :param limit : if u need to specific count of row then u can give the limit as number of rows only or first and
    limit together

    :returns: A dictionary content containing;
        'list' : Object list,
        'string': Result of database operation, to use it in black screen,
        'message': Result of database operation, to use it in frontend for users,
        'type': Type of message to use in frontend, error, success, warning etc.
        'count': Count of objects taken from database
    """
    _all_objects = []
    _db_result = ""
    _template_msg = ""
    _msg_type = "info"
    _count = len(_all_objects)
    try:
        if first == 0 and limit == 0:
            _all_objects = db_class.objects.all()
            _count = len(_all_objects)
            if _count == 0:
                _db_result = f"Database table for class {db_class} is Empty"
                _msg_type = "info"
                _template_msg = "No data to show"
            else:
                _db_result = f"All objects received successfully for {db_class} objects count {_count}"
                _msg_type = "success"
                _template_msg = f"Successfully finished for {_count} object"
        elif first == 0 and limit != 0:
            _all_objects = db_class.objects.all()[:limit]
            _count = len(_all_objects)
            _db_result = f"First {_count} pieces objects received successfully for {db_class}"
            _msg_type = "success"
            _template_msg = f"Successfully finished for first {_count} objects"
        else:
            _all_objects = db_class.objects.all()[first:limit]
            _count = len(_all_objects)
            _db_result = f"Start from {first}, first {_count} pieces objects received successfully for {db_class}"
            _msg_type = "success"
            _template_msg = f"Successfully finished for {_count} objects form {first}. record"
    except ObjectDoesNotExist:
        logger.error(f"There is no instance object for {db_class} class in database")
        _db_result = f"No object found for class {db_class}"
        _msg_type = "warning"
        _template_msg = f"There no data compatible for your choice"
    except Exception as err:
        logger.exception(f"Object could not get from {db_class}. ERROR IS : {err}")
        _db_result = f"{err} occurred when trying to get {db_class} class objects"
        _msg_type = "error"
        _template_msg = f"An error occurred like {err}"

    _context = {
        "list": _all_objects, "string": _db_result, "message": _template_msg, "type": _msg_type, "count": _count,
    }

    return _context


def source_incident_alert_organizer(logSourceList, incidentList, alertList):
    """
    use this function to group incidents and alerts according to log sources
    :param logSourceList: List of Log Sources that you need to organize incidents and alerts
    :param incidentList: List of incidents grouped by log source like (log source uniqueid, list of open incident ids,
    list of closed incident ids)
    :param alertList: List of dictionaries which is include source uniqueid, status and count
    :returns: list of tuples sorted by most recent incident and alert dates like this;
     (
      Log Source Object,
      (Most recent open incident creation date, count of open incidents, count of closed incidents),
      (Most recent open Alert logdateend, count of open alerts, count of closed alerts)
     )
    """
    source_incident_alert = []

    # logger.debug(f"alerts grouping started")
    # alerts_by_sources = [(l, list(v)) for l, v in groupby(sorted(alertList, key=lambda x: x.get_device().uniqueid),
    #                                               lambda x: x.get_device().uniqueid)]
    # logger.debug(f"alerts grouping ended : {len(alertList)}")
    for _ in logSourceList:
        incs_open = []
        incs_closed = []
        recent_inc_date = None
        open_alerts = 0
        closed_alerts = 0

        recent_alts_date = None
        for alt in alertList:
            if alt["lsuniqueid"] == _.uniqueid:
                if alt["status"] == "000":
                    open_alerts = alt["total"]
                    recent_alts_date = Anomalies.objects.get(id=alt["recent"]).credate if alt["total"] > 0 else None
                if alt["status"] == "001":
                    closed_alerts = alt["total"]

        for inc in incidentList:
            if inc[0] == _.uniqueid:
                incs_open = [ids for ids in inc[1] if ids]
                incs_closed = [ids for ids in inc[2] if ids]
                if incs_open:
                    # logger.debug(f"max inc id : {max(incs_open)}")
                    recent_inc_date = list(Incidents.objects.filter(id=max(incs_open)).values("creationdate"))[0]["creationdate"]
                    # logger.debug(f"latest inc date : {recent_inc_date}")
                incidentList.remove(inc)
                break

        # logger.debug(f"Incidents operation over and incident list length : {len(incidentList)}")
        recent_inc = recent_inc_date if incs_open else None
        recent_alt = recent_alts_date
        source_incident_alert.append(
            (_, (recent_inc, len(incs_open), len(incs_closed)), (recent_alt, open_alerts, closed_alerts))
        )

    def sort_source_incident_alert(el):
        if el[1][0] and el[2][0]:
            return max(el[1][0], el[2][0])
        elif el[1][0] and not el[2][0]:
            return el[1][0]
        elif el[2][0] and not el[1][0]:
            return el[2][0]
        if not el[1][0] and not el[2][0]:
            return datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0)

    try:
        source_incident_alert.sort(key=lambda x: sort_source_incident_alert(x), reverse=True)
    except Exception as err:
        logger.debug(f"LIST SORTING ERROR : {err}")
    return source_incident_alert


def get_anomaly_log_detail(identity):
    """
    use to take log from AnomalyLogs with given id. Simple but useful, it's in use..
    """
    try:
        _log = AnomalyLogs.objects.get(id=identity)
    except ObjectDoesNotExist:
        _log = f"Couldn't find matching object with id : {identity}"
    return _log


def root_and_leaves(root_list, path_list, leaf_list):
    """
    use for matching incidents and root-causes related with it. Related means there is a path from root to that leaf.

    Variables:
        root_list : list of incidents, rootlist column
        path_list : list of paths, graphpaths column with json.loads(_.graphpaths)
        leaf_list : list of root-causes, use it to control elements node or leaf
    :param root_list: list of incidents, rootlist column
    :param path_list: list of paths, graphpaths column with json.loads(_.graphpaths)
    :param leaf_list: list of root-causes, use it to control elements node or leaf
    :returns: This function returns a list of tuples which contains
    (root log, log code list, (leaf, (path incident to root-cause, relations between logs, existing user feed back )))
    """
    # _pathList = json.loads(_rcMap.graphpaths)  # map it before give this function
    _rlList = []
    if type(path_list) is list:
        for _root in root_list:
            _leaves = []
            _codes = []
            for path in path_list:
                for k, v in path.items():
                    if v[0] == _root and v[-1] in leaf_list:
                        _leaf = get_anomaly_log_detail(v[-1])
                        _logs_in_path = [get_anomaly_log_detail(_) for _ in v]
                        _relation = []
                        _user_feedback = []
                        for i in range(len(v)):
                            _str = ''
                            _fb = ''
                            if i != 0:
                                _detail = AnomalyLogsDetails.objects.filter(anomalyLog_id=v[i-1]).filter(subAnomalyLog_id=v[i])[0]
                                _fb = _detail.userfeedback
                                _str = _detail.get_relation_string()
                                # if _detail.scoredeviceip == 3:
                                #     _str = _str+" similarity in ip address,"
                                # if _detail.scorelocgroup == 1:
                                #     _str = _str+" similarity in location group,"
                                # if _detail.scoreparameters > 10:
                                #     _str = _str+" similarity in parameters,"
                                # # if _detail.scoretimeseries > 10:
                                # #     _str = _str+" similarity in time series"
                            _relation.append(_str)
                            _user_feedback.append(_fb)
                        _path = [(_logs_in_path[_], _relation[_], _user_feedback[_]) for _ in range(len(_logs_in_path))]
                        _leaves.append((_leaf, _path))
                        _codes.append(_leaf.logcode)
            _rlList.append((get_anomaly_log_detail(_root), list(set(_codes)), _leaves))
    return _rlList


process_running = False


def create_rc_picture(rc_id=None, max_count=None, re_draw=False):
    """
    Function for creating directed network graphs
    :param rc_id: id of RootCauseGraphDetails to draw
    :param max_count: if you want to start bulk draw operation you can give a max draw count. if you don't give this
    function will create all undrawn graphs
    :param re_draw: if you didn't like the shape of graph then give it True as a value, it allows you to redraw graph,
    you need to rc_id with it
    :returns: Nothing
    """
    global process_running
    if process_running:
        logger.debug(f"Bulk drawing operation is running ? {process_running}. That's why new thread ended")
        return "BUSY"

    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.use('Agg')

    if not os.path.isdir(os.path.join(MEDIA_ROOT, 'GRAPHS')):
        logger.info(f"There is no directory for graph image files, now it's creating")
        os.mkdir(f"{MEDIA_ROOT}/GRAPHS")
    if rc_id:
        logger.info(f"Function is called for id : {rc_id}")
        _rc = RootCauseGraphsDetails.objects.only("graphimage", "rcgraph").get(id=rc_id)
        if not _rc.graphimage:
            # if there is no graph drawn before
            process_running = True
            logger.info(f"Creating graph image for {rc_id}")
            logger.debug(f"creating graphimage for {_rc.rcgraph}")
            _rc_graph = json.loads(json.dumps(_rc.rcgraph))
            try:
                nx.draw_networkx(nx.readwrite.json_graph.adjacency_graph(_rc_graph))
                buf = io.BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                file_name = f"GRAPHS/rc_graph_{_rc.id}.png"
                file_with_path = f"{MEDIA_ROOT}/{file_name}"
                plt.savefig(file_with_path, transparent=True)
                # plt.show()
                # _rcMap.graphimage = Image.open(file_with_path)
                # _rcMap.graphimage = file_name
                RootCauseGraphsDetails.objects.filter(id=_rc.id).update(graphimage=file_name)
                # image_bytes = buf.getvalue().decode('utf-8')
                # image_bytes = Image.open(buf)
                buf.close()
                plt.close()
                logger.debug(f"graph image is {file_name}, operation finished successfully for id {rc_id}")
                logger.info(f"graph image is successfully created as {file_name} for id {rc_id}")
                process_running = False
            except Exception as err:
                logger.exception(f"An error occurred trying to draw nx graph. ERROR IS : {err}")
                process_running = False
        elif re_draw:
            # if yo want to force re draw graph, may be you didn't like the shape :) ;
            process_running = True
            logger.info(f"Creating graph image for {rc_id}")
            logger.debug(f"creating graphimage for {_rc.rcgraph}")
            _rc_graph = json.loads(json.dumps(_rc.rcgraph))
            try:
                nx.draw_networkx(nx.readwrite.json_graph.adjacency_graph(_rc_graph))
                buf = io.BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                file_name = f"GRAPHS/rc_graph_{_rc.id}.png"
                file_with_path = f"{MEDIA_ROOT}/{file_name}"
                plt.savefig(file_with_path, transparent=True)
                RootCauseGraphsDetails.objects.filter(id=_rc.id).update(graphimage=file_name)
                buf.close()
                plt.close()
                logger.debug(f"graph image is {file_name}, operation finished successfully for id {rc_id}")
                logger.info(f"graph image is successfully created as {file_name} for id {rc_id}")
                process_running = False
            except Exception as err:
                logger.exception(f"An error occurred trying to draw nx graph. ERROR IS : {err}")
                process_running = False
        else:
            # if already has a graph drawn before;
            logger.debug(f"RootCauseGraphDetails with id {_rc.id} has already graphimage {_rc.graphimage}")
            logger.info(f"{_rc.id} already has a graph image {_rc.graphimage}")
    else:
        _rc_ids = []
        if max_count:
            _rc_ids = list(
                RootCauseGraphsDetails.objects.values_list('id', flat=True).filter(graphimage__isnull=True)[:max_count])
        else:
            _rc_ids = list(RootCauseGraphsDetails.objects.values_list('id', flat=True).filter(graphimage__isnull=True)[:5])
        if _rc_ids:
            _update_start = datetime.datetime.now()
            _c = 0
            for _ in _rc_ids:
                create_rc_picture(rc_id=_)
                _c += 1
            logger.info(
                f"{_c} graph images created in {(datetime.datetime.now() - _update_start).total_seconds()} seconds")
        else:
            logger.debug("There is no RootCauseGraphDetails object without graphimage...")
            logger.info("No need to new graph image")

    return "FINISH"


def update_anomalylogsdetails_userfeedback(path_list, form_response):
    """
    use for update user feedback and ai status in anomaly logs details table
    :param path_list : list of paths, graphpaths column with json.loads(_.graphpaths)
    :param form_response : list of user feedbacks taken from html form as list of string in
        (node id-feedback-root id-leaf id) format string data taken from html form element is parsed to meaningful
        parts and create new list which is containing anomalyLog_id, subAnomalyLog_id as integer and userfeedback as
        boolean to manipulate data in source
    :returns: function returns a boolean value about changes on database.
    """
    _form_data = []
    _changed = False
    for j in range(len(form_response)):
        _s = form_response[j].split("-")
        for i in range(len(_s)):
            if i == 1:
                if _s[i] == 'False' or _s[i] == 'false':
                    _s[i] = False
                else:
                    _s[i] = True
            else:
                _s[i] = int(_s[i])
        for path in path_list:
            for _d in path.values():
                if _d[0] == _s[2] and _d[-1] == _s[3]:
                    _form_data.append((_d[_d.index(_s[0])-1], _s[0], _s[1]))
        form_response[j] = _s

    logger.debug(f"path list for feedback operation : {path_list}")
    logger.debug(f"form response about feedback : {form_response}")
    logger.debug(f"prepared data list : {_form_data}")

    for alog, subalog, t_f in _form_data:
        _obj = AnomalyLogsDetails.objects.filter(anomalyLog_id=alog).filter(subAnomalyLog_id=subalog)[0]
        if not ((t_f and _obj.userfeedback) or (not t_f and not _obj.userfeedback)):
            _changed = True
            if not t_f:
                # t_f is False
                _obj.userfeedback = t_f
                if _obj.aioutputscore:
                    _obj.userscorefeedback = float(int((float(_obj.aioutputscore) * 0.95) * 10000)/10000)
                _obj.aistatus = 2
                _obj.save()
            else:
                # t_f is True
                _obj.userfeedback = t_f
                if _obj.aioutputscore:
                    _obj.userscorefeedback = float(int((float(_obj.aioutputscore) * 1.1) * 10000) / 10000)
                _obj.aistatus = 1
                _obj.save()
        elif _obj.userfeedback is None:  # if there is no user feedback it means null and no given feedback before;
            _changed = True
            if not t_f:
                # t_f is False
                _obj.userfeedback = t_f
                if _obj.aioutputscore:
                    _obj.userscorefeedback = float(int((float(_obj.aioutputscore) * 0.95) * 10000)/10000)
                _obj.aistatus = 2
                _obj.save()
            else:
                # t_f is True
                _obj.userfeedback = t_f
                if _obj.aioutputscore:
                    _obj.userscorefeedback = float(int((float(_obj.aioutputscore) * 1.1) * 10000) / 10000)
                _obj.aistatus = 1
                _obj.save()

    return _changed


def update_anomalylogs_isshow(form_response):
    """
    use for update of isshow, ttr(time to resolve) and aistatus properties on incident which is given in the html form.
    String data taken from html form element is parsed to meaningful parts and create new list which is containing
    incident log id as integer and isshow data as boolean to manipulate data in source
    :param form_response : list of user feedbacks about show attribute of incident. List of string elements in form of
        ['incident log id, boolean value']
    :returns: This function returns a boolean value about changes on database.
    """
    _form_data = []
    _changed = False
    for _data in form_response:
        _data = _data.split("-")
        _data[0] = int(_data[0])
        if _data[1] == 'False' or _data[1] == 'false':
            _data[1] = False
        else:
            _data[1] = True
        _data = (_data[0], _data[1])
        _form_data.append(_data)
    # logger.debug(f"{form_response}")
    # logger.debug(f"{_form_data}")

    for root, t_f in _form_data:
        _obj = AnomalyLogs.objects.get(id=root)
        if not ((t_f and _obj.isshow) or (not t_f and not _obj.isshow)):
            _changed = True
            _obj.isshow = t_f
            _obj.ttr = timezone.now()
            _obj.aistatus = 2
            _obj.save()
            # if not t_f:
            #     # t_f is False
            #     _obj.isshow = t_f
            #     _obj.ttr = timezone.now()
            #     _obj.save()
            # else:
            #     # t-f is True
            #     _obj.isshow = t_f
            #     _obj.ttr = timezone.now()
            #     _obj.save()
    return _changed


def reboot_system():
    """
    to reboot system it is working on
    """
    _result = True
    logger.warning("REBOOT IN 5 SECONDS!!")
    time.sleep(5)
    try:
        subprocess.call('reboot')
    except Exception as err:
        _result = False
        logger.exception(f"An error occurred while trying to execute command. ERROR IS : {err}")
    return _result


def reset_ai(ai_type):
    """
    to reset ai variables from database
    :param ai_type: Type of educated ai you want to reset information that learned. Choices are correlation and
        adaptation for now.
    :returns: Nothing..
    """
    if ai_type == "correlation":
        logger.warning(f"{ai_type} ai will be reset --------------------------------------------")
        _aiModelsCount = AiModels.objects.filter(modeltype="rccandidates").update(model=None, encodelogndx=None,
                                                                                  encodeparams=None, aimetric=None)
        logger.warning(f"updated AiModels count : {_aiModelsCount}")
        _id_list = [_.id for _ in AnomalyLogsDetails.objects.filter()[:20000]]
        _anomalyLogsDetailsCount = AnomalyLogsDetails.objects.filter(id__in=_id_list).update(aistatus=2,
                                                                                             userfeedback=True,
                                                                                             userscorefeedback=F("scorelast"))
        logger.warning(f"updated AnomalyLogsDetails count : {_anomalyLogsDetailsCount}")
        logger.warning(f"{ai_type} ai reset completed -------------------------------------------")

    elif ai_type == "adaptation":
        logger.warning(f"{ai_type} ai will be reset --------------------------------------------")
        _aiModelsCount = AiModels.objects.filter(modeltype="incidents").update(model=None, encodelogndx=None,
                                                                               encodeparams=None, aimetric=None)
        logger.warning(f"updated AiModels count : {_aiModelsCount}")
        _id_list = [_.id for _ in AnomalyLogs.objects.filter()[:20000]]
        _anomalyLogsCount = AnomalyLogs.objects.filter(id__in=_id_list).update(isshow=True, aistatus=2,
                                                                               ttr=timezone.now())
        logger.warning(f"updated AnomalyLogs count : {_anomalyLogsCount}")
        logger.warning(f"{ai_type} ai reset completed -------------------------------------------")

    elif ai_type == "scoring":
        logger.warning(f"{ai_type} ai will be reset --------------------------------------------")
        _aiModelsCount = AiModels.objects.filter(modeltype="anomalyscoring").update(model=None)
        logger.warning(f"updated AiModels count : {_aiModelsCount}")
        logger.warning(f"{ai_type} ai reset completed -------------------------------------------")


def string_mask(string_data):
    """
    to mask private string values like parameter values
    :param string_data: clean string
    :returns: string like str***
    """
    return string_data[:2]+"***"


def date_picker_string(string_data):
    """
    convert string datetime value that taken from html date time picker to form which comparable with elasticsearch
    credate data
    :param string_data: It's datetime picker format string like 2021-01-01T12:35 (in form of %Y-%m-%dT%H:%M)
    :returns: '%Y-%m-%d %H:%M:%S' formatted time string
    """
    if string_data is not None and string_data != "":
        _result = string_data.replace("T", " ")+":00"
    else:
        _result = ""
    return _result


def edit_ip_address_from_string(string_ip):
    """
    this function can be used to get rid of meaningless zeros from ip address.
    For example convert ip address from 190.210.001.010 to 190.210.1.10
    """
    _list = string_ip.split(".")
    _sep = "."
    _list = [str(int(_)) for _ in _list]
    _result = _sep.join(_list)
    return _result


def get_percentage_pri(percentage):
    """
    this function using to generate priority for news on page to colorize them on UI
    """
    if percentage < 60:
        return "info"
    elif 60 <= percentage < 80:
        return "warning"
    else:
        return "danger"


def check_existence(value):
    """
    this function checks value is None type or empty string or string type None and if value applicable returns True.
    it can be especially used in form values instead of using
    if request.POST.get('form_part_name') and request.POST.get('form_part_name') != ""
    """
    _result = (value is not None and value != "" and value != "None" and value != "none" and value != "NONE")
    return _result


def check_special_chars(string_value, list_of_exceptions=None):
    """
    Checks the given string if contains one or more special characters in it or not.
    :param string_value: String to control if contains special characters or not
    :param list_of_exceptions: List of special characters which are doesn't matter being in
    :returns: A boolean value about special characters if exist or not. If exists return True
    """
    _specials = string.punctuation+" "
    if list_of_exceptions is not None:
        for arg in list_of_exceptions:
            _specials = _specials.replace(arg, "")
    # _specialsSet = set(string.punctuation.replace(":", "").replace(".", ""))
    _specialsSet = set(_specials)
    string_value = set(string_value)
    # if len(string_value.intersection(_specialsSet)) > 0:
    #     _result = True
    # else:
    #     _result = False
    #
    # return _result
    return len(string_value.intersection(_specialsSet)) > 0


def reconstruct_log_definition(log_defs_list):
    """
    function need json object list to reconstruct logstructs attribute value
    :returns: reconstructed string
    """
    _string = ""
    if log_defs_list is not None and type(log_defs_list) is list and len(log_defs_list) > 0:
        for _ in log_defs_list:
            for key, value in _.items():
                if key == "s":
                    _string += value
                elif key == "d":
                    _string += "<<"+value+">>"
                else:
                    continue
    return _string


def atiba_encrypt(decoded_string):
    """
    encryption function.
    :param decoded_string: unprotected string value
    :returns: encrypted string value
    """
    # key = Fernet..generate_key()
    _key = base64.b64decode(encription_key)
    try:
        # chipher_suit = Fernet(encription_key)
        # encoded_string = chipher_suit.encrypt(decoded_string.encode('ascii'))
        # encoded_string = base64.urlsafe_b64encode(encoded_string).decode('ascii')
        # return encoded_string
        BS = 16
        pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
        raw = pad(decoded_string)
        iv = "KutHasCenkKurFat".encode('UTF-8')
        cipher = AES.new(_key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw.encode())).decode()
    except Exception as err:
        logger.exception(f"atiba_encrypt function failed because {err}")
        return None


def atiba_decrypt(encoded_string):
    """
    decryption function
    :param encoded_string: encrypted string value
    :returns: decrypted string value
    """
    _key = base64.b64decode(encription_key)
    try:
        # encoded_string = base64.urlsafe_b64decode(encoded_string)
        # cipher_suite = Fernet(encription_key)
        # decoded_string = cipher_suite.decrypt(encoded_string).decode("ascii")
        # return decoded_string
        unpad = lambda s: s[:-ord(s[len(s) - 1:])]
        enc = base64.b64decode(encoded_string)
        iv = "KutHasCenkKurFat".encode('UTF-8')
        cipher = AES.new(_key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(enc[16:])).decode()
    except Exception as err:
        logger.exception(f"atiba_decrypt function failed because {err}")
        return None


def get_system_hw_macaddress():
    """
    function to get system unique identifier encrypted string...
    :returns: encrypted identifier string
    """
    _system_unique_string = ""
    try:
        _system_unique_bytes = subprocess.check_output(['sh', '/usr/local/bin/getmacaddr.sh'])
        _system_unique_string = _system_unique_bytes.decode("utf-8").replace("\n", "")
    except Exception as err:
        logger.exception(f"An error occurred trying to system hw_mac_address. ERROR IS : {err}")
    return _system_unique_string


def check_environment_for_elastic():
    """
    returns a boolean value about environment if elasticsearch connection possible or not
    """
    return os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.production" or os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.developing"


def check_environment_for_production():
    """
    returns a boolean value about environment if it work on a customer machine (may be demo machine) or not
    """
    return os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.production"


postgresql_conn_string = postgresql_conn_string_prod if check_environment_for_elastic() else postgresql_conn_string_dev

"""
    PERMANENT LICENSE CONTROL STEPS
"""


class LicenseControl:

    def __init__(self, values_tuple, *args, **kwargs):
        self.gpdsira = values_tuple[0]
        self.gpdkod = values_tuple[1]
        self.amountinuse = values_tuple[2] if values_tuple[2] else 0
        self.amountlimit = values_tuple[3] if values_tuple[3] else 0
        if self.gpdkod in ["STORAGE", "ACCPNT"]:
            self.isExceeded = self.amountinuse > self.amountlimit*1.1
        else:
            self.isExceeded = self.amountinuse > self.amountlimit
        self.status = f"License exceed for {self.gpdkod} ! (License : {self.amountlimit}, " \
                      f"In Use : {self.amountinuse})" if self.isExceeded else f"{self.gpdkod} in license limits"

    def __str__(self):
        return self.status


def calculate_permanent_license():
    """
    02/09/2021
    Query for license check:
    with lused  as (select unnest(ls.licenseused) lu from logsources ls  where ls.scanstatus != 9), ltotal as
    (select ald.lictypeid lid, gpd.kod lkod, sum(ald.liccount) slic from atibalicdetails ald join
    genelparametredetay gpd on ald.lictypeid=gpd.sira where gpd.kisakod='CIHAZTUR' group by lictypeid, gpd.kod),
    tot as (select gpd.ack gack,gpd.kod gkod, lu,gpd.sira, count(lu) cl from lused join genelparametredetay gpd on
    gpd.sira = lu where gpd.kisakod = 'CIHAZTUR'  group by lu, gpd.kod, gpd.ack, gpd.sira)
    select ltotal.lid as sira, ltotal.lkod as kod, cl as used, ltotal.slic as liccount from tot
    right outer join ltotal on ltotal.lid=tot.sira

    the answer of query is a tuple list, every tuples consist of 4 element as explained below :
        lid  : GeneralParameterDetail table sira column value for licdevtype value in license
        lkod : GeneralParameterDetail table kod column value for licdevtype value in license
        cl   : used amount of license for licdevtype
        slic : limit amount in license for licdevtype

    :returns: [boolean exceed status, list of exceed details]
    """

    qq = """
    with lused  as (select unnest(ls.licenseused) lu from logsources ls  where ls.scanstatus != 9), ltotal as 
    (select ald.lictypeid lid, gpd.kod lkod, sum(ald.liccount) slic from atibalicdetails ald join 
    genelparametredetay gpd on ald.lictypeid=gpd.sira where gpd.kisakod='CIHAZTUR' group by lictypeid, gpd.kod), 
    tot as (select gpd.ack gack,gpd.kod gkod, lu,gpd.sira, count(lu) cl from lused join genelparametredetay gpd on 
    gpd.sira = lu where gpd.kisakod = 'CIHAZTUR'  group by lu, gpd.kod, gpd.ack, gpd.sira)
    select ltotal.lid as sira, ltotal.lkod as kod, cl as used, ltotal.slic as liccount from tot 
    right outer join ltotal on ltotal.lid=tot.sira
    """
    conn = psycopg2.connect(postgresql_conn_string)
    cur = conn.cursor()
    cur.execute(qq)
    _license_results = cur.fetchall()
    cur.close()
    logger.debug(f"Permanent license query results ({type(_license_results)}) : {_license_results}")
    _control_list = [LicenseControl(_) for _ in _license_results]

    _exceed_list = [("danger", _.status) for _ in _control_list if _.isExceeded]
    _exceed = True if _exceed_list else False

    return _exceed, _exceed_list


"""
    END OF PERMANENT LICENSE CONTROL STEPS
"""


def check_psql_is_recovery():
    """

    """
    qq = "select pg_is_in_recovery from pg_is_in_recovery()"
    conn = psycopg2.connect(postgresql_conn_string)
    cur = conn.cursor()
    cur.execute(qq)
    try:
        _recovery = cur.fetchone()[0]
    except Exception as err:
        logger.exception(f"An error occurred trying to check recovery info from PSQL. ERROR IS : {err}")
        _recovery = False
    # cur.close()
    conn.close()
    logger.debug(f"IS PSQL IN RECOVERY MODE ? : {_recovery}")
    return _recovery


def check_psql_health():
    try:
        conn = psycopg2.connect(f"{postgresql_conn_string} connect_timeout=2")
        conn.close()
        logger.info(f"Postgresql is alive")
        return True
    except Exception as err:
        logger.error(f"Postgresql is not alive. ERROR IS : {err}")
        return False


def check_elastic_health():
    if check_environment_for_elastic():
        _health = Elasticsearch(es_host_list, scheme='http', port=es_port_number, timeout=2).ping()
        if _health:
            logger.info(f"Elasticsearch is alive")
            return True
        else:
            logger.error(f"Elasticsearch is not alive. Ping response : {_health}")
            return False
    else:
        logger.warning(f"You are in development environment, no elasticsearch in here")
        return True


def execute_sql_file(sql_file_with_path, database_name='atibadb'):
    """
    To execute sql file to a database with bulk operation.
    :param sql_file_with_path: complete path and file name which will be executed
    :param database_name: database name affected by the operation
    :returns: success condition in boolean, error information if an error occurred during the operation and operation
    duration (in seconds) in given order
    """
    _trigger_time = datetime.datetime.now()
    if database_name == 'atibadb':
        postgresql_conn_string = postgresql_conn_string_prod if check_environment_for_elastic() else postgresql_conn_string_dev
    else:
        logger.warning(f"There is no configuration for database {database_name}")
        return False, f"undefined database {database_name}", 0
    _success = None
    _error = None
    _rows = None
    logger.info(f"Starting execution for {sql_file_with_path}")
    try:
        with open(sql_file_with_path, 'r', encoding='utf-8') as f:
            _rows = f.read()
        _success = True
    except Exception as err:
        _success = False
        _error = str(err)
        logger.exception(f"An error occurred trying to read {sql_file_with_path}. ERROR IS : {err}")
    if _rows:
        # logger.debug(f"_rows : {_rows}")
        _rows = _rows.replace('<SQL_SEPERATOR>', ' ')
        logger.debug(f"_rows : {_rows}")
        conn = psycopg2.connect(postgresql_conn_string)
        cur = conn.cursor()
        try:
            cur.execute(_rows)
            _success = True
        except Exception as err:
            _success = False
            _error = str(err)
            pass
        finally:
            conn.commit()
    _duration = (round(((datetime.datetime.now() - _trigger_time).total_seconds())*100)/100)
    logger.info(f"Process finished in {_duration} seconds with results. success : {_success} - error : {_error}")
    return _success, _error, _duration


def get_file_creation_date(file_with_path):
    """
    get file creation date
    """
    if platform.system() == 'Windows':
        return os.path.getctime(file_with_path)
    else:
        try:
            return os.path.getctime(file_with_path)
        except Exception as err:
            logger.exception(f"os.path.getctime({file_with_path}) didn't work in {platform.system()}. ERROR IS : {err}")
            stat = os.stat(file_with_path)
            try:
                return stat.st_birthtime
            except AttributeError:
                logger.exception(f"Couldn't get creation date of {file_with_path} file.")
                # return stat.st_mtime
                return None


def read_your_own_logs(end_date, start_date=None, day_count=1, file_with_path=None):
    """
    to read and show them parsed
    :param end_date: end date of time interval, i use it as today and give it from the view function
    :param start_date: start date of time interval, None if not given and then use day_count variable
    :param day_count: days count to go back
    :param file_with_path: file name with complete path eg: '/var/log/iamatiba-djangoserver.log'
    :returns:   log list: list of raw logs
                parsed log list:    list of tuples (priority, log service, log date, function name,
                                    line number in code, process id, thread id, log event)
    """
    if file_with_path:
        _my_log_file = file_with_path if check_environment_for_production() else 'Log/OtherServiceTest.log'
    else:
        _my_log_file = '/var/log/iamatiba-djangoserver.log' if check_environment_for_production() else 'Log/ATIBAreport.log'
    _my_logs = None
    _start_date = start_date if start_date else end_date - datetime.timedelta(days=day_count)
    logger.debug(f"Reading Logs in between days {_start_date} & {end_date}")
    _log_list = []
    parsed_log_list = []
    _success = True
    _unparsed_count = 0
    try:
        with open(_my_log_file, mode='r') as logs:
            for log in logs:
                if log.startswith("["):
                    _parts = log.split(" - ")
                    _credate_parts = (_parts[2][:10]).split("-")
                    _credate = datetime.date(int(_credate_parts[0]), int(_credate_parts[1]), int(_credate_parts[2]))
                    if _start_date <= _credate <= end_date:
                        _log_list.append(log)
                        try:
                            parsed_log_list.append(
                                (
                                    _parts[0].replace("[", ""),  # log priority
                                    _parts[1],  # log service
                                    datetime.datetime.strptime(_parts[2], "%Y-%m-%d %H:%M:%S,%f"),  # log creation date
                                    _parts[3],  # function name
                                    (_parts[4]).split(" ")[1],  # code line no
                                    (_parts[5]).split(" ")[1],  # process no
                                    (_parts[6][:_parts[6].index("]")]).split(" ")[1],  # thread no
                                    ("".join(_parts[6:]))[("".join(_parts[6:])).index(": ") + 1:]  # log event
                                )
                            )
                        except Exception as err:
                            logger.error(f"An error occurred trying to parse log. ERROR IS : {err}")
                            _unparsed_count += 1
                            continue
        if _unparsed_count:
            logger.info(f"{len(_log_list)} logs successfully read and {len(parsed_log_list)} successfully parsed from"
                        f" {_my_log_file} between {_start_date} and {end_date}")
        else:
            logger.info(f"{len(_log_list)} logs successfully read and parsed from {_my_log_file} between {_start_date}"
                        f" and {end_date}")
    except Exception as err:
        _success = False
        logger.exception(f"An error occurred trying to read my own logs from '{_my_log_file}'. ERROR IS : {err}")
    return _log_list, parsed_log_list, _success


def read_timer_logs(file_with_path, days_from_now=7):
    """
    Function to read timer logs.
    give a path with file name (full path according to BASE_DIR) as 'Log/ATIBAreportTimer.log' & give a date interval
    return 4 different list;
    :param file_with_path: full path according to BASE_DIR
    :param days_from_now: How many day containing. default is 7 days.
    :returns: views_durations_and_dates - tuple of three values. view function name, durations and dates
    view_functions - view function list.
    durations - duration list, with the same indexes as view_functions.
    dates_form_datetime - date values of timer logs.
    """
    time_triggerred = datetime.datetime.now()
    logger.debug(f"Called read_timer_logs({file_with_path}, {days_from_now})")
    _file_creation = get_file_creation_date(file_with_path)  # <class 'float'> - 1619771376.3360093 , timestamp value of creation date
    # _file_creation = time.ctime(os.path.getctime(file_with_path))  # in format Thu Apr 22 14:15:23 2021
    # _file_modified = time.ctime(os.path.getmtime(file_with_path))
    # logger.debug(f"type of creation time : {type(_file_creation)}")
    # logger.debug(f"Creation time of {file_with_path} : {_file_creation}")
    # logger.debug(f"Last modification time of {file_with_path} : {_file_modified}")
    # logger.debug(f"File name and path for timer logs : {file_with_path}")
    views_durations_and_dates = []
    dates_form_datetime = []
    view_functions = []
    durations = []
    try:
        with open(file_with_path, mode='r', encoding='utf-8') as time_logs:
            # logger.debug(f"Timer logs : {time_logs}")
            for log in time_logs:
                try:
                    _row = log.split(" - ")
                    log_date = datetime.datetime.strptime(_row[1], "%Y-%m-%d %H:%M:%S,%f")
                    # logger.debug(f"{log_date}")
                    # logger.debug(f"{log_date.date()}")
                    # logger.debug(f"{(time_triggerred - log_date).days}")
                    if (time_triggerred.date() - log_date.date()).days > days_from_now:
                        continue
                    else:
                        view_functions.append(_row[2])
                        durations.append(float(_row[3]))
                        dates_form_datetime.append(log_date.date())
                        views_durations_and_dates.append((_row[2], float(_row[3]), log_date.date()))
                except Exception as err:
                    logger.exception(f"An error occurred while reading {file_with_path}. ERROR IS : {err}")
                    continue
    except Exception as err:
        logger.exception(f"An error occurred trying to read UI logs in read_timer_logs({file_with_path}, {days_from_now}). ERROR IS : {err}")
    return views_durations_and_dates, view_functions, durations, dates_form_datetime


def get_ui_charts_data(file_with_path, days_from_now=7):
    """
    Function to get suitable chart data from timer logs. It takes 2 arguments & returns 4 different lists;
    :param file_with_path: full path according to BASE_DIR
    :param days_from_now: How many day containing. default is 7 days.
    :returns: |->views_list - view function list, |->home_chart_json - home view chart values in json format for initial
    chart values, |->chart_jsons - chart values for all view functions that worked in given day interval in json format,
    |->chart_tuples - tuple that contain (view function, dates, max duration, min duration).
    :Note: we also use it with memorytracer...
    """
    view_duration_date_tuple, views_list, durations_list, dates = read_timer_logs(file_with_path, days_from_now)
    chart_tuples = []
    chart_jsons = []
    home_chart_json = None
    for view in set(views_list):
        _dates = list(set(dates))
        _dates.sort()
        view_dates = []
        view_max_durations = []
        view_avrg_durations = []
        view_min_durations = []
        total_of_day = []
        for day in _dates:
            # view_dates.append(day)
            durations_in_day = []
            max_list = []
            min_list = []
            for x in view_duration_date_tuple:
                if x[0] == view and x[2] == day:
                    durations_in_day.append((x[1]))
            if durations_in_day:
                view_dates.append(day.strftime('%d-%m-%Y'))
                view_max_durations.append(max(durations_in_day))
                view_avrg_durations.append(np.mean(durations_in_day))
                view_min_durations.append(min(durations_in_day))
                total_of_day.append(sum(durations_in_day))
                # max_and_min.append(max(durations_in_day))
                # max_and_min.append(min(durations_in_day))
                # view_durations.append(max_and_min)
            # view_durations.append(durations_in_day)
        # chart_tuples.append((view, view_dates, view_durations))
        chart_tuples.append((view, view_dates, view_max_durations, view_min_durations))
        element = {
            'name': view, 'dates': view_dates, 'max_durations': view_max_durations,
            'avrg_durations': view_avrg_durations, 'min_durations': view_min_durations, 'total': total_of_day
        }
        chart_jsons.append(json.dumps(element, indent=4))
        if view == 'home_view':
            home_chart_json = json.dumps(element, indent=4)
    return views_list, home_chart_json, chart_jsons, chart_tuples


def take_memory_usage(stat_list, slice_first=10):
    """
    to use this u have to start tracemalloc with tracemalloc.start() at the beginning of the view function
    and give this function ;
    :param stat_list: top_stats = tracemalloc.take_snapshot().statistics('lineno') statistics as an argument
    :param slice_first: it refer to how many record will be taken with slicing, default is 10
    :returns: |->total_size - total used memory size, |->unit - Byte, KIB, MB, GB
    """
    stat_list = stat_list[:slice_first]
    _total_size = 0
    _unit = None
    for stat in stat_list:
        _total_size += stat.size
    logger.debug(f"Memory allocation of view {_total_size} B")
    _total_size = ((round((_total_size / (1024 * 1024)) * 100)) / 100)
    _unit = "MB"
    # if (_total_size / 1024) < 1:
    #     _total_size = _total_size
    #     _unit = "Byte"
    # elif 1 <= (_total_size / 1024) < 1024:
    #     _total_size = ((round((_total_size / 1024) * 100)) / 100)
    #     _unit = "KIB"
    # elif 1024 <= (_total_size / 1024) < 1024*1024:
    #     _total_size = ((round((_total_size / (1024 * 1024)) * 100)) / 100)
    #     _unit = "MB"
    # elif 1024*1024 <= (_total_size / 1024):
    #     _total_size = ((round((_total_size / (1024 * 1024 * 1024)) * 100)) / 100)
    #     _unit = "GB"
    # _total_size = ((round((_total_size / 1024) * 100)) / 100) if (_total_size / 1024) < 1024 else ((round((_total_size / (1024 * 1024)) * 100)) / 100)
    # _unit = "KIB" if (_total_size / 1024) < 1024 else "MB"
    return _total_size, _unit


iamatiba_service_list = [
    {'name': 'UI Server', 'service_name': 'iamatiba-djangoserver',
     'log_screen_url': "/monitor/atiba/logs", 'log_file': "/var/log/iamatiba-djangoserver.log",
     'info': 'Restarting this service will cause the interface to be disabled for a while, it is recommended not to do anything new for about 30 seconds.'},
    {'name': 'ElasticSearch', 'service_name': 'elasticsearch',
     'log_screen_url': "", 'log_file': "",
     'info': 'Data may be missing on some screens until this service restart process is completed. It is recommended that you do not operate on other screens for approximately 30 seconds.'},
    {'name': 'API Service', 'service_name': 'iamatiba-apiservice',
     'log_screen_url': '', 'log_file': 'var/log/iamatiba-apiservice.log',
     'info': ''},
    {'name': 'Logger', 'service_name': 'iamatiba-logger',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-logger.log",
     'info': 'Note that restarting this service may interrupt the retrieval of new incoming logs.'},
    {'name': 'Elastic Logger', 'service_name': 'iamatiba-elasticlogger',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-elasticlogger.log",
     'info': ''},
    {'name': 'Log Arranger', 'service_name': 'iamatiba-logarranger',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-logarranger.log",
     'info': ''},
    {'name': 'Parser', 'service_name': 'iamatiba-parser',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-parser.log",
     'info': ''},
    {'name': 'Parameter Analyst', 'service_name': 'iamatiba-loganalyze',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-loganalyze.log",
     'info': ''},
    {'name': 'AI Anomaly', 'service_name': 'iamatiba-aianomaly',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-aianomaly.log",
     'info': ''},
    {'name': 'Analyzer', 'service_name': 'iamatiba-analyzer',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-analyzer.log",
     'info': ''},
    # {'name': 'Anomaly', 'service_name': 'iamatiba-anomaly',
    #  'info': ''},
    {'name': 'Causal Graphs', 'service_name': 'iamatiba-causalgraphs',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-causalgraphs.log",
     'info': ''},
    {'name': 'Causality', 'service_name': 'iamatiba-causality',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-causality.log",
     'info': ''},
    {'name': 'Time Series Causality', 'service_name': 'iamatiba-timeseriescausality',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-timeseriescausality.log",
     'info': ''},
    {'name': 'Parameters Modelling', 'service_name': 'iamatiba-paramsmodelling',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-paramsmodelling.log",
     'info': ''},
    {'name': 'SNMP Controller', 'service_name': 'iamatiba-snmpcontroller',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-snmpcontroller.log",
     'info': ''},
    {'name': 'HTTP Monitoring', 'service_name': 'iamatiba-httpmonitoring',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-httpmonitoring.log",
     'info': ''},
    {'name': 'ICMP Monitoring', 'service_name': 'iamatiba-icmpmonitoring',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-icmpmonitoring.log",
     'info': ''},
    {'name': 'SQL Monitoring', 'service_name': 'iamatiba-sqlmonitoring',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-sqlmonitoring.log",
     'info': ''},
    # {'name': 'Log Series', 'service_name': 'iamatiba-logseries',
    #  'info': ''},
    # {'name': 'Reporting', 'service_name': 'iamatiba-reporting',
    #  'info': ''},
    {'name': 'Services', 'service_name': 'iamatiba-services',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-services.log",
     'info': ''},
    {'name': 'UDS', 'service_name': 'iamatiba-uds',
     'log_screen_url': "", 'log_file': "/var/log/iamatiba-uds.log",
     'info': ''},
]


def check_service_status(service_name=None):
    """
    :param service_name: You can give a service name as string to check specific service or don't give any parameter
        to check all services listed above
    :returns:
    {
      "head": {"active": 17, "inactive": 4},
      'active': [
        {'name': 'iamatiba-logger', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-elasticlogger', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-logarranger', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-parser', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-aianomaly', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-analyzer', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-causalgraphs', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-causality', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-djangoserver', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-httpmonitoring', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-icmpmonitoring', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-paramsmodelling', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-services', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-snmpcontroller', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-sqlmonitoring', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-timeseriescausality', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-uds', 'code': 0, 'status': 'ok', 'is_running': True}
      ],
      'inactive': [
        {'name': 'elasticsearch', 'code': 2, 'status': 'error info', 'is_running': False},
        {'name': 'iamatiba-anomaly', 'code': 768, 'status': 'error info', 'is_running': False},
        {'name': 'iamatiba-logseries', 'code': 768, 'status': 'error info', 'is_running': False},
        {'name': 'iamatiba-reporting', 'code': 768, 'status': 'error info', 'is_running': False}
      ]
    }
    """
    if not service_name:
        _active_services, _inactive_services = [], []
        for _service in iamatiba_service_list:
            _result = check_service_status(_service["service_name"])
            if _result["status"]:
                _active_services.append(_result)
            else:
                _inactive_services.append(_result)
        _overall_result = {
            "head": {
                "active": len(_active_services),
                "inactive": len(_inactive_services)
            },
            "active": _active_services,
            "inactive": _inactive_services
        }
        return _overall_result
    else:
        try:
            _status_code = os.system('systemctl status ' + service_name)
            _is_running = True if _status_code == 0 else False
            _status = "Ok" if _status_code == 0 else "Not running"
            _result = {"name": service_name, "code": _status_code, "status": _status, "is_running": _is_running}
        except Exception as err:
            logger.exception(f"An error occurred trying to get status of {service_name}. ERROR IS : {err}")
            _result = {"name": service_name, "code": 9999, "status": f"Error : {err}", "is_running": False}
        return _result


def start_iamatiba_service(service_name):
    try:
        _status_code = os.system('systemctl start ' + service_name)
        _is_running = True if _status_code == 0 else False
        _status = "Ok" if _status_code == 0 else "Not running"
        _result = {"name": service_name, "code": _status_code, "status": _status, "is_running": _is_running}
        logger.info(f"{service_name} started.")
    except Exception as err:
        logger.exception(f"An error occurred trying to start {service_name}. ERROR IS : {err}")
        _result = {"name": service_name, "code": 9999, "status": f"Error : {err}", "is_running": False}
    return _result


def restart_iamatiba_service(service_name):
    try:
        _status_code = os.system('systemctl restart ' + service_name)
        _is_running = True if _status_code == 0 else False
        _status = "Ok" if _status_code == 0 else "Not running"
        _result = {"name": service_name, "code": _status_code, "status": _status, "is_running": _is_running}
        logger.info(f"{service_name} restarted.")
    except Exception as err:
        logger.exception(f"An error occurred trying to restart {service_name}. ERROR IS : {err}")
        _result = {"name": service_name, "code": 9999, "status": f"Error : {err}", "is_running": False}
    return _result


def stop_iamatiba_service(service_name):
    try:
        _status_code = os.system('systemctl stop ' + service_name)
        _is_running = True if _status_code == 0 else False
        _status = "Ok" if _status_code == 0 else "Not running"
        _result = {"name": service_name, "code": _status_code, "status": _status, "is_running": _is_running}
        logger.info(f"{service_name} stopped.")
    except Exception as err:
        logger.exception(f"An error occurred trying to stop {service_name}. ERROR IS : {err}")
        _result = {"name": service_name, "code": 9999, "status": f"Error : {err}", "is_running": False}
    return _result


"""
functions below are out of order for now
"""


def rename_old_log_file(file_path, file_name, file_extention):
    """
    NOT IN USE
    function to rename old log files and let django to generate an empty new log file
    :param file_path: file directory path according to project base directory as string
    :param file_name: file name as string
    :param file_extention: file extention as string "txt", "log" etc.
    :returns: it rename log file if file is one month old else do nothing, also function returns nothing...
    """
    _today = datetime.date.today()
    _old_file_name = f"{file_name}.{file_extention}"
    _old_file = os.path.join(file_path, _old_file_name)
    # _file_creation = time.ctime(os.path.getctime(_old_file))  # in format Thu Apr 22 14:15:23 202
    try:
        # _file_creation = time.strptime(time.ctime(os.path.getctime(_old_file)), "%c")
        # _file_creation = get_file_creation_date(f"{file_path}/{file_name}.{file_extention}")
        _file_creation = get_file_creation_date(f"{_old_file}")
        logger.debug(f"Creation date as timestamp: {type(_file_creation)} - {_file_creation}")
        if _file_creation and isinstance(_file_creation, float):
            _file_creation = datetime.datetime.fromtimestamp(_file_creation)
            logger.debug(f"Creation date of {_old_file} : {_file_creation} -> old?:{_file_creation.month<_today.month}")
            if _file_creation.month < _today.month:
                # _new_file_name = f"{file_name}-{_today.year}-{_today.month}.{file_extention}"
                _new_file_name = f"{file_name}-{_file_creation.year}-{_file_creation.month}.{file_extention}"
                _new_file = os.path.join(file_path, _new_file_name)
                # with open(_old_file, newline='') as f:
                #     # to avoid using another process error
                #     pass
                os.rename(_old_file, _new_file)
                logger.info(f"{_old_file} was renamed as {_new_file}")
    except Exception as err:
        logger.exception(f"{err}")
        # time.sleep(3)
        # rename_old_log_file(file_path, file_name, file_extention)

    # _new_file_name = f"{file_name}-{_today.year}-{_today.month}.{file_extention}"
    # _new_file = os.path.join(file_path, _new_file_name)
    # os.rename(_old_file, _new_file)


def check_log_files():
    """
    Function for check log files in given list old or not, and if file is one month old rename it
    """
    # _today = datetime.date.today()
    # _days_left = None
    # if _today.month in [1, 3, 5, 7, 8, 10, 12]:
    #     # 31 days
    #     _days_left = 31 - _today.day
    # elif _today.month in [4, 6, 9, 11]:
    #     # 30 days
    #     _days_left = 30 - _today.day
    # elif _today.month == 2 and _today.year % 4 == 0:
    #     # 29 days
    #     _days_left = 29 - _today.day
    # else:
    #     # 28 days
    #     _days_left = 28 - _today.day
    # logger.debug(f"")
    # if _days_left and _days_left < 1:
    #     time.sleep(15)
    #     for path, file, ext in log_files_list:
    #         rename_old_log_file(path, file, ext)
    # log_file_list = [
    #     ("Log", "ATIBAreport", "log"),
    #     ("Log", "ATIBAreportTimer", "log"),
    #     ("Log", "ATIBAreportMemoryTracer", "log")
    # ]
    time.sleep(3)
    for path, file, ext in log_files_list:
        rename_old_log_file(path, file, ext)
    # time.sleep(15)
    # check_log_files()


def timeout_test(wait_for=20):
    """
    Function to test request timeout in UI with basic time.sleep() operation
    """
    logger.debug(f"Called Function timeout test for {wait_for} seconds")
    # asyncio.sleep(wait_for)
    time.sleep(wait_for)
    _res = 147896*125578*3254
    logger.debug(f"Operation finished with result {_res}")
    return _res


def list_of_active_license():
    """
    Active licenses and get some details for its own
    """
    pass


def data_null_safety(data):
    """None control, deprecated..."""
    result = (data is not None)
    return result
