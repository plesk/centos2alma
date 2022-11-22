import shutil
class Action():

    def __init__(self):
        self.name = ""

    def __str__(self):
        return "I'm an action {name}!".format(name=self.name)

    def __repr__(self):
        return "{classname}".format(classname=self.__class__.__name__)

    def invoke_prepare(self):
        try:
            self._prepare_action()
        except Exception as ex:
            raise Exception("Prepare action '{name}' has been failed".format(name=self.name)) from ex

    def invoke_post(self):
        try:
            self._post_action()
        except Exception as ex:
            raise Exception("Finishing action '{name}' has been failed".format(name=self.name)) from ex

    def _prepare_action(self):
        raise NotImplementedError("Not implemented prapare action is called")

    def _post_action(self):
        raise NotImplementedError("Not implemented post action is called")

    def _replace_string(filename, original_substring, new_substring):
        with open(filename, "r") as original, open(filename + ".next", "w") as dst:
            for line in original.readlines():
                line = line.replace(original_substring, new_substring)
                if line:
                    dst.write(line)

        shutil.move(filename + ".next", filename)


class ActionsFlow():

    def __init__(self, stages):
        self.stages = stages

    def pass_actions(self):
        stages = self._get_flow()

        for stage_id, actions in stages.items():
            self._pre_stage(stage_id, actions)
            for action in actions:
                print("Making {description!s}".format(description=action))
                self._invoke_action(action)
                print("{feel}OK".format(feel="." * (40 - len(str(action)))))
            self._post_stage(stage_id, actions)

    def _get_flow(self):
        pass

    def _pre_stage(self, stage_id, actions):
        print("Stage {stage}:".format(stage=stage_id))
        pass

    def _post_stage(self, stage_id, actions):
        pass

    def _invoke_action(self, action):
        pass


class PrepareActionsFlow(ActionsFlow):
    def _get_flow(self):
        return self.stages

    def _invoke_action(self, action):
        action.invoke_prepare()


class FinishActionsFlow(ActionsFlow):
    def _get_flow(self):
        return dict(reversed(list(self.stages.items())))

    def _invoke_action(self, action):
        action.invoke_post()
