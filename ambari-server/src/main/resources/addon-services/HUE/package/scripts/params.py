#!/usr/bin/env python
import os,re
import resource_management.libraries.functions
from resource_management import *
from ambari_commons.os_check import OSCheck
from ambari_commons.str_utils import cbool, cint
from resource_management.libraries.functions import StackFeature
from resource_management.libraries.functions import conf_select
from resource_management.libraries.functions import get_kinit_path
from resource_management.libraries.functions import stack_select
from resource_management.libraries.functions.default import default
from resource_management.libraries.functions.format import format
from resource_management.libraries.functions.get_stack_version import get_stack_version
from resource_management.libraries.functions.stack_features import check_stack_feature
from resource_management.libraries.functions.version import format_stack_version
from resource_management.libraries.resources.hdfs_resource import HdfsResource
from resource_management.libraries.functions.get_not_managed_resources import get_not_managed_resources
from resource_management.libraries.script.script import Script
import status_params
import functools
import commands

# a map of the Ambari role to the component name
# for use with <stack-root>/current/<component>
SERVER_ROLE_DIRECTORY_MAP = {
  'HUE_SERVER' : 'hue-server',
}

component_directory = Script.get_component_from_role(SERVER_ROLE_DIRECTORY_MAP, "HUE_SERVER")
config = Script.get_config()
tmp_dir = Script.get_tmp_dir()
stack_root = Script.get_stack_root()

# New Cluster Stack Version that is defined during the RESTART of a Rolling Upgrade
version = default("/commandParams/version", None)
stack_name = default("/hostLevelParams/stack_name", None)
cluster_name = str(config['clusterName'])

# Java home path
java_home = config["ambariLevelParams"]["java_home"] if "java_home" in config["ambariLevelParams"] else None
http_host = config['agentLevelParams']['hostname']
hostname_lowercase = config['agentLevelParams']['hostname'].lower()
http_port = config['configurations']['hue-env']['http_port']
hue_pid_dir = config['configurations']['hue-env']['hue_pid_dir']
hue_log_dir = config['configurations']['hue-env']['hue_log_dir']
hue_server_pid_file = os.path.join(hue_pid_dir, 'hue-server.pid')
hue_log_file = os.path.join(hue_log_dir, 'hue-install.log')
hue_user = config['configurations']['hue-env']['hue_user']
hue_group = config['configurations']['hue-env']['hue_group']
hue_local_home_dir = os.path.expanduser("~{0}".format(hue_user))
hue_hdfs_home_dir = format('/user/{hue_user}')
user_group = config['configurations']['cluster-env']['user_group']

#cmd = "/usr/bin/hdp-select versions"
#hue_install_dir = '/usr/hdp/'+commands.getoutput(cmd)
hue_install_dir='/usr/hdp/current'
hue_dir = format('{hue_install_dir}/hue')
hue_conf_dir = format('{hue_dir}/desktop/conf')
hue_bin_dir = format('{hue_dir}/build/env/bin')


# configurations of metastore 
metastore_db_flavor =  (config['configurations']['hue-desktop-ini']['DB_FLAVOR']).lower()
metastore_db_host = config['configurations']['hue-desktop-ini']['db_host'].strip()
metastore_db_port = str(config['configurations']['hue-desktop-ini']['db_port']).strip()
metastore_db_name = config['configurations']['hue-desktop-ini']['db_name'].strip()
metastore_db_user = config['configurations']['hue-desktop-ini']['db_user'].strip()
metastore_db_password = str(config['configurations']['hue-desktop-ini']['db_password']).strip()
#metastore_db_password_script = config['configurations']['hue-desktop-ini']['db_password_script']
metastore_db_options = config['configurations']['hue-desktop-ini']['db_options'].strip()

# configurations of security
kinit_path_local = get_kinit_path(default('/configurations/kerberos-env/executable_search_paths', None))
security_enabled = config['configurations']['cluster-env']['security_enabled']
if security_enabled:
  HTTP_principal = config['configurations']['hdfs-site']['dfs.web.authentication.kerberos.principal']
  HTTP_keytab = config['configurations']['hdfs-site']['dfs.web.authentication.kerberos.keytab']
  hue_principal = config['configurations']['hue-desktop-ini']['kerberos_hue_principal'].replace('_HOST',hostname_lowercase)
  hue_keytab = config['configurations']['hue-desktop-ini']['kerberos_hue_keytab']
  kinit_path = kinit_path_local
  zk_principal = config['configurations']['zookeeper-env']['zookeeper_principal_name'].replace('_HOST',hostname_lowercase)
  zk_keytab = config['configurations']['zookeeper-env']['zookeeper_principal_name']


