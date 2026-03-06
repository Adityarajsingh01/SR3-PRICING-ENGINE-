"""
SR3 SOFR Futures Calculation Engine
====================================
Implements CME Three-Month SOFR futures pricing per official CME specifications.

Key Formula:
  Price = 100 - R
  R = (PRODUCT(1 + r_i/360) for each calendar day - 1) * (360/N) * 100
  where r_i = SOFR for business day i (last preceding bday rate for weekends/holidays)
  N = total calendar days in reference quarter

Reference Quarter:
  From 3rd Wednesday of month 3 months BEFORE delivery month (inclusive)
  To 3rd Wednesday of delivery month (exclusive)

Contract Specs:
  Delivery months: Mar, Jun, Sep, Dec (quarterly)
  Tick size: 0.005 (half basis point for nearby) / 0.01 for deferred
  Tick value: $12.50 per contract
  DV01: $25 per basis point per contract
  Contract size: ~$1,000,000 notional (exact is $2,500 per index point)
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
import calendar
from typing import Dict, List, Tuple, Optional

# ─────────────────────────────────────────────
# US GOVERNMENT SECURITIES MARKET HOLIDAYS
# ─────────────────────────────────────────────

_US_HOLIDAYS = {
    # 2025
    date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17), date(2025, 4, 18),
    date(2025, 5, 26), date(2025, 6, 19), date(2025, 7, 4), date(2025, 9, 1),
    date(2025, 10, 13), date(2025, 11, 11), date(2025, 11, 27), date(2025, 12, 25),
    # 2026
    date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 4, 3),
    date(2026, 5, 25), date(2026, 6, 19), date(2026, 7, 3), date(2026, 9, 7),
    date(2026, 10, 12), date(2026, 11, 11), date(2026, 11, 26), date(2026, 12, 25),
    # 2027
    date(2027, 1, 1), date(2027, 1, 18), date(2027, 2, 15), date(2027, 3, 26),
    date(2027, 5, 31), date(2027, 6, 18), date(2027, 7, 5), date(2027, 9, 6),
    date(2027, 10, 11), date(2027, 11, 11), date(2027, 11, 25), date(2027, 12, 24),
    # 2028
    date(2028, 1, 1), date(2028, 1, 17), date(2028, 2, 21), date(2028, 4, 14),
    date(2028, 5, 29), date(2028, 6, 19), date(2028, 7, 4), date(2028, 9, 4),
    date(2028, 10, 9), date(2028, 11, 10), date(2028, 11, 23), date(2028, 12, 25),
}

def is_business_day(d: date) -> bool:
    """Check if date is a US government securities market business day."""
    return d.weekday() < 5 and d not in _US_HOLIDAYS

def get_prev_business_day(d: date) -> date:
    """Get the last preceding business day (may return d itself if it's a bday)."""
    temp = d
    while not is_business_day(temp):
        temp -= timedelta(days=1)
    return temp

def get_next_business_day(d: date) -> date:
    """Get the next business day on or after d."""
    temp = d
    while not is_business_day(temp):
        temp += timedelta(days=1)
    return temp

def get_last_n_business_days_of_month(year: int, month: int, n: int = 2) -> List[date]:
    """Get the last N business days of a given month."""
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    bdays = []
    temp = last_day
    while len(bdays) < n:
        if is_business_day(temp):
            bdays.append(temp)
        temp -= timedelta(days=1)
    return sorted(bdays)

# ─────────────────────────────────────────────
# IMM DATE CALCULATIONS
# ─────────────────────────────────────────────

def get_third_wednesday(year: int, month: int) -> date:
    """Get the third Wednesday of a given month."""
    d = date(year, month, 1)
    # Find first Wednesday
    while d.weekday() != 2:
        d += timedelta(days=1)
    return d + timedelta(weeks=2)

def get_sr3_reference_period(delivery_year: int, delivery_month: int) -> Tuple[date, date]:
    """
    Get the reference quarter for an SR3 contract.
    Reference Quarter: 3rd Wed of (delivery_month - 3 months) to 3rd Wed of delivery_month (exclusive)

    e.g., Mar 2026 delivery:
      Start: 3rd Wed Dec 2025 = Dec 17, 2025
      End (exclusive): 3rd Wed Mar 2026 = Mar 18, 2026
    """
    # Calculate 3 months before
    start_month = delivery_month - 3
    start_year = delivery_year
    if start_month <= 0:
        start_month += 12
        start_year -= 1

    start = get_third_wednesday(start_year, start_month)
    end = get_third_wednesday(delivery_year, delivery_month)
    return start, end

QUARTERLY_MONTHS = [3, 6, 9, 12]

CONTRACT_MONTH_CODES = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
CONTRACT_MONTH_NAMES = {3: 'Mar', 6: 'Jun', 9: 'Sep', 12: 'Dec'}

def get_active_sr3_contracts(n: int = 16, reference_date: Optional[date] = None) -> List[Dict]:
    """
    Return the next N active SR3 quarterly contracts.
    Each dict contains contract metadata.
    """
    if reference_date is None:
        reference_date = date.today()

    contracts = []
    year = reference_date.year

    # Start looking from current quarter
    for yr in range(year, year + 5):
        for qm in QUARTERLY_MONTHS:
            contract_date = date(yr, qm, 1)
            if contract_date >= date(reference_date.year, reference_date.month, 1):
                start, end = get_sr3_reference_period(yr, qm)
                # Skip if contract already expired (reference period over)
                if end <= reference_date:
                    continue

                code = CONTRACT_MONTH_CODES[qm]
                year_2d = str(yr)[2:]
                name_short = f"{CONTRACT_MONTH_NAMES[qm]} {year_2d}"
                ticker = f"SR3{code}{year_2d}"
                days = (end - start).days

                contracts.append({
                    'ticker': ticker,
                    'name': name_short,
                    'full_name': f"{CONTRACT_MONTH_NAMES[qm]} {yr}",
                    'delivery_year': yr,
                    'delivery_month': qm,
                    'start': start,
                    'end': end,
                    'days': days,
                    'days_remaining': max(0, (end - reference_date).days),
                    'pct_elapsed': max(0, min(100, (reference_date - start).days / days * 100))
                })

                if len(contracts) >= n:
                    return contracts
    return contracts

# ─────────────────────────────────────────────
# SOFR RATE PATH
# ─────────────────────────────────────────────

def get_sofr_rate_on_date(
    d: date,
    base_sofr: float,
    fomc_changes: Dict[date, float],
    me_basis: float = 0.0001,
    qe_basis: float = 0.0002,
    ye_basis: float = 0.0004,
    apply_me: bool = True,
    apply_qe: bool = True,
    apply_ye: bool = True,
) -> float:
    """
    Get the applicable SOFR rate on a given date.

    Parameters:
    -----------
    d : date
    base_sofr : float - starting SOFR (e.g. 0.05 for 5%)
    fomc_changes : dict - {meeting_date: bps_change}
                  Rate change takes effect the next business day after meeting
    me_basis : float - month-end premium added on last 2 bdays of each month
    qe_basis : float - additional quarter-end premium (total = me + qe for qtr end)
    ye_basis : float - additional year-end premium (total = me + qe + ye for Dec 31)
    """
    # Only applies to business days; non-bday dates use previous bday's rate
    if not is_business_day(d):
        prev = get_prev_business_day(d - timedelta(days=1))
        return get_sofr_rate_on_date(prev, base_sofr, fomc_changes, me_basis, qe_basis, ye_basis,
                                     apply_me, apply_qe, apply_ye)

    # Cumulative FOMC changes: effective next business day after meeting
    rate = base_sofr
    for mtg_date, bps in sorted(fomc_changes.items()):
        effective = get_next_business_day(mtg_date + timedelta(days=1))
        if d >= effective:
            rate += bps / 10000.0

    # Basis effects (month-end, quarter-end, year-end)
    year, month = d.year, d.month
    last_2_bdays = get_last_n_business_days_of_month(year, month, 2)

    if d in last_2_bdays:
        if apply_me:
            rate += me_basis
        # Quarter-end: March, June, Sep, Dec
        if month in [3, 6, 9, 12] and apply_qe:
            rate += qe_basis
        # Year-end: December
        if month == 12 and apply_ye:
            rate += ye_basis

    return rate

def build_daily_sofr_path(
    start: date,
    end: date,
    base_sofr: float,
    fomc_changes: Dict[date, float],
    me_basis: float = 0.0001,
    qe_basis: float = 0.0002,
    ye_basis: float = 0.0004,
    apply_me: bool = True,
    apply_qe: bool = True,
    apply_ye: bool = True,
) -> pd.DataFrame:
    """Build a daily SOFR path for the given date range."""
    rows = []
    current = start
    prev_bday_rate = None

    while current < end:
        if is_business_day(current):
            r = get_sofr_rate_on_date(current, base_sofr, fomc_changes,
                                       me_basis, qe_basis, ye_basis, apply_me, apply_qe, apply_ye)
            prev_bday_rate = r
            is_bday = True
        else:
            if prev_bday_rate is None:
                # Bootstrap from day before start
                temp = current - timedelta(days=1)
                while not is_business_day(temp):
                    temp -= timedelta(days=1)
                prev_bday_rate = get_sofr_rate_on_date(temp, base_sofr, fomc_changes,
                                                        me_basis, qe_basis, ye_basis,
                                                        apply_me, apply_qe, apply_ye)
            r = prev_bday_rate
            is_bday = False

        rows.append({
            'date': current,
            'rate': r,
            'is_business_day': is_bday,
            'daily_factor': 1 + r / 360,
            'weekday': current.strftime('%a')
        })
        current += timedelta(days=1)

    return pd.DataFrame(rows)

# ─────────────────────────────────────────────
# SR3 CONTRACT PRICING
# ─────────────────────────────────────────────

def price_sr3_contract(
    start: date,
    end: date,
    base_sofr: float,
    fomc_changes: Dict[date, float],
    me_basis: float = 0.0001,
    qe_basis: float = 0.0002,
    ye_basis: float = 0.0004,
    apply_me: bool = True,
    apply_qe: bool = True,
    apply_ye: bool = True,
    today: Optional[date] = None,
) -> Dict:
    """
    Price an SR3 contract given its reference period and SOFR path.

    Returns a dict with:
    - price: IMM Index price (e.g. 95.125)
    - rate: implied annualized rate R (e.g. 4.875)
    - compound: total compound factor
    - days: total calendar days
    - daily_path: DataFrame of daily rates and factors
    """
    if today is None:
        today = date.today()

    daily = build_daily_sofr_path(start, end, base_sofr, fomc_changes,
                                   me_basis, qe_basis, ye_basis, apply_me, apply_qe, apply_ye)
    N = (end - start).days
    compound = daily['daily_factor'].prod()
    R = (compound - 1) * (360 / N) * 100
    price = 100 - R

    # DV01: derivative of price w.r.t. 1bp parallel shift
    # Approximately: 1bp * (days_remaining/360) * ... but standard = $25
    dv01_price = (end - start).days / 360 * 0.01  # approximate in price pts per bp

    return {
        'price': round(price, 7),
        'rate': round(R, 7),
        'compound': compound,
        'days': N,
        'dv01_price': round(dv01_price, 6),   # price points per 1bp parallel shift
        'dv01_dollar': 25.0,                   # $25 per bp per contract (CME standard)
        'daily_path': daily
    }

def price_all_contracts(
    contracts: List[Dict],
    base_sofr: float,
    fomc_changes: Dict[date, float],
    me_basis: float = 0.0001,
    qe_basis: float = 0.0002,
    ye_basis: float = 0.0004,
    apply_me: bool = True,
    apply_qe: bool = True,
    apply_ye: bool = True,
) -> pd.DataFrame:
    """Price all SR3 contracts and return a DataFrame."""
    rows = []
    for c in contracts:
        result = price_sr3_contract(
            c['start'], c['end'], base_sofr, fomc_changes,
            me_basis, qe_basis, ye_basis, apply_me, apply_qe, apply_ye
        )
        rows.append({
            'Ticker': c['ticker'],
            'Contract': c['name'],
            'Start': c['start'].strftime('%d %b %Y'),
            'End': c['end'].strftime('%d %b %Y'),
            'Days': c['days'],
            'Price': result['price'],
            'Rate (%)': result['rate'],
            'DV01 ($)': result['dv01_dollar'],
            'DV01 (pts)': result['dv01_price'],
            'Compound': result['compound'],
            '_start': c['start'],
            '_end': c['end'],
        })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────
# FOMC IMPACT MATRIX
# ─────────────────────────────────────────────

def calculate_fomc_weightage(
    meeting_date: date,
    contract_start: date,
    contract_end: date,
) -> float:
    """
    Calculate the weightage of a FOMC meeting on an SR3 contract.

    Weightage = (days remaining in reference period after effective date of change)
                / (total days in reference period)

    Effective date = next business day after meeting.
    """
    effective = get_next_business_day(meeting_date + timedelta(days=1))
    N = (contract_end - contract_start).days

    if effective <= contract_start:
        return 1.0  # Entire period affected
    elif effective >= contract_end:
        return 0.0  # No effect
    else:
        days_affected = (contract_end - effective).days
        return days_affected / N

def build_impact_matrix(
    meetings: List[date],
    contracts: List[Dict],
    change_bps: float = 25.0,
) -> pd.DataFrame:
    """
    Build the FOMC meeting impact matrix.

    Returns a DataFrame of: meetings (rows) × contracts (columns)
    Each cell = price impact of `change_bps` move at that meeting on that contract
    (in basis points of price, i.e., 0.01 = 1 tick)
    """
    rows = []
    for mtg in meetings:
        row = {'Meeting': mtg.strftime('%d %b %Y')}
        for c in contracts:
            w = calculate_fomc_weightage(mtg, c['start'], c['end'])
            impact = w * change_bps  # in bps of price
            row[c['name']] = round(impact, 2)
            row[f"_w_{c['name']}"] = w
        rows.append(row)
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────
# SCENARIO ENGINE
# ─────────────────────────────────────────────

DEFAULT_FOMC_DATES_2026_2027 = [
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 4, 29),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 9),
    date(2027, 1, 27),
    date(2027, 3, 17),
    date(2027, 4, 28),
    date(2027, 6, 9),
    date(2027, 7, 28),
    date(2027, 9, 15),
    date(2027, 10, 27),
    date(2027, 12, 8),
]

