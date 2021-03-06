import unittest

import apps
import core.case.database as case_database
import core.case.subscription as case_subscription
import core.config.config
import core.controller
import core.loadbalancer
import core.multiprocessedexecutor
from core.helpers import import_all_flags, import_all_filters
from tests import config
from tests.util.mock_objects import *


class TestExecutionEvents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apps.cache_apps(config.test_apps_path)
        core.config.config.load_app_apis(apps_path=config.test_apps_path)
        core.config.config.flags = import_all_flags('tests.util.flagsfilters')
        core.config.config.filters = import_all_filters('tests.util.flagsfilters')
        core.config.config.load_flagfilter_apis(path=config.function_api_path)
        core.multiprocessedexecutor.MultiprocessedExecutor.initialize_threading = mock_initialize_threading
        core.multiprocessedexecutor.MultiprocessedExecutor.shutdown_pool = mock_shutdown_pool

    def setUp(self):
        self.c = core.controller.controller
        self.c.initialize_threading()
        case_database.initialize()

    def tearDown(self):
        case_database.case_db.tear_down()

    @classmethod
    def tearDownClass(cls):
        apps.clear_cache()

    def test_workflow_execution_events(self):

        self.c.load_playbook(resource=config.test_workflows_path + 'multiactionWorkflowTest.playbook')
        workflow_uid = self.c.get_workflow('multiactionWorkflowTest', 'multiactionWorkflow').uid
        subs = {'case1': {workflow_uid: ['App Instance Created', 'Step Execution Success',
                                         'Next Step Found', 'Workflow Shutdown']}}
        case_subscription.set_subscriptions(subs)
        self.c.execute_workflow('multiactionWorkflowTest', 'multiactionWorkflow')

        self.c.shutdown_pool(1)
        execution_events = case_database.case_db.session.query(case_database.Case) \
            .filter(case_database.Case.name == 'case1').first().events.all()

        self.assertEqual(len(execution_events), 6,
                         'Incorrect length of event history. '
                         'Expected {0}, got {1}'.format(6, len(execution_events)))

    def test_step_execution_events(self):
        self.c.load_playbook(resource=config.test_workflows_path + 'basicWorkflowTest.playbook')
        workflow = self.c.get_workflow('basicWorkflowTest', 'helloWorldWorkflow')
        step_uids = [step.uid for step in workflow.steps.values()]
        step_events = ['Function Execution Success', 'Step Started', 'Conditionals Executed']
        subs = {'case1': {step_uid: step_events for step_uid in step_uids}}
        case_subscription.set_subscriptions(subs)

        self.c.execute_workflow('basicWorkflowTest', 'helloWorldWorkflow')

        self.c.shutdown_pool(1)

        execution_events = case_database.case_db.session.query(case_database.Case) \
            .filter(case_database.Case.name == 'case1').first().events.all()
        self.assertEqual(len(execution_events), 3,
                         'Incorrect length of event history. '
                         'Expected {0}, got {1}'.format(3, len(execution_events)))

    def test_flag_filters_execution_events(self):
        self.c.load_playbook(resource=config.test_workflows_path + 'basicWorkflowTest.playbook')
        workflow = self.c.get_workflow('basicWorkflowTest', 'helloWorldWorkflow')
        step = workflow.steps['start']
        subs = {step.uid: ['Function Execution Success', 'Step Started', 'Conditionals Executed']}
        next_step = next(conditional for conditional in step.next_steps if conditional.name == '1')
        subs[next_step.uid] = ['Next Step Taken', 'Next Step Not Taken']
        flag = next(flag for flag in next_step.flags if flag.action == 'regMatch')
        subs[flag.uid] = ['Flag Success', 'Flag Error']
        filter_ = next(filter_elem for filter_elem in flag.filters if filter_elem.action == 'length')
        subs[filter_.uid] = ['Filter Success', 'Filter Error']

        case_subscription.set_subscriptions({'case1': subs})

        self.c.execute_workflow('basicWorkflowTest', 'helloWorldWorkflow')

        self.c.shutdown_pool(1)

        events = case_database.case_db.session.query(case_database.Case) \
            .filter(case_database.Case.name == 'case1').first().events.all()
        self.assertEqual(len(events), 6,
                         'Incorrect length of event history. '
                         'Expected {0}, got {1}'.format(6, len(events)))
