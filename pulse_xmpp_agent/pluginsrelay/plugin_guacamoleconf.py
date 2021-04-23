# -*- coding: utf-8 -*-
#
# (c) 2016 siveo, http://www.siveo.net
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
# file : pluginsrelay/plugin_guacamoleconf.py

import MySQLdb
import traceback
import socket
import base64
import json
import logging

class GuacamoleError(Exception):
    pass

plugin = {"VERSION": "2.21", "NAME": "guacamoleconf", "TYPE": "relayserver"}
logger = logging.getLogger()


def get_free_tcp_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def insertprotocole(protocole, hostname):
    logger.debug("New connection for machine %s_%s protcol %s" % (protocole.upper(),
                                                                  hostname,
                                                                  protocole.lower()))
    return """INSERT
                INTO guacamole_connection (connection_name, protocol)
                    VALUES ( '%s_%s', '%s');""" % (protocole.upper(),
                                                   hostname,
                                                   protocole.lower())

def deleteprotocole(protocole, hostname):
    logger.debug("Deleting old connection for : %s_%s" % (protocole.upper(),
                                                          hostname))
    return """DELETE FROM `guacamole_connection`
                     WHERE connection_name = '%s_%s';"""%(protocole.upper(),
                                                          hostname)

def insertparameter(index, parameter, value):
    logger.debug("New parameters in guacamole database: %s = %s" % (parameter,
                                                                    value))
    return """INSERT
                 INTO guacamole_connection_parameter (connection_id,
                                                      parameter_name,
                                                      parameter_value)
                 VALUES (%s, '%s', '%s');"""%(index,
                                              parameter,
                                              value)

