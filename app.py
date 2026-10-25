
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

st.title("📊 THẨM ĐỊNH HIỆU QUẢ TÀI CHÍNH DỰ ÁN")
st.caption(
    "Tính toán NPV, IRR, MIRR, PI, PP và DPP. "
    "Đơn vị tiền tệ: triệu đồng."
)

st.info(
    "Nhập vốn đầu tư năm 0 dưới dạng số dương. "
    "Dòng tiền thu vào nhập số dương; dòng tiền chi ra nhập số âm. "
    "Lãi suất chiết khấu được sử dụng để tính NPV, PI, DPP "
    "và làm lãi suất tài trợ, tái đầu tư khi tính MIRR."
)


# =====================================================
# 2. CÁC HÀM TÍNH TOÁN
# =====================================================
def tinh_npv(dong_tien, lai_suat):
    return float(npf.npv(lai_suat, dong_tien))


def tinh_irr(dong_tien):
    if not (
        any(x < 0 for x in dong_tien)
        and any(x > 0 for x in dong_tien)
    ):
        return None

    try:
        ket_qua = float(npf.irr(dong_tien))
        return ket_qua if np.isfinite(ket_qua) else None
    except (ValueError, ZeroDivisionError, FloatingPointError):
        return None


def tinh_mirr(dong_tien, lai_suat):
    """
    MIRR sử dụng cùng một lãi suất cho tài trợ
    và tái đầu tư theo yêu cầu của người dùng.
    """
    if not (
        any(x < 0 for x in dong_tien)
        and any(x > 0 for x in dong_tien)
    ):
        return None

    try:
        ket_qua = float(
            npf.mirr(
                dong_tien,
                finance_rate=lai_suat,
                reinvest_rate=lai_suat
            )
        )
        return ket_qua if np.isfinite(ket_qua) else None
    except (ValueError, ZeroDivisionError, FloatingPointError):
        return None


def tinh_pi(dong_tien, lai_suat):
    """
    PI = PV các dòng tiền dương / PV trị tuyệt đối
    của tất cả dòng tiền âm, bao gồm năm 0.
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


def tinh_hoan_von(dong_tien, lai_suat=None):
    """
    PP: hoàn vốn không chiết khấu.
    DPP: hoàn vốn có chiết khấu.
    Nội suy trong năm giả định dòng tiền phát sinh đều.
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

            phan_nam = max(
                0.0,
                min(1.0, -truoc_do / cf)
            )
            return nam - 1 + phan_nam

    return None


def dinh_dang_tien(x):
    return f"{x:,.2f}"


def dinh_dang_ty_le(x):
    if x is None or not np.isfinite(x):
        return "Không xác định"
    return f"{x * 100:.2f}%"


def dinh_dang_hoan_von(x):
    if x is None:
        return "Không hoàn vốn trong thời gian dự án"
    return f"{x:.2f} năm"


def tao_excel(bang_chi_tieu, bang_dong_tien):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        bang_chi_tieu.to_excel(
            writer,
            sheet_name="Ket_qua_tham_dinh",
            index=False
        )

        bang_dong_tien.to_excel(
            writer,
            sheet_name="Phan_tich_dong_tien",
            index=False
        )

        for sheet in writer.sheets.values():
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions

            for cells in sheet.columns:
                max_length = max(
                    len(str(cell.value))
                    if cell.value is not None else 0
                    for cell in cells
                )
                sheet.column_dimensions[
                    cells[0].column_letter
                ].width = min(max_length + 3, 35)

    output.seek(0)
    return output.getvalue()


# =====================================================
# 3. NHẬP THÔNG SỐ DỰ ÁN
# =====================================================
st.header("1. Nhập thông số đầu tư")

col1, col2 = st.columns(2)

with col1:
    von_dau_tu = st.number_input(
        "Vốn đầu tư ban đầu tại năm 0 (triệu đồng)",
        min_value=0.01,
        value=1000.0,
        step=100.0,
        format="%.2f"
    )

with col2:
    so_nam = st.number_input(
        "Số năm đầu tư",
        min_value=1,
        max_value=50,
        value=5,
        step=1
    )

lai_suat_pct = st.number_input(
    "Lãi suất chiết khấu (%)",
    min_value=0.0,
    max_value=500.0,
    value=20.0,
    step=1.0,
    format="%.2f"
)

r = lai_suat_pct / 100

st.caption(
    f"Vốn đầu tư năm 0: {dinh_dang_tien(von_dau_tu)} triệu đồng | "
    f"Lãi suất chiết khấu: {lai_suat_pct:.2f}%"
)


# =====================================================
# 4. NHẬP DÒNG TIỀN
# =====================================================
st.header("2. Nhập dòng tiền theo từng năm")

st.write(
    "Bảng dưới đây gồm dòng tiền năm 0 và các năm tiếp theo. "
    "Bạn có thể điều chỉnh dòng tiền trực tiếp trên bảng."
)

df_dong_tien = pd.DataFrame({
    "Năm": list(range(int(so_nam) + 1)),
    "Dòng tiền (triệu đồng)": [
        -float(von_dau_tu)
    ] + [
        0.0
    ] * int(so_nam)
})

