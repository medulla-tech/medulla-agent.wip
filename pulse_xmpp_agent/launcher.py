#!/usr/bin/env python
# -*- coding: utf-8; -*-
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

# file : pulse_xmpp_agent/launcher.py

import sys
if sys.version_info[0] != 2:
    sys.setdefaultencoding('utf8')

import logging
import platform
import traceback
import hashlib
from optparse import OptionParser
import os, subprocess
import time
import json
import shutil
from datetime import datetime
import psutil
import urllib2
import signal

if sys.platform.startswith('win'):
    import win32con
    import win32api

from ConfigParser import ConfigParser

logger = logging.getLogger()
# code exclusif for launcher


DEBUGPULSE = 25
filePath=os.path.dirname(os.path.realpath(__file__))

def singletonclass(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance

@singletonclass
class global_data_process:
    def __init__(self):
        self.PIDagent = 0
        self.ProcessObj  = None
        self.cmd = ""
        self.pid_schilds=[]
        self.terminate_process=False

    def load_child_process(self):
        """
            get list child process
        """
        listpid=[]
        if self.ProcessObj is not None and self.PIDagent != 0:
            parent = psutil.Process(self.PIDagent)
            children = parent.children(recursive=True)
            for child in children:
                listpid.append(child.pid)
            self.pid_schilds.extend(listpid)
            self.pid_schilds = list(set(self.pid_schilds))
        #delete child process defunct
        list_defunct=[]
        for pid_child in self.pid_schilds:
            if not psutil.pid_exists(pid_child):
                list_defunct.append(pid_child)
        for pid_defunct in list_defunct:
            try:
                self.pid_schilds.remove(pid_defunct)
            except ValueError:
                pass

    def list_child_exist(self):
        """test si 1 child exist """
        for pid_child in self.pid_schilds:
            if psutil.pid_exists(pid_child):
                return True
            return False

    def is_alive(self):
        """
            #on utilise pas les signaux process fils defunct
        """
        # poll() is None indique que le processus ne s’est pas encore terminé.
        if self.ProcessObj is not None:
            if self.ProcessObj.poll() is None:
                # process pas terminate.
                logger.debug("Process fils vivant %s" % self.PIDagent)
                return True
            else:
                logger.debug("clear Process fils defunct %s" % self.PIDagent)
                # on arrete les sous process du fils defunct
                self.stop_process_agent()
                # on libere le pere du fils defunct
                self.ProcessObj.wait()
                self.PIDagent = 0
                self.ProcessObj = None
                self.pid_schilds=[]
        return False

    def stop_process_agent(self, pere=True):
        """
            stop les process pere et fils multi os
        """
        if self.ProcessObj is not None:
            if self.PIDagent != 0:
                parent = psutil.Process(self.PIDagent)
                children = parent.children(recursive=True)
                for child in children:
                    logger.debug("kill schild process %s" % (child.pid) )
                    child.kill()
                gone, still_alive = psutil.wait_procs(children, timeout=5)
                if pere:
                    try:
                        logger.debug("kill parent process %s" % (parent.pid) )
                        parent.kill()
                        parent.wait(5)
                    except:
                        pass
                    self.PIDagent=0
                    self.ProcessObj = None
                    self.pid_schilds=[]
        self.display_Process()

    def start_process_agent(self, prog):
        if self.ProcessObj is None:
            self.cmd = prog
            if sys.platform.startswith('win'):
                self.ProcessObj = subprocess.Popen( self.cmd,
                                                    stdout=None,
                                                    stderr=None,
                                                    stdin=None,
                                                    close_fds=True)
            else:
                self.ProcessObj = subprocess.Popen( self.cmd,
                                                    stdout=None,
                                                    stderr=None,
                                                    stdin=None,
                                                    close_fds=True,
                                                    preexec_fn=os.setpgrp)
            self.PIDagent = self.ProcessObj.pid
            time.sleep(1)
            self.load_child_process()
            self.display_Process()


    def display_Process(self):
        try:
            if self.ProcessObj is not None:
                strpid="PID agent %s"%(self.PIDagent)
                logger.debug(strpid)
                logstring = "\\_ -Launcher\n    \\_ -%s"%self.PIDagent
                for schildpid in self.pid_schilds:
                    logstring = logstring + "\n\t\\_ -%s"%schildpid
                logger.debug("\n%s"%logstring)
            else:
                logger.debug("process no launcher yet")
        except:
            pass

    def _CtrlHandler(self, evt):
        """## todo intercep message in console program
        win32con.WM_QUERYENDSESSION win32con.WM_POWERBROADCAS(PBT_APMSUSPEND
        """
        if sys.platform.startswith('win'):
            if evt == win32con.CTRL_SHUTDOWN_EVENT:
                logger.debug("SIGNAL EVENT CTRL_SHUTDOWN_EVENT")
                self.terminate_process=True
                self.stop_process_agent()
                return True
            elif evt == win32con.CTRL_LOGOFF_EVENT:
                logger.debug("SIGNAL EVENT CTRL_LOGOFF EVENT")
                return True
            elif evt == win32con.CTRL_BREAK_EVENT:
                logger.debug("SIGNAL EVENT CTRL_BREAK_EVENT")
                return True
            elif evt == win32con.CTRL_CLOSE_EVENT:
                logger.debug("SIGNAL EVENT CTRL_CLOSE_EVENT")
                return True
            elif evt == win32con.CTRL_C_EVENT:
                logger.debug("SIGNAL EVENT CTRL_C_EVENT")
                self.terminate_process=True
                self.stop_process_agent()
                return True
            logger.debug("SIGNAL EVENT INCONUE")
        else:
            pass
        return False

    def signal_handler(self, signal_in, frame):
        if signal_in in [signal.SIGINT, signal.SIGQUIT,signal.SIGQUIT]:
            logger.debug("SIGNAL EVENT %s"%signal_in)
            self.terminate_process=True
            self.stop_process_agent()

class base_folder:
    def __init__(self):
        self.path_agent = os.path.join(os.path.dirname(os.path.realpath(__file__)))
        self.path_rescue = os.path.join(self.path_agent,
                                        "agentrescue")

                                              #'launcher.py',
        self.list_script_python_for_update = ['agentxmpp.py',
                                              'connectionagent.py',
                                              'replicator.py']

        self.folder_rescue_py = ['lib',
                                 'pluginsmachine',
                                 'pluginsrelay',
                                 'descriptor_scheduler_machine',
                                 'descriptor_scheduler_relay']

        self.clean_folder=["cycle",
                           os.path.join( "lib", "INFOSTMP"),
                           "sessionsmachine",
                           "INFOSTMP"]

    def _exist_rescue(self):
        if not os.path.isdir(self.path_rescue):
            return False
        return True

    def _clean_rescue_agent(self):
        if self._exist_rescue():
            logger.debug('clean rescue agent %s '%self.path_rescue)
            shutil.rmtree(self.path_rescue)

    def copytree1(self, src, dst, symlinks=False, ignore=None):
        if not os.path.exists(dst):
            os.makedirs(dst)
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                self.copytree1(s, d, symlinks, ignore)
            else:
                if not os.path.exists(d) or os.stat(s).st_mtime - os.stat(d).st_mtime > 1:
                    shutil.copy2(s, d)

    def copytree(self, src, dst, symlinks=False, ignore=None):
        logger.debug('copytree %s '%src)
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, symlinks, ignore)
            else:
                shutil.copy2(s, d)

    def copy3(self, src, dest):
        """copy et remplace file"""
        if os.path.isfile(dest):
            logger.debug('remove %s' %(dest))
            os.remove(dest)
        logger.debug('reinstall %s %s' %(src, dest))
        shutil.copy2(src, dest)

    def clean_agent_src(self):
        for fold in self.clean_folder:
            src  = os.path.join(self.path_agent, fold)
            if  os.path.isdir(src):
                shutil.rmtree(src)
            if not os.path.isdir(src):
                os.makedirs(src)

    def _create_folder_rescue(self):
        if not os.path.isdir(self.path_rescue):
            os.makedirs(self.path_rescue)
        for foldercreate in self.folder_rescue_py:
            if not os.path.isdir(os.path.join(self.path_rescue, foldercreate)):
                os.makedirs(os.path.join(self.path_rescue, foldercreate))
        folder_makedir=["script", "etc", "fileviewer", "keys", "JIDSUFFIXE" ]
        for foldercreate in folder_makedir:
            if not os.path.isdir(os.path.join(self.path_rescue, foldercreate)):
                os.makedirs(os.path.join(self.path_rescue, foldercreate))

