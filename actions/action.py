import os
import json
import math
import time
import shutil
import sys

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

    # For all estimates we assume all actions takes no more
    # than 1 second by default.
    # We trying to avoid estimate for small actions like
    # "change one line in string" or "remove one file"... etc
    def estimate_prepare_time(self):
        return 1

    def estimate_post_time(self):
        return 1

    def estimate_revert_time(self):
        return 1


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

    PATH_TO_ACTIONS_DATA = "/usr/local/psa/tmp/centos2alma_actions.json"

    def __init__(self, stages):
        super().__init__(stages)
        self._finished = False
        self.current_stage = "initiliazing"
        self.current_action = "initiliazing"
        self.total_time = 0
        self.error = None

    def validate_actions(self):
        # Note. This one is for development porpuses only
        for _, actions in self.stages.items():
            for action in actions:
                if not isinstance(action, ActiveAction):
                    raise TypeError("Non an ActiveAction passed into action flow. Name of the action is {name!s}".format(action.name))

    def pass_actions(self):
        stages = self._get_flow()
        self._finished = False

        for stage_id, actions in stages.items():
            self._pre_stage(stage_id, actions)
            for action in actions:
                try:
                    if not self._is_action_required(action):
                        common.log.info("Skipped: {description!s}".format(description=action))
                        self._save_action_state(action.name, ActionState.skiped)
                        continue

                    self._invoke_action(action)

                    self._save_action_state(action.name, ActionState.success)
                    common.log.info("Success: {description!s}".format(description=action))
                except Exception as ex:
                    self._save_action_state(action.name, ActionState.failed)
                    self.error = Exception("Failed: {description!s}. The reason: {error}".format(description=action, error=ex))
                    common.log.err("Failed: {description!s}. The reason: {error}".format(description=action, error=ex))
                    return False

            self._post_stage(stage_id, actions)

        self._finished = True
        return True

    def _get_flow(self):
        pass

    def _pre_stage(self, stage_id, actions):
        common.log.info("Start stage {stage}.".format(stage=stage_id))
        self.current_stage = stage_id
        pass

    def _post_stage(self, stage_id, actions):
        pass

    def _is_action_required(self, action):
        return action.is_required()

    def _invoke_action(self, action):
        common.log.info("Do: {description!s}".format(description=action))
        self.current_action = action.name

    def _save_action_state(self, name, state):
        pass

    def _load_actions_state(self):
        if os.path.exists(self.PATH_TO_ACTIONS_DATA):
            with open(self.PATH_TO_ACTIONS_DATA, "r") as actions_data_file:
                return json.load(actions_data_file)

        return {"actions": []}

    def is_finished(self):
        return self._finished or self.error is not None

    def is_failed(self):
        return self.error is not None

    def get_error(self):
        return self.error

    def get_current_stage(self):
        return self.current_stage

    def get_current_action(self):
        return self.current_action

    def _get_action_estimate(self, action):
        return action.estimate_prepare_time()

    def get_total_time(self):
        if self.total_time != 0:
            return self.total_time

        for _, actions in self.stages.items():
            for action in actions:
                self.total_time += self._get_action_estimate(action)

        return self.total_time


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
        super()._invoke_action(action)
        action.invoke_prepare()

    def _get_action_estimate(self, action):
        return action.estimate_prepare_time()


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
        super()._invoke_action(action)
        action.invoke_post()

    def _get_action_estimate(self, action):
        if not self._is_action_required(action):
            return 0
        return action.estimate_post_time()


class RevertActionsFlow(ReverseActionFlow):
    def _invoke_action(self, action):
        super()._invoke_action(action)
        action.invoke_revert()

    def _get_action_estimate(self, action):
        if not self._is_action_required(action):
            return 0
        return action.estimate_revert_time()


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
        failed_checks_msgs = []
        common.log.debug("Start checks")
        for check in self.stages:
            common.log.debug("Make check {name}".format(name=check.name))
            if not check.do_check():
                failed_checks_msgs.append(f"Required pre-conversion condition {check.name!s} not met:\n\t{check.description!s}\n")

        return failed_checks_msgs


class FlowProgressbar():
    def __init__(self, flow, writers=None):
        self.flow = flow
        self.total_time = flow.get_total_time()

        if writers is None:
            writers = [common.StdoutWriter]
        self.writers = writers

    def _seconds_to_minutes(self, seconds):
        minutes = int(seconds / 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def get_action_description(self):
        description = f" stage {self.flow.get_current_stage()} / action {self.flow.get_current_action()} "
        description_length = len(description)
        return "(" + " " * math.floor((50 - description_length) / 2) + description + " " * math.ceil((50 - description_length) / 2) + ")"

    def write(self, msg):
        for writer in self.writers:
            writer.write(msg)

    def display(self):
        start_time = time.time()
        passed_time = 0

        while passed_time < self.total_time and not self.flow.is_finished():
            percent = int((passed_time) / self.total_time * 100)

            description = self.get_action_description()

            progress = "=" * int(percent / 2) + ">" + " " * (50 - int(percent / 2))
            progress = "[" + progress[:25] + description + progress[25:] + "]"

            terminal_size, _ = shutil.get_terminal_size()
            output = ""
            if terminal_size > 118:
                output = progress + " " + self._seconds_to_minutes(passed_time) + " / " + self._seconds_to_minutes(self.total_time)
            elif terminal_size > 65 and terminal_size < 118:
                output = description + " " + self._seconds_to_minutes(passed_time) + " / " + self._seconds_to_minutes(self.total_time)
            else:
                output = self._seconds_to_minutes(passed_time) + " / " + self._seconds_to_minutes(self.total_time)

            clean = " " * (terminal_size - len(output))

            if percent < 80:
                color = "\033[92m"  # green
            else:
                color = "\033[93m"  # yellow
            drop_color = "\033[0m"

            self.write(f"\r{color}{output}{clean}{drop_color}")
            time.sleep(1)
            passed_time = time.time() - start_time

        if passed_time > self.total_time:
            self.write("\r\033[91m[" + "X" * 25 + self.get_action_description() + "X" * 25 + "] exceed\033[0m")
            self.write(common.TIME_EXCEEDED_MESSAGE.format(common.DEFAULT_LOG_FILE))

