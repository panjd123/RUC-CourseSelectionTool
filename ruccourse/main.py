import asyncio
import json
import logging
import os
import os.path as osp
from datetime import datetime, timedelta
from timeit import default_timer as timer
import uuid

import aiohttp

import argparse
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
COURSES_PATH = osp.join(ROOT, "courses.json")
HEADERS_PATH = osp.join(ROOT, "headers.json")
RING_PATH = osp.join(ROOT, "ring.wav")
REQUESTS_THRESHOLD = 10
REQUESTS_HARD_THRESHOLD = REQUESTS_THRESHOLD * 1.5
DYNAMIC_REQUESTS_THRESHOLD = 20
WARMUP_SECONDS = 20
STATS_INTERVAL = 600

STATS_URL = "https://ruccourse.panjd.net"

UUID = str(uuid.uuid1())

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
logger.setLevel(logging.DEBUG)
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
    report_tic: float
    report_toc: float
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
        self.report_tic = self.report_toc = timer()


rejectErrorCode = set(
    ["服务器繁忙，请稍后再试！", "正在准备数据，请稍后重试...", "选课已结束！"]
)
processedClasses = set()


async def success_report():
    try:
        global settings, UUID, logger
        if settings.stats:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                uri = f"/suceess_report?count=1&uuid={UUID}"
                async with session.get(STATS_URL + uri) as response:
                    logger.info(f"{uri}: {await response.text()}")
    except NameError:
        pass


async def request_report():
    try:
        global log_infos, settings, UUID, logger
        if settings.stats:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                uri = f"/request_report?count={log_infos.report_requests}&uuid={UUID}"
                async with session.get(STATS_URL + uri) as response:
                    logger.info(f"{uri}: {await response.text()}")
    except NameError:
        pass


async def grab(json_data):
    global cookies, json_datas, log_infos, rejectErrorCode, player, headers
    url = "https://jw.ruc.edu.cn/resService/jwxtpt/v1/xsd/stuCourseCenterController/saveStuXkByRmdx"
    params = {
        "resourceCode": "XSMH0303",
        "apiCode": "jw.xsd.courseCenter.controller.StuCourseCenterController.saveStuXkByRmdx",
    }

    now_headers = headers.copy()
    now_headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "TOKEN": cookies["token"],
        }
    )

    async with aiohttp.ClientSession(
        cookies={"SESSION": cookies["SESSION"]}
    ) as session:
        async with session.post(
            url, params=params, json=json_data, headers=now_headers
        ) as response:
            result = await response.json()
            errorCode = result["errorCode"]
            cls_name = json_data["ktmc_name"]
            if errorCode == "success":
                if cls_name not in processedClasses:
                    logger.imp_info(f"选到 {cls_name}")
                    processedClasses.add(cls_name)
                    await success_report()
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
                    f"未知 errCode：{errorCode}，将视该 errorCode 为服务器拒绝响应，请根据请求速度等信息判断是否会影响选课"
                )
                logger.warning(f"Response: {result}")
            log_infos.update(cls_name, errorCode)
            return [cls_name, errorCode]


async def log(stop_signal):
    global log_infos, settings, json_datas
    log_infos.reset(json_datas)
    await asyncio.sleep(1)
    while not stop_signal.is_set():
        log_infos.report_toc = log_infos.toc = timer()
        reqs = log_infos.iter_requests / (log_infos.toc - log_infos.tic)
        tru_reqs = (log_infos.iter_requests - log_infos.iter_reject_requests) / (
            log_infos.toc - log_infos.tic
        )
        rej_ratio = (
            log_infos.iter_reject_requests / log_infos.iter_requests
            if log_infos.iter_requests != 0
            else 0
        )

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
                if settings.requests_per_second < REQUESTS_HARD_THRESHOLD:
                    settings.requests_per_second = settings.requests_per_second * 1.05
                    logger.info(
                        f"真实请求速度小于预期，已调整为{round(settings.requests_per_second,2):<6} req/s"
                    )
                    flush = True
                else:
                    logger.info(
                        f"真实请求速度小于预期，但是请求速度已经超过硬限制 {REQUESTS_HARD_THRESHOLD}，取消动态调整"
                    )
            if tru_reqs > settings.target_requests_per_second * 1.1:
                settings.requests_per_second = settings.requests_per_second * 0.95
                logger.info(
                    f"真实请求速度大于预期，已调整为{round(settings.requests_per_second,2)} req/s"
                )
                flush = True

        if log_infos.toc - log_infos.tic > 60:
            flush = True

        if flush:
            log_infos.reset(json_datas)

        if (
            log_infos.report_requests > 10000
            or log_infos.report_toc - log_infos.report_tic > STATS_INTERVAL
        ):
            await request_report()
            log_infos.report_requests = 0
            log_infos.report_tic = log_infos.report_toc = timer()

        await asyncio.sleep(settings.log_interval_seconds)


