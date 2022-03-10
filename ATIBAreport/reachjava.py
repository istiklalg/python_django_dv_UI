
"""
@author: istiklal
"""
import datetime
import logging
import jpype as jp
from jpype.types import *

logger = logging.getLogger('commons')

classpaths = ["/usr/local/atiba/AtibaSnmpController/AtibaSnmpController-1.0.jar",
              "/usr/local/atiba/AtibaLogAnalyze/AtibaLogAnalyze-1.0.jar",
              "/usr/local/atiba/AtibaLogArranger/AtibaLogArranger-1.0.jar"]


def decode_with_java(hash_text):
    """
    to decode string with decoder in java codes
    returns decoded string
    """
    _result = ""
    _path = "/usr/local/atiba/AtibaSnmpController/AtibaSnmpController-1.0.jar"
    try:
        if not jp.isJVMStarted():
            jp.startJVM(jp.getDefaultJVMPath(), classpath=classpaths)
            logger.info("JVM was closed, it has been started successfully")
        else:
            logger.info("JVM is already started before")
    except Exception as err:
        logger.error(f"An error occurred in decode_with_java while trying to startJVM error is : {err}")
    try:
        LicDecryptSample = jp.JClass("com.atiba.atibasnmpcontroller.LicDecrypt")
        _result = LicDecryptSample().getAes256DecodedLic(JString(hash_text))
    except Exception as err:
        logger.exception(f"An error occurred in decode_with_java, error is : {err}")
    # finally:
    #     try:
    #         jp.shutdownJVM()
    #     except Exception as err:
    #         print(f"An error occurred in decode_with_java when trying to shutdownJVM, error is : {err}")

    return _result


def encode_with_java(clear_text):
    """
    to encode strings with encoder in java codes
    returns encoded string
    """
    _result = ""
    _path = "/usr/local/atiba/AtibaSnmpController/AtibaSnmpController-1.0.jar"
    try:
        if not jp.isJVMStarted():
            jp.startJVM(jp.getDefaultJVMPath(), classpath=classpaths)
            logger.info("JVM was closed, it has been started successfully")
        else:
            logger.info("JVM is already started before")
    except Exception as err:
        logger.error(f"An error occurred in encode_with_java while trying to startJVM error is : {err}")

    try:
        LicEncrypterSample = jp.JClass("com.atiba.licencrypter.LicEncrypter")
        _result = LicEncrypterSample().getAes256EncodedLic(JString(clear_text))
    except Exception as err:
        logger.exception(f"An error occurred in encode_with_java, error is : {err}")
    # finally:
    #     try:
    #         jp.shutdownJVM()
    #     except Exception as err:
    #         print(f"An error occurred in decode_with_java when trying to shutdownJVM, error is : {err}")

    return _result


def scan_device_with_java(network_parameters_id, monitor_profiledetails_id, uniqueidtype_of_logsource):
    """
    this function will be triggered
    scansnmpFromPyton(Integer networkParametersid, Integer mpdid, String uniqueidtype)


    HashMap<String, Object> map = ....
    
    {id=5, subnetMask=24, ipAddr=192.168.1.62, netPrmName=istiklal}

    scanSnmp(List<NetworkParams> netParams, List<ScanParams> scParams, Integer mpdid, String uniqueidtype)

    public class NetworkParams implements Serializable, Comparable<NetworkParams> {
        private Integer id;
        private String netPrmName;
        private String ipAddr;
        private Integer subnetMask;

        public NetworkParams() {
        }

        public NetworkParams(Integer id) {
            this.id = id;
        }
    }

    public class ScanParams implements Serializable, Comparable<ScanParams> {

        private Integer id;
        private String paramsName;
        private String commString;
        private String commString2;

        public ScanParams() {
        }

        public ScanParams(Integer id) {
            this.id = id;
        }


    -- public void scanSnmp(List<NetworkParams> netParams, List<ScanParams> scParams)
    public class NetworkParams implements Serializable, Comparable<NetworkParams> {
        private Integer id;
        private String netPrmName;
        private String ipAddr;
        private Integer subnetMask;
    }
    public class ScanParams implements Serializable, Comparable<ScanParams> {

        private Integer id;
        private String paramsName;
        private String commString;
        private String commString2;
        private String snmpv3User;
        private String snmpv3AuthPass;
        private String snmpv3AuthPass2;
        private String snmpv3AuthProtocol;
        private String snmpv3PrivacyPass;
        private String snmpv3PrivacyPass2;
        private String snmpv3PrivacyProtocol;
        private String snmpVersion;
    }
    """
    # result of java function OK or NOTOK in type of string
    _result = ""
    _path = "/usr/local/atiba/AtibaSnmpController/AtibaSnmpController-1.0.jar"
    try:
        if not jp.isJVMStarted():
            jp.startJVM(jp.getDefaultJVMPath(), classpath=classpaths)
            logger.info("JVM was closed, it has been started successfully")
        else:
            logger.info("JVM is already started before")
    except Exception as err:
        logger.error(f"An error occurred in scan_device_with_java while trying to startJVM error is : {err}")

    try:
        ScanDeviceServiceSample = jp.JClass("com.atiba.atibasnmpcontroller.ScanDeviceService")
        _result = ScanDeviceServiceSample().scansnmpFromPyton(JInt(network_parameters_id),
                                                              JInt(monitor_profiledetails_id),
                                                              uniqueidtype_of_logsource)
        logger.info(f"JAVA - Successfully called ScanDeviceServiceSample().scansnmpFromPyton({network_parameters_id}, {monitor_profiledetails_id}, {uniqueidtype_of_logsource}) -> RESULT : {_result}")
    except Exception as err:
        logger.exception(f"An error occurred in scan_device_with_java, error is : {err}")
    # finally:
    #     try:
    #         jp.shutdownJVM()
    #     except Exception as err:
    #         print(f"An error occurred in decode_with_java when trying to shutdownJVM, error is : {err}")

    return _result