# configurations of HDFS
namenode_hosts = default("/clusterHostInfo/namenode_hosts", [])
namenode_hosts.sort()
namenode_address = None
if 'dfs.namenode.rpc-address' in config['configurations']['hdfs-site']:
  namenode_rpcaddress = config['configurations']['hdfs-site']['dfs.namenode.rpc-address']
  namenode_address = format("hdfs://{namenode_rpcaddress}")
else:
  namenode_address = config['configurations']['core-site']['fs.defaultFS']
# To judge whether the namenode HA mode
logical_name = ''
dfs_ha_enabled = False
dfs_ha_nameservices = default("/configurations/hdfs-site/dfs.nameservices", None)
dfs_ha_namenode_ids = default(format("/configurations/hdfs-site/dfs.ha.namenodes.{dfs_ha_nameservices}"), None)
dfs_ha_namemodes_ids_list = []
if dfs_ha_namenode_ids:
  dfs_ha_namemodes_ids_list = dfs_ha_namenode_ids.split(",")
  dfs_ha_namenode_ids_array_len = len(dfs_ha_namemodes_ids_list)
  if dfs_ha_namenode_ids_array_len > 1:
    dfs_ha_enabled = True
if dfs_ha_enabled:
  namenode_address = format('hdfs://{dfs_ha_nameservices}')
  logical_name = dfs_ha_nameservices
  hdfs_httpfs_host = config['configurations']['hue-desktop-ini']['hdfs_httpfs_host']
  # if kerberos is disabled, using HttpFS . Otherwise using WebHDFS.
  if hdfs_httpfs_host in namenode_hosts :
    webhdfs_url = format('http://' + hdfs_httpfs_host + ':50070/webhdfs/v1')
  else:
    webhdfs_url = format('http://' + namenode_hosts[0] + ':50070/webhdfs/v1')
else:
  dfs_namenode_http_address = config['configurations']['hdfs-site']['dfs.namenode.http-address']
  webhdfs_url = format('http://' + dfs_namenode_http_address + '/webhdfs/v1')

# if setup httpfs then use httpfs
if 'httpfs_gateway_hosts' in config['clusterHostInfo']:
  httpfs_server_host = config['clusterHostInfo']['httpfs_gateway_hosts'][0]  
  httpfs_server_port = config['configurations']['httpfs-env']['port']
  webhdfs_url = format('http://' + httpfs_server_host + ':' + httpfs_server_port  + '/webhdfs/v1')
  print(webhdfs_url)
 

hdfs_user = config['configurations']['hadoop-env']['hdfs_user']
hadoop_bin_dir = stack_select.get_hadoop_dir('bin')
hadoop_conf_dir = conf_select.get_hadoop_conf_dir()
hdfs_site = config['configurations']['hdfs-site']
default_fs = config['configurations']['core-site']['fs.defaultFS']
dfs_type = default("/commandParams/dfs_type", "")
hdfs_user_keytab = config['configurations']['hadoop-env']['hdfs_user_keytab']
hdfs_principal_name = config['configurations']['hadoop-env']['hdfs_principal_name']
kinit_path_local = get_kinit_path(default('/configurations/kerberos-env/executable_search_paths', None))
# create partial functions with common arguments for every HdfsResource call
# to create hdfs directory we need to call params.HdfsResource in code
HdfsResource = functools.partial(
    HdfsResource,
    user=hdfs_user,
    hdfs_resource_ignore_file='/var/lib/ambari-agent/data/.hdfs_resource_ignore',
    security_enabled=security_enabled,
    keytab=hdfs_user_keytab,
    kinit_path_local=kinit_path_local,
    hadoop_bin_dir=hadoop_bin_dir,
    hadoop_conf_dir=hadoop_conf_dir,
    principal_name=hdfs_principal_name,
    hdfs_site=hdfs_site,
    default_fs=default_fs,
    immutable_paths=get_not_managed_resources(),
    dfs_type=dfs_type
)

# configurations of Yarn
resourcemanager_hosts = default("/clusterHostInfo/resourcemanager_hosts", [])
resourcemanager_host = str(resourcemanager_hosts)
resourcemanager_port = config['configurations']['yarn-site']['yarn.resourcemanager.address'].split(':')[-1]
resourcemanager_ha_enabled = False
if len(resourcemanager_hosts) > 1:
  resourcemanager_ha_enabled = True
if resourcemanager_ha_enabled:
  resourcemanager_host1 = config['configurations']['yarn-site']['yarn.resourcemanager.hostname.rm1']
  resourcemanager_host2 = config['configurations']['yarn-site']['yarn.resourcemanager.hostname.rm2']
  resourcemanager_webapp_address1 = config['configurations']['yarn-site']['yarn.resourcemanager.webapp.address.rm1']
  resourcemanager_webapp_address2 = config['configurations']['yarn-site']['yarn.resourcemanager.webapp.address.rm2']
  resourcemanager_api_url1 = format('http://{resourcemanager_webapp_address1}')
  resourcemanager_api_url2 = format('http://{resourcemanager_webapp_address2}')
  proxy_api_url1 = resourcemanager_api_url1
  proxy_api_url2 = resourcemanager_api_url2
