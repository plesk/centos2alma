import unittest
from unittest import mock
import os

import actions


class SimpleAction(actions.ActiveAction):
    def __init__(self):
        self.name = "Simple action"
        self.description = "Simple action description"

    def _prepare_action(self):
        pass

    def _post_action(self):
        pass

    def _revert_action(self):
        pass


class SkipAction(actions.ActiveAction):
    def __init__(self):
        self.name = "Skip action"
        self.description = "Skip action description"

    def _is_required(self):
        return False

    def _prepare_action(self):
        pass

    def _post_action(self):
        pass

    def _revert_action(self):
        pass


class PrepareActionsFlowForTests(actions.PrepareActionsFlow):
    PATH_TO_ACTIONS_DATA = "./actions.json"


class TestPrepareActionsFlow(unittest.TestCase):

    def setUp(self):
        with open("actions.json", "w") as actions_data_file:
            actions_data_file.write("{ \"actions\": [] }")

    def tearDown(self):
        os.remove("actions.json")

    def test_one_simple_action(self):
        simple_action = SimpleAction()
        simple_action._prepare_action = mock.Mock()
        with PrepareActionsFlowForTests({ 1: [ simple_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._prepare_action.assert_called_once()

    def test_several_simple_actions(self):
        actions = []
        for _ in range(5):
            simple_action = SimpleAction()
            simple_action._prepare_action = mock.Mock()
            actions.append(simple_action)

        with PrepareActionsFlowForTests({ 1: actions }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        for action in actions:
            action._prepare_action.assert_called_once()

    def test_several_steps(self):
        simple_action_step_1 = SimpleAction()
        simple_action_step_1._prepare_action = mock.Mock()
        simple_action_step_2 = SimpleAction()
        simple_action_step_2._prepare_action = mock.Mock()

        with PrepareActionsFlowForTests({ 1: [ simple_action_step_1 ], 2: [ simple_action_step_2 ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action_step_1._prepare_action.assert_called_once()
        simple_action_step_2._prepare_action.assert_called_once()

    def test_skip_action(self):
        simple_action = SimpleAction()
        simple_action._prepare_action = mock.Mock()
        skip_action = SkipAction()
        skip_action._prepare_action = mock.Mock()

        with PrepareActionsFlowForTests({ 1: [ simple_action, skip_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._prepare_action.assert_called_once()
        skip_action._prepare_action.assert_not_called()

class SavedAction(actions.ActiveAction):
    def __init__(self):
        self.name = "saved"
        self.description = "Saved action description"

    def _prepare_action(self):
        pass

    def _post_action(self):
        pass

    def _revert_action(self):
        pass


class FinishActionsFlowForTests(actions.FinishActionsFlow):
    PATH_TO_ACTIONS_DATA = "./actions.json"


class TestFinishActionsFlow(unittest.TestCase):

    def setUp(self):
        with open("actions.json", "w") as actions_data_file:
            actions_data_file.write("{ \"actions\": [] }")

    def tearDown(self):
        # Flow removes the file by itself
        pass

    def test_one_simple_action(self):
        simple_action = SimpleAction()
        simple_action._post_action = mock.Mock()
        with FinishActionsFlowForTests({ 1: [ simple_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._post_action.assert_called_once()

    def test_several_simple_actions(self):
        actions = []
        for _ in range(5):
            simple_action = SimpleAction()
            simple_action._post_action = mock.Mock()
            actions.append(simple_action)

        with FinishActionsFlowForTests({ 1: actions }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        for action in actions:
            action._post_action.assert_called_once()

    def test_several_steps(self):
        simple_action_step_1 = SimpleAction()
        simple_action_step_1._post_action = mock.Mock()
        simple_action_step_2 = SimpleAction()
        simple_action_step_2._post_action = mock.Mock()

        with FinishActionsFlowForTests({ 1: [ simple_action_step_1 ], 2: [ simple_action_step_2 ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action_step_1._post_action.assert_called_once()
        simple_action_step_2._post_action.assert_called_once()

    def test_skip_action(self):
        simple_action = SimpleAction()
        simple_action._post_action = mock.Mock()
        skip_action = SkipAction()
        skip_action._post_action = mock.Mock()

        with FinishActionsFlowForTests({ 1: [ simple_action, skip_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._post_action.assert_called_once()
        skip_action._post_action.assert_not_called()

    def test_pass_based_on_saved_state(self):
        simple_action = SimpleAction()
        simple_action._post_action = mock.Mock()
        saved_action = SavedAction()
        saved_action._post_action = mock.Mock()

        with open("actions.json", "w") as actions_data_file:
            actions_data_file.write("{ \"actions\": [ { \"name\" : \"saved\", \"state\" : \"success\"}] }")

        with FinishActionsFlowForTests({ 1: [ simple_action, saved_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._post_action.assert_called_once()
        saved_action._post_action.assert_called_once()

    def test_skip_based_on_saved_state(self):
        simple_action = SimpleAction()
        simple_action._post_action = mock.Mock()
        saved_action = SavedAction()
        saved_action._post_action = mock.Mock()

        with open("actions.json", "w") as actions_data_file:
            actions_data_file.write("{ \"actions\": [ { \"name\" : \"saved\", \"state\" : \"skip\"}] }")

        with FinishActionsFlowForTests({ 1: [ simple_action, saved_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._post_action.assert_called_once()
        saved_action._post_action.assert_not_called()

    def test_skip_failed_saved_state(self):
        simple_action = SimpleAction()
        simple_action._post_action = mock.Mock()
        saved_action = SavedAction()
        saved_action._post_action = mock.Mock()

        with open("actions.json", "w") as actions_data_file:
            actions_data_file.write("{ \"actions\": [ { \"name\" : \"saved\", \"state\" : \"failed\"}] }")

        with FinishActionsFlowForTests({ 1: [ simple_action, saved_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._post_action.assert_called_once()
        saved_action._post_action.assert_not_called()

class RevertActionsFlowForTests(actions.RevertActionsFlow):
    PATH_TO_ACTIONS_DATA = "./actions.json"


class TestRevertActionsFlow(unittest.TestCase):

    def setUp(self):
        with open("actions.json", "w") as actions_data_file:
            actions_data_file.write("{ \"actions\": [] }")

    def tearDown(self):
        # Flow removes the file by itself
        pass

    def test_one_simple_action(self):
        simple_action = SimpleAction()
        simple_action._revert_action = mock.Mock()
        with RevertActionsFlowForTests({ 1: [ simple_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._revert_action.assert_called_once()

    def test_several_simple_actions(self):
        actions = []
        for _ in range(5):
            simple_action = SimpleAction()
            simple_action._revert_action = mock.Mock()
            actions.append(simple_action)

        with RevertActionsFlowForTests({ 1: actions }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        for action in actions:
            action._revert_action.assert_called_once()

    def test_several_steps(self):
        simple_action_step_1 = SimpleAction()
        simple_action_step_1._revert_action = mock.Mock()
        simple_action_step_2 = SimpleAction()
        simple_action_step_2._revert_action = mock.Mock()

        with RevertActionsFlowForTests({ 1: [ simple_action_step_1 ], 2: [ simple_action_step_2 ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action_step_1._revert_action.assert_called_once()
        simple_action_step_2._revert_action.assert_called_once()

    def test_skip_action(self):
        simple_action = SimpleAction()
        simple_action._revert_action = mock.Mock()
        skip_action = SkipAction()
        skip_action._revert_action = mock.Mock()

        with RevertActionsFlowForTests({ 1: [ simple_action, skip_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._revert_action.assert_called_once()
        skip_action._revert_action.assert_not_called()

    def test_pass_based_on_saved_state(self):
        simple_action = SimpleAction()
        simple_action._revert_action = mock.Mock()
        saved_action = SavedAction()
        saved_action._revert_action = mock.Mock()

        with open("actions.json", "w") as actions_data_file:
            actions_data_file.write("{ \"actions\": [ { \"name\" : \"saved\", \"state\" : \"success\"}] }")

        with RevertActionsFlowForTests({ 1: [ simple_action, saved_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._revert_action.assert_called_once()
        saved_action._revert_action.assert_called_once()

    def test_skip_based_on_saved_state(self):
        simple_action = SimpleAction()
        simple_action._revert_action = mock.Mock()
        saved_action = SavedAction()
        saved_action._revert_action = mock.Mock()

        with open("actions.json", "w") as actions_data_file:
            actions_data_file.write("{ \"actions\": [ { \"name\" : \"saved\", \"state\" : \"skip\"}] }")

        with RevertActionsFlowForTests({ 1: [ simple_action, saved_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._revert_action.assert_called_once()
        saved_action._revert_action.assert_not_called()

    def test_skip_failed_saved_state(self):
        simple_action = SimpleAction()
        simple_action._revert_action = mock.Mock()
        saved_action = SavedAction()
        saved_action._revert_action = mock.Mock()

        with open("actions.json", "w") as actions_data_file:
            actions_data_file.write("{ \"actions\": [ { \"name\" : \"saved\", \"state\" : \"failed\"}] }")

        with RevertActionsFlowForTests({ 1: [ simple_action, saved_action ] }) as flow:
            flow.validate_actions()
            flow.pass_actions()

        simple_action._revert_action.assert_called_once()
        saved_action._revert_action.assert_not_called()


class TrueCheckAction(actions.CheckAction):
    def __init__(self):
        self.name = "true"
        self.description = "Always returns true"

    def _do_check(self):
        return True


class FalseCheckAction(actions.CheckAction):
    def __init__(self):
        self.name = "false"
        self.description = "Always returns false"

    def _do_check(self):
        return False


class TestCheckFlow(unittest.TestCase):
    def test_true_check(self):
        check_action = TrueCheckAction()
        with actions.CheckFlow([ check_action ]) as flow:
            flow.validate_actions()
            res = flow.make_checks()
            self.assertEqual(len(res), 0)

    def test_several_true(self):
        checks = []
        for _ in range(5):
            checks.append(TrueCheckAction())

        with actions.CheckFlow(checks) as flow:
            flow.validate_actions()
            res = flow.make_checks()
            self.assertEqual(len(res), 0)

    def test_several_checks_with_one_false(self):
        checks = []
        checks.append(FalseCheckAction())
        for _ in range(5):
            checks.append(TrueCheckAction())

        with actions.CheckFlow(checks) as flow:
            flow.validate_actions()
            res = flow.make_checks()
            self.assertEqual(len(res), 1)

    def test_several_checks_with_several_false(self):
        checks = []
        for _ in range(5):
            checks.append(FalseCheckAction())
        for _ in range(5):
            checks.append(TrueCheckAction())

        with actions.CheckFlow(checks) as flow:
            flow.validate_actions()
            res = flow.make_checks()
            self.assertEqual(len(res), 5)
