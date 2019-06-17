# -*- coding: UTF-8 -*-
"""
A suite of tests for the functions in vmware.py
"""
import unittest
from unittest.mock import patch, MagicMock

from vlab_esxi_api.lib.worker import vmware


class TestVMware(unittest.TestCase):
    """A set of test cases for the vmware.py module"""

    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_show_esxi(self, fake_vCenter, fake_consume_task, fake_get_info):
        """``esxi`` returns a dictionary when everything works as expected"""
        fake_vm = MagicMock()
        fake_vm.name = 'ESXi'
        fake_folder = MagicMock()
        fake_folder.childEntity = [fake_vm]
        fake_vCenter.return_value.__enter__.return_value.get_by_name.return_value = fake_folder
        fake_get_info.return_value = {'meta': {'component': 'ESXi',
                                               'created': 1234,
                                               'version': '6.5',
                                               'configured': False,
                                               'generation': 1}}

        output = vmware.show_esxi(username='alice')
        expected = {'ESXi': {'meta': {'component': 'ESXi',
                                      'created': 1234,
                                      'version': '6.5',
                                      'configured': False,
                                      'generation': 1}}}

        self.assertEqual(output, expected)

    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware.virtual_machine, 'power')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_delete_esxi(self, fake_vCenter, fake_consume_task, fake_power, fake_get_info):
        """``delete_esxi`` returns None when everything works as expected"""
        fake_logger = MagicMock()
        fake_vm = MagicMock()
        fake_vm.name = 'ESXiBox'
        fake_folder = MagicMock()
        fake_folder.childEntity = [fake_vm]
        fake_vCenter.return_value.__enter__.return_value.get_by_name.return_value = fake_folder
        fake_get_info.return_value = {'meta': {'component': 'ESXi',
                                               'created': 1234,
                                               'version': '6.5',
                                               'configured': False,
                                               'generation': 1}}

        output = vmware.delete_esxi(username='bob', machine_name='ESXiBox', logger=fake_logger)
        expected = None

        self.assertEqual(output, expected)

    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware.virtual_machine, 'power')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_delete_esxi_value_error(self, fake_vCenter, fake_consume_task, fake_power, fake_get_info):
        """``delete_esxi`` raises ValueError when unable to find requested vm for deletion"""
        fake_logger = MagicMock()
        fake_vm = MagicMock()
        fake_vm.name = 'win10'
        fake_folder = MagicMock()
        fake_folder.childEntity = [fake_vm]
        fake_vCenter.return_value.__enter__.return_value.get_by_name.return_value = fake_folder
        fake_get_info.return_value = {'meta': {'component': 'ESXi',
                                               'created': 1234,
                                               'version': '6.5',
                                               'configured': False,
                                               'generation': 1}}

        with self.assertRaises(ValueError):
            vmware.delete_esxi(username='bob', machine_name='myOtherESXiBox', logger=fake_logger)

    @patch.object(vmware.virtual_machine, 'set_meta')
    @patch.object(vmware, 'Ova')
    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware.virtual_machine, 'deploy_from_ova')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_create_esxi(self, fake_vCenter, fake_consume_task, fake_deploy_from_ova, fake_get_info, fake_Ova, fake_set_meta):
        """``create_esxi`` returns a dictionary upon success"""
        fake_logger = MagicMock()
        fake_deploy_from_ova.return_value.name = 'myESXi'
        fake_get_info.return_value = {'worked': True}
        fake_Ova.return_value.networks = ['someLAN']
        fake_vCenter.return_value.__enter__.return_value.networks = {'someLAN' : vmware.vim.Network(moId='1')}

        output = vmware.create_esxi(username='alice',
                                       machine_name='ESXiBox',
                                       image='1.0.0',
                                       network='someLAN',
                                       logger=fake_logger)
        expected =  {'myESXi' : {'worked': True}}

        self.assertEqual(output, expected)

    @patch.object(vmware, 'Ova')
    @patch.object(vmware.virtual_machine, 'get_info')
    @patch.object(vmware.virtual_machine, 'deploy_from_ova')
    @patch.object(vmware, 'consume_task')
    @patch.object(vmware, 'vCenter')
    def test_create_esxi_invalid_network(self, fake_vCenter, fake_consume_task, fake_deploy_from_ova, fake_get_info, fake_Ova):
        """``create_esxi`` raises ValueError if supplied with a non-existing network"""
        fake_logger = MagicMock()
        fake_get_info.return_value = {'worked': True}
        fake_Ova.return_value.networks = ['someLAN']
        fake_vCenter.return_value.__enter__.return_value.networks = {'someLAN' : vmware.vim.Network(moId='1')}

        with self.assertRaises(ValueError):
            vmware.create_esxi(username='alice',
                                  machine_name='ESXiBox',
                                  image='1.0.0',
                                  network='someOtherLAN',
                                  logger=fake_logger)

    @patch.object(vmware.os, 'listdir')
    def test_list_images(self, fake_listdir):
        """``list_images`` - Returns a list of available ESXi versions that can be deployed"""
        fake_listdir.return_value = ['esxi-6.5u2.ova', 'esxi-6.5u1.ova', 'esxi-6.5.ova']

        output = vmware.list_images()
        expected = ['6.5', '6.5u1', '6.5u2']

        # set() avoids ordering issue in test
        self.assertEqual(set(output), set(expected))

    def test_convert_name(self):
        """``convert_name`` - defaults to converting to the OVA file name"""
        output = vmware.convert_name(name='6.5u2')
        expected = 'esxi-6.5u2.ova'

        self.assertEqual(output, expected)

    def test_convert_name_to_version(self):
        """``convert_name`` - can take a OVA file name, and extract the version from it"""
        output = vmware.convert_name('esxi-6.5u2.ova', to_version=True)
        expected = '6.5u2'

        self.assertEqual(output, expected)

    @patch.object(vmware, 'consume_task')
    def test_config_vm(self, fake_consume_task):
        """``config_vm`` Enables hardware-assisted virtualization"""
        fake_vm = MagicMock()
        vmware.config_vm(fake_vm)

        the_args, _ = fake_vm.ReconfigVM_Task.call_args
        the_spec = the_args[0]

        self.assertTrue(the_spec.nestedHVEnabled)


if __name__ == '__main__':
    unittest.main()
