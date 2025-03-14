import os
import streamlit as st
import pandas as pd
import datetime
import toml

# ============ 数据文件定义 ============
XP_FILE = "xp_data.csv"              # 存「累计经验(accumulated_xp)」与「可用经验(current_xp)」
TASKS_FILE = "tasks.csv"             # 存任务
REWARDS_FILE = "rewards.csv"         # 存"可兑换奖励"列表
REDEEMED_FILE = "redeemed_rewards.csv"   # 存"已兑换奖励"列表

# 读取 config.toml 里的密码
try:
    config = toml.load("config.toml")
    CORRECT_PASSWORD = config["auth"]["password"]
except Exception as e:
    st.error(f"读取配置文件失败：{e}")
    CORRECT_PASSWORD = "password"  # 默认密码

# **确保 session_state 存在**
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False  # 记录用户是否登录

# **如果尚未登录，显示密码输入框**
if not st.session_state["authenticated"]:
    st.title("🔒 登录")
    pwd = st.text_input("🔑 请输入密码：", type="password")

    if st.button("登录"):
        if pwd == CORRECT_PASSWORD:
            st.session_state["authenticated"] = True  # 设为已登录
            st.experimental_set_query_params(auth="true")  # 记录 URL 状态
            st.success("✅ 登录成功！")
            st.rerun()  # **刷新页面，隐藏密码输入框**
        else:
            st.error("❌ 密码错误！")

    # **停止执行，避免未登录时加载主界面**
    st.stop()

# **登录成功后，加载主界面**
st.success("🎉 欢迎回来！ 你已成功登录")

# **登出按钮**
if st.button("🔓 退出登录"):
    st.session_state["authenticated"] = False
    st.experimental_set_query_params(auth="false")  # 清除 URL 记录
    st.rerun()  # **刷新页面，回到登录界面**

# ============ 1. 初始化/修正 XP_FILE ============
if not os.path.exists(XP_FILE):
    print(f"⚠️ 警告: 经验值数据文件 {XP_FILE} 不存在，创建默认文件。")
    xp_df = pd.DataFrame({"accumulated_xp": [0], "current_xp": [0]})
    xp_df.to_csv(XP_FILE, index=False)
else:
    try:
        xp_df = pd.read_csv(XP_FILE, on_bad_lines='skip')
        print("✅ 经验值数据文件加载成功")
    except pd.errors.EmptyDataError:
        print(f"❌ 读取 {XP_FILE} 时数据为空，创建默认数据。")
        xp_df = pd.DataFrame({"accumulated_xp": [0], "current_xp": [0]})
        xp_df.to_csv(XP_FILE, index=False)
    except Exception as e:
        print(f"❌ 读取 {XP_FILE} 失败: {e}")
        xp_df = pd.DataFrame({"accumulated_xp": [0], "current_xp": [0]})


    # 确保两列都存在
    for col in ["accumulated_xp", "current_xp"]:
        if col not in xp_df.columns:
            xp_df[col] = 0
    xp_df.to_csv(XP_FILE, index=False)

# 确保读取的值为整数类型
accumulated_xp = int(xp_df.at[0, "accumulated_xp"])
current_xp = int(xp_df.at[0, "current_xp"])

# ============ 2. 初始化/修正 TASKS_FILE ============
if not os.path.exists(TASKS_FILE):
    tasks_df = pd.DataFrame(columns=["分类", "任务名称", "经验值", "截止日期", "完成次数"])
    tasks_df.to_csv(TASKS_FILE, index=False)
else:
    try:
        tasks_df = pd.read_csv(TASKS_FILE)
        # 补列
        if "截止日期" not in tasks_df.columns:
            tasks_df["截止日期"] = ""
        if "完成次数" not in tasks_df.columns:
            tasks_df["完成次数"] = 0
        tasks_df.to_csv(TASKS_FILE, index=False)
    except Exception as e:
        print(f"❌ 读取 {TASKS_FILE} 失败: {e}")
        tasks_df = pd.DataFrame(columns=["分类", "任务名称", "经验值", "截止日期", "完成次数"])
        tasks_df.to_csv(TASKS_FILE, index=False)

# ============ 3. 初始化/修正 REWARDS_FILE (可兑换奖励) ============
if not os.path.exists(REWARDS_FILE):
    rewards_df = pd.DataFrame(columns=["奖励名称", "经验值消耗"])
    rewards_df.to_csv(REWARDS_FILE, index=False)