class info_create_rescue_agent(base_folder):
    def __init__(self):
        base_folder.__init__(self)
        self._path_files_py_agent()
        # file in script
        self.folderlistscript = os.path.join(self.path_agent, "script")
        self.files_agent_script=[x for x in os.listdir(self.folderlistscript)\
                                    if os.path.isfile(os.path.join(self.folderlistscript, x))\
                                    and x[-4:] != ".pyc"]

        self.path_files_configuration = directoryconffile()
        self.list_config_file_ini = [x for x in os.listdir(self.path_files_configuration)\
                                    if os.path.isfile(os.path.join(self.path_files_configuration, x))\
                                    and (x[-4:] == ".ini" or x[-10:] == ".ini.local")]

    def _path_files_py_agent(self):
        self.files_agent={}
        for foldercreate in self.folder_rescue_py:
            folderlist = os.path.join(self.path_agent, foldercreate)
            if os.path.isdir(folderlist):
                self.files_agent[foldercreate] = [x for x in os.listdir(folderlist) if x[-3:] == ".py"]
            else:
                self.files_agent[foldercreate] = []

class info_rescue_reinstall(base_folder):
    def __init__(self):
        base_folder.__init__(self)
        self._path_files_py_agent()
        # file in script
        self.folderlistscript = os.path.join(self.path_rescue, "script")
        self.files_agent_script=[x for x in os.listdir(self.folderlistscript)\
                                    if os.path.isfile(os.path.join(self.folderlistscript, x))\
                                    and x[-4:] != ".pyc"]

        self.path_files_configuration = os.path.join(self.path_rescue, "etc")
        self.list_config_file_ini = [x for x in os.listdir(self.path_files_configuration)\
                                    if os.path.isfile(os.path.join(self.path_files_configuration, x))\
                                    and (x[-4:] == ".ini" or x[-10:] == ".ini.local")]

    def _path_files_py_agent(self):
        self.files_agent={}
        for foldercreate in self.folder_rescue_py:
            folderlist = os.path.join(self.path_rescue, foldercreate)
            if os.path.isdir(folderlist):
                self.files_agent[foldercreate] = [x for x in os.listdir(folderlist) if x[-3:] == ".py"]
            else:
                self.files_agent[foldercreate] = []

