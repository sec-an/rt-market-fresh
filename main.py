# -*- coding:utf8 -*-
import base64
import hashlib
import hmac
import json
import requests
import time
import threading
import os
import datetime
import sys

# 获取用户配置
with open('config.json', 'r', encoding='utf-8') as f:
    userInfo = json.load(f)
f.close()


def print_log(message):
    print(
        f"{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]} {threading.current_thread().name} {sys._getframe().f_back.f_code.co_name} {message}")


print_log(userInfo)

# 请求体参数配置
clientid = "a7ea53059fc868e2e3e2dd7c04027035"  # 固定值
device_id = userInfo['device_id']  # 未加验证,使用随机36位字符串即可
token = userInfo['token']  # 用户令牌,有效期未知

# 用户坐标,直接使用配送地址坐标,自动获取,base64编码
positionLat = ""
positionLng = ""
# 配送地址ID
addrId = ""

# 店铺坐标,自动获取
lat = ""
lng = ""
# 店铺信息,自动获取
store_id = ""  # 店铺编号
scopeType = 1
businessType = 1
businessId = "17000001"  # 店铺编号+0001
deliveryCircleType = "1"    # 配送时效

packageId = ""
packageName = ""
deliveryTimeList = []   # 配送时间

# 优惠券相关,出于多线程原因,暂不支持
freshVoucherSeqs = {}
itemsVoucherSeqs = {}
deductVoucherSeqs = {}
total_prices = ""   # 订单总价

headers = {
    'Accept-Encoding': 'gzip, deflate, br',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36 MicroMessenger/7.0.9.501 NetType/WIFI MiniProgramEnv/Windows WindowsWechat',
    'Referer': 'https://servicewechat.com/wx08cc6bd15fabfa53/84/page-frame.html'
}

# 标志
goods_changed_flag = False
time_changed_flag = False


class multi_thread(threading.Thread):
    def __init__(self, threadID, name, date, day, time, dayListScroll):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.date = date
        self.day = day
        self.time = time
        self.dayListScroll = dayListScroll

    def run(self):
        createOrder(self.name, self.date, self.day, self.time, self.dayListScroll)


# 构造post数据包,并对data签名
def sign(body, key="@653yx#*^&HrTy99"):
    data = {
        "apiVersion": "t141",
        "appVersion": "1.5.1",
        "areaCode": "CS000016",
        "channel": "online",
        "clientid": clientid,
        "device_id": device_id,
        "time": int(round(time.time() * 1000)),
        "reRule": "4",  # 固定值
        "token": token,
        "viewSize": "720x1184",
        "networkType": "wifi",
        "isSimulator": False,
        "osType": "4",
        "scopeType": scopeType,
        "businessType": businessType,
        "businessId": businessId,
        "deliveryCircleType": deliveryCircleType,
        "body": body
    }
    dataStr = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    isSimulator = data['isSimulator']
    viewSize = data['viewSize']
    networkType = data['networkType']
    timestamp = data['time']
    signStr = dataStr + (str(isSimulator).lower() + viewSize + networkType + str(timestamp))
    data = signStr.encode('utf-8')
    appsecret = key.encode('utf-8')
    signature = base64.b64encode(hmac.new(appsecret, data, digestmod=hashlib.sha256).digest()).decode()
    # print(signature)
    body = {
        "data": dataStr,
        "h5": "yx_touch",
        "paramsMD5": signature
    }
    return body


# 获取配送地址信息
def getAddressList():
    url = "https://yx.feiniu.com/member-yxapp/address/getAddressList/t141"
    body = {
        "action": 2
    }
    try:
        res = requests.post(url=url, data=sign(body), headers=headers, timeout=(3.05, 6.05)).json()
        if res['errorCode'] == 0:
            print_log('Success!')
            global addrId, positionLat, positionLng
            res = res['body']['addrList'][0]
            addrId = res['addrId']
            positionLat = res['latitude']
            positionLng = res['longitude']
            content = f"\n默认配送信息：\n"
            content += f"姓名：{base64.b64decode(res['name']).decode()}\n"
            content += f"联系方式：{base64.b64decode(res['cellPhone']).decode()}\n"
            content += f"地址：{res['province']}{base64.b64decode(res['city']).decode()}{base64.b64decode(res['area']).decode()}{base64.b64decode(res['addrMap']).decode()}{base64.b64decode(res['addr']).decode()}\n"
            content += f"标签：{res['addrType']}\n"
            print_log(content)
            return True
        elif res['errorCode'] == 20103 or res['errorCode'] == 1000:
            print_log(res['errorDesc'])
        else:
            print_log(res['errorDesc'])
            print_log(res)
        return False
    except Exception as e:
        print_log(e)
    return False


