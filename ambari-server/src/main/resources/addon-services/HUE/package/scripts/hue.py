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
import os
from ambari_commons.os_family_impl import OsFamilyFuncImpl, OsFamilyImpl
from resource_management import *


@OsFamilyFuncImpl(os_family=OsFamilyImpl.DEFAULT)
def hue(name=None):
    import params

    Directory(params.hue_log_dir,
              owner=params.hue_user,
              create_parents=True,
              group=params.user_group,
              mode=0775
              )

    Directory(params.hue_pid_dir,
              owner=params.hue_user,
              create_parents=True,
              group=params.user_group,
              mode=0775
              )  

    File(os.path.join(params.hue_conf_dir, "hue.ini"),
       owner=params.hue_user,
       group=params.hue_group,
       mode=0755,
       content=InlineTemplate(params.hue_destop_ini_content)
    )
    
    File(os.path.join(params.hue_conf_dir, "log.conf"),
       owner=params.hue_user,
       group=params.hue_group,
       mode=0755,
       content=InlineTemplate(params.hue_desktop_log_conf_content)
    )

    File(os.path.join(params.hue_conf_dir, "log4j.properties"),
       owner=params.hue_user,
       group=params.hue_group,
       mode=0755,
       content=InlineTemplate(params.hue_destop_log4j_properties_content)
    )


   