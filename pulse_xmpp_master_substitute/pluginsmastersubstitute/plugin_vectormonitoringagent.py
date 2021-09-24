#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# (c) 2016-2018 siveo, http://www.siveo.net
#
# This file is part of Pulse 2, http://www.siveo.net
#
# Pulse 2 is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Pulse 2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pulse 2; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#
# file pluginsmastersubstitute/plugin_vectormonitoringagent.py
import sys
import json
import logging


import traceback
from lib.plugins.xmpp import XmppMasterDatabase

import os
import ConfigParser
from lib.utils import file_put_contents
import netaddr
from math import cos, sin, atan2, sqrt
try:
    from lib.stat import statcallplugin
    statfuncton = True
except:
    statfuncton = False

logger = logging.getLogger()

plugin = {"VERSION": "1.5", "NAME": "vectormonitoringagent", "TYPE": "substitute"}

def process_system(functionname,
                   xmppobject,
                   msg_from,
                   sessionid,
                   data,
                   id_machine,
                   hostname,
                   id_mon_machine):
    device_type = functionname[8:]
    logger.debug("Device %s" % device_type)
    serial, status, firmware, alarm_msg = ["", "ready", "", []]
    if "serial" in data:
        serial = data['serial']
        del data['serial']
    if "status" in data and data['status'] != "":
        status = data['status']
        del data['status']
    if "firmware" in data:
        firmware = data['firmware']
        del data['firmware']
    if 'alarms' in data:
        if isinstance(data['alarms'], basestring):
            alarm_msg = [data['alarms']]
        elif isinstance(data['alarms'], list):
            alarm_msg = data['alarms']
        del data['alarms']
    XmppMasterDatabase().setMonitoring_device_reg(hostname,
                                                  xmppobject,
                                                  msg_from,
                                                  sessionid,
                                                  id_mon_machine,
                                                  device_type,
                                                  serial,
                                                  firmware,
                                                  status,
                                                  json.dumps(alarm_msg),
                                                  json.dumps(data['metriques']))

def process_nfcreader(functionname,
                      xmppobject,
                      msg_from,
                      sessionid,
                      data,
                      id_machine,
                      hostname,
                      id_mon_machine):
    device_type = functionname[8:]
    serial, status, firmware, alarm_msg = ["", "ready", "", []]
    if "serial" in data:
        serial = data['serial']
        del data['serial']
    if "status" in data and data['status'] != "":
        status = data['status']
        del data['status']
    if "firmware" in data:
        firmware = data['firmware']
        del data['firmware']
    if 'message' in data:
        if isinstance(data['message'], basestring):
            alarm_msg = [data['message']]
        elif isinstance(data['message'], list):
            alarm_msg = data['message']
        del data['message']
    XmppMasterDatabase().setMonitoring_device_reg(hostname,
                                                  xmppobject,
                                                  msg_from,
                                                  sessionid,
                                                  id_mon_machine,
                                                  device_type,
                                                  serial,
                                                  firmware,
                                                  status,
                                                  json.dumps(alarm_msg),
                                                  json.dumps(data['metriques']))

def process_generic(functionname,
                    xmppobject,
                    msg_from,
                    sessionid,
                    data,
                    id_machine,
                    hostname,
                    id_mon_machine):
    try:
        device_type = functionname[8:]
        logger.debug("Device %s" % device_type)
        serial, status, firmware, alarm_msg = ["", "ready", "", []]
        if "serial" in data:
            serial = data['serial']
            del data['serial']
        if "status" in data and data['status'] != "":
            status = data['status']
            del data['status']
        if "firmware" in data:
            firmware = data['firmware']
            del data['firmware']
        if 'message' in data:
            if isinstance(data['message'], basestring):
                alarm_msg = [data['message']]
            elif isinstance(data['message'], list):
                alarm_msg = data['message']
            del data['message']
        logger.debug("\ncall setMonitoring_device_reg hostname %s\n"\
                                            "\t id_mon_machine %s \n"\
                                            "\t device_type, %s\n"\
                                            "\t serial %s \n" \
                                            "\t firmware %s\n" \
                                            "\t status %s\n" \
                                            "\t alarm_msg %s\n" \
                                            "\t metriques %s"% (hostname,
                                                                id_mon_machine,
                                                                device_type,
                                                                serial,
                                                                firmware,
                                                                status,
                                                                json.dumps(alarm_msg),
                                                                json.dumps(data['metriques'])))
        XmppMasterDatabase().setMonitoring_device_reg(hostname,
                                                    xmppobject,
                                                    msg_from,
                                                    sessionid,
                                                    id_mon_machine,
                                                    device_type,
                                                    serial,
                                                    firmware,
                                                    status,
                                                    json.dumps(alarm_msg),
                                                    json.dumps(data['metriques']))
    except Exception:
        logger.error("\n%s" % (traceback.format_exc()))

