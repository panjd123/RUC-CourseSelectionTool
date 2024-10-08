import asyncio
import json
import logging
import os
import os.path as osp
from datetime import datetime, timedelta
from timeit import default_timer as timer

import aiohttp

from docopt import docopt
from ruclogin import *

if __name__ == "__main__":  # 并不是一种优雅的写法，待改进
    import collect
    from settings import Settings
else:
    from . import collect
    from .settings import Settings

ROOT = osp.dirname(osp.abspath(__file__))


LOG_PATH = osp.join(ROOT, "ruccourse.log")
CONFIG_PATH = osp.join(ROOT, "config.ini")
OLD_PKL_PATH = osp.join(ROOT, "json_datas.pkl")
COURSES_PATH = osp.join(ROOT, "courses.json")
RING_PATH = osp.join(ROOT, "ring.wav")

settings = Settings(CONFIG_PATH)

try:
    from simpleaudio import WaveObject

except ImportError:

    class WaveObject:
        @classmethod
        def from_wave_file(cls, *args, **kwargs):
            global logger
            if not settings.silent:
                logger.error(
                    "simpleaudio 未安装，无法播放提示音，请 pip install simpleaudio"
                )
            return None


IMPORTANT_INFO = 25
logging.addLevelName(IMPORTANT_INFO, "IMPORTANT_INFO")
logger = logging.getLogger(__name__)


def imp_info(self, message, *args, **kwargs):
    if self.isEnabledFor(IMPORTANT_INFO):
        self._log(IMPORTANT_INFO, message, args, **kwargs)


logging.Logger.imp_info = imp_info
logger.setLevel(logging.INFO)
file_hd = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
file_hd.setLevel(logging.INFO)
file_hd.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
console_hd = logging.StreamHandler()
console_hd.setLevel(IMPORTANT_INFO)
console_hd.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_hd)
logger.addHandler(console_hd)
json_datas = []


class Player(object):
    def __init__(self, path, silent=False) -> None:
        self.wave_obj = WaveObject.from_wave_file(path)
        self.play_obj = None
        self.silent = silent

    def play(self):
        if self.silent:
            return
        if self.play_obj is not None:
            self.play_obj.stop()
        if self.wave_obj is not None:
            self.play_obj = self.wave_obj.play()

    def is_playing(self):
        if self.play_obj is None:
            return False
        return self.play_obj.is_playing()

    def stop(self):
        if self.play_obj is not None:
            self.play_obj.stop()


class Log_infomations(object):
    tic: float
    toc: float
    total_requests: int
    report_requests: int
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

    def update(self, cls_name, errorCode):
        global rejectErrorCode
        self.course_info[cls_name]["total"] += 1
        self.total_requests += 1
        self.report_requests += 1
        self.iter_requests += 1
        if errorCode == "eywxt.save.stuLimit.error":
            pass
        elif (
            errorCode == "success"
            or errorCode == "eywxt.save.msLimit.error"
            or errorCode == "eywxt.save.cantXkByCopy.error"
        ):
            del log_infos.course_info[cls_name]
        else:
            self.iter_reject_requests += 1
            self.course_info[cls_name]["reject"] += 1

    def __init__(self, json_datas) -> None:
        self.reset(json_datas)
        self.total_requests = 0
        self.report_requests = 0


rejectErrorCode = set(
    ["服务器繁忙，请稍后再试！", "正在准备数据，请稍后重试...", "选课已结束！"]
)
processedClasses = set()


async def success_report():
    try:
        global settings
        if settings.share:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.get(
                    f"https://ruccourse.panjd.net/success_report?count=1"
                ) as response:
                    pass
    except NameError:
        pass


async def request_report():
    try:
        global log_infos, settings
        if settings.share:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.get(
                    f"https://ruccourse.panjd.net/request_report?count={log_infos.report_requests}"
                ) as response:
                    pass
    except NameError:
        pass