else:
    try:
        # 读取 CSV，并尝试修复潜在问题
        rewards_df = pd.read_csv(REWARDS_FILE, encoding="utf-8")

        # 修复数据格式
        rewards_df["奖励名称"] = rewards_df["奖励名称"].astype(str).str.strip()

        # 强制转换"经验值消耗"列为整数
        rewards_df["经验值消耗"] = (
            rewards_df["经验值消耗"]
            .astype(str)  # 先转换为字符串，避免数据类型错误
            .str.replace(r"[^\d]", "", regex=True)  # 只保留数字，去除任何可能的特殊字符
        )

        # 尝试转换为整数，如果失败则填充 0
        rewards_df["经验值消耗"] = pd.to_numeric(rewards_df["经验值消耗"], errors="coerce").fillna(0).astype(int)

    except Exception as e:
        print(f"❌ 读取 {REWARDS_FILE} 失败: {e}")
        rewards_df = pd.DataFrame(columns=["奖励名称", "经验值消耗"])  # 读取失败时创建默认 DataFrame

# 确保 rewards_df 结构完整
for col in ["奖励名称", "经验值消耗"]:
    if col not in rewards_df.columns:
        rewards_df[col] = 0 if col == "经验值消耗" else ""

# 写回 CSV，确保数据格式统一
rewards_df.to_csv(REWARDS_FILE, index=False)

# ============ 4. 初始化/修正 REDEEMED_FILE (已兑换奖励) ============
if not os.path.exists(REDEEMED_FILE):
    # 存储"已兑换奖励"的信息：奖励名称, 经验值消耗, 已兑换次数
    redeemed_df = pd.DataFrame(columns=["奖励名称", "经验值消耗", "已兑换次数"])
    redeemed_df.to_csv(REDEEMED_FILE, index=False)
else:
    try:
        redeemed_df = pd.read_csv(REDEEMED_FILE)
        for col in ["奖励名称", "经验值消耗", "已兑换次数"]:
            if col not in redeemed_df.columns:
                redeemed_df[col] = 0 if col in ["经验值消耗", "已兑换次数"] else ""
        redeemed_df.to_csv(REDEEMED_FILE, index=False)
    except Exception as e:
        print(f"❌ 读取 {REDEEMED_FILE} 失败: {e}")
        redeemed_df = pd.DataFrame(columns=["奖励名称", "经验值消耗", "已兑换次数"])
        redeemed_df.to_csv(REDEEMED_FILE, index=False)

# ============ Streamlit 界面开始 ============

st.title("🌟 白鸟的数据 🌟")

# ---- A. 手动调整经验值 ----
st.sidebar.header("🔧 经验值管理")

acc_change = st.sidebar.number_input(
    "调整【累计总经验】(±)",
    min_value=-999999, max_value=999999, step=1, value=0
)
cur_change = st.sidebar.number_input(
    "调整【可用经验】(±)",
    min_value=-999999, max_value=999999, step=1, value=0
)

if st.sidebar.button("应用调整"):
    # 第一部分：调整累计总经验
    if acc_change != 0:
        # 如果不允许累计总经验变成负数
        if accumulated_xp + acc_change < 0:
            st.sidebar.error("累计总经验不能低于0，操作无效")
        else:
            accumulated_xp += acc_change

    # 第二部分：调整可用经验
    if cur_change != 0:
        # 如果不允许可用经验变负
        if current_xp + cur_change < 0:
            st.sidebar.error("可用经验不能低于0，操作无效")
        else:
            current_xp += cur_change

    # 最后写回CSV
    xp_df.at[0, "accumulated_xp"] = accumulated_xp
    xp_df.at[0, "current_xp"] = current_xp
    xp_df.to_csv(XP_FILE, index=False)

    st.sidebar.success(f"成功调整：累计经验 {acc_change} / 可用经验 {cur_change}")
    st.rerun()

# ---- B. 任务管理 ----
st.sidebar.header("📝 任务管理")
category_options = ["每日任务", "每周任务", "期间限定任务"]
new_category = st.sidebar.selectbox("选择任务分类", category_options)
new_task = st.sidebar.text_input("新增任务名称")
new_xp = st.sidebar.number_input("任务经验值", min_value=1, max_value=500, step=1, value=10)

if new_category == "期间限定任务":
    new_deadline = st.sidebar.date_input("截止日期（仅限期间限定任务）", min_value=datetime.date.today())
else:
    new_deadline = ""

if st.sidebar.button("添加任务"):
    if not new_task.strip():
        st.sidebar.error("任务名称不能为空！")
    else:
        tasks_df = pd.concat([
            tasks_df,
            pd.DataFrame([{
                "分类": new_category,
                "任务名称": new_task.strip(),
                "经验值": new_xp,
                "截止日期": str(new_deadline) if new_category == "期间限定任务" else "",
                "完成次数": 0
            }])
        ], ignore_index=True)
        tasks_df.to_csv(TASKS_FILE, index=False)
        st.sidebar.success(f"任务 '{new_task}' 已添加！")
        st.rerun()

