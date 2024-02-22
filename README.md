# 中国人民大学半自动化抢课脚本

[![PyPI Downloads](https://img.shields.io/pypi/dm/ruccourse.svg?label=PyPI%20downloads)](
https://pypi.org/project/ruccourse/) [![GitHub Repo stars](https://img.shields.io/github/stars/panjd123/RUC-CourseSelectionTool?label=Github%20stars)](https://github.com/panjd123/RUC-CourseSelectionTool) 

**欢迎 Star！欢迎 pr！**

适用：时间优先选课阶段（即本学期末，下学期初）

支持：

- 请求速度控制
- 服务器运行
- 整点运行
- 自动重试
- 自动停止

## Simple Usage

```
pip install ruccourse
ruclogin                # only need to run once
ruccourse --verbose
```

> 关于 ruclogin 这个包，你可以查看 [ruclogin](https://github.com/panjd123/ruclogin) 的具体文档。

像这样，请注意，密码的输入不带回显（即不显示你输入的内容），你只需要直接输入，然后回车。

```
(base) PS D:\Code\RUC-CourseSelectionTool> pip install ruccourse
....

(base) PS D:\Code\ruclogin> ruclogin     
username, type enter to skip: 2021201212
password, type enter to skip: 
browser(Chrome/Edge/Chromium), type enter to skip:
driver_path, type enter to skip:

Config D:\Program\anaconda3\Lib\site-packages\ruclogin\config.ini updated:
        Username: 2021201212
        Password: ******
        Browser: Chrome
        driver_path: D:/Other/driver/chromedriver.exe


Test login? (Y/n):
你好, 信息学院 xxx from v.ruc.edu.cn
你好，xxx 图灵实验班（信息学拔尖人才实验班），你一共修了123学分，48门课，平均绩点3.9，专业排名第2名 from jw.ruc.edu.cn
driver init time: 4.749s
v.ruc.edu.cn get cookies time: 1.587s, check cookies time: 0.348s
jw.ruc.edu.cn get cookies time: 1.925s, check cookies time: 0.395s


(base) PS D:\Code\RUC-CourseSelectionTool> ruccourse --verbose
2023-12-20 17:10:25,184 - IMPORTANT_INFO - 脚本开始运行
2023-12-20 17:10:25,184 - IMPORTANT_INFO - 加载配置文件 D:\Program\anaconda3\Lib\site-packages\ruccourse\config.ini
2023-12-20 17:10:25,184 - IMPORTANT_INFO - 日志输出到 D:\Program\anaconda3\Lib\site-packages\ruccourse\ruccourse.log
2023-12-20 17:10:25,184 - ERROR - 抢课列表为空
你需要先手动选择要抢的课，是否现在开始选择（请确保你已经正确配置好 ruclogin） Y/n：
请等待脚本输出“等待浏览器被关闭...”后，再开始选择课程，选择后关闭浏览器。按回车键继续...
在浏览器里，选一遍所有你想选的课程（即使失败）
等待浏览器被关闭...
你选择的课程是： 信息检索导论01班
2023-12-20 17:10:25,185 - IMPORTANT_INFO - 学期：2023-2024学年夏季学期
2023-12-20 17:10:25,185 - IMPORTANT_INFO - 待抢课程：信息检索导论01班
2023-12-20 17:10:25,185 - IMPORTANT_INFO - gap=0，脚本将不间断执行
2023-12-20 17:10:26,580 - INFO - req/s: 17.621  tru_reqs/s: 15.663      total: 18
2023-12-20 17:10:27,571 - INFO - req/s: 21.356  tru_reqs/s: 20.362      total: 43
2023-12-20 17:10:28,588 - INFO - req/s: 22.442  tru_reqs/s: 20.792      total: 68
2023-12-20 17:10:28,689 - IMPORTANT_INFO - 抢到 信息检索导论01班
2023-12-20 17:10:28,919 - IMPORTANT_INFO - 脚本已停止
```

## Advanced Usage

- 见 `ruccourse --help`
- 默认情况下（即不加 `--verbose` 参数时）抢到课或同类别选满会输出到控制台，速度监控会输出到文件，这样你可以一眼看出有没有抢到课
- 配置文件中包含更多可设置量

## Remind

拥有 cookies 相当于拥有微人大的完全访问权限，请不要和任何人分享。

执行 `ruclogin --reset` 可以将所有信息初始化（包括配置文件内保存的用户名密码，以及缓存的 cookies）。

脚本默认会上传请求次数等信息到服务器，这些信息不包含个人隐私，将用于改进抢课体验（如开发不抓包，直接抢课）和便于脚本作者了解这个脚本的被使用情况，~~在被大规模使用前跑路~~。虽然你可以在配置文件中关闭，但我不建议没有能力阅读源码，自行判断这个功能是否会泄露个人隐私的非专业人士使用这个脚本，因为这个脚本高度涉及隐私。

## Q&A

Q：如何更新抢课列表，或者说想抢别的课？

A：`ruccouse --recollect`

Q: 怎么检验抢课脚本的效果？

A: 你可以 `ruccourse --recollect` 重新选一次课，并选择还有名额的课，同时在关闭浏览器前手动退选这门课。此时关闭浏览器，脚本开始运行，你应该会看到其显示抢课成功，同时教务处网站也会显示你抢到了这门课。

Q：运行原理？

A：暴力发选课请求，直到抢到，或者同类课达到选课上线。其实抢课的实现不复杂，但是之前的测试表明，cookies 容易失效，所以现在配合 [ruclogin](https://github.com/panjd123/ruclogin) 可以保证抢课不中断。

Q：有没有被检测的风险？

A：经过 2021-2023 年三年的尝试，1000/s 的请求速度都没有出现过问题，当然，没必要设这么高。脚本默认参数是 10/s，已经足够，同时脚本禁止过高的请求速度，如果你清楚你在做什么，请自行魔改源代码去掉这个限制。

Q：为什么是半自动化？

A：人大的教务系统写得“非常好”，抢课请求里面引入了一大堆意义不明，命名不明的不知道怎么填，不填还会炸的参数，研究清楚太费劲，遂采用抓包的方法。

Q：控制台输出 “WARNING - 44.55% 的请求被拒绝，真实请求速度为 29.251 req/s，最低请求速度为 4.897 req/s”

A：系统有时候会返回“服务器繁忙，请稍后再试！”，这表示一个无效请求，当最低速度（对某课程）超过阈值时（比例 * 期望总请求速度 / 课程数），脚本会输出警报，你需要自行判断其程度是否会影响你的抢课，比例可以在 `config.ini` 文件里调整。注意，如果你同时打开了动态调整请求速度，那么其调整的是真实请求速度，即被服务器正确处理的请求。

Q：怎么支持一上来就抢课？

A：不支持，必须先抓包，一个可能的方法是提前抓包，下阶段抢课，但是实测参数不同，你可以试试。

Q：服务器上怎么运行？

A：将本地的 json_datas.pkl 上传到服务器对应目录下，其他类似。

Q：怎么当作脚本运行？

A：`python /path/to/RUC-CourseSelectionTool/ruccourse/main.py`

Q: 遇到了其他报错。

A: 你可以尝试 `ruccourse --debug` 以抛出错误，在这之前，你或许需要先尝试 `ruclogin --debug` 排除获取 cookies 阶段的问题。如果你无法解决这个问题，可以提交 Issue。

## 效果

抢别人后阶段退的课，实际上这种名额挺多的，我抢过：

- 社会主义500年
- 素质拓展
- 电影导论
- 后人类时代的全球影像
- 羽毛球

这些课最初的中签率都在 10% 到 30% 之间。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=panjd123/RUC-CourseSelectionTool&type=Date)](https://star-history.com/#panjd123/RUC-CourseSelectionTool&Date)

## Update

### 0.1.7

- 优化了提示信息
- 修复了不能正常访问 [ruccourse.panjd.net](https://ruccourse.panjd.net) 的问题

### 0.1.6

- 为了避免这个脚本产生过大的影响，默认分享网络请求次数到 [ruccourse.panjd.net](https://ruccourse.panjd.net) 用以追踪脚本被滥用的情况（不涉及个人账户信息），如果你对相关隐私有所顾虑，可以在配置文件中关闭或者退回到 0.1.5 版本，你可以到 [RUC-CourseSelectionTool-stats](https://github.com/panjd123/RUC-CourseSelectionTool-stats) 查看服务端源代码
- 修复不能正常自动结束的问题
- ruclogin 已经适配最新教务网站

### 0.1.5

- 添加新 errorCode 处理

### 0.1.4

- 添加了对未知 errorCode 的处理
- 添加了抢到课，或欲强课程有名额但同类名额到达上限时的声音提示功能，可以在配置文件中打开，默认关闭
- 增加了 `--debug` 参数，追踪报错信息
