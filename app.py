
import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
from io import BytesIO

# =====================================================
# 1. CẤU HÌNH ỨNG DỤNG
# =====================================================
st.set_page_config(
    page_title="Thẩm định dự án đầu tư",
    page_icon="📊",
    layout="wide"
)

st.title("📊 ỨNG DỤNG THẨM ĐỊNH DỰ ÁN ĐẦU TƯ")
st.caption(
    "Phân tích hiệu quả tài chính dự án bằng 6 chỉ tiêu: "
    "NPV, IRR, MIRR, PI, PP và DPP."
)

st.info(
    "Nhập dòng tiền theo cùng một đơn vị tiền tệ. "
    "Vốn đầu tư ban đầu nhập số dương; dòng tiền thu vào nhập số dương "
    "và dòng tiền chi ra nhập số âm."
)


# =====================================================
# 2. CÁC HÀM TÍNH TOÁN
# =====================================================
def tinh_npv(dong_tien, lai_suat):
    """NPV với dòng tiền năm 0 ở vị trí đầu tiên."""
    return float(npf.npv(lai_suat, dong_tien))


def tinh_irr(dong_tien):
    """Tính IRR; trả về None nếu không tính được."""
    if not (any(x < 0 for x in dong_tien)
            and any(x > 0 for x in dong_tien)):
        return None

    try:
        ket_qua = float(npf.irr(dong_tien))
        return ket_qua if np.isfinite(ket_qua) else None
    except (ValueError, ZeroDivisionError, FloatingPointError):
        return None


def tinh_mirr(dong_tien, lai_suat_von, lai_suat_tai_dau_tu):
    """Tính MIRR theo lãi suất tài trợ và tái đầu tư."""
    if not (any(x < 0 for x in dong_tien)
            and any(x > 0 for x in dong_tien)):
        return None

    try:
        ket_qua = float(
            npf.mirr(
                dong_tien,
                finance_rate=lai_suat_von,
                reinvest_rate=lai_suat_tai_dau_tu
            )
        )
        return ket_qua if np.isfinite(ket_qua) else None
    except (ValueError, ZeroDivisionError, FloatingPointError):
        return None


def tinh_pi(dong_tien, lai_suat):
    """
    PI = PV dòng tiền dương / PV trị tuyệt đối dòng tiền âm.
    Bao gồm vốn đầu tư ban đầu và các khoản chi âm ở các năm sau.
    """
    pv_duong = 0.0
    pv_am = 0.0

    for nam, cf in enumerate(dong_tien):
        pv = cf / ((1 + lai_suat) ** nam)

        if cf > 0:
            pv_duong += pv
        elif cf < 0:
            pv_am += abs(pv)

    if pv_am == 0:
        return None

    return pv_duong / pv_am


def tinh_thoi_gian_hoan_von(dong_tien, lai_suat=None):
    """
    PP nếu lai_suat=None.
    DPP nếu có lai_suat.
    Nội suy trong năm giả định dòng tiền phát sinh đều trong năm.
    """
    if len(dong_tien) < 2 or dong_tien[0] >= 0:
        return None

    tich_luy = dong_tien[0]

    for nam in range(1, len(dong_tien)):
        cf = dong_tien[nam]

        if lai_suat is not None:
            cf = cf / ((1 + lai_suat) ** nam)

        truoc_do = tich_luy
        tich_luy += cf

        if tich_luy >= 0:
            if cf <= 0:
                return float(nam)

            phan_nam = max(0.0, min(1.0, -truoc_do / cf))
            return (nam - 1) + phan_nam

    return None


def dinh_dang_tien(gia_tri):
    return f"{gia_tri:,.2f}"


def dinh_dang_ty_le(gia_tri):
    if gia_tri is None or not np.isfinite(gia_tri):
        return "Không xác định"
    return f"{gia_tri * 100:.2f}%"


def dinh_dang_nam(gia_tri):
    if gia_tri is None:
        return "Không hoàn vốn trong thời gian dự án"
    return f"{gia_tri:.2f} năm"


# =====================================================
# 3. NHẬP THÔNG SỐ DỰ ÁN
# =====================================================
st.header("1. Thông số đầu tư")

col1, col2, col3 = st.columns(3)

