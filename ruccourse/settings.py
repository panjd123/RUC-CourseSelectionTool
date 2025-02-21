from configparser import ConfigParser


class Settings(object):
    enabled_dynamic_requests: bool
    target_requests_per_second: int
    requests_per_second: int
    reject_warning_threshold: float
    log_interval_seconds: int
    gap: int
    silent: bool
    stats: bool

    def __init__(self, config_path) -> None:
        config = ConfigParser()
        config.read(config_path, encoding="utf-8")

        self.enabled_dynamic_requests = config["DEFAULT"].getboolean(
            "enabled_dynamic_requests"
        )
        self.target_requests_per_second = int(config["DEFAULT"]["requests_per_second"])
        self.requests_per_second = self.target_requests_per_second
        self.reject_warning_threshold = float(
            config["DEFAULT"]["reject_warning_threshold"]
        )
        self.log_interval_seconds = int(config["DEFAULT"]["log_interval_seconds"])
        self.reject_warning_threshold = (
            self.reject_warning_threshold * self.target_requests_per_second
        )
        self.gap = int(config["DEFAULT"]["gap"])
        self.silent = config["DEFAULT"].getboolean("silent")
        self.stats = config["DEFAULT"].getboolean("stats")