# Giá trị mặc định minh họa cho dự án 5 năm
if int(so_nam) == 5:
    df_dong_tien["Dòng tiền (triệu đồng)"] = [
        -float(von_dau_tu),
        -200.0,
        -100.0,
        300.0,
        800.0,
        1200.0
    ]

df_dong_tien["Năm"] = df_dong_tien["Năm"].astype(int)

df_da_sua = st.data_editor(
    df_dong_tien,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key="bang_dong_tien_du_an",
    disabled=["Năm"],
    column_config={
        "Năm": st.column_config.NumberColumn(
            "Năm",
            format="%d"
        ),
        "Dòng tiền (triệu đồng)": st.column_config.NumberColumn(
            "Dòng tiền (triệu đồng)",
            min_value=-1_000_000_000_000.0,
            max_value=1_000_000_000_000.0,
            step=100.0,
            format="%.2f",
            required=True
        )
    }
)

# Năm 0 phải bằng âm vốn đầu tư ban đầu
dong_tien_nguoi_dung = (
    df_da_sua["Dòng tiền (triệu đồng)"]
    .astype(float)
    .tolist()
)

dong_tien_nguoi_dung[0] = -float(von_dau_tu)

st.caption(
    "Năm 0 được tự động gán bằng âm vốn đầu tư ban đầu. "
    "Các dòng tiền từ năm 1 trở đi có thể nhập số dương hoặc âm."
)


# =====================================================
# 5. TÍNH TOÁN
# =====================================================
if st.button(
    "🧮 TÍNH CÁC CHỈ TIÊU THẨM ĐỊNH",
    type="primary",
    use_container_width=True
):
    if df_da_sua["Dòng tiền (triệu đồng)"].isna().any():
        st.error("Vui lòng nhập đầy đủ dòng tiền.")
        st.stop()

    dong_tien = dong_tien_nguoi_dung

    npv = tinh_npv(dong_tien, r)
    irr = tinh_irr(dong_tien)
    mirr = tinh_mirr(dong_tien, r)
    pi = tinh_pi(dong_tien, r)
    pp = tinh_hoan_von(dong_tien)
    dpp = tinh_hoan_von(dong_tien, lai_suat=r)

    bang = pd.DataFrame({
        "Năm": list(range(int(so_nam) + 1)),
        "Dòng tiền (triệu đồng)": dong_tien
    })

    bang["Hệ số chiết khấu"] = [
        1 / ((1 + r) ** nam)
        for nam in range(int(so_nam) + 1)
    ]

    bang["Giá trị hiện tại (triệu đồng)"] = (
        bang["Dòng tiền (triệu đồng)"]
        * bang["Hệ số chiết khấu"]
    )

    bang["Dòng tiền tích lũy (triệu đồng)"] = (
        bang["Dòng tiền (triệu đồng)"].cumsum()
    )

    bang["Giá trị hiện tại tích lũy (triệu đồng)"] = (
        bang["Giá trị hiện tại (triệu đồng)"].cumsum()
    )

    ket_qua = {
        "von_dau_tu": float(von_dau_tu),
        "so_nam": int(so_nam),
        "lai_suat_pct": float(lai_suat_pct),
        "dong_tien": dong_tien,
        "npv": npv,
        "irr": irr,
        "mirr": mirr,
        "pi": pi,
        "pp": pp,
        "dpp": dpp,
        "bang": bang
    }

    st.session_state["ket_qua_tham_dinh"] = ket_qua


