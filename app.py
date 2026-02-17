import sys
import os
import streamlit as st
from io import StringIO
from contextlib import contextmanager, redirect_stdout
import pendulum as pdlm
import urllib, calendar

# 引入专业历法库
from lunar_python import Solar, Lunar

# --- 1. 核心路径与全局定义 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入本地零件
try:
    import liuren_core as kinliuren 
    import jieqi
    import config
    import angan
    from bidict import bidict
except Exception as e:
    st.error(f"核心零件加载提示: {e}")

# 全局干支列表（修复 NameError 的关键）
GAN = list("甲乙丙丁戊己庚辛壬癸")
ZHI = list("子丑寅卯辰巳午未申酉戌亥")

# 数字映射选项
GAN_OPTIONS = [f"{g} ({i+1})" for i, g in enumerate(GAN)]
ZHI_OPTIONS = [f"{z} ({i+1})" for i, z in enumerate(ZHI)]

@contextmanager
def st_capture(output_func):
    with StringIO() as stdout, redirect_stdout(stdout):
        old_write = stdout.write
        def new_write(string):
            ret = old_write(string)
            output_func(stdout.getvalue())
            return ret
        stdout.write = new_write
        yield

# --- 2. 演禽计算辅助函数 ---
def multi_key_dict_get(d, k):
    for keys, v in d.items():
        if k in keys: return v
    return None

def new_list(olist, o):
    zhihead_code = olist.index(o)
    return [olist[ (zhihead_code + i) % len(olist) ] for i in range(len(olist))]

def get_weekday_name(y, m, d):
    cweekdays = ["星期"+i for i in list("日一二三四五六")]
    try:
        dayNumber = calendar.weekday(y, m, d)
        return dict(zip([int(i) for i in list("6012345")], cweekdays)).get(dayNumber)
    except: return "星期一"

def day_chin(zhi, weekday_str):
    three_zhi = "申子辰,巳酉丑,寅午戌,亥卯未".split(",")
    head = ["虛畢翼箕奎鬼氐", "房危觜軫斗婁柳", "星心室參角牛胃", "昴張尾壁井亢女"]
    cweekdays = ["星期"+i for i in list("日一二三四五六")]
    ydict = {}
    for i in range(4):
        b = {tuple(list(three_zhi[i])): dict(zip(cweekdays , list(head[i])))}
        ydict.update(b)
    res = multi_key_dict_get(ydict, zhi)
    return res.get(weekday_str) if res else "虛"

# --- 3. 界面配置 ---
st.set_page_config(layout="wide", page_title="堅六壬 - 專業研究終極版", page_icon="icon.jpg")
now_dt = pdlm.now(tz='Asia/Shanghai')

tab_pan, tab_search = st.tabs(['🔮 核心排盤 (正時/研究)', '🔍 八字精確反推'])

