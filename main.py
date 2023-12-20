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

IMPORTANT_INFO = 25
logging.addLevelName(IMPORTANT_INFO, "IMPORTANT_INFO")
logger = logging.getLogger(__name__)


def imp_info(self, message, *args, **kwargs):
    if self.isEnabledFor(IMPORTANT_INFO):
        self._log(IMPORTANT_INFO, message, args, **kwargs)


logging.Logger.imp_info = imp_info
logger.setLevel(logging.INFO)
file_hd = logging.FileHandler("ruccourse.log", mode="a", encoding="utf-8")
file_hd.setLevel(logging.INFO)
file_hd.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
console_hd = logging.StreamHandler()
console_hd.setLevel(IMPORTANT_INFO)
console_hd.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_hd)
logger.addHandler(console_hd)
logger.imp_info("脚本开始运行")

config = ConfigParser()
config.read("config.ini", encoding="utf-8")

semester = config["DEFAULT"]["semester"]
enabled_dynamic_requests = config["DEFAULT"].getboolean("enabled_dynamic_requests")
target_requests_per_second = int(config["DEFAULT"]["requests_per_second"])
gap = int(config["DEFAULT"]["gap"])
stage = int(config["DEFAULT"]["stage"])
log_interval_seconds = int(config["DEFAULT"]["log_interval_seconds"])

if not os.path.exists("json_datas.pkl"):
    logger.error("未找到抢课列表，请先执行 collect.py 抓包")
    logger.imp_info("脚本已停止")
    exit(1)

try:
    json_datas: list = pickle.load(open("json_datas.pkl", "rb"))
    if len(json_datas) == 0:
        raise ValueError
except Exception as e:
    logger.error("抢课列表为空")
    logger.imp_info("脚本已停止")
    exit(1)

if semester:
    semester_code = semester2code(semester)
    logger.imp_info(f"学期：{semester}")
else:
    semester_code = json_datas[0]["jczy013id"]
    logger.imp_info(f"自动获取学期：{code2semester(semester_code)}")

for json_data in json_datas:
    logger.imp_info(f"待抢课程：{json_data['ktmc_name']}")

if stage != 0:
    for i in range(len(json_datas)):
        json_datas[i]["xkfs_name"] = stage

requests_per_second = target_requests_per_second

if enabled_dynamic_requests and target_requests_per_second > 50:
    logger.warning("动态调整对请求速度过高的情况不适用，请自行查看日志确认速率是否符合要求")
    enabled_dynamic_requests = False

if gap == 0:
    logger.imp_info("gap=0，脚本将不间断执行")
else:
    logger.imp_info(f"gap={gap}，脚本将在每个小时的整{gap}分钟执行")

total_requests = 0  # 总请求数
iter_requests = 0
iter_reject_requests = 0
tic = 0

cookies = {}


async def grab(json_data):
    global cookies, json_datas, total_requests, iter_requests, iter_reject_requests
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
            "eywxt.save.msLimit.error"  # 已选课数目达到类别上限
            "服务器繁忙，请稍后再试！"  # 服务器繁忙，请稍后再试！
            if errorCode == "success":
                logger.imp_info(f"抢到 {cls_name}")
                json_datas.remove(json_data)
            elif errorCode == "eywxt.save.msLimit.error":
                logger.imp_info(f"{cls_name} 有名额，但已选课数目达到类别上限")
                json_datas.remove(json_data)
            elif errorCode == "服务器繁忙，请稍后再试！":
                iter_reject_requests += 1
            if len(json_datas) == 0:
                logger.imp_info("抢课列表为空")
                logger.imp_info("脚本已停止")
                exit(0)
            total_requests += 1
            iter_requests += 1
            return [cls_name, errorCode]


async def grab_all():
    global json_datas
    coroutines = [grab(json_data) for json_data in json_datas]
    results = await asyncio.gather(*coroutines)
    return results


async def log(stop_signal):
    global tic, total_requests, iter_requests, iter_reject_requests, requests_per_second
    tic = timer()
    iter_requests = 0
    iter_reject_requests = 0
    await asyncio.sleep(1)
    while not stop_signal.is_set():
        toc = timer()
        reqs = iter_requests / (toc - tic)
        tru_reqs = (iter_requests - iter_reject_requests) / (toc - tic)
        rej_ratio = iter_reject_requests / iter_requests
        if rej_ratio > 0.1:
            logger.warning(
                f"{round(iter_reject_requests/iter_requests*100,3)}% 的请求被拒绝，真实请求速度为 {round(tru_reqs,3)} req/s"
            )
        logger.info(
            f"req/s: {round(reqs, 3)}\ttru_reqs/s: {round(tru_reqs,3)}\ttotal: {total_requests}"
        )

        if enabled_dynamic_requests:
            if tru_reqs < target_requests_per_second * 0.9 and toc - tic > 5:
                requests_per_second = requests_per_second * 1.05
                logger.info(f"请求速度小于预期，已调整为{round(requests_per_second,2)} req/s")
                tic = toc
                iter_requests = 0
                iter_reject_requests = 0
            if tru_reqs > target_requests_per_second * 1.1 and toc - tic > 5:
                requests_per_second = requests_per_second * 0.95
                logger.info(f"请求速度大于预期，已调整为{round(requests_per_second,2)} req/s")
                tic = toc
                iter_requests = 0
                iter_reject_requests = 0

        await asyncio.sleep(log_interval_seconds)


async def main():
    global json_datas, cookies, tic, requests_per_second
    cookies = get_cookies(domain="jw")
    stop_signal = asyncio.Event()
    asyncio.create_task(log(stop_signal))

    while True:
        if gap > 0:
            current = datetime.now()
            next_min = gap - 1 - current.minute % gap
            next_sec = 45 - current.second
            wait_time = next_min * 60 + next_sec

            if wait_time > 0 and wait_time < gap * 60 - 30:
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
            asyncio.create_task(grab_all())
            await asyncio.sleep(len(json_datas) / requests_per_second)


if __name__ == "__main__":
    for _ in range(10):
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.imp_info("脚本已停止")
            exit(0)
        except Exception as e:
            if not check_cookies(cookies, domain="jw"):
                logger.warning("cookie失效")
            else:
                logger.error(e)
