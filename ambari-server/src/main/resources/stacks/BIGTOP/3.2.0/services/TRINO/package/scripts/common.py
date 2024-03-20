# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from resource_management.core.resources.system import Execute
import re
script_dir = os.path.dirname(os.path.realpath(__file__))
# def create_connectors(node_properties, connectors_to_add):
#     if not connectors_to_add:
#         return
#     Execute('mkdir -p {0}'.format(node_properties['plugin.config-dir']))
#     connectors_dict = ast.literal_eval(connectors_to_add)
#     for connector in connectors_dict:
#         connector_file = os.path.join(node_properties['plugin.config-dir'], connector + '.properties')
#         with open(connector_file, 'w') as f:
#             for lineitem in connectors_dict[connector]:
#                 f.write('{0}\n'.format(lineitem))
#
# def delete_connectors(node_properties, connectors_to_delete):
#     if not connectors_to_delete:
#         return
#     connectors_list = ast.literal_eval(connectors_to_delete)
#     for connector in connectors_list:
#         connector_file_name = os.path.join(node_properties['plugin.config-dir'], connector + '.properties')
#         Execute('rm -f {0}'.format(connector_file_name))



# Function to update or insert JAVA_HOME and PATH exports
def update_java_exports(file_path, java_home):

    # Constants for the export statements
    java_home_export = f"export JAVA_HOME={java_home}\n"
    path_export = "export PATH=$JAVA_HOME/bin:$PATH\n"

    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Find the index of the target exec line
    exec_index = next((i for i, line in enumerate(lines) if 'exec "$(dirname "$0")/launcher.py" "$@' in line), None)

    if exec_index is not None:
        # Check if the export lines already exist
        java_home_exists = any("export JAVA_HOME" in line for line in lines[:exec_index])
        path_exists = any("export PATH" in line for line in lines[:exec_index])

        # Update or insert JAVA_HOME and PATH exports
        if not java_home_exists:
            lines.insert(exec_index, java_home_export)
            exec_index += 1  # Adjust index due to insertion
        else:
            # Update the existing JAVA_HOME export
            lines = [java_home_export if "export JAVA_HOME" in line else line for line in lines]

        if not path_exists:
            lines.insert(exec_index, path_export)
        else:
            # Update the existing PATH export
            lines = [path_export if "export PATH" in line else line for line in lines]

        # Write the updated lines back to the file
        with open(file_path, 'w') as file:
            file.writelines(lines)

# Replace 'your_file_path' with the actual file path