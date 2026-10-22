"""BakeWise: practical bakery planning demo (Streamlit)."""
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import streamlit as st
from forecast import validate_sales, make_forecast

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "data" / "historical_sales.csv"
LOCAL = ROOT / "data" / "local_entries.csv"
st.set_page_config(page_title="BakeWise | Daily Baking Plan", page_icon="🍩", layout="wide")
# make contents fit the device window

@st.cache_data
def demo_data():
    return validate_sales(pd.read_csv(DEMO))

def load_data():
    base = demo_data()
    if LOCAL.exists():
        extra = pd.read_csv(LOCAL)
        if not extra.empty:
            combined = pd.concat([base, extra], ignore_index=True)
            combined = combined.drop_duplicates(["date", "product"], keep="last")
            return validate_sales(combined)
    return base

def save_entries(entries):
    if LOCAL.exists():
        old = pd.read_csv(LOCAL)
        entries = pd.concat([old, entries], ignore_index=True)
    entries = entries.drop_duplicates(["date", "product"], keep="last")
    entries.to_csv(LOCAL, index=False)

st.title("🍩 BakeWise")
st.caption("A Simple and Practical Way to Plan Tomorrow's Baking · Prototype for Hackathon Taskforge Project · By Charles Chen")
st.info("DEMO MODE: Historical sales data are for demonstration purposes only. Weather data must be entered manually. Forecasts are estimates and may differ from actual demand.")

try:
    sales = load_data()
except Exception as err:
    st.error(f"Cannot load sales data: {err}")
    st.stop()

products = sorted(sales["product"].unique().tolist())
latest = sales.date.max().date()
#with st.sidebar:
#    st.header("Tomorrow's plan")
#    planning_date = st.date_input("Production date", value=max(date.today() + timedelta(days=1), latest + timedelta(days=1)))
#    temperature = st.number_input("Expected temperature (°F)", min_value=-20, max_value=130, value=72)
#    rain = st.checkbox("Rain expected")
#    strategy = st.selectbox("Production strategy", ["Balanced", "Lean", "Safe Buffer"])
#    st.caption("Lean and Safe Buffer use heuristic forecast-error adjustments; they are not validated profit optimizers.")
planning_date = st.session_state.get(
    "planning_date",
    max(date.today() + timedelta(days=1), latest + timedelta(days=1))
)

#tab_entry, tab_forecast, tab_history, tab_info = st.tabs(["📝 Today's Sales", "📋 Tomorrow's Forecast", "📈 Time History", "ℹ️ About"])
if "active_page" not in st.session_state:
    st.session_state["active_page"] = "📝 Today's Sales"

if "next_page" in st.session_state:
    st.session_state["active_page"] = st.session_state.pop("next_page")
    
def go_to_forecast():
    st.session_state["active_page"] = "📋 Tomorrow's Forecast"
page = st.segmented_control(
    "Navigation",
    [
        "📝 Today's Sales",
        "📋 Tomorrow's Forecast",
        "📈 Time History",
        "ℹ️ About"
    ],
    key="active_page",
    label_visibility="collapsed"
)

