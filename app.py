import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import re

st.set_page_config(
    page_title="📊 Расходный дашборд",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Расходный дашборд")
st.caption(f"📆 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

DATA_URL = "https://script.google.com/macros/s/AKfycbxVXqV-y4qWfpfyp8MtrxApVqwuKWvbcxg0R1awJC81H06tM1efWpyTiP5O-DFq0tjTrA/exec"

@st.cache_data(ttl=300)
def load_data():
    try:
        response = requests.get(DATA_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        st.error(f"❌ Ошибка загрузки: {e}")
        return None

raw_data = load_data()
if raw_data is None:
    st.stop()

def parse_expenses(raw_data):
    result = {}
    all_months = set()
    
    for item in raw_data:
        for key in item.keys():
            if key != "Показатель":
                match = re.search(r'(\w{3}) (\w{3}) (\d{2}) (\d{4})', key)
                if match:
                    month_short = f"{match.group(4)}-{match.group(3)}"
                    all_months.add(month_short)
    
    sorted_months = sorted(list(all_months))
    
    for item in raw_data:
        label = item.get("Показатель", "")
        if not label:
            continue
            
        month_values = {}
        total = 0
        
        for key, value in item.items():
            if key != "Показатель" and isinstance(value, (int, float)) and value > 0:
                match = re.search(r'(\w{3}) (\w{3}) (\d{2}) (\d{4})', key)
                if match:
                    month_short = f"{match.group(4)}-{match.group(3)}"
                    month_values[month_short] = value
                    total += value
        
        if total > 0:
            result[label] = {
                "total": total,
                "months": month_values
            }
    
    return result, sorted_months

expenses, months = parse_expenses(raw_data)

if not expenses:
    st.warning("⚠️ Нет данных для отображения")
    st.stop()

st.sidebar.header("🔍 Фильтры")

categories = list(expenses.keys())
selected_cats = st.sidebar.multiselect(
    "📂 Категории расходов",
    options=categories,
    default=categories
)

max_val = int(max([v["total"] for v in expenses.values()])) if expenses else 100000
amount_range = st.sidebar.slider(
    "💰 Сумма (минимум)",
    min_value=0,
    max_value=max_val,
    value=0,
    step=1000
)

filtered = {}
for cat, cat_data in expenses.items():
    if cat in selected_cats and cat_data["total"] >= amount_range:
        filtered[cat] = cat_data

if not filtered:
    st.warning("⚠️ Нет данных с выбранными фильтрами")
    st.stop()

total_all = sum([v["total"] for v in filtered.values()])

st.subheader("📊 Ключевые показатели")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("💰 Всего расходов", f"{total_all:,.0f} ₽")

with col2:
    st.metric("📂 Категорий", len(filtered))

with col3:
    if filtered:
        max_cat = max(filtered.items(), key=lambda x: x[1]["total"])
        st.metric("🏆 Максимум", max_cat[0], f"{max_cat[1]['total']:,.0f} ₽")

with col4:
    avg = total_all / len(filtered) if filtered else 0
    st.metric("📊 Среднее на категорию", f"{avg:,.0f} ₽")

with col5:
    all_months_set = set()
    for cat_data in filtered.values():
        all_months_set.update(cat_data["months"].keys())
    st.metric("📅 Месяцев", len(all_months_set))

st.markdown("---")

st.subheader("🧩 Структура расходов по категориям")

col_chart1, col_chart2 = st.columns([2, 1])

with col_chart1:
    if filtered:
        pie_data = [{"Категория": k, "Сумма": v["total"]} for k, v in filtered.items()]
        df_pie = pd.DataFrame(pie_data).sort_values("Сумма", ascending=False)
        
        fig = px.pie(
            df_pie,
            values="Сумма",
            names="Категория",
            title="Распределение расходов",
            color_discrete_sequence=px.colors.qualitative.Set3,
            hover_data=["Сумма"]
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

with col_chart2:
    st.markdown("#### 🏆 Топ-5 категорий")
    top5 = df_pie.head(5) if not df_pie.empty else pd.DataFrame()
    for _, row in top5.iterrows():
        pct = (row["Сумма"] / total_all * 100) if total_all > 0 else 0
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #eee;">
            <span style="font-size: 14px;">{row['Категория']}</span>
            <span style="font-size: 14px; font-weight: bold;">{row['Сумма']:,.0f} ₽</span>
            <span style="font-size: 12px; color: #888;">{pct:.1f}%</span>
        </div>
        """, unsafe_allow_html=True)

st.subheader("📊 Сравнение категорий")

if filtered:
    bar_data = [{"Категория": k, "Сумма": v["total"]} for k, v in filtered.items()]
    df_bar = pd.DataFrame(bar_data).sort_values("Сумма", ascending=True)
    
    fig = px.bar(
        df_bar,
        x="Сумма",
        y="Категория",
        title="Расходы по категориям (горизонтальный)",
        color="Сумма",
        color_continuous_scale="Viridis",
        text="Сумма",
        orientation='h'
    )
    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

if months:
    st.subheader("📈 Динамика расходов по месяцам")
    
    dynamic_data = []
    for cat, cat_data in filtered.items():
        for month, val in cat_data["months"].items():
            if val > 0:
                dynamic_data.append({
                    "Категория": cat,
                    "Месяц": month,
                    "Сумма": val
                })
    
    if dynamic_data:
        df_dynamic = pd.DataFrame(dynamic_data)
        month_order = sorted(df_dynamic["Месяц"].unique())
        df_dynamic["Месяц"] = pd.Categorical(df_dynamic["Месяц"], categories=month_order, ordered=True)
        
        df_monthly = df_dynamic.groupby("Месяц")["Сумма"].sum().reset_index()
        
        fig = px.line(
            df_monthly,
            x="Месяц",
            y="Сумма",
            title="Общая динамика расходов",
            markers=True
        )
        fig.update_traces(line=dict(width=3))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📈 Детальная динамика по категориям")
        top_cats = sorted(filtered.items(), key=lambda x: x[1]["total"], reverse=True)[:5]
        top_cat_names = [c[0] for c in top_cats]
        df_top = df_dynamic[df_dynamic["Категория"].isin(top_cat_names)]
        
        fig = px.line(
            df_top,
            x="Месяц",
            y="Сумма",
            color="Категория",
            title="Динамика топ-5 категорий",
            markers=True
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Детализация по категориям")

selected_cat = st.selectbox(
    "Выберите категорию для детализации",
    options=list(filtered.keys())
)

if selected_cat and selected_cat in filtered:
    cat_data = filtered[selected_cat]
    
    if cat_data["months"]:
        df_detail = pd.DataFrame([
            {"Месяц": k, "Сумма": v} for k, v in cat_data["months"].items() if v > 0
        ])
        
        if not df_detail.empty:
            col_det1, col_det2 = st.columns([2, 1])
            
            with col_det1:
                fig = px.bar(
                    df_detail,
                    x="Месяц",
                    y="Сумма",
                    title=f"Динамика: {selected_cat}",
                    color="Сумма",
                    color_continuous_scale="Blues",
                    text="Сумма"
                )
                fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            with col_det2:
                st.markdown(f"#### 📊 {selected_cat}")
                total_cat = cat_data["total"]
                for _, row in df_detail.iterrows():
                    pct = (row["Сумма"] / total_cat * 100) if total_cat > 0 else 0
                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #eee;">
                        <span>{row['Месяц']}</span>
                        <span><b>{row['Сумма']:,.0f} ₽</b> ({pct:.1f}%)</span>
                    </div>
                    """, unsafe_allow_html=True)

st.subheader("📋 Детальная таблица всех расходов")

table_data = []
for cat, cat_data in filtered.items():
    for month, val in cat_data["months"].items():
        if val > 0:
            pct_of_total = (val / total_all * 100) if total_all > 0 else 0
            table_data.append({
                "Категория": cat,
                "Месяц": month,
                "Сумма": val,
                "% от всех": f"{pct_of_total:.1f}%"
            })

if table_data:
    df_table = pd.DataFrame(table_data).sort_values("Сумма", ascending=False)
    st.dataframe(df_table, use_container_width=True, height=400)

st.subheader("🧠 Инсайты и выводы")

insights = []

if filtered:
    max_cat = max(filtered.items(), key=lambda x: x[1]["total"])
    pct_max = (max_cat[1]["total"] / total_all * 100) if total_all > 0 else 0
    insights.append(f"🏆 **{max_cat[0]}** — самая крупная категория: **{max_cat[1]['total']:,.0f} ₽** ({pct_max:.1f}% от всех расходов)")
    
    insights.append(f"📂 Всего **{len(filtered)}** категорий с расходами")
    
    avg_cat = total_all / len(filtered) if filtered else 0
    insights.append(f"📊 Средняя сумма на категорию: **{avg_cat:,.0f} ₽**")
    
    min_cat = min(filtered.items(), key=lambda x: x[1]["total"])
    if min_cat[1]["total"] > 0:
        insights.append(f"📌 **{min_cat[0]}** — самая маленькая категория: **{min_cat[1]['total']:,.0f} ₽**")
    
    avg_all = total_all / len(filtered) if filtered else 0
    anomalies = []
    for cat, cat_data in filtered.items():
        if cat_data["total"] > avg_all * 2:
            anomalies.append(cat)
    
    if anomalies:
        insights.append(f"⚠️ Категории с аномально высокими расходами (>2× среднего): **{', '.join(anomalies)}**")

for insight in insights:
    st.markdown(f"""
    <div style="background: #f0f2f6; padding: 12px 18px; border-radius: 10px; border-left: 5px solid #667eea; margin: 8px 0;">
        <span style="color: #333;">{insight}</span>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.header("💾 Экспорт")

if st.sidebar.button("📥 Скачать данные (Excel)"):
    if table_data:
        df_export = pd.DataFrame(table_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, sheet_name="Расходы", index=False)
            summary = [{"Категория": k, "Итого": v["total"], "Кол-во месяцев": len(v["months"])} 
                      for k, v in filtered.items()]
            df_summary = pd.DataFrame(summary).sort_values("Итого", ascending=False)
            df_summary.to_excel(writer, sheet_name="Сводка", index=False)
        
        st.sidebar.download_button(
            label="💾 Скачать Excel",
            data=output.getvalue(),
            file_name=f"expenses_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

st.sidebar.markdown("---")
st.sidebar.info(f"""
**📊 Расходный дашборд**
- Категорий: {len(filtered)}
- Всего расходов: {total_all:,.0f} ₽
- Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}
""")