async def main(warmup=False):
    global json_datas, cookies, log_infos, settings, player, headers

    logger.imp_info(
        "已知有同学因为使用本脚本被封号，如果你不理解这个脚本的原理，不能自行判断风险，你不应该使用这个脚本"
    )
    if input("我已经阅读并理解上述内容，继续？ Y/n：").lower().startswith("n"):
        logger.imp_info("脚本已停止")
        exit(0)
    logger.imp_info("脚本开始运行")
    logger.imp_info(
        f"如果你喜欢这个项目，欢迎给项目点个 star ：https://github.com/panjd123/RUC-CourseSelectionTool"
    )
    logger.imp_info(f"配置文件路径：{CONFIG_PATH}")
    logger.imp_info(f"选课列表路径：{COURSES_PATH}")
    logger.imp_info(f"日志文件路径：{LOG_PATH}")

    player = Player(RING_PATH, silent=settings.silent)

    try:
        logger.imp_info(f"正在读取选课列表: {COURSES_PATH}")
        with open(COURSES_PATH, "r", encoding="utf-8") as f:
            json_datas = json.loads(f.read())
        if osp.exists(HEADERS_PATH):
            with open(HEADERS_PATH, "r", encoding="utf-8") as f:
                headers = json.loads(f.read())
                # fmt: off
                keys = [
                    "Accept", "Accept-Language", "Cache-Control", "Connection", "Content-Type", "Origin",
                    "Pragma", "Referer", "Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site",
                    "Simulated-By", "TOKEN", "User-Agent", "X-Requested-With", "app",
                    "locale", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "userAgent", "userRoleCode",
                ]
                # fmt: on
                headers = {k: headers[k] for k in keys if k in headers}
        else:
            logger.warning(
                f"未找到 headers.json，使用默认 headers，这可能会增加被检测的风险"
            )
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            }
        if len(json_datas) == 0:
            raise ValueError
    except Exception:
        logger.error("选课列表为空")
        collect_now = input(
            "你需要先手动选择要选的课，是否现在开始选择（请确保你已经正确配置好 ruclogin） Y/n："
        )
        if collect_now.lower().startswith("y") or collect_now == "":
            json_datas = collect.collect_courses()
            if len(json_datas) == 0:
                logger.error("选课列表为空")
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

    if settings.target_requests_per_second > REQUESTS_THRESHOLD:
        logger.error(
            f"请求速度过高（{settings.target_requests_per_second }> {REQUESTS_THRESHOLD}）会给服务器正常运行带来压力，脚本默认不允许这样的请求速度"
        )
        logger.imp_info("脚本已停止")
        request_report()
        exit(1)

    if (
        settings.enabled_dynamic_requests
        and settings.target_requests_per_second > DYNAMIC_REQUESTS_THRESHOLD
    ):
        logger.warning(
            f"经验上，动态调整对请求速度过高的情况（{settings.target_requests_per_second } > {DYNAMIC_REQUESTS_THRESHOLD}）不适用，已禁用动态调整"
        )
        settings.enabled_dynamic_requests = False

    if settings.gap == 0:
        logger.error("gap=0，但是脚本默认不允许不间断执行，请考虑修改 gap=5")
        logger.imp_info("脚本已停止")
        exit(1)
    else:
        logger.imp_info(
            f"gap={settings.gap}，脚本将在每个小时的整{settings.gap}分钟执行"
        )

    for json_data in json_datas:
        logger.imp_info(f"待选课程：{json_data['ktmc_name']}")

    log_infos = Log_infomations(json_datas)

    cookies = get_cookies(domain="jw")
    stop_signal = asyncio.Event()
    asyncio.create_task(log(stop_signal))

    start = timer()

    while True:
        if settings.gap > 0 and not (warmup and timer() - start < WARMUP_SECONDS):
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

        # 约 2s 检查一次
        for _ in range(max(1, int(2 / len(json_datas) * settings.requests_per_second))):
            for json_data in json_datas:
                asyncio.create_task(grab(json_data))
                await asyncio.sleep(1 / settings.requests_per_second)
            if len(json_datas) == 0:
                logger.imp_info("选课列表已经为空")
                logger.imp_info("脚本停止中...")
                await request_report()
                logger.imp_info("脚本已停止")
                exit(0)


def run(debug=False, warmup=False):
    global cookies
    for _ in range(10):
        try:
            asyncio.run(main(warmup=warmup))
        except KeyboardInterrupt as esc:
            logger.imp_info("脚本停止中...")
            asyncio.run(request_report())
            if debug:
                raise esc
            logger.imp_info("脚本已停止")
            exit(0)
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
    logger.error(f"脚本因未知错误导致 {e} 的重试次数过多")
    logger.imp_info("脚本停止中...")
    asyncio.run(request_report())
    logger.imp_info("脚本已停止")
    exit(1)


def entry_point():
    parser = argparse.ArgumentParser()
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="Show more information.")
    parser.add_argument("--recollect", action="store_true", help="Recollect courses.")
    parser.add_argument("--debug", action="store_true", help="Show debug information.")
    parser.add_argument("-V", action="store_true", help="Show paths.")
    args = parser.parse_args()
    if args.V:
        print(f"配置文件路径：{CONFIG_PATH}")
        print(f"选课列表路径：{COURSES_PATH}")
        print(f"Headers文件路径：{HEADERS_PATH}")
        print(f"日志文件路径：{LOG_PATH}")
        print(f"铃声文件路径：{RING_PATH}")
    else:
        if args.verbose:
            console_hd.setLevel(logging.INFO)
        if args.debug:
            file_hd.setLevel(logging.DEBUG)
            console_hd.setLevel(logging.DEBUG)
        if args.recollect:
            collect.collect_courses()
        run(debug=args.debug, warmup=args.warmup)


if __name__ == "__main__":
    entry_point()
