import requests
from bs4 import BeautifulSoup
import re
import json
import time
from prettytable import PrettyTable
from PIL import Image

from crack import Crack

class JZAssitant:

    _main_url = "http://125.89.69.234/"
    _login_url = _main_url+"default2.aspx"
    _validate_code_url = _main_url+"CheckCode.aspx?"
    _exam_url = _main_url+"xscj_gc.aspx?xh="
    _schedule_url = _main_url+"xskbcx.aspx?xh="
    _student_info_url = _main_url+"xsgrxx.aspx?"
    _course_category_url = _main_url+"xskc.aspx?xnxq="
    _elective_courses_url = _main_url+"xsxk.aspx?xh="
    _select_course_url = _main_url+"xsxjs.aspx?xkkh="

    def __init__(self, username, password):

        self._username = username
        self._password = password
        self._info = {}
        self._info["gnmkdm"] = "N121501"
        self._info["xnxq"] = "2016-20171"
        self._first_visit = True
        self._categories = None
        self._course_url_code = {}
        self._hidden_param = ''
        self._s = requests.Session()
        self._s.encoding = None
        self._s.headers.update({
            'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection':'keep-alive',
            'Content-Type':'application/x-www-form-urlencoded',
            'Referer':self._login_url,
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
        })
        

    def _get_validate_code(self):

        r = requests.get(JZAssitant._validate_code_url)
        self.cookies = r.cookies
        self._s.headers.update({
            'Cookie':r.headers.get("Set-Cookie"),
            })
        with open('code.png',    'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        
    def _get_viewstate(self, url, way="get", post_data=""):

        viewstate = ''

        if way == "get":
            r = self._s.get(url, headers=self._s.headers, cookies=self.cookies)
        elif way == "post":
            r = self._s.post(url, data=post_data, headers=self._s.headers, cookies=self.cookies)

        html = r.text
        m = re.search(r'input type="hidden" name="__VIEWSTATE" value="(.*)"', html)
        if m:
            viewstate = m.group(1)
        return viewstate

    def _login(self, validate_code):

        viewstate = self._get_viewstate(self._login_url)
        #print(viewstate)
        post_data = {
            '__VIEWSTATE': viewstate,
            'txtUserName': self._username,
            'TextBox2': self._password,
            'txtSecretCode': validate_code,
            'RadioButtonList1': "学生",
            'Button1': '',
            'lbLanguage': '',
            'hidPdrs': '',
            'hidsc': ''
            }
                
        try:
            r = self._s.post(self._login_url, headers=self._s.headers, data=post_data, cookies=self.cookies)
        except ConnectionError as e:
            print(e.strerror)

        msg = re.search(r"alert\('(.*?)'\)", r.text)
        if msg:
            return {"msg": msg.group(1)}

        if r.status_code == requests.codes.ok:
            soup = BeautifulSoup(r.text, "html.parser")
            r = soup.find(id="xhxm")
            dr = re.match(r'(.*?)同学', r.string)
            self._info["xm"] = dr.group(1)
            return {"status": 302}

    def _get_examination(self, year, semester):

        self._exam_url += self._username+"&xm="+self._info["xm"]+"&gnmkdm=N121605"
        viewstate = self._get_viewstate(self._exam_url)

        post_data = {
                "__VIEWSTATE": viewstate,
                "ddlXN": "",
                "ddlXQ": "",
                "Button1": ""
            }

        if year == None:
            post_data["Button1"] = "在校学习成绩查询"
        elif year and semester:
            post_data["ddlXN"] = year
            post_data["ddlXQ"] = semester
            post_data["Button1"] = "按学期查询"

        html = self._s.post(self._exam_url, data=post_data, headers=self._s.headers, cookies=self.cookies)
        soup = BeautifulSoup(html.text, "html.parser")
        table = soup.find(id="Datagrid1")
        trs = table.find_all("tr")
        title = ["学年", "学期", "课程代码", "课程名称", "课程性质", "课程归属", "学分", "绩点", "成绩", "辅修标记", "补考成绩", "重修成绩", "学院名称", "备注", "重修标记", "课程英文名称"]

        scores = []
        score_table = []

        for tr in trs:
            if 'class' in tr.attrs:
                if tr.attrs["class"] == ["datelisthead"]:
                    continue
            score_list = []
            tds = tr.find_all("td")
            for td in tds:
                score_list.append(td.text.replace("\xa0", ""))
            scores.append(dict(zip(title, score_list)))
            score_table.append(score_list)
        return {
            "scores": scores,
            "title": title,
            "score_table": score_table
        }

    def _get_schedule(self, year, semester):

        self._schedule_url = self._schedule_url+self._username+"&xm="+self._info["xm"]+"&gnmkdm=N121603"

        post_data = []
        if year == None:
            html = self._s.get(self._schedule_url, headers=self._s.headers, cookies=self.cookies)
        elif year and semester:
            viewstate = self._get_viewstate(self._schedule_url)
            post_data = {
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": viewstate,
                "xnd": year,
                "xqd": semester
            }

        html = self._s.post(self._schedule_url, data=post_data, headers=self._s.headers, cookies=self.cookies)
        soup = BeautifulSoup(html.text, "html.parser")
        trs = soup.find(id="Table1").find_all("tr")

        classes = []
        class_keys = ["name", "time", "teacher", "location", "detailed_time"]

        for tr in trs:
            tds = tr.find_all("td")
            for td in tds:
                if td.string == None:
                    td_string = td.renderContents().decode().replace("<br>", " ")
                    td_string = td_string.replace("</br>", "")
                    class_values = td_string.split(" ")

                    detailed_time = []
                    detailed_time.append(class_values[1][1])
                    detailed_time.append((class_values[1][3], class_values[1][5]))
                    detailed_time.append((class_values[1][9], class_values[1][11:13]))
                    if "单" in class_values[1]:
                        detailed_time.append("单")
                    elif "双" in class_values[1]:
                        detailed_time.append("双")
                    class_values.append(detailed_time)

                    class_dict = dict(zip(class_keys, class_values))
                    classes.append(class_dict)

        return classes

    def _get_elective_course(self, category=None):

        self._elective_courses_url = self._elective_courses_url+self._username+"&xm="+self._info["xm"]+"&gnmkdm="+self._info["gnmkdm"]
        html = self._s.get(self._elective_courses_url, headers=self._s.headers, cookies=self.cookies)
        soup = BeautifulSoup(html.text, "html.parser")
        self._info["zymc"] = soup.find(id="zymc").text

        viewstate = re.search(r'input type="hidden" name="__VIEWSTATE" value="(.*)"', html.text).group(1)

        post_data1 = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "zymc": self._info["zymc"],
            "xx": "",
            "Button2": "选修课程"
        }

        viewstate = self._get_viewstate(self._elective_courses_url, "post", post_data1)

        category = category+"||院公选课5"

        post_data2 = {
            "__EVENTTARGET": "zymc",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "zymc": category.encode(encoding='gb2312'),
            "xx": ""
        }

        html = self._s.post(self._elective_courses_url, data=post_data2, headers=self._s.headers, cookies=self.cookies)
        soup = BeautifulSoup(html.text, "html.parser")
        print("\n"+soup.find(id="Label4").string+"\n")
        num = int(re.search(r'共(\d*)条记录！', soup.find(id="Label4").string).group(1))

        m = re.findall(r'kcmcgrid\$_ctl\d*\$_ctl\d*', html.text)

        mark = 1
        self._courses = []

        while(True):

            table = soup.find(id="kcmcgrid")
            trs = table.find_all("tr")

            course_title = ["课程代码", "课程名称", "课程性质", "组或模块", "学分", "周学时", "考试时间", "课程介绍", "选否", "余量"]

            for tr in trs:

                if "class" in tr.attrs:
                    if tr.attrs["class"] == ["datelisthead"]:
                        continue
                if "nowrap" in tr.attrs:
                    continue

                tds = tr.find_all("td")

                course = []
                url_code = re.search(r'xkkh=(.*)&', tds[0].find("a").attrs["onclick"]).group(1)

                for item in tds:
                    course.append(item.text.replace("\xa0", ""))

                self._course_url_code[course[0]] = url_code
                self._courses.append(dict(zip(course_title, course)))

            if not len(m):
                break

            mark += 1
            viewstate = re.search(r'input type="hidden" name="__VIEWSTATE" value="(.*)"', html.text).group(1)
            post_data2["__VIEWSTATE"] = viewstate
            post_data2["__EVENTTARGET"] = m[0].replace('$', ':')
            del m[0]

            html = self._s.post(self._elective_courses_url, data=post_data2, headers=self._s.headers, cookies=self.cookies)
            soup = BeautifulSoup(html.text, "html.parser")

            if mark == 11:
                m = re.findall(r'kcmcgrid\$_ctl\d*\$_ctl\d*', html.text)
                num = 10-(num//10-9)
                m = [m[i] for i in range(0, len(m)) if i>num]

        return self._courses

    def _get_selective_course(self, url_code):

        self._select_course_url += url_code+"&xh="+self._username

        headers = self._s.headers
        if self._first_visit:
            headers["Cache-Control"] = "max-age=0"
        headers["Referer"] = self._select_course_url

        html = requests.get(self._select_course_url, headers=headers, cookies=self.cookies, allow_redirects=False)

        msg = re.search(r"alert\('(.*?)'\)", html.text)
        if msg:
            return {
                "msg": msg.group(1)
            }

        soup = BeautifulSoup(html.text, "html.parser")

        print("\n"+soup.find(id="Label1").string)
        course_name = re.search(r'课程名称：(.*)学分', soup.find(id="Label1").string).group(1).replace("\xa0", "")

        table = soup.find(id="xjs_table")
        trs = table.find_all("tr")

        option_title = ["教师姓名", "教学班/开课学院", "周学时", "考核", "上课时间", "上课地点", "校区", "备注", "授课方式", "是否短学期", "容量(人数)", "教材名称", "本专业已选人数", "所有已选人数", "选择情况"]
        option_code = []
        trs = []

        for tr in trs:

            if tr.string == None:

                tds = tr.find_all("td")
                first = True
                option = []

                for td in tds:
                    if first:
                        first = False
                        continue

                    radio = td.find("input")
                    if radio:
                        if "checked" in radio.attrs:
                            option.append("已选")
                        else:
                            option.append("未选")
                    else:
                        option.append(td.text.replace("\xa0", ""))

                option_code.append(tr.find("input").attrs["value"])
                trs.append(dict(zip(option_title, option)))

        return {
            "course_name": course_name,
            "option_code": option_code,
            "trs": trs
        }

    def _select_elective_course(self, course):
        
        self._select_course_url += course["url_code"]+"&xh="+self._username
        viewstate = self._get_viewstate(self._select_course_url)

        post_data = {
            "__EVENTTARGET": "Button1",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "xkkh": course["course_selection"],
            "RadioButtonList1": course["whether_booking"]
        }

        html = self._s.post(self._select_course_url, data=post_data, headers=self._s.headers, cookies=self.cookies)

        return re.search(r"alert\('(.*)'\)", html.text).group(1)

    def _get_course_category(self):

        self._course_category_url = self._course_category_url+self._info["xnxq"]+"&xh="+self._username
        html = self._s.get(self._course_category_url, headers=self._s.headers, cookies=self.cookies)
        soup = BeautifulSoup(html.text, "html.parser")

        table = soup.find(id="ListBox1")
        trs = table.find_all("option")
        self._categories = []

        for tr in trs:
            self._categories.append(tr.text)

        return self._categories
        
    def _get_student_info(self):
        self._student_info_url = self._student_info_url + "xh=" + self._username + "&xm=" + self._info["xm"] + "&gnmkdm=" + self._gnmkdm
        viewstate = self._get_viewstate(self._student_info_url)

        
if __name__ == '__main__':
    
    username = ''
    password = ''
    with open('user.txt', "r") as f:
        username = f.readline().strip()
        password = f.readline().strip()
        assitant = JZAssitant(username, password)

    crack = Crack()

    print("请输入验证码:")
    while True:

        assitant._get_validate_code()
        #code = input()
        code = "".join(crack.compare())
        ret = assitant._login(code)
        if "msg" in ret:
            print("登录失败，原因：%s" % ret["msg"])
            if "验证码" in ret["msg"]:
                print("已刷新验证码，请重新输入：")
            else:
                exit()
        elif "status" in ret:
            if ret["status"] == 302:
                print("登录成功！")
                break
        #print(is_successful)

    def get_year_and_semester():
        year = input()
        semester = ""
        if year:
            print("请输入学期(1:第一学期, 2:第二学期, 3:第三学期)")
            semester = input()
        return year, semester

    def query_exam_scores():

        print("请输入学年(可留空查询全部成绩或者按照右边的格式输入:2015-2016):")
        year, semester = get_year_and_semester()
        ret = assitant._get_examination(year, semester)

        pt = PrettyTable(ret["title"])

        for x in ret["score_table"]:
            pt.add_row(x)

        print(pt)
        #for item in scores:
        #    print(item)

    def query_schedule():

        print("请输入学年(可留空查询本学年课表或者按照右边的格式输入:2015-2016):")
        year, semester = get_year_and_semester()
        schedule = assitant._get_schedule(year, semester)
        print(schedule)

    def query_elective_course():

        if assitant._categories == None:
            categories = assitant._get_course_category()
        else:
            categories = assitant._categories

        print("")
        for index in range(len(categories)):
            print(str(index+1)+"："+categories[index])

        while True:
            print("\n请输入院公选课的课程分类序号(可留空查询院公选课全部课程):")

            i = input()
            if i:
                i = int(i)
            else:
                i = len(categories)

            courses = assitant._get_elective_course(categories[i-1])
            if len(courses) == 0:
                print("该分类下没有可供选择的课程")
            else:
                for item in courses:
                    print(item)
                break

        select_elective_course()

    def select_elective_course():

        while True:
            print("\n请输入院公选课的课程代码(或输入-1退出):")
            i = input()
            if i == "-1":
                return
            ret = assitant._get_selective_course(assitant._course_url_code[i])
            if "msg" in ret:
                print("\n"+ret["msg"])
            else:
                break

        wish = {}

        for index in range(len(ret["trs"])):
            print(str(index)+"："+str(ret["trs"][index]))

        print("\n请输入序号以添加指定班级(请确认是否与课表冲突):")
        course_selection = ret["option_code"][int(input())]

        print("请输入数字0或1以表示是否预订教材(0或留空:不预订，1:预订)")
        whether_booking = input()
        if whether_booking == "":
            whether_booking = "0"

        wish["course_name"] = ret["course_name"]
        wish["url_code"] = assitant._course_url_code[i]
        wish["whether_booking"] = whether_booking
        wish["course_selection"] = course_selection
        wishlist.append(wish)
        print("添加成功")

    def grab_elective_course():

        worklist = wishlist

        sleep_time = 10

        while len(worklist):
            for course in worklist:
                ret = assitant._select_elective_course(course)
                print("\n"+course["course_name"]+"：")

                if ret == "门数超过限制！":
                    print("退出选课，原因：门数超过限制")
                    return
                elif ret == "上课时间冲突！":
                    print("选课失败，原因：上课时间冲突")
                    worklist.remove(course)

                print(ret)

                time.sleep(sleep_time)

    def view_wishlist():

        #print(wishlist)
        for wish in wishlist:
            print(wish)

    def quit():
        with open("wishlist.txt", "w+") as f:
            f.write(json.dumps(wishlist, ensure_ascii=False))
        print("已保存愿望清单")
        exit()

    wishlist = []

    try:
        with open("wishlist.txt", "r+") as f:
            wishlist = json.loads(f.read())
    except:
        with open("wishlist.txt", "w+") as f:
            f.write("")









    while True:
        
        print("\n请输入操作代号：")
        print("\n# 查询 #")
        print("1：成绩")
        print("2：课表")
        print("\n# 选课 #")
        print("3：院公选课")
        print("\n# 抢课 #")
        print("Q：开始抢课")
        print("W：查看愿望清单")
        print("\n0：退出并保存愿望清单\n")

        cmd = input()

        trs = {
            "0": quit,
               "1": query_exam_scores,
            "2": query_schedule,
            "3": query_elective_course,
            "Q": grab_elective_course,
            "W": view_wishlist,

        }

        trs.get(cmd, lambda :print("命令错误！"))()
        print("\n按任意键继续......")
        input()
