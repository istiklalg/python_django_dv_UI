
-- DEVICE MARK 

Insert into public.devicemark (
id, markname, markfilename, markversion, marksubversion) 
VALUES (1904001,'MICROSOFT','microsoft','1.0',0) 
on conflict (id) do update set 
markname = excluded.markname, 
markfilename = excluded.markfilename; 

-- DEVICE MODELS 

INSERT INTO public.devicemodel(
        devicemarkid, modelname, devicetypecode,
       fielddefcode, modelcode, devicetype, versionparseid)
	VALUES (1904001, 'Windows Server 2008', 'SERVER', 1904019, NULL, 'Windows Server', NULL) 
    on conflict (modelcode) do update set 
           modelname=excluded.modelname, 
           devicetypecode=excluded.devicetypecode,
           fielddefcode=excluded.fielddefcode, 
           modelcode=excluded.modelcode,  
           devicetype=excluded.devicetype, 
           versionparseid=excluded.versionparseid; 
<SQL_SEPERATOR>
INSERT INTO public.devicemodel(
        devicemarkid, modelname, devicetypecode,
       fielddefcode, modelcode, devicetype, versionparseid)
	VALUES (1904001, 'Windows Server 2008 R2', 'SERVER', 1904018, NULL, 'Windows Server', NULL) 
    on conflict (modelcode) do update set 
           modelname=excluded.modelname, 
           devicetypecode=excluded.devicetypecode,
           fielddefcode=excluded.fielddefcode, 
           modelcode=excluded.modelcode,  
           devicetype=excluded.devicetype, 
           versionparseid=excluded.versionparseid; 
<SQL_SEPERATOR>
INSERT INTO public.devicemodel(
        devicemarkid, modelname, devicetypecode,
       fielddefcode, modelcode, devicetype, versionparseid)
	VALUES (1904001, 'Windows Server 2012', 'SERVER', 1904017, NULL, 'Windows Server', NULL) 
    on conflict (modelcode) do update set 
           modelname=excluded.modelname, 
           devicetypecode=excluded.devicetypecode,
           fielddefcode=excluded.fielddefcode, 
           modelcode=excluded.modelcode,  
           devicetype=excluded.devicetype, 
           versionparseid=excluded.versionparseid; 
<SQL_SEPERATOR>
INSERT INTO public.devicemodel(
        devicemarkid, modelname, devicetypecode,
       fielddefcode, modelcode, devicetype, versionparseid)
	VALUES (1904001, 'Windows Server 2012 R2', 'SERVER', 1904016, NULL, 'Windows Server', NULL) 
    on conflict (modelcode) do update set 
           modelname=excluded.modelname, 
           devicetypecode=excluded.devicetypecode,
           fielddefcode=excluded.fielddefcode, 
           modelcode=excluded.modelcode,  
           devicetype=excluded.devicetype, 
           versionparseid=excluded.versionparseid; 
<SQL_SEPERATOR>
INSERT INTO public.devicemodel(
        devicemarkid, modelname, devicetypecode,
       fielddefcode, modelcode, devicetype, versionparseid)
	VALUES (1904001, 'Windows Server 2016', 'SERVER', 1904015, NULL, 'Windows Server', NULL) 
    on conflict (modelcode) do update set 
           modelname=excluded.modelname, 
           devicetypecode=excluded.devicetypecode,
           fielddefcode=excluded.fielddefcode, 
           modelcode=excluded.modelcode,  
           devicetype=excluded.devicetype, 
           versionparseid=excluded.versionparseid; 
<SQL_SEPERATOR>
INSERT INTO public.devicemodel(
        devicemarkid, modelname, devicetypecode,
       fielddefcode, modelcode, devicetype, versionparseid)
	VALUES (1904001, 'Windows Server 2019', 'SERVER', 1904014, NULL, 'Windows Server', NULL) 
    on conflict (modelcode) do update set 
           modelname=excluded.modelname, 
           devicetypecode=excluded.devicetypecode,
           fielddefcode=excluded.fielddefcode, 
           modelcode=excluded.modelcode,  
           devicetype=excluded.devicetype, 
           versionparseid=excluded.versionparseid; 
<SQL_SEPERATOR>
INSERT INTO public.devicemodel(
        devicemarkid, modelname, devicetypecode,
       fielddefcode, modelcode, devicetype, versionparseid)
	VALUES (1904001, 'Windows Server version 1903', 'SERVER', 1904013, NULL, 'Windows Server', NULL) 
    on conflict (modelcode) do update set 
           modelname=excluded.modelname, 
           devicetypecode=excluded.devicetypecode,
           fielddefcode=excluded.fielddefcode, 
           modelcode=excluded.modelcode,  
           devicetype=excluded.devicetype, 
           versionparseid=excluded.versionparseid; 
<SQL_SEPERATOR>
INSERT INTO public.devicemodel(
        devicemarkid, modelname, devicetypecode,
       fielddefcode, modelcode, devicetype, versionparseid)
	VALUES (1904001, 'Windows Server version 1909', 'SERVER', 1904012, NULL, 'Windows Server', NULL) 
    on conflict (modelcode) do update set 
           modelname=excluded.modelname, 
           devicetypecode=excluded.devicetypecode,
           fielddefcode=excluded.fielddefcode, 
           modelcode=excluded.modelcode,  
           devicetype=excluded.devicetype, 
           versionparseid=excluded.versionparseid; 
<SQL_SEPERATOR>
INSERT INTO public.devicemodel(
        devicemarkid, modelname, devicetypecode,
       fielddefcode, modelcode, devicetype, versionparseid)
	VALUES (1904001, 'Windows Server version 2004', 'SERVER', 1904011, NULL, 'Windows Server', NULL) 
    on conflict (modelcode) do update set 
           modelname=excluded.modelname, 
           devicetypecode=excluded.devicetypecode,
           fielddefcode=excluded.fielddefcode, 
           modelcode=excluded.modelcode,  
           devicetype=excluded.devicetype, 
           versionparseid=excluded.versionparseid; 


-- DEVICE VERSIONS 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('NT 10.0', NULL, 'Windows Server', 1904001, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('NT 6.3', NULL, 'Windows Server', 1904001, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('NT 6.2', NULL, 'Windows Server', 1904001, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('NT 6.1', NULL, 'Windows Server', 1904001, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('NT 6.0', NULL, 'Windows Server', 1904001, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 


-- PARSE FORMULS 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1904001, 'Windows Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 


-- LOG RULES  
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1904001, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1904001')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 


-- LOG DEFINITIONSS  


-- LOG DEFINITION DETAILS  


-- ENTERPRISE ID  


-- VERSION CONFIG  


-- VIRTUAL DEVICE PARAMS  