# 根据配送地址选择店铺
def homeStoreList(choice):
    global positionLng, positionLat
    url = "https://yx.feiniu.com/member-yxapp/location/homeStoreList/t141"
    body = {
        "longitude": positionLng,
        "latitude": positionLat
    }
    try:
        res = requests.post(url=url, data=sign(body), headers=headers, timeout=(3.05, 6.05)).json()
        if res['errorCode'] == 0:
            print_log('Success!')
            global lat, lng, store_id, scopeType, businessType, businessId, deliveryCircleType
            res = res['body']['stores'][choice]
            lat = res['shopLatitude']
            lng = res['shopLongitude']
            store_id = res['shopId']
            scopeType = res['scopeType']
            businessType = res['businessType']
            businessId = res['businessId']
            deliveryCircleType = res['deliveryCircleType']
            content = f"\n店铺信息：\n"
            content += f"店铺名：{res['shopName']}\n"
            content += f"联系方式：{res['shopPhone']}\n"
            content += f"距离：{res['distance']}\n"
            print_log(content)
            return True
        elif res['errorCode'] == 20103 or res['errorCode'] == 1000:
            print_log(res['errorDesc'])
        else:
            print_log(res['errorDesc'])
            print_log(res)
        return False
    except Exception as e:
        print_log(e)
    return False


# 购物车全选
def allselect():
    url = "https://yx.feiniu.com/cart-yxapp/shopcart/adminshopcart/allselect/t141"
    body = {
        "is_get": 0,
        "action": 2,
        "is_selected": 1,
        "select": 0,
        "store_id": store_id
    }
    try:
        res = requests.post(url=url, data=sign(body), headers=headers, timeout=(3.05, 6.05)).json()
        if res['errorCode'] == 0:
            print_log('Success!')
            return True
        elif res['errorCode'] == 20103 or res['errorCode'] == 1000:
            print_log(res['errorDesc'])
        else:
            print_log(res['errorDesc'])
            print_log(res)
        return False
    except Exception as e:
        print_log(e)
    return False


# 请求购物车信息,若不请求则服务器端购物车数据存在问题
def cartget():
    url = "https://yx.feiniu.com/cart-yxapp/shopcart/adminshopcart/cartget/t141"
    body = {
        "ticket_id": "",
        "store_id": store_id,
        "notNeedScallion": ""
    }
    try:
        res = requests.post(url=url, data=sign(body), headers=headers, timeout=(3.05, 6.05)).json()
        if res['errorCode'] == 0:
            if res['body']['total_items'] == 0:
                print_log(f'购物车中无有效商品!')
                sys.exit(0)
            print_log('Success!')
            return True
        elif res['errorCode'] == 20103 or res['errorCode'] == 1000:
            print_log(res['errorDesc'])
        else:
            print_log(res['errorDesc'])
            print_log(res)
        return False
    except Exception as e:
        print_log(e)
    return False


# 刷新购物车:全选+请求数据直到成功
def refresh_cart():
    while not allselect():
        pass
    while not cartget():
        pass
    print_log('购物车刷新成功!')


# 检查是否有未付款订单
def orderlist():
    url = "https://yx.feiniu.com/member-yxapp/order/list/t141"
    body = {
        "type": "1",
        "index": 1,
        "size": 10,
        "keyWorlds": ""
    }
    try:
        res = requests.post(url=url, data=sign(body), headers=headers, timeout=(3.05, 6.05)).json()
        if res['errorCode'] == 0:
            count = res['body']['count']
            if count:
                print_log(f'存在{count}笔未支付订单,请尽快付款!')
                sys.exit(0)
            print_log('不存在未支付订单!')
            return True
        elif res['errorCode'] == 20103 or res['errorCode'] == 1000:
            print_log(res['errorDesc'])
        else:
            print_log(res['errorDesc'])
            print_log(res)
        return False
    except Exception as e:
        print_log(e)
    return False


