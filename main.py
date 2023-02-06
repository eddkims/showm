import os
import sys
import re
import time
import ctypes
import subprocess
import pymysql
import datetime
from datetime import timedelta, date
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup as bs
import math
import configparser
import time
from xml.etree.ElementTree import parse
import time

try:
    import xmltodict
except ImportError:
    subprocess.run(['python', '-m', 'pip', 'install', '--upgrade', 'xmltodict'])
    import xmltodict

try:
    from scode.util import *
except ImportError:
    subprocess.run(['python', '-m', 'pip', 'install', '--upgrade', 'scode'])
    from scode.util import *

from scode.selenium import *
from scode.paramiko import *

# ===============================================================================
#                               Definitions
# ===============================================================================

def command(ssh: paramiko.SSHClient, query: str, timeout: float = None):
    """
    It executes a command on a remote server and returns the output and error text
    
    :param ssh: paramiko.SSHClient
    :type ssh: paramiko.SSHClient
    :param query: The command you want to run on the remote server
    :type query: str
    :param timeout: The time in seconds to wait for the command to finish. If the command doesn't finish
    in the given time, the function will return the output of the command so far
    :type timeout: float
    :return: stdout_text, err_text
    """

    stdin, stdout, stderr = ssh.exec_command(query)
    
    if timeout:
        start_time = time.time()
    
    # Wait for the command to terminate  
    while not stdout.channel.exit_status_ready():
        time.sleep(.1)
        if timeout:
            latest_time = time.time()

            if latest_time - start_time > timeout:
                stdout_text = stdout.read().decode('utf-8').strip()
                err_text = stderr.read().decode('utf-8').strip()
                return stdout_text, err_text
    
    stdout_text = stdout.read().decode('utf-8').strip()
    err_text = stderr.read().decode('utf-8').strip()
    return stdout_text, err_text


def execute_sql_query(ssh: paramiko.SSHClient, user_id: str, user_pw: str, db_name: str, query: str, timeout = None):
    """execute sql query

    Args:
        ssh (paramiko.SSHClient): paramiko ssh client.
        user_id (str): ID to log in.
        user_pw (str): Password to log in.
        db_name (str): Name of the database to be connected to.
        query (str): query statement to execute.

    Returns:
        tuple[str, str]: stdout, stderr
    """    
    query = query.replace('\'','\"')
    fquery = f"""mysql -u{user_id} -p{user_pw} {db_name} -e '{query}'"""
    return command(ssh, fquery, timeout=timeout)


def quart_to_list(query_stdout : str) :
    DB_lst = query_stdout.split('\n')
    del DB_lst[0]
    result = []
    for db_data in DB_lst :
        result.append(tuple(db_data.split('\t')))

    time.sleep(1)
    return result

def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print ('Error: Creating directory. ' +  directory)
 


def what_day_is_it(date):
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day = date.weekday()
    return days[day]