def build_default_scenarios() -> List[Dict]:
    """Build a set of default FOMC scenarios for quick-start."""
    meetings = DEFAULT_FOMC_DATES_2026_2027[:8]

    scenarios = [
        {
            'name': 'Base (No Change)',
            'base_sofr': 4.33,
            'changes': {m: 0 for m in meetings},
            'color': '#888888',
            'description': 'Current SOFR rate held constant'
        },
        {
            'name': '1 Cut (Mar 26)',
            'base_sofr': 4.33,
            'changes': {meetings[0]: 0, meetings[1]: -25, meetings[2]: 0, meetings[3]: 0,
                        meetings[4]: 0, meetings[5]: 0, meetings[6]: 0, meetings[7]: 0},
            'color': '#00cc88',
            'description': '25bp cut in March 2026'
        },
        {
            'name': '2 Cuts (Mar+Jun 26)',
            'base_sofr': 4.33,
            'changes': {meetings[0]: 0, meetings[1]: -25, meetings[2]: 0, meetings[3]: -25,
                        meetings[4]: 0, meetings[5]: 0, meetings[6]: 0, meetings[7]: 0},
            'color': '#00e676',
            'description': 'Cuts in March and June 2026'
        },
        {
            'name': '3 Cuts (Mar+Jun+Sep 26)',
            'base_sofr': 4.33,
            'changes': {meetings[0]: 0, meetings[1]: -25, meetings[2]: 0, meetings[3]: -25,
                        meetings[4]: 0, meetings[5]: -25, meetings[6]: 0, meetings[7]: 0},
            'color': '#69f0ae',
            'description': 'Three quarterly cuts in 2026'
        },
        {
            'name': '4 Cuts (Every Qtr 26)',
            'base_sofr': 4.33,
            'changes': {meetings[0]: 0, meetings[1]: -25, meetings[2]: 0, meetings[3]: -25,
                        meetings[4]: 0, meetings[5]: -25, meetings[6]: 0, meetings[7]: -25},
            'color': '#b9f6ca',
            'description': 'Four cuts in 2026 at quarterly meetings'
        },
        {
            'name': 'Hawkish (No Cut 2026)',
            'base_sofr': 4.33,
            'changes': {m: 0 for m in meetings},
            'color': '#ff6d00',
            'description': 'No rate action in 2026'
        },
        {
            'name': '50bp Cut (Jun 26)',
            'base_sofr': 4.33,
            'changes': {meetings[0]: 0, meetings[1]: 0, meetings[2]: 0, meetings[3]: -50,
                        meetings[4]: 0, meetings[5]: 0, meetings[6]: 0, meetings[7]: 0},
            'color': '#ff9100',
            'description': 'Single 50bp cut in June 2026'
        },
        {
            'name': '25bp Hike (Mar 26)',
            'base_sofr': 4.33,
            'changes': {meetings[0]: 0, meetings[1]: +25, meetings[2]: 0, meetings[3]: 0,
                        meetings[4]: 0, meetings[5]: 0, meetings[6]: 0, meetings[7]: 0},
            'color': '#ff3d3d',
            'description': '25bp hike in March 2026'
        },
    ]
    return scenarios