def callFunction(functionname, *args, **kwargs):
    functionname = "process_%s" % functionname.lower()
    logger.debug("**call function %s %s %s" % (functionname, args, kwargs))
    thismodule = sys.modules[__name__]
    try:
        return getattr(thismodule,
                       functionname)(functionname, *args, **kwargs)
    except AttributeError:
        logger.debug("%s no defined: call process_generic"%functionname)
        process_generic(functionname, *args, **kwargs)
    except Exception:
        logger.error("\n%s" % (traceback.format_exc()))

def action(xmppobject, action, sessionid, data, message, ret, dataobj):
    logger.debug("#################################################")
    logger.debug("call plugin %s from %s" % (plugin,message['from']))
    logger.debug(json.dumps(data, indent=4))
    logger.debug("#################################################")


    compteurcallplugin = getattr(xmppobject, "num_call%s" % action)
    logger.debug("compteur num_call pluging %s %s" % (action,
                                                      compteurcallplugin))

    if compteurcallplugin == 0:
        xmppobject.typelistMonitoring_device = \
            XmppMasterDatabase().getlistMonitoring_devices_type()
        logger.debug("list device %s" % (xmppobject.typelistMonitoring_device))

    try:
        if compteurcallplugin == 0:
            if statfuncton:
                xmppobject.stat_vectormonitoringagent_agent = statcallplugin(xmppobject,
                                                                    plugin['NAME'])
            read_conf_vectormonitoringagent(xmppobject)
        else:
            if statfuncton:
                xmppobject.stat_vectormonitoringagent_agent.statutility()
            pass

    except Exception:
        logger.error("\n%s" % (traceback.format_exc()))


    if "subaction" in data and \
        data['subaction'].lower() in [ "terminalinformations", "terminalalert"]:
        # inscription message alert depuis machine

        if 'from' in data and data['from'] != "":
            machine = XmppMasterDatabase().getMachinefromjid(data['from'])
        else:
            machine = XmppMasterDatabase().getMachinefromjid(message['from'])

        statusmsg = ""

        logger.debug("Machine %s %s" % (machine['id'], machine['hostname']))
        if 'status' in data:
            statusmsg = json.dumps(data['status'])
        id_mom_machine = XmppMasterDatabase().setMonitoring_machine(
                                machine['id'],
                                machine['hostname'],
                                date=data['date'],
                                statusmsg=statusmsg)
        # for each device/service call process
        if 'device_service' in data:
            for element in data['device_service']:
                for devicename in element:
                    # call process functions defined
                    if devicename.lower() in xmppobject.typelistMonitoring_device:
                        # globals()["process_%s"%element](data['opticalReader'])
                        callFunction(devicename,
                                        xmppobject,
                                        str(message['from']),
                                        sessionid,
                                        element[devicename],
                                        machine['id'],
                                        machine['hostname'],
                                        id_mom_machine)
    #except Exception:
        #logger.error("\n%s" % (traceback.format_exc()))



def read_conf_vectormonitoringagent(objectxmpp):
    """
        lit la configuration du plugin
    """

    namefichierconf = plugin['NAME'] + ".ini"
    pathfileconf = os.path.join( objectxmpp.config.pathdirconffile, namefichierconf)
    if not os.path.isfile(pathfileconf):
        logger.error("plugin %s\nConfiguration file  missing\n  %s" % (plugin['NAME'],
                                                                       pathfileconf))
        dataconfigfile ="[parameters]\ntime_between_checks =  60\n"
        file_put_contents(pathfileconf, dataconfigfile)
        if statfuncton:
            objectxmpp.stat_vectormonitoringagent_agent.display_param_config( msg="DEFAULT")
        return False
    else:
        Config = ConfigParser.ConfigParser()
        Config.read(pathfileconf)
        if os.path.exists(pathfileconf + ".local"):
            Config.read(pathfileconf + ".local")
        if Config.has_section("parameters"):
            if statfuncton:
                objectxmpp.stat_vectormonitoringagent_agent.load_param_lap_time_stat_(Config)
                objectxmpp.stat_vectormonitoringagent_agent.display_param_config("CONFIG")
        else:
            logger.error("see SECTION [parameters] mising in file : %s " % pathfileconf)
            if statfuncton:
                objectxmpp.stat_vectormonitoringagent_agent.display_param_config("DEFAULT")
    return True
