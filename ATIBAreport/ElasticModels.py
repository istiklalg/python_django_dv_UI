"""
@author: istiklal
"""
import json
import os
from datetime import datetime
import socket
import struct

from django.utils.encoding import is_protected_type

# connection_string = "192.168.1.62:9200"
from accounts.aescipher import AESCipher

# from time import timezone
# from cryptography.fernet import Fernet
# from inventories.models import NetworkDevice

# connection_string = "192.168.1.63:9200"
# es_host_list = ['127.0.0.1', '192.168.1.62']
# es_host_list = ['127.0.0.1', '192.168.1.63', '192.168.1.92']
# es_host_list = ['192.168.1.92']


# def get_interface_ip_address(interfaceName):
#     """
#     * !! : fcntl doesn't work on windows machines !!!
#     DEPRECATED
#     """
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     _interface_ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', interfaceName[:15]))[20:24])
#     s.close()
#     return _interface_ip


def get_ETH0IP_for_ES(cluster=None):
    """
    to get ETH0 network interface IP according to cluster (if cluster is True) exists or not
    """
    if cluster:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('192.255.255.255', 1))
            _interface_ip = s.getsockname()[0]
        except:
            try:
                import fcntl
                _interface_ip = socket.inet_ntoa(
                    fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', 'eth0'[:15]))[20:24])
            except:
                _interface_ip = ['127.0.0.1']
        finally:
            s.close()
        _eth0_ip = _interface_ip
        # _eth0_ip = get_interface_ip_address('eth0')
        return [f"{_eth0_ip}"]
    else:
        # This lines can be operated only when cluster is None or False.
        # In production environment never operate unless cluster value manually convert to False or None
        if os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.production":
            return ['127.0.0.1']
        else:
            return ['192.168.1.92']


def get_PORT_for_ES(cluster=None):
    """
    to get port number according to cluster exists (if cluster is True) or not
    """
    if cluster:
        return 19200
    else:
        if os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.production":
            return 9200
        else:
            return 9200

# in cluster structure elasticsearch ip address will be ETH0IP and port will be 19200
# es_host_list = ['127.0.0.1'] if os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.production" else ['192.168.1.92']


cluster_condition = os.environ['DJANGO_SETTINGS_MODULE'] == "ATIBAreport.setting_files.production"

es_host_list = get_ETH0IP_for_ES(cluster=cluster_condition)
es_port_number = get_PORT_for_ES(cluster=cluster_condition)


class LogFromElastic:
    def __init__(self, hit_object=None, dictionary=None, *args, **kwargs):
        if hit_object:
            _obj = hit_object
            self.id = _obj.id
            self.logcode = _obj.logndx if hasattr(_obj, "logndx") else None
            self.uniqueid = _obj.uniqueid if hasattr(_obj, "uniqueid") else None
            self.ipaddress = _obj.inetaddress if hasattr(_obj, "inetaddress") else None
            self.logevent = _obj.event if hasattr(_obj, "event") else None
            self.severity = _obj.severity if hasattr(_obj, "severity") else None
            try:
                self.credate = datetime.strptime(_obj.credate, "%Y-%m-%d %H:%M:%S.%f") if hasattr(_obj, "credate") else None
            except Exception as err:
                self.credate = datetime.strptime(_obj.credate, "%Y-%m-%d %H:%M:%S") if hasattr(_obj, "credate") else None
            try:
                self.logdate = datetime.strptime(_obj.logdate, "%Y-%m-%d %H:%M:%S.%f") if hasattr(_obj, "logdate") else None
            except Exception as err:
                self.logdate = datetime.strptime(_obj.logdate, "%Y-%m-%d %H:%M:%S") if hasattr(_obj, "logdate") else None
            self.socketaddress = _obj.socketaddress if hasattr(_obj, "socketaddress") else None
            self.port = _obj.port if hasattr(_obj, "port") else None
            self.rawlog = _obj.logdata if hasattr(_obj, "logdata") else None
            self.logpri = _obj.logrefval if hasattr(_obj, "logrefval") else None
            self.logservice = _obj.logservice if hasattr(_obj, "logservice") else None
            self.logserviceno = _obj.logserviceno if hasattr(_obj, "logserviceno") else None
            self.outclasstype = _obj.outclass if hasattr(_obj, "outclass") else None
            self.logCodeCount = None
            # self.logCodeUniqueids = []  # tupple list for (uniqueid, countforthis)
            self.logCodeUniqueids = []  # list for uniqueid
            self.logCodeUniqueidCounts = []  # list for log counts with that uniqueid
        elif dictionary:
            _obj = dictionary
            self.id = int(_obj['id'])
            self.logcode = _obj['logndx'] if "logndx" in _obj else None
            self.uniqueid = _obj['uniqueid'] if "uniqueid" in _obj and _obj['uniqueid'] else None
            self.ipaddress = _obj['inetaddress'] if "inetaddress" in _obj else None
            self.logevent = _obj['event'] if "event" in _obj else None
            self.severity = _obj['severity'] if "severity" in _obj else None
            try:
                self.credate = datetime.strptime(_obj['credate'], "%Y-%m-%d %H:%M:%S.%f") if "credate" in _obj else None
            except Exception as err:
                self.credate = datetime.strptime(_obj['credate'], "%Y-%m-%d %H:%M:%S") if "credate" in _obj else None
            try:
                self.logdate = datetime.strptime(_obj['logdate'], "%Y-%m-%d %H:%M:%S.%f") if "logdate" in _obj else None
            except Exception as err:
                self.logdate = datetime.strptime(_obj['logdate'], "%Y-%m-%d %H:%M:%S") if "logdate" in _obj else None
            self.socketaddress = _obj['socketaddress'] if "socketaddress" in _obj else None
            self.port = _obj['port'] if "port" in _obj else None
            self.rawlog = _obj['logdata'] if "logdata" in _obj else None
            self.logpri = _obj['logrefval'] if "logrefval" in _obj else None
            self.logservice = _obj['logservice'] if "logservice" in _obj else None
            self.logserviceno = _obj['logserviceno'] if "logserviceno" in _obj else None
            self.outclasstype = _obj['outclass'] if "outclass" in _obj else None
            self.parameters = _obj['parameters'] if 'parameters' in _obj.keys() else None
            self.logCodeCount = None
            self.logCodeUniqueids = []  # list for uniqueid
            self.logCodeUniqueidCounts = []  # list for log counts with that uniqueid
        elif args:
            _obj = args[0]
            self.id = _obj["id"] if 'id' in _obj.keys() else None
            self.logcode = _obj["logndx"] if 'logndx' in _obj.keys() else None
            self.uniqueid = _obj["uniqueid"] if 'uniqueid' in _obj.keys() else None
            self.ipaddress = _obj["inetaddress"] if 'inetaddress' in _obj.keys() else None
            self.logevent = _obj["event"] if 'event' in _obj.keys() else None
            self.severity = _obj["severity"] if 'severity' in _obj.keys() else None
            self.credate = _obj["credate"] if 'credate' in _obj.keys() else None  # datetime string
            self.logdate = _obj["logdate"] if 'logdate' in _obj.keys() else None  # datetime string
            self.socketaddress = _obj["socketaddress"] if 'socketaddress' in _obj.keys() else None
            self.port = _obj["port"] if 'port' in _obj.keys() else None
            self.rawlog = _obj["logdata"] if 'logdata' in _obj.keys() else None
            self.logpri = _obj["logrefval"] if 'logrefval' in _obj.keys() else None
            self.logservice = _obj["logservice"] if 'logservice' in _obj.keys() else None
            self.logserviceno = _obj["logserviceno"] if 'logserviceno' in _obj.keys() else None
            self.outclasstype = _obj["outclass"] if 'outclass' in _obj.keys() else None
            self.parameters = _obj['parameters'] if 'parameters' in _obj.keys() else None
            self.logCodeCount = None
            self.logCodeUniqueids = []  # list for uniqueid
            self.logCodeUniqueidCounts = []  # list for log counts with that uniqueid
        else:
            _obj = kwargs
            self.id = _obj['id']
            self.logcode = _obj['logndx'] if "logndx" in _obj else None
            self.uniqueid = _obj['uniqueid'] if "uniqueid" in _obj and _obj['uniqueid'] else None
            self.ipaddress = _obj['inetaddress'] if "inetaddress" in _obj else None
            self.logevent = _obj['event'] if "event" in _obj else None
            self.severity = _obj['severity'] if "severity" in _obj else None
            self.credate = _obj['credate'] if "credate" in _obj else None  # datetime string
            self.logdate = _obj['logdate'] if "logdate" in _obj else None  # datetime string
            self.socketaddress = _obj['socketaddress'] if "socketaddress" in _obj else None
            self.port = _obj['port'] if "port" in _obj else None
            self.rawlog = _obj['logdata'] if "logdata" in _obj else None
            self.logpri = _obj['logrefval'] if "logrefval" in _obj else None
            self.logservice = _obj['logservice'] if "logservice" in _obj else None
            self.logserviceno = _obj['logserviceno'] if "logserviceno" in _obj else None
            self.outclasstype = _obj['outclass'] if "outclass" in _obj else None
            self.parameters = _obj['parameters'] if 'parameters' in _obj.keys() else None
            self.logCodeCount = None
            self.logCodeUniqueids = []  # list for uniqueid
            self.logCodeUniqueidCounts = []  # list for log counts with that uniqueid

    def __str__(self):
        return f"from source {self.uniqueid}, Log Code {self.logcode}, elastic id : {self.id}"

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


class AggregationElastic:

    def __init__(self, aggregation_object=None, dictionary=None, aggregation_name=None, *args, **kwargs):
        self.kvtupples = []
        self.keys = []
        self.values = []
        if aggregation_object and aggregation_name:
            _obj = aggregation_object.get(aggregation_name)
            # _obj = aggregation_object
            self.name = aggregation_name
            if not _obj.buckets or len(_obj.buckets) == 0:
                self.kvtupples = [(None, None)]
                self.keys = [None]
                self.values = [None]
            elif len(_obj.buckets) == 1:
                for k, v in _obj.buckets[0]:
                    self.kvtupples = [(k, v)]
                    self.keys = [k]
                    self.values = [v]
            elif len(_obj.buckets) > 1:
                for bucket in _obj.buckets:
                    for k, v in bucket:
                        self.kvtupples.append((k, v))
                        self.keys.append(k)
                        self.values.append(v)
        elif dictionary and aggregation_name:
            _obj = dictionary.get(aggregation_name)
            # _obj = dictionary.get(aggregation_name)
            # print(_obj)
            self.name = aggregation_name
            if not _obj["buckets"] or len(_obj["buckets"]) == 0:
                self.kvtupples = [(None, None)]
                self.keys = [None]
                self.values = [None]
            elif len(_obj["buckets"]) == 1:
                for k, v in _obj["buckets"][0].items():
                    self.kvtupples.append((k, v))
                    self.keys.append(k)
                    self.values.append(v)
            elif len(_obj["buckets"]) > 1:
                for bucket in _obj["buckets"]:
                    for k, v in bucket.items():
                        self.kvtupples.append((k, v))
                        self.keys.append(k)
                        self.values.append(v)

        elif args and len(args) > 0:
            self.name = "Custom form bucket list"
            for bucket in args:
                for k, v in bucket:
                    self.kvtupples.append((k, v))
                    self.keys.append(k)
                    self.values.append(v)
        else:
            _obj = kwargs
            self.name = "Custom from aggregation detail"
            if not _obj["buckets"] or len(_obj["buckets"]) == 0:
                self.kvtupples = [(None, None)]
                self.keys = [None]
                self.values = [None]
            elif len(_obj["buckets"]) == 1:
                for k, v in _obj["buckets"][0]:
                    self.kvtupples = [(k, v)]
                    self.keys = [k]
                    self.values = [v]
            elif len(_obj["buckets"]) > 1:
                for bucket in _obj["buckets"]:
                    for k, v in bucket.items():
                        self.kvtupples.append((k, v))
                        self.keys.append(k)
                        self.values.append(v)

    def __str__(self):
        return f"Aggregation {self.name}"