# ─────────────────────────────────────────────
# CARRY & ROLL CALCULATION
# ─────────────────────────────────────────────

def calculate_carry(
    contract: Dict,
    base_sofr: float,
    fomc_changes: Dict[date, float],
    today: Optional[date] = None,
    holding_days: int = 1,
) -> Dict:
    """
    Calculate the carry for an SR3 contract over holding_days.

    Carry = change in contract price from time decay alone (assuming no rate change)
    = (locked-in SOFR for elapsed days) contributed to price
    """
    if today is None:
        today = date.today()

    price_today = price_sr3_contract(contract['start'], contract['end'],
                                      base_sofr, fomc_changes)['price']

    future_date = today + timedelta(days=holding_days)
    # After holding_days, some days have been realized at current SOFR
    # Price would change as those days are "locked in"
    new_start = min(future_date, contract['end'])
    if new_start >= contract['end']:
        return {'daily_carry_bps': 0, 'daily_carry_dollar': 0}

    price_future = price_sr3_contract(new_start, contract['end'],
                                       base_sofr, fomc_changes)['price']

    # Carry = price change from realized rates
    carry_price_pts = price_future - price_today
    carry_bps = carry_price_pts * 100  # convert to bps
    carry_dollar = carry_bps * 25  # $25 per bp

    return {
        'carry_price_pts': carry_price_pts,
        'daily_carry_bps': carry_bps / holding_days,
        'daily_carry_dollar': carry_dollar / holding_days,
    }

