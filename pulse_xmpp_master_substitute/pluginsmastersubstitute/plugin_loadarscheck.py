# -*- coding: utf-8 -*-
#
# (c) 2004-2007 Linbox / Free&ALter Soft, http://linbox.com
# (c) 2007-2009 Mandriva, http://www.mandriva.com/
# (c) 2016 siveo, http://www.siveo.net
#
# $Id$
#
# This file is part of Pulse 2, http://pulse2.mandriva.org
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

""" declare the substitute plugin for deployments"""
# pluginsmastersubstitute/plugin_loadarscheck.py
#
import base64
import traceback
import os
import sys
import json
import logging
from lib.plugins.xmpp import XmppMasterDatabase
from lib.utils import name_random
import ConfigParser
import types
import datetime
import time
import random
import re
from sleekxmpp import jid
from sleekxmpp.exceptions import IqError, IqTimeout

logger = logging.getLogger()


plugin = {"VERSION": "1.2", "NAME": "loadarscheck", "TYPE": "substitute"}

def action(objectxmpp, action, sessionid, data, msg, ret):
    try:
        logger.debug("=====================================================")
        logger.debug("call %s from %s" % (plugin, msg['from']))
        logger.debug("=====================================================")
        compteurcallplugin = getattr(objectxmpp, "num_call%s"%action)

        if compteurcallplugin == 0:
            read_conf_loadarscheck(objectxmpp)
    except Exception as e:
        logger.error("Plugin loadarscheck, we encountered the error %s" % str(e))
        logger.error("We obtained the backtrace %s" % traceback.format_exc())


def arscheck(self):
    """
        This function is used to ping the ARS regularly.
        The check_ars_scan_interval variable define how much this is done.
        check_ars_by_ping
    """
    sessionid = name_random(5, "monitoring_check_ars")
    
    if not self.ressource_scan_available:
        logger.debug("The ressource is not available.")
        return
    try:
        self.ressource_scan_available = False
        list_ars_search =  XmppMasterDatabase().getRelayServer()
        enabled_ars = [ x for x in list_ars_search if x['enabled']]
        disabled_ars = [ x for x in list_ars_search if not x['enabled']]
        logger.debug("disable %s" % len(disabled_ars))
        logger.debug("enable %s" % len(enabled_ars))

        self.ars_server_list_status = []
        listaction=[]
        for ars in enabled_ars:
            arsstatus = self.ping_ejabberd_and_relay(ars['jid'])
            # logger.debug("ARS DATA present %s" % ars['jid'])
            # logger.info("presence %s" % self.ping_ejabberd_and_relay(arsstatus)
            self.ars_server_list_status.append(arsstatus)
            if arsstatus['server']['presense'] == 0 or \
                    arsstatus['ars']['presense'] == 0:
                listaction.append(ars['jid'])

        if logger.level == 10 and self.ars_server_list_status :
            self.display_server_status()
            
        logger.debug("listaction %s" % listaction)
        
         # We give some time for the relay server, to be correctly/fully started
        for jidaction in listaction:
            time.sleep(1)
            arsstatus = self.ping_ejabberd_and_relay(jidaction)
            if arsstatus['server']['presense'] == 0 or \
                arsstatus['ars']['presense'] == 0:
                if self.update_table:
                    ## update table machine et relay.
                    XmppMasterDatabase().update_Presence_Relay(jidaction['jid'])

                    logger.debug("update on ping ars %s" % jidaction['jid'])
                    self.xmpplog("update on ping ars%s" % jidaction['jid'],
                                type='Monitoring',
                                sessionname=sessionid,
                                priority=-1,
                                action="xmpplog",
                                why=self.boundjid.bare,
                                module="Notify | Substitut | Monitoring",
                                date=None,
                                fromuser=jidaction['jid'])
                    if self.monitoring_message_on_machine_no_presense:
                        logger.debug("SEND MONITORING MESSAGE FOR ARS DOWN %s" % jidaction['jid'])
                        self.message_datas_to_monitoring_loadarscheck (jidaction['jid'], "ARS %s Down"%jidaction['jid'],
                                                                       informationaction="ack")
                    #logger.debug("update ARS %s" % enabled_ars)
                    if self.action_reconf_ars_machines:
                        # update machine for reconf
                        self.xmpplog("Reconf all machines of group down ars %s" % jidaction['jid'],
                                    type='Monitoring',
                                    sessionname=sessionid,
                                    priority=-1,
                                    action="xmpplog",
                                    why=self.boundjid.bare,
                                    module="Notify | Substitut | Monitoring",
                                    date=None,
                                    fromuser=ars['jid'])
                        XmppMasterDatabase().is_machine_reconf_needed(jidaction['jid'])

        for ars in disabled_ars:
            arsstatus = self.ping_ejabberd_and_relay(ars['jid'])
            if arsstatus['server']['presense'] == 1 and \
                    arsstatus['ars']['presense'] == 1:
                self.xmpplog("ars up %s" % ars['jid'],
                            type='Monitoring',
                            sessionname=sessionid,
                            priority=-1,
                            action="xmpplog",
                            why=self.boundjid.bare,
                            module="Notify | Substitut | Monitoring",
                            date=None,
                            fromuser=ars['jid'])
                XmppMasterDatabase().update_Presence_Relay(ars['jid'], presense=1)
    finally:
        self.ressource_scan_available = True

