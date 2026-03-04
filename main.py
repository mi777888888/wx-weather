import json
import os
from datetime import date, datetime, timedelta

import requests
from lunardate import LunarDate
from wechatpy import WeChatClient
from wechatpy.client.api import WeChatMessage


def clean_env(v: str) -> str:
    """去空格 + 去一层首尾引号（避免 secrets 里误存 '\"xxx\"'）"""
    if v is None:
        return ""
    v = str(v).strip()
    if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
        v = v[1:-1].strip()
    return v


# ----------------------- 从环境变量读取配置 -----------------------
start_date = clean_env(os.getenv("START_DATE", "2025-06-04"))
appKey = clean_env(os.getenv("APP_KEY", "cb4b121913484d0090d506a70455945e"))
birthday = clean_env(os.getenv("BIRTHDAY", "2025-06-04"))

app_id = clean_env(os.getenv("APP_ID", "wx0b974221d291ec14"))
app_secret = clean_env(os.getenv("APP_SECRET", "066e9c8dedb348c51315ac8499ac8c7a"))

user_ids = clean_env(os.getenv("USER_IDS", "oJL-12FttD-OPz0dCc_QOR1jk7Gw"))
template_id_day = clean_env(os.getenv("TEMPLATE_ID_DAY", "he0mUm-aBE9UWzUmYzMGPCF_yyuPaD8keP26z7gt6Ho"))
template_id_night = clean_env(os.getenv("TEMPLATE_ID_NIGHT", "8GKqU099P3IdOEkOBa24CgpTFETx3WtwCUrUGDgNJ7Q"))

name = clean_env(os.getenv("NAME", "小高"))
city = clean_env(os.getenv("CITY", "北京"))

# 和风 Host：默认用你之前能访问到的专属 host；也允许你用 env 覆盖
qweather_host = clean_env(os.getenv("QWEATHER_HOST", "https://n93jpfeh9u.re.qweatherapi.com"))

required = {
    "APP_KEY": appKey,
    "APP_ID": app_id,
    "APP_SECRET": app_secret,
    "USER_IDS": user_ids,
    "TEMPLATE_ID_DAY": template_id_day,
    "TEMPLATE_ID_NIGHT": template_id_night,
}
missing = [k for k, v in required.items() if not v]
if missing:
    raise RuntimeError(f"Missing env vars: {', '.join(missing)}")


# ----------------------- 当前时间 -----------------------
today = datetime.now()
today_date = today.strftime("%Y年%m月%d日")


def http_get_json(url: str, params: dict, timeout: int = 15) -> dict:
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        safe_params = dict(params)
        if "key" in safe_params and safe_params["key"]:
            k = str(safe_params["key"])
            safe_params["key"] = (k[:4] + "***" + k[-4:]) if len(k) >= 8 else "***"
        print("---- HTTP ERROR ----")
        print("Request URL:", resp.url)
        print("Request params(safe):", safe_params)
        print("Status Code:", resp.status_code)
        print("Response Text:", resp.text)
        print("--------------------")
        raise RuntimeError(f"HTTP {resp.status_code} for {url}")
    return resp.json()


# ----------------------- 和风：城市 -> location id -----------------------
params = {"key": appKey, "location": city}
print({"key": "****", "location": city})  # 不泄露 key

geo_url = f"{qweather_host}/geo/v2/city/lookup"
geo_json = http_get_json(geo_url, params)

city_id = geo_json["location"][0]["id"]
params["location"] = city_id

# ----------------------- 和风：实时天气 -----------------------
now_url = f"{qweather_host}/v7/weather/now"
realtime_json = http_get_json(now_url, params)
realtime = realtime_json["now"]
now_temperature = realtime["temp"] + "℃" + realtime["text"]

# ----------------------- 和风：3天天气 -----------------------
forecast_url = f"{qweather_host}/v7/weather/3d"
day_forecast_json = http_get_json(forecast_url, params)

# ----------------------- 今天 -----------------------
day_forecast_today = day_forecast_json["daily"][0]
day_forecast_today_sunrise = day_forecast_today["sunrise"]
day_forecast_today_sunset = day_forecast_today["sunset"]
day_forecast_today_weather = day_forecast_today["textDay"]
day_forecast_today_temperature_min = day_forecast_today["tempMin"] + "℃"
day_forecast_today_temperature_max = day_forecast_today["tempMax"] + "℃"
day_forecast_today_night = day_forecast_today["textNight"]
day_forecast_today_windDirDay = day_forecast_today["windDirDay"]
day_forecast_today_windDirNight = day_forecast_today["windDirNight"]
day_forecast_today_windScaleDay = day_forecast_today["windScaleDay"]