class create_rescue_agent:
    def __init__(self):
        self.info = info_create_rescue_agent()

    def save_rescue_src(self):
        # on s'assure de toujours copy 1 agent sur du net
        self.info._clean_rescue_agent()
        self.info._create_folder_rescue()
        # copy file .py  lib
        logger.debug('copy version : ')
        src  = os.path.join(self.info.path_agent, "agentversion")
        dest = os.path.join(self.info.path_rescue,"agentversion")
        logger.debug('copy %s %s' %(src, dest))
        shutil.copy2(src, dest)

        logger.debug('copy JIDSUFFIXE : ')
        src  = os.path.join(self.info.path_agent, "lib", "INFOSTMP", "JIDSUFFIXE")
        dest = os.path.join(self.info.path_rescue,"JIDSUFFIXE","JIDSUFFIXE")
        logger.debug('copy %s %s' %(src, dest))
        shutil.copy2(src, dest)

        logger.debug('copy file python : ')
        for keysfile in self.info.files_agent:
            for f in self.info.files_agent[keysfile]:
                src  = os.path.join(self.info.path_agent, keysfile,f)
                dest = os.path.join(self.info.path_rescue, keysfile, f)
                logger.debug('copy %s %s' %(src, dest))
                shutil.copy2(src, dest)
        logger.debug('copy progr python : ')
        for f in self.info.list_script_python_for_update:
            src  = os.path.join(self.info.path_agent, f)
            dest = os.path.join(self.info.path_rescue, f)
            logger.debug('copy %s %s' %(src, dest))
            shutil.copy2(src, dest)
        logger.debug('copy script embarque : ')
        for f in self.info.files_agent_script:
            src  = os.path.join(self.info.path_agent, "script", f)
            dest = os.path.join(self.info.path_rescue,"script", f)
            logger.debug('copy %s %s' %(src, dest))
            shutil.copy2(src, dest)
        logger.debug('rescue ini file : ')
        for f in self.info.list_config_file_ini:
            src  = os.path.join(self.info.path_files_configuration, f)
            dest = os.path.join(self.info.path_rescue,"etc", f)
            logger.debug('copy %s %s' %(src, dest))
            shutil.copy2(src, dest)
        logger.debug('rescue fileviewer resource')
        src  = os.path.join(self.info.path_agent, "lib", "ressources","fileviewer")
        dest = os.path.join(self.info.path_rescue,"fileviewer")
        logger.debug('copy %s %s' %(src, dest))
        self.info.copytree(src , dest )
        #logger.debug('rescue keys')
        #for f in self.info.files_agent_key:
            #src  = os.path.join(self.info.path_agent, "INFOSTMP",f)
            #dest = os.path.join(self.info.path_rescue,"INFOSTMP",f)
            #logger.debug('copy %s %s' %(src, dest))
            #shutil.copy2(src, dest)

class install_rescue_image:
    def __init__(self):
        self.info = info_rescue_reinstall()

    def reinstall_agent_rescue(self):
        self.info.clean_agent_src()
        #self.clean_agent_src()
        logger.debug('reinstall version : ')
        dest  = os.path.join(self.info.path_agent, "agentversion")
        src = os.path.join(self.info.path_rescue,"agentversion")
        logger.debug('reinstall %s %s' %(src, dest))
        self.info.copy3(src, dest)

        logger.debug('reinstall JIDSUFFIXE : ')
        dest  = os.path.join(self.info.path_agent, "lib", "INFOSTMP", "JIDSUFFIXE")
        src = os.path.join(self.info.path_rescue,"JIDSUFFIXE","JIDSUFFIXE")
        logger.debug('reinstall %s %s' %(src, dest))
        self.info.copy3(src, dest)

        logger.debug('reinstall file python : ')
        for keysfile in self.info.files_agent:
            logger.debug('***************** %s ***************' %(keysfile))
            for f in self.info.files_agent[keysfile]:
                dest  = os.path.join(self.info.path_agent, keysfile,f)
                src = os.path.join(self.info.path_rescue, keysfile, f)
                logger.debug('reinstall %s %s' %(src, dest))
                self.info.copy3(src, dest)

        logger.debug('reinstall progr python : ')
        for f in self.info.list_script_python_for_update:
            dest  = os.path.join(self.info.path_agent, f)
            src = os.path.join(self.info.path_rescue, f)
            logger.debug('reinstall %s %s' %(src, dest))
            self.info.copy3(src, dest)

        logger.debug('reinstall script embarque : ')
        for f in self.info.files_agent_script:
            dest  = os.path.join(self.info.path_agent, "script", f)
            src = os.path.join(self.info.path_rescue,"script", f)
            logger.debug('reinstall %s %s' %(src, dest))
            self.info.copy3(src, dest)

        logger.debug('reinstall ini file : ')
        for f in self.info.list_config_file_ini:
            dest  = os.path.join(directoryconffile(), f)
            src = os.path.join(self.info.path_rescue,"etc", f)
            logger.debug('reinstall %s %s' %(src, dest))
            self.info.copy3(src, dest)

        logger.debug('reinstall fileviewer resource')
        dest  = os.path.join(self.info.path_agent, "lib","ressources","fileviewer")
        src = os.path.join(self.info.path_rescue,"fileviewer")
        logger.debug('reinstall %s %s' %(src, dest))
        shutil.rmtree(dest)
        self.info.copytree( src , dest )

