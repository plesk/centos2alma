import os
import json
from enum import Enum

import common


class Action():

    def __init__(self):
        self.name = ""
        self.description = ""

    def __str__(self):
        return "{name}!".format(name=self.name)

    def __repr__(self):
        return "{classname}".format(classname=self.__class__.__name__)


class ActiveAction(Action):
    def invoke_prepare(self):
        self._prepare_action()

    def invoke_post(self):
        self._post_action()

    def invoke_revert(self):
        self._revert_action()

    def is_required(self):
        return self._is_required()

    def _is_required(self):
        # All actions are required by default - just to simplefy things
        return True

    def _prepare_action(self):
        raise NotImplementedError("Not implemented prapare action is called")

    def _post_action(self):
        raise NotImplementedError("Not implemented post action is called")

    def _revert_action(self):
        raise NotImplementedError("Not implemented revert action is called")


class ActionState(str, Enum):
    success = 'success'
    skiped = 'skip'
    failed = 'failed'


class ActionsFlow():

    def __init__(self, stages):
        self.stages = stages

    def __enter__(self):
        return self

    def __exit__(self, *kwargs):
        pass


class ActiveFlow(ActionsFlow):

    PATH_TO_ACTIONS_DATA = "/usr/local/psa/tmp/distupgrader_actions.json"

    def __init__(self, stages):
        super().__init__(stages)

    def validate_actions(self):
        # Note. This one is for development porpuses only
        for _, actions in self.stages.items():
            for action in actions:
                if not isinstance(action, ActiveAction):
                    raise TypeError("Non an ActiveAction passed into action flow. Name of the action is {name!s}".format(action.name))

    def pass_actions(self):
        stages = self._get_flow()

        for stage_id, actions in stages.items():
            self._pre_stage(stage_id, actions)
            for action in actions:
                if not self._is_action_required(action):
                    common.log.info("Skipped: {description!s}".format(description=action))
                    self._save_action_state(action.name, ActionState.skiped)
                    continue

                common.log.info("Do: {description!s}".format(description=action))

                try:
                    self._invoke_action(action)
                except Exception as ex:
                    self._save_action_state(action.name, ActionState.failed)
                    raise Exception("Failed: {description!s}. The reason: {error}".format(description=action, error=ex))

                self._save_action_state(action.name, ActionState.success)
                common.log.info("Success: {description!s}".format(description=action))

            self._post_stage(stage_id, actions)

    def _get_flow(self):
        pass

    def _pre_stage(self, stage_id, actions):
        common.log.info("Start stage {stage}.".format(stage=stage_id))
        pass

    def _post_stage(self, stage_id, actions):
        pass

    def _is_action_required(self, action):
        return action.is_required()

    def _invoke_action(self, action):
        pass

    def _save_action_state(self, name, state):
        pass

    def _load_actions_state(self):
        if os.path.exists(self.PATH_TO_ACTIONS_DATA):
            with open(self.PATH_TO_ACTIONS_DATA, "r") as actions_data_file:
                return json.load(actions_data_file)

        return {"actions": []}


class PrepareActionsFlow(ActiveFlow):

    def __init__(self, stages):
        super().__init__(stages)
        self.actions_data = {}

    def __enter__(self):
        self.actions_data = self._load_actions_state()
        return self

    def __exit__(self, *kwargs):
        common.rewrite_json_file(self.PATH_TO_ACTIONS_DATA, self.actions_data)

    def _save_action_state(self, name, state):
        for action in self.actions_data["actions"]:
            if action["name"] == name:
                action["state"] = state
                return

        self.actions_data["actions"].append({"name": name, "state": state})

    def _get_flow(self):
        return self.stages

    def _invoke_action(self, action):
        action.invoke_prepare()


class ReverseActionFlow(ActiveFlow):

    def __enter__(self):
        self.actions_data = self._load_actions_state()
        return self

    def __exit__(self, *kwargs):
        if os.path.exists(self.PATH_TO_ACTIONS_DATA):
            os.remove(self.PATH_TO_ACTIONS_DATA)

    def _get_flow(self):
        return dict(reversed(list(self.stages.items())))

    def _is_action_required(self, action):
        # I believe the finish stage could have an action that was not performed on preparation and conversation stages
        # So we ignore the case when there is no actions is persistance store
        for stored_action in self.actions_data["actions"]:
            if stored_action["name"] == action.name:
                if stored_action["state"] == ActionState.failed or stored_action["state"] == ActionState.skiped:
                    return False
                elif stored_action["state"] == ActionState.success:
                    return True

        return action.is_required()


class FinishActionsFlow(ReverseActionFlow):
    def _invoke_action(self, action):
        action.invoke_post()


class RevertActionsFlow(ReverseActionFlow):
    def _invoke_action(self, action):
        action.invoke_revert()

class CheckAction(Action):
    def do_check(self):
        return self._do_check()

    def _do_check(self):
        raise NotImplementedError("Not implemented check call")


class CheckFlow(ActionsFlow):

    def validate_actions(self):
        # Note. This one is for development porpuses only
        for check in self.stages:

            if not isinstance(check, CheckAction):
                raise TypeError("Non an CheckAction passed into check flow. Name of the action is {name!s}".format(check.name))

    def make_checks(self):
        is_all_passed = True
        common.log.debug("Start checks")
        for check in self.stages:
            common.log.debug("Make check {name}".format(name=check.name))
            if not check.do_check():
                common.log.err("Required pre-conversion condition {name!s} not met:\n{description!s}".format(name=check.name, description=check.description))
                is_all_passed = False

        return is_all_passed
