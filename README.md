# ⚠️ 警告

已知教务处封禁了部分使用该脚本的人，并要求写检讨/报告，请自行判断并合理使用这个脚本。**如果你不理解这个脚本的原理，不能自行判断风险，你不应该使用这个脚本。使用本软件的风险应该由用户自行承担，我们不对因使用或依赖本软件所导致的任何直接或间接损失承担责任。**

----------

# 中国人民大学半自动化选课脚本 <img src="imgs/logo.png" width="100">

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

> 本脚本仅用于学习目的，其功能仅限自动化网页选课时的重复性的点击操作，不会对服务器产生额外的压力。禁止用于其他目的。使用本脚本的风险应该由用户自行承担，我们不对因使用或依赖本软件所导致的任何直接或间接损失承担责任。
>
> 请不要将本脚本用于恶意攻击（DDNS），这很愚蠢，也是违法的。

## Simple Usage

```bash
pip install ruccourse
# pip install ruccourse[all]  # 包含 simpleaudio，用于铃声提示
ruclogin                # only need to run once
ruccourse --verbose --warmup
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
2023-12-20 17:10:25,184 - ERROR - 选课列表为空
你需要先手动选择要选的课，是否现在开始选择（请确保你已经正确配置好 ruclogin） Y/n：
请等待脚本输出“等待浏览器被关闭...”后，再开始选择课程，选择后关闭浏览器。按回车键继续...
在浏览器里，选一遍所有你想选的课程（即使失败）
等待浏览器被关闭...
你选择的课程是： 信息检索导论01班
2023-12-20 17:10:25,185 - IMPORTANT_INFO - 学期：2023-2024学年夏季学期
2023-12-20 17:10:25,185 - IMPORTANT_INFO - 待选课程：信息检索导论01班
2023-12-20 17:10:25,185 - IMPORTANT_INFO - gap=0，脚本将不间断执行
2023-12-20 17:10:26,580 - INFO - req/s: 17.621  tru_reqs/s: 15.663      total: 18
2023-12-20 17:10:27,571 - INFO - req/s: 21.356  tru_reqs/s: 20.362      total: 43
2023-12-20 17:10:28,588 - INFO - req/s: 22.442  tru_reqs/s: 20.792      total: 68
2023-12-20 17:10:28,689 - IMPORTANT_INFO - 选到 信息检索导论01班
2023-12-20 17:10:28,919 - IMPORTANT_INFO - 脚本已停止
```

## Advanced Usage

- 见 `ruccourse --help`
- 默认情况下（即不加 `--verbose` 参数时）选到课或同类别选满会输出到控制台，速度监控会输出到文件，这样你可以一眼看出有没有选到课
- 配置文件中包含更多可设置量
- 特别地，如果你需要选课铃声提示功能，请手动 `pip install simpleaudio`，然后在配置文件中修改 `silent` 项

## Remind

- 拥有 cookies 相当于拥有微人大的完全访问权限，请不要和任何人分享。

   执行 `ruclogin --reset` 可以将所有信息初始化（包括配置文件内保存的用户名密码，以及缓存的 cookies）。

- 脚本默认会上传请求次数等信息到服务器，这些信息不包含个人隐私，将用于改进选课体验和便于脚本作者了解这个脚本的被使用情况，~~在被大规模使用前跑路~~。你可以在配置文件中关闭，但我认为：

    - 如果你有能力阅读源码，并判断出这个功能不会泄露你的个人隐私，那么你不需要关闭这个功能。
    - 如果你没有能力阅读源代码，那么你从一开始就不应该使用这个脚本，因为这个脚本高度涉及隐私。

- 当你通过 `pip install -U ruccourse` 更新脚本时，你的配置文件会被覆盖，请提前备份。值得备份的文件有 `config.ini` 和 `courses.json`，你可以通过 `ruccourse -V` 来检查他们的路径。

## Q&A

Q：有没有风险？

A：2024年前，答案是没有，2024年后，答案是有，而且已经有处罚案例。脚本默认参数是 2/s，同时脚本禁止过高的请求速度，除非你自己修改代码，从原理上，通过脚本和在网页上手动点击并无本质区别，但频率太高会对服务器产生巨大的压力。

> 补充1：其实脚本每次只发送选课请求而不请求其他 API，只要你的频率小于等于正常访问，你对服务器的压力比正常浏览器点击还低。
>
> 补充2：根据作者的统计，在处罚事件发送前的最近一次选课周期内，由该脚本发送的请求次数超过了数千万次，已经远远超过了合理的范围。

Q：如何更新选课列表，或者说想选别的课？

A：`ruccourse --recollect`