def analyse_parameters_with_java(log_definitions_id):
    """
    function to analyse parameter service start. its a void function in java but in python return a boolean value
    due to exceptional conditions.
    changed now its returns nothing..
    """
    _result = True
    _path = "/usr/local/atiba/AtibaLogAnalyze/AtibaLogAnalyze-1.0.jar"

    try:
        if not jp.isJVMStarted():
            jp.startJVM(jp.getDefaultJVMPath(), classpath=classpaths)
            logger.info("JVM was closed, it has been started successfully")
        else:
            logger.info("JVM is already started before")
    except Exception as err:
        _result = False
        logger.error(f"An error occurred in analyse_parameters_with_java while trying to startJVM error is : {err}")
    try:
        LogDefinitionMB = jp.JClass("com.atiba.loganalyze.LogDefinitionMB")
        # _result = LogDefinitionMB().analyzeParameters(JInt(log_definitions_id))
        LogDefinitionMB().analyzeParameters(JInt(log_definitions_id))
        logger.info(f"JAVA - Successfully called LogDefinitionMB().analyzeParameters({log_definitions_id}). Void function...")
    except Exception as err:
        _result = False
        logger.exception(f"An error occurred in analyse_parameters_with_java, error is : {err}")


def change_severity_with_java(logCode, oldSeverity, newSeverity, subDefCode):
    """
    it's a void function, it returns nothing.
    """
    _result = True
    _path = "/usr/local/atiba/AtibaLogAnalyze/AtibaLogAnalyze-1.0.jar"

    try:
        if not jp.isJVMStarted():
            jp.startJVM(jp.getDefaultJVMPath(), classpath=classpaths)
            logger.info("JVM was closed, it has been started successfully")
        else:
            logger.info("JVM is already started before")
    except Exception as err:
        _result = False
        logger.error(f"An error occurred in change_severity_with_java while trying to startJVM error is : {err}")
    try:
        LogDefinitionService = jp.JClass("com.atiba.loganalyze.LogDefinitionService")
        # _result = LogDefinitionService().updateSeverityDBandElastic(str(logCode), str(oldSeverity), str(newSeverity))
        LogDefinitionService().updateSeverityDBandElastic(str(logCode), str(oldSeverity), str(newSeverity), JInt(subDefCode))
        logger.info(f"JAVA - Successfully called LogDefinitionService().updateSeverityDBandElastic({logCode}, {oldSeverity}, {newSeverity}, {subDefCode}). Void function...")
    except Exception as err:
        _result = False
        logger.exception(f"An error occurred in change_severity_with_java, error is : {err}")


def analyze_parameter_with_java(log_definitions_id, log_code):
    """
    it's a void function, it returns nothing.
    """
    _result = True
    _path = "/usr/local/atiba/AtibaLogAnalyze/AtibaLogAnalyze-1.0.jar"

    try:
        if not jp.isJVMStarted():
            jp.startJVM(jp.getDefaultJVMPath(), classpath=classpaths)
            logger.info("JVM was closed, it has been started successfully")
        else:
            logger.info("JVM is already started before")
    except Exception as err:
        _result = False
        logger.error(f"An error occurred in analyze_parameter_with_java while trying to startJVM error is : {err}")
    try:
        LogDefinitionMB = jp.JClass("com.atiba.loganalyze.LogDefinitionMB")
        # _result = LogDefinitionMB().analyzeParameter(JInt(log_definitions_id), log_code)
        LogDefinitionMB().analyzeParameter(JInt(log_definitions_id), log_code)
        logger.info(f"JAVA - Successfully called LogDefinitionMB().analyzeParameter({log_definitions_id}, {log_code}). Void function...")
    except Exception as err:
        _result = False
        logger.exception(f"An error occurred in analyze_parameter_with_java, error is : {err}")


