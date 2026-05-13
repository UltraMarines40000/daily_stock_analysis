#!/usr/bin/env python
# coding: utf-8
import requests
import pandas as pd
import json
import re
import time
from datetime import datetime
from datetime import date,timedelta

# -------------------------- 公共配置 --------------------------
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://vipmoney.eastmoney.com/",
    "Content-Type": "application/json"
}

MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.99 Mobile Safari/537.36",
    "Referer": "https://vipmoney.eastmoney.com/",
    "Content-Type": "application/json"
}

# -------------------------- 公共工具函数 --------------------------
def get_dynamic_params():
    try:
        return {
            "ut": "f057cbcbce2a86e2866ab8877db1d059",
            "globalId": "786e4c21-70dc-435a-93bb-38"
        }
    except Exception as e:
        print(f"获取参数失败: {e}")
        return None

def parse_json_response(response_text):
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        match = re.search(r'\((.*?)\)', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                return None
        return None

def send_post_request(url, headers, payload):
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return parse_json_response(response.text)
    except Exception as e:
        print(f"POST请求失败: {e}")
        return None

def send_get_request(url, headers, params):
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"GET请求失败: {e}")
        return None

def format_dataframe(df, column_mapping, has_timestamp=True, has_percent=True):
    if df.empty:
        return df
    
    for k, v in column_mapping.items():
        if k in df.columns:
            df.rename(columns={k: v}, inplace=True)
    
    if has_percent and "涨跌幅" in df.columns:
        df["涨跌幅"] = df["涨跌幅"].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")
    
    if has_timestamp and "更新时间戳" in df.columns:
        df["更新时间"] = pd.to_datetime(df["更新时间戳"], unit='ms', errors='coerce')
        df.drop(columns=["更新时间戳"], inplace=True, errors='ignore')
    
    return df

# -------------------------- 核心业务函数 --------------------------
def normalize_eastmoney_stock_code(raw_code):
    code = str(raw_code or "").strip().upper()
    if code.startswith(("SH", "SZ", "BJ")) and code[2:].isdigit():
        return code[2:]
    if "." in code:
        base, suffix = code.rsplit(".", 1)
        if suffix in ("SH", "SZ", "BJ") and base.isdigit():
            return base
    return code


def get_eastmoney_popularity_top100(limit=5):
    params = get_dynamic_params()
    if not params:
        return None

    url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
    payload = {
        "appId": "appId01",
        "globalId": params["globalId"],
        "marketType": "",
        "pageNo": 1,
        "pageSize": limit,
        "sort": "1",
        "ut": params["ut"],
        "version": "6.9.9"
    }

    data = send_post_request(url, COMMON_HEADERS, payload)
    if not data or not isinstance(data.get("data"), list):
        print("人气榜数据为空")
        return None

    df = pd.DataFrame(data["data"])
    mapping = {"sc": "股票代码", "n": "股票名称", "p": "当前价格", "pc": "涨跌幅", "rk": "排名", "t": "更新时间戳"}
    return format_dataframe(df, mapping)


def get_eastmoney_popularity_codes(limit=5):
    df = get_eastmoney_popularity_top100(limit=limit)
    if df is None or df.empty or "股票代码" not in df.columns:
        return []
    codes = []
    for value in df["股票代码"].tolist():
        code = normalize_eastmoney_stock_code(value)
        if code and code not in codes:
            codes.append(code)
    return codes[:limit]


# def get_eastmoney_lhb_data(date=None):
#     date = date or datetime.now().strftime('%Y-%m-%d')
#     url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    
#     headers = COMMON_HEADERS.copy()
#     headers["Referer"] = "https://data.eastmoney.com/lhb/"

#     params = {
#         "sortColumns": "SECURITY_CODE",
#         "sortTypes": "1",
#         "pageSize": 100,
#         "pageNumber": 1,
#         "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
#         "columns": "ALL",
#         "source": "WEB",
#         "filter": f"(TRADE_DATE='{date}')"
#     }

#     data = send_get_request(url, headers, params)
#     if not data or not data.get("result", {}).get("data"):
#         print(f"{date} 无龙虎榜数据")
#         return None

#     df = pd.DataFrame(data["result"]["data"])
#     mapping = {
#         "SECURITY_CODE": "股票代码",
#         "SECURITY_NAME_ABBR": "股票名称",
#         "EXPLAIN": "上榜原因",
#         "CHANGE_RATE": "涨跌幅",
#         "NET_BUY": "净买入额"
#     }
#     df = format_dataframe(df, mapping, has_timestamp=False, has_percent=False)
    
#     if "净买入额" in df.columns:
#         df["净买入额"] = df["净买入额"].apply(lambda x: f"{x/10000:.2f}万" if pd.notnull(x) else "-")
#     if "涨跌幅" in df.columns:
#         df["涨跌幅"] = df["涨跌幅"].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")
    
#     return df

# -------------------------- 运行 --------------------------
if __name__ == "__main__":
    now = datetime.now()
    formatted_datetime = now.strftime("%Y-%m-%d")
    today = date.today()
    yesterday = today - timedelta(days=1)
    yesterday = "2026-05-11"
    print("前一天日期:", yesterday)
    print("="*50)
    df1 = get_eastmoney_popularity_top100()
    if df1 is not None:
        print(f"人气榜前{len(result)}名")
        print(df1.to_string(index=False))

    print("="*50)
#     df2 = get_eastmoney_lhb_data(yesterday)
#     if df2 is not None:
#         print("龙虎榜")
#         cols_to_show = ["股票代码", "股票名称", "上榜原因", "涨跌幅", "净买入额", "买一营业部"]
#         available_cols = [c for c in cols_to_show if c in df2.columns]
#         print(df2[available_cols].head(100).to_string(index=False))
# #         print(df2.to_string(index=False))
