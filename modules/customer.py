import streamlit as st
from modules.auth import update_user_info
from modules.booking import bookings, list_user_bookings, return_vehicle
from modules.vehicle import search_vehicles

def customer_dashboard(user):
    st.subheader(f"Chào mừng khách hàng: {user['full_name']}")
    menu = ["Tìm Kiếm Xe", "Đặt Xe", "Trả Xe", "Cập nhật thông tin"]
    # Thêm key="menu_customer" cho st.sidebar.selectbox
    choice = st.sidebar.selectbox("Menu Khách Hàng", menu, key="menu_customer")

    if choice == "Tìm Kiếm Xe":
        search_vehicles()
    elif choice == "Đặt Xe":
        bookings(user)
    elif choice == "Trả Xe":
        return_vehicle(user)
    elif choice == "Cập nhật thông tin":
        update_user_info(user)