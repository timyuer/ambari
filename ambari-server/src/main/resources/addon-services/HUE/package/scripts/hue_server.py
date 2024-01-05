import sys, os, pwd, grp, signal, time
from resource_management import *
from subprocess import call
from resource_management.libraries.script.script import Script
from hue_service import hue_service
from hue import hue


class hue_server(Script):
  """
  Contains the interface definitions for methods like install, 
  start, stop, status, etc. for the Hue Server
  """
  def install(self, env):
    config = Script.get_config()
    Logger.info("config['clusterHostInfo']: {0} ".format(config['clusterHostInfo']))
    # Import properties defined in -config.xml file from params class
    import params
    env.set_params(params)
    self.install_packages(env)
    self.configure(env)
    hue_service('hue_server', action='metastoresync', upgrade_type=None)
 

  def configure(self, env):
    import params
    env.set_params(params)
    hue(name = 'hue_server')
    
  def start(self, env):
    import params
    self.configure(env)
    hue_service('hue_server', action='start', upgrade_type=None)
 
  def stop(self, env):
    import params
    env.set_params(params)
    hue_service('hue_server', action='stop', upgrade_type=None)
 

  def status(self, env):
    import status_params
    env.set_params(status_params)
    #use built-in method to check status using pidfile
    check_process_status(status_params.hue_server_pid_file)

  def usersync(self, env):
    import params
    env.set_params(params)
    hue_service('hue_server', action='usersync', upgrade_type=None)
 

  def metastoresync(self, env):
    import params
    env.set_params(params)
    hue_service('hue_server', action='metastoresync', upgrade_type=None)
 

if __name__ == "__main__":
  hue_server().execute()