def message_datas_to_monitoring_loadarscheck (self, ars,  message, informationaction="ack"):
    ### status// "ready", "disable", "busy", "warning", "error"
    logger.debug("message_datas_to_monitoring_loadarscheck( %s,%s) " %(message, informationaction))
    sessionid = name_random(5, "monitoring_check_ars")
    self.xmpplog(message,
                type='Monitoring',
                sessionname=sessionid,
                priority=-1,
                action="xmpplog",
                why=self.boundjid.bare,
                module="Notify | Substitut | Monitoring",
                date=None,
                fromuser=ars)

    msg={
    "action": "vectormonitoringagent",
    "sessionid": "",
    "base64": False,
    "data": {
        "subaction" : "terminalalert",
        "from" : "",
        "date": "",
        "device_service": [
            {
                "alertMonitoring": {
                    "status": "warning",
                    "serial": "",
                    "firmware": "",
                    "metriques": {
                        "informationaction":  ""
                    },
                    "message": [ ""]
                }
            }
        ],
        "other_data": {}
    },
    "ret": 0}
    try:
        msg["data"]['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg["data"]['from'] = ars
        msg["sessionid"] = sessionid
        msg["data"]['device_service'][0]['alertMonitoring']['metriques']['informationaction'] =  informationaction
        msg["data"]['device_service'][0]['alertMonitoring']['message'][0] = message
        logger.debug("SEND MSG %s to %s" % (msg , self.monitor_agent))
    except Exception as e:
        logger.error("( %s) " %(str(e)))
        self.xmpplog("( %s) " %(str(e)),
                    type='Monitoring',
                    sessionname=sessionid,
                    priority=-1,
                    action="xmpplog",
                    why=self.boundjid.bare,
                    module="Notify | Substitut | Monitoring | Error",
                    date=None,
                    fromuser=ars)
    self.send_message(mto=self.monitor_agent,
                            mbody=json.dumps(msg),
                            mtype='chat')


def ping_ejabberd_and_relay(self, jid_client):
    """
        Used to test both the relayserver and the ejabberd server
        to determine which one is not functionnal.
        Args:
            jid_client: jid of the relay
    """
    jidserveur = str(jid.JID(jid_client).domain)
    jidnamears = str(jid.JID(jid_client).user)
    rep= { 'server' : { 'jid' : jidserveur, 'presense' : 1},
           'ars' : { 'jid' : jidnamears, 'presense' : 1}}
    result = self.send_ping_relay(jid_client, self.check_timeout_ping)
    if result == 1:
        return rep
    elif result == -1:
        rep['ars']['presense'] = 2
        rep['server']['presense'] = 2
        return rep
    else:
        rep['ars']['presense'] = 0
        result = self.send_ping_relay(jidserveur, self.check_timeout_ping)
        if result == 1:
            return rep
        elif  result == -1:
            rep['server']['presense'] = 2
            return rep
        else:
            rep['server']['presense'] = 0
            return rep

def send_ping_relay(self, jid,  timeout=5):
    """
        Send ping to the relay using the XEP 0199.
        ref: https://xmpp.org/extensions/xep-0199.html
        Args:
            jid: jid of the relay to ping
            timeout: time before a timeout of the IQ
    """
    logger.debug("send ping to %s " % jid)
    result = False
    err = False
    try:
        result = self['xep_0199'].send_ping(jid, timeout=timeout)
        logger.debug("ars present %s" % (jid))
        return 1
    except IqError as e:
        logger.error("test presense  %s :[%s]" % (jid, e.iq['error']['text']))
        return 0
    except IqTimeout:
        logger.error("No response from server.")
        #logger.error("ARS TIMEOUT  ")
        return -1

def display_server_status(self):
    """
        Display the status of both ejabberd and ARS.
    """
    logger.debug("+-------------------------+-+-------------------------+-+")
    logger.debug("|         EJABBERD        |S|           ARS           |S|")
    logger.debug("+-------------------------+-+-------------------------+-+")
    for status_ars in self.ars_server_list_status:
        logger.debug("|%25s|%1s|%25s|%1s|" % (status_ars['server']['jid'],
                                              status_ars['server']['presence'],
                                              status_ars['ars']['jid'],
                                              status_ars['ars']['presence']))
    logger.debug("+-------------------------+-+-------------------------+-+")

def read_conf_loadarscheck(objectxmpp):
    """
        Define all the variables and functions used in the plugin
        Args:
            objectxmpp: Permit to acces to all xmpp mecanism.
    """
    logger.debug("Initialisation plugin : %s " % plugin["NAME"])
    namefichierconf = plugin['NAME'] + ".ini"


    #objectxmpp.ars_server_list_status = []
    # for _ in range(15): logger.info("read_conf_loadarscheck")

    pathfileconf = os.path.join( objectxmpp.config.pathdirconffile, namefichierconf )
    objectxmpp.ressource_scan_available = True
    objectxmpp.ars_server_list_status = []

    if not os.path.isfile(pathfileconf):
        # not config files
        objectxmpp.check_ars_scan_interval = 120
        objectxmpp.check_timeout_ping = 5
        objectxmpp.update_table = True
        objectxmpp.action_reconf_ars_machines = True
        objectxmpp.monitoring_message_on_machine_no_presense = False
        objectxmpp.monitor_agent="master_mon@pulse"
    else:
        ars_config = ConfigParser.ConfigParser()
        ars_config.read(pathfileconf)
        if ars_config.has_option("parameters", "check_ars_scan_interval"):
            objectxmpp.check_ars_scan_interval =  ars_config.getint('parameters',
                                                                    'check_ars_scan_interval')
        else:
            # default values parameters
            objectxmpp.check_ars_scan_interval = 30

        if ars_config.has_option("parameters", "check_timeout_ping"):
            objectxmpp.check_timeout_ping =  ars_config.getint('parameters',
                                                               'check_timeout_ping')
        else:
            # default values parameters
            objectxmpp.check_timeout_ping = 15

        if ars_config.has_option("parameters", "update_table"):
            objectxmpp.update_table =  ars_config.getboolean('parameters',
                                                             'update_table')
        else:
            # default values parameters
            objectxmpp.update_table = True

        if ars_config.has_option("parameters", "action_reconf_ars_machines"):
            objectxmpp.action_reconf_ars_machines =  ars_config.getboolean('parameters',
                                                                           'action_reconf_ars_machines')
        else:
            # default values parameters
            objectxmpp.action_reconf_ars_machines = False

        if ars_config.has_option("parameters", "monitoring_message_on_machine_no_presense"):
            objectxmpp.monitoring_message_on_machine_no_presense =  ars_config.getboolean('parameters',
                                                                                          'monitoring_message_on_machine_no_presense')
        else:
            # default values parameters
            objectxmpp.monitoring_message_on_machine_no_presense = False

        if ars_config.has_option("parameters", "monitor_agent"):
            objectxmpp.monitor_agent =  ars_config.get('parameters', 'monitor_agent')
        else:
            # default values parameters
            objectxmpp.monitor_agent = "master_mon@pulse"

    logger.info("parameter loadarscheck : check_ars_scan_interval = %s" % objectxmpp.check_ars_scan_interval)
    logger.info("parameter loadarscheck : check_timeout_ping = %s" % objectxmpp.check_timeout_ping)
    logger.info("parameter loadarscheck : update_table = %s" % objectxmpp.update_table)
    if objectxmpp.update_table:
        logger.info("parameter loadarscheck : action_reconf_ars_machines = %s" % objectxmpp.action_reconf_ars_machines)
        logger.info("parameter monitoring_message_on_machine_no_presense : "\
                    "   monitoring_message_on_machine_no_presense = %s" % objectxmpp.check_ars_scan_interval)
        logger.info("parameter loadarscheck : monitor_agent = %s" % objectxmpp.monitor_agent)
    logger.info("lock ressource_scan_available = %s" % objectxmpp.ressource_scan_available)

    ## declaration function message_datas_to_monitoring_loadarscheck in object xmpp
    objectxmpp.message_datas_to_monitoring_loadarscheck = types.MethodType(message_datas_to_monitoring_loadarscheck, objectxmpp)

    ## declaration function ping_ejabberd_and_relay in object xmpp
    objectxmpp.ping_ejabberd_and_relay = types.MethodType(ping_ejabberd_and_relay, objectxmpp)

    ## declaration function send_ping_relay in object xmpp
    objectxmpp.send_ping_relay = types.MethodType(send_ping_relay, objectxmpp)

    ## declaration function arscheck in object xmpp
    objectxmpp.arscheck = types.MethodType(arscheck, objectxmpp)

    ## declaration function display_server_status in object xmpp
    objectxmpp.display_server_status = types.MethodType(display_server_status, objectxmpp)

    # schedule function arscheck
    objectxmpp.schedule('check_ars_by_ping',
                        objectxmpp.check_ars_scan_interval,
                        objectxmpp.arscheck,
                        repeat=True)
