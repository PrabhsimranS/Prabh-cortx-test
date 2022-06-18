#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""All IAM users test  Module."""
import asyncio
import time
import logging
from http import HTTPStatus
import pytest

from libs.s3.s3_iam_rest_rgw import RestApiRgw
from commons import cortxlogging

class TestRestApiRgw:
    """
    REST API Test cases for IAM users.
    IAM CRUD operations.
    """
    @classmethod
    def setup_class(cls):
        """Function will be invoked before running each test case."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup class ")
        cls.obj = RestApiRgw()
        cls.user_name_prefix = "user"
        cls.email_id = "{}@seagate.com"
        cls.created_users = []

    def teardown_method(self):
        """
        Teardown for deleting resources like users,object and bucket created as part of testcases
        """
        self.log.info("[STARTED] ######### Teardown #########")
        self.log.info("Deleting all users created as part of test")
        delete_failed = []
        delete_success = []
        self.log.debug("created_users list : %s",self.created_users)
        for usr in self.created_users:
            self.log.info("Sending request to delete user %s", usr)
            try:
                loop = asyncio.get_event_loop()
                status = loop.run_until_complete(self.obj.delete_user(usr))
                if status[0] != HTTPStatus.OK:
                    delete_failed.append(usr)
                else:
                    delete_success.append(usr)
            # pylint: disable=broad-except
            except BaseException as err:
                self.log.warning("Ignoring %s while deleting user: %s", err, usr)
        for usr in delete_success:
            self.created_users.remove(usr)
        self.log.info("User delete success list %s", delete_success)
        self.log.info("User delete failed list %s", delete_failed)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36622')
    def test_user_create_36622(self):
        """Test create iam user specifying uid and display name."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create iam user specifying uid and display name.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'display-name': user_name,
            'uid' : user_name
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36630')
    def test_user_create_36630(self):
        """Test create iam user specifying uid and display name and email."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create iam user specifying uid and display name and email.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        email=f"{user_name}@seagate.com"
        user_params = {
            'display-name': user_name,
            'email' : email,
            'uid' : user_name
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info("END: %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36632')
    def test_user_create_36632(self):
        """Test create iam user specifying just uid."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create iam user specifying just uid .")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'uid' : user_name
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.BAD_REQUEST, "Able to create user with just uid. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        #self.created_users.append(user_params)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36633')
    def test_user_create_36633(self):
        """Test create using uid which already exist."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create using uid which already exist.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'display-name': user_name,
            'uid' : user_name
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Creating another IAM user with same name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.CONFLICT , "Didn't get the expected error"
        self.log.info("Create user output: %s",user_info)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36636')
    def test_user_create_36636(self):
        """Test create user using display name which already exist."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create user using display name which already exist.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_name2 = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'display-name': user_name,
            'uid' : user_name
         }
        user_params2 = {
            'display-name': user_name,
            'uid' : user_name2
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Creating another IAM user with same display name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params2))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 4: Verifying that new IAM user is created successfully with same display name")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params2))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params2)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36664')
    def test_user_create_36664(self):
        """Test create using email which already exist."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create using email which already exist.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_name2 = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        email=f"{user_name}@seagate.com"
        user_params = {
            'display-name': user_name,
            'email' : email,
            'uid' : user_name
        }
        user_params2 = {
            'display-name': user_name2,
            'email' : email,
            'uid' : user_name2
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Creating another IAM user with same email %s", str(email))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params2))
        assert status == HTTPStatus.CONFLICT , "Didn't get the expected error"
        self.log.info("Create user output: %s",user_info)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36665')
    def test_user_create_36665(self):
        """Test create user with uid containing special characters."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create user with uid containing special characters.")
        user_name = '#user##@%@%%@#%^@#%12313223new'
        user_params = {
            'display-name': user_name,
            'uid' : user_name
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36666')
    def test_user_create_36666(self):
        """Test create iam user specifying max_buckets."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create iam user specifying max_buckets.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        max_buckets = 5
        user_params = {
            'display-name': user_name,
            'uid' : user_name,
            'max-buckets':max_buckets
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Try creating buckets more than the specified max_buckets.")

        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36667')
    def test_user_create_36667(self):
        """Test create iam user specifying negative value for max_buckets."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create iam user specifying negative value for max_buckets.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        max_buckets = -5
        user_params = {
            'display-name': user_name,
            'uid' : user_name,
            'max-buckets':max_buckets
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Try creating buckets more than the specified max_buckets.")
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-37155')
    def test_user_create_37155(self):
        """Test create iam user specifying tenant."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create iam user specifying tenant.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        tenant = "tnt1"
        user_params = {
            'display-name': user_name,
            'uid' : user_name,
            'tenant' : tenant
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-37156')
    def test_user_create_37156(self):
        """Test create iam user with same userid but different tenant values."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create iam user with same userid but different tenant values.")
        user_name = f"{self.user_name_prefix}1"
        tenant = "tnt1"
        tenant2 = "tnt2"
        user_params = {
            'display-name': user_name,
            'uid' : user_name,
            'tenant' : tenant
        }
        user_params2 = {
            'display-name': user_name,
            'uid' : user_name,
            'tenant' : tenant2
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Creating another IAM user with same name %s but different tenant ", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params2))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 4: Verifying another new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params2))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-37157')
    def test_user_create_37157(self):
        """Test create iam user specifying tenant in the uid using $."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START : Test create iam user specifying tenant in the uid using $.")
        display_name = "test user"
        user_name = "tenant11$newtestuser"
        user_params = {
            'display-name': display_name,
            'uid' : user_name
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-37158')
    def test_user_create_37158(self):
        """Test duplicate user specifying tenant in the uid using $ and other using tenant parameter ."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test duplicate user specifying tenant in the uid using $ and"
                      " other using tenant parameter .")
        user_name = f"{self.user_name_prefix}1"
        tenant = "tnt1"
        user_name_with_tenant = tenant + '$' + user_name
        user_params = {
            'display-name': user_name,
            'uid' : user_name,
            'tenant' : tenant
        }
        user_params2 = {
            'display-name': user_name,
            'uid' : user_name_with_tenant
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Creating another IAM user with same name containing tenant name as %s", str(user_name_with_tenant))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params2))
        assert status == HTTPStatus.CONFLICT , "Haven't got the expected failure. Test Failed"
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-37159')
    def test_user_create_37159(self):
        """Test create user with user defined access key."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create user with user defined access key.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        access_key = "ABCDEFGH"
        user_params = {
            'display-name': user_name,
            'uid' : user_name,
            'access-key' : access_key
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s and "
            "user defined access key %s", str(user_name),str(access_key))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Using user defined access key and secret key run IOs")
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-37160')
    def test_user_create_37160(self):
        """Test create user with user defined access key which is already in use."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create user with user defined access key which is already in use.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_name2 = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        access_key = "ABCDEFGH"
        user_params = {
            'display-name': user_name,
            'uid' : user_name,
            'access-key' : access_key
        }
        user_params2 = {
            'display-name': user_name,
            'uid' : user_name2,
            'access-key' : access_key
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s and "
            "user defined access key %s", str(user_name),str(access_key))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Creating a new IAM user with same"
            "user defined access key %s",str(access_key))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params2))
        assert status == HTTPStatus.CONFLICT, "Didnt get the required error status. Test Failed"
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-37299')
    def test_user_create_37299(self):
        """Test create user with user defined access key value with special characters."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create user with user defined access key value with special characters .")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        access_key = 'ABC#&@$%i?*DEFGH'
        user_params = {
            'display-name': user_name,
            'uid' : user_name,
            'access-key' : access_key
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name :%s and "
            "user defined access key with special character :%s", str(user_name),str(access_key))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Using user defined access key and secret key run IOs")
        self.log.info("END : %s",test_case_name)