else:
  resourcemanager_host1 = resourcemanager_hosts[0]
  resourcemanager_webapp_address1 = config['configurations']['yarn-site']['yarn.resourcemanager.webapp.address']
  resourcemanager_api_url1 = format('http://{resourcemanager_webapp_address1}')
  proxy_api_url1 = resourcemanager_api_url1
histroryserver_host = default("/clusterHostInfo/historyserver_hosts", [])
history_server_api_url = format('http://{histroryserver_host[0]}:19888')
slave_hosts = default("/clusterHostInfo/slave_hosts", [])



# configurations of Hive and Pig
# Hive service is depended on Pig in ambari
hive_server_hosts =  default("/clusterHostInfo/hive_server_hosts", [])
if len(hive_server_hosts) > 0:
  hive_server_host = config['clusterHostInfo']['hive_server_hosts'][0]
  hive_transport_mode = config['configurations']['hive-site']['hive.server2.transport.mode']
  if hive_transport_mode.lower() == "http":
    hive_server_port = config['configurations']['hive-site']['hive.server2.thrift.http.port']
  else:
    hive_server_port = default('/configurations/hive-site/hive.server2.thrift.port',"10000")

hive_metastore_hosts = default('/clusterHostInfo/hive_metastore_hosts', [])
hive_metastore_host = hive_metastore_hosts[0] if len(hive_metastore_hosts) > 0 else None
if hive_metastore_host:
  hive_metastore_port = get_port_from_url(config['configurations']['hive-site']['hive.metastore.uris'])
 

impala_hosts = default('/clusterHostInfo/impala_daemon_hosts', [])
impala_host = impala_hosts[0] if len(impala_hosts) > 0 else None
#impala_port = get_port_from_url(config['configurations']['hive-site']['hive.metastore.uris'])
if impala_host:
  if security_enabled:
    impala_principal = config['configurations']['impala-env']['impala_daemon_kerberos_principal'].replace('_HOST',impala_host.lower())

kyuubi_hosts = default('/clusterHostInfo/kyuubi_server_hosts', [])
kyuubi_host = kyuubi_hosts[0] if len(kyuubi_hosts) > 0 else None
if kyuubi_host:
  if security_enabled:
    kyuubi_principal = config['configurations']['kyuubi-defaults']['kyuubi.kinit.principal'].replace('_HOST',kyuubi_host.lower())

# configurations of Hbase HBASE_THRIFTSERVER
hbase_thriftserver_hosts = default("/clusterHostInfo/hbase_thriftserver_hosts", [])
hbase_clusters = []
hbase_cluster = ''
if len(hbase_thriftserver_hosts) > 0:
  for i in range(len(hbase_thriftserver_hosts)):
    hbase_clusters.append(format("(Cluster" + str(i+1) + "|" + hbase_thriftserver_hosts[i] + ":9090)"))
  hbase_cluster = ",".join(hbase_clusters)
else:
  hbase_cluster='(Cluster|localhost:9090)'
hbase_conf_dir = '/etc/hbase/conf'
#hbase_truncate_limit = config['configurations']['hue-hbase-site']['truncate_limit']
#hbase_thrift_transport = config['configurations']['hue-hbase-site']['thrift_transport']

# configurations of Zookeeper
zookeeper_hosts = default("/clusterHostInfo/zookeeper_hosts", [])
zookeeper_hosts.sort()
zookeeper_client_port = default('/configurations/zoo.cfg/clientPort', None)
zookeeper_host_ports = []
zookeeper_host_port = ''
zookeeper_rest_url = ''
if len(zookeeper_hosts) > 0:
  if zookeeper_client_port is not None:
    for i in range(len(zookeeper_hosts)):
  	  zookeeper_host_ports.append(format(zookeeper_hosts[i] + ":{zookeeper_client_port}"))
  else:
    for i in range(len(zookeeper_hosts)):
  	  zookeeper_host_ports.append(format(zookeeper_hosts[i] + ":2181"))
  zookeeper_host_port = ",".join(zookeeper_host_ports)
  zookeeper_rest_url = format("http://" + zookeeper_hosts[0] + ":9998")


# Ranger hosts
ranger_admin_hosts = default("/clusterHostInfo/ranger_admin_hosts", [])
has_ranger_admin = not len(ranger_admin_hosts) == 0


hue_destop_ini_content = config['configurations']['hue-desktop-ini']['content']
hue_desktop_log_conf_content = config['configurations']['hue-desktop-log-conf']['content']
hue_destop_log4j_properties_content = config['configurations']['hue-desktop-log4j-properties']['content']