# ---- C. 展示任务列表 & 完成任务 ----
st.subheader("📋 任务列表")
grouped = tasks_df.groupby("分类")

for category, group in grouped:
    st.write(f"### {category}")  # 小标题

    for idx, row in group.iterrows():
        tname = row["任务名称"]
        txp = row["经验值"]
        tdone = row["完成次数"]
        tdeadline = row["截止日期"]

        # 如果是"期间限定任务"且有截止日期，显示剩余天数
        if category == "期间限定任务" and tdeadline:
            try:
                d = datetime.datetime.strptime(tdeadline, "%Y-%m-%d").date()
                days_left = (d - datetime.date.today()).days
                st.write(f"**{tname}** | 经验+{txp} | 已完成 {tdone} 次 | 剩余 {days_left} 天")
            except:
                st.write(f"**{tname}** | 经验+{txp} | 已完成 {tdone} 次 | 截止日期异常：{tdeadline}")
        else:
            st.write(f"**{tname}** | 经验+{txp} | 已完成 {tdone} 次")

        # 完成任务按钮（加上 key 避免重复 ID）
        if st.button(f"完成【{tname}】", key=f"complete_{category}_{idx}"):
            # 完成次数+1
            tasks_df.loc[idx, "完成次数"] += 1
            tasks_df.to_csv(TASKS_FILE, index=False)

            # "累计经验"与"可用经验"都增加
            accumulated_xp += txp
            current_xp += txp
            xp_df.at[0, "accumulated_xp"] = accumulated_xp
            xp_df.at[0, "current_xp"] = current_xp
            xp_df.to_csv(XP_FILE, index=False)

            st.success(f"任务 {tname} 完成！经验+{txp}")
            st.rerun()

# ---- D. 删除任务 ----
st.sidebar.header("🗑 删除任务")
if len(tasks_df) > 0:
    del_task_name = st.sidebar.selectbox("选择要删除的任务", tasks_df["任务名称"].tolist())
    if st.sidebar.button("删除所选任务"):
        tasks_df = tasks_df[tasks_df["任务名称"] != del_task_name]
        tasks_df.to_csv(TASKS_FILE, index=False)
        st.sidebar.success(f"任务 '{del_task_name}' 已删除！")
        st.rerun()

# ---- E. 显示经验值信息 ----
st.subheader("📊 经验值进度")

progress_value = current_xp % 100 / 100.0
st.progress(progress_value)
st.write(f"**当前可用经验：{current_xp}**")
st.write(f"**累计总经验：{accumulated_xp}** (不受兑换影响)")

# ---- F. 奖励系统：添加 / 查看 / 兑换 / 删除 ----
st.subheader("🎁 奖励兑换")

# (F1) 新增奖励
st.sidebar.header("🎁 奖励管理")
new_reward_name = st.sidebar.text_input("奖励名称")
new_reward_cost = st.sidebar.number_input("奖励经验值消耗", min_value=1, max_value=9999, step=1, value=50)

if st.sidebar.button("添加新奖励"):
    if not new_reward_name.strip():
        st.sidebar.error("奖励名称不能为空！")
    else:
        # 添加到"可兑换奖励"列表
        new_row = pd.DataFrame([{
            "奖励名称": new_reward_name.strip(),
            "经验值消耗": new_reward_cost
        }])
        rewards_df = pd.concat([rewards_df, new_row], ignore_index=True)
        rewards_df.to_csv(REWARDS_FILE, index=False)
        st.sidebar.success(f"奖励 '{new_reward_name}' 已添加！")
        st.rerun()

# (F2) 删除奖励（从可兑换奖励列表移除）
if not rewards_df.empty:
    st.sidebar.write("———")
    del_reward_name = st.sidebar.selectbox("删除可兑换奖励", rewards_df["奖励名称"].tolist())
    if st.sidebar.button("删除所选可兑换奖励"):
        rewards_df = rewards_df[rewards_df["奖励名称"] != del_reward_name]
        rewards_df.to_csv(REWARDS_FILE, index=False)
        st.sidebar.success(f"奖励 '{del_reward_name}' 已从可兑换列表删除！")
        st.rerun()

if "redeemed_flags" not in st.session_state:
    st.session_state["redeemed_flags"] = {}

import streamlit as st
import pandas as pd

# 假设已经定义了 XP_FILE, REDEEMED_FILE, rewards_df, xp_df, redeemed_df, current_xp

# 初始化 redeemed_flags
if "redeemed_flags" not in st.session_state:
    st.session_state["redeemed_flags"] = {}