# --- 4. 核心排盘模块 ---
with tab_pan:
    col_side, col_main = st.columns([1, 3])
    with col_side:
        st.header("⏳ 時間輸入")
        input_mode = st.radio("歷法選擇", ["公曆 (Solar)", "農曆 (Lunar)"], horizontal=True)
        y = st.number_input("年份 (負數為公元前)", -4000, 3000, now_dt.year)
        if input_mode == "公曆 (Solar)":
            m, d = st.number_input("月份", 1, 12, now_dt.month), st.number_input("日期", 1, 31, now_dt.day)
            is_leap = False
        else:
            temp_l = Solar.fromYmd(now_dt.year, now_dt.month, now_dt.day).getLunar()
            m, d = st.number_input("農曆月", 1, 12, abs(temp_l.getMonth())), st.number_input("農曆日", 1, 30, temp_l.getDay())
            is_leap = st.checkbox("是否為閏月")
        h, minute = st.number_input("小時 (時辰)", 0, 23, now_dt.hour), st.number_input("分鐘", 0, 59, now_dt.minute)
        if st.button("現在時間"): st.rerun()

    with col_main:
        try:
            if input_mode == "公曆 (Solar)":
                solar_obj = Solar.fromYmdHms(y, m, d, h, minute, 0)
                lunar_obj = solar_obj.getLunar()
            else:
                lunar_obj = Lunar.fromYmdHms(y, -m if is_leap else m, d, h, minute, 0)
                solar_obj = lunar_obj.getSolar()
            
            jq_obj = lunar_obj.getPrevJieQi()
            jq_str = str(jq_obj.getName())
            cm = str(lunar_obj.getMonthInChinese()) + '月'
            gz_y, gz_m, gz_d, gz_t = str(lunar_obj.getYearInGanZhi()), str(lunar_obj.getMonthInGanZhi()), str(lunar_obj.getDayInGanZhi()), str(lunar_obj.getTimeInGanZhi())
            st.info(f"🗓️ **核對：{gz_y}年 {gz_m}月 {gz_d}日 {gz_t}時 ({jq_str})**")
            
            # 排盘
            l_res = kinliuren.Liuren(jq_str, cm, gz_d, gz_t).result_d(0)
            
            # 演禽计算
            w_day = get_weekday_name(solar_obj.getYear(), solar_obj.getMonth(), solar_obj.getDay())
            d_宿 = day_chin(gz_d[1], w_day)
            zdict = dict(zip(ZHI, range(1, 13)))
            chin_list = list('角亢氐房心尾箕斗牛女虛危室壁奎婁胃昴畢觜參井鬼柳星張翼軫')
            rotated_chins = new_list(chin_list, d_宿)
            home_禽 = rotated_chins[(zdict[gz_t[1]] + (1 if minute > 30 else 0)) % 28] 
            away_禽 = rotated_chins[zdict[gz_t[1]] % 28]
            try:
                gui_loc = bidict(l_res.get("地轉天將")).inverse["貴"]
                tp = l_res.get("地轉天盤")
                sky_gui = tp.get(gui_loc)
                sky_禽 = rotated_chins[(zdict[gui_loc] + zdict[sky_gui]) % 28]
            except: sky_禽 = "--"

            output_area = st.empty()
            with st_capture(output_area.code):
                print(f"【堅六壬·排盤結果】")
                print(f"格局：{l_res.get('格局',['--'])[0]}")
                print(f"旬空：{lunar_obj.getDayXunKong()} | 日馬：{l_res.get('日馬','--')}")
                print("-" * 45)
                sc, k = l_res.get("三傳", {}), l_res.get('四課', {})
                def sk(kn, r):
                    try: return k[kn][0][r]
                    except: return " "
                print(f"【三傳】　　　　　　【四課】")
                print(f"初傳：{''.join(sc.get('初傳',''))}　　　　　{sk('四課',0)} {sk('三課',0)} {sk('二課',0)} {sk('一課',0)}")
                print(f"中傳：{''.join(sc.get('中傳',''))}　　　　　{sk('四課',1)} {sk('三課',1)} {sk('二課',1)} {sk('一課',1)}")
                print(f"末傳：{''.join(sc.get('末傳',''))}")
                print("-" * 45)
                print(f"【堅六壬用禽法】")
                print(f"地禽：{home_禽} (主) VS {away_禽} (客) | 天禽：{sky_禽}")
                print("-" * 45)
                tj, tp = l_res.get("地轉天將", {}), l_res.get("地轉天盤", {})
                def gp(p, z): return str(p.get(z)) if p.get(z) else "  "
                print(f"【天地盤佈局】")
                print(f"　　{gp(tj,'巳')}{gp(tp,'巳')} {gp(tj,'午')}{gp(tp,'午')} {gp(tj,'未')}{gp(tp,'未')} {gp(tj,'申')}{gp(tp,'申')}")
                print(f"　　{gp(tj,'辰')}{gp(tp,'辰')} 　　　　 {gp(tj,'酉')}{gp(tp,'酉')}")
                print(f"　　{gp(tj,'卯')}{gp(tp,'卯')} 　　　　 {gp(tj,'戌')}{gp(tp,'戌')}")
                print(f"　　{gp(tj,'寅')}{gp(tp,'寅')} {gp(tj,'丑')}{gp(tp,'丑')} {gp(tj,'子')}{gp(tp,'子')} {gp(tj,'亥')}{gp(tp,'亥')}")
        except Exception as e: st.error(f"排盤計算出錯: {e}")

# --- 5. 八字反推模块 ---
with tab_search:
    st.header("🔍 八字精確反推 (支持數字映射)")
    st.write("請選擇或輸入對應的干支編號（如：甲選1，子選1）")
    
    # 辅助转换函数
    def get_val(s): return s.split(" ")[0]

    r1, r2, r3, r4 = st.columns(4)
    with r1: 
        tyg = get_val(st.selectbox("年干 (1-10)", GAN_OPTIONS, index=2))
        tyz = get_val(st.selectbox("年支 (1-12)", ZHI_OPTIONS, index=4))
    with r2: 
        tmg = get_val(st.selectbox("月干 (1-10)", GAN_OPTIONS, index=6))
        tmz = get_val(st.selectbox("月支 (1-12)", ZHI_OPTIONS, index=2))
    with r3: 
        tdg = get_val(st.selectbox("日干 (1-10)", GAN_OPTIONS, index=2))
        tdz = get_val(st.selectbox("日支 (1-12)", ZHI_OPTIONS, index=8))
    with r4: 
        ttg = get_val(st.selectbox("時干 (1-10)", GAN_OPTIONS, index=9))
        ttz = get_val(st.selectbox("時支 (1-12)", ZHI_OPTIONS, index=5))
    
    s_y, e_y = st.number_input("起始年份", -2000, 2026, 1900), st.number_input("結束年份", -2000, 2026, 2026)
    
    if st.button("🚀 開始深度搜索"):
        target = [tyg+tyz, tmg+tmz, tdg+tdz, ttg+ttz]
        found = []
        progress = st.progress(0)
        total = e_y - s_y + 1
        for idx, curr_y in enumerate(range(s_y, e_y + 1)):
            if idx % 20 == 0: progress.progress((idx+1)/total)
            if Solar.fromYmd(curr_y, 6, 1).getLunar().getYearInGanZhi() == target[0]:
                for cur_m in range(1, 13):
                    for cur_d in range(1, 32):
                        try:
                            l = Solar.fromYmd(curr_y, cur_m, cur_d).getLunar()
                            if l.getMonthInGanZhi() == target[1] and l.getDayInGanZhi() == target[2]:
                                for h_v in range(0, 24, 2):
                                    lt = Solar.fromYmdHms(curr_y, cur_m, cur_d, h_v, 0, 0).getLunar()
                                    if lt.getTimeInGanZhi() == target[3]: found.append(f"📌 {lt.getSolar().toFullString()} (農曆 {lt.toString()})")
                        except: continue
        progress.progress(1.0)
        if found:
            st.success(f"找到 {len(found)} 個匹配日期：")
            for item in found: st.write(item)
        else: st.warning("未找到匹配日期。")