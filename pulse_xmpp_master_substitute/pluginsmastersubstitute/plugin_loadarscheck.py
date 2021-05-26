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
from lib.managepackage import managepackage
from lib.managesession import session
from lib.utils import getRandomName, call_plugin, name_random, name_randomplus, file_get_contents, file_put_contents
import ConfigParser
import types
import datetime
import time
#from datetime import datetime
import random
import re
from sleekxmpp import jid
from sleekxmpp.exceptions import IqError, IqTimeout

logger = logging.getLogger()


plugin = {"VERSION": "1.0", "NAME": "loadarscheck", "TYPE": "substitute"}

def action(objectxmpp, action, sessionid, data, msg, ret):
    try:
        logger.debug("=====================================================")
        logger.debug("call %s from %s" % (plugin, msg['from']))
        logger.debug("=====================================================")
        compteurcallplugin = getattr(objectxmpp, "num_call%s"%action)

        if compteurcallplugin == 0:
            read_conf_loadarscheck(objectxmpp)
        # must list plugin substitute for deploy
        # wakeonlan, wakeonlangroup, deploysyncthing, resultenddeploy,
        # ___________________ code  _____________________

        # _______________________________________________
    except Exception as e:
        logger.error("machine info %s\n%s" % (str(e),traceback.format_exc()))


def arscheck(self):
    """
        # cette function ping tout les ars toute le n sesonde.
    """
    logger.debug("====================arscheck=================================")
    sessionid = name_random(5, "monitoring_check_ars")
    # scheck ars enable
    # logger.debug("objectxmpp.ressource_scan_disponible is %s " % self.ressource_scan_disponible)
    if not self.ressource_scan_disponible:
        logger.debug("ressource non disponible")
        return
    try:
        self.ressource_scan_disponible = False
        list_ars_search =  XmppMasterDatabase().getRelayServer()
        #logger.debug("list_ars_search %s" % list_ars_search)
        list_ars_enable = [ x for x in list_ars_search if x['enabled']]
        list_ars_disable = [ x for x in list_ars_search if not x['enabled']]
        logger.debug("disable %s" % len(list_ars_disable))
        logger.debug("enable %s" % len(list_ars_enable))
        self.ars_server_list_status = []
        listaction=[]
        for ars in list_ars_enable:
            arsstatus = self.test_client_and_serveur(ars['jid'])
            # logger.debug("ARS DATA present %s" % ars['jid'])
            # logger.info("presence %s" % self.test_client_and_serveur(arsstatus)
            self.ars_server_list_status.append(arsstatus)
            if arsstatus['server']['presense'] == 0 or \
                    arsstatus['ars']['presense'] == 0:
                # no presence
                listaction.append(ars['jid'])
        if logger.level == 10 and self.ars_server_list_status :
            self.affiche_server_status()
        logger.debug("listaction %s" % listaction)
        # trasitoire effect on donne du temps au relay server d'etre bien demare.
        for jidaction in listaction:
            time.sleep(1)
            arsstatus = self.test_client_and_serveur(jidaction)
            if arsstatus['server']['presense'] == 0 or \
                arsstatus['ars']['presense'] == 0:
                if self.update_table:

                    ## update table machine et relay.
                    XmppMasterDatabase().update_Presence_Relay(ars['jid'])
                    logger.debug("update on ping ars %s" % ars['jid'])
                    self.xmpplog("update on ping ars%s" % ars['jid'],
                                type='Monitoring',
                                sessionname=sessionid,
                                priority=-1,
                                action="xmpplog",
                                why=self.boundjid.bare,
                                module="Notify | Substitut | Monitoring",
                                date=None,
                                fromuser=ars['jid'])
                    if self.monitoring_message_on_machine_no_presense:
                        logger.debug("SEND MONITORING MESSAGE FOR ARS DOWN %s" % ars['jid'])
                        self.message_datas_to_monitoring_loadarscheck (ars['jid'], "ARS %s Down"%ars['jid'],
                                                                       informationaction="ack")
                    #logger.debug("update ARS %s" % list_ars_enable)
                    if self.action_reconf_ars_machines:
                        # update machine for reconf
                        self.xmpplog("Reconf all machines of group down ars %s" % ars['jid'],
                                    type='Monitoring',
                                    sessionname=sessionid,
                                    priority=-1,
                                    action="xmpplog",
                                    why=self.boundjid.bare,
                                    module="Notify | Substitut | Monitoring",
                                    date=None,
                                    fromuser=ars['jid'])
                        XmppMasterDatabase().update_reconf_mach_of_Relay_down(ars['jid'])
                        #logger.error("Update reconf %s" % ars['jid'])

        for ars in list_ars_disable:
            arsstatus = self.test_client_and_serveur(ars['jid'])
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
        self.ressource_scan_disponible = True

def message_datas_to_monitoring_loadarscheck (self,ars,  message, informationaction="ack"):
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