with col1:
    von_dau_tu = st.number_input(
        "Vốn đầu tư ban đầu",
        min_value=0.01,
        value=1000.0,
        step=100.0,
        help="Nhập số dương. Dòng tiền năm 0 sẽ được ghi nhận là số âm."
    )

with col2:
    so_nam = st.number_input(
        "Thời gian dự án (năm)",
        min_value=1,
        max_value=50,
        value=5,
        step=1
    )

with col3:
    lai_suat_chiet_khau = st.number_input(
        "Lãi suất chiết khấu (%)",
        min_value=0.0,
        max_value=500.0,
        value=20.0,
        step=1.0
    )

col4, col5 = st.columns(2)

with col4:
    lai_suat_von = st.number_input(
        "Lãi suất tài trợ vốn (%) - MIRR",
        min_value=0.0,
        max_value=500.0,
        value=12.0,
        step=1.0
    )

with col5:
    lai_suat_tai_dau_tu = st.number_input(
        "Lãi suất tái đầu tư (%) - MIRR",
        min_value=0.0,
        max_value=500.0,
        value=10.0,
        step=1.0
    )

r = lai_suat_chiet_khau / 100
finance_rate = lai_suat_von / 100
reinvest_rate = lai_suat_tai_dau_tu / 100


# =====================================================
# 4. NHẬP DÒNG TIỀN THEO NĂM
# =====================================================
st.header("2. Nhập dòng tiền dự án")

st.write(
    "Bạn có thể sửa trực tiếp dòng tiền thuần từng năm. "
    "Năm 0 là vốn đầu tư ban đầu; các năm 1 đến N là dòng tiền "
    "phát sinh trong quá trình hoạt động."
)

dong_tien_mac_dinh = {
    1: -200.0,
    2: -100.0,
    3: 300.0,
    4: 800.0,
    5: 1200.0
}

du_lieu = []

for nam in range(1, int(so_nam) + 1):
    du_lieu.append({
        "Năm": nam,
        "Dòng tiền thuần": dong_tien_mac_dinh.get(nam, 0.0)
    })

df_dong_tien = pd.DataFrame(du_lieu)

df_da_sua = st.data_editor(
    df_dong_tien,
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    disabled=["Năm"],
    column_config={
        "Năm": st.column_config.NumberColumn(
            "Năm", format="%d"
        ),
        "Dòng tiền thuần": st.column_config.NumberColumn(
            "Dòng tiền thuần",
            help="Số dương là dòng tiền vào; số âm là dòng tiền ra.",
            format="%.2f",
            required=True
        )
    },
    key="bang_dong_tien"
)

st.caption(
    "Ví dụ: dòng tiền -200 nghĩa là phát sinh khoản chi 200 "
    "trong năm tương ứng."
)


# =====================================================
# 5. NÚT THỰC HIỆN PHÂN TÍCH
# =====================================================
if st.button(
    "🧮 TÍNH TOÁN CÁC CHỈ TIÊU",
    type="primary",
    use_container_width=True
):
    if df_da_sua["Dòng tiền thuần"].isna().any():
        st.error("Vui lòng nhập đầy đủ dòng tiền cho tất cả các năm.")
        st.stop()

    dong_tien_tuong_lai = (
        df_da_sua["Dòng tiền thuần"].astype(float).tolist()
    )

    # Dòng tiền năm 0 là vốn đầu tư âm
    dong_tien = [-float(von_dau_tu)] + dong_tien_tuong_lai

    npv = tinh_npv(dong_tien, r)
    irr = tinh_irr(dong_tien)
    mirr = tinh_mirr(dong_tien, finance_rate, reinvest_rate)
    pi = tinh_pi(dong_tien, r)
    pp = tinh_thoi_gian_hoan_von(dong_tien)
    dpp = tinh_thoi_gian_hoan_von(dong_tien, lai_suat=r)

    # Tạo bảng dòng tiền và giá trị hiện tại
    bang_phan_tich = pd.DataFrame({
        "Năm": list(range(int(so_nam) + 1)),
        "Dòng tiền": dong_tien
    })

    bang_phan_tich["Hệ số chiết khấu"] = [
        1 / ((1 + r) ** nam)
        for nam in range(int(so_nam) + 1)
    ]

    bang_phan_tich["Giá trị hiện tại"] = (
        bang_phan_tich["Dòng tiền"]
        * bang_phan_tich["Hệ số chiết khấu"]
    )

    bang_phan_tich["Dòng tiền tích lũy"] = (
        bang_phan_tich["Dòng tiền"].cumsum()
    )

    bang_phan_tich["Giá trị hiện tại tích lũy"] = (
        bang_phan_tich["Giá trị hiện tại"].cumsum()
    )

    # Lưu kết quả để không mất khi tải file
    st.session_state["ket_qua_tham_dinh"] = {
        "dong_tien": dong_tien,
        "npv": npv,
        "irr": irr,
        "mirr": mirr,
        "pi": pi,
        "pp": pp,
        "dpp": dpp,
        "bang": bang_phan_tich,
        "r": r,
        "finance_rate": finance_rate,
        "reinvest_rate": reinvest_rate,
        "von_dau_tu": von_dau_tu,
        "so_nam": int(so_nam)
    }