def reparse_all_with_java(log_code, flag):
    """
    It's a void function, returns nothing.
    """
    _result = True
    _path = "/usr/local/atiba/AtibaLogAnalyze/AtibaLogAnalyze-1.0.jar"

    try:
        if not jp.isJVMStarted():
            jp.startJVM(jp.getDefaultJVMPath(), classpath=classpaths)
            logger.info("JVM was closed, it has been started successfully")
        else:
            logger.info("JVM is already started before")
    except Exception as err:
        _result = False
        logger.error(f"An error occurred in reparse_all_with_java while trying to startJVM error is : {err}")
    try:
        LogManageMB = jp.JClass("com.atiba.loganalyze.LogManageMB")
        # _result = LogManageMB().reParse(log_code, JInt(flag))
        LogManageMB().reParse(log_code, JInt(flag))
        logger.info(f"JAVA - Successfully called LogManageMB().reParse({log_code}, {flag}). Void function...")
    except Exception as err:
        _result = False
        logger.exception(f"An error occurred in reparse_all_with_java, error is : {err}")


def reparse_selected_with_java(elastic_id, flag):
    """
    It's a void function, returns nothing.
    """
    _result = True
    _path = "/usr/local/atiba/AtibaLogAnalyze/AtibaLogAnalyze-1.0.jar"

    try:
        if not jp.isJVMStarted():
            jp.startJVM(jp.getDefaultJVMPath(), classpath=classpaths)
            logger.info("JVM was closed, it has been started successfully")
        else:
            logger.info("JVM is already started before")
    except Exception as err:
        _result = False
        logger.error(f"An error occurred in reparse_selected_with_java while trying to startJVM error is : {err}")
    try:
        LogManageMB = jp.JClass("com.atiba.loganalyze.LogManageMB")
        # _result = LogManageMB().reParse(JLong(elastic_id), JInt(flag))
        LogManageMB().reParse(JLong(elastic_id), JInt(flag))
        logger.info(f"JAVA - Successfully called LogManageMB().reParse({elastic_id}, {flag}). Void function...")
    except Exception as err:
        _result = False
        logger.exception(f"An error occurred in reparse_selected_with_java, error is : {err}")


def logdefValidate_with_java(logdefdetailsId):
    """
    it's a void function, it returns nothing.
    """
    _result = True

    try:
        if not jp.isJVMStarted():
            jp.startJVM(jp.getDefaultJVMPath(), classpath=classpaths)
            logger.info("JVM was closed, it has been started successfully")
        else:
            logger.info("JVM is already started before")
    except Exception as err:
        _result = False
        logger.error(f"An error occurred in logdefValidate_with_java while trying to startJVM error is : {err}")
    try:
        LogDefinitionMB = jp.JClass("com.atiba.loganalyze.LogDefinitionMB")
        # _result = LogDefinitionMB().logDefValidate(JLong(logdefdetailsId))
        LogDefinitionMB().logDefValidate(JLong(logdefdetailsId))
        logger.info(f"JAVA - Successfully called LogDefinitionMB().logDefValidate({logdefdetailsId}). Void function...")
    except Exception as err:
        _result = False
        logger.exception(f"An error occurred in logdefValidate_with_java, error is : {err}")


def take_logs_from_elastic_with_java(variable_type, variable):
    """
    Function to take accumulated error logs from elasticsearch and write them to loglar table in postgresql with
    recstatus = 0 for retry parse
    classpath = "/usr/local/atiba/AtibaLogArranger/AtibaLogArranger-1.0.jar"
    className = "Atibalogarranger"
    No return, it's void function..
    """
    _error = None
    _called_at = datetime.datetime.now()
    logger.info(f"Function take_logs_from_elastic_with_java called at : {_called_at}")
    _result = True

    try:
        if not jp.isJVMStarted():
            jp.startJVM(jp.getDefaultJVMPath(), classpath=classpaths)
            logger.info("JVM was closed, it has been started successfully")
        else:
            logger.info("JVM is already started before")
    except Exception as err:
        _result = False
        _error = str(err)
        logger.error(f"An error occurred in take_logs_from_elastic_with_java while trying to startJVM error is : {err}")
    try:
        LogArrengerSample = jp.JClass("com.atiba.atibalogarranger.Atibalogarranger")
        LogArrengerSample().getLogsFromElastic(JString(variable_type), JString(variable))
        logger.info(f"JAVA - Successfully called LogArrengerSample().getLogsFromElastic({variable_type}, {variable}). Void function..")
        _process_duration = (datetime.datetime.now() - _called_at).total_seconds()
    except Exception as err:
        _result = False
        _error = str(err)
        logger.exception(f"An error occurred in take_logs_from_elastic_with_java, error is : {err}")
        _process_duration = (datetime.datetime.now() - _called_at).total_seconds()
    logger.warning(f"take_logs_from_elastic_with_java({variable_type}, {variable}) completed with -> result : {_result} duration : {_process_duration} error : {_error}")
    return _result, _process_duration, _error

