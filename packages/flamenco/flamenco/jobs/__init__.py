"""Job management."""

import collections
import copy

import attr
import pillarsdk
from pillar import attrs_extra
from pillar.web.system_util import pillar_api

from pillarsdk.resource import List
from pillarsdk.resource import Find
from pillarsdk.resource import Create
from pillarsdk.resource import Post
from pillarsdk.resource import Update
from pillarsdk.resource import Delete
from pillarsdk.resource import Replace


class ProjectSummary(object):
    """Summary of the jobs in a project."""

    def __init__(self):
        self._counts = collections.defaultdict(int)
        self._total = 0

    def count(self, status):
        self._counts[status] += 1
        self._total += 1

    def percentages(self):
        """Generator, yields (status, percentage) tuples.

        The percentage is on a 0-100 scale.
        """

        remaining = 100
        last_index = len(self._counts) - 1

        for idx, status in enumerate(sorted(self._counts.keys())):
            if idx == last_index:
                yield (status, remaining)
                continue

            perc = float(self._counts[status]) / self._total
            whole_perc = int(round(perc * 100))
            remaining -= whole_perc

            yield (status, whole_perc)


class Job(List, Find, Create, Post, Update, Delete, Replace):
    """Job class wrapping the REST nodes endpoint
    """
    path = 'flamenco/jobs'
    ensure_query_projections = {'project': 1}


@attr.s
class JobManager(object):
    _log = attrs_extra.log('%s.JobManager' % __name__)

    def api_create_job(self, job_name, job_desc, job_type, job_settings,
                       project_id, user_id, manager_id):
        """Creates a job, returning a dict with its generated fields."""

        from eve.methods.post import post_internal

        job = {
            'name': job_name,
            'description': job_desc,
            'job_type': job_type,
            'project': project_id,
            'user': user_id,
            'manager': manager_id,
            'status': 'queued',
            'priority': 50,
            'settings': copy.deepcopy(job_settings),
        }

        self._log.info('Creating job %r for user %s and manager %s',
                       job_name, user_id, manager_id)

        r, _, _, status = post_internal('flamenco_jobs', job)
        if status != 201:
            self._log.error('Status should be 201, not %i: %s' % (status, r))
            raise ValueError('Unable to create Flamenco job, status code %i' % status)

        job.update(r)
        return job

    def edit_job(self, job_id, **fields):
        """Edits a job.

        :type job_id: str
        :type fields: dict
        :rtype: pillarsdk.Node
        """

        api = pillar_api()
        job = pillarsdk.Node.find(job_id, api=api)

        job._etag = fields.pop('_etag')
        job.name = fields.pop('name')
        job.description = fields.pop('description')
        job.status = fields.pop('status')
        job.properties.job_type = fields.pop('job_type', '').strip() or None

        users = fields.pop('users', None)
        job.properties.assigned_to = {'users': users or []}

        self._log.info('Saving job %s', job.to_dict())

        if fields:
            self._log.warning('edit_job(%r, ...) called with unknown fields %r; ignoring them.',
                              job_id, fields)

        job.update(api=api)
        return job

    def delete_job(self, job_id, etag):
        api = pillar_api()

        self._log.info('Deleting job %s', job_id)
        job = pillarsdk.Resource({'_id': job_id, '_etag': etag})
        job.path = 'flamenco/jobs'
        job.delete(api=api)

    def jobs_for_user(self, user_id):
        """Returns the jobs for the given user.

        :returns: {'_items': [job, job, ...], '_meta': {Eve metadata}}
        """

        api = pillar_api()

        # TODO: also include jobs assigned to any of the user's groups.
        jobs = pillarsdk.resource.List()
        jobs.list_class.path = 'flamenco/jobs'
        j = jobs.all({
            'where': {
                'user': user_id,
            }
        }, api=api)

        return j

    def jobs_for_project(self, project_id):
        """Returns the jobs for the given project.

        :returns: {'_items': [job, job, ...], '_meta': {Eve metadata}}
        """

        api = pillar_api()
        jobs = pillarsdk.resource.List()
        jobs.list_class.path = 'flamenco/jobs'
        j = jobs.all({
            'where': {
                'project': project_id,
            }}, api=api)
        return j

    def job_status_summary(self, project_id):
        """Returns number of shots per shot status for the given project.

                :rtype: ProjectSummary
                """

        api = pillar_api()

        # TODO: turn this into an aggregation call to do the counting on
        # MongoDB.
        jobs = Job.all({
            'where': {
                'project': project_id,
            },
            'projection': {
                'status': 1,
            },
            'order': [
                ('status', 1),
            ],
        }, api=api)

        # FIXME: this breaks when we hit the pagination limit.
        summary = ProjectSummary()
        for job in jobs['_items']:
            summary.count(job['status'])

        return summary


def setup_app(app):
    from . import eve_hooks

    eve_hooks.setup_app(app)