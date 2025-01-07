import streamlit as st
from modules.vehicle import manage_vehicles
from modules.booking import manage_bookings
from config import db
import pandas as pd
import matplotlib.pyplot as plt
from bson import ObjectId
import datetime

def admin_dashboard(user):
    st.subheader("Quản lý hệ thống: Admin")
    menu = ["Quản Lý Xe", "Quản Lý Đơn Đặt Hàng", "Thống Kê"]
    # Lưu lựa chọn vào session_state
    if 'selected_menu' not in st.session_state:
        st.session_state['selected_menu'] = menu[0]

    # Thêm key="menu_admin" cho st.sidebar.selectbox
    choice = st.sidebar.selectbox("Menu Quản Lý", menu, index=menu.index(st.session_state['selected_menu']), key="menu_admin")
    st.session_state['selected_menu'] = choice

    if choice == "Quản Lý Xe":
        manage_vehicles()  # Hàm quản lý xe
    elif choice == "Quản Lý Đơn Đặt Hàng":
        manage_bookings()  # Gọi hàm quản lý đơn đặt hàng
    elif choice == "Thống Kê":
        view_statistics()  # Gọi hàm thống kê

def view_statistics():
    st.subheader("Thống Kê Chi Tiết")

    # Bộ lọc
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Ngày bắt đầu", datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        end_date = st.date_input("Ngày kết thúc", datetime.date.today())

    # Chuyển đổi kiểu dữ liệu
    start_date = datetime.datetime.combine(start_date, datetime.datetime.min.time())
    end_date = datetime.datetime.combine(end_date, datetime.datetime.max.time())

    # Thêm bộ lọc xe
    selected_vehicles = st.multiselect("Chọn xe", [v['license_plate'] for v in db.vehicles.find({}, {"license_plate": 1})])

    # Tạo bộ lọc chung cho các truy vấn
    query_filter = {
        "created_at": {"$gte": start_date, "$lte": end_date}
    }

    if selected_vehicles:
        vehicle_ids = [v["_id"] for v in db.vehicles.find({"license_plate": {"$in": selected_vehicles}}, {"_id": 1})]
        query_filter["vehicle_id"] = {"$in": vehicle_ids}

    # Thống kê tổng số đơn đặt hàng
    total_bookings = db.bookings.count_documents(query_filter)
    st.metric(label="Tổng số đơn đặt hàng", value=total_bookings)

    # Thống kê tổng doanh thu
    total_revenue = db.bookings.aggregate([
        {"$match": query_filter},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
    ])
    revenue = next(total_revenue, {}).get("total", 0)
    st.metric(label="Tổng doanh thu (USD)", value=f"{revenue:,.2f}") # Format số

    # Thống kê số lượng khách hàng
    # Lưu ý: Cần lọc các đơn hàng của cùng 1 khách hàng, nếu không sẽ tính trùng
    distinct_customers = db.bookings.aggregate([
        {"$match": query_filter},
        {"$group": {"_id": "$user_id"}}
    ])
    total_customers = len(list(distinct_customers))
    st.metric(label="Tổng số khách hàng", value=total_customers)

    # Thống kê tổng số xe
    total_vehicles = db.vehicles.count_documents({})
    st.metric(label="Tổng số xe", value=total_vehicles)

    # Thống kê doanh thu theo tháng
    st.subheader("Doanh Thu Theo Tháng")
    monthly_revenue = db.bookings.aggregate([
        {"$match": query_filter},
        {"$addFields": {"start_date": {"$toDate": "$start_date"}}},  # Convert string to date
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$start_date"}},
            "total": {"$sum": "$total_price"}
        }},
        {"$sort": {"_id": 1}}
    ])
    monthly_revenue = list(monthly_revenue)
    months = [item["_id"] for item in monthly_revenue]
    revenues = [item["total"] for item in monthly_revenue]
    revenue_df = pd.DataFrame({"Tháng": months, "Doanh Thu (USD)": revenues})
    revenue_df["Doanh Thu (USD)"] = revenue_df["Doanh Thu (USD)"].map("{:,.2f}".format) # Format số
    st.line_chart(revenue_df.set_index("Tháng"))

    # Thống kê số lượng đơn đặt hàng theo trạng thái thanh toán
    st.subheader("Số Lượng Đơn Đặt Hàng Theo Trạng Thái Thanh Toán")
    booking_status = db.bookings.aggregate([
        {"$match": query_filter},
        {"$group": {"_id": "$payment_status", "count": {"$sum": 1}}}
    ])
    booking_status = list(booking_status)
    statuses = [item["_id"] for item in booking_status]
    counts = [item["count"] for item in booking_status]
    status_df = pd.DataFrame({"Trạng Thái": statuses, "Số Lượng": counts})
    st.bar_chart(status_df.set_index("Trạng Thái"))

    # Thống kê doanh thu theo xe
    st.subheader("Doanh Thu Theo Từng Xe")
    vehicle_revenue = db.bookings.aggregate([
        {"$match": query_filter},
        {"$lookup": {
            "from": "vehicles",
            "localField": "vehicle_id",
            "foreignField": "_id",
            "as": "vehicle_info"
        }},
        {"$unwind": "$vehicle_info"},
        {"$group": {
            "_id": "$vehicle_info.license_plate",
            "total_revenue": {"$sum": "$total_price"}
        }},
        {"$sort": {"total_revenue": -1}}
    ])
    vehicle_revenue = list(vehicle_revenue)
    vehicles = [item["_id"] for item in vehicle_revenue]
    revenues_per_vehicle = [item["total_revenue"] for item in vehicle_revenue]
    vehicle_df = pd.DataFrame({"Biển Số": vehicles, "Doanh Thu (USD)": revenues_per_vehicle})
    vehicle_df["Doanh Thu (USD)"] = vehicle_df["Doanh Thu (USD)"].map("{:,.2f}".format) # Format số
    st.bar_chart(vehicle_df.set_index("Biển Số"))

    # Thống kê số lượng đơn đặt hàng theo tháng
    st.subheader("Số Lượng Đơn Đặt Hàng Theo Tháng")
    monthly_booking_count = db.bookings.aggregate([
        {"$match": query_filter},
        {"$addFields": {"start_date": {"$toDate": "$start_date"}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$start_date"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ])
    monthly_booking_count = list(monthly_booking_count)
    booking_months = [item["_id"] for item in monthly_booking_count]
    booking_counts = [item["count"] for item in monthly_booking_count]
    booking_count_df = pd.DataFrame({"Tháng": booking_months, "Số Lượng Đơn": booking_counts})
    st.line_chart(booking_count_df.set_index("Tháng"))

    # Thống kê tỷ lệ phần trăm trạng thái thanh toán
    st.subheader("Tỷ Lệ Phần Trăm Trạng Thái Thanh Toán")
    payment_status_stats = db.bookings.aggregate([
        {"$match": query_filter},
        {"$group": {"_id": "$payment_status", "count": {"$sum": 1}}},
        {"$project": {
            "payment_status": "$_id",
            "count": 1,
            "percentage": {"$multiply": [{"$divide": ["$count", {"$sum": [b['count'] for b in booking_status]}]}, 100]} # Tính tổng số đơn hàng từ biến booking_status
        }}
    ])

    payment_status_stats_df = pd.DataFrame(list(payment_status_stats))
    payment_status_stats_df["percentage"] = payment_status_stats_df["percentage"].map("{:.2f}%".format) # Format phần trăm
    st.dataframe(payment_status_stats_df)