class Update_Remote_Agent:
    """
        this class make fingerprint of agent.
    """
    def __init__(self, dir_agent_base, autoupdate=True):
        """
        Initialisation function.

        It create the directory JSon Structure

        Args:
           dir_agent_base is location of agent
           autoupdate is switch for enable or disable remote update
        """
        self.dir_agent_base = dir_agent_base
        self.autoupdate = autoupdate
        self.directory = {"program_agent": {},
                          "version": "",
                          "version_agent": "",
                          "lib_agent": {},
                          "script_agent": {},
                          "fingerprint": ""}
        #verify exist dir and create si not exit. The default mode is 0777 (octal)
        dir_create = [dir_agent_base,
                      os.path.join(dir_agent_base, 'lib'),
                      os.path.join(dir_agent_base, 'script')]
        for path_dir_remoteagent in dir_create:
            if not os.path.exists(path_dir_remoteagent):
                os.makedirs(path_dir_remoteagent)
                logging.getLogger().debug("Creating folder for remote base agent : %s" % dir_agent_base)
        if os.path.exists(os.path.join(dir_agent_base, 'agentversion')):
            self.load_list_md5_agentbase()

    def get_md5_descriptor_agent(self):
        """
        This function allow to have the 'directory' structure in json format.

        Returns:
            It returns the whole directory
            (program_agent, version, version_agent,
              lib_agent, script_agent and fingerprint)
        """
        return self.directory

    def md5_descriptor_agent_to_string(self):
        """
        This function allow to have the 'directory' structure in string format.

        Returns:
            It returns the whole directory
            ( program_agent, version, version_agent,
              lib_agent, script_agent and fingerprint )
        """

        return json.dumps(self.get_md5_descriptor_agent(), indent=4)

    def get_fingerprint_agent_base(self):
        """
        This function allow to have the fingerprint in json format.

        Returns:
            It returns the fingerprint
        """

        return self.directory["fingerprint"]

    def load_list_md5_agentbase(self):
        """
        This function calcule le md5 de tout les fichiers de l'agent (excepter les plugins) , il calcule aussi le fingerprint de l'agent
        ces calculs sont contenues dans le 1 structure with the values
        """
        listmd5 = [] # accumule les md5 de tout les fichier de l'agent
                     # fingerprint de l'agent et le md5 de cette list ordonne au format string json
        self.directory = {"program_agent": {},
                          "version": "",
                          "version_agent": "",
                          "lib_agent": {},
                          "script_agent": {},
                          "fingerprint": ""}
        self.directory["version"] = file_get_contents(os.path.join(self.dir_agent_base,
                                                                   'agentversion')).replace("\n",
                                                                                            "").replace("\r",
                                                                                                        "").strip()
        self.directory["version_agent"] = hashlib.md5(self.directory["version"]).hexdigest()
        listmd5.append(self.directory["version_agent"])
        list_script_python_for_update = ['agentxmpp.py',
                                         'launcher.py',
                                         'connectionagent.py',
                                         'replicator.py']

        for fichiername in list_script_python_for_update:
            self.directory["program_agent"][fichiername] = hashlib.md5(file_get_contents(os.path.join(self.dir_agent_base,
                                                                                                      fichiername))).hexdigest()
            listmd5.append(self.directory["program_agent"][fichiername])

        for fichiername in [x for x in os.listdir(os.path.join(self.dir_agent_base, 'lib')) if x[-3:] == ".py"]:
            self.directory["lib_agent"][fichiername] = hashlib.md5(file_get_contents(os.path.join(self.dir_agent_base, 'lib', fichiername))).hexdigest()
            listmd5.append(self.directory["lib_agent"][fichiername])
        for fichiername in [x for x in os.listdir(os.path.join(self.dir_agent_base, 'script')) if x[-4:] == ".ps1"]:
            self.directory["script_agent"][fichiername] = hashlib.md5(file_get_contents(os.path.join(self.dir_agent_base, 'script', fichiername))).hexdigest()
            listmd5.append(self.directory["script_agent"][fichiername])
        listmd5.sort()
        self.directory["fingerprint"] = hashlib.md5(json.dumps(listmd5)).hexdigest()