#with tab_entry:
if page == "📝 Today's Sales":
    st.subheader("Today's Production and Sales")
    st.write("Enter the actual units produced and leftover for each item. Check **Sold out early** only when you know it ran out before closing.")
    col1, col2, col3 = st.columns([170, 170, 170],width=520, gap="small")    
    with col1:
        entry_date = st.date_input(
            "Today's date",
            value=min(date.today(), planning_date - timedelta(days=1)),
            key="entry_date",
            width=150
        )
    with col2:
        actual_temp = st.number_input(
            "Actual temperature (°F)",
            min_value=-20,
            max_value=130,
            value=72,
            width=150
        )
    with col3:
        st.write("")  # Adds vertical spacing
        actual_rain = st.checkbox(
            "Rain today?"
        )    
    #entry_date = st.date_input("Sales date", value=min(date.today(), planning_date - timedelta(days=1)), key="entry_date")
    existing = sales[sales.date.dt.date == entry_date].set_index("product")
    defaults = []
    for product in products:
        if product in existing.index:
            r = existing.loc[product]
            defaults.append({"Product": product, "Produced": int(r.produced), "Leftover": int(r.leftover), "Sold out early": bool(r.sold_out_early)})
        else:
            recent = sales[(sales["product"] == product) & (sales.date.dt.date < entry_date)].tail(7)
            suggested = int(round(recent.produced.mean())) if not recent.empty else 0
            defaults.append({"Product": product, "Produced": suggested, "Leftover": 0, "Sold out early": False})
    #actual_temp = st.number_input("Today’s actual temperature (°F)", min_value=-20, max_value=130, value=72)
    #actual_rain = st.checkbox("Did it rain today?")    
    
    #grid = st.data_editor(pd.DataFrame(defaults), hide_index=True, use_container_width=True,
    #                     disabled=["Product"], num_rows="fixed", key=f"grid_{entry_date}",
    #                     column_config={"Produced": st.column_config.NumberColumn(min_value=0, step=1, required=True),
    #                                    "Leftover": st.column_config.NumberColumn(min_value=0, step=1, required=True),
    #                                    "Sold out early": st.column_config.CheckboxColumn()})
    
    # Initialize editable table data for the selected date
    table_key = f"production_table_{entry_date}"
    version_key = f"{table_key}_version"

    if table_key not in st.session_state:
        st.session_state[table_key] = pd.DataFrame(defaults)
        st.session_state[version_key] = 0

    def update_sales(editor_key, table_key, version_key):
        changes = st.session_state[editor_key].get("edited_rows", {})
        df = st.session_state[table_key].copy()

        for row_index, updates in changes.items():
            for column, value in updates.items():
                if column in ["Produced", "Leftover", "Sold out early"]:
                    df.at[int(row_index), column] = value

        st.session_state[table_key] = df
        st.session_state[version_key] += 1

    # Automatically calculate sold quantities
    df = st.session_state[table_key].copy()
    df["Sold"] = df["Produced"] - df["Leftover"]

    editor_key = f"{table_key}_editor_{st.session_state[version_key]}"
    #use_container_width=True,
    grid = st.data_editor(
        df,
        hide_index=True,        
        width=800,
        disabled=["Product", "Sold"],
        num_rows="fixed",
        key=editor_key,
        on_change=update_sales,
        args=(editor_key, table_key, version_key),

        column_config={
            "Product": st.column_config.TextColumn(
                alignment="center"
            ),
            "Produced": st.column_config.NumberColumn(
                min_value=0, step=1, required=True,
                alignment="center"
            ),
            "Leftover": st.column_config.NumberColumn(
                min_value=0, step=1, required=True,
                alignment="center"
            ),
            "Sold": st.column_config.NumberColumn(
                help="Automatically calculated: Produced - Leftover",
                alignment="center"
            ),
            "Sold out early": st.column_config.CheckboxColumn(
                alignment="center"
            )
        }

    )



    #raw = grid.copy()
    #raw["Sold"] = pd.to_numeric(raw["Produced"], errors="coerce") - pd.to_numeric(raw["Leftover"], errors="coerce")
    #st.dataframe(raw[["Product", "Sold"]], hide_index=True, use_container_width=True)
    
    if st.button("Save Data and Generate Forecast", type="primary"):
        invalid = False

        for c in ["Produced", "Leftover"]:
            v = pd.to_numeric(grid[c], errors="coerce")
            if v.isna().any() or (v < 0).any() or (v % 1 != 0).any():
                invalid = True

        if not invalid and (
            pd.to_numeric(grid["Leftover"]) >
            pd.to_numeric(grid["Produced"])
        ).any():
            invalid = True

        if entry_date >= planning_date:
            st.error("The forecast date must be after the sales-entry date.")

        elif invalid:
            st.error("Use nonnegative whole numbers; leftovers cannot exceed production.")

        else:
            records = pd.DataFrame({
                "date": [str(entry_date)] * len(grid),
                "product": grid["Product"],
                "produced": grid["Produced"].astype(int),
                "leftover": grid["Leftover"].astype(int),
                "sold_out_early": grid["Sold out early"].astype(bool),
                "temperature_f": [actual_temp] * len(grid),
                "rain": [int(actual_rain)] * len(grid)
            })

            try:
                save_entries(records)
                st.session_state["last_saved"] = str(entry_date)
                st.session_state["next_page"] = "📋 Tomorrow's Forecast"
                st.rerun()

            except OSError as err:
                st.error(f"Could not save to local CSV: {err}")


    #st.caption("Daily weather is entered manually for this demo. Hosted persistent storage is not implemented.")

