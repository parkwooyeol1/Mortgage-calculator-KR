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

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date


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

class MortgageApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("저당액 계산 프로그램")
        self.geometry("480x520")
        self.resizable(False, False)
        self.configure(bg="#f4f5f7")

        self.creditor_var = tk.StringVar(value="은행")  # 기본 선택: 은행

        self._build_widgets()

    def _build_widgets(self):
        pad = {"padx": 16, "pady": 6}

        title = tk.Label(self, text="저당액 계산 프로그램", font=("맑은 고딕", 16, "bold"), bg="#f4f5f7")
        title.pack(pady=(20, 10))

        # 채권최고액 입력
        frame1 = tk.Frame(self, bg="#f4f5f7")
        frame1.pack(fill="x", **pad)
        tk.Label(frame1, text="채권최고액 (원)", font=("맑은 고딕", 11), bg="#f4f5f7").pack(anchor="w")
        self.amount_entry = tk.Entry(frame1, font=("맑은 고딕", 12))
        self.amount_entry.pack(fill="x", pady=4)
        self.amount_entry.insert(0, "예: 385000000")
        self.amount_entry.bind("<FocusIn>", self._clear_placeholder)

        # 근저당권자 구분 - 라디오 버튼(마우스 클릭)
        frame2 = tk.Frame(self, bg="#f4f5f7")
        frame2.pack(fill="x", **pad)
        tk.Label(frame2, text="근저당권자 구분", font=("맑은 고딕", 11), bg="#f4f5f7").pack(anchor="w")

        radio_frame = tk.Frame(frame2, bg="#f4f5f7")
        radio_frame.pack(fill="x", pady=4)

        style = ttk.Style()
        style.configure("TRadiobutton", font=("맑은 고딕", 11), background="#f4f5f7")

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
        self.date_frame = tk.Frame(self, bg="#f4f5f7")
        self.date_frame.pack(fill="x", **pad)
        self.date_label = tk.Label(self.date_frame, text="접수일자", font=("맑은 고딕", 11), bg="#f4f5f7")
        self.date_label.pack(anchor="w")

        date_input_frame = tk.Frame(self.date_frame, bg="#f4f5f7")
        date_input_frame.pack(fill="x", pady=4)

        self.year_entry = tk.Entry(date_input_frame, font=("맑은 고딕", 12), width=6, justify="center")
        self.year_entry.pack(side="left")
        tk.Label(date_input_frame, text="년", font=("맑은 고딕", 11), bg="#f4f5f7").pack(side="left", padx=(4, 12))

        self.month_entry = tk.Entry(date_input_frame, font=("맑은 고딕", 12), width=4, justify="center")
        self.month_entry.pack(side="left")
        tk.Label(date_input_frame, text="월", font=("맑은 고딕", 11), bg="#f4f5f7").pack(side="left", padx=(4, 12))

        self.day_entry = tk.Entry(date_input_frame, font=("맑은 고딕", 12), width=4, justify="center")
        self.day_entry.pack(side="left")
        tk.Label(date_input_frame, text="일", font=("맑은 고딕", 11), bg="#f4f5f7").pack(side="left", padx=(4, 0))

        self.date_widgets = [self.year_entry, self.month_entry, self.day_entry]

        # 계산 버튼
        calc_btn = tk.Button(
            self, text="계산하기", font=("맑은 고딕", 13, "bold"),
            bg="#2d6cdf", fg="white", activebackground="#1e54b8",
            command=self._on_calculate, height=2
        )
        calc_btn.pack(fill="x", padx=16, pady=(16, 8))

        # 결과 표시 영역
        self.result_box = tk.Text(self, font=("맑은 고딕", 10), height=10, bg="white", state="disabled")
        self.result_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _clear_placeholder(self, event):
        if self.amount_entry.get().startswith("예:"):
            self.amount_entry.delete(0, "end")

    def _on_creditor_change(self):
        if self.creditor_var.get() == "은행":
            for w in self.date_widgets:
                w.configure(state="normal")
            self.date_label.configure(fg="black")
        else:
            for w in self.date_widgets:
                w.configure(state="disabled")
            self.date_label.configure(fg="gray")

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
    app = MortgageApp()
    # 초기 상태: 은행 선택이 기본값이므로 날짜 입력 활성화 상태 유지
    app.mainloop()