Q: 怎么检验选课脚本的效果？

A: 你可以 `ruccourse --recollect` 重新选一次课，并选择还有名额的课，同时在关闭浏览器前手动退选这门课。此时关闭浏览器，脚本开始运行，你应该会看到其显示选课成功，同时教务处网站也会显示你选到了这门课。

Q：运行一段时间后卡住，表现为不再输出日志？

A：期待有缘人修复 BUG，目前的解决方案是：已知微人大总是整 5 分钟放出课程，所以你可以定时重启本脚本。

Q：运行原理？

A：暴力发选课请求，直到选到，或者同类课达到选课上线。其实选课的实现不复杂，但是之前的测试表明，cookies 容易失效，所以现在配合 [ruclogin](https://github.com/panjd123/ruclogin) 可以保证选课不中断。

Q：为什么是半自动化？

A：选课请求里面有一大堆意义不明，命名不明的不知道怎么填，不填还会炸的参数，研究清楚太费劲，遂采用抓包的方法。

Q：控制台输出 “WARNING - 44.55% 的请求被拒绝，真实请求速度为 29.251 req/s，最低请求速度为 4.897 req/s”

A：系统有时候会返回“服务器繁忙，请稍后再试！”，这表示一个无效请求，当最低速度（对某课程）超过阈值时（比例 * 期望总请求速度 / 课程数），脚本会输出警报，你需要自行判断其程度是否会影响你的选课，比例可以在 `config.ini` 文件里调整。注意，如果你同时打开了动态调整请求速度，那么其调整的是真实请求速度，即被服务器正确处理的请求。

Q：怎么支持一上来就选课？

A：不支持，必须先抓包，一个可能的方法是提前抓包，下阶段选课，但是实测参数不同，你可以试试。

Q：服务器上怎么运行？

A：将本地的**选课列表文件** 和 **Headers文件**（运行时有输出其路径）上传到服务器对应目录下，其他类似。

Q: 遇到了其他报错。

A: 你或许需要先尝试 `ruclogin --debug` 排除获取 cookies 阶段的问题。接着你可以尝试更新脚本，新版本总是倾向于抛出错误供 debug，如果问题仍然存在，你可以用显示的报错提交 Issue。尽量不要直接联系原作者，因为原作者已经不再更新脚本，发布在 Issue 中更有可能得到其他开发者的帮助。发起 Issue 时注意隐私，不要泄露自己的 Cookies。

## 效果

选别人后阶段退的课，实际上这种名额挺多的，我选过：

- 社会主义500年
- 素质拓展
- 电影导论
- 后人类时代的全球影像
- 羽毛球

这些课最初的中签率都在 10% 到 30% 之间。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=panjd123/RUC-CourseSelectionTool&type=Date)](https://star-history.com/#panjd123/RUC-CourseSelectionTool&Date)

## Update

### 0.2.4

- 修复 gap 的误差

### 0.2.3

- 保证 stats 和日志的内容一致

### 0.2.2

- 修复选择 no 时不能直接退出的问题
- 修复 stats success 上传的问题

### 0.2.1

- 修复 stats 的上传频率

### 0.2.0

#### 请求速度方面 

- 修改了部分配置文件默认值，总体上大幅降低了请求速度
- 添加了动态调整请求速度时的速度上限
- 由于现在默认禁止 gap=0 不间断选课，增加了 `--warmup` 参数便于测试，其会在最初20秒时间内无间断运行，然后开始遵循 gap 参数

#### 其他方面

- 优化了脚本提示
- 修复了不能正常获取课程列表的问题
- 统计选课次数时额外上传了 `uuid.uuid1()` 以便区分不同用户

#### UUID

这个信息不会被用于追踪个人信息，统计是为了确认是否有人在不经意间发送了不合理的大量请求（比如由于误设置或者脚本BUG）。

其不能防止故意攻击，但是可以让所有脚本使用者自愿地互相监督和检查，以免被滥用。

### 0.1.11

- 更新到更现代的 pyproject.toml

### 0.1.10

- 删除 --debug 选项，去掉默认情况下大部分错误捕获以方便调试（相当于默认开启 --debug）

### 0.1.9

- 显式指定了 courses.json 的编码，防止跨系统时默认编码不一致导致的问题

### 0.1.8

- 删除了对 simpleaudio 的默认安装要求，因为安装这个包很容易报错
- 更新到用 json 格式存储抓包
- 实时上传选课次数

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
- 添加了选到课，或欲强课程有名额但同类名额到达上限时的声音提示功能，可以在配置文件中打开，默认关闭
- 增加了 `--debug` 参数，追踪报错信息