# ─────────────────────────────────────────────
# SPREAD & FLY CALCULATIONS
# ─────────────────────────────────────────────

def calculate_spread(price1: float, price2: float) -> Dict:
    """Calculate a calendar spread."""
    spread = price1 - price2  # front - back
    return {
        'spread': round(spread * 100, 3),   # in bps
        'spread_pts': round(spread, 5),      # in price pts
        'dollar_value': round(spread * 100 * 25, 2)  # $ per contract pair
    }

def calculate_butterfly(price1: float, price2: float, price3: float) -> Dict:
    """Calculate a butterfly (front - 2*middle + back)."""
    fly = price1 - 2 * price2 + price3
    return {
        'fly': round(fly * 100, 3),         # in bps
        'fly_pts': round(fly, 5),            # in price pts
        'dollar_value': round(fly * 100 * 25, 2)
    }

# ─────────────────────────────────────────────
# MEETING PROBABILITY (OIS-IMPLIED)
# ─────────────────────────────────────────────

def extract_meeting_probability(
    contract_price_before: float,
    contract_price_after: float,
    days_before: int,
    days_after: int,
    total_days: int,
    current_sofr: float,
    cut_size_bps: float = 25.0,
) -> Dict:
    """
    Extract implied probability of a rate cut from SR3 futures.

    Based on: implied_rate = current_sofr * (days_before/total) +
              (current_sofr + cut) * prob + current_sofr * (1-prob)) * (days_after/total)

    Returns probability of a 25bp cut.
    """
    implied_rate = 100 - contract_price_after
    weight_after = days_after / total_days
    weight_before = 1 - weight_after

    # implied_rate = r_before * w_before + r_after * w_after
    # r_after = current_sofr + cut * prob
    # Solving for prob:
    r_before = current_sofr
    r_after_no_cut = current_sofr
    r_after_full_cut = current_sofr + cut_size_bps / 100

    expected_r_after = (implied_rate - r_before * weight_before) / weight_after
    prob = (expected_r_after - r_after_no_cut) / (r_after_full_cut - r_after_no_cut)
    prob = max(0.0, min(1.0, prob))

    return {
        'prob_cut': round(prob * 100, 1),
        'prob_hold': round((1 - prob) * 100, 1),
        'implied_rate_after': round(expected_r_after, 4),
    }