def redeem_reward(idx, rname, rcost):
    global current_xp, xp_df, redeemed_df
    if current_xp >= rcost:
        # 设置标志位，防止重复触发
        st.session_state["redeemed_flags"][idx] = True

        # 扣减可用经验
        current_xp -= rcost
        xp_df.at[0, "current_xp"] = current_xp
        xp_df.to_csv(XP_FILE, index=False)

        # 更新已兑换记录
        existing = redeemed_df[redeemed_df["奖励名称"] == rname]
        if len(existing) > 0:
            rid = existing.index[0]
            redeemed_df.at[rid, "已兑换次数"] += 1
        else:
            new_redeem = pd.DataFrame([{
                "奖励名称": rname,
                "经验值消耗": rcost,
                "已兑换次数": 1
            }])
            redeemed_df = pd.concat([redeemed_df, new_redeem], ignore_index=True)
        redeemed_df.to_csv(REDEEMED_FILE, index=False)

        st.success(f"成功兑换奖励：{rname}！消耗 {rcost} 可用经验")
        st.rerun()  # 重新运行脚本，更新 UI
    else:
        st.error(f"经验值不足！需要 {rcost} 点经验，当前只有 {current_xp} 点")

import streamlit as st
import pandas as pd
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 假设已经定义了 XP_FILE, REDEEMED_FILE, rewards_df, xp_df, redeemed_df

# 初始化 current_xp
if "current_xp" not in st.session_state:
    st.session_state["current_xp"] = xp_df.at[0, "current_xp"]

current_xp = st.session_state["current_xp"]

# (F3) 显示 “可兑换奖励” 列表
if rewards_df.empty:
    st.write("**当前暂无可兑换奖励**")
else:
    st.write("### 可兑换奖励")
    for idx, rrow in rewards_df.iterrows():
        rname = rrow["奖励名称"]
        try:
            rcost = int(rrow["经验值消耗"])  # 确保 rcost 是整数
        except (ValueError, TypeError):
            st.error(f"奖励 '{rname}' 的经验值消耗无效，已跳过")
            continue

        st.write(f"- {rname} (消耗 {rcost} 可用经验)")

        # 替换你的 `st.button()` 逻辑
        if f"button_clicked_{idx}" not in st.session_state:
            st.session_state[f"button_clicked_{idx}"] = False

        if st.button(f"兑换 {rname}", key=f"redeem_{idx}") and not st.session_state[f"button_clicked_{idx}"]:
            st.session_state[f"button_clicked_{idx}"] = True  # 防止重复执行
            if current_xp >= rcost:
                new_xp = current_xp - rcost
                try:
                    # 再次校验经验值
                    updated_xp_df = pd.read_csv(XP_FILE)
                    if updated_xp_df.at[0, "current_xp"] != current_xp:
                        st.error("经验值已发生变化，请刷新页面！")
                        logging.error("经验值校验失败！")
                        break

                    xp_df.at[0, "current_xp"] = new_xp
                    xp_df.to_csv(XP_FILE, index=False)
                    st.success(f"兑换成功！剩余经验值：{new_xp}")

                    # 更新 session_state
                    st.session_state["current_xp"] = new_xp
                    current_xp = new_xp

                    # 更新已兑换奖励列表
                    existing = redeemed_df[redeemed_df["奖励名称"] == rname]
                    if len(existing) > 0:
                        rid = existing.index[0]
                        redeemed_df.at[rid, "已兑换次数"] += 1
                    else:
                        new_redeem = pd.DataFrame([{
                            "奖励名称": rname,
                            "经验值消耗": rcost,
                            "已兑换次数": 1
                        }])
                        redeemed_df = pd.concat([redeemed_df, new_redeem], ignore_index=True)

                    redeemed_df.to_csv(REDEEMED_FILE, index=False)

                    # 确保 UI 刷新但不触发二次执行
                    st.rerun()  # 替换为 st.rerun()
                except Exception as e:
                    st.error(f"兑换奖励时出错：{e}")
                    logging.error(f"兑换奖励时出错：{e}")
            else:
                st.error("经验值不足，无法兑换！")
                logging.error("经验值不足，无法兑换！")




# (F4) "已兑换奖励"表展示 & 删除
st.write("### 已获得的奖励统计")
if redeemed_df.empty:
    st.write("你还没有兑换任何奖励哦~")
else:
    st.dataframe(redeemed_df)

    # 在侧边栏增加 删除操作
    st.sidebar.header("🗑 删除已兑换的记录")
    if not redeemed_df.empty:
        del_redeem_name = st.sidebar.selectbox(
            "选择要删除的'已兑换奖励'",
            redeemed_df["奖励名称"].tolist()
        )
        if st.sidebar.button("删除所选已兑换"):
            redeemed_df = redeemed_df[redeemed_df["奖励名称"] != del_redeem_name]
            redeemed_df.to_csv(REDEEMED_FILE, index=False)
            st.sidebar.success(f"已删除 '{del_redeem_name}' 的兑换记录！")
            st.rerun()