def agentinfoversion(xmppobject):
    """
        return information on agent.

        Returns:
            A JSON with informations about the Agent
            (like testmodule , pathagent, agentdescriptor, pathimg,
              imgdescriptor, actiontxt, conf and plugins)
    """
    cmd = "python %s -i -v" % (os.path.join(xmppobject.pathagent, "replicator.py"))
    logger.debug("cmd : %s" % (cmd))
    result = simplecommand(cmd)
    resultobj = {}
    rr = [x.rstrip() for x in result['result']]
    val = ['testmodule', 'pathagent', 'agentdescriptor', 'pathimg', 'imgdescriptor', 'action', 'other1', 'other2']
    boottrap = 0
    for t in rr:
        if t.startswith('--') or t.startswith('__'):
            continue
        if t.endswith('pulse_xmpp_agent'):
            boottrap = boottrap + 1
        if t.startswith('{'):
            boottrap = boottrap + 1
        if t.startswith('}'):
            resultobj[val[boottrap]].append(t.strip())
            boottrap = boottrap + 1
            continue

        if not val[boottrap] in resultobj:
            resultobj[val[boottrap]] = []
        resultobj[val[boottrap]].append(t.strip())

    testmodule = resultobj['testmodule'][0]
    information = "".join(resultobj['testmodule'][1:])
    agentdescriptor = "".join(resultobj['agentdescriptor'])
    imgdescriptor = "".join(resultobj['imgdescriptor'])
    pathimg = resultobj['pathimg'][0]
    pathagent = resultobj['pathagent'][0]
    actiontxt = ",".join(resultobj['action'])
    res = {'testmodule': testmodule,
           'information': information,
           'pathagent': pathagent,
           'agentdescriptor': agentdescriptor,
           'pathimg': pathimg,
           'imgdescriptor': imgdescriptor,
           'actiontxt': actiontxt,
           "conf": xmppobject.config.updating,
           "plugins": xmppobject.dataplugininstall}
    l = json.dumps(res, indent=4)
    return l

def add_coloring_to_emit_windows(fn):
        # add methods we need to the class
    # def _out_handle(self):
        #import ctypes
        # return ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
    #out_handle = property(_out_handle)

    def _set_color(self, code):
        import ctypes
        # Constants from the Windows API
        self.STD_OUTPUT_HANDLE = -11
        hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
        ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)

    setattr(logging.StreamHandler, '_set_color', _set_color)

    def new(*args):
        FOREGROUND_BLUE = 0x0001  # text color contains blue.
        FOREGROUND_GREEN = 0x0002  # text color contains green.
        FOREGROUND_RED = 0x0004  # text color contains red.
        FOREGROUND_INTENSITY = 0x0008  # text color is intensified.
        FOREGROUND_WHITE = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED
        # winbase.h
        #STD_INPUT_HANDLE = -10
        #STD_OUTPUT_HANDLE = -11
        #STD_ERROR_HANDLE = -12

        # wincon.h
        #FOREGROUND_BLACK     = 0x0000
        FOREGROUND_BLUE = 0x0001
        FOREGROUND_GREEN = 0x0002
        #FOREGROUND_CYAN      = 0x0003
        FOREGROUND_RED = 0x0004
        FOREGROUND_MAGENTA = 0x0005
        FOREGROUND_YELLOW = 0x0006
        #FOREGROUND_GREY      = 0x0007
        FOREGROUND_INTENSITY = 0x0008  # foreground color is intensified.

        #BACKGROUND_BLACK     = 0x0000
        #BACKGROUND_BLUE      = 0x0010
        #BACKGROUND_GREEN     = 0x0020
        #BACKGROUND_CYAN      = 0x0030
        #BACKGROUND_RED       = 0x0040
        #BACKGROUND_MAGENTA   = 0x0050
        BACKGROUND_YELLOW = 0x0060
        #BACKGROUND_GREY      = 0x0070
        BACKGROUND_INTENSITY = 0x0080  # background color is intensified.

        levelno = args[1].levelno
        if(levelno >= 50):
            color = BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY
        elif(levelno >= 40):
            color = FOREGROUND_RED | FOREGROUND_INTENSITY
        elif(levelno >= 30):
            color = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
        elif(levelno >= 20):
            color = FOREGROUND_GREEN
        elif(levelno >= 10):
            color = FOREGROUND_MAGENTA
        else:
            color = FOREGROUND_WHITE
        args[0]._set_color(color)

        ret = fn(*args)
        args[0]._set_color(FOREGROUND_WHITE)
        # print "after"
        return ret
    return new

def add_coloring_to_emit_ansi(fn):
    # add methods we need to the class
    def new(*args):
        levelno = args[1].levelno
        if(levelno >= 50):
            color = '\x1b[31m'  # red
        elif(levelno >= 40):
            color = '\x1b[31m'  # red
        elif(levelno >= 30):
            color = '\x1b[33m'  # yellow
        elif(levelno >= 20):
            color = '\x1b[32m'  # green
        elif(levelno >= 10):
            color = '\x1b[35m'  # pink
        else:
            color = '\x1b[0m'  # normal
        args[1].msg = color + str(args[1].msg) + '\x1b[0m'  # normal
        # print "after"
        return fn(*args)
    return new

def directoryconffile():
    """
        This function provide the path to the configuration files of pulse-xmpp-agent.

        Return:
            it returns the path to the configuration files if it exists
            it returns None if the path does not exist
    """
    if sys.platform.startswith('linux'):
        fileconf = os.path.join(
            "/",
            "etc",
            "pulse-xmpp-agent")
    elif sys.platform.startswith('win'):
        fileconf = os.path.join(
            os.environ["ProgramFiles"],
            "Pulse",
            "etc")
    elif sys.platform.startswith('darwin'):
        fileconf = os.path.join(
            "/opt",
            "Pulse",
            "etc")
    if os.path.isdir(fileconf):
        return fileconf
    else:
        return None

