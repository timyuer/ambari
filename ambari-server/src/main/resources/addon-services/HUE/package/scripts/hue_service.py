#!/usr/bin/env python
"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""
from resource_management import *
import os
from ambari_commons.os_family_impl import OsFamilyFuncImpl, OsFamilyImpl


def hue_service(name, action='start', upgrade_type=None):
    # initializing the op command variables
    import params 
    
    hueExecEnv={'JAVA_HOME': params.java_home,
                      'HADOOP_CONF_DIR': params.hadoop_conf_dir,
                      'CRYPTOGRAPHY_ALLOW_OPENSSL_102': 'True',
                      'LD_LIBRARY_PATH': '$LD_LIBRARY_PATH:/usr/hdp/current/hue/lib-native',
                      }
    if action == 'start':
      Execute(format("{hue_bin_dir}/supervisor >> {hue_log_file} 2>&1 &"),
          environment=hueExecEnv,
          user=params.hue_user
        )
      Execute ('ps -ef | grep hue | grep supervisor | grep -v grep | awk \'{print $2}\' > ' + params.hue_server_pid_file, user=params.hue_user)


    elif action == 'stop':        
      # Kill the process of Hue
      Execute ('ps -ef | grep hue | grep -v grep | awk  \'{print $2}\' | xargs kill -9', user=params.hue_user, ignore_failures=True)
      File(params.hue_server_pid_file,
        action = "delete",
        owner = params.hue_user
      )

    elif action == 'metastoresync':
      if params.metastore_db_flavor != 'sqlite3':
        Execute (format("{hue_bin_dir}/hue syncdb --noinput"), 
                 environment=hueExecEnv,
                 user=params.hue_user)
        Execute (format("{hue_bin_dir}/hue migrate"), 
                  environment=hueExecEnv,
                 user=params.hue_user)
      else:
        Logger.info("echo Hue Metastore is stored in $HUE/desktop/desktop.db >> " + params.hue_log_file)

    elif action == 'usersync':
      if params.usersync_enabled:
        if params.usersync_source == 'unix':
          Execute ('{0}/hue useradmin_sync_with_unix --min-uid={1} --max-uid={2} --min-gid={3} --max-gid={4}'.format(params.hue_bin_dir, params.usersync_unix_minUserId, params.usersync_unix_maxUserId, params.usersync_unix_minGroupId, params.usersync_unix_maxGroupId), environment=hueExecEnv,user=params.hue_user)
        else:
          Execute ('{0}/hue sync_ldap_users_and_groups'.format(params.hue_bin_dir), environment=hueExecEnv,user=params.hue_user)
      else:
        Logger.info("Hue UserSync is disabled >> " + params.hue_log_file)
     
    else:
        Logger.info( format("unknown command type: :{action}"))

