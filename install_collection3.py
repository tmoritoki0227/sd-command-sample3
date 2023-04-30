#!/usr/bin/env python3

import json
import requests 
# from requests.auth import HTTPBasicAuth
from distutils.version import StrictVersion

import os # 環境変数取得に必要
import re
import time
import subprocess # 外部プログラム実行につかう
import sys # 引数受け取りで使う

class VersionNotFoundError(Exception): # 指定したバージョンがArtifactoryにないとき
    pass # 何もしない宣言らしい
class WrongVersionFormat(Exception): # 指定したバージョンがArtifactoryにないとき
    pass # 何もしない宣言らしい

# def get_collection() -> list:
#     sd_collection: str = os.getenv('SD_COLLECTION')

#     # collectionをカンマで区切って配列に格納。splitは分割メソッド。stripは前後の空白削除
#     collections: list = sd_collection.split(',')
#     print("collections = " + str(collections))

#     return collections

def get_available_version() -> list:
    url = 'https://moritoki.jfrog.io/artifactory/api/storage/xraysample-local/release/'
    # ユーザー名を指定(これはそのうち使えなくなるよ)
    username = 'tmoritoki0227@gmail.com'
    # パスワードを指定(これはそのうち使えなくなるよ)
    # 不正
    # password = 'cmVmdGtuOjAxOjE3MTM5NjM4ODI6SG5RV3ZGMXdjeXhieklLc1loNDdsNHdMeTF'
    # 正しい
    password = 'cmVmdGtuOjAxOjE3MTM5NjM4ODI6SG5RV3ZGMXdjeXhieklLc1loNDdsNHdMeTF2'
    timeout = 3 # connect timeoutとread timeoutする時間が３秒となる
    # connect timeout: 相手のサーバーと接続を確立する(establish a connection)までの待機時間
    # read timeout:    サーバーがレスポンスを返してくるまでの待機時間
    retry_times = 3 # ３回
    # errs = [500, 502, 503, 401 ,403] #  401 ,403 を入れてパスワードを違うのにするとリトライテストがしやすい
    errs = [500, 502, 503]
    # HTTP 500 Internal Server Error
    # HTTP 503 Service Unavailable
    # HTTP 502 Bad Gateway
    
    # https://gammasoft.jp/support/solutions-of-requests-get-failed/
    for t in range(retry_times + 1):
        response = requests.get(url, auth=requests.auth.HTTPBasicAuth(username, password), timeout=3)
        print("response.status_code = " + str(response.status_code))
        
        # errsに該当するレスポンスが返ってきた場合はリトライする
        if t < retry_times:
            if response.status_code in errs:
                print("APIの実行に失敗しました。2秒後にリトライします... " + "response.status_code = " + str(response.status_code))
                time.sleep(2)
                continue
        
        # forを終了する処理がいる
        break # 通常こうなるのはレスポンス２００、[500, 502, 503]のリトライがおわったとき

    response.raise_for_status() # Response オブジェクトの raise_for_status メソッドをコールすることで 400-599 の時に HTTPError を raise します。
    # URL、レスポンスコードも表示されるらしいのtry_catchして情報出力させることをしていない
    # requests.exceptions.HTTPError: 403 Client Error:  for url: https://moritoki.jfrog.io/artifactory/api/storage/xraysample-local/release/
    res_json = json.loads(response.text)

    # キーchildrenの値を取得
    children_info = res_json['children']
    # print ("children_info = " + str(children_info) )

    # キーuriの値を取得
    available_version: list = []
    for c in children_info:
        # print(c['uri'])
        available_version.append(c['uri'].replace('/', ''))

    return available_version