# =====================================================
# 6. HIỂN THỊ KẾT QUẢ
# =====================================================
if "ket_qua_tham_dinh" in st.session_state:
    kq = st.session_state["ket_qua_tham_dinh"]

    # Không hiển thị kết quả cũ khi thông số vừa thay đổi
    thong_so_hien_tai = (
        float(von_dau_tu),
        int(so_nam),
        float(lai_suat_pct),
        tuple(dong_tien_nguoi_dung)
    )

    thong_so_da_tinh = (
        kq["von_dau_tu"],
        kq["so_nam"],
        kq["lai_suat_pct"],
        tuple(kq["dong_tien"])
    )

    if thong_so_hien_tai != thong_so_da_tinh:
        st.warning(
            "Bạn đã thay đổi thông số hoặc dòng tiền. "
            "Hãy nhấn nút tính toán để cập nhật kết quả."
        )
    else:
        st.divider()
        st.header("3. Kết quả thẩm định")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "NPV (triệu đồng)",
            dinh_dang_tien(kq["npv"])
        )
        c2.metric(
            "IRR",
            dinh_dang_ty_le(kq["irr"])
        )
        c3.metric(
            "MIRR",
            dinh_dang_ty_le(kq["mirr"])
        )

        c4, c5, c6 = st.columns(3)

        c4.metric(
            "PI",
            f"{kq['pi']:.4f}"
            if kq["pi"] is not None
            else "Không xác định"
        )
        c5.metric(
            "PP",
            dinh_dang_hoan_von(kq["pp"])
        )
        c6.metric(
            "DPP",
            dinh_dang_hoan_von(kq["dpp"])
        )

        # ---------------------------------------------
        # NHẬN XÉT
        # ---------------------------------------------
        st.header("4. Nhận xét tham khảo")

        if kq["npv"] > 0:
            st.success(
                "NPV > 0: Dự án tạo giá trị hiện tại ròng dương "
                "theo lãi suất chiết khấu đã chọn."
            )
        elif kq["npv"] < 0:
            st.warning(
                "NPV < 0: Dự án chưa bù đắp được chi phí vốn "
                "theo lãi suất chiết khấu đã chọn."
            )
        else:
            st.info(
                "NPV = 0: Dự án hòa vốn theo tiêu chuẩn NPV."
            )

        if kq["irr"] is not None:
            if kq["irr"] > r:
                st.write(
                    f"IRR ({kq['irr']:.2%}) lớn hơn lãi suất "
                    f"chiết khấu ({r:.2%}). Với dòng tiền thông thường, "
                    "đây là tín hiệu thuận lợi."
                )
            else:
                st.write(
                    f"IRR ({kq['irr']:.2%}) không vượt lãi suất "
                    "chiết khấu. Cần xem xét thêm hiệu quả dự án."
                )
        else:
            st.write(
                "IRR không xác định được bằng phép tính hiện tại. "
                "Cần kiểm tra cấu trúc dòng tiền; dự án có thể không có "
                "IRR thực hoặc có nhiều nghiệm."
            )

        if kq["mirr"] is not None:
            st.write(
                f"MIRR = {kq['mirr']:.2%}, sử dụng lãi suất chiết khấu "
                f"{r:.2%} làm lãi suất tài trợ và tái đầu tư."
            )
        else:
            st.write(
                "MIRR không xác định: cần ít nhất một dòng tiền âm "
                "và một dòng tiền dương."
            )

        if kq["pi"] is not None:
            if kq["pi"] > 1:
                st.write("PI > 1: Giá trị hiện tại dòng tiền dương lớn hơn dòng tiền âm.")
            elif kq["pi"] < 1:
                st.write("PI < 1: Giá trị hiện tại dòng tiền dương nhỏ hơn dòng tiền âm.")
            else:
                st.write("PI = 1: Giá trị hiện tại dòng tiền dương bằng dòng tiền âm.")
        else:
            st.write("Không xác định PI do không có dòng tiền âm.")

        # ---------------------------------------------
        # BẢNG DÒNG TIỀN
        # ---------------------------------------------
        st.header("5. Bảng phân tích dòng tiền")

        st.dataframe(
            kq["bang"].style.format({
                "Dòng tiền (triệu đồng)": "{:,.2f}",
                "Hệ số chiết khấu": "{:.4f}",
                "Giá trị hiện tại (triệu đồng)": "{:,.2f}",
                "Dòng tiền tích lũy (triệu đồng)": "{:,.2f}",
                "Giá trị hiện tại tích lũy (triệu đồng)": "{:,.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )

        # ---------------------------------------------
        # BIỂU ĐỒ
        # ---------------------------------------------
        st.header("6. Biểu đồ dòng tiền")

        st.bar_chart(
            kq["bang"].set_index("Năm")[
                ["Dòng tiền (triệu đồng)"]
            ]
        )

        st.line_chart(
            kq["bang"].set_index("Năm")[
                [
                    "Dòng tiền tích lũy (triệu đồng)",
                    "Giá trị hiện tại tích lũy (triệu đồng)"
                ]
            ]
        )

        # ---------------------------------------------
        # XUẤT EXCEL
        # ---------------------------------------------
        st.header("7. Xuất báo cáo Excel")

        bang_chi_tieu = pd.DataFrame({
            "Chỉ tiêu": [
                "Đơn vị tiền tệ",
                "Vốn đầu tư ban đầu năm 0",
                "Số năm đầu tư",
                "Lãi suất chiết khấu",
                "NPV (triệu đồng)",
                "IRR",
                "MIRR",
                "PI",
                "PP (năm)",
                "DPP (năm)"
            ],
            "Giá trị": [
                "Triệu đồng",
                kq["von_dau_tu"],
                kq["so_nam"],
                kq["lai_suat_pct"] / 100,
                kq["npv"],
                kq["irr"],
                kq["mirr"],
                kq["pi"],
                kq["pp"],
                kq["dpp"]
            ]
        })

        file_excel = tao_excel(
            bang_chi_tieu,
            kq["bang"]
        )

        st.download_button(
            label="📥 TẢI BÁO CÁO EXCEL (.xlsx)",
            data=file_excel,
            file_name="bao_cao_tham_dinh_du_an.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True
        )

        st.caption(
            "PP và DPP được nội suy trong năm, giả định dòng tiền phát sinh "
            "đều trong năm. PI được tính bằng PV dòng tiền dương chia cho "
            "PV trị tuyệt đối tất cả dòng tiền âm."
        )

else:
    st.info(
        "Nhập vốn đầu tư năm 0, thời gian đầu tư, lãi suất chiết khấu "
        "và dòng tiền từng năm, sau đó nhấn nút tính toán."
    )