def refreshfingerprint():
    fp = createfingerprintnetwork()
    file_put_contents(
        os.path.join(
            Setdirectorytempinfo(),
            'fingerprintnetwork'),
        fp)
    return fp

def simplecommandstr(cmd, emptyline=True):
    obj = {}
    p = subprocess.Popen(cmd,
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    result = p.stdout.readlines()
    obj['code'] = p.wait()
    if not emptyline:
        result=[x for x in result if x.strip()!="" ]
    obj['result'] = "\n".join(result)
    return obj

def simplecommand(cmd):
    obj = {}
    p = subprocess.Popen(cmd,
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    result = p.stdout.readlines()
    obj['code'] = p.wait()
    obj['result'] = result
    return obj

def file_get_contents(filename,
                      use_include_path=0,
                      context=None,
                      offset=-1,
                      maxlen=-1):
    if filename.find('://') > 0:
        ret = urllib2.urlopen(filename).read()
        if offset > 0:
            ret = ret[offset:]
        if maxlen > 0:
            ret = ret[:maxlen]
        return ret
    else:
        fp = open(filename, 'rb')
        try:
            if offset > 0:
                fp.seek(offset)
            ret = fp.read(maxlen)
            return ret
        finally:
            fp.close()

def refreshfingerprintconf(typeconf):
    fp = createfingerprintconf(typeconf)
    file_put_contents(
        os.path.join(
            Setdirectorytempinfo(),
            'fingerprintconf'),
        fp)
    return fp

def confinfoexist():
    filenetworkinfo = os.path.join(Setdirectorytempinfo(), 'fingerprintconf')
    if os.path.exists(filenetworkinfo):
        return True
    return False

def confchanged(typeconf):
    if confinfoexist():
        fingerprintconf = file_get_contents(
            os.path.join(
                Setdirectorytempinfo(),
                'fingerprintconf'))
        newfingerprintconf = createfingerprintconf(typeconf)
        if newfingerprintconf == fingerprintconf:
            return False
    return True

def createfingerprintconf(typeconf):
    namefileconfig = conffilename(typeconf)
    return hashlib.md5(file_get_contents(namefileconfig)).hexdigest()

def file_put_contents(filename, data):
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    f = open(filename, 'w')
    f.write(data)
    f.close()

def Setdirectorytempinfo():
    """
    This functions create a temporary directory.

    @returns path directory INFO Temporaly and key RSA
    """
    dirtempinfo = os.path.join(
        os.path.dirname(
            os.path.realpath(__file__)),
        "INFOSTMP")
    if not os.path.exists(dirtempinfo):
        os.makedirs(dirtempinfo, mode=0o007)
    return dirtempinfo

def createfingerprintnetwork():
    md5network = ""
    if sys.platform.startswith('win'):
        obj = simplecommandstr("ipconfig")
        md5network = hashlib.md5(obj['result']).hexdigest()
    elif sys.platform.startswith('linux'):
        # voir pour remplacer par  ip address | grep inet | grep -v inet6
        obj = simplecommandstr("LANG=C ifconfig | egrep '.*(inet|HWaddr).*' | grep -v inet6")
        md5network = hashlib.md5(obj['result']).hexdigest()
    elif sys.platform.startswith('darwin'):
        obj = simplecommandstr("ipconfig")
        md5network = hashlib.md5(obj['result']).hexdigest()
    return md5network

def networkinfoexist():
    """
    This function checks if the fingerprintnetwork file exists.

    Returns:
        it returns True if the file exists. False otherwise
    """
    filenetworkinfo = os.path.join(
        Setdirectorytempinfo(),
        'fingerprintnetwork')
    if os.path.exists(filenetworkinfo):
        return True
    return False

def networkchanged():
    if networkinfoexist():
        fingerprintnetwork = file_get_contents(os.path.join(
            Setdirectorytempinfo(), 'fingerprintnetwork'))
        newfingerprint = createfingerprintnetwork()
        if fingerprintnetwork == newfingerprint:
            return False
    else:
        return True

def conffilename(agenttype):
    """
        This function define where the configuration file is located.

        Args:
            agenttype: type of the agent, relay or machine or cluster for RelayServer

        Returns:
            Return the config file path

    """
    if agenttype in ["machine"]:
        conffilenameparameter = "agentconf.ini"
    elif agenttype in ["cluster"]:
        conffilenameparameter = "cluster.ini"
    else:
        conffilenameparameter = "relayconf.ini"

    if directoryconffile() is not None:
        fileconf = os.path.join(directoryconffile(), conffilenameparameter)
    else:
        fileconf = conffilenameparameter

    if conffilenameparameter == "cluster.ini":
        return fileconf

    if os.path.isfile(fileconf):
        return fileconf
    else:
        return conffilenameparameter

def testagentconf(typeconf):
    if typeconf == "relayserver":
        return True
    Config = ConfigParser()
    namefileconfig = conffilename(typeconf)
    Config.read(namefileconfig)
    if Config.has_option("type", "guacamole_baseurl")\
            and Config.has_option('connection', 'port')\
            and Config.has_option('connection', 'server')\
            and Config.has_option('global', 'relayserver_agent')\
            and Config.get('type', 'guacamole_baseurl') != ""\
            and Config.get('connection', 'port') != ""\
            and Config.get('connection', 'server') != ""\
            and Config.get('global', 'relayserver_agent') != "":
        return True
    return False

def start_agent(pathagent, agent="connection", console=False, typeagent="machine"):
    pythonexec = psutil.Process().exe()
    agentfunction   = os.path.join(pathagent, "connectionagent.py")

    if agent != "connection" :
        agentfunction =  os.path.join(pathagent, "agentxmpp.py")

    modeagent = " -c " if console else ""
    logger.debug('AGENT %s'%agent)
    if agent == "connection" :
        logger.debug("start agent connection")

        if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
            logger.debug('launcher for os system  %s %s%s -t %s' % (pythonexec,
                                                         agentfunction,
                                                         modeagent,
                                                         typeagent))
            os.system('%s %s%s -t %s' % (pythonexec,
                                         agentfunction,
                                         modeagent,
                                         typeagent))
        else:
            logger.debug('launcher for python %s%s -t %s' % (agentfunction,
                                                             modeagent,
                                                             typeagent))
            os.system('python %s%s -t %s' % (agentfunction,
                                             modeagent,
                                             typeagent))
    else:
        logger.debug("start agent machine ")
        ProcessData = global_data_process()
        ProcessData.start_process_agent([pythonexec,
                                         agentfunction,
                                         modeagent,
                                         "-t",
                                         typeagent])
        logger.debug('start agent %s'%[ pythonexec,
                                        agentfunction,
                                        modeagent,
                                        "-t",
                                        typeagent])



if __name__ == '__main__':
    #pathagent = os.path.join(os.path.dirname(os.path.realpath(__file__)))
    ProcessData = global_data_process()
    if sys.platform.startswith('win'):
        result = win32api.SetConsoleCtrlHandler(ProcessData._CtrlHandler, 1)
        if result == 0:
            logging.log(DEBUGPULSE,'Could not SetConsoleCtrlHandler (error %r)' %
                            win32api.GetLastError())
        else:
            logging.log(DEBUGPULSE,'Set handler for console events.')
    elif sys.platform.startswith('linux') :
        signal.signal(signal.SIGINT, ProcessData.signal_handler)
        signal.signal(signal.SIGQUIT, ProcessData.signal_handler)

    if platform.system()=='Windows':
        # Windows does not support ANSI escapes and we are using API calls to set the console color
        logging.StreamHandler.emit = add_coloring_to_emit_windows(logging.StreamHandler.emit)
    else:
        # all non-Windows platforms are supporting ANSI escapes so we use them
        logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)

    # format log more informations
    format = '%(asctime)s - %(levelname)s - (LAUNCHER)%(message)s'

    directory_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                  "INFOSTMP")

    BOOL_FILE_CONTROL_WATCH_DOG = os.path.join(directory_file,
                                               "BOOL_FILE_CONTROL_WATCH_DOG")
    if os.path.isfile(BOOL_FILE_CONTROL_WATCH_DOG):
        os.remove(BOOL_FILE_CONTROL_WATCH_DOG)

    file_put_contents(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   "INFOSTMP",
                                   "pidlauncher"), "%s" % os.getpid())


    if sys.platform.startswith('win'):
        try:
            result = subprocess.check_output(["icacls",
                                              os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                           "INFOSTMP",
                                                           "pidlauncher"),
                                              "/setowner",
                                              "pulseuser",
                                              "/t"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            pass
    optp = OptionParser()
    optp.add_option("-t", "--type",
                    dest="typemachine", default=False,
                    help="Type machine: machine or relayserver")

    optp.add_option("-c", "--consoledebug", action="store_true",
                    dest="consoledebug", default=False,
                    help="console debug")

    opts, args = optp.parse_args()

    if opts.typemachine.lower() in ["machine"]:
        defaultnamelogfile = "xmpp-agent-machine.log"
    else:
        defaultnamelogfile = "xmpp-agent-relay.log"

    if sys.platform.startswith('win'):
        logfile = os.path.join(os.environ["ProgramFiles"],
                                    "Pulse",
                                    "var",
                                    "log",
                                    defaultnamelogfile)
    elif sys.platform.startswith('darwin'):
        logfile = os.path.join(
            "/opt",
            "Pulse",
            "var",
            "log",
            defaultnamelogfile)
    else:
        logfile = os.path.join("/",
                                    "var",
                                    "log",
                                    "pulse",
                                    defaultnamelogfile)
    if opts.consoledebug:
        logging.basicConfig(level = logging.DEBUG, format=format)
    else:
        logging.basicConfig(level = logging.DEBUG,
                            format=format,
                            filename = logfile,
                            filemode = 'a')
    logger.debug("Start launcher")

    if not opts.typemachine.lower() in ["machine",'relayserver']:
        logger.error("Parameter error command line type option -t")
        sys.exit(1)
    if not testagentconf(opts.typemachine):
        logger.warning("configuration option missing option checking are : \n"\
                        "\tin section type\n"\
                            "\t\toption : guacamole_baseurl\n"\
                        "\tin section connection\n"\
                            "\t\toption : port\n"\
                            "\t\toption : server\n"\
                        "\tin section global\n"\
                            "\t\toption : relayserver_agent\n")
        logger.debug("the option missing We need to reconfigure")

    networkchanged = networkchanged()
    if networkchanged:
        logger.debug("The network changed. We need to reconfigure")
        refreshfingerprint()

    configchanged = confchanged(opts.typemachine)
    if configchanged:
        logger.info ("The configuration changed. We need to reconfigure")
        refreshfingerprintconf(opts.typemachine)

    testagenttype = testagentconf(opts.typemachine)

    testspeedagent = networkchanged or configchanged or not testagenttype

    path_reconf_nomade = os.path.join(filePath, "BOOL_FILE_ALWAYSNETRECONF")
    if os.path.exists(path_reconf_nomade):
        testspeedagent = True
        print ("file %s must Reconf " % path_reconf_nomade)

    if  testspeedagent:
        logger.debug("launch configurator agent")

    pathagent = os.path.join(os.path.dirname(os.path.realpath(__file__)))

    launcher = os.path.join(pathagent, "launcher.py")
    connectionagent = os.path.join(pathagent, "connectionagent.py")
    agentxmpp = os.path.join(pathagent, "agentxmpp.py")


    pythonexec = psutil.Process().exe()

    os.chdir(pathagent)

    if ProcessData.terminate_process:
        logger.debug("Quit program")
        sys.exit(0)

    if opts.typemachine.lower() in ["machine"]:
        if  testspeedagent:
            start_agent(pathagent ,agent="connection", console=opts.consoledebug)


    if ProcessData.terminate_process:
        logger.debug("Quit program")
        sys.exit(0)

    start_agent(pathagent, agent="am", console=opts.consoledebug, typeagent=opts.typemachine)


    if ProcessData.terminate_process:
        logger.debug("Quit program")
        sys.exit(0)
    test= 1
    logger.debug('start loop loop test')
    # possible genere descripteur agent file
    # Update_Remote_Agentlist = Update_Remote_Agent(pathagent, True )
    time.sleep(20)
    try:
        # on cree l'image rescue si elle n'existe pas
        red = create_rescue_agent()
        if not red.info._exist_rescue():
            # il n'y a pas d'agent rescue on le cree
            red.save_rescue_src()
    except:
        logger.error("\n%s"%(traceback.format_exc()))

    update_rescue_on_stabilisation = False
    countcycle = 1
    logger.debug('launcher listen mode')
    logger.debug('moditoring and watch dog')
    while 1:
        if ProcessData.terminate_process:
            logger.debug("Quit program on event")
            break
        ProcessData.is_alive() # verify process exist
        ProcessData.load_child_process()
        try:
            logger.debug('################ LOOP LAUNCHER CYCLE %s#################'%countcycle)
            if (countcycle % 6) == 0: #toutes les 60 secondes
                if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
                    # action a faire tout le n secondes sur linux serveur
                    logger.debug('monitoring memoire linux')
                    ret = simplecommandstr("free -m",  emptyline=False)
                    logger.debug("%s" % ret['result'])
                    ret = simplecommandstr("mpstat -P ALL",  emptyline=False)
                    logger.debug("%s" % ret['result'])
            if (countcycle % 18) == 0: # toutes les 180 secondes
                logger.debug("traitement watch dog AT : %s"%str(datetime.now()))
                ProcessData.display_Process()
                if os.path.isfile(BOOL_FILE_CONTROL_WATCH_DOG):
                    # pas de soucis detecter
                    # on efface le fichier du chien de garde
                    data_file = file_get_contents(BOOL_FILE_CONTROL_WATCH_DOG)
                    # on supprime le fichier de watchdog
                    os.remove(BOOL_FILE_CONTROL_WATCH_DOG)
                    logger.debug("watch dog : %s" % data_file)
                    if  not update_rescue_on_stabilisation:
                        # On cree le rescue 1 seule fois quand agent update_rescue_on_stabilisation.
                        update_rescue_on_stabilisation = True
                        logger.debug('control si start agent stabilisé')
                        logger.debug('on ne lance pas lagent rescue cat agent fonctionnement correct')
                        # mais on sauve l'agent stabilise seulement si update_rescue_on_stabilisation est a False
                        try:
                            red = create_rescue_agent().save_rescue_src()
                        except:
                            logger.error("\n%s"%(traceback.format_exc()))
                else:
                    logger.debug('l agent a 1 soucis ( start pas encore stabilisé)')
                    #1) on stope l'agent
                    ProcessData.stop_process_agent()
                    #2) on rescue l'agent avec image rescue
                    logger.debug('On reinstall rescue')
                    ret=install_rescue_image().reinstall_agent_rescue
                    logger.debug('On relance reconfiguration')
                    # on lance 1 reconfigure si machine.
                    if opts.typemachine.lower() in ["machine"]:
                        start_agent(pathagent,
                                    agent="connection",
                                    console=opts.consoledebug)

                    #3) ici on lance 1 agent rescue specialise permettant des action
                    ##quel que soit l'etat de l'agnet machine
                    #i l n'existe pas encore.

                    logger.debug("on lance lagent regenere.")
                    start_agent(pathagent, agent="am", console=opts.consoledebug, typeagent=opts.typemachine)
            else:
                #logger.debug("CYCLE 10 seconde terminate")
                pass
        except:
            logger.error("\n%s"%(traceback.format_exc()))
        countcycle = countcycle + 1
        time.sleep(10)
    ProcessData.stop_process_agent()
    time.sleep(1)