# =====================================================
# 6. HIỂN THỊ KẾT QUẢ
# =====================================================
if "ket_qua_tham_dinh" in st.session_state:
    kq = st.session_state["ket_qua_tham_dinh"]

    # Nếu người dùng thay đổi thông số sau lần tính trước,
    # yêu cầu tính lại để tránh hiển thị kết quả cũ.
    thong_so_hien_tai = (
        float(von_dau_tu),
        int(so_nam),
        float(r),
        float(finance_rate),
        float(reinvest_rate),
        tuple(
            df_da_sua["Dòng tiền thuần"].astype(float).tolist()
        )
    )

    thong_so_da_tinh = (
        float(kq["von_dau_tu"]),
        int(kq["so_nam"]),
        float(kq["r"]),
        float(kq["finance_rate"]),
        float(kq["reinvest_rate"]),
        tuple(kq["dong_tien"][1:])
    )

    if thong_so_hien_tai != thong_so_da_tinh:
        st.warning(
            "Thông số hoặc dòng tiền đã thay đổi. "
            "Nhấn 'TÍNH TOÁN CÁC CHỈ TIÊU' để cập nhật kết quả."
        )
    else:
        st.divider()
        st.header("3. Kết quả thẩm định dự án")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "NPV",
                dinh_dang_tien(kq["npv"])
            )

        with c2:
            st.metric(
                "IRR",
                dinh_dang_ty_le(kq["irr"])
            )

        with c3:
            st.metric(
                "MIRR",
                dinh_dang_ty_le(kq["mirr"])
            )

        c4, c5, c6 = st.columns(3)

        with c4:
            st.metric(
                "PI",
                f"{kq['pi']:.4f}" if kq["pi"] is not None
                else "Không xác định"
            )

        with c5:
            st.metric(
                "PP",
                dinh_dang_nam(kq["pp"])
            )

        with c6:
            st.metric(
                "DPP",
                dinh_dang_nam(kq["dpp"])
            )

        # ---------------------------------------------
        # 7. NHẬN XÉT THAM KHẢO
        # ---------------------------------------------
        st.header("4. Nhận xét kết quả")

        if kq["npv"] > 0:
            st.success(
                "NPV > 0: Dự án tạo ra giá trị hiện tại ròng dương "
                "theo tỷ lệ chiết khấu đã chọn."
            )
        elif kq["npv"] < 0:
            st.warning(
                "NPV < 0: Giá trị hiện tại của dòng tiền vào "
                "chưa bù đắp dòng tiền ra theo tỷ lệ chiết khấu đã chọn."
            )
        else:
            st.info(
                "NPV = 0: Dự án hòa vốn theo tiêu chuẩn giá trị hiện tại ròng."
            )

        if kq["irr"] is not None:
            if kq["irr"] > kq["r"]:
                st.write(
                    f"IRR ({kq['irr']:.2%}) cao hơn lãi suất chiết khấu "
                    f"({kq['r']:.2%}). Với dòng tiền thông thường, "
                    "đây là dấu hiệu thuận lợi."
                )
            else:
                st.write(
                    f"IRR ({kq['irr']:.2%}) không cao hơn lãi suất "
                    f"chiết khấu ({kq['r']:.2%}). Cần xem xét kỹ hiệu quả dự án."
                )
        else:
            st.write(
                "Không xác định được IRR duy nhất bằng phương pháp tính "
                "của thư viện. Kiểm tra lại dấu và cấu trúc dòng tiền."
            )

        if kq["mirr"] is not None:
            st.write(
                f"MIRR = {kq['mirr']:.2%}; "
                f"lãi suất tài trợ = {kq['finance_rate']:.2%}; "
                f"lãi suất tái đầu tư = {kq['reinvest_rate']:.2%}."
            )
        else:
            st.write(
                "Không tính được MIRR: cần có ít nhất một dòng tiền âm "
                "và một dòng tiền dương."
            )

        if kq["pi"] is not None:
            if kq["pi"] > 1:
                st.write(
                    "PI > 1: Giá trị hiện tại của dòng tiền dương "
                    "lớn hơn giá trị hiện tại của dòng tiền âm."
                )
            elif kq["pi"] < 1:
                st.write(
                    "PI < 1: Giá trị hiện tại của dòng tiền dương "
                    "nhỏ hơn giá trị hiện tại của dòng tiền âm."
                )
            else:
                st.write("PI = 1: Hai giá trị hiện tại bằng nhau.")
        else:
            st.write("Không xác định PI do không có dòng tiền âm.")

        # ---------------------------------------------
        # 8. BẢNG PHÂN TÍCH DÒNG TIỀN
        # ---------------------------------------------
        st.header("5. Bảng phân tích dòng tiền")

        st.dataframe(
            kq["bang"].style.format({
                "Dòng tiền": "{:,.2f}",
                "Hệ số chiết khấu": "{:.4f}",
                "Giá trị hiện tại": "{:,.2f}",
                "Dòng tiền tích lũy": "{:,.2f}",
                "Giá trị hiện tại tích lũy": "{:,.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )

        # ---------------------------------------------
        # 9. BIỂU ĐỒ DÒNG TIỀN
        # ---------------------------------------------
        st.header("6. Biểu đồ dòng tiền dự án")

        bieu_do = kq["bang"].set_index("Năm")[
            ["Dòng tiền", "Dòng tiền tích lũy"]
        ]

        st.line_chart(bieu_do)

        # ---------------------------------------------
        # 10. XUẤT EXCEL
        # ---------------------------------------------
        st.header("7. Xuất báo cáo Excel")

        output = BytesIO()

        bang_chi_tieu = pd.DataFrame({
            "Chỉ tiêu": [
                "Vốn đầu tư ban đầu",
                "Thời gian dự án (năm)",
                "Lãi suất chiết khấu",
                "Lãi suất tài trợ vốn",
                "Lãi suất tái đầu tư",
                "NPV",
                "IRR",
                "MIRR",
                "PI",
                "PP (năm)",
                "DPP (năm)"
            ],
            "Giá trị": [
                kq["von_dau_tu"],
                kq["so_nam"],
                kq["r"],
                kq["finance_rate"],
                kq["reinvest_rate"],
                kq["npv"],
                kq["irr"],
                kq["mirr"],
                kq["pi"],
                kq["pp"],
                kq["dpp"]
            ]
        })

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            bang_chi_tieu.to_excel(
                writer, sheet_name="Chi_tieu_tham_dinh", index=False
            )

            kq["bang"].to_excel(
                writer, sheet_name="Dong_tien_du_an", index=False
            )

            for ten_sheet in writer.sheets:
                ws = writer.sheets[ten_sheet]
                ws.freeze_panes = "A2"
                ws.auto_filter.ref = ws.dimensions

                for cells in ws.columns:
                    do_rong = max(
                        len(str(cell.value)) if cell.value is not None else 0
                        for cell in cells
                    )
                    ws.column_dimensions[
                        cells[0].column_letter
                    ].width = min(do_rong + 3, 35)

        output.seek(0)

        st.download_button(
            label="📥 TẢI BÁO CÁO THẨM ĐỊNH (.xlsx)",
            data=output.getvalue(),
            file_name="bao_cao_tham_dinh_du_an.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True
        )

        st.caption(
            "Lưu ý: PP và DPP sử dụng nội suy trong năm, giả định "
            "dòng tiền phát sinh đều trong năm. Các chỉ tiêu là công cụ "
            "hỗ trợ phân tích, không thay thế việc đánh giá rủi ro và "
            "các giả định thực tế của dự án."
        )

else:
    st.info(
        "Hãy nhập các thông số, chỉnh sửa dòng tiền và nhấn "
        "'TÍNH TOÁN CÁC CHỈ TIÊU' để xem kết quả."
    )