def action(objectxmpp, action, sessionid, data, message, dataerreur):
    logger.debug("###################################################")
    logger.debug("call %s from %s"%(plugin, message['from']))
    logger.debug("###################################################")
    logger.debug(json.dumps(data, indent=4))
    logger.debug("###################################################")
    resultaction = "result%s" % action
    result = {}
    result['action'] = resultaction
    result['ret'] = 0
    result['sessionid'] = sessionid
    result['base64'] = False
    result['data'] = {}
    dataerreur['action'] = resultaction
    dataerreur['data']['msg'] = "ERROR : %s" % action
    dataerreur['sessionid'] = sessionid
    #try:
    try:
        db = MySQLdb.connect(host=objectxmpp.config.guacamole_dbhost,
                                user=objectxmpp.config.guacamole_dbuser,
                                passwd=objectxmpp.config.guacamole_dbpasswd,
                                db=objectxmpp.config.guacamole_dbname)
        logger.debug("Connecting with parameters\n" \
                        "\thost: %s\n" \
                        "\tuser: %s\n" \
                        "\tdb: %s\n" %( objectxmpp.config.guacamole_dbhost,
                                    objectxmpp.config.guacamole_dbuser,
                                    objectxmpp.config.guacamole_dbname))
    except Exception as e:
        errorstr = "%s" % traceback.format_exc()
        logger.error("\n%s" % (errorstr))
        dataerreur['data']['msg'] = "REMOTE MySQL Error: %s on %s\n" \
                                    "traceback\n"\
                                    "%s" % (str(e),
                                            objectxmpp.boundjid.bare,
                                            errorstr)
        #raise GuacamoleError("MySQL connection error")
        db.close()
        return

    try:
        cursor = db.cursor()
    except Exception as e:
        errorstr = "%s" % traceback.format_exc()
        logger.error("\n%s" % (errorstr))
        dataerreur['data']['msg'] = "REMOTE Error: %s on %s\n" \
                                    "traceback\n"\
                                    "%s" % (str(e),
                                            objectxmpp.boundjid.bare,
                                            errorstr)
        db.close()
        return
    result['data']['uuid'] = data['uuid']
    result['data']['machine_id'] = data['machine_id']
    result['data']['connection'] = {}

    # Add only detected protocols
    if hasattr(objectxmpp.config, 'guacamole_protocols'):
        protos = list(set(objectxmpp.config.guacamole_protocols.split()) \
                    & set(data['remoteservice'].keys()))
    else:
        protos = data['remoteservice'].keys()

    try:
        # delete connection
        for proto in protos:
            cursor.execute(deleteprotocole(proto,
                                            data['hostname']))
            db.commit()
        # create connection
        for proto in protos:
            result['data']['connection'][proto.upper()] = -1
            cursor.execute(insertprotocole(proto, data['hostname']))
            db.commit()
            result['data']['connection'][proto.upper()] = cursor.lastrowid
    #except MySQLdb.Error as e:
        #errorstr = "%s" % traceback.format_exc()
        #logger.error("\n%s" % (errorstr))
        #dataerreur['data']['msg'] = "REMOTE MySQL Error: %s on %s\n" \
                                    #"traceback\n"\
                                    #"%s" % (str(e),
                                            #objectxmpp.boundjid.bare,
                                            #errorstr)
        #raise GuacamoleError("MySQL error deleting existing protocol")
    except Exception as e:
        errorstr = "%s" % traceback.format_exc()
        logger.error("\n%s" % (errorstr))
        dataerreur['data']['msg'] = "REMOTE Error: %s on %s\n" \
                                    "traceback\n"\
                                    "%s" % (str(e),
                                            objectxmpp.boundjid.bare,
                                            errorstr)
        db.close()
        return
    ###################################
    ## configure parameters
    ###################################
    try:
        for proto in protos:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((data['machine_ip'], int(data['remoteservice'][proto])))
                # Machine is directly reachable. We will not need a reversessh connection
                hostname = data['machine_ip']
                cursor.execute(insertparameter(result['data']['connection'][proto.upper()],
                                                'hostname',
                                                hostname))
                port = data['remoteservice'][proto]
                cursor.execute(insertparameter(result['data']['connection'][proto.upper()],
                                                'port',
                                                port))
            except socket.error:
                # Machine is not reachable. We will need a reversessh connection
                hostname = 'localhost'
                cursor.execute(insertparameter(result['data']['connection'][proto.upper()],
                                                'hostname',
                                                hostname))
                port = get_free_tcp_port()
                if port != -1:
                    cursor.execute(insertparameter(result['data']['connection'][proto.upper()],
                                                    'port',
                                                    port))
                    if proto.upper() == 'VNC':
                        # We need additional options for reverse VNC
                        listen_timeout = 50000
                        cursor.execute(insertparameter(result['data']['connection'][proto.upper()],
                                                        'listen-timeout',
                                                        listen_timeout))
                        reverse_connect = 'true'
                        cursor.execute(insertparameter(result['data']['connection'][proto.upper()],
                                                        'reverse-connect',
                                                        reverse_connect))
                else:
                    logger.error("Error finding a free port for reverse VNC")
            finally:
                sock.close()

            # Options specific to a protocol
            for option in objectxmpp.config.__dict__.keys():
                if option.startswith(proto.lower()):
                    if option == 'ssh_keyfile':
                        # specific processing for ssh key
                        with open(objectxmpp.config.ssh_keyfile, 'r') as keyfile:
                            keydata=keyfile.read()

                        cursor.execute(insertparameter(\
                            result['data']['connection'][proto.upper()],
                        'private-key', keydata))
                    else:
                        # Update account for the os
                        if option[4:] == "username":
                            username = "pulseuser"

                            cursor.execute(insertparameter(\
                                            result['data']['connection'][proto.upper()],
                                            "username",
                                            username))
                        else:
                            cursor.execute(insertparameter(\
                                            result['data']['connection'][proto.upper()],
                                            option[4:],
                                            getattr(objectxmpp.config,
                                                    option)))
                # Commit our queries
                db.commit()
    #except MySQLdb.Error as e:
        #errorstr = "%s" % traceback.format_exc()
        #logger.error("\n%s" % (errorstr))
        #dataerreur['data']['msg'] = "REMOTE MySQL Error: %s on %s\n" \
                                    #"traceback\n"\
                                    #"%s" % (str(e),
                                            #objectxmpp.boundjid.bare,
                                            #errorstr)
        #raise GuacamoleError("MySQL error inserting existing protocol")
    except Exception as e:
        errorstr = "%s" % traceback.format_exc()
        logger.error("\n%s" % (errorstr))
        dataerreur['data']['msg'] = "REMOTE Error: %s on %s\n" \
                                    "traceback\n"\
                                    "%s" % (str(e),
                                            objectxmpp.boundjid.bare,
                                            errorstr)
        db.close()
    #except Exception as e:
        #logger.error("Guacamole configuration error %s" % (str(e)))
        #objectxmpp.send_message(mto=message['from'],
                               #mbody=json.dumps(dataerreur),
                               #mtype='chat')
    #finally:
        #db.close()
        ## send message result conf guacamol.
        #if result['base64'] is True:
            #result['data'] = base64.b64encode(json.dumps(result['data']))
        #logger.debug("Sending message %s" % result)
        #objectxmpp.send_message(mto=message['from'],
                                #mbody=json.dumps(result),
                                #mtype='chat')

