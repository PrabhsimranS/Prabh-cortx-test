#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""
HA common utility methods
"""
import logging
import os
import time
import sys
from multiprocessing import Process
import sys

from commons import commands as common_cmd
from commons import constants as common_const
from commons import pswdmanager
from commons.constants import Rest as Const
from commons.exceptions import CTException
from commons.utils import system_utils
from config import CMN_CFG, HA_CFG
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.di.di_mgmt_ops import ManagementOPs
from libs.di.di_run_man import RunDataCheckManager
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench

LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
class HAK8s:
    """
    This class contains common utility methods for HA related operations.
    """

    def __init__(self):
        self.system_health = SystemHealth()
        self.setup_type = CMN_CFG["setup_type"]
        self.vm_username = os.getenv(
            "QA_VM_POOL_ID", pswdmanager.decrypt(
                HA_CFG["vm_params"]["uname"]))
        self.vm_password = os.getenv(
            "QA_VM_POOL_PASSWORD", pswdmanager.decrypt(
                HA_CFG["vm_params"]["passwd"]))
        self.bmc_user = CMN_CFG["bmc"]["username"]
        self.bmc_pwd = CMN_CFG["bmc"]["password"]
        self.t_power_on = HA_CFG["common_params"]["power_on_time"]
        self.t_power_off = HA_CFG["common_params"]["power_off_time"]
        self.mgnt_ops = ManagementOPs()
        self.num_nodes = len(CMN_CFG["nodes"])
        self.num_pods = ""
        self.s3_rest_obj = S3AccountOperationsRestAPI()
        self.parallel_ios = None
        self.dir_path = common_const.K8s_SCRIPTS_PATH

    def polling_host(self,
                     max_timeout: int,
                     host: str,
                     exp_resp: bool,
                     bmc_obj=None):
        """
        Helper function to poll for host ping response.
        :param max_timeout: Max timeout allowed for expected response from ping
        :param host: Host to ping
        :param exp_resp: Expected resp True/False for host state Reachable/Unreachable
        :param bmc_obj: BMC object
        :return: bool
        """
        poll = time.time() + max_timeout  # max timeout
        while poll > time.time():
            time.sleep(20)
            resp = system_utils.check_ping(host)
            if self.setup_type == "VM":
                vm_name = host.split(".")[0]
                vm_info = system_utils.execute_cmd(
                    common_cmd.CMD_VM_INFO.format(
                        self.vm_username, self.vm_password, vm_name))
                if not vm_info[0]:
                    LOGGER.info(f"Unable to get VM power status for {vm_name}")
                    return False
                data = vm_info[1].split("\\n")
                pw_state = ""
                for lines in data:
                    if 'power_state' in lines:
                        pw_state = (lines.split(':')[1].strip('," '))
                LOGGER.debug("Power state for %s : %s", host, pw_state)
                if exp_resp:
                    exp_state = pw_state == 'up'
                else:
                    exp_state = pw_state == 'down'
            else:
                out = bmc_obj.bmc_node_power_status(self.bmc_user, self.bmc_pwd)
                if exp_resp:
                    exp_state = "on" in out
                else:
                    exp_state = "off" in out

            if resp == exp_resp and exp_state:
                return True
        return False

    def host_power_on(self, host: str, bmc_obj=None):
        """
        Helper function for host power on
        :param host: Host to be power on
        :param bmc_obj: BMC object
        :rtype: boolean from polling_host() response
        """

        if self.setup_type == "VM":
            vm_name = host.split(".")[0]
            resp = system_utils.execute_cmd(
                common_cmd.CMD_VM_POWER_ON.format(
                    self.vm_username, self.vm_password, vm_name))
            if not resp[0]:
                LOGGER.info("Response for failed VM power on command: %s", resp)
                return False
        else:
            bmc_obj.bmc_node_power_on_off(self.bmc_user, self.bmc_pwd, "on")

        LOGGER.info("Check if %s is powered on.", host)
        # SSC cloud is taking time to on VM host hence timeout
        resp = self.polling_host(max_timeout=self.t_power_on, host=host,
                                 exp_resp=True, bmc_obj=bmc_obj)
        return resp

    def host_safe_unsafe_power_off(self, host: str, bmc_obj=None,
                                   pod_obj=None, is_safe: bool = False):
        """
        Helper function for safe/unsafe host power off
        :param host: Host to be power off
        :param bmc_obj: BMC object
        :param pod_obj: Pod object
        :param is_safe: Power off host with safe/unsafe shutdown
        :rtype: boolean from polling_host() response
        """
        if is_safe:
            resp = pod_obj.execute_cmd(cmd="shutdown -P now", exc=False)
            LOGGER.debug("Response for shutdown: {}".format(resp))
        else:
            if self.setup_type == "VM":
                vm_name = host.split(".")[0]
                resp = system_utils.execute_cmd(
                    common_cmd.CMD_VM_POWER_OFF.format(
                        self.vm_username, self.vm_password, vm_name))
                if not resp[0]:
                    LOGGER.info("Response for failed VM power off command: %s", resp)
                    return False
            else:
                bmc_obj.bmc_node_power_on_off(self.bmc_user, self.bmc_pwd, "off")

        LOGGER.info("Check if %s is powered off.", host)
        # SSC cloud is taking time to off VM host hence timeout
        resp = self.polling_host(
            max_timeout=self.t_power_off, host=host, exp_resp=False, bmc_obj=bmc_obj)
        return resp

    def status_pods_online(self, no_pods: int):
        """
        Helper function to check that all Pods are shown online in cortx REST
        :param no_pods: Number of pods in the cluster
        :return: boolean
        """
        # Future: Right now system health api is not available but will be implemented after M0
        check_rem_pod = ["online" for _ in range(no_pods)]
        rest_resp = self.system_health.verify_node_health_status_rest(exp_status=check_rem_pod)
        LOGGER.info("REST response for pods health status. %s", rest_resp[1])
        return rest_resp

    def status_cluster_resource_online(self):
        """
        Check cluster/rack/site/pods are shown online in Cortx REST
        :return: boolean
        """
        LOGGER.info("Check cluster/rack/site/pods health status.")
        resp = self.check_csrn_status(csr_sts="online", pod_sts="online", pod_id=0)
        LOGGER.info("Health status response : %s", resp[1])
        if resp[0]:
            LOGGER.info("cluster/rack/site/pods health status is online in REST")
        return resp

    def check_csrn_status(self, csr_sts: str, pod_sts: str, pod_id: int):
        """
        Check cluster/rack/site/pod status with expected status using REST
        :param csr_sts: cluster/rack/site's expected status
        :param pod_sts: Pod's expected status
        :param pod_id: Pod ID to check for expected status
        :return: (bool, response)
        """
        check_rem_pod = [
            pod_sts if num == pod_id else "online" for num in range(self.num_pods)]
        LOGGER.info("Checking pod-%s status is %s via REST", pod_id+1, pod_sts)
        resp = self.system_health.verify_node_health_status_rest(
            check_rem_pod)
        if not resp[0]:
            return resp
        LOGGER.info("Checking Cluster/Site/Rack status is %s via REST", csr_sts)
        resp = self.system_health.check_csr_health_status_rest(csr_sts)
        if not resp[0]:
            return resp

        return True, f"cluster/rack/site status is {csr_sts} and \
        pod-{pod_id+1} is {pod_sts} in Cortx REST"

    def delete_s3_acc_buckets_objects(self, s3_data: dict):
        """
        This function deletes all s3 buckets objects for the s3 account
        and all s3 accounts
        :param s3_data: Dictionary for s3 operation info
        :return: (bool, response)
        """
        try:
            for details in s3_data.values():
                s3_del = S3TestLib(endpoint_url=S3_CFG["s3_url"],
                                   access_key=details['accesskey'],
                                   secret_key=details['secretkey'])
                response = s3_del.delete_all_buckets()
                if not response[0]:
                    return response
                response = self.s3_rest_obj.delete_s3_account(details['user_name'])
                if not response[0]:
                    return response
            return True, "Successfully performed S3 operation clean up"
        except (ValueError, KeyError, CTException) as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HAK8s.delete_s3_acc_buckets_objects.__name__,
                         error)
            return False, error

    # pylint: disable=too-many-arguments
    def perform_ios_ops(
            self,
            prefix_data: str = None,
            nusers: int = 2,
            nbuckets: int = 2,
            files_count: int = 10,
            di_data: tuple = None,
            is_di: bool = False,
            async_io: bool = False,
            stop_upload_time: int = 60):
        """
        This function creates s3 acc, buckets and performs IO.
        This will perform DI check if is_di True and once done,
        deletes all the buckets and s3 accounts created.
        :param prefix_data: Prefix data for IO Operation
        :param nusers: Number of s3 user
        :param nbuckets: Number of buckets per s3 user
        :param files_count: NUmber of files to be uploaded per bucket
        :param di_data: Data for DI check operation
        :param is_di: To perform DI check operation
        :param async_io: To perform parallel IO operation
        :param stop_upload_time: Approx time allowed for write operation to be finished
        before starting stop_io_async
        :return: (bool, response)
        """
        io_data = None
        try:
            if not is_di:
                LOGGER.info("create s3 acc, buckets and upload objects.")
                users = self.mgnt_ops.create_account_users(nusers=nusers)
                io_data = self.mgnt_ops.create_buckets(
                    nbuckets=nbuckets, users=users)
                run_data_chk_obj = RunDataCheckManager(users=io_data)
                pref_dir = {"prefix_dir": prefix_data}
                if async_io:
                    run_data_chk_obj.start_io_async(
                        users=io_data, buckets=None, files_count=files_count, prefs=pref_dir)
                    run_data_chk_obj.event.set()
                    time.sleep(stop_upload_time)
                    run_data_chk_obj.event.is_set()
                else:
                    star_res = run_data_chk_obj.start_io(
                        users=io_data, buckets=None, files_count=files_count, prefs=pref_dir)
                    if not star_res:
                        return False, star_res
                return True, run_data_chk_obj, io_data

            LOGGER.info("Checking DI for IOs run.")
            if async_io:
                stop_res = di_data[0].stop_io_async(users=di_data[1], di_check=is_di)
            else:
                stop_res = di_data[0].stop_io(users=di_data[1], di_check=is_di)
            if not stop_res[0]:
                return stop_res
            del_resp = self.delete_s3_acc_buckets_objects(di_data[1])
            if not del_resp[0]:
                return del_resp
            return True, "Di check for IOs passed successfully"
        except ValueError as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HAK8s.perform_ios_ops.__name__,
                         error)
            return False, error

    def perform_io_read_parallel(self, di_data, is_di=True, start_read=True):
        """
        This function runs parallel async stop_io function until called again with
        start_read with False.
        :param di_data: Tuple of RunDataCheckManager obj and User-bucket info from
        WRITEs call
        :param is_di: IF DI check is required on READ objects
        :param start_read: If True, function will start the parallel READs
        and if False function will Stop the parallel READs
        :return: bool/Process object or stop process status
        """
        if start_read:
            self.parallel_ios = Process(
                target=di_data[0].stop_io, args=(di_data[1], is_di))
            self.parallel_ios.start()
            return_val = (True, self.parallel_ios)
        else:
            if self.parallel_ios.is_alive():
                self.parallel_ios.join()
            LOGGER.info(
                "Parallel IOs stopped: %s",
                not self.parallel_ios.is_alive())
            return_val = (not self.parallel_ios.is_alive(), "Failed to stop parallel READ IOs.")
        return return_val

    # pylint: disable=too-many-arguments
    def ha_s3_workload_operation(
            self,
            log_prefix: str,
            s3userinfo: dict,
            skipread: bool = False,
            skipwrite: bool = False,
            skipcleanup: bool = False,
            nsamples: int = 20,
            nclients: int = 10):
        """
        This function creates s3 acc, buckets and performs WRITEs/READs/DELETEs
        operations on VM/HW.
        :param log_prefix: Test number prefix for log file
        :param s3userinfo: S3 user info
        :param skipread: Skip reading objects created in this run if True
        :param skipwrite: Skip writing objects created in this run if True
        :param skipcleanup: Skip deleting objects created in this run if True
        :param nsamples: Number of samples of object
        :param nclients: Number of clients/workers
        :return: bool/operation response
        """
        workloads = [
            "0B", "1KB", "16KB", "32KB", "64KB", "128KB", "256KB", "512KB",
            "1MB", "4MB", "8MB", "16MB", "32MB", "64MB", "128MB", "256MB", "512MB"]
        if self.setup_type == "HW":
            workloads.extend(["1GB", "2GB", "3GB" "4GB", "5GB"])

        resp = s3bench.setup_s3bench()
        if not resp:
            return resp, "Couldn't setup s3bench on client machine."
        for workload in workloads:
            resp = s3bench.s3bench(
                s3userinfo['accesskey'], s3userinfo['secretkey'], bucket=f"bucket_{log_prefix}",
                num_clients=nclients, num_sample=nsamples, obj_name_pref=f"ha_{log_prefix}",
                obj_size=workload, skip_write=skipwrite, skip_read=skipread,
                skip_cleanup=skipcleanup, log_file_prefix=f"log_{log_prefix}")
            resp = s3bench.check_log_file_error(resp[1])
            if resp:
                return resp, f"s3bench operation failed with {resp[1]}"
        return True, "Sucessfully completed s3bench operation"

    def cortx_start_cluster(self, pod_obj):
        """
        This function starts the cluster
        :param pod_obj : Pod object from which the command should be triggered
        :return: Boolean, response
        """
        LOGGER.info("Start the cluster")
        resp = pod_obj.execute_cmd(common_cmd.CLSTR_START_CMD.format(self.dir_path),
                                   read_lines=True, exc=False)
        LOGGER.info("Cluster start response: {}".format(resp))
        if resp[0]:
            return True, resp
        return False, resp

    def cortx_stop_cluster(self, pod_obj):
        """
        This function stops the cluster
        :param pod_obj : Pod object from which the command should be triggered
        :return: Boolean, response
        """
        LOGGER.info("Stop the cluster")
        resp = pod_obj.execute_cmd(common_cmd.CLSTR_STOP_CMD.format(self.dir_path),
                                   read_lines=True, exc=False)
        LOGGER.info("Cluster stop response: {}".format(resp))
        if resp[0]:
            return True, resp
        return False, resp

    def restart_cluster(self, pod_obj):
        """
        Restart the cluster and check all nodes health.
        :param pod_obj: pod object for stop/start cluster
        """
        LOGGER.info("Stop the cluster")
        resp = self.cortx_stop_cluster(pod_obj)
        if not resp[0]:
            return False, "Error during Stopping cluster"
        # TODO: will need to check if delay needed when stopping or starting cluster
        time.sleep(CMN_CFG["delay_60sec"])
        LOGGER.info("Check all Pods are offline.")
        resp = self.check_cluster_status(pod_obj)
        if resp[0]:
            return False, "Pods are still running."
        LOGGER.info("Start the cluster")
        resp = self.cortx_start_cluster(pod_obj)
        if not resp[0]:
            return False, "Error during Starting cluster"
        time.sleep(CMN_CFG["delay_60sec"])
        LOGGER.info("Check all Pods and cluster online.")
        resp = self.check_cluster_status(pod_obj)
        if not resp[0]:
            return False, "Cluster is not started"
        return True, resp

    @staticmethod
    def check_pod_status(pod_obj):
        """
        Helper function to check pods status.
        :param pod_obj: Pod object
        :return:
        """
        LOGGER.info("Checking if all Pods are online.")
        resp = pod_obj.execute_cmd(common_cmd.CMD_POD_STATUS, read_lines=True)
        for line in resp[1]:
            if "Running" in line or "Completed" in line:
                return True, resp
        return False, resp

    @staticmethod
    def create_bucket_to_complete_mpu(s3_data, bucket_name, object_name, file_size, total_parts,
                                      multipart_obj_path):
        """
        Helper function to complete multipart upload.
        :param s3_data: s3 account details
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param file_size: Size of the file to be created to upload
        :param total_parts: Total parts to be uploaded
        :param multipart_obj_path: Path of the file to be uploaded
        :return: response
        """
        access_key = s3_data["access_key"]
        secret_key = s3_data["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        s3_mp_test_obj = S3MultipartTestLib(access_key=access_key,
                                            secret_key=secret_key, endpoint_url=S3_CFG["s3_url"])

        LOGGER.info("Creating a bucket with name : %s", bucket_name)
        res = s3_test_obj.create_bucket(bucket_name)
        if not res[0] or res[1] != bucket_name:
            return res
        LOGGER.info("Created a bucket with name : %s", bucket_name)
        LOGGER.info("Initiating multipart upload")
        res = s3_mp_test_obj.create_multipart_upload(bucket_name, object_name)
        if not res[0]:
            return res
        mpu_id = res[1]["UploadId"]
        LOGGER.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        LOGGER.info("Uploading parts into bucket")
        res = s3_mp_test_obj.upload_parts(mpu_id=mpu_id, bucket_name=bucket_name,
                                          object_name=object_name, multipart_obj_size=file_size,
                                          total_parts=total_parts,
                                          multipart_obj_path=multipart_obj_path)
        if not res[0] or len(res[1]) != total_parts:
            return res
        parts = res[1]
        LOGGER.info("Uploaded parts into bucket: %s", parts)
        LOGGER.info("Successfully uploaded object")

        LOGGER.info("Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, bucket_name, object_name)
        if not res[0] or len(res[1]["Parts"]) != total_parts:
            return res
        LOGGER.info("Listed parts of multipart upload: %s", res[1])
        LOGGER.info("Completing multipart upload")
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts, bucket_name, object_name)
        if not res[0]:
            return res
        res = s3_test_obj.object_list(bucket_name)
        if object_name not in res[1]:
            return res
        LOGGER.info("Multipart upload completed")
        return True, s3_data

    def partial_multipart_upload(self, s3_data, bucket_name, object_name, part_numbers, parts_etag,
                                 **kwargs):
        """
        Helper function to do partial multipart upload.
        :param s3_data: s3 account details
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param part_numbers: List of parts to be uploaded
        :param parts_etag: List containing uploaded part number with its ETag
        :return: response
        """
        try:
            total_parts = kwargs.get("total_parts", None)
            multipart_obj_size = kwargs.get("multipart_obj_size", None)
            multipart_obj_path = kwargs.get("multipart_obj_path", None)
            remaining_upload = kwargs.get("remaining_upload", False)
            parts = kwargs.get("parts", None)
            mpu_id = kwargs.get("mpu_id", None)
            access_key = s3_data["access_key"]
            secret_key = s3_data["secret_key"]
            s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                    endpoint_url=S3_CFG["s3_url"])
            s3_mp_test_obj = S3MultipartTestLib(access_key=access_key, secret_key=secret_key,
                                                endpoint_url=S3_CFG["s3_url"])

            if not remaining_upload:
                LOGGER.info("Creating a bucket with name : %s", bucket_name)
                res = s3_test_obj.create_bucket(bucket_name)
                if not res[0] or res[1] != bucket_name:
                    return res
                LOGGER.info("Created a bucket with name : %s", bucket_name)
                LOGGER.info("Initiating multipart upload")
                res = s3_mp_test_obj.create_multipart_upload(bucket_name, object_name)
                if not res[0]:
                    return res
                mpu_id = res[1]["UploadId"]
                LOGGER.info("Multipart Upload initiated with mpu_id %s", mpu_id)

                LOGGER.info("Creating parts of data")
                if os.path.exists(multipart_obj_path):
                    os.remove(multipart_obj_path)
                system_utils.create_file(multipart_obj_path, multipart_obj_size)
                parts = self.create_multiple_data_parts(multipart_obj_size=multipart_obj_size,
                                                        multipart_obj_path=multipart_obj_path,
                                                        total_parts=total_parts)
                LOGGER.info("Created parts of data: %s", parts)

            LOGGER.info("Uploading parts %s", part_numbers)
            for part in part_numbers:
                resp = s3_mp_test_obj.upload_multipart(body=parts[part], bucket_name=bucket_name,
                                                       object_name=object_name, upload_id=mpu_id,
                                                       part_number=part)
                p_etag = resp[1]
                LOGGER.debug("Part : %s", str(p_etag))
                parts_etag.append({"PartNumber": part, "ETag": p_etag["ETag"]})
                LOGGER.info("Uploaded part %s", part)
            return True, mpu_id, parts, parts_etag
        except BaseException as error:
            LOGGER.error("Error in %s: %s", HAK8s.partial_multipart_upload.__name__, error)
            return False, error

    @staticmethod
    def create_multiple_data_parts(multipart_obj_path, multipart_obj_size, total_parts):
        """
        :param multipart_obj_size: Size of the file to be created to upload
        :param total_parts: Total parts to be uploaded
        :param multipart_obj_path: Path of the file to be uploaded
        :return: response
        """
        parts = {}
        uploaded_bytes = 0
        single_part_size = int(multipart_obj_size) // int(total_parts)
        with open(multipart_obj_path, "rb") as file_pointer:
            i = 1
            while True:
                data = file_pointer.read(1048576 * single_part_size)
                LOGGER.info("data_len %s", str(len(data)))
                if not data:
                    break
                parts[i] = data
                uploaded_bytes += len(data)
                i += 1

        return parts

    @staticmethod
    def create_bucket_copy_obj(s3_test_obj=None, bucket_name=None, object_name=None,
                               bkt_obj_dict=None, output=None, **kwargs):
        """
        Function create multiple buckets and upload and copy objects (Can be used to start
        background process for the same)
        :param s3_test_obj: s3 test lib object
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param bkt_obj_dict: Dict of buckets and objects
        :param output: Queue used to fill output
        :return: response
        """
        file_path = kwargs.get("file_path", None)
        background = kwargs.get("background", False)
        bkt_op = kwargs.get("bkt_op", True)
        put_etag = kwargs.get("put_etag", None)
        if bkt_op:
            LOGGER.info("Create bucket and put object.")
            resp = s3_test_obj.create_bucket(bucket_name)
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                return resp if not background else sys.exit(1)
            resp, bktlist = s3_test_obj.bucket_list()
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Bucket list: %s", bktlist)
            if bucket_name not in bktlist:
                return False, bktlist if not background else sys.exit(1)
            resp = system_utils.create_file(fpath=file_path, count=1000, b_size="1M")
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                return resp if not background else sys.exit(1)
            put_resp = s3_test_obj.put_object(bucket_name=bucket_name, object_name=object_name,
                                              file_path=file_path,
                                              metadata={"City": "Pune", "Country": "India"})
            LOGGER.info("Put object response: %s", put_resp)
            if not put_resp[0]:
                return resp if not background else sys.exit(1)
            put_etag = put_resp[1]["ETag"]
            resp = s3_test_obj.object_list(bucket_name)
            LOGGER.info("Response: %s", resp)
            if not resp[0] or object_name not in resp[1]:
                return resp if not background else sys.exit(1)

        LOGGER.info("Copy object to different bucket with different object name.")
        for k, v in bkt_obj_dict.items():
            bkt_name = k
            obj_name = v
            resp, bktlist = s3_test_obj.bucket_list()
            if bkt_name not in bktlist:
                resp = s3_test_obj.create_bucket(bkt_name)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    return resp if not background else sys.exit(1)
            status, response = s3_test_obj.copy_object(source_bucket=bucket_name,
                                                       source_object=object_name,
                                                       dest_bucket=bkt_name,
                                                       dest_object=obj_name)
            LOGGER.info("Response: %s", response)
            copy_etag = response['CopyObjectResult']['ETag']
            if put_etag == copy_etag:
                LOGGER.info("Object %s copied to bucket %s with object name %s successfully",
                            object_name, bkt_name, obj_name)
            else:
                LOGGER.info("Failed to copy object %s to bucket %s with object name %s",
                            object_name, bkt_name, obj_name)
                return False, response if not background else sys.exit()

        return True, put_etag if not background else output.put((True, put_etag))

    def start_random_mpu(self, s3_data, bucket_name, object_name, file_size, total_parts,
                         multipart_obj_path, part_numbers, parts_etag, output):
        """
        Helper function to start mpu (To start mpu in background, this function needs to be used)
        :param s3_data: s3 account details
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param file_size: Size of the file to be created to upload
        :param total_parts: Total parts to be uploaded
        :param multipart_obj_path: Path of the file to be uploaded
        :param part_numbers: List of random parts to be uploaded
        :param parts_etag: List containing uploaded part number with its ETag
        :param output: Queue used to fill output
        :return: response
        """
        access_key = s3_data["access_key"]
        secret_key = s3_data["secret_key"]
        failed_parts = {}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        s3_mp_test_obj = S3MultipartTestLib(access_key=access_key,
                                            secret_key=secret_key, endpoint_url=S3_CFG["s3_url"])

        try:
            LOGGER.info("Creating a bucket with name : %s", bucket_name)
            res = s3_test_obj.create_bucket(bucket_name)
            LOGGER.info("Response: %s", res)
            LOGGER.info("Created a bucket with name : %s", bucket_name)
            LOGGER.info("Initiating multipart upload")
            res = s3_mp_test_obj.create_multipart_upload(bucket_name, object_name)
            LOGGER.info("Response: %s", res)
            mpu_id = res[1]["UploadId"]
            LOGGER.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        except (Exception, CTException) as error:
            LOGGER.error("Failed mpu due to error %s. Exiting from background process.", error)
            sys.exit(1)

        LOGGER.info("Creating parts of data")
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        system_utils.create_file(multipart_obj_path, file_size)
        parts = self.create_multiple_data_parts(multipart_obj_size=file_size,
                                                multipart_obj_path=multipart_obj_path,
                                                total_parts=total_parts)
        LOGGER.debug("Created parts of data: %s", parts)
        LOGGER.info("Uploading parts into bucket")
        for i in part_numbers:
            try:
                resp = s3_mp_test_obj.upload_multipart(body=parts[i], bucket_name=bucket_name,
                                                       object_name=object_name, upload_id=mpu_id,
                                                       part_number=i)
                LOGGER.info("Response: %s", resp)
                p_tag = resp[1]
                LOGGER.debug("Part : %s", str(p_tag))
                parts_etag.append({"PartNumber": i, "ETag": p_tag["ETag"]})
                res = (parts_etag, mpu_id)
            except (Exception, CTException) as error:
                LOGGER.error("Error: %s", error)
                failed_parts[i] = parts[i]
                res = (failed_parts, parts_etag, mpu_id)

        output.put(res)

    def check_cluster_status(self, pod_obj):
        """
        :param pod_obj: Object for master node
        :return: boolean, response
        """
        LOGGER.info("Check the overall K8s cluster status.")
        resp = pod_obj.execute_cmd(common_cmd.CLSTR_STATUS_CMD.format(self.dir_path))
        LOGGER.info("Response for K8s cluster status: %s", resp)
        for line in resp:
            if "FAILED" in line:
                return False, resp
        res = pod_obj.send_k8s_cmd(
            operation="exec", pod=common_const.POD_NAME, namespace=common_const.NAMESPACE,
            command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} -- {common_cmd.MOTR_STATUS_CMD}",
            decode=True)
        LOGGER.info("Response for cortx cluster status: %s", res)
        for line in res:
            if "started" not in line:
                return False, res

        return True, "K8s and cortx both cluster up."