def requests_retry_session(
    retries=10,
    backoff_factor=0.5,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def dateform_changer(date) :
    date = datetime.datetime.strptime(str(date),'%Y%m%d')
    date = date.strftime("%Y-%m-%d")
    return date

def removing_comma(item):

    item = item.replace(' ','').replace('\n','').replace('\t','')
    if ',' in item :
        total = int(item.replace(',',''))
        return total
    else :
        total = int(item)
    return total

def get_dayoff(year) :
    holiday_api_url = 'http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo'
    api_key = 'dXPzBCd+KPJj8+QBl30akaTsd8I4XOQAUE+98Mhlz8S5rwQ/OvbNq154UKBPZKIkESAidjPFYmMo/Z2dpj0yWw=='

    params = {'ServiceKey' : api_key, 'solYear' : year, 'numOfRows' : 100}
    res = requests_retry_session().get(holiday_api_url,params=params)
    con = res.text

    data_dict = xmltodict.parse(con)
    holidays = data_dict['response']['body']['items']['item']
    holi_date = []
    for holiday in holidays :
        holi_date.append(dateform_changer(holiday['locdate']))
    return holi_date

def run():

    createFolder('log')
    createFolder('log_month')

#연습용             #메인 서버
#dev.e-e.kr         52.79.245.216
#kin_like3          kin_like2
#elql12!            elql12!
#test_hongyeon      kin_like

    try :
        host = 'dev.e-e.kr'
        user = 'root'
        password = 'xptmxm12'
        db = 'test_hongyeon'

        referer = 'https://kin.naver.com'
        user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36"
        header = {'referer': referer, 'user_agent': user_agent}
        conn = ssh_connect(hostname=host,username=user,password=password) 
        
    except Exception as e :
        print(f'DB 접속 정보를 확인해주세요. error : {e}')
        print(f'입력 받은 정보 - host : {host}, user : {user}, password : {password}, db : {db}')
        input_data = {'error' : e, 'reason' : 'plz check the information about DB'}
        err_logging(input_data)
    # Inintialize
    try :
        holi_date = get_dayoff(datetime.datetime.now().strftime("%Y"))
    except Exception as e :
        print('휴일 데이터를 가져오는데 실패했습니다.')
        input_data = {'error' : e, 'reason' : 'fail to requests Holiday_info'}
        err_logging(input_data)
        pass

    config = configparser.ConfigParser()
    try :
        config.read('dev.txt',encoding='cp949')
        chilling_time = int(config['DEFAULT']['time'])
        signal = config['DEFAULT']['only_today_check']
        signal = signal.lower()
        log_signal = config['DEFAULT']['log']
        log_signal = log_signal.lower()
        rest_signal = config['DEFAULT']['rest_mode']
        rest_signal = rest_signal.lower()
        if rest_signal == 'y' :
            rest_time = int(config['DEFAULT']['rest_time'])
            rest_times = [x for x in range(rest_time)]
            
    except Exception as e  :
        print(f'dev.txt 파일이 없거나, 파일 내에 데이터가 입력 되지 않았습니다. 확인 후 다시 실행 해주세요. Error : {e}')
        sys.exit()
    
    def reconnect_DB():
        conn.close()
        print(f'Error - 1 , {chilling_time}초 쉬고 재검사 실행')
        time.sleep(chilling_time)
        conn = ssh_connect(hostname=host,username=user,password=password) 

    if log_signal == 'y' :
        Log = True
    else :
        Log = False
    
    a_day_ago = timedelta(days=-1)
    compare_today = ''

    while True :
        try :
            try:
                begin = time.time()
                today = datetime.datetime.now()
                q_today = today.strftime("%Y-%m-%d")# 당일 쿼리용 날짜
                log_today = today.strftime("%y%m%d") # 로그 파일용 날짜
                start_time = today.strftime("%y-%m-%d %H:%M:%S")
                this_month = today.strftime("%m")
                what_day = what_day_is_it(today) # 오늘의 요일
                log_file_path = f'log/log_{log_today}.txt'
                log_time_file_path = f'log/time_log_{log_today}.txt'
                exist_log_file_path = f'log_month/log_{this_month}.txt'

            except Exception as e :
                err_string = f'error : {e}'
                if Log : fwrite(log_file_path, f'{err_string}')
                input_data = {'error' : e, 'reason' : 'fail to connection with DB is not smooth'}
                err_logging(input_data)
                reconnect_DB()
                continue

            if compare_today != q_today : # 하루에 한번 공휴일 requests 
                try :
                    holi_date = get_dayoff(datetime.datetime.now().strftime("%Y"))
                    compare_today = q_today
                    
                except Exception as e :
                    err_string = f'error : {e}'
                    if Log : fwrite(log_file_path, f'{start_time} >> {err_string}')
                    input_data = {'error' : e, 'reason' : 'fail to requests Holiday_info or connection with DB is not smooth'}
                    err_logging(input_data)
                    pass

            Select_sql = "SELECT seq, order_date, kin_url, answer_no, kin_id, kin_ucode, point FROM like_order WHERE like1_check_date = '' " # SQL 쿼리

            if signal == 'y' : 
                if q_today in holi_date or what_day == 'Sat' and 'Sun' : # 공휴일 혹은 주말
                    while True :
                        today += a_day_ago
                        one_day_ago = (today).strftime("%Y-%m-%d") # 1일 전 쿼리용 날짜
                        what_day = what_day_is_it(today)
                        if one_day_ago not in holi_date and what_day != 'Sat' and what_day != 'Sun' :
                            Select_sql += f" and order_date LIKE '%{one_day_ago}%' "
                            break

                else : # 평일
                    Select_sql += f" and order_date = '{q_today}' " 
                    what_time = int(today.strftime("%H"))
                    if rest_signal == 'y' :
                        if what_time in rest_times :
                            conn.close()
                            time_string = f'{start_time} >> 평일 {rest_times[0]} 시 ~ {rest_time} 시까지 쉬는시간입니다.'
                            if Log : fwrite(log_file_path,time_string)
                            print(time_string)
                            time.sleep(5)
                            conn = ssh_connect(hostname=host,username=user,password=password) 
                            continue
            Select_sql += "AND description = '' "
            # print(Select_sql)
            #쿼리문 만드는 작업 끝 --
            print(Select_sql)
            try :
                query_stdout, query_stderr = execute_sql_query(conn, user, password, db, Select_sql)

                if 'error' in query_stderr.lower(): # 쿼리문 오류시 에러 발생 시킴
                    connect_err_str = f'서버 연결이 원할하지 않습니다. 서버 정보를 확인해주세요 : serverIP - {host}, user - {user}, pwd - {password}, DB - {db}'
                    print(connect_err_str)
                    if Log : fwrite(log_file_path,connect_err_str)
                    input_data = {'file' : 'main.py','quary' : Select_sql}
                    err_logging(input_data)
                    reconnect_DB()
                    continue

                
                res = quart_to_list(query_stdout)
                len_res = len(res)

                if len_res == 0 :
                    if Log : fwrite(log_file_path, f'{start_time} >> {Select_sql}')
                    non_data_string = f'{start_time}\t검사 할 데이터가 없습니다. 60 초후 다시 검사'
                    print(non_data_string)
                    if Log : fwrite(log_file_path,non_data_string)
                    time.sleep(60)
                    continue
                    
            except Exception as e  :
                connect_err = f'{start_time}\tDB 서버와 통신이 불안정합니다. 다시 시도하겠습니다. Error : {e}'
                print(connect_err)
                if Log : fwrite(log_file_path,connect_err)
                input_data = {'reason' : 'fail to connect Mysql server or the quary has some problem plz check sql'}
                err_logging(input_data)
                reconnect_DB()
                continue



            string = f'검사 : {len_res}'
            print(string)
            if Log : fwrite(log_file_path,string)
            if len_res == 0 :
                string = f'Q : {Select_sql}'
                print(string)
                if Log : fwrite(log_file_path,string)

            data_list = []
            cur_url = ''
            number_of_order = 0
            number_of_emotion = 0
            for i, data in enumerate(res) :

                cur_time = datetime.datetime.now().strftime("%H:%M:%S")
                key_err_string = f'{cur_time} > 가져온 데이터가 비어있습니다. 접속 제한을 당했다면 잠시 기다려주세요.'
                ip_err_string = f'{cur_time} > 접속 제한으로 60초 waiting...'
                quary_err_string = f'{cur_time} > SQL 오류 발생'
                try :
                    check_time = datetime.datetime.now()
                    check_date = check_time.strftime("%Y-%m-%d %H:%M:%S")
                    flag = False
                    like1_flag = False

                    like_flag = ''
                    seq = data[0]
                    db_order_date = data[1]
                    order_date = int(data[1].replace('-',''))
                    url = data[2]
                    answer_no = data[3]
                    kin_id = data[4]
                    ucode = data[5]
                    #print(f'\n{i+1} > {kin_id} > {answer_no} > {url}')
                except Exception as e :
                    err_string = f'{cur_time}\terror - 1 : {e}'
                    print(err_string)
                    if Log : fwrite(log_file_path,err_string)
                    input_data = {'data' : data, 'reason' : 'fail to bring data from Database'}
                    err_logging(input_data)

                an_no = re.findall('answer_(\d+)', answer_no)[0]
                dir_id, doc_id = re.search('dirId=(\d+)&docId=(\d+)', url).groups()
                emotion_url = f'https://m.kin.naver.com/mobile/qna/likeUserList.naver?dirId={dir_id}&docId={doc_id}&answerNo={an_no}'


    ###앞의 데이터와 다른 url 이면 데이터 체크 후, 리스트에 dict 담음

                if cur_url != emotion_url :
                    number_of_order +=1
                    cur_time = datetime.datetime.now().strftime("%H:%M:%S")
                    # print('======여기까지 같은 url과 an_no ====')
                    data_list.clear()
                    cur_url = emotion_url
                    time.sleep(0.5)
                    s = requests.session()
                    s.headers.update(header)
                    #res = requests_retry_session().get(emotion_url) # 호출
                    res = s.get(emotion_url) # 호출
                
                

                    if '접속이 제한되었습니다' in res.text:
                        cur_time = datetime.datetime.now().strftime("%H:%M:%S")
                        print(ip_err_string)
                        if Log : fwrite(log_file_path,ip_err_string)
                        time.sleep(60)
                        continue 

                    html = res.text

                    if '해당 컨텐츠를 공감한 회원' in html :
                        cur_time = datetime.datetime.now().strftime("%H:%M:%S")
                        string = f'{cur_time} >> {i+1} / {len_res} , answer_no : {an_no}, url : {url} 공감페이지 표정 존재 X'
                        print(string)
                        if Log : fwrite(log_file_path,string)
                        continue

                    if '게시물이 존재하지 않습니다' in html : # 게시물존재 x 
                        cur_time = datetime.datetime.now().strftime("%H:%M:%S")
                        try : # 여기 테스트
                            s = requests.session()
                            s.headers.update(header)
                            res = s.get(url)
                            html = res.text
                        except :
                            input_data = {'url' : url,'no' : answer_no, 'reason' : 'fail to requsts to site'}
                            err_logging(input_data)
                            continue
                        if '접속이 제한되었습니다' in res.text :
                            print(ip_err_string)
                            if Log : fwrite(log_file_path,ip_err_string)
                            time.sleep(60)
                            continue 
                        if '게시물이 삭제되어 요청하신 페이지를 표시할 수 없습니다' in html : # 질문삭제
                            try :

                                update_description_sql = f"UPDATE like_order SET description = '질문삭제' WHERE kin_url = '{url}' AND answer_no = '{answer_no}' "
                                query_stdout, query_stderr = execute_sql_query(conn,user,password,db,update_description_sql)

                                if 'error' in query_stderr.lower():
                                    print(quary_err_string)
                                    if Log : fwrite(log_file_path,quary_err_string)
                                    input_data = {'reason':query_stderr}
                                    err_logging(input_data)
                                    raise Exception(quary_err_string)

                                q_delete_string = f'{cur_time} >> {i+1} / {len_res} , answer_no : {an_no}, url : {url} 질문이 삭제 되었습니다.'
                                print(q_delete_string)
                                if Log : fwrite(log_file_path,q_delete_string)
                            except Exception as e :
                                input_data = {'url' : url,'no' : answer_no, 'reason' : 'Invalid sql quary'}
                                err_logging(input_data)
                                continue

                        else : # 답변삭제
                            try :

                                update_description_sql = f"UPDATE like_order SET description = '답변삭제' WHERE kin_url = '{url}' AND answer_no = '{answer_no}' "
                                query_stdout, query_stderr = execute_sql_query(conn,user,password,db,update_description_sql)

                                if 'error' in query_stderr.lower():
                                    print(quary_err_string)
                                    if Log : fwrite(log_file_path,quary_err_string)
                                    input_data = {'reason':query_stderr}
                                    err_logging(input_data)
                                    raise Exception(quary_err_string)

                                a_delete_string = f'{cur_time} >> {i+1} / {len_res} , answer_no : {an_no}, url : {url} 답변이 삭제 되었습니다.'
                                print(a_delete_string)
                                if Log : fwrite(log_file_path,a_delete_string)
                            except Exception as e :
                                input_data = {'url' : url,'no' : answer_no, 'reason' : 'Invalid sql quary'}
                                err_logging(input_data)
                                continue
                        continue

                    soup = bs(html,'html.parser')
                    try :
                        like_total_len = soup.select_one('#ct > div > div.likeit_user__menu > ul > li.likeit_user__item.like > a > span.likeit_list_count._count').text
                        like_total_len = removing_comma(like_total_len)

                        useful_total_len = soup.select_one('#ct > div > div.likeit_user__menu > ul > li.likeit_user__item.useful > a > span.likeit_list_count._count').text
                        useful_total_len = removing_comma(useful_total_len)

                        jouful_total_len = soup.select_one('#ct > div > div.likeit_user__menu > ul > li.likeit_user__item.haha > a > span.likeit_list_count._count').text
                        jouful_total_len = removing_comma(jouful_total_len)

                    except Exception as e :
                        err_string = f'{cur_time}\terror - 1 : {e}'
                        print(err_string)
                        if Log : fwrite(log_file_path,err_string)
                        input_data = {'data' : data, 'url' : emotion_url, 'reason' : 'fail to bring a total mount data from site'}
                        err_logging(input_data)
                        continue

                #type_list = {'like':like_total_len, 'useful':useful_total_len, 'haha':jouful_total_len}
                # 좋아요 만 검사
                    type_list = {'like':like_total_len}

                    for type, len_tnt in type_list.items() : # 좋아요 카테고리 3개 돌리기
                        
                        if len_tnt == 0 :
                                continue
                        
                        circle = math.ceil(len_tnt/100)

                        for n in range(circle) :         
                            try :
                                time.sleep(0.5)
                                request_url = f'https://m.kin.naver.com/mobile/ajax/getAnswerLikeUserListAjax.naver?reactionType={type}&dirId={dir_id}&docId={doc_id}&answerNo={an_no}&page={n+1}&count=100'
                                s = requests.session()
                                s.headers.update(header)
                                #res = requests_retry_session(session=s).get(request_url)
                                res = s.get(request_url)

                                if '접속이 제한되었습니다' in res.text :
                                    print(ip_err_string)
                                    if Log : fwrite(log_file_path,ip_err_string)
                                    time.sleep(60)
                                    continue 

                                res_list = res.json()
                                dict_list = res_list['list']
                                first_elem_date = int(dict_list[0]['reactionTime'].replace('.','')) 

                                if first_elem_date < order_date :
                                    break
                            except KeyError :
                                print(key_err_string)
                                if Log : fwrite(log_file_path,key_err_string)
                                input_data = {'url':f"{request_url}",'reason' : f"Nothing in this data, perhap there is a realation with blocking IP"}
                                err_logging(input_data)

                            except Exception as e :
                                err_string = f'{cur_time}\terror - 1 : {e}'
                                print(err_string)
                                if Log : fwrite(log_file_path,err_string)
                                input_data = {'url':f"{request_url}",'reason' : f"Fail to requests the url with Ajax, plz check the url with Ajax is exist\n{e}"}
                                err_logging(input_data)

                            for item in dict_list : # 각각의 공감 리스트 (각각 카테고리 내부 글 리스트)
                                try :
                                    id = item['userText']
                                    if '회원 탈퇴' in id :
                                        continue
                                    if '질문 작성자' in id :
                                        continue
                                    if '답변 작성자' in id :
                                        continue

                                    u_code = item['profileLinkUrl'].split('u=',1)[1]
                                    date = int(item['reactionTime'].replace('.',''))
                                    if date < order_date :
                                        break
                                    else :
                                        data_list.append(item)

                                except Exception as e :
                                    err_string = f'{cur_time}\terror - 1 : {e}'
                                    print(err_string)
                                    if Log : fwrite(log_file_path,err_string)
                                    input_data = {'url':f"{request_url}",'elem':f'{item}','data' : f'{ucode},{u_code},{order_date}','reason' : f"Fail to crawling the data on Ajax url, plz check the data with Ajax is exist\n{e}"}
                                    err_logging(input_data)

                        
                    # print(f'가져온 json 데이터 갯수 : {len(data_list)}')
    #### 여기까지 ###


                for item in data_list : # 리스트에 따로 적재 해둔 데이터와 DB의 데이터를 비교
                    u_code = item['profileLinkUrl'].split('u=',1)[1]
                    if ucode == u_code : #ucode는 내가 가져온거 , u_code는 지식인 사이트에서 가져온거
                        flag = True
                        #print(item['userText'],item['profileLinkUrl'],item['reactionTime'])
                        if type == 'like' :
                            like_flag = '1'
                            like1_flag = True

                        elif type == 'useful' :
                            like_flag = '2'

                        elif type == 'haha' :
                            like_flag = '3'
                        break
                
                if flag :
                    result = 'O'
                    try :

                        get_point_sql = f"SELECT base_point FROM like_user WHERE kin_ucode = '{ucode}' "
                        Base_point, query_stderr = execute_sql_query(conn, user, password, db, get_point_sql)
                        Base_point = int(Base_point.split('\n')[1])
                        if 'error' in query_stderr.lower(): # 쿼리문 오류시 에러 발생 시킴
                            print(quary_err_string)
                            if Log : fwrite(log_file_path,quary_err_string)
                            input_data = {'reason':query_stderr}
                            err_logging(input_data)
                            raise Exception(quary_err_string)


                        if like1_flag : 
                            number_of_emotion += 1
                            plus_point_sql = f"UPDATE like_user SET point_all = base_point+cur_point, cur_point=cur_point+base_point WHERE kin_ucode = '{ucode}' "
                            query_stdout, query_stderr = execute_sql_query(conn, user, password, db, plus_point_sql)
                            # print(query_stdout)
                            if 'error' in query_stderr.lower(): # 쿼리문 오류시 에러 발생 시킴
                                print(quary_err_string)
                                if Log : fwrite(log_file_path,quary_err_string)
                                input_data = {'reason':query_stderr}
                                err_logging(input_data)
                                raise Exception(quary_err_string)


                            update_sql = f"UPDATE like_order SET like_no = '{like_flag}', like{like_flag}_check_date = '{str(check_date)}', point = '{Base_point}' WHERE seq = {seq} "
                        else:
                            update_sql = f"UPDATE like_order SET like_no = '{like_flag}', like{like_flag}_check_date = '{str(check_date)}' WHERE seq = {seq} "
                        
                        query_stdout, query_stderr = execute_sql_query(conn, user, password, db, update_sql)
                        # print(query_stdout)
                        if 'error' in query_stderr.lower(): # 쿼리문 오류시 에러 발생 시킴
                            print(quary_err_string)
                            if Log : fwrite(log_file_path,quary_err_string)
                            input_data = {'reason':query_stderr}
                            err_logging(input_data)
                            raise Exception(quary_err_string)



                        if like1_flag :
                            # point_list insert
                            point_check_sql = f"INSERT INTO point_list ( order_date, kin_id, kin_url, answer_no, check_date, like_no, like_point, point_type ) " \
                                            f"VALUES('{db_order_date}','{kin_id}','{url}','{answer_no}','{check_date}','{like_flag}','{Base_point}','등록') "
                            query_stdout, query_stderr = execute_sql_query(conn, user, password, db, point_check_sql)
                            # print(query_stdout)
                            if 'error' in query_stderr.lower(): # 쿼리문 오류시 에러 발생 시킴
                                print(quary_err_string)
                                if Log : fwrite(log_file_path,quary_err_string)
                                input_data = {'reason':query_stderr}
                                err_logging(input_data)
                                raise Exception(quary_err_string)

                    except Exception as e :
                        err_string = f'{cur_time}\terror - 1 : {e}'
                        print(err_string)
                        if Log : fwrite(log_file_path,err_string)
                        input_data = {'ucode' : ucode, 'reason' : 'some problem at Database or Sql quary write wrong way plz check sql'}
                        err_logging(input_data) 

                    fwrite(exist_log_file_path,f"seq = {seq}\tkin_id = {kin_id}\turl = {url}\tlike{like_flag}_check_date = '{str(check_date)}' ") #표정 있을때 남기는 로그

                else :
                    result = 'X'

                cur_time = datetime.datetime.now().strftime("%H:%M:%S")

                note_string = f'{cur_time} >> {i+1} / {len_res} ID : {kin_id}, answer_no : {an_no}, 표정 : {result}, url : {url}'
                print(note_string)
                if Log : fwrite(log_file_path,note_string)

            end_time = datetime.datetime.now().strftime("%y-%m-%d %H:%M:%S")
            start_string = f'시작 시간 : {start_time}'
            end_string = f'종료 시간 : {end_time}'
            retest_string = f'{chilling_time} 초 뒤에 다시 검사를 실행하겠습니다. \n'
            
            print(start_string)
            print(end_string)
            print(retest_string)

            sec = time.time() - begin
            taking_time = str(datetime.timedelta(seconds=sec)).split(".")[0]
            log_string = f'{cur_time} >> 소요 시간 : {taking_time}, 검사 수 : {len_res}, URL 갯수 : {number_of_order}, Like1 갯수 : {number_of_emotion}'
            fwrite(log_time_file_path,log_string)

            if Log : 
                fwrite(log_file_path,start_string)
                fwrite(log_file_path,end_string)
                fwrite(log_file_path,retest_string)

            
            # time.sleep(chilling_time)
            time.sleep(5)

            
            

            
        except Exception as e :
            conn.close()
            err_string = f'{cur_time}\terror - 1 : {e}'
            print(err_string)
            if Log : fwrite(log_file_path,err_string)
            input_data = {'reason' : e }
            err_logging(input_data)
            conn = ssh_connect(hostname=host,username=user,password=password)  
            continue


# ===============================================================================
#                            Program infomation
# ===============================================================================

__author__ = '김홍연'
__requester__ = '이광헌 부장'
__registration_date__ = '221212'
__latest_update_date__ = '221227'
__version__ = 'v1.00'
__title__ = '20221209_표정체크 24시 감시 프로그램'
__desc__ = '20221209_표정체크 24시 감시 프로그램'
__changeLog__ = {
    'v1.00': ['Initial Release.'],
    'v1.01': ['20221213 김홍연 시간체크 추가, ip 차단 에러 추가, 시간값 config 파일 추가'],
    'v1.02': ['20221214 김홍연 requests 간소화로 시간 단축 및 ip차단 방지, 공감페이지 존재x 에러 추가, 게시물 삭제 에러 추가'],
    'v1.03': ['20221215 김홍연 게시물 삭제 시 에러 추가 및 데이터 베이스 삭제 정보 추가'],
    'v1.03': ['20221216 김홍연 로그 폴더, 로그 파일 추가, 주말은 금요일 데이터 감시 기능 추가'],
    'v1.04': ['20221220 김홍연 공휴일, 금요일 데이터 감시 기능 추가'],
    'v1.05': ['20221221 김홍연 공휴일, 장시간 DB연결시 오류 부분 개선, 표정 완료 된 로그 1달 단위로 개선'],
    'v1.06': ['20221222 김홍연 평일 새벽 00시부터 9시까지 프로그램 잠시 쉬는 기능 추가'],
    'v1.07': ['20221227 김홍연 pymysql에서 paramiko 버전으로 변경'],
}
version_lst = list(__changeLog__.keys())

full_version_log = '\n'
short_version_log = '\n'

for ver in __changeLog__:
    full_version_log += f'{ver}\n' + '\n'.join(['    - ' + x for x in __changeLog__[ver]]) + '\n'

if len(version_lst) > 5:
    short_version_log += '.\n.\n.\n'
    short_version_log += f'{version_lst[-2]}\n' + '\n'.join(['    - ' + x for x in __changeLog__[version_lst[-2]]]) + '\n'
    short_version_log += f'{version_lst[-1]}\n' + '\n'.join(['    - ' + x for x in __changeLog__[version_lst[-1]]]) + '\n'

# ===============================================================================
#                                 Main Code
# ===============================================================================

if __name__ == '__main__':

    ctypes.windll.kernel32.SetConsoleTitleW(f'{__title__} {__version__} ({__latest_update_date__})')

    sys.stdout.write(f'{__title__} {__version__} ({__latest_update_date__})\n')

    sys.stdout.write(f'{short_version_log if short_version_log.strip() else full_version_log}\n')

    run()