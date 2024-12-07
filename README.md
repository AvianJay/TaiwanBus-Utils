# TaiwanBus-Utils
一些TaiwanBus跟YouBikePython的腳本
# 安裝
Termux 設定
```shell
yes "" | pkg upgrade
pkg install git python python-pip
```
複製儲存庫+cd
```shell
git clone https://github.com/AvianJay/TaiwanBus-Utils.git
cd TaiwanBus-Utils
```
安裝依賴庫
```shell
pip install -r requirements.txt
```
更新公車資料庫
```shell
taiwanbus updatedb
```
# 使用
執行下列指令來取得幫助：<br>
termux-notify.py: 公車提醒
```shell
python termux-notify.py -h
```
termux-youbike.py: YouBike剩餘站點提醒
```shell
python termux-youbike.py -h
```
unzlib.py: zlib資料解壓工具
```shell
python unzlib.py -h
```
apiserver.py: TaiwanBus的API伺服器<br>
discord.py: 還未完成