# 结算页面,同时返回可配送时间、优惠券信息
def getdeliveryTimeList():
    url = "https://yx.feiniu.com/cart-yxapp/account/details/t141"
    body = {
        "lat": lat,
        "lng": lng,
        "store_id": store_id,
        "addrId": addrId,
        "pay_code": "45",
        "revoke_default_voucher": 1,  # 默认不自动选择优惠券
        "is_remove_changed": 0,
        "deleteSelectAddr": "0",
        "orderNotesId": "",
        "positionLat": positionLat,
        "positionLng": positionLng,
        "autoChooseProof": 1,
        "storeCardUsed": "",
        "phone_model": "microsoft",
        "freshVoucherSeqs": {},
        "itemsVoucherSeqs": {},
        "proofSeqs": {},
        "deductVoucherSeqs": {},
        "packageExpress": {}
    }
    try:
        res = requests.post(url=url, data=sign(body), headers=headers, timeout=(3.05, 6.05)).json()
        global packageId, packageName, deliveryTimeList, total_prices, freshVoucherSeqs, itemsVoucherSeqs, deductVoucherSeqs
        if res['errorCode'] == 0 and res['body']['packageList'] and res['body']['packageList'][0]['deliveryTimeList']:
            res = res['body']['packageList'][0]
            packageId = res['packageId']
            packageName = res['packageName']
            deliveryTimeList = res['deliveryTimeList'][0]
            print_log(deliveryTimeList)
            total_prices = res['packageAmount']['total_prices']
            # couponInfo = res['packageAmount']['couponInfo']
            # if 'seq' in couponInfo['voucher']:
            #     freshVoucherSeqs[couponInfo['voucher']['seq']] = packageId
            # if 'seq' in couponInfo['item']:
            #     itemsVoucherSeqs[couponInfo['item']['seq']] = packageId
            # if 'seq' in couponInfo['deduct']:
            #     deductVoucherSeqs[couponInfo['deduct']['seq']] = packageId
            return True
        elif res['errorCode'] == 0:
            print_log('No deliveryTime!')
            if res['body']['packageList']:
                total_prices = res['body']['packageList'][0]['packageAmount']['total_prices']
            return True
        elif res['errorCode'] == 20103 or res['errorCode'] == 1000:
            print_log(res['errorDesc'])
        elif res['errorCode'] == 20102:  # 商品异动,刷新购物车
            print_log(res['errorDesc'])
            refresh_cart()
        else:
            print_log(res['errorDesc'])
            print_log(res)
        return False
    except Exception as e:
        print_log(e)
    return False


# 创建订单
def createOrder(name, date, day, time, dayListScroll):
    global packageId, packageName
    real_time = time.split(' ')[0]
    url = "https://yx.feiniu.com/cart-yxapp/account/createOrder/t141"
    body = {
        "lat": lat,
        "lng": lng,
        "store_id": store_id,
        "addrId": addrId,
        "pay_code": "45",
        "revoke_default_voucher": 1,
        "is_remove_changed": 0,
        "deleteSelectAddr": "0",
        "orderNotesId": "",
        "positionLat": positionLat,
        "positionLng": positionLng,
        "autoChooseProof": 1,
        "storeCardUsed": "",
        "phone_model": "microsoft",
        "freshVoucherSeqs": freshVoucherSeqs,
        "itemsVoucherSeqs": itemsVoucherSeqs,
        "proofSeqs": {},
        "deductVoucherSeqs": deductVoucherSeqs,
        "packageExpress": {
            packageId: {
                "delivery_day": date,
                "delivery_time": real_time,
                "packageName": packageName,
                "packageId": packageId,
                "dayTxt": day,
                "dateTxt": date,
                "timeTxt": real_time,
                "oreTimeTxt": time,
                "dayTabIndex": 0,
                "dayListScroll": dayListScroll,
                "chooseTimeTxt": f"{day} {real_time}"
            }
        }
    }
    try:
        res = requests.post(url=url, data=sign(body), headers=headers, timeout=(3.05, 6.05)).json()
        global total_prices, goods_changed_flag, time_changed_flag
        if res['errorCode'] == 0:
            print_log(f'订单创建成功\n配送时间：{real_time}\n金额：{total_prices}元\n请尽快付款！！！')
            os._exit(0)
            return True
        elif res['errorCode'] == 20103 or res['errorCode'] == 1000:
            print_log(f"{time} {res['errorDesc']}")
        elif res['errorCode'] == 20102 or res['errorCode'] == 20107:  # 商品异动,刷新购物车
            print_log(f"{time} {res['errorDesc']}")
            goods_changed_flag = True
        elif res['errorCode'] == 20000:  # 配送时间变动
            print_log(f"{time} {res['errorDesc']}")
            time_changed_flag = True
        else:
            print_log(f"{time} {res['errorDesc']}")
            print_log(res)
        return False
    except Exception as e:
        print_log(e)
    return False


if __name__ == '__main__':
    # 获取收货地址信息,默认选择列表第一个,因此建议只留一个地址
    while not addrId:
        getAddressList()
    # 根据地址选择店铺,可能存在多家店铺,在配置文件中修改
    while not store_id:
        homeStoreList(userInfo['store'])
    # 检查是否有未支付订单
    while not orderlist():
        pass
    # 刷新购物车
    refresh_cart()
    # 获取可配送时间
    while not deliveryTimeList:
        getdeliveryTimeList()
    i = 1
    threads = []
    thread_max_nums = 7
    while True:
        if goods_changed_flag:
            refresh_cart()
            goods_changed_flag = False
        if time_changed_flag:
            while not getdeliveryTimeList():
                pass
            time_changed_flag = False
        for k, item_time in enumerate(deliveryTimeList['times']):
            t = multi_thread(i, f"thread_{i}", deliveryTimeList['date'], deliveryTimeList['day'], item_time,
                             101 * (k + 1))
            t.start()
            threads.append(t)
            if threading.activeCount() > thread_max_nums:  # 限制最多线程个数
                for j in range(i):
                    threads[j].join()
                print_log(f"当前最大线程数:{thread_max_nums}")
            i += 1
