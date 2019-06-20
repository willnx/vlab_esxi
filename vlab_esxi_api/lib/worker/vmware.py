# -*- coding: UTF-8 -*-
"""Business logic for backend worker tasks"""
import time
import random
import os.path
from vlab_inf_common.vmware import vCenter, Ova, vim, virtual_machine, consume_task

from vlab_esxi_api.lib import const


def show_esxi(username):
    """Obtain basic information about ESXi

    :Returns: Dictionary

    :param username: The user requesting info about their ESXi
    :type username: String
    """
    info = {}
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER, \
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        folder = vcenter.get_by_name(name=username, vimtype=vim.Folder)
        esxi_vms = {}
        for vm in folder.childEntity:
            info = virtual_machine.get_info(vcenter, vm)
            if info['meta']['component'] == 'ESXi':
                esxi_vms[vm.name] = info
    return esxi_vms


def delete_esxi(username, machine_name, logger):
    """Unregister and destroy a user's ESXi

    :Returns: None

    :param username: The user who wants to delete their jumpbox
    :type username: String

    :param machine_name: The name of the VM to delete
    :type machine_name: String

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER, \
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        folder = vcenter.get_by_name(name=username, vimtype=vim.Folder)
        for entity in folder.childEntity:
            if entity.name == machine_name:
                info = virtual_machine.get_info(vcenter, entity)
                if info['meta']['component'] == 'ESXi':
                    logger.debug('powering off VM')
                    virtual_machine.power(entity, state='off')
                    delete_task = entity.Destroy_Task()
                    logger.debug('blocking while VM is being destroyed')
                    consume_task(delete_task)
                    break
        else:
            raise ValueError('No {} named {} found'.format('esxi', machine_name))


def create_esxi(username, machine_name, image, network, logger):
    """Deploy a new instance of ESXi

    :Returns: Dictionary

    :param username: The name of the user who wants to create a new ESXi
    :type username: String

    :param machine_name: The name of the new instance of ESXi
    :type machine_name: String

    :param image: The image/version of ESXi to create
    :type image: String

    :param network: The name of the network to connect the new ESXi instance up to
    :type network: String

    :param logger: An object for logging messages
    :type logger: logging.LoggerAdapter
    """
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER,
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        image_name = convert_name(image)
        logger.info(image_name)
        ova = Ova(os.path.join(const.VLAB_ESXI_IMAGES_DIR, image_name))
        try:
            network_map = vim.OvfManager.NetworkMapping()
            network_map.name = ova.networks[0]
            try:
                network_map.network = vcenter.networks[network]
            except KeyError:
                raise ValueError('No such network named {}'.format(network))
            the_vm = virtual_machine.deploy_from_ova(vcenter=vcenter,
                                                     ova=ova,
                                                     network_map=[network_map],
                                                     username=username,
                                                     machine_name=machine_name,
                                                     logger=logger,
                                                     power_on=False)
        finally:
            ova.close()
        config_vm(the_vm)
        virtual_machine.power(the_vm, state='on')
        meta_data = {'component' : "ESXi",
                     'created': time.time(),
                     'version': image,
                     'configured': False,
                     'generation': 1,
                    }
        virtual_machine.set_meta(the_vm, meta_data)
        info = virtual_machine.get_info(vcenter, the_vm, ensure_ip=True)
        return {the_vm.name: info}


def list_images():
    """Obtain a list of available versions of ESXi that can be created

    :Returns: List
    """
    images = os.listdir(const.VLAB_ESXI_IMAGES_DIR)
    images = [convert_name(x, to_version=True) for x in images]
    return images


def convert_name(name, to_version=False):
    """This function centralizes converting between the name of the OVA, and the
    version of software it contains.

    The naming convention of the ESXi OVAs is ``esxi-<version>.ova``; i.e. esxi-6.7u1.ova

    :param name: The thing to covert
    :type name: String

    :param to_version: Set to True to covert the name of an OVA to the version
    :type to_version: Boolean
    """
    if to_version:
        return name.split('-')[-1].replace('.ova', '')
    else:
        return 'esxi-{}.ova'.format(name)


def config_vm(the_vm):
    """Enable hardware-assisted virtualization so 64-bit OSes can run on the
    virtual ESXi host.

    :Returns: None

    :param the_vm: The new ESXi virtual machine object
    :type the_vm: vim.VirtualMachine
    """
    spec = vim.vm.ConfigSpec()
    spec.nestedHVEnabled = True
    task = the_vm.ReconfigVM_Task(spec)
    consume_task(task)


def update_network(username, machine_name, new_network):
    """Implements the VM network update

    :param username: The name of the user who owns the virtual machine
    :type username: String

    :param machine_name: The name of the virtual machine
    :type machine_name: String

    :param new_network: The name of the new network to connect the VM to
    :type new_network: String
    """
    with vCenter(host=const.INF_VCENTER_SERVER, user=const.INF_VCENTER_USER, \
                 password=const.INF_VCENTER_PASSWORD) as vcenter:
        folder = vcenter.get_by_name(name=username, vimtype=vim.Folder)
        for entity in folder.childEntity:
            if entity.name == machine_name:
                info = virtual_machine.get_info(vcenter, entity)
                if info['meta']['component'] == 'ESXi':
                    the_vm = entity
                    break
        else:
            error = 'No VM named {} found'.format(machine_name)
            raise ValueError(error)

        try:
            network = vcenter.networks[new_network]
        except KeyError:
            error = 'No VM named {} found'.format(machine_name)
            raise ValueError(error)
        else:
            virtual_machine.change_network(the_vm, network)
