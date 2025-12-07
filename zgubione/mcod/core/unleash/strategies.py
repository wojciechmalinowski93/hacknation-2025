from UnleashClient.strategies import Strategy


class EnvironmentName(Strategy):
    def load_provisioning(self) -> list:
        return [x.strip() for x in self.parameters["envNames"].split(",")]

    def apply(self, context: dict = None) -> bool:
        return_value = False

        if "envName" in context.keys():
            return_value = context["envName"] in self.parsed_provisioning

        return return_value