#with tab_forecast:
if page == "📋 Tomorrow's Forecast":
    st.subheader(f"Tomorrow's Production Plan")
    # Show latest saved sales date
    if st.session_state.get("last_saved"):
        st.success(
            f"Latest entered sales date: {st.session_state['last_saved']}"
        )
    col1, col2, col3, col4 = st.columns(
        [170, 170, 150, 190],
        gap="small",
        width=760
    )
    with col1:
        planning_date = st.date_input(
            "Tomorrow date",
            value=planning_date,
            key="planning_date",
            width=150
        )
    with col2:
        temperature = st.number_input(
            "Expected temperature (°F)",
            min_value=-20,
            max_value=130,
            value=72,
            width=180
        )
    with col3:
        st.write("")
        st.write("")
        rain = st.checkbox("Rain expected?")

    with col4:
        strategy = st.selectbox(
            "Production strategy",
            ["Balanced", "Lean", "Safe Buffer"],
            width=180
        )        
    try:
        results = make_forecast(
            sales, planning_date, temperature, rain, strategy
        )

        #st.write("**Tomorrow's Recommended Production**")

        # Display one combined table with editable recommendations
        editable = st.data_editor(
            results[["Product", "Expected sales", "Recommended"]],
            hide_index=True,
            width=700,
            disabled=["Product", "Expected sales"],
            num_rows="fixed",
            key=f"forecast_adjustments_{planning_date}_{temperature}_{rain}_{strategy}",
            column_config={
                "Product": st.column_config.TextColumn(
                    alignment="center"
                ),
                "Expected sales": st.column_config.NumberColumn(
                    alignment="center",
                    format="%.1f"
                ),
                "Recommended": st.column_config.NumberColumn(
                    min_value=0,
                    step=1,
                    required=True,
                    alignment="center"
                )
            }
        )

        # Validate manual adjustments
        quantities = pd.to_numeric(
            editable["Recommended"], errors="coerce"
        )

        if (
            quantities.isna().any()
            or (quantities < 0).any()
            or (quantities % 1 != 0).any()
        ):
            st.warning(
                "Please enter valid whole-number production quantities."
            )

        else:
            # Generate downloadable production plan
            lines = [
                f"BakeWise production plan · {planning_date.isoformat()}",
                f"Strategy: {strategy}",
                ""
            ]

            lines += [
                f"{row['Product']}: {int(row['Recommended'])} units"
                for _, row in editable.iterrows()
            ]

            text_plan = "\n".join(lines)

            st.download_button(
                "Download Production Plan (.txt)",
                text_plan,
                file_name=f"bakewise_plan_{planning_date}.txt",
                mime="text/plain"
            )

            st.caption(
                "Share the downloaded plan with staff. "
                "Automatic scheduled email is not included in this prototype."
            )

    except Exception as err:
        st.error(f"Forecast error: {err}")


#with tab_history:
if page == "📈 Time History":
    st.subheader("Historical Production Results")
    selected = st.selectbox("Pick a Product", products)
    chart = sales[sales["product"] == selected].sort_values("date")
    st.line_chart(chart.set_index("date")[["sold", "leftover"]])
    st.download_button("Download combined sales CSV", sales.to_csv(index=False), file_name="bakewise_sales.csv", mime="text/csv")
    #st.caption("Sample history is synthetically generated. Historical plots are optional for deeper review.")

#with tab_info:
if page == "ℹ️ About":    
    st.markdown("""### How it works
1. Enter units **produced**, **left over**, and whether each product **sold out early**.
2. BakeWise calculates observed sales and estimates each product's next-day demand using weekday, US federal holiday, temperature, rain, and time-trend features.
3. The model uses ridge regression when sufficient history exists and a recent weekday average otherwise. Known early stockouts are excluded from fitting when possible, because observed sales may understate demand.
4. Choose a production strategy, inspect the plan, make adjustments, and download it.

**Limitations:** This is a single-shop educational demo. It ships with synthetic history, manual forecast-weather inputs, and heuristic risk settings. It has no live weather integration, POS connection, user authentication, durable hosted storage, or scheduled email delivery. Local CSV updates should not be relied on for a production web deployment.""")
