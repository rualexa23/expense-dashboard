import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import re

# === НАСТРОЙКА СТРАНИЦЫ ===
st.set_page_config(
    page_title="📊 Расходный дашборд",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Расходный дашборд")
st.caption(f"📆 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

# === ССЫЛКА НА ДАННЫЕ ===
DATA_URL = "https://script.google.com/macros/s/AKfycbxVXqV-y4qWfpfyp8MtrxApVqwuKWvbcxg0R1awJC81H06tM1efWpyTiP5O-DFq0tjTrA/exec"

# === ИЕРАРХИЯ РАСХОДОВ ===
EXPENSE_HIERARCHY = {
    "Транспорт": {
        "total_row": 14,
        "items": {
            "Архангельск": 15, "Балашиха": 16, "Владимир": 17,
            "Дмитров": 18, "Заморозка": 19, "Ив-Яр-Вл": 20,
            "Иваново": 21, "Калуга": 22, "Карелия": 23,
            "Клин": 24, "Кострома": 25, "Москва": 26,
            "Мурманск": 27, "Нижний Новгород": 28, "Ногинск": 29,
            "Осетия": 30, "Платка": 31, "Подольск": 32,
            "Рязань": 33, "СПБ": 34, "Тверь": 35,
            "Тула": 36, "Химки": 37, "Ярославль": 38
        }
    },
    "Возврат": {
        "total_row": 43,
        "items": {
            "Заморозка": 44, "Печень": 45, "Рыба": 46
        }
    },
    "Другое": {
        "total_row": 49,
        "items": {
            "Командировка": 50, "Комиссия Банка": 51,
            "Корпоративные мероприятия": 52, "Обучение": 53,
            "Оплата пакетов": 54, "Разовое": 55,
            "Спецодежда": 56, "Подбор персонала": 57
        }
    },
    "Зарплата": {
        "total_row": 64,
        "items": {
            "ОФИС": 65, "Склад": 66, "Экспедиторы": 67,
            "Отдел сопровождения": 68, "Административный персонал": 69,
            "Отдел холодных продаж": 70, "Отдел входящая линия": 71,
            "Отдел по работе с юр.лицами": 72
        }
    },
    "Оплата поставщикам": {
        "total_row": 74,
        "items": {
            "Аквафор": 75, "Баркад": 76, "Кала-Ранта": 77,
            "Мурман": 78, "Натурпродукт": 79, "Норд-ост": 80,
            "Парола": 81, "Риф Карелия": 82, "РИф Новгород": 83,
            "Руспроектстрой": 84, "Рыбная ферма": 85,
            "Рыбы Плюс": 86, "Счастливый хвост": 87
        }
    },
    "Оплата заморозка": {
        "total_row": 90,
        "items": {
            "ИП Огнерубова": 91, "К-Флот": 92, "Кала-Ранта": 93,
            "Норебо Ру": 94, "Ультра Фиш": 95, "Эридан": 96
        }
    },
    "Реклама": {
        "total_row": 98,
        "items": {
            "АМО СРМ": 99, "Билайн Связь": 100, "Билайн Смс": 101,
            "Вконтакте": 102, "Листовки и прочее": 103,
            "Маркетинг": 104, "Мегафон": 105, "Оплата за работу": 106,
            "Призы": 107, "Прочие": 108
        }
    },
    "Скидки": {
        "total_row": 111,
        "items": {
            "50р. с конкурса": 112, "50р. с сопровождения": 113,
            "Возврат/замена": 114, "Конкурс": 115,
            "Областные города": 116, "От 33 штук": 117,
            "Промокод": 118, "Тайный покупатель": 119
        }
    },
    "Склад": {
        "total_row": 121,
        "items": {
            "Аренда": 122, "Интернет/связь": 123, "Лед": 124,
            "Хозрасходы": 125, "Ящики": 126
        }
    },
    "ОФИС": {
        "total_row": 131,
        "items": {
            "Аренда": 132, "Занятия": 133, "Интернет": 134,
            "Канцелярия": 135, "Офисная техника/мебель": 136,
            "Покупки в офис": 137, "Уборка": 138
        }
    },
    "Налоги": {
        "total_row": 145,
        "items": {}
    },
    "Связь": {
        "total_row": 147,
        "items": {
            "Интернет": 148, "Телефон": 149
        }
    }
}

# === ЗАГРУЗКА ДАННЫХ ===
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

# === ПАРСИНГ ДАННЫХ ===
def parse_hierarchical_expenses(raw_data, hierarchy):
    """
    Парсит данные с учётом иерархии: категории → подкатегории
    """
    if not raw_data:
        return None
    
    # Создаём словарь: "Показатель" → данные по месяцам
    data_map = {}
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
            data_map[label] = {
                "total": total,
                "months": month_values
            }
    
    # Строим иерархию
    result = {}
    all_months = set()
    
    for category, cat_info in hierarchy.items():
        total_row = cat_info.get("total_row")
        total_label = None
        
        # Ищем итоговую строку категории
        for label, label_data in data_map.items():
            # Проверяем, совпадает ли название с категорией
            if label == category or label == f"{category} (итого)":
                total_label = label
                break
        
        # Если не нашли итог — пропускаем категорию
        if total_label is None:
            continue
        
        cat_total = data_map[total_label]["total"]
        cat_months = data_map[total_label]["months"]
        
        # Если итог равен 0 — пропускаем
        if cat_total == 0:
            continue
        
        # Собираем подкатегории
        items = {}
        for item_name, item_row in cat_info["items"].items():
            # Ищем подкатегорию по названию
            for label, label_data in data_map.items():
                if label == item_name:
                    if label_data["total"] > 0:
                        items[item_name] = {
                            "total": label_data["total"],
                            "months": label_data["months"]
                        }
                    break
        
        # Сохраняем категорию
        result[category] = {
            "total": cat_total,
            "months": cat_months,
            "items": items
        }
        
        # Собираем все месяцы
        all_months.update(cat_months.keys())
        for item in items.values():
            all_months.update(item["months"].keys())
    
    return result, sorted(list(all_months))

expenses, months = parse_hierarchical_expenses(raw_data, EXPENSE_HIERARCHY)

if not expenses:
    st.warning("⚠️ Нет данных для отображения")
    st.stop()

# === БОКОВАЯ ПАНЕЛЬ: ФИЛЬТРЫ ===
st.sidebar.header("🔍 Фильтры")

categories = list(expenses.keys())
selected_cats = st.sidebar.multiselect(
    "📂 Категории расходов",
    options=categories,
    default=categories
)

# Фильтр по сумме
max_val = int(max([v["total"] for v in expenses.values()])) if expenses else 100000
amount_range = st.sidebar.slider(
    "💰 Минимальная сумма категории",
    min_value=0,
    max_value=max_val,
    value=0,
    step=1000
)

# Применяем фильтры
filtered = {}
for cat, cat_data in expenses.items():
    if cat in selected_cats and cat_data["total"] >= amount_range:
        filtered[cat] = cat_data

if not filtered:
    st.warning("⚠️ Нет данных с выбранными фильтрами")
    st.stop()

total_all = sum([v["total"] for v in filtered.values()])

# === СТРАТЕГИЧЕСКИЕ KPI ===
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

# === ГРАФИК 1: СТРУКТУРА РАСХОДОВ (УРОВЕНЬ 1) ===
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
            title="Распределение расходов по категориям",
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

# === ГРАФИК 2: ДЕТАЛИЗАЦИЯ ПО КАТЕГОРИИ (УРОВЕНЬ 2) ===
st.subheader("📊 Детализация по категориям")

selected_cat = st.selectbox(
    "Выберите категорию для детализации",
    options=list(filtered.keys())
)

if selected_cat and selected_cat in filtered:
    cat_data = filtered[selected_cat]
    
    # Показываем общую сумму категории
    st.metric(f"📊 {selected_cat}", f"{cat_data['total']:,.0f} ₽")
    
    if cat_data["items"]:
        # График по подкатегориям
        items_data = [{"Подкатегория": k, "Сумма": v["total"]} for k, v in cat_data["items"].items()]
        df_items = pd.DataFrame(items_data).sort_values("Сумма", ascending=False)
        
        col_det1, col_det2 = st.columns([2, 1])
        
        with col_det1:
            fig_items = px.bar(
                df_items,
                x="Подкатегория",
                y="Сумма",
                title=f"Детализация: {selected_cat}",
                color="Сумма",
                color_continuous_scale="Blues",
                text="Сумма"
            )
            fig_items.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_items.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_items, use_container_width=True)
        
        with col_det2:
            st.markdown(f"#### 📋 Подкатегории в «{selected_cat}»")
            for _, row in df_items.iterrows():
                pct = (row["Сумма"] / cat_data["total"] * 100) if cat_data["total"] > 0 else 0
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #eee;">
                    <span>{row['Подкатегория']}</span>
                    <span><b>{row['Сумма']:,.0f} ₽</b> ({pct:.1f}%)</span>
                </div>
                """, unsafe_allow_html=True)
        
        # Динамика подкатегорий
        if months and df_items is not None:
            st.subheader("📈 Динамика подкатегорий")
            
            # Собираем данные по месяцам для всех подкатегорий
            dyn_data = []
            for item_name, item_data in cat_data["items"].items():
                for month, val in item_data["months"].items():
                    if val > 0:
                        dyn_data.append({
                            "Подкатегория": item_name,
                            "Месяц": month,
                            "Сумма": val
                        })
            
            if dyn_data:
                df_dyn = pd.DataFrame(dyn_data)
                month_order = sorted(df_dyn["Месяц"].unique())
                df_dyn["Месяц"] = pd.Categorical(df_dyn["Месяц"], categories=month_order, ordered=True)
                
                fig_dyn = px.line(
                    df_dyn,
                    x="Месяц",
                    y="Сумма",
                    color="Подкатегория",
                    title=f"Динамика подкатегорий: {selected_cat}",
                    markers=True
                )
                fig_dyn.update_layout(height=400)
                st.plotly_chart(fig_dyn, use_container_width=True)
    else:
        st.info(f"В категории «{selected_cat}» нет детализированных подкатегорий")

# === ДИНАМИКА КАТЕГОРИЙ ПО МЕСЯЦАМ ===
if months:
    st.subheader("📈 Динамика категорий по месяцам")
    
    dyn_all = []
    for cat, cat_data in filtered.items():
        for month, val in cat_data["months"].items():
            if val > 0:
                dyn_all.append({
                    "Категория": cat,
                    "Месяц": month,
                    "Сумма": val
                })
    
    if dyn_all:
        df_dyn_all = pd.DataFrame(dyn_all)
        month_order = sorted(df_dyn_all["Месяц"].unique())
        df_dyn_all["Месяц"] = pd.Categorical(df_dyn_all["Месяц"], categories=month_order, ordered=True)
        
        # Общая динамика
        df_monthly = df_dyn_all.groupby("Месяц")["Сумма"].sum().reset_index()
        fig_total = px.line(
            df_monthly,
            x="Месяц",
            y="Сумма",
            title="Общая динамика расходов",
            markers=True
        )
        fig_total.update_traces(line=dict(width=3))
        fig_total.update_layout(height=400)
        st.plotly_chart(fig_total, use_container_width=True)
        
        # Динамика по категориям (топ-5)
        st.subheader("📈 Динамика топ-5 категорий")
        top_cats = sorted(filtered.items(), key=lambda x: x[1]["total"], reverse=True)[:5]
        top_cat_names = [c[0] for c in top_cats]
        df_top = df_dyn_all[df_dyn_all["Категория"].isin(top_cat_names)]
        
        fig_top = px.line(
            df_top,
            x="Месяц",
            y="Сумма",
            color="Категория",
            title="Динамика топ-5 категорий",
            markers=True
        )
        fig_top.update_layout(height=400)
        st.plotly_chart(fig_top, use_container_width=True)

# === ДЕТАЛЬНАЯ ТАБЛИЦА ВСЕХ РАСХОДОВ ===
st.subheader("📋 Детальная таблица всех расходов")

table_data = []
for cat, cat_data in filtered.items():
    for item, item_data in cat_data["items"].items():
        for month, val in item_data["months"].items():
            if val > 0:
                pct_of_total = (val / total_all * 100) if total_all > 0 else 0
                table_data.append({
                    "Категория": cat,
                    "Подкатегория": item,
                    "Месяц": month,
                    "Сумма": val,
                    "% от всех": f"{pct_of_total:.1f}%"
                })

if table_data:
    df_table = pd.DataFrame(table_data).sort_values("Сумма", ascending=False)
    st.dataframe(df_table, use_container_width=True, height=400)

# === АВТОВЫВОДЫ ===
st.subheader("🧠 Инсайты и выводы")

insights = []

if filtered:
    # Самая крупная категория
    max_cat = max(filtered.items(), key=lambda x: x[1]["total"])
    pct_max = (max_cat[1]["total"] / total_all * 100) if total_all > 0 else 0
    insights.append(f"🏆 **{max_cat[0]}** — самая крупная категория: **{max_cat[1]['total']:,.0f} ₽** ({pct_max:.1f}% от всех расходов)")
    
    # Количество категорий
    insights.append(f"📂 Всего **{len(filtered)}** категорий с расходами")
    
    # Средняя сумма на категорию
    avg_cat = total_all / len(filtered) if filtered else 0
    insights.append(f"📊 Средняя сумма на категорию: **{avg_cat:,.0f} ₽**")
    
    # Самая маленькая категория
    min_cat = min(filtered.items(), key=lambda x: x[1]["total"])
    if min_cat[1]["total"] > 0:
        insights.append(f"📌 **{min_cat[0]}** — самая маленькая категория: **{min_cat[1]['total']:,.0f} ₽**")
    
    # Категории с наибольшим количеством подкатегорий
    max_items_cat = max(filtered.items(), key=lambda x: len(x[1]["items"]))
    if max_items_cat[1]["items"]:
        insights.append(f"📂 **{max_items_cat[0]}** содержит больше всего подкатегорий ({len(max_items_cat[1]['items'])} шт.)")

for insight in insights:
    st.markdown(f"""
    <div style="background: #f0f2f6; padding: 12px 18px; border-radius: 10px; border-left: 5px solid #667eea; margin: 8px 0;">
        <span style="color: #333;">{insight}</span>
    </div>
    """, unsafe_allow_html=True)

# === КНОПКА "БЭКАП" ===
st.sidebar.markdown("---")
st.sidebar.header("💾 Экспорт")

if st.sidebar.button("📥 Скачать данные (Excel)"):
    if table_data:
        df_export = pd.DataFrame(table_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, sheet_name="Расходы", index=False)
            
            # Сводка по категориям
            summary = [{"Категория": k, "Итого": v["total"], "Кол-во подкатегорий": len(v["items"])} 
                      for k, v in filtered.items()]
            df_summary = pd.DataFrame(summary).sort_values("Итого", ascending=False)
            df_summary.to_excel(writer, sheet_name="Сводка", index=False)
        
        st.sidebar.download_button(
            label="💾 Скачать Excel",
            data=output.getvalue(),
            file_name=f"expenses_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# === ИНФОРМАЦИЯ ===
st.sidebar.markdown("---")
st.sidebar.info(f"""
**📊 Расходный дашборд**
- Категорий: {len(filtered)}
- Всего расходов: {total_all:,.0f} ₽
- Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}
""")
