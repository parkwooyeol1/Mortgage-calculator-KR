# -*- coding: utf-8 -*-
"""
저당액 계산 프로그램 (GUI 버전)

규칙:
1) 근저당권자가 '대부/개인'인 경우
   - 대출원금 = 채권최고액 / 150 * 100
   - 기간 계산 없이 위 값을 그대로 저당액으로 사용

2) 근저당권자가 '은행'인 경우
   - 대출원금 = 채권최고액 / 120 * 100
   - 접수일자 ~ 오늘까지 경과월수가 1개월 미만이면
       => 대출원금을 그대로 저당액으로 사용 (상환계산 안 함)
   - 1개월 이상이면
       => 20년(240개월) / 연 3% 원리금균등상환 기준으로
          경과월수만큼 상환했다고 가정하고 남은 잔액을 저당액으로 사용
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date


# ----------------------------
# 고해상도(HiDPI) 모니터 대응
#   - 모니터를 바꾼 뒤 글자/버튼이 뿌옇게 번지는 현상(화질 저하)은
#     프로세스가 DPI 인식을 하지 않아 Windows가 저해상도 화면을
#     강제로 확대해서 그리기 때문입니다.
#   - Tk를 만들기 '전에' 프로세스를 DPI 인식으로 설정하면 원래 해상도
#     그대로 선명하게 렌더링됩니다.
# ----------------------------

def enable_hidpi():
    """Windows에서 프로세스를 per-monitor DPI 인식으로 설정한다.

    반환값: 96DPI 기준 배율(scale factor). 실패 시 1.0.
    """
    if not sys.platform.startswith("win"):
        return 1.0

    import ctypes

    # 1) DPI 인식 활성화 (가능한 최신 API부터 시도)
    try:
        # PER_MONITOR_AWARE_V2 (-4): 가장 선명, Win10 1703+
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except Exception:
        try:
            # PER_MONITOR_AWARE (2): Win8.1+
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()  # 구형 폴백
            except Exception:
                pass

    # 2) 현재 모니터의 실제 배율 계산 (96DPI = 100%)
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
        return max(1.0, dpi / 96.0)
    except Exception:
        return 1.0


# ----------------------------
# 계산 로직
# ----------------------------

def elapsed_months(start_date: date, today: date) -> int:
    if today < start_date:
        return 0
    years = today.year - start_date.year
    months = today.month - start_date.month
    if today.day < start_date.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    return years * 12 + months


def remaining_balance(principal: float, annual_rate: float, total_months: int, paid_months: int) -> float:
    r = annual_rate / 12
    n = total_months

    if paid_months <= 0:
        return principal
    if paid_months >= n:
        return 0.0

    M = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)

    balance = principal
    for _ in range(paid_months):
        interest = balance * r
        principal_paid = M - interest
        balance -= principal_paid

    return balance


def calc_mortgage(
    max_claim_amount: float,
    is_loan_company: bool,
    received_date: date = None,
    today: date = None,
    annual_rate: float = 0.03,
    loan_years: int = 20,
):
    if today is None:
        today = date.today()

    result = {
        "채권최고액": max_claim_amount,
        "기준일": today,
        "접수일자": None,
        "경과월수": None,
    }

    if is_loan_company:
        principal = max_claim_amount / 150 * 100
        result["근저당권자_구분"] = "대부 / 개인"
        result["대출원금_추정"] = principal
        result["저당액"] = principal
        result["계산방식"] = "대부/개인: 채권최고액÷150×100, 기간계산 없음"
        return result

    principal = max_claim_amount / 120 * 100
    result["근저당권자_구분"] = "은행"
    result["대출원금_추정"] = principal

    if received_date is None:
        raise ValueError("은행 케이스는 접수일자가 필요합니다.")

    months = elapsed_months(received_date, today)
    result["경과월수"] = months
    result["접수일자"] = received_date

    if months < 1:
        result["저당액"] = principal
        result["계산방식"] = "은행: 채권최고액÷120×100, 접수 1개월 미만이라 기간계산 없이 원금 그대로"
    else:
        total_months = loan_years * 12
        balance = remaining_balance(principal, annual_rate, total_months, months)
        result["저당액"] = balance
        result["계산방식"] = (
            f"은행: 채권최고액÷120×100 후 {loan_years}년/연{annual_rate*100:.1f}% "
            f"원리금균등상환 기준 {months}개월 경과분 차감"
        )

    return result


def parse_date(s: str) -> date:
    s = s.strip().replace(".", "-").replace("/", "-")
    if "-" not in s and len(s) == 8:
        s = f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    parts = s.split("-")
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    return date(y, m, d)


# ----------------------------
# GUI
# ----------------------------

# 색상 팔레트 (sRGB 표준값 기준 - 모니터가 달라도 일관된 색감)
# 라이트/다크 두 벌을 정의하고, 실행 중 토글로 전환한다.
THEMES = {
    "light": {
        "BG":          "#eef1f6",   # 앱 배경
        "CARD":        "#ffffff",   # 입력/결과 카드 배경
        "PRIMARY":     "#2563eb",   # 메인 파랑 (버튼)
        "PRIMARY_ACT": "#1d4ed8",
        "TEXT":        "#1f2933",   # 기본 글자색 (대비 높음)
        "MUTED":       "#6b7280",   # 보조 글자색
        "BORDER":      "#cbd5e1",   # 테두리
        "DISABLED_BG": "#f1f3f7",   # 비활성 입력칸 배경
        "TOGGLE_ICON": "◐ 다크 모드",   # 라이트일 때: 다크로 전환 버튼
    },
    "dark": {
        "BG":          "#1e2430",
        "CARD":        "#262d3a",
        "PRIMARY":     "#3b82f6",
        "PRIMARY_ACT": "#2563eb",
        "TEXT":        "#e5e9f0",
        "MUTED":       "#9aa4b2",
        "BORDER":      "#3a4453",
        "DISABLED_BG": "#2a313d",
        "TOGGLE_ICON": "◑ 라이트 모드",   # 다크일 때: 라이트로 전환 버튼
    },
}


class MortgageApp(tk.Tk):
    def __init__(self, scale: float = 1.0, theme: str = "light"):
        super().__init__()

        # 화면 배율에 맞춰 Tk 폰트/위젯 스케일링 (선명도 유지)
        self.scale = scale
        try:
            self.tk.call("tk", "scaling", scale * 96.0 / 72.0)
        except Exception:
            pass

        self.theme_name = theme if theme in THEMES else "light"
        self.colors = THEMES[self.theme_name]
        self._themed = []            # (위젯, 역할) 목록 - 테마 전환 시 다시 칠함
        self._amount_placeholder = True

        self.title("저당액 계산 프로그램")
        w, h = int(480 * scale), int(600 * scale)
        self.geometry(f"{w}x{h}")
        self.minsize(w, h)
        self.resizable(False, False)

        self.creditor_var = tk.StringVar(value="은행")  # 기본 선택: 은행

        self.style = ttk.Style()
        self._build_widgets()
        self._apply_theme()

    def _f(self, size, weight="normal"):
        """배율을 반영한 폰트 튜플."""
        return ("맑은 고딕", max(1, int(round(size * self.scale))), weight)

    def _reg(self, widget, role):
        """테마 대상 위젯을 역할과 함께 등록한다."""
        self._themed.append((widget, role))
        return widget

    # ----- 테마 적용 -----
    def _setup_style(self):
        c = self.colors
        try:
            self.style.theme_use("clam")  # 색상 커스터마이즈가 잘 먹는 테마
        except Exception:
            pass

        self.style.configure("TRadiobutton", font=self._f(11),
                             background=c["BG"], foreground=c["TEXT"],
                             indicatorcolor=c["CARD"])
        self.style.map("TRadiobutton",
                       background=[("active", c["BG"])],
                       foreground=[("disabled", c["MUTED"])],
                       indicatorcolor=[("selected", c["PRIMARY"])])

        # 계산 버튼
        self.style.configure("Accent.TButton", font=self._f(13, "bold"),
                             foreground="#ffffff", background=c["PRIMARY"],
                             borderwidth=0, focusthickness=0, padding=(0, 12))
        self.style.map("Accent.TButton",
                       background=[("active", c["PRIMARY_ACT"]), ("pressed", c["PRIMARY_ACT"])],
                       foreground=[("disabled", "#e5e7eb")])

    def _apply_theme(self):
        c = self.colors
        self._setup_style()
        self.configure(bg=c["BG"])

        for w, role in self._themed:
            if role == "frame":
                w.configure(bg=c["BG"])
            elif role == "title":
                w.configure(bg=c["BG"], fg=c["TEXT"])
            elif role == "muted":
                w.configure(bg=c["BG"], fg=c["MUTED"])
            elif role == "text_label":
                w.configure(bg=c["BG"], fg=c["TEXT"])
            elif role == "entry":
                w.configure(bg=c["CARD"], fg=c["TEXT"],
                            highlightbackground=c["BORDER"], highlightcolor=c["PRIMARY"],
                            disabledbackground=c["DISABLED_BG"], insertbackground=c["TEXT"])
            elif role == "result":
                w.configure(bg=c["CARD"], fg=c["TEXT"], highlightbackground=c["BORDER"])

        # 상태에 따라 색이 달라지는 위젯들 마무리
        self.amount_entry.configure(fg=(c["MUTED"] if self._amount_placeholder else c["TEXT"]))
        self.toggle_btn.configure(text=c["TOGGLE_ICON"], bg=c["BG"], fg=c["TEXT"],
                                  activebackground=c["BG"], activeforeground=c["PRIMARY"])
        self._on_creditor_change()
        self._set_titlebar_dark(self.theme_name == "dark")

    def _toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.colors = THEMES[self.theme_name]
        self._apply_theme()

    def _set_titlebar_dark(self, dark: bool):
        """Windows 제목표시줄도 테마에 맞춰 어둡게/밝게 (Win10 2004+)."""
        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            value = ctypes.c_int(1 if dark else 0)
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

    # ----- 화면 구성 -----
    def _build_widgets(self):
        pad = {"padx": 16, "pady": 6}

        # 헤더: 제목 + 우측 테마 토글 버튼
        header = self._reg(tk.Frame(self), "frame")
        header.pack(fill="x", padx=16, pady=(18, 6))
        title = self._reg(tk.Label(header, text="저당액 계산 프로그램", font=self._f(16, "bold")), "title")
        title.pack(side="left")
        self.toggle_btn = tk.Button(header, text="", font=self._f(10), relief="flat",
                                    bd=0, cursor="hand2", takefocus=0,
                                    command=self._toggle_theme)
        self.toggle_btn.pack(side="right")

        # 채권최고액 입력
        frame1 = self._reg(tk.Frame(self), "frame")
        frame1.pack(fill="x", **pad)
        self._reg(tk.Label(frame1, text="채권최고액 (원)", font=self._f(11)), "muted").pack(anchor="w")
        self.amount_entry = self._reg(
            tk.Entry(frame1, font=self._f(12), relief="solid", bd=1, highlightthickness=1), "entry")
        self.amount_entry.pack(fill="x", pady=4, ipady=int(3 * self.scale))
        self.amount_entry.insert(0, "예: 385000000")
        self.amount_entry.bind("<FocusIn>", self._clear_placeholder)

        # 근저당권자 구분 - 라디오 버튼(마우스 클릭)
        frame2 = self._reg(tk.Frame(self), "frame")
        frame2.pack(fill="x", **pad)
        self._reg(tk.Label(frame2, text="근저당권자 구분", font=self._f(11)), "muted").pack(anchor="w")

        radio_frame = self._reg(tk.Frame(frame2), "frame")
        radio_frame.pack(fill="x", pady=4)

        rb_bank = ttk.Radiobutton(
            radio_frame, text="은행", variable=self.creditor_var, value="은행",
            command=self._on_creditor_change
        )
        rb_loan = ttk.Radiobutton(
            radio_frame, text="대부 / 개인", variable=self.creditor_var, value="대부",
            command=self._on_creditor_change
        )
        rb_bank.pack(side="left", padx=(0, 20))
        rb_loan.pack(side="left")

        # 접수일자 입력 (은행 선택시만 활성) - 년/월/일 칸 3개로 분리
        self.date_frame = self._reg(tk.Frame(self), "frame")
        self.date_frame.pack(fill="x", **pad)
        self.date_label = self._reg(tk.Label(self.date_frame, text="접수일자", font=self._f(11)), "muted")
        self.date_label.pack(anchor="w")

        date_input_frame = self._reg(tk.Frame(self.date_frame), "frame")
        date_input_frame.pack(fill="x", pady=4)

        def _mk_date_entry(width):
            return self._reg(
                tk.Entry(date_input_frame, font=self._f(12), width=width, justify="center",
                         relief="solid", bd=1, highlightthickness=1), "entry")

        self.year_entry = _mk_date_entry(6)
        self.year_entry.pack(side="left", ipady=int(2 * self.scale))
        self._reg(tk.Label(date_input_frame, text="년", font=self._f(11)), "text_label").pack(side="left", padx=(4, 12))

        self.month_entry = _mk_date_entry(4)
        self.month_entry.pack(side="left", ipady=int(2 * self.scale))
        self._reg(tk.Label(date_input_frame, text="월", font=self._f(11)), "text_label").pack(side="left", padx=(4, 12))

        self.day_entry = _mk_date_entry(4)
        self.day_entry.pack(side="left", ipady=int(2 * self.scale))
        self._reg(tk.Label(date_input_frame, text="일", font=self._f(11)), "text_label").pack(side="left", padx=(4, 0))

        self.date_widgets = [self.year_entry, self.month_entry, self.day_entry]

        # 계산 버튼
        calc_btn = ttk.Button(
            self, text="계산하기", style="Accent.TButton",
            command=self._on_calculate
        )
        calc_btn.pack(fill="x", padx=16, pady=(16, 8))

        # 결과 표시 영역
        self.result_box = self._reg(
            tk.Text(self, font=self._f(10), height=10, relief="solid", bd=1,
                    highlightthickness=1, padx=10, pady=8, state="disabled", wrap="word"), "result")
        self.result_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _clear_placeholder(self, event):
        if self._amount_placeholder and self.amount_entry.get().startswith("예:"):
            self.amount_entry.delete(0, "end")
            self._amount_placeholder = False
            self.amount_entry.configure(fg=self.colors["TEXT"])

    def _on_creditor_change(self):
        c = self.colors
        if self.creditor_var.get() == "은행":
            for w in self.date_widgets:
                w.configure(state="normal")
            self.date_label.configure(fg=c["MUTED"])
        else:
            for w in self.date_widgets:
                w.configure(state="disabled")
            self.date_label.configure(fg=c["BORDER"])

    def _on_calculate(self):
        try:
            amount_str = self.amount_entry.get().strip().replace(",", "")
            if amount_str.startswith("예:") or amount_str == "":
                messagebox.showwarning("입력 오류", "채권최고액을 입력해주세요.")
                return
            max_claim_amount = float(amount_str)

            is_loan_company = (self.creditor_var.get() == "대부")

            received_date = None
            if not is_loan_company:
                year_str = self.year_entry.get().strip()
                month_str = self.month_entry.get().strip()
                day_str = self.day_entry.get().strip()
                if not (year_str and month_str and day_str):
                    messagebox.showwarning("입력 오류", "은행인 경우 접수일자(년/월/일)를 모두 입력해주세요.")
                    return
                try:
                    received_date = date(int(year_str), int(month_str), int(day_str))
                except ValueError:
                    messagebox.showwarning("입력 오류", "접수일자가 올바르지 않습니다. (예: 2025 / 8 / 25)")
                    return

            result = calc_mortgage(
                max_claim_amount=max_claim_amount,
                is_loan_company=is_loan_company,
                received_date=received_date,
            )

            self._show_result(result)

        except Exception as e:
            messagebox.showerror("오류", f"입력값을 다시 확인해주세요.\n\n{e}")

    def _show_result(self, result: dict):
        lines = []
        lines.append(f"채권최고액        : {result['채권최고액']:,.0f}원")
        lines.append(f"근저당권자 구분    : {result['근저당권자_구분']}")
        lines.append(f"대출원금(추정)     : {result['대출원금_추정']:,.0f}원")
        if result.get("접수일자"):
            lines.append(f"접수일자          : {result['접수일자']}")
        lines.append(f"기준일(오늘)       : {result['기준일']}")
        if result["경과월수"] is not None:
            lines.append(f"경과월수          : {result['경과월수']}개월")
        lines.append(f"계산방식          : {result['계산방식']}")
        lines.append("-" * 40)
        lines.append(f">>> 저당액(기입값) : {result['저당액']:,.0f}원")

        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("end", "\n".join(lines))
        self.result_box.configure(state="disabled")


if __name__ == "__main__":
    scale = enable_hidpi()          # DPI 인식 활성화 (Tk 생성 전에 호출해야 함)
    app = MortgageApp(scale=scale)
    # 초기 상태: 은행 선택이 기본값이므로 날짜 입력 활성화 상태 유지
    app.mainloop()
