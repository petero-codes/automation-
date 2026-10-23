import random
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class FinancialCell:
    row: int
    col: int
    value: str
    is_formula: bool = False
    is_header: bool = False
    format_currency: bool = False

@dataclass
class FinancialModel:
    model_name: str
    sheet_title: str
    row_count: int
    headers: List[str]
    cells: List[FinancialCell]

class FinancialGenerator:
    """
    Generates dynamic financial spreadsheet models with 50-90 rows of dynamic data
    and live accounting formulas (=SUM, =AVERAGE, =IF, =VLOOKUP).
    """
    def generate_model(self) -> FinancialModel:
        row_count = random.randint(52, 88)
        model_types = ["saas_unit_economics", "dcf_valuation", "opex_variance"]
        selected = random.choice(model_types)

        if selected == "saas_unit_economics":
            return self._build_saas_model(row_count)
        elif selected == "dcf_valuation":
            return self._build_dcf_model(row_count)
        else:
            return self._build_opex_model(row_count)

    def _build_saas_model(self, rows: int) -> FinancialModel:
        headers = ["Cohort", "New ARR ($)", "Expansion ARR ($)", "Churned ARR ($)", "Net ARR ($)", "CAC ($)", "LTV ($)"]
        cells: List[FinancialCell] = []

        # Headers (Row 1)
        for col_idx, h in enumerate(headers, start=1):
            cells.append(FinancialCell(row=1, col=col_idx, value=h, is_header=True))

        # Data (Rows 2 to rows + 1)
        for r in range(2, rows + 2):
            cohort_name = f"2026-M{r:02d}"
            new_arr = random.randint(45000, 185000)
            exp_arr = random.randint(12000, 65000)
            churn_arr = random.randint(5000, 28000)
            cac = random.randint(14000, 42000)
            
            # Direct data entries
            cells.append(FinancialCell(row=r, col=1, value=cohort_name))
            cells.append(FinancialCell(row=r, col=2, value=str(new_arr), format_currency=True))
            cells.append(FinancialCell(row=r, col=3, value=str(exp_arr), format_currency=True))
            cells.append(FinancialCell(row=r, col=4, value=str(churn_arr), format_currency=True))
            # Live Formula: Net ARR = New ARR + Expansion - Churned
            cells.append(FinancialCell(row=r, col=5, value=f"=B{r}+C{r}-D{r}", is_formula=True, format_currency=True))
            cells.append(FinancialCell(row=r, col=6, value=str(cac), format_currency=True))
            # Live Formula: LTV = IF(D{r}>0, (B{r}+C{r})*3.5, B{r}*4.0)
            cells.append(FinancialCell(row=r, col=7, value=f"=IF(D{r}>0, (B{r}+C{r})*3.5, B{r}*4)", is_formula=True, format_currency=True))

        # Summary Row (Row rows + 2)
        summary_row = rows + 2
        cells.append(FinancialCell(row=summary_row, col=1, value="TOTAL / AVG", is_header=True))
        cells.append(FinancialCell(row=summary_row, col=2, value=f"=SUM(B2:B{summary_row-1})", is_formula=True, format_currency=True))
        cells.append(FinancialCell(row=summary_row, col=3, value=f"=SUM(C2:C{summary_row-1})", is_formula=True, format_currency=True))
        cells.append(FinancialCell(row=summary_row, col=4, value=f"=SUM(D2:D{summary_row-1})", is_formula=True, format_currency=True))
        cells.append(FinancialCell(row=summary_row, col=5, value=f"=SUM(E2:E{summary_row-1})", is_formula=True, format_currency=True))
        cells.append(FinancialCell(row=summary_row, col=6, value=f"=AVERAGE(F2:F{summary_row-1})", is_formula=True, format_currency=True))
        cells.append(FinancialCell(row=summary_row, col=7, value=f"=AVERAGE(G2:G{summary_row-1})", is_formula=True, format_currency=True))

        return FinancialModel(
            model_name="FY27_SaaS_Unit_Economics",
            sheet_title="Cohort Economics",
            row_count=rows,
            headers=headers,
            cells=cells
        )

    def _build_dcf_model(self, rows: int) -> FinancialModel:
        headers = ["Period", "Revenue ($)", "COGS ($)", "Gross Profit ($)", "OPEX ($)", "EBITDA ($)", "FCF ($)"]
        cells: List[FinancialCell] = []

        for col_idx, h in enumerate(headers, start=1):
            cells.append(FinancialCell(row=1, col=col_idx, value=h, is_header=True))

        for r in range(2, rows + 2):
            period = f"Period_{r-1}"
            rev = random.randint(120000, 950000)
            cogs = int(rev * random.uniform(0.25, 0.45))
            opex = int(rev * random.uniform(0.30, 0.42))

            cells.append(FinancialCell(row=r, col=1, value=period))
            cells.append(FinancialCell(row=r, col=2, value=str(rev), format_currency=True))
            cells.append(FinancialCell(row=r, col=3, value=str(cogs), format_currency=True))
            cells.append(FinancialCell(row=r, col=4, value=f"=B{r}-C{r}", is_formula=True, format_currency=True))
            cells.append(FinancialCell(row=r, col=5, value=str(opex), format_currency=True))
            cells.append(FinancialCell(row=r, col=6, value=f"=D{r}-E{r}", is_formula=True, format_currency=True))
            cells.append(FinancialCell(row=r, col=7, value=f"=F{r}*0.79", is_formula=True, format_currency=True))

        summary_row = rows + 2
        cells.append(FinancialCell(row=summary_row, col=1, value="TOTAL VALUATION", is_header=True))
        cells.append(FinancialCell(row=summary_row, col=2, value=f"=SUM(B2:B{summary_row-1})", is_formula=True, format_currency=True))
        cells.append(FinancialCell(row=summary_row, col=7, value=f"=SUM(G2:G{summary_row-1})", is_formula=True, format_currency=True))

        return FinancialModel(
            model_name="Corporate_DCF_Valuation",
            sheet_title="DCF Projections",
            row_count=rows,
            headers=headers,
            cells=cells
        )

    def _build_opex_model(self, rows: int) -> FinancialModel:
        headers = ["Dept Code", "Headcount", "Salaries ($)", "Cloud Infra ($)", "Travel ($)", "Total OPEX ($)"]
        cells: List[FinancialCell] = []

        for col_idx, h in enumerate(headers, start=1):
            cells.append(FinancialCell(row=1, col=col_idx, value=h, is_header=True))

        for r in range(2, rows + 2):
            dept = f"D-{100 + r}"
            hc = random.randint(4, 45)
            sal = hc * random.randint(8500, 16000)
            cloud = random.randint(12000, 95000)
            travel = random.randint(2000, 18000)

            cells.append(FinancialCell(row=r, col=1, value=dept))
            cells.append(FinancialCell(row=r, col=2, value=str(hc)))
            cells.append(FinancialCell(row=r, col=3, value=str(sal), format_currency=True))
            cells.append(FinancialCell(row=r, col=4, value=str(cloud), format_currency=True))
            cells.append(FinancialCell(row=r, col=5, value=str(travel), format_currency=True))
            cells.append(FinancialCell(row=r, col=6, value=f"=SUM(C{r}:E{r})", is_formula=True, format_currency=True))

        summary_row = rows + 2
        cells.append(FinancialCell(row=summary_row, col=1, value="CONSOLIDATED", is_header=True))
        cells.append(FinancialCell(row=summary_row, col=2, value=f"=SUM(B2:B{summary_row-1})", is_formula=True))
        cells.append(FinancialCell(row=summary_row, col=6, value=f"=SUM(F2:F{summary_row-1})", is_formula=True, format_currency=True))

        return FinancialModel(
            model_name="Departmental_OPEX_Variance",
            sheet_title="OPEX Model",
            row_count=rows,
            headers=headers,
            cells=cells
        )
