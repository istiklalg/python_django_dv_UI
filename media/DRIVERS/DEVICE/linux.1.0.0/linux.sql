
-- DEVICE MARK 

Insert into public.devicemark (
id, markname, markfilename) 
VALUES (1906001,'LINUX','linux') 
on conflict (id) do update set 
markname = excluded.markname, 
markfilename = excluded.markfilename; 

-- DEVICE MODELS 

INSERT INTO public.devicemodel(
        devicemarkid, modelname, devicetypecode,
       fielddefcode, modelcode, devicetype, versionparseid)
	VALUES (1906001, 'Manjaro Server', 'SERVER', 1906101, NULL, 'Manjaro Server', NULL) 
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
	VALUES (1906001, 'Arch Server', 'SERVER', 1906091, NULL, 'Arch Server', NULL) 
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
	VALUES (1906001, 'Mint Server', 'SERVER', 1906081, NULL, 'Mint Server', NULL) 
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
	VALUES (1906001, 'Kali Server', 'SERVER', 1906071, NULL, 'Kali Server', NULL) 
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
	VALUES (1906001, 'SUSE Server', 'SERVER', 1906061, NULL, 'SUSE Server', NULL) 
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
	VALUES (1906001, 'Fedora Server', 'SERVER', 1906051, NULL, 'Fedora Server', NULL) 
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
	VALUES (1906001, 'RedHat Server', 'SERVER', 1906041, NULL, 'RedHat Server', NULL) 
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
	VALUES (1906001, 'Centos Server', 'SERVER', 1906031, NULL, 'Centos Server', NULL) 
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
	VALUES (1906001, 'Debian Server', 'SERVER', 1906021, NULL, 'Debian Server', NULL) 
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
	VALUES (1906001, 'Ubuntu Server', 'SERVER', 1906011, NULL, 'Ubuntu Server', NULL) 
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
	VALUES ('21.04', NULL, 'Ubuntu Server', 1906011, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('20.10', NULL, 'Ubuntu Server', 1906011, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('20.04', NULL, 'Ubuntu Server', 1906011, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('18.04', NULL, 'Ubuntu Server', 1906011, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('16.04', NULL, 'Ubuntu Server', 1906011, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('14.04', NULL, 'Ubuntu Server', 1906011, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('10', NULL, 'Debian Server', 1906021, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('9', NULL, 'Debian Server', 1906021, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('8', NULL, 'Debian Server', 1906021, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('7', NULL, 'Debian Server', 1906021, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('6', NULL, 'Debian Server', 1906021, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('5', NULL, 'Debian Server', 1906021, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('4', NULL, 'Debian Server', 1906021, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('3.1', NULL, 'Debian Server', 1906021, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('3.0', NULL, 'Debian Server', 1906021, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('8', NULL, 'Centos Server', 1906031, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('7', NULL, 'Centos Server', 1906031, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('6', NULL, 'Centos Server', 1906031, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('7.1', NULL, 'RedHat Server', 1906041, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('7.2', NULL, 'RedHat Server', 1906041, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('7.3', NULL, 'RedHat Server', 1906041, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('7.4', NULL, 'RedHat Server', 1906041, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('7.5', NULL, 'RedHat Server', 1906041, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('7.6', NULL, 'RedHat Server', 1906041, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('7.7', NULL, 'RedHat Server', 1906041, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('8', NULL, 'RedHat Server', 1906041, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('35', NULL, 'Fedora Server', 1906051, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('34', NULL, 'Fedora Server', 1906051, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('33', NULL, 'Fedora Server', 1906051, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('32', NULL, 'Fedora Server', 1906051, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('31', NULL, 'Fedora Server', 1906051, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('30', NULL, 'Fedora Server', 1906051, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('29', NULL, 'Fedora Server', 1906051, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('28', NULL, 'Fedora Server', 1906051, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('27', NULL, 'Fedora Server', 1906051, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('26', NULL, 'Fedora Server', 1906051, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('11', NULL, 'SUSE Server', 1906061, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('12', NULL, 'SUSE Server', 1906061, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('15', NULL, 'SUSE Server', 1906061, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('2021', NULL, 'Kali Server', 1906071, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('2020', NULL, 'Kali Server', 1906071, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('2019', NULL, 'Kali Server', 1906071, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('2018', NULL, 'Kali Server', 1906071, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('4', NULL, 'Mint Server', 1906081, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('19', NULL, 'Mint Server', 1906081, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('19.1', NULL, 'Mint Server', 1906081, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('19.2', NULL, 'Mint Server', 1906081, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('19.3', NULL, 'Mint Server', 1906081, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('20', NULL, 'Mint Server', 1906081, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('20.1', NULL, 'Mint Server', 1906081, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('20.2', NULL, 'Mint Server', 1906081, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('2021', NULL, 'Arch Server', 1906091, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('21', NULL, 'Manjaro Server', 1906101, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('20', NULL, 'Manjaro Server', 1906101, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 
<SQL_SEPERATOR>
INSERT INTO public.deviceversions(
	 versioncode, parsedversionname, devicetype, parseformulcode, configid)
	VALUES ('19', NULL, 'Manjaro Server', 1906101, NULL)
    on conflict (versioncode,devicetype) do update set 
           parsedversionname=excluded.parsedversionname, 
           parseformulcode=excluded.parseformulcode,
           configid=excluded.configid; 


-- PARSE FORMULS 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1906011, 'Ubuntu Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1906021, 'Debian Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1906031, 'Centos Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1906041, 'RedHat Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1906051, 'Fedora Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1906061, 'SUSE Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1906071, 'Kali Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1906081, 'Mint Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1906091, 'Arch Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 
<SQL_SEPERATOR>
INSERT INTO public.pparseformulkod(
	parseformulkod, formulname, alternateparseid, alternatecondition)
	VALUES (1906101, 'Manjaro Server', NULL, NULL)
    on conflict (parseformulkod) do update set 
           formulname=excluded.formulname, 
           alternateparseid=excluded.alternateparseid,
           alternatecondition=excluded.alternatecondition; 


-- LOG RULES  
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1906011, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1906011')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1906021, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1906021')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1906031, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1906031')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1906041, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1906041')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1906051, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1906051')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1906061, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1906061')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1906071, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1906071')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1906081, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1906081')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1906091, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1906091')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 
<SQL_SEPERATOR>
INSERT INTO public.logkural(
	 parseformulkod, basla, karaktersay, tur, format, degisken, staticval)
	VALUES (1906101, '1', 'length($1)-1 ', 'string', NULL, 'logevent', 'undef1906101')
    on conflict (parseformulkod,degisken) do update set 
           basla=excluded.basla, 
           karaktersay=excluded.karaktersay,
           tur=excluded.tur, 
           format=excluded.format,
           staticval=excluded.staticval; 


-- LOG DEFINITIONSS  
<SQL_SEPERATOR>
INSERT INTO public.logdefinitions(
	definitioncode, definitionname, logcodeaccept, shortcode, logcodedelete)
	VALUES (1906011, 'Ubuntu Server', '1=1', 'UBUNTU01', NULL) 
    on conflict (definitioncode) do update set 
           definitionname=excluded.definitionname, 
           logcodeaccept=excluded.logcodeaccept,
           shortcode=excluded.shortcode,
           logcodedelete=excluded.logcodedelete; 
<SQL_SEPERATOR>
INSERT INTO public.logdefinitions(
	definitioncode, definitionname, logcodeaccept, shortcode, logcodedelete)
	VALUES (1906021, 'Debian Server', '1=1', 'DEBIAN01', NULL) 
    on conflict (definitioncode) do update set 
           definitionname=excluded.definitionname, 
           logcodeaccept=excluded.logcodeaccept,
           shortcode=excluded.shortcode,
           logcodedelete=excluded.logcodedelete; 
<SQL_SEPERATOR>
INSERT INTO public.logdefinitions(
	definitioncode, definitionname, logcodeaccept, shortcode, logcodedelete)
	VALUES (1906031, 'Centos Server', '1=1', 'CENTOS01', NULL) 
    on conflict (definitioncode) do update set 
           definitionname=excluded.definitionname, 
           logcodeaccept=excluded.logcodeaccept,
           shortcode=excluded.shortcode,
           logcodedelete=excluded.logcodedelete; 
<SQL_SEPERATOR>
INSERT INTO public.logdefinitions(
	definitioncode, definitionname, logcodeaccept, shortcode, logcodedelete)
	VALUES (1906041, 'RedHat Server', '1=1', 'REDHAT01', NULL) 
    on conflict (definitioncode) do update set 
           definitionname=excluded.definitionname, 
           logcodeaccept=excluded.logcodeaccept,
           shortcode=excluded.shortcode,
           logcodedelete=excluded.logcodedelete; 
<SQL_SEPERATOR>
INSERT INTO public.logdefinitions(
	definitioncode, definitionname, logcodeaccept, shortcode, logcodedelete)
	VALUES (1906051, 'Fedora Server', '1=1', 'FEDORA01', NULL) 
    on conflict (definitioncode) do update set 
           definitionname=excluded.definitionname, 
           logcodeaccept=excluded.logcodeaccept,
           shortcode=excluded.shortcode,
           logcodedelete=excluded.logcodedelete; 
<SQL_SEPERATOR>
INSERT INTO public.logdefinitions(
	definitioncode, definitionname, logcodeaccept, shortcode, logcodedelete)
	VALUES (1906061, 'SUSE Server', '1=1', 'SUSEXX01', NULL) 
    on conflict (definitioncode) do update set 
           definitionname=excluded.definitionname, 
           logcodeaccept=excluded.logcodeaccept,
           shortcode=excluded.shortcode,
           logcodedelete=excluded.logcodedelete; 
<SQL_SEPERATOR>
INSERT INTO public.logdefinitions(
	definitioncode, definitionname, logcodeaccept, shortcode, logcodedelete)
	VALUES (1906071, 'Kali Server', '1=1', 'KALIXX01', NULL) 
    on conflict (definitioncode) do update set 
           definitionname=excluded.definitionname, 
           logcodeaccept=excluded.logcodeaccept,
           shortcode=excluded.shortcode,
           logcodedelete=excluded.logcodedelete; 
<SQL_SEPERATOR>
INSERT INTO public.logdefinitions(
	definitioncode, definitionname, logcodeaccept, shortcode, logcodedelete)
	VALUES (1906081, 'Mint Server', '1=1', 'MINTXX01', NULL) 
    on conflict (definitioncode) do update set 
           definitionname=excluded.definitionname, 
           logcodeaccept=excluded.logcodeaccept,
           shortcode=excluded.shortcode,
           logcodedelete=excluded.logcodedelete; 
<SQL_SEPERATOR>
INSERT INTO public.logdefinitions(
	definitioncode, definitionname, logcodeaccept, shortcode, logcodedelete)
	VALUES (1906091, 'Arch Server', '1=1', 'ARCHXX01', NULL) 
    on conflict (definitioncode) do update set 
           definitionname=excluded.definitionname, 
           logcodeaccept=excluded.logcodeaccept,
           shortcode=excluded.shortcode,
           logcodedelete=excluded.logcodedelete; 
<SQL_SEPERATOR>
INSERT INTO public.logdefinitions(
	definitioncode, definitionname, logcodeaccept, shortcode, logcodedelete)
	VALUES (1906101, 'Manjaro Server', '1=1', 'MANJAR01', NULL) 
    on conflict (definitioncode) do update set 
           definitionname=excluded.definitionname, 
           logcodeaccept=excluded.logcodeaccept,
           shortcode=excluded.shortcode,
           logcodedelete=excluded.logcodedelete; 


-- LOG DEFINITION DETAILS  


-- ENTERPRISE ID  


-- VERSION CONFIG  


-- VIRTUAL DEVICE PARAMS  