async def grab(json_data):
    global cookies, json_datas, log_infos, rejectErrorCode, player
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
            if errorCode == "success":
                asyncio.create_task(success_report())
                if cls_name not in processedClasses:
                    logger.imp_info(f"抢到 {cls_name}")
                    processedClasses.add(cls_name)
                json_datas.remove(json_data)
                player.play()
            elif errorCode == "eywxt.save.msLimit.error":
                if cls_name not in processedClasses:
                    logger.imp_info(f"{cls_name} 有名额，但同类别已选数目达到上限")
                    processedClasses.add(cls_name)
                json_datas.remove(json_data)
                player.play()
            elif errorCode in rejectErrorCode:
                logger.debug(f"{cls_name} 服务器拒绝响应，errorCode：{errorCode}")
            elif errorCode == "eywxt.save.cantXkByCopy.error":
                if cls_name not in processedClasses:
                    logger.imp_info(f"{cls_name} 已选，跳过")
                    processedClasses.add(cls_name)
                json_datas.remove(json_data)
            elif errorCode != "eywxt.save.stuLimit.error":
                rejectErrorCode.add(errorCode)
                logger.warning(
                    f"未知 errCode：{errorCode}，将视该 errorCode 为服务器拒绝响应，请根据请求速度等信息判断是否会影响抢课"
                )
                logger.warning(f"Response: {result}")
            log_infos.update(cls_name, errorCode)
            return [cls_name, errorCode]


async def log(stop_signal):
    global log_infos, settings, json_datas
    log_infos.reset(json_datas)
    await asyncio.sleep(1)
    while not stop_signal.is_set():
        log_infos.toc = timer()
        reqs = log_infos.iter_requests / (log_infos.toc - log_infos.tic)
        tru_reqs = (log_infos.iter_requests - log_infos.iter_reject_requests) / (
            log_infos.toc - log_infos.tic
        )
        rej_ratio = log_infos.iter_reject_requests / log_infos.iter_requests

        worst_reqs = float("inf")
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

        if (
            worst_reqs < settings.reject_warning_threshold / len(json_datas)
            and log_infos.toc - log_infos.tic > 5
        ):
            if log_infos.iter_reject_requests == log_infos.iter_requests:
                logger.warning(f"所有请求被拒绝，请检查是否处于选课时间")
            else:
                logger.warning(
                    f"{str(round(rej_ratio*100,2))+'%':<5} 的请求被拒绝，真实请求速度为 {round(tru_reqs,2):<5} req/s，其中最低请求速度的课程为 {round(worst_reqs,2):<5} req/s"
                )

        logger.info(
            f"req/s: {round(reqs, 2):<5}\ttru_reqs/s: {round(tru_reqs,2):<5}\ttotal: {log_infos.total_requests}"
        )

        flush = False
        if settings.enabled_dynamic_requests and log_infos.toc - log_infos.tic > 5:
            if tru_reqs < settings.target_requests_per_second * 0.9:
                settings.requests_per_second = settings.requests_per_second * 1.05
                logger.info(
                    f"请求速度小于预期，已调整为{round(settings.requests_per_second,2):<6} req/s"
                )
                flush = True
            if tru_reqs > settings.target_requests_per_second * 1.1:
                settings.requests_per_second = settings.requests_per_second * 0.95
                logger.info(
                    f"请求速度大于预期，已调整为{round(settings.requests_per_second,2)} req/s"
                )
                flush = True

        if log_infos.toc - log_infos.tic > 60:
            flush = True

        if flush:
            log_infos.reset(json_datas)

        if log_infos.report_requests > 10000:
            await request_report()
            log_infos.report_requests = 0

        await asyncio.sleep(settings.log_interval_seconds)