def test_client_and_serveur(self, jid_client):
    jidserveur = str(jid.JID(jid_client).domain)
    jidnamears = str(jid.JID(jid_client).user)
    rep= { 'server' : { 'jid' : jidserveur, 'presense' : 1},
           'ars' : { 'jid' : jidnamears, 'presense' : 1}}
    result = self.ping_jid_xep_0199(jid_client, self.check_timeout_ping)
    if result == 1:
        return rep
    elif result == -1:
        rep['ars']['presense'] = 2
        rep['server']['presense'] = 2
        return rep
    else:
        rep['ars']['presense'] = 0
        result = self.ping_jid_xep_0199(jidserveur, self.check_timeout_ping)
        if result == 1:
            return rep
        elif  result == -1:
            rep['server']['presense'] = 2
            return rep
        else:
            rep['server']['presense'] = 0
            return rep

def ping_jid_xep_0199(self, jid,  timeout=5):
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

def affiche_server_status(self):
    logger.debug("+-------------------------+-+-------------------------+-+")
    logger.debug("|         SERVER          |S|           ARS           |S|")
    logger.debug("+-------------------------+-+-------------------------+-+")
    for status_ars in self.ars_server_list_status:
        logger.debug("|%25s|%1s|%25s|%1s|" % (status_ars['server']['jid'],
                                             status_ars['server']['presense'],
                                             status_ars['ars']['jid'],
                                             status_ars['ars']['presense']))
    logger.debug("+-------------------------+-+-------------------------+-+")

def read_conf_loadarscheck(objectxmpp):
    logger.debug("Initialisation plugin : %s " % plugin["NAME"])
    namefichierconf = plugin['NAME'] + ".ini"


    #objectxmpp.ars_server_list_status = []
    # for _ in range(15): logger.info("read_conf_loadarscheck")

    pathfileconf = os.path.join( objectxmpp.config.pathdirconffile, namefichierconf )
    logger.debug("fichier configuration if exist : %s " % pathfileconf)
    objectxmpp.ressource_scan_disponible = True
    objectxmpp.ars_server_list_status = []

    if not os.path.isfile(pathfileconf):
        # not config files
        objectxmpp.check_ars_scan_interval = 20
        objectxmpp.check_timeout_ping = 1
        objectxmpp.update_table = True
        objectxmpp.action_reconf_ars_machines = True
        objectxmpp.monitoring_message_on_machine_no_presense = True
        objectxmpp.monitor_agent="master_mon@pulse"
    else:
        Config = ConfigParser.ConfigParser()
        Config.read(pathfileconf)
        if Config.has_option("parameters", "check_ars_scan_interval"):
            objectxmpp.check_ars_scan_interval =  Config.getint('parameters', 'check_ars_scan_interval')
        else:
            # default values parameters
            objectxmpp.check_ars_scan_interval = 30

        if Config.has_option("parameters", "check_timeout_ping"):
            objectxmpp.check_timeout_ping =  Config.getint('parameters', 'check_timeout_ping')
        else:
            # default values parameters
            objectxmpp.check_timeout_ping = 15

        if Config.has_option("parameters", "update_table"):
            objectxmpp.update_table =  Config.getboolean('parameters', 'update_table')
        else:
            # default values parameters
            objectxmpp.update_table = True

        if Config.has_option("parameters", "action_reconf_ars_machines"):
            objectxmpp.update_table =  Config.getboolean('parameters', 'action_reconf_ars_machines')
        else:
            # default values parameters
            objectxmpp.action_reconf_ars_machines = False

        if Config.has_option("parameters", "monitoring_message_on_machine_no_presense"):
            objectxmpp.update_table =  Config.getboolean('parameters', 'monitoring_message_on_machine_no_presense')
        else:
            # default values parameters
            objectxmpp.monitoring_message_on_machine_no_presense = False

        if Config.has_option("parameters", "monitor_agent"):
            objectxmpp.update_table =  Config.get('parameters', 'monitor_agent')
        else:
            # default values parameters
            objectxmpp.monitor_agent = "master_mon@pulse"

    logger.info("parameter loadarscheck : check_ars_scan_interval = %s" % objectxmpp.check_ars_scan_interval)
    logger.info("parameter loadarscheck : check_timeout_ping = %s" % objectxmpp.check_timeout_ping)
    logger.info("lock ressource_scan_disponible = %s" % objectxmpp.ressource_scan_disponible)

    ## declaration function message_datas_to_monitoring_loadarscheck in object xmpp
    objectxmpp.message_datas_to_monitoring_loadarscheck = types.MethodType(message_datas_to_monitoring_loadarscheck, objectxmpp)

    ## declaration function test_client_and_serveur in object xmpp
    objectxmpp.test_client_and_serveur = types.MethodType(test_client_and_serveur, objectxmpp)

    ## declaration function ping_jid_xep_0199 in object xmpp
    objectxmpp.ping_jid_xep_0199 = types.MethodType(ping_jid_xep_0199, objectxmpp)

    ## declaration function arscheck in object xmpp
    objectxmpp.arscheck = types.MethodType(arscheck, objectxmpp)

    ## declaration function affiche_server_status in object xmpp
    objectxmpp.affiche_server_status = types.MethodType(affiche_server_status, objectxmpp)

    # schedule function arscheck
    objectxmpp.schedule('check_ars_by_ping',
                        objectxmpp.check_ars_scan_interval,
                        objectxmpp.arscheck,
                        repeat=True)
