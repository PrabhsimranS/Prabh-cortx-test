# -*- coding: utf-8 -*-
# !/usr/bin/python

"""All Users Object Acl Test Module."""
import os
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import remove_file

from libs.s3 import s3_test_lib, iam_test_lib, s3_acl_test_lib


LOGGER = logging.getLogger(__name__)

s3_test_obj = s3_test_lib.S3TestLib()
acl_obj = s3_acl_test_lib.S3AclTestLib()
no_auth_obj = s3_test_lib.S3LibNoAuth()
iam_test_obj = iam_test_lib.IamTestLib()

all_users_conf = read_yaml("config/s3/test_all_users_object_acl.yaml")


class AllUsers:
    """All Users Object ACL Testsuite."""

    all_user_cfg = all_users_conf["all_users_obj_acl"]

    def put_object_acl(self, acl):
        """helper method to put object acl and verify it."""
        if acl == "grant_read":
            resp = acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                grant_read=self.all_user_cfg["group_uri"])
            assert resp[0], resp[1]
        elif acl == "grant_write":
            resp = acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                grant_write=self.all_user_cfg["group_uri"])
            assert resp[0], resp[1]
        elif acl == "grant_full_control":
            resp = acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                grant_full_control=self.all_user_cfg["group_uri"])
            assert resp[0], resp[1]
        elif acl == "grant_read_acp":
            resp = acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                grant_read_acp=self.all_user_cfg["group_uri"])
            assert resp[0], resp[1]
        elif acl == "grant_write_acp":
            resp = acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                grant_write_acp=self.all_user_cfg["group_uri"])
            assert resp[0], resp[1]

    def verify_obj_acl_edit(self, permission):
        """helper method to verify object's acl is changed."""
        LOGGER.info("Step 2: Verifying that object's acl is changed")
        resp = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert permission == resp[1]["Grants"][0]["Permission"], resp[1]
        LOGGER.info("Step 2: Verified that object's acl is changed")

    def setup_method(self):
        """
        Function will be invoked before running each test case.

        It will perform all prerequisite steps required for test execution.
        It will create a bucket and upload an object to that bucket.
        """
        LOGGER.info("STARTED: Setup operations")
        self.bucket_name = "{0}{1}".format(
            self.all_user_cfg["bucket_name"], str(int(time.time())))
        self.obj_name = "{0}{1}".format(
            self.all_user_cfg["obj_name"], str(int(time.time())))
        LOGGER.info("Creating a bucket and putting an object into bucket")
        resp = s3_test_obj.create_bucket_put_object(
            self.bucket_name,
            self.obj_name,
            self.all_user_cfg["file_path"],
            self.all_user_cfg["mb_count"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Created a bucket and put an object into bucket successfully")
        LOGGER.info("Setting bucket ACL to FULL_CONTROL for all users")
        resp = acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_full_control=self.all_user_cfg["group_uri"])
        assert resp[0], resp[1]
        LOGGER.info("Set bucket ACL to FULL_CONTROL for all users")
        LOGGER.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        LOGGER.info("STARTED: Teardown operations")
        bucket_list = s3_test_obj.bucket_list()[1]
        all_users_buckets = [
            bucket for bucket in bucket_list if all_users_conf["all_users_obj_acl"]["bucket_name"]
            in bucket]
        LOGGER.info("Deleting buckets...")
        for bucket in all_users_buckets:
            acl_obj.put_bucket_acl(
                bucket, grant_full_control=all_users_conf["all_users_obj_acl"]["group_uri"])
        s3_test_obj.delete_multiple_buckets(all_users_buckets)
        LOGGER.info("Deleted buckets")
        if os.path.exists(all_users_conf["all_users_obj_acl"]["file_path"]):
            remove_file(all_users_conf["all_users_obj_acl"]["file_path"])
        LOGGER.info("ENDED: Teardown operations")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-6019", "account_user_management")
    @CTFailOn(error_handler)
    def test_695(self):
        """
        Put an object with same name in bucket without Autentication.

        when AllUsers have READ permission on object
        """
        test_695_cfg = all_users_conf["test_695"]
        LOGGER.info(
            "STARTED: Put an object with same name in bucket without Autentication "
            "when AllUsers have READ permission on object")
        LOGGER.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        LOGGER.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit(test_695_cfg["permission"])
        LOGGER.info(
            "Step 3: Uploading same object into bucket using unsigned account")
        resp = no_auth_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.all_user_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Uploaded same object into bucket successfully")
        LOGGER.info(
            "ENDED: Put an object with same name in bucket without Autentication when "
            "AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-6016", "account_user_management")
    @CTFailOn(error_handler)
    def test_697(self):
        """
        Delete an object from bucket without Authentication.

        when AllUsers have READ permission on object
        """
        test_697_cfg = all_users_conf["test_697"]
        LOGGER.info(
            "STARTED: Delete an object from bucket without Authentication when "
            "AllUsers have READ permission on object")
        LOGGER.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        LOGGER.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit(test_697_cfg["permission"])
        LOGGER.info(
            "Step 3: Deleting an object from bucket using unsigned account")
        resp = no_auth_obj.delete_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Deleted an object from bucket using unsigned account successfully")
        LOGGER.info(
            "ENDED: Delete an object from bucket without Authentication "
            "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-6014", "account_user_management")
    def test_698(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have READ permission on object
        """
        test_698_cfg = all_users_conf["test_698"]
        LOGGER.info(
            "STARTED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ permission on object")
        LOGGER.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        LOGGER.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit(test_698_cfg["permission"])
        LOGGER.info(
            "Step 3: Reading an object ACL from bucket using unsigned account")
        try:
            no_auth_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_698_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Step 3: Reading an object ACL using unsigned account failed with %s",
            test_698_cfg["err_message"])
        LOGGER.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-6011", "account_user_management")
    def test_699(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have READ permission on object
        """
        test_699_cfg = all_users_conf["test_699"]
        LOGGER.info(
            "STARTED: Update an object ACL in bucket without Authentication "
            "when AllUsers have READ permission on object")
        LOGGER.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        LOGGER.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit(test_699_cfg["permission"])
        LOGGER.info(
            "Step 3: Updating an object ACL from bucket using unsigned account")
        try:
            no_auth_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, acl=test_699_cfg["acl"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_699_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Step 3: Updating an object ACL using unsigned account failed with %s",
            test_699_cfg["err_message"])
        LOGGER.info(
            "ENDED: Update an object ACL in bucket without Authentication "
            "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-6009", "account_user_management")
    @CTFailOn(error_handler)
    def test_700(self):
        """
        Put an object with same name in bucket without Autentication.

        when AllUsers have WRITE permission on object
        """
        test_700_cfg = all_users_conf["test_700"]
        LOGGER.info(
            "STARTED: Put an object with same name in bucket without Autentication "
            "when AllUsers have WRITE permission on object")
        LOGGER.info("Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        LOGGER.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit(test_700_cfg["permission"])
        LOGGER.info(
            "Step 3: Putting an object with same name to bucket using unsigned account")
        resp = no_auth_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.all_user_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Put an object with same name to bucket using unsigned account successfully")
        LOGGER.info(
            "ENDED: Put an object with same name in bucket without Autentication "
            "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-6006", "account_user_management")
    @CTFailOn(error_handler)
    def test_701(self):
        """
        Delete an object from bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        test_701_cfg = all_users_conf["test_701"]
        LOGGER.info(
            "STARTED: Delete an object from bucket without Authentication "
            "when AllUsers have WRITE permission on object")
        LOGGER.info("Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        LOGGER.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit(test_701_cfg["permission"])
        LOGGER.info(
            "Step 3: Deleting an object from a bucket using unsigned account")
        resp = no_auth_obj.delete_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Deleted an object from a bucket using unsigned account successfully")
        LOGGER.info(
            "ENDED: Delete an object from bucket without Authentication "
            "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-6004", "account_user_management")
    def test_702(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        test_702_cfg = all_users_conf["test_702"]
        LOGGER.info(
            "STARTED: Read an object ACL from bucket without Authentication "
            "when AllUsers have WRITE permission on object")
        LOGGER.info("Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        LOGGER.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit(test_702_cfg["permission"])
        LOGGER.info(
            "Step 3: Reading an object acl from a bucket using unsigned account")
        try:
            no_auth_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_702_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-6002", "account_user_management")
    def test_703(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        test_703_cfg = all_users_conf["test_703"]
        LOGGER.info(
            "STARTED: Update an object ACL in bucket without Authentication "
            "when AllUsers have WRITE permission on object")
        LOGGER.info("Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        LOGGER.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit(test_703_cfg["permission"])
        LOGGER.info("Step 3: Updating an object ACL using unsigned account")
        try:
            no_auth_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, acl=test_703_cfg["acl"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_703_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "ENDED: Update an object ACL in bucket without Authentication "
            "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-6001", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_704(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        test_704_cfg = all_users_conf["test_704"]
        LOGGER.info(
            "STARTED: Put an object with same name in bucket without Autentication "
            "when AllUsers have READ_ACP permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        LOGGER.info("Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit(test_704_cfg["permission"])
        LOGGER.info(
            "Step 3: Putting an object with same name in bucket using unsigned account")
        resp = no_auth_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.all_user_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Put an object with same name in bucket using unsigned account successfully")
        LOGGER.info(
            "ENDED: Put an object with same name in bucket without Autentication "
            "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5970", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_757(self):
        """
        GET an object from bucket without Autentication.

        when AllUsers have READ permission on object
        """
        test_757_cfg = all_users_conf["test_757"]
        LOGGER.info(
            "STARTED: GET an object from bucket without Autentication "
            "when AllUsers have READ permission on object")
        LOGGER.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        LOGGER.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit(test_757_cfg["permission"])
        LOGGER.info(
            "Step 3: Reading an object which is uploaded to bucket using unsigned account")
        resp = no_auth_obj.get_object(
            self.bucket_name,
            self.obj_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Read an object which is uploaded to bucket successfully")
        LOGGER.info(
            "ENDED: GET an object from bucket without Autentication "
            "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5968", "account_user_management")
    def test_758(self):
        """
        GET an object from bucket without Autentication.

        when AllUsers have WRITE permission on object
        """
        test_758_cfg = all_users_conf["test_758"]
        LOGGER.info(
            "STARTED: GET an object from bucket without Autentication "
            "when AllUsers have WRITE permission on object")
        LOGGER.info("Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        LOGGER.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit(test_758_cfg["permission"])
        LOGGER.info(
            "Step 3: Reading an object from a bucket using unsigned account")
        try:
            no_auth_obj.get_object(
                self.bucket_name,
                self.obj_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_758_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Step 3: Reading object from a bucket using unsigned account failed with %s",
            test_758_cfg["err_message"])
        LOGGER.info(
            "ENDED: GET an object from bucket without Autentication "
            "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5999", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_705(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        test_705_cfg = all_users_conf["test_705"]
        LOGGER.info(
            "Started : GET an object from bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        LOGGER.info("Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit(test_705_cfg["permission"])
        LOGGER.info(
            "Step 3: Reading an object from a bucket using unsigned account")
        try:
            no_auth_obj.get_object(
                self.bucket_name,
                self.obj_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_705_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Step 3: Reading object from a bucket using unsigned account failed with %s",
            test_705_cfg["err_message"])
        LOGGER.info(
            "ENDED: GET an object from bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5997", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_706(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        test_706_cfg = all_users_conf["test_706"]
        LOGGER.info(
            "Started: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        LOGGER.info("Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit(test_706_cfg["permission"])
        LOGGER.info(
            "Step 3: Reading acl of object from a bucket using unsigned account")
        resp = no_auth_obj.get_object_acl(
            self.bucket_name,
            self.obj_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5995", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_707(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        test_707_cfg = all_users_conf["test_707"]
        LOGGER.info(
            "Started: Update an object ACL in bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        LOGGER.info("Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit(test_707_cfg["permission"])
        LOGGER.info("Step 3: Updating an object ACL using unsigned account")
        try:
            no_auth_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, acl=test_707_cfg["acl"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_707_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "ENDED: Update an object ACL in bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5993", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_708(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        test_708_cfg = all_users_conf["test_708"]
        LOGGER.info(
            "Started: Put an object with same name in bucket without Autentication "
            "when AllUsers have WRITE_ACP permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to WRITE_ACP for all users")
        self.put_object_acl("grant_write_acp")
        LOGGER.info(
            "Step 1: Changed object's acl to WRITE_ACP for all users")
        self.verify_obj_acl_edit(test_708_cfg["permission"])
        LOGGER.info(
            "Step 3: Upload same object to bucket using unsigned account")
        resp = no_auth_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.all_user_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED: Put an object with same name in bucket without Autentication "
            "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5986", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_709(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        test_709_cfg = all_users_conf["test_709"]
        LOGGER.info(
            "Started:GET an object from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to WRITE_ACP for all users")
        self.put_object_acl("grant_write_acp")
        LOGGER.info(
            "Step 1: Changed object's acl to WRITE_ACP for all users")
        self.verify_obj_acl_edit(test_709_cfg["permission"])
        LOGGER.info(
            "Step 3: Get object using unsigned account")
        try:
            no_auth_obj.get_object(
                self.bucket_name,
                self.obj_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_709_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "ENDED:GET an object from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5984", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_710(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        test_710_cfg = all_users_conf["test_710"]
        LOGGER.info(
            "Started: Read an object ACL from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_write_acp")
        LOGGER.info("Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit(test_710_cfg["permission"])
        LOGGER.info(
            "Step 3: Reading acl of object from a bucket using unsigned account")
        try:
            no_auth_obj.get_object_acl(
                self.bucket_name,
                self.obj_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_710_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5982", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_711(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        test_711_cfg = all_users_conf["test_711"]
        LOGGER.info(
            "Started:Update an object ACL in bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to WRITE_ACP for all users")
        self.put_object_acl("grant_write_acp")
        LOGGER.info(
            "Step 1: Changed object's acl to WRITE_ACP for all users")
        self.verify_obj_acl_edit(test_711_cfg["permission"])
        LOGGER.info(
            "Step 3: Update ACL of object using unsigned account")
        self.put_object_acl("grant_full_control")
        LOGGER.info(
            "ENDED:Update an object ACL in bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5979", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_712(self):
        """
        Put an object with same name in bucket without Autentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        test_712_cfg = all_users_conf["test_712"]
        LOGGER.info(
            "Started:Put an object with same name in bucket without Autentication "
            "when AllUsers have FULL_CONTROL permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        LOGGER.info(
            "Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit(test_712_cfg["permission"])
        LOGGER.info(
            "Step 3: upload same object in that bucket using unsigned account")
        resp = no_auth_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.all_user_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED:Put an object with same name in bucket without Autentication "
            "when AllUsers have FULL_CONTROL permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5977", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_713(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        test_713_cfg = all_users_conf["test_713"]
        LOGGER.info(
            "Started:GET an object from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        LOGGER.info(
            "Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit(test_713_cfg["permission"])
        LOGGER.info(
            "Step 3: Get object from that bucket using unsigned account")
        resp = no_auth_obj.get_object(
            self.bucket_name,
            self.obj_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED:GET an object from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5975", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_714(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        test_714_cfg = all_users_conf["test_714"]
        LOGGER.info(
            "Started:Read an object ACL from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        LOGGER.info(
            "Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit(test_714_cfg["permission"])
        LOGGER.info(
            "Step 3: Get object acl from that bucket using unsigned account")
        resp = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert test_714_cfg["permission"] == resp[1]["Grants"][0]["Permission"], resp[1]
        LOGGER.info(
            "ENDED:Read an object ACL from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5973", "all_users_object_acl")
    @CTFailOn(error_handler)
    def test_715(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        test_715_cfg = all_users_conf["test_715"]
        LOGGER.info(
            "Started:Update an object ACL in bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")
        LOGGER.info(
            "Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        LOGGER.info(
            "Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit(test_715_cfg["permission"])
        LOGGER.info(
            "Step 3: Update object acl from that bucket using unsigned account")
        self.put_object_acl("grant_write_acp")
        LOGGER.info(
            "Step 3: Changed object's acl to FULL_CONTROL for all users")
        LOGGER.info("Step 4: Verifying that object's acl is changed")
        resp = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert test_715_cfg["new_permission"] == resp[1]["Grants"][0]["Permission"], resp[1]
        LOGGER.info("Step 4: Verified that object's acl is changed")
        LOGGER.info(
            "ENDED:Update an object ACL in bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")