async def main():
    global json_datas, cookies, log_infos, settings, player

    logger.imp_info("脚本开始运行")
    logger.imp_info(
        f"如果你喜欢这个项目，欢迎给项目点个 star ：https://github.com/panjd123/RUC-CourseSelectionTool"
    )
    logger.imp_info(f"配置文件路径：{CONFIG_PATH}")
    logger.imp_info(f"抢课列表路径：{COURSES_PATH}")
    logger.imp_info(f"日志文件路径：{LOG_PATH}")

    player = Player(RING_PATH, silent=settings.silent)

    try:
        if os.path.exists(COURSES_PATH):
            logger.imp_info(f"正在读取抢课列表: {COURSES_PATH}")
            with open(COURSES_PATH, "r", encoding="utf-8") as f:
                json_datas = json.loads(f.read())
        elif os.path.exists(OLD_PKL_PATH):
            logger.imp_info(f"正在读取旧格式抢课列表: {OLD_PKL_PATH}")
            json_datas = collect.migrate_old_pkl()

        if len(json_datas) == 0:
            raise ValueError
    except Exception:
        logger.error("抢课列表为空")
        collect_now = input(
            "你需要先手动选择要抢的课，是否现在开始选择（请确保你已经正确配置好 ruclogin） Y/n："
        )
        if collect_now.lower().startswith("y") or collect_now == "":
            json_datas = collect.collect_courses()
            if len(json_datas) == 0:
                logger.error("抢课列表为空")
                logger.imp_info("脚本已停止")
                exit(1)
        else:
            logger.imp_info("脚本已停止")
            exit(1)

    if settings.silent:
        logger.imp_info(f"不启用提示铃声")
    else:
        logger.imp_info(f"启用提示铃声")
        logger.imp_info(f"铃声文件路径：{RING_PATH}")

    semester_code = json_datas[0]["jczy013id"]
    logger.imp_info(f"学期：{code2semester(semester_code)}")

    if settings.target_requests_per_second > 100:
        logger.error(
            f"请求速度过高（{settings.target_requests_per_second }> 100）会导致意料外的问题，同时会给服务器正常运行带来压力，如果你清楚你在做什么，请自行修改源代码"
        )
        logger.imp_info("脚本已停止")
        request_report()
        exit(1)

    if settings.enabled_dynamic_requests and settings.target_requests_per_second > 30:
        logger.warning(
            f"动态调整对请求速度过高的情况（{settings.target_requests_per_second }> 30）不适用，请自行查看日志确认速率是否符合要求"
        )
        settings.enabled_dynamic_requests = False

    if settings.gap == 0:
        logger.imp_info("gap=0，脚本将不间断执行")
    else:
        logger.imp_info(
            f"gap={settings.gap}，脚本将在每个小时的整{settings.gap}分钟执行"
        )

    for json_data in json_datas:
        logger.imp_info(f"待抢课程：{json_data['ktmc_name']}")

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

            if 0 < wait_time < settings.gap * 60 - 30:
                stop_signal.set()
                logger.info(
                    "等待中，下次启动时间为："
                    + str(current + timedelta(seconds=wait_time))
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
            if len(json_datas) == 0:
                logger.imp_info("抢课列表为空")
                logger.imp_info("脚本已停止")
                await request_report()
                exit(0)


def run(debug=False):
    global cookies
    for _ in range(10):
        try:
            asyncio.run(main())
        except KeyboardInterrupt as esc:
            asyncio.run(request_report())
            raise KeyboardInterrupt from esc
            # logger.imp_info("脚本已停止")
            # exit(0)
        except Exception as e:
            try:
                if not check_cookies(cookies, domain="jw"):
                    logger.warning("cookie失效")
                    continue
            except NameError:
                pass
            asyncio.run(request_report())
            if debug:
                raise e
            logger.error(f"脚本遇到未知错误：{e}，重试")
    logger.error(f"脚本因未知错误导致 {e} 的重试次数过多，已停止")
    asyncio.run(request_report())
    exit(1)


__doc__ = """
Usage:
    main.py
    main.py [--verbose] [--recollect] [--debug]
    main.py -h | --help
    main.py -V

Options:
    -h --help           Show this screen.
    --verbose           Show more information.
    --recollect         Recollect courses.
    -V                  Show information.
"""


def entry_point():
    args = docopt(__doc__)
    if args["-V"]:
        print(f"配置文件路径：{CONFIG_PATH}")
        print(f"抢课列表路径：{COURSES_PATH}")
        print(f"日志文件路径：{LOG_PATH}")
        print(f"铃声文件路径：{RING_PATH}")
    else:
        if args["--verbose"]:
            console_hd.setLevel(logging.INFO)
        if args["--debug"]:
            file_hd.setLevel(logging.DEBUG)
            console_hd.setLevel(logging.DEBUG)
        if args["--recollect"]:
            collect.collect_courses()
        run()


if __name__ == "__main__":
    entry_point()
