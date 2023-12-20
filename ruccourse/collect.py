from ruclogin import RUC_LOGIN
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    WebDriverException,
)
import pickle
import os.path as osp


def main():
    ROOT = osp.dirname(osp.abspath(__file__))

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
        except WebDriverException as e:
            json_datas = []
            for request in driver.requests:
                if request.path.endswith("saveStuXkByRmdx"):
                    data = request.body.decode("utf-8")
                    data = data.replace("null", "None")
                    data = data.replace("false", "False")
                    data = data.replace("true", "True")
                    d = eval(data)
                    json_datas.append(d)
            pickle.dump(json_datas, open(osp.join(ROOT, "json_datas.pkl"), "wb"))
            print("你选择的课程是：", " ".join([data["ktmc_name"] for data in json_datas]))
            return json_datas
        driver.implicitly_wait(0.1)


if __name__ == "__main__":
    main()
