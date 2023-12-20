from ruclogin import *
from datetime import datetime, timedelta
from time import sleep
import pickle
import aiohttp
import asyncio
from timeit import default_timer as timer
from configparser import ConfigParser
import logging
import os
import os.path as osp

if __name__ == "__main__":  # 并不是一种优雅的写法，待改进
    import collect
else:
    from . import collect

from docopt import docopt

ROOT = osp.dirname(osp.abspath(__file__))
log_path = osp.join(ROOT, "ruccourse.log")
config_path = osp.join(ROOT, "config.ini")
json_datas_path = osp.join(ROOT, "json_datas.pkl")
collect_py_path = osp.join(ROOT, "collect.py")

IMPORTANT_INFO = 25
logging.addLevelName(IMPORTANT_INFO, "IMPORTANT_INFO")
logger = logging.getLogger(__name__)


def imp_info(self, message, *args, **kwargs):
    if self.isEnabledFor(IMPORTANT_INFO):
        self._log(IMPORTANT_INFO, message, args, **kwargs)


logging.Logger.imp_info = imp_info
logger.setLevel(logging.INFO)
file_hd = logging.FileHandler(log_path, mode="a", encoding="utf-8")
file_hd.setLevel(logging.INFO)
file_hd.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
console_hd = logging.StreamHandler()
console_hd.setLevel(IMPORTANT_INFO)
console_hd.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_hd)
logger.addHandler(console_hd)
json_datas = []


class Log_infomations(object):
    tic: float
    toc: float
    total_requests: int
    iter_requests: int
    iter_reject_requests: int
    course_info: dict

    @staticmethod
    def init_info(json_datas):
        return {
            json_data["ktmc_name"]: {
                "kcmc": json_data["ktmc_name"],
                "total": 0,
                "reject": 0,
            }
            for json_data in json_datas
        }

    def reset(self, json_datas):
        self.tic = self.toc = timer()
        self.iter_requests = 0
        self.iter_reject_requests = 0
        self.course_info = self.init_info(json_datas)

    def __init__(self, json_datas) -> None:
        self.reset(json_datas)
        self.total_requests = 0


class Settings(object):
    enabled_dynamic_requests: bool
    target_requests_per_second: int
    requests_per_second: int
    reject_warning_threshold: float
    log_interval_seconds: int
    gap: int

    def __init__(self, config_path, json_datas) -> None:
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
            self.reject_warning_threshold
            * self.target_requests_per_second
            / len(json_datas)
        )
        self.gap = int(config["DEFAULT"]["gap"])

    def __str__(self) -> str:
        return f"enabled_dynamic_requests: {self.enabled_dynamic_requests}\ntarget_requests_per_second: {self.target_requests_per_second}\nrequests_per_second: {self.requests_per_second}\nreject_warning_threshold: {self.reject_warning_threshold}\nlog_interval_seconds: {self.log_interval_seconds}"

    def __repr__(self) -> str:
        return self.__str__()