# ----------------------- 明天（修复：不要再用 today 的字段） -----------------------
day_forecast_tomorrow = day_forecast_json["daily"][1]
day_forecast_tomorrow_weather = day_forecast_tomorrow["textDay"]
day_forecast_tomorrow_sunrise = day_forecast_tomorrow["sunrise"]
day_forecast_tomorrow_sunset = day_forecast_tomorrow["sunset"]
day_forecast_tomorrow_temperature_min = day_forecast_tomorrow["tempMin"] + "℃"
day_forecast_tomorrow_temperature_max = day_forecast_tomorrow["tempMax"] + "℃"
day_forecast_tomorrow_night = day_forecast_tomorrow["textNight"]
day_forecast_tomorrow_windDirDay = day_forecast_tomorrow["windDirDay"]
day_forecast_tomorrow_windDirNight = day_forecast_tomorrow["windDirNight"]
day_forecast_tomorrow_windScaleDay = day_forecast_tomorrow["windScaleDay"]


# 距离春节还有多少天
def days_until_spring_festival(year=None):
    if year is None:
        year = datetime.now().year
    spring_festival_lunar = LunarDate(year, 1, 1)
    spring_festival_solar = spring_festival_lunar.toSolarDate()
    today_date_only = datetime.now().date()
    days_until = (spring_festival_solar - today_date_only).days
    if days_until <= 0:
        return days_until_spring_festival(year + 1)
    return days_until


# 在一起多天计算
def get_count():
    delta = today - datetime.strptime(start_date, "%Y-%m-%d")
    return delta.days + 1


# 生日计算
def get_birthday():
    month_day = birthday[5:]
    nxt = datetime.strptime(f"{date.today().year}-{month_day}", "%Y-%m-%d")
    if nxt < datetime.now():
        nxt = nxt.replace(year=nxt.year + 1)
    return (nxt - today).days


# 彩虹屁接口
def get_words():
    words = requests.get("https://api.shadiao.pro/chp", timeout=15)
    if words.status_code != 200:
        return get_words()
    text = words.json().get("data", {}).get("text", "")
    chunk_size = 20
    split_notes = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    note1, note2, note3, note4, note5 = (split_notes + [""] * 5)[:5]
    return note1, note2, note3, note4, note5


def split_user_ids(raw: str):
    raw = (raw or "").strip()
    if ";" in raw:
        parts = [x.strip() for x in raw.split(";")]
    elif "," in raw:
        parts = [x.strip() for x in raw.split(",")]
    else:
        parts = [raw]
    return [p for p in parts if p]


if __name__ == "__main__":
    client = WeChatClient(app_id, app_secret)
    wm = WeChatMessage(client)

    note1, note2, note3, note4, note5 = get_words()

    now_utc = datetime.utcnow()
    beijing_time = now_utc + timedelta(hours=8)
    hour_of_day = beijing_time.hour

    strDay = "today"
    template_to_use = template_id_day
    if hour_of_day > 15:
        strDay = "tomorrow"
        template_to_use = template_id_night

    print("当前时间：" + str(beijing_time) + " 即将推送：" + strDay + " 信息")

    data = {
        "name": {"value": name},
        "today": {"value": today_date},
        "city": {"value": city},
        "weather": {"value": globals()[f"day_forecast_{strDay}_weather"]},
        "now_temperature": {"value": now_temperature},
        "min_temperature": {"value": globals()[f"day_forecast_{strDay}_temperature_min"]},
        "max_temperature": {"value": globals()[f"day_forecast_{strDay}_temperature_max"]},
        "love_date": {"value": get_count()},
        "birthday": {"value": get_birthday()},
        "diff_date1": {"value": days_until_spring_festival()},
        "sunrise": {"value": globals()[f"day_forecast_{strDay}_sunrise"]},
        "sunset": {"value": globals()[f"day_forecast_{strDay}_sunset"]},
        "textNight": {"value": globals()[f"day_forecast_{strDay}_night"]},
        "windDirDay": {"value": globals()[f"day_forecast_{strDay}_windDirDay"]},
        "windDirNight": {"value": globals()[f"day_forecast_{strDay}_windDirNight"]},
        "windScaleDay": {"value": globals()[f"day_forecast_{strDay}_windScaleDay"]},
        "note1": {"value": note1},
        "note2": {"value": note2},
        "note3": {"value": note3},
        "note4": {"value": note4},
        "note5": {"value": note5},
    }

    for uid in split_user_ids(user_ids):
        res = wm.send_template(uid, template_to_use, data)
        print(res)