# ─────────────────────────────────────────────
# P&L ENGINE
# ─────────────────────────────────────────────

def calculate_pnl(
    entry_price: float,
    exit_price: float,
    num_contracts: int,
    direction: str = 'long',  # 'long' or 'short'
) -> Dict:
    """Calculate P&L for an SR3 futures position."""
    price_diff = exit_price - entry_price  # in price points
    if direction == 'short':
        price_diff = -price_diff

    bps_change = price_diff * 100
    dollar_pnl = bps_change * 25 * num_contracts
    tick_pnl = price_diff / 0.005  # number of half-bp ticks

    return {
        'price_change_pts': round(price_diff, 4),
        'bps_change': round(bps_change, 2),
        'tick_change': round(tick_pnl, 1),
        'dollar_pnl': round(dollar_pnl, 2),
        'pnl_per_contract': round(dollar_pnl / max(1, num_contracts), 2)
    }

# ─────────────────────────────────────────────
# CONVEXITY ADJUSTMENT (SIMPLIFIED ESTIMATE)
# ─────────────────────────────────────────────

def estimate_convexity_adj(
    time_to_expiry_years: float,
    sigma: float = 0.005,  # rate volatility (50bps annual)
) -> float:
    """
    Simple convexity adjustment estimate for SOFR futures vs OIS swap.
    Futures convexity = -0.5 * sigma^2 * t1 * t2
    where t1 = time to start of reference quarter, t2 = time to end
    (Simplified formula; exact depends on rate model)
    """
    t1 = time_to_expiry_years
    t2 = t1 + 0.25  # approximately 3-month period
    conv_adj = -0.5 * sigma**2 * t1 * t2
    return round(conv_adj * 10000, 2)  # in bps

