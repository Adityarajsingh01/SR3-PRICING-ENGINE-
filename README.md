# SR3 SOFR Futures Terminal 🟧

A Bloomberg Terminal-style professional trading dashboard for CME Three-Month SOFR Futures (SR3), built with Streamlit.

## Features

### 📊 Overview
- Real-time contract pricing for all active SR3 quarterly contracts
- Forward rate curve visualization
- FOMC meeting countdown and cumulative rate path
- Configurable basis effects (ME, QE, YE)

### ⚙️ Pricing Engine
- Full day-by-day SOFR compounding per CME specs
- Editable FOMC meeting dates and rate changes
- Daily SOFR path visualization per contract
- Convexity adjustment estimates

### 🔄 Scenario Builder
- Up to **30 named scenarios** with custom SOFR paths
- Side-by-side price comparison with color-coded diffs vs base
- Multi-scenario rate curve overlay chart
- Add, edit, duplicate, and delete scenarios

### 📋 FOMC Impact Matrix
- Weightage heatmap: how each FOMC meeting affects each contract
- Dollar impact per meeting per contract
- Cumulative impact if all meetings move by X bps

### 💰 P&L Calculator
- Multi-leg position builder (long/short, any quantity)
- P&L computed under each scenario
- Bar chart + summary table
- Per-contract and aggregate P&L

### 📈 Curve & Analytics
- Forward rate curve with scenario overlays
- IMM Index price curve
- Implied term SOFR rates (3M, 6M, 9M, 12M, 18M, 24M)
- Convexity adjustments with configurable vol assumption
- DV01 profile by contract

### 📐 Spreads & Flies
- All calendar spreads (consecutive contracts)
- All butterfly values
- Pack pricing (Whites/Reds/Greens)
- Custom spread calculator
- Spread comparison across scenarios

### 📌 Risk Monitor
- DV01 profile chart
- Carry indicators
- Implied meeting cut probabilities
- Parallel shift sensitivity table
- Position P&L heat map

## Pricing Methodology

Per CME official specification:

```
Price = 100 − R
R = (∏(1 + SOFR_i/360) − 1) × (360/N) × 100

Where:
  SOFR_i = daily SOFR rate (weekends/holidays use last business day's rate)
  N = total calendar days in reference quarter
  Reference Quarter = 3rd Wed of (delivery month − 3) to 3rd Wed of delivery month
```

**DV01 = $25 per basis point per contract** (CME standard, $2,500 per index point)

## Deployment

### Local
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Cloud
1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo, set `app.py` as entry point
4. Deploy!

## Contract Specifications

| Spec | Detail |
|------|--------|
| Product | CME SR3 Three-Month SOFR Futures |
| Delivery Months | Mar, Jun, Sep, Dec |
| Reference Quarter | 3rd Wed of named month → +3 months |
| Settlement | Cash, 100 − compounded SOFR |
| Min Tick (nearby) | 0.005 (½bp) = $12.50 |
| Min Tick (deferred) | 0.01 (1bp) = $25.00 |
| DV01 | $25/bp/contract |
| Listings | 39 consecutive quarterly months |

---
*For professional use only. Not investment advice. All calculations are indicative.*