async def grab(json_data):
    global cookies, json_datas, log_infos
    url = "https://jw.ruc.edu.cn/resService/jwxtpt/v1/xsd/stuCourseCenterController/saveStuXkByRmdx"
    params = {
        "resourceCode": "XSMH0303",
        "apiCode": "jw.xsd.courseCenter.controller.StuCourseCenterController.saveStuXkByRmdx",
    }

    headers = {
        "Accept": "application/json, text/plain, */*",
        "TOKEN": cookies["token"],
    }

    async with aiohttp.ClientSession(
        cookies={"SESSION": cookies["SESSION"]}
    ) as session:
        async with session.post(
            url, params=params, json=json_data, headers=headers
        ) as response:
            result = await response.json()
            errorCode = result["errorCode"]
            cls_name = json_data["ktmc_name"]
            "eywxt.save.stuLimit.error"  # 选课人数已满
            "eywxt.save.msLimit.error"  # 本身有剩余名额，但同类别已选数目达到上限
            "服务器繁忙，请稍后再试！"  # 服务器繁忙，请稍后再试！
            if errorCode == "success":
                logger.imp_info(f"抢到 {cls_name}")
                json_datas.remove(json_data)
                del log_infos.course_info[json_data["ktmc_name"]]
            elif errorCode == "eywxt.save.msLimit.error":
                logger.imp_info(f"{cls_name} 有名额，但同类别已选数目达到上限")
                json_datas.remove(json_data)
                del log_infos.course_info[json_data["ktmc_name"]]
            elif errorCode == "服务器繁忙，请稍后再试！":
                log_infos.iter_reject_requests += 1
                log_infos.course_info[cls_name]["reject"] += 1
            elif errorCode == "eywxt.save.cantXkByCopy.error":
                logger.imp_info(f"{cls_name} 已选，跳过")
                json_datas.remove(json_data)
                del log_infos.course_info[json_data["ktmc_name"]]
            else:
                logger.warning(f"未知 errCode: {errorCode}，请联系开发人员")
            if len(json_datas) == 0:
                logger.imp_info("抢课列表为空")
                logger.imp_info("脚本已停止")
                exit(0)
            log_infos.course_info[cls_name]["total"] += 1
            log_infos.total_requests += 1
            log_infos.iter_requests += 1
            return [cls_name, errorCode]


async def log(stop_signal):
    global log_infos, settings  # requests_per_second, enabled_dynamic_requests, target_requests_per_second, reject_warning_threshold, log_interval_seconds,
    log_infos.reset(json_datas)
    await asyncio.sleep(1)
    while not stop_signal.is_set():
        log_infos.toc = timer()
        reqs = log_infos.iter_requests / (log_infos.toc - log_infos.tic)
        tru_reqs = (log_infos.iter_requests - log_infos.iter_reject_requests) / (
            log_infos.toc - log_infos.tic
        )
        rej_ratio = log_infos.iter_reject_requests / log_infos.iter_requests

        worst_reqs = 100000
        for cls_name in log_infos.course_info.keys():
            if log_infos.course_info[cls_name]["total"] != 0:
                worst_reqs = min(
                    worst_reqs,
                    (
                        log_infos.course_info[cls_name]["total"]
                        - log_infos.course_info[cls_name]["reject"]
                    )
                    / (log_infos.toc - log_infos.tic),
                )

        if worst_reqs < settings.reject_warning_threshold:
            logger.warning(
                f"{str(round(rej_ratio*100,2))+'%':<5} 的请求被拒绝，真实请求速度为 {round(tru_reqs,2):<5} req/s，其中最低请求速度的课程为 {round(worst_reqs,2):<5} req/s"
            )

        logger.info(
            f"req/s: {round(reqs, 2):<5}\ttru_reqs/s: {round(tru_reqs,2):<5}\ttotal: {log_infos.total_requests}"
        )

        flush = False
        if settings.enabled_dynamic_requests:
            if (
                tru_reqs < settings.target_requests_per_second * 0.9
                and log_infos.toc - log_infos.tic > 5
            ):
                settings.requests_per_second = settings.requests_per_second * 1.05
                logger.info(
                    f"请求速度小于预期，已调整为{round(settings.requests_per_second,2):<6} req/s"
                )
                flush = True
            if (
                tru_reqs > settings.target_requests_per_second * 1.1
                and log_infos.toc - log_infos.tic > 5
            ):
                settings.requests_per_second = settings.requests_per_second * 0.95
                logger.info(
                    f"请求速度大于预期，已调整为{round(settings.requests_per_second,2)} req/s"
                )
                flush = True

        if log_infos.toc - log_infos.tic > 60:
            flush = True

        if flush:
            log_infos.reset(json_datas)

        await asyncio.sleep(settings.log_interval_seconds)