# ─────────────────────────────────────────────
# RISK METRICS
# ─────────────────────────────────────────────

def calculate_portfolio_dv01(positions: List[Dict]) -> Dict:
    """
    Calculate portfolio DV01 from a list of positions.
    Each position: {'contract': str, 'quantity': int, 'direction': str}
    """
    total_dv01 = 0
    for pos in positions:
        sign = 1 if pos.get('direction', 'long') == 'long' else -1
        total_dv01 += sign * pos.get('quantity', 0) * 25  # $25 per bp

    return {
        'total_dv01': total_dv01,
        'dv01_per_bp': total_dv01,
        'pnl_100bp': total_dv01 * 100
    }

# ─────────────────────────────────────────────
# TERM SOFR IMPLIED
# ─────────────────────────────────────────────

def implied_term_sofr(
    contracts: List[Dict],
    prices: List[float],
    term_months: int = 12,
) -> float:
    """
    Compute implied n-month term SOFR from strip of SR3 contracts.
    Returns annualized compounded rate.
    """
    compound = 1.0
    total_days = 0

    for c, price in zip(contracts, prices):
        r = (100 - price) / 100
        days = c['days']
        compound *= (1 + r * days / 360)
        total_days += days
        if total_days >= term_months * 30:
            break

    implied = ((compound - 1) * 360 / total_days) * 100
    return round(implied, 4)
