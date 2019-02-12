import datetime
import logging
import unittest
from unittest import mock

from bson import ObjectId

from pillar.tests import common_test_data as ctd
from abstract_flamenco_test import AbstractFlamencoTest


class JobRunnabilityTest(AbstractFlamencoTest):
    def setUp(self, **kwargs):
        AbstractFlamencoTest.setUp(self, **kwargs)

        mngr_doc, account, token = self.create_manager_service_account()
        self.mngr_id = mngr_doc['_id']
        self.mngr_token = token['token']

        self.job_id = self.create_job()

    def create_job(self) -> ObjectId:
        from pillar.api.utils.authentication import force_cli_user

        # logging.basicConfig(level=logging.DEBUG)

        with self.app.test_request_context():
            force_cli_user()
            job = self.jmngr.api_create_job(
                'test job',
                'Wörk wørk w°rk.',
                'blender-render-progressive',
                {
                    'frames': '1-5',
                    'chunk_size': 3,
                    'render_output': '/render/out/frames-######',
                    'fps': 5.3,
                    'format': 'EXR',
                    'filepath': '/agent327/scenes/someshot/somefile.blend',
                    'blender_cmd': '/path/to/blender --enable-new-depsgraph',
                    'cycles_sample_count': 30,
                    # Effectively uncapped so that the number of tasks stays small.
                    'cycles_sample_cap': 30,
                },
                self.proj_id,
                ctd.EXAMPLE_PROJECT_OWNER_ID,
                self.mngr_id,
            )
        return job['_id']

    def test_runnability_check(self):
        tasks = self.get('/api/flamenco/managers/%s/depsgraph' % self.mngr_id,
                         auth_token=self.mngr_token).json['depsgraph']

        # Just check some things we assume in this test.
        self.assertEqual('create-preview-images', tasks[2]['name'])
        self.assertEqual([tasks[1]['_id']], tasks[2]['parents'])

        self.enter_app_context()

        from flamenco.celery import job_runnability_check as jrc

        # At first everything is runnable.
        self.assertEqual([], jrc._nonrunnable_tasks(self.job_id))

        # When we fail task 1, task 2 becomes unrunnable, and this should fail the job.
        self.force_task_status(tasks[1]['_id'], 'failed')
        self.assertIn(ObjectId(tasks[2]['_id']), jrc._nonrunnable_tasks(self.job_id))

        # If the job isn't active, the runnability check shouldn't do anything.
        self.assert_job_status('queued')
        jrc.runnability_check(str(self.job_id))
        self.assert_job_status('queued')

        # If the job is active, the check should fail the job.
        self.force_job_status('active')
        jrc.runnability_check(str(self.job_id))
        self.assert_job_status('fail-requested')

        job_doc = self.flamenco.db('jobs').find_one(self.job_id)
        self.assertIn('tasks have a failed/cancelled parent and will not be able to run.',
                      job_doc['status_reason'])
