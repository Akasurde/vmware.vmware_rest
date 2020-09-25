#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = """
module: vcenter_folder_info
short_description: Collect the information associated with the vCenter folders
description: Collect the information associated with the vCenter folders
options:
  filter_datacenters:
    description:
    - Datacenters that must contain the folder for the folder to match the filter.
    - If unset or empty, folder in any datacenter match the filter.
    - 'When clients pass a value of this structure as a parameter, the field must
      contain the id of resources returned by M(vcenter_datacenter_info). '
    elements: str
    type: list
  filter_folders:
    description:
    - Identifiers of folders that can match the filter.
    - If unset or empty, folders with any identifier match the filter.
    - 'When clients pass a value of this structure as a parameter, the field must
      contain the id of resources returned by M(vcenter_folder_info). '
    elements: str
    type: list
  filter_names:
    description:
    - Names that folders must have to match the filter (see I(name)).
    - If unset or empty, folders with any name match the filter.
    elements: str
    type: list
  filter_parent_folders:
    description:
    - Folders that must contain the folder for the folder to match the filter.
    - If unset or empty, folder in any folder match the filter.
    - 'When clients pass a value of this structure as a parameter, the field must
      contain the id of resources returned by M(vcenter_folder_info). '
    elements: str
    type: list
  filter_type:
    choices:
    - DATACENTER
    - DATASTORE
    - HOST
    - NETWORK
    - VIRTUAL_MACHINE
    description:
    - The I(type) enumerated type defines the type of a vCenter Server folder. The
      type of a folder determines what what kinds of children can be contained in
      the folder.
    type: str
  vcenter_hostname:
    description:
    - The hostname or IP address of the vSphere vCenter
    - If the value is not specified in the task, the value of environment variable
      C(VMWARE_HOST) will be used instead.
    required: true
    type: str
  vcenter_password:
    description:
    - The vSphere vCenter username
    - If the value is not specified in the task, the value of environment variable
      C(VMWARE_PASSWORD) will be used instead.
    required: true
    type: str
  vcenter_username:
    description:
    - The vSphere vCenter username
    - If the value is not specified in the task, the value of environment variable
      C(VMWARE_USER) will be used instead.
    required: true
    type: str
  vcenter_validate_certs:
    default: true
    description:
    - Allows connection when SSL certificates are not valid. Set to C(false) when
      certificates are not trusted.
    - If the value is not specified in the task, the value of environment variable
      C(VMWARE_VALIDATE_CERTS) will be used instead.
    type: bool
author:
- Goneri Le Bouder (@goneri) <goneri@lebouder.net>
version_added: 1.0.0
requirements:
- python >= 3.6
- aiohttp
"""

EXAMPLES = """
- name: Build a list of all the folders
  vcenter_folder_info:
  register: my_folders
- name: Build a list of all the folders
  vcenter_folder_info:
  register: my_folders
- name: Build a list of the folders, with a filter
  vcenter_folder_info:
    filter_type: DATASTORE
"""

RETURN = """
"""

# This structure describes the format of the data expected by the end-points
PAYLOAD_FORMAT = {
    "list": {
        "query": {
            "filter.datacenters": "filter.datacenters",
            "filter.folders": "filter.folders",
            "filter.names": "filter.names",
            "filter.parent_folders": "filter.parent_folders",
            "filter.type": "filter.type",
        },
        "body": {},
        "path": {},
    }
}

import socket
import json
from ansible.module_utils.basic import env_fallback

try:
    from ansible_collections.cloud.common.plugins.module_utils.turbo.module import (
        AnsibleTurboModule as AnsibleModule,
    )
except ImportError:
    from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware_rest.plugins.module_utils.vmware_rest import (
    build_full_device_list,
    exists,
    gen_args,
    get_device_info,
    get_subdevice_type,
    list_devices,
    open_session,
    prepare_payload,
    update_changed_flag,
)


def prepare_argument_spec():
    argument_spec = {
        "vcenter_hostname": dict(
            type="str", required=True, fallback=(env_fallback, ["VMWARE_HOST"]),
        ),
        "vcenter_username": dict(
            type="str", required=True, fallback=(env_fallback, ["VMWARE_USER"]),
        ),
        "vcenter_password": dict(
            type="str",
            required=True,
            no_log=True,
            fallback=(env_fallback, ["VMWARE_PASSWORD"]),
        ),
        "vcenter_validate_certs": dict(
            type="bool",
            required=False,
            default=True,
            fallback=(env_fallback, ["VMWARE_VALIDATE_CERTS"]),
        ),
    }

    argument_spec["filter_datacenters"] = {"type": "list", "elements": "str"}
    argument_spec["filter_folders"] = {"type": "list", "elements": "str"}
    argument_spec["filter_names"] = {"type": "list", "elements": "str"}
    argument_spec["filter_parent_folders"] = {"type": "list", "elements": "str"}
    argument_spec["filter_type"] = {
        "type": "str",
        "choices": ["DATACENTER", "DATASTORE", "HOST", "NETWORK", "VIRTUAL_MACHINE"],
    }

    return argument_spec


async def main():
    module_args = prepare_argument_spec()
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    session = await open_session(
        vcenter_hostname=module.params["vcenter_hostname"],
        vcenter_username=module.params["vcenter_username"],
        vcenter_password=module.params["vcenter_password"],
    )
    result = await entry_point(module, session)
    module.exit_json(**result)


def build_url(params):

    _in_query_parameters = PAYLOAD_FORMAT["list"]["query"].keys()
    return ("https://{vcenter_hostname}" "/rest/vcenter/folder").format(
        **params
    ) + gen_args(params, _in_query_parameters)


async def entry_point(module, session):
    url = build_url(module.params)
    async with session.get(url) as resp:
        _json = await resp.json()
        if module.params.get("None"):
            _json["id"] = module.params.get("None")
        elif module.params.get("label"):  # TODO extend the list of filter
            _json = await exists(module.params, session, url)
        else:  # list context, retrieve the details of each entry
            try:
                if (
                    isinstance(_json["value"][0]["None"], str)
                    and len(list(_json["value"][0].values())) == 1
                ):
                    # this is a list of id, we fetch the details
                    full_device_list = await build_full_device_list(session, url, _json)
                    _json = {"value": [i["value"] for i in full_device_list]}
            except (TypeError, KeyError, IndexError):
                pass

        return await update_changed_flag(_json, resp.status, "get")


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