async def main():
    global json_datas, cookies, log_infos, settings

    logger.imp_info("脚本开始运行")
    logger.imp_info(f"加载配置文件 {config_path}")
    logger.imp_info(f"日志输出到 {log_path}")

    try:
        if not os.path.exists(json_datas_path):
            raise ValueError
        json_datas = pickle.load(open(json_datas_path, "rb"))
        if len(json_datas) == 0:
            raise ValueError
    except Exception as e:
        logger.error("抢课列表为空")
        collect_now = input("你需要先手动选择要抢的课，是否现在开始选择（请确保你已经正确配置好 ruclogin） Y/n：")
        if collect_now.lower().startswith("y") or collect_now == "":
            json_datas = collect.main()
            if len(json_datas) == 0:
                logger.error("抢课列表为空")
                logger.imp_info("脚本已停止")
                exit(1)
        else:
            logger.imp_info("脚本已停止")
            exit(1)

    settings = Settings(config_path, json_datas)

    semester_code = json_datas[0]["jczy013id"]
    logger.imp_info(f"学期：{code2semester(semester_code)}")

    for json_data in json_datas:
        logger.imp_info(f"待抢课程：{json_data['ktmc_name']}")

    if settings.enabled_dynamic_requests and settings.target_requests_per_second > 50:
        logger.warning("动态调整对请求速度过高的情况不适用，请自行查看日志确认速率是否符合要求")
        settings.enabled_dynamic_requests = False

    if settings.target_requests_per_second > 300:
        logger.error("请求速度过高会导致意料外的问题，同时会给服务器正常运行带来压力，如果你清楚你在做什么，请自行修改源代码")
        logger.imp_info("脚本已停止")
        exit(1)

    if settings.gap == 0:
        logger.imp_info("gap=0，脚本将不间断执行")
    else:
        logger.imp_info(f"gap={settings.gap}，脚本将在每个小时的整{settings.gap}分钟执行")

    log_infos = Log_infomations(json_datas)

    cookies = get_cookies(domain="jw")
    stop_signal = asyncio.Event()
    asyncio.create_task(log(stop_signal))

    while True:
        if settings.gap > 0:
            current = datetime.now()
            next_min = settings.gap - 1 - current.minute % settings.gap
            next_sec = 45 - current.second
            wait_time = next_min * 60 + next_sec

            if wait_time > 0 and wait_time < settings.gap * 60 - 30:
                stop_signal.set()
                logger.info(
                    "wait, until " + str(current + timedelta(seconds=wait_time))
                )
                while wait_time > 5:
                    if not check_cookies(cookies, domain="jw"):
                        logger.warning("cookie失效")
                        cookies = get_cookies(domain="jw", cache=False)
                    await asyncio.sleep(5)
                    wait_time -= 5
                await asyncio.sleep(wait_time)
                wait_time = 0
                stop_signal.clear()
                asyncio.create_task(log(stop_signal))

        for _ in range(10):  # 减少检查时间的次数
            for json_data in json_datas:
                asyncio.create_task(grab(json_data))
                await asyncio.sleep(1 / settings.requests_per_second)


def run():
    global cookies
    for _ in range(10):
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.imp_info("脚本已停止")
            exit(0)
        except Exception as e:
            try:
                if not check_cookies(cookies, domain="jw"):
                    logger.warning("cookie失效")
                    continue
            except NameError:
                pass
            raise e


__doc__ = """
Usage:
    main.py
    main.py [--verbose] [--recollect] 
    main.py -h | --help
    main.py -V

Options:
    -h --help           Show this screen.
    --verbose           Show more information.
    --recollect         Recollect courses.
    -V                  Show version information.
"""


def entry_point():
    args = docopt(__doc__, version="0.1.0")
    if args["-V"]:
        print(f"配置文件路径：{config_path}")
        print(f"日志输出到 {log_path}")
    else:
        if args["--verbose"]:
            console_hd.setLevel(logging.INFO)
        if args["--recollect"]:
            collect.main()
        run()


if __name__ == "__main__":
    entry_point()