def get_match_version(available_version:list, user_specified_version: str) -> str: # ユーザ指定のバージョンを渡して、マッチするものを返すメソッドが欲しいか.
    # ユーザ指定のバージョンを3分割して変数格納
    match = re.match(r'(?P<major>.+)\.(?P<minor>.+)\.(?P<micro>.+)', user_specified_version)
    if match:
        majaor_version = match.group('major').strip()
        minor_version = match.group('minor').strip()
        micro_version = match.group('micro').strip()

        print('majaor_version = ' + majaor_version + ' , ' +  'minor_version = ' + minor_version + ' , ' + 'micro_version = ' + micro_version)
        # print('minor_version = ' + minor_version)
        # print('micro_version = ' + micro_version)        
    else:
        if not match: raise WrongVersionFormat('Invalid version specification. ' +  'user_specified_version = ' + user_specified_version) 
        # 3.1とか指定されるとエラー

    match_version : list = []
    if re.match(r'[0-9]+', majaor_version) and re.match(r'[0-9]+', minor_version) and re.match(r'[0-9]+', micro_version):
        print ("ALL数字でマッチンぐしたよ") # この場合はそのまま使う
        # match_version = [v for v in available_version if re.match(majaor_version + r'\.' + minor_version + r'\.' + micro_version, v)] # user_specified_versionと同じだが他と処理を同じにしている
        return user_specified_version
    
    elif re.match(r'[0-9]+', majaor_version) and re.match(r'[0-9]+', minor_version) and re.match(r'\*', micro_version):
        print ("最後に＊ありでマッチンぐしたよ") # ＊箇所だけ数字として抽出。その他は指定の値で抽出
        match_version = [v for v in available_version if re.match(majaor_version + r'\.' + minor_version + r'\.[0-9]+', v)]

    elif re.match(r'[0-9]+', majaor_version) and re.match(r'\*', minor_version) and re.match(r'[0-9]+', micro_version):
        print ("真ん中に＊ありでマッチンぐしたよ")
        match_version = [v for v in available_version if re.match(majaor_version  + r'\.[0-9]+\.' + micro_version, v)]

    elif re.match(r'[0-9]+', majaor_version) and re.match(r'\*', minor_version) and re.match(r'\*', micro_version):
        print ("真ん中、最後に＊ありでマッチンぐしたよ")
        match_version = [v for v in available_version if re.match(majaor_version  + r'\.[0-9]+' + r'\.[0-9]+', v)]
    
    if not match_version: raise VersionNotFoundError('Specified version was not found in Artifactory. ' + 'user_specified_version = ' + user_specified_version ) # 入ってなければfalseを返す
        # ユーザのバージョン指定方法正しいが、ユーザ指定のバージョンがartifactoryにはなかった状況
 
    # Traceback (most recent call last):
    #   File "/home/moritoki/python_test/test3.py", line 101, in <module>
    #     raise VersionNotFoundError('指定されたバージョンがArtifactoryにありませんでした')
    # __main__.VersionNotFoundError: 指定されたバージョンがArtifactoryにありませんでした

    match_version.sort(key=StrictVersion) # match_versionの中身がソートされて保存もされる
    print("match_version_sorted = " + str(match_version))

    return match_version[-1] # [-1] は配列の最後。並び替えてるから最後が１番あたらしいものになる

# def exec_ansible_galaxy_install(name:str, version:str) -> None: 
#     """
#     Parameters
#     ----------
#     name : str
#         installするコレクション名
#     version : str
#         installするコレクションのバージョン

#     # Returns
#     # -------
#     # int
#     #     Description of anonymous integer return value.
#     """

#     # try:
#     cmd = "ansible-gallaxy install " + str(name) + "-" + str(version) + ".tar.gz"
#     print ("ansible_gallaxy_command = " + str(cmd)) 
#     cmd = "hostname"
#     print ("ansible_gallaxy_command = " + str(cmd)) # 失敗した時のためにも出しておく
#     # check=Trueを指定。check に真を指定した場合、プロセスが非ゼロの終了コードで終了すると CalledProcessError 例外が送出されます。 
#     # stderr=subprocess.STDOUT とすると、標準エラー出力も標準出力に追記される（いらないかも）
#     result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

#     print(result.stdout)
#     # エラー情報が出てれば問題ない
#     # except subprocess.CalledProcessError as e:
#     #     # 終了コードが0以外の場合、例外が発生
#     #     print(e)


def main():
    # 環境変数取得
    # export SD_COLLECTION="/aaa/release/1.0.0 , /bbb/release/1.*.0, /ccc/release/1.0.*, /ddd/release/1.*.*, /aaa/test/3.0.0"
    # export SD_COLLECTION="/aaa/release/1.0.0 , /bbb/release/1.*.0, /ccc/release/1.0.*, /ddd/release/1.*.*, /aaa/test/3.0.1"
    # export SD_COLLECTION="/aaa/release/1.0.0 , /bbb/release/1.*.0, /ccc/release/1.0.*, /ddd/release/1.*.*, /aaa/test/3.1"

    # collectionをカンマで区切って配列に格納。splitは分割メソッド。stripは前後の空白削除
    # collections: list =  get_collection()

    # for でcollectionを１つずつ処理していく
    # for collection in collections:
    print('------------ start ------------------')
    args = sys.argv
    print(args[1]) 
    collection = args[1]
    print('collection = ' + print(str(collection)))
    #if not collection : raise VersionNotFoundError('arg nai yo')

    # print ("------------------------loopスタート-------------------------")
    collection_parts = args[1].strip().split('/') # 空白除去して/で分割　/aaa/release/1.0.0 => ["", "aaa" ,"release" ,"1.0.0"]
    # collection_parts = collection.strip().split('/') # 空白除去して/で分割　/aaa/release/1.0.0 => ["", "aaa" ,"release" ,"1.0.0"]
    print ("collection_parts = " + str(collection_parts))

    # ユーザ指定のname取得
    name = collection_parts[1]
    print ("name = " + str(name))
    
    # ユーザ指定のversion取得
    user_specified_version = str(collection_parts[3]) # 1.0.0が欲しい。a[3]に入っている
    print ("user_specified_version = " + str(user_specified_version) )
    
    # Artifactoryにあるバージョンの一覧を取得
    available_version: list = get_available_version()

    # ユーザの指定をもとに、インストールするバージョンを決定する
    install_version = get_match_version(available_version, user_specified_version)
    
    # ansible_galaxy_installを実行する
    # exec_ansible_galaxy_install(name, install_version) # 失敗したら例外発生

    # ここまでループ
    return str(name) + "-" + str(install_version) + ".tar.gz" 

if __name__ == "__main__":
    main()