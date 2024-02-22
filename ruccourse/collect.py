import os
import os.path as osp
from json import dumps, loads

from ruclogin import RUC_LOGIN
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        WebDriverException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

ROOT = osp.dirname(osp.abspath(__file__))

old_pkl_path = osp.join(ROOT, "json_datas.pkl")
COURSES_PATH = osp.join(ROOT, "courses.json")


def collect_courses():
    input("请等待脚本输出“等待浏览器被关闭...”后，再开始选择课程，选择后关闭浏览器。按回车键继续...")
    login = RUC_LOGIN(debug=True)
    login.initial_login("jw")
    login.login()
    driver = login.driver
    wait = WebDriverWait(driver, 10)

    def try_click(wait, by, value):
        ele = wait.until(EC.element_to_be_clickable((by, value)))
        while True:
            try:
                ele.click()
            except ElementClickInterceptedException:
                driver.implicitly_wait(0.1)
                continue
            break
        return ele

    try_click(
        wait,
        By.XPATH,
        '//*[@id="app"]/div[2]/div[1]/div/div[3]/div[1]/div/ul/div/li[1]/div',
    )
    try_click(
        wait,
        By.XPATH,
        '//*[@id="app"]/div[2]/div[1]/div/div[3]/div[1]/div/ul/div/li[1]/ul/div/li[2]',
    )
    try_click(
        wait,
        By.XPATH,
        '//*[@id="app"]/div[2]/div[2]/div/div[1]/div/div[1]/div/div/div/div[2]/button[1]',
    )

    driver.switch_to.window(driver.window_handles[-1])
    del driver.requests
    print("在浏览器里，选一遍所有你想选的课程（请确保返回成功或选课人数已经到达上限，而不是时间冲突！！！）")
    print("等待浏览器被关闭...")
    while True:
        try:
            driver.current_url
        except WebDriverException:
            json_datas = []
            for request in driver.requests:
                if request.path.endswith("saveStuXkByRmdx"):
                    data = request.body.decode("utf-8")
                    d = loads(data)
                    json_datas.append(d)
            with open(COURSES_PATH, "w") as f:
                f.write(dumps(json_datas, ensure_ascii=False, indent=4))
            print("你选择的课程是：", " ".join(
                [data["ktmc_name"] for data in json_datas]))
            return json_datas
        driver.implicitly_wait(0.1)


def migrate_old_pkl():
    try:
        import pickle
        with open(old_pkl_path, "rb") as f:
            data = pickle.load(f)
        with open(COURSES_PATH, "w", encoding='utf-8') as f:
            f.write(dumps(data, ensure_ascii=False, indent=4))
    except FileNotFoundError:
        return None

    # remove old pkl file
    try:
        os.remove(old_pkl_path)
    except FileNotFoundError:
        pass

    return data


if __name__ == "__main__":
    collect_courses